from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes import router
from app.db.session import init_db


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    yield


app = FastAPI(title="Code Review Platform", lifespan=lifespan)
app.include_router(router)
