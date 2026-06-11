from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

RULES_FILE = Path(__file__).parent / "rules.yaml"

CODE_PLACEHOLDER = "{{CODE}}"
RULE_PLACEHOLDER = "{{RULE}}"

PROMPT_TEMPLATE = """\
You are a strict code reviewer evaluating a single rule against the Python code below.

Rule: {{RULE}}

Code:
```python
{{CODE}}
```

Decide whether the code adheres to the rule.
Respond with adheres (boolean: true if the rule is followed, false if violated)
and reason (a short explanation).
"""


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    rule_text: str

    def build_prompt(self, code: str) -> str:
        return PROMPT_TEMPLATE.replace(RULE_PLACEHOLDER, self.rule_text).replace(CODE_PLACEHOLDER, code)


def load_rules(path: Path = RULES_FILE) -> list[Rule]:
    with path.open() as f:
        data = yaml.safe_load(f)

    entries = data.get("rules") if isinstance(data, dict) else None
    if not entries:
        raise ValueError(f"No rules defined in {path}")

    rules: list[Rule] = []
    seen_ids: set[str] = set()
    for entry in entries:
        for field in ("id", "name", "rule"):
            if field not in entry:
                raise ValueError(f"Rule entry missing required field {field!r}: {entry}")
        if entry["id"] in seen_ids:
            raise ValueError(f"Duplicate rule id: {entry['id']!r}")
        seen_ids.add(entry["id"])
        rules.append(Rule(id=entry["id"], name=entry["name"], rule_text=entry["rule"].strip()))

    return rules


RULES: list[Rule] = load_rules()
