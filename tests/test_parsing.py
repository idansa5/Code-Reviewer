from __future__ import annotations

import json

import pytest

from app.llm.parsing import VerdictParseError, parse_verdict


def test_parse_verdict_true_from_json():
    assert parse_verdict(json.dumps({"adheres": True, "reason": "ok"})) is True


def test_parse_verdict_false_from_json():
    assert parse_verdict(json.dumps({"adheres": False, "reason": "bad"})) is False


def test_parse_verdict_strips_markdown_fence():
    raw = "```json\n" + json.dumps({"adheres": True, "reason": "ok"}) + "\n```"
    assert parse_verdict(raw) is True


def test_parse_verdict_handles_string_boolean():
    assert parse_verdict('{"adheres": "true", "reason": "ok"}') is True


def test_parse_verdict_falls_back_to_bare_token():
    assert parse_verdict("The code does not adhere. Verdict: false") is False


def test_parse_verdict_raises_on_garbage():
    with pytest.raises(VerdictParseError):
        parse_verdict("this response contains neither json nor a boolean")
