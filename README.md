# Code Review Platform (POC)

An async service that accepts a Python source file, runs a set of LLM-based rule
checks against it locally via [Ollama](https://ollama.com), and exposes the
results through a separate fetch endpoint.

Rules currently checked (see [Adding a rule](#adding-a-rule)):

1. All variables have meaningful names.
2. Function docstrings reflect the actual code's logic.

## How it works

- `POST /scans` accepts a `.py` file and returns immediately (`202`) with a
  `scan_id`. The scan runs in the background.
- `GET /scans/{scan_id}` returns the scan's status and, once `completed`, a
  `TRUE`/`FALSE` verdict per rule.
- Up to `MAX_PARALLEL_SCANS` scans run concurrently. A request received while
  at capacity gets `503` immediately (no queueing) — retry later.
- Identical file content (combined with the current rules version and model)
  reuses a previous scan instead of re-running the LLM.
- Scan results older than `RESULT_TTL_HOURS` are no longer returned and are
  periodically deleted.

## Prerequisites

- Python 3.12
- [Ollama](https://ollama.com) installed and running locally, with a model
  pulled, e.g.:

  ```bash
  ollama pull qwen2.5-coder:7b
  ```

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For running the test suite, also install the dev dependencies:

```bash
pip install -r requirements-dev.txt
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Meaning |
| --- | --- |
| `OLLAMA_BASE_URL` | URL of the Ollama (or compatible) server |
| `OLLAMA_MODEL` | Model used to evaluate each rule |
| `LLM_TIMEOUT_SECONDS` | Per-LLM-call timeout before the scan is marked failed |
| `MAX_PARALLEL_SCANS` | Max scans running concurrently; further requests get `503` |
| `RESULT_TTL_HOURS` | How long scan results are kept before deletion |
| `CLEANUP_INTERVAL_SECONDS` | How often expired scans are swept from the database |
| `DATABASE_URL` | SQLAlchemy async database URL |
| `RULES_VERSION` | Bump when rule prompts change, to invalidate cached verdicts |
| `MAX_FILE_SIZE_BYTES` | Reject uploads larger than this |

### Swapping the model or provider

To use a different model, change `OLLAMA_MODEL` in `.env` (and `ollama pull`
it first). To point at a different Ollama-compatible server, change
`OLLAMA_BASE_URL`. To use an entirely different provider, implement the
`LLMClient` protocol in `app/llm/client.py` and use it instead of
`OllamaClient` in `app/api/routes.py`.

## Running

```bash
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.

## Example usage

Submit a file for review:

```bash
curl -F "file=@samples/clean.py" http://localhost:8000/scans
```

```json
{"scan_id": "1f2e...", "status": "pending", "cached": false}
```

Fetch the results once the scan completes:

```bash
curl http://localhost:8000/scans/1f2e...
```

```json
{
  "scan_id": "1f2e...",
  "status": "completed",
  "created_at": "2026-06-11T12:00:00",
  "results": [
    {"rule_id": "meaningful_variable_names", "rule_name": "All variables have meaningful names", "adheres": true},
    {"rule_id": "docstring_matches_logic", "rule_name": "Docstring of function reflects the actual code's logic", "adheres": true}
  ]
}
```

Check service health:

```bash
curl http://localhost:8000/health
```

## Sample files

The `samples/` directory contains files for trying out each rule:

- `clean.py` — adheres to both rules.
- `bad_variable_names.py` — violates the meaningful-variable-names rule.
- `misleading_docstrings.py` — violates the docstring-matches-logic rule.

## Adding a rule

Rules are defined in `app/reviewer/rules.yaml` as a list of:

```yaml
- id: unique_rule_id
  name: Human-readable name
  rule: |
    ... description of what the code must (or must not) do ...
```

Every rule shares the same prompt (see `PROMPT_TEMPLATE` in
`app/reviewer/rules.py`); only the `rule` text is swapped in. Add a new
entry, restart the app, and bump `RULES_VERSION` in `.env` so previously
cached verdicts (produced under the old rule set) aren't reused.

## Running tests

```bash
pytest
```

Tests use a mocked LLM client and a throwaway SQLite database — no running
Ollama instance is required.
