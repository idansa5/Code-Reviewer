from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

RULES_FILE = Path(__file__).parent / "rules.yaml"

CODE_PLACEHOLDER = "{{CODE}}"


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    prompt_template: str

    def build_prompt(self, code: str) -> str:
        return self.prompt_template.replace(CODE_PLACEHOLDER, code)


def load_rules(path: Path = RULES_FILE) -> list[Rule]:
    with path.open() as f:
        data = yaml.safe_load(f)

    entries = data.get("rules") if isinstance(data, dict) else None
    if not entries:
        raise ValueError(f"No rules defined in {path}")

    rules: list[Rule] = []
    seen_ids: set[str] = set()
    for entry in entries:
        for field in ("id", "name", "prompt_template"):
            if field not in entry:
                raise ValueError(f"Rule entry missing required field {field!r}: {entry}")
        if entry["id"] in seen_ids:
            raise ValueError(f"Duplicate rule id: {entry['id']!r}")
        seen_ids.add(entry["id"])
        rules.append(Rule(id=entry["id"], name=entry["name"], prompt_template=entry["prompt_template"]))

    return rules


RULES: list[Rule] = load_rules()
