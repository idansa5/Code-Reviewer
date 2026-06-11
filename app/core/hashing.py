from __future__ import annotations

import hashlib

from app.config import settings


def compute_content_hash(code: str) -> str:
    """Hash of the code plus the rules version and model that will check it.

    Including RULES_VERSION and OLLAMA_MODEL means a cached verdict is only
    reused if it was produced by the same rules and the same model.
    """
    normalized = code.replace("\r\n", "\n").strip()
    payload = f"{settings.rules_version}\0{settings.ollama_model}\0{normalized}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
