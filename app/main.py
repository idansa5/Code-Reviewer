from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.db.repository import delete_expired_scans
from app.db.session import async_session_factory, init_db


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(settings.cleanup_interval_seconds)
        async with async_session_factory() as session:
            await delete_expired_scans(session)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Code Review Platform", lifespan=lifespan)
app.include_router(router)
