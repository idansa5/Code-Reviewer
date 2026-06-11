from __future__ import annotations

from app.api import routes
from tests.helpers import make_py_file, wait_for_new_tasks


async def test_full_scan_flow_returns_rule_verdicts(client, mock_llm):
    mock_llm.responses = [True, False]
    before = set(routes._background_tasks)
    submit = await client.post("/scans", files=make_py_file("flow"))
    await wait_for_new_tasks(before)

    result = await client.get(f"/scans/{submit.json()['scan_id']}")
    assert [r["adheres"] for r in result.json()["results"]] == [True, False]


async def test_non_py_upload_is_rejected(client, mock_llm):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    r = await client.post("/scans", files=files)
    assert r.status_code == 422


async def test_empty_file_is_rejected(client, mock_llm):
    files = {"file": ("empty.py", b"", "text/x-python")}
    r = await client.post("/scans", files=files)
    assert r.status_code == 422


async def test_unknown_scan_id_returns_404(client, mock_llm):
    r = await client.get("/scans/does-not-exist")
    assert r.status_code == 404


async def test_unparseable_llm_response_marks_scan_failed(client, mock_llm):
    mock_llm.raw_response = "neither json nor a boolean"
    before = set(routes._background_tasks)
    submit = await client.post("/scans", files=make_py_file("garbage"))
    await wait_for_new_tasks(before)

    result = await client.get(f"/scans/{submit.json()['scan_id']}")
    assert result.json()["status"] == "failed"
