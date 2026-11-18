"""Validate a l2-errata JSONL log with the pydantic models, and check that
schema/entry.schema.yaml and taxonomy.yaml agree with them.

Usage: uv run scripts/validate.py [path/to/log.jsonl]
"""
from pathlib import Path
from typing import Annotated

import typer

from l2_errata import DEFAULT_LOG
from l2_errata.log import Log
from l2_errata.schema import EntrySchema, Taxonomy


def main(log: Annotated[Path, typer.Argument(help="JSONL log file")] = DEFAULT_LOG):
    """Validate the log, the YAML schema and the taxonomy."""
    entries, problems = Log(log).scan()
    problems += EntrySchema().problems() + Taxonomy().problems()
    for p in problems:
        typer.echo(p)
    typer.echo(f"{len(entries)} entries, {len(problems)} error(s)")
    if problems:
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
