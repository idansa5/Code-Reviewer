from __future__ import annotations

import asyncio
import json

from app.api import routes


class MockLLMClient:
    """Stand-in for OllamaClient: records prompts and returns scripted verdicts."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.responses: list[bool] | None = None
        self.raw_response: str | None = None
        self.exception: Exception | None = None
        self.block_event = None
        self.delay: float | None = None

    async def complete(self, prompt: str, *, json_schema: dict | None = None) -> str:
        if self.block_event is not None:
            await self.block_event.wait()
        if self.delay is not None:
            await asyncio.sleep(self.delay)
        self.calls.append(prompt)
        if self.exception is not None:
            raise self.exception
        if self.raw_response is not None:
            return self.raw_response
        if self.responses is None:
            adheres = True
        else:
            adheres = self.responses[(len(self.calls) - 1) % len(self.responses)]
        return json.dumps({"adheres": adheres, "reason": "test"})

    async def is_reachable(self) -> bool:
        return True


def code_for(label: str) -> str:
    return f"# {label}\ndef foo():\n    return 1\n"


def make_py_file(label: str) -> dict:
    return {"file": (f"{label}.py", code_for(label).encode(), "text/x-python")}


async def wait_for_new_tasks(before: set) -> None:
    for task in routes._background_tasks - before:
        await task
