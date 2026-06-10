from __future__ import annotations

import json
import re

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "adheres": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["adheres", "reason"],
}

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_BOOL_TOKEN_RE = re.compile(r"\b(true|false)\b", re.IGNORECASE)


class VerdictParseError(Exception):
    """Raised when an LLM response cannot be parsed into a verdict."""


def parse_verdict(raw: str) -> bool:
    """Parse an LLM response into an adherence verdict, tolerating common deviations."""
    text = _FENCE_RE.sub("", raw.strip()).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict) and "adheres" in data:
        adheres = data["adheres"]
        if isinstance(adheres, str):
            return adheres.strip().lower() == "true"
        return bool(adheres)

    match = _BOOL_TOKEN_RE.search(text)
    if match:
        return match.group(1).lower() == "true"

    raise VerdictParseError(f"Could not parse verdict from response: {raw!r}")
