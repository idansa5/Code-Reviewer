from __future__ import annotations

import logging
from typing import Protocol

import ollama

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def complete(self, prompt: str, *, json_schema: dict | None = None) -> str:
        """Send a prompt to the model and return its raw text response."""

    async def is_reachable(self) -> bool:
        """Cheap connectivity check used by /health."""


class OllamaClient:
    """Thin wrapper around ollama.AsyncClient; base_url and model are injected
    so config.py controls which provider/model is used."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._model = model or settings.ollama_model
        self._client = ollama.AsyncClient(
            host=base_url or settings.ollama_base_url,
            timeout=timeout_seconds or settings.llm_timeout_seconds,
        )

    async def complete(self, prompt: str, *, json_schema: dict | None = None) -> str:
        """Send a prompt to the model and return the raw completion."""
        response = await self._client.generate(
            model=self._model,
            prompt=prompt,
            format=json_schema,
            stream=False,
            options={"temperature": 0},  # keeps output deterministic
        )
        return response.response

    async def is_reachable(self) -> bool:
        try:
            await self._client.list()
            return True
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return False
