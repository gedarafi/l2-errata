"""The YAML schema generated from the Entry model, and consistency checks with taxonomy.yaml."""
from pathlib import Path
from typing import Any

import yaml
from pydantic.json_schema import GenerateJsonSchema

from . import SCHEMA_PATH, TAXONOMY_PATH
from .models import ERRANT_OPERATIONS, ERRANT_TYPES, Cause, Entry

HEADER = """\
# JSON Schema (draft 2020-12) for one l2-errata log entry, written as YAML.
# Generated from scripts/l2_errata/models.py: do not edit by hand.
# Regenerate with: uv run scripts/errata.py schema
"""


class _OptionalNotNull(GenerateJsonSchema):
    """Optional fields are omitted from entries, never null: drop the `anyOf: [.., null]` wrapper."""

    def nullable_schema(self, schema):
        return self.generate_inner(schema["schema"])


class EntrySchema:
    def __init__(self, path: Path = SCHEMA_PATH):
        self.path = path

    @staticmethod
    def generate() -> dict[str, Any]:
        body = Entry.model_json_schema(schema_generator=_OptionalNotNull)
        for prop in body["properties"].values():
            prop.pop("title", None)
            if prop.get("default", ...) is None:
                del prop["default"]
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://github.com/gedarafi/l2-errata/schema/entry.schema.yaml",
            **body,
        }

    def dump(self) -> str:
        return HEADER + yaml.safe_dump(self.generate(), sort_keys=False, allow_unicode=True, width=100)

    def write(self) -> None:
        self.path.write_text(self.dump(), encoding="utf-8")

    def problems(self) -> list[str]:
        if not self.path.exists():
            return [f"{self.path.name} is missing; run: uv run scripts/errata.py schema"]
        if yaml.safe_load(self.path.read_text(encoding="utf-8")) != self.generate():
            return [f"{self.path.name} is out of date with models.py; run: uv run scripts/errata.py schema"]
        return []


class Taxonomy:
    """taxonomy.yaml: the human-readable labels; must list the same labels as the models."""

    def __init__(self, path: Path = TAXONOMY_PATH):
        self.data = yaml.safe_load(path.read_text(encoding="utf-8"))

    def problems(self) -> list[str]:
        problems = []
        checks = [
            ("causes", set(self.data["causes"]), {c.value for c in Cause}),
            ("errant.types", set(self.data["errant"]["types"]), set(ERRANT_TYPES)),
            ("errant.operations", set(self.data["errant"]["operations"]), set(ERRANT_OPERATIONS)),
        ]
        for name, in_yaml, in_models in checks:
            if missing := sorted(in_models - in_yaml):
                problems.append(f"taxonomy.yaml {name} is missing {', '.join(missing)}")
            if extra := sorted(in_yaml - in_models):
                problems.append(f"taxonomy.yaml {name} has {', '.join(extra)}, not in models.py")
        return problems
