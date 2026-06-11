from __future__ import annotations

import asyncio
import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.capacity import CapacityLimiter
from app.core.hashing import compute_content_hash
from app.db import repository as repo
from app.db.models import ScanStatus
from app.db.session import get_session
from app.llm.client import LLMClient, OllamaClient
from app.reviewer.scanner import run_scan
from app.schemas import (
    HealthResponse,
    RuleResultOut,
    ScanResultResponse,
    ScanSubmitResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Process-wide singletons. A single asyncio.Lock serializes the cache
# lookup -> create-scan section (see app/db/models.py for the matching
# defensive partial unique index).
cache_lock = asyncio.Lock()
capacity_limiter = CapacityLimiter(max_concurrent=settings.max_parallel_scans)
llm_client: LLMClient = OllamaClient()
_background_tasks: set[asyncio.Task] = set()


def get_capacity_limiter() -> CapacityLimiter:
    return capacity_limiter


def get_llm_client() -> LLMClient:
    return llm_client


def get_cache_lock() -> asyncio.Lock:
    return cache_lock


# Submit a new scan request.
@router.post("/scans", response_model=ScanSubmitResponse)
async def submit_scan(
    response: Response,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    limiter: CapacityLimiter = Depends(get_capacity_limiter),
    client: LLMClient = Depends(get_llm_client),
    lock: asyncio.Lock = Depends(get_cache_lock),
) -> ScanSubmitResponse:
    if not file.filename or not file.filename.lower().endswith(".py"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Only .py files are accepted"
        )
    # check the file is non-empty, valid UTF-8, and within the size limit
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Uploaded file is empty"
        )
    if len(raw) > settings.max_file_size_bytes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "File exceeds maximum size"
        )

    try:
        code = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "File must be valid UTF-8 text"
        )

    if not code.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Uploaded file is empty"
        )

    content_hash = compute_content_hash(code)
    #  atomically check cache, update stale scans and, if no cached entry, create a new scan and queue it.
    async with lock:
        await repo.fail_stale_scans(session)
        existing = await repo.find_reusable_scan(session, content_hash)
        if existing is not None:
            logger.debug(
                "Scan %s reused for content_hash %s (status=%s)",
                existing.id,
                content_hash,
                existing.status,
            )
            response.status_code = (
                status.HTTP_200_OK
                if existing.status == ScanStatus.COMPLETED.value
                else status.HTTP_202_ACCEPTED
            )
            return ScanSubmitResponse(
                scan_id=existing.id, status=existing.status, cached=True
            )

        if not limiter.try_acquire():  # at capacity (max_parallel_scans)
            logger.warning(
                "Scan submission rejected: at capacity (%d/%d)",
                limiter.in_use,
                settings.max_parallel_scans,
            )
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"Scan capacity reached ({settings.max_parallel_scans} concurrent scans). "
                "Please try again later.",
            )

        try:
            scan = await repo.create_scan(session, content_hash, file.filename, code)
        except Exception:
            limiter.release()  # in case the creation of the scan failed, release the slot
            raise
    # keep a reference to the background task to prevent early garbage collection
    try:
        task = asyncio.create_task(
            run_scan(scan.id, code, llm_client=client, release_slot=limiter.release)
        )
    except Exception:
        limiter.release()
        raise
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    logger.info("Scan %s submitted (file=%s)", scan.id, file.filename)
    response.status_code = status.HTTP_202_ACCEPTED
    return ScanSubmitResponse(scan_id=scan.id, status=scan.status, cached=False)


# get scan result by id
@router.get("/scans/{scan_id}", response_model=ScanResultResponse)
async def get_scan_result(
    scan_id: str, session: AsyncSession = Depends(get_session)
) -> ScanResultResponse:
    scan = await repo.get_scan(session, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")

    return ScanResultResponse(
        scan_id=scan.id,
        status=scan.status,
        created_at=scan.created_at,
        results=[
            RuleResultOut(rule_id=r.rule_id, rule_name=r.rule_name, adheres=r.adheres)
            for r in scan.results
        ],
    )


@router.get("/health", response_model=HealthResponse)
async def health(client: LLMClient = Depends(get_llm_client)) -> HealthResponse:
    return HealthResponse(status="ok", ollama_reachable=await client.is_reachable())
