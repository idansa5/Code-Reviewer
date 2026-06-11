from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.config import settings
from app.db import repository as repo
from app.db.session import async_session_factory
from app.llm.client import LLMClient
from app.llm.parsing import VERDICT_SCHEMA, parse_verdict
from app.reviewer.rules import RULES

logger = logging.getLogger(__name__)


async def _run(fn, *args):
    async with async_session_factory() as session:
        return await fn(session, *args)


async def run_scan(
    scan_id: str,
    code: str,
    *,
    llm_client: LLMClient,
    release_slot: Callable[[], None],
) -> None:
    """Run all configured rule checks for a scan and persist the results.

    Always ends with the scan marked completed or failed and the capacity
    slot released, even if an LLM call or response parse fails partway through.
    """
    try:
        await _run(repo.mark_running, scan_id)
        # run each rule and check the code according to it
        for rule in RULES:
            prompt = rule.build_prompt(code)
            try:
                raw = await asyncio.wait_for(
                    llm_client.complete(prompt, json_schema=VERDICT_SCHEMA),
                    timeout=settings.llm_timeout_seconds,
                )
            except TimeoutError:
                raise TimeoutError(
                    f"LLM call for rule '{rule.id}' exceeded {settings.llm_timeout_seconds}s"
                ) from None
            adheres = parse_verdict(raw)
            await _run(
                repo.save_rule_result, scan_id, rule.id, rule.name, adheres, None
            )

        await _run(
            repo.mark_completed, scan_id
        )  # mark the scan as completed after going all of the rules
    except Exception as exc:
        logger.exception("Scan %s failed", scan_id)
        try:
            await _run(repo.mark_failed, scan_id, str(exc))
        except Exception:
            logger.exception("Scan %s: also failed to record failure status", scan_id)
    finally:
        release_slot()
