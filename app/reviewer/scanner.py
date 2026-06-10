from __future__ import annotations

import logging
from collections.abc import Callable

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

        for rule in RULES:
            prompt = rule.build_prompt(code)
            raw = await llm_client.complete(prompt, json_schema=VERDICT_SCHEMA)
            adheres = parse_verdict(raw)
            await _run(repo.save_rule_result, scan_id, rule.id, rule.name, adheres, None)

        await _run(repo.mark_completed, scan_id)
    except Exception as exc:
        logger.exception("Scan %s failed", scan_id)
        await _run(repo.mark_failed, scan_id, str(exc))
    finally:
        release_slot()
