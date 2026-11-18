"""l2-errata command line: classify mistakes with ERRANT and append them to the log.

Examples
  uv run scripts/errata.py classify "depends of" "depends on"
  uv run scripts/errata.py add --original "count with me" --corrected "count on me" \\
      --cause CALQUE --context "Please count with me." --source chat --note "contar conmigo"
  uv run scripts/errata.py import batch.jsonl --source chat --date 2026-11-15
  uv run scripts/errata.py check
  uv run scripts/errata.py stats --by month

Setup
  uv sync
"""
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError

from l2_errata import DEFAULT_LOG
from l2_errata.classifier import ErrantClassifier
from l2_errata.log import Log, LogError, Recorder, RecordError
from l2_errata.models import Cause, Entry, EntryDraft, Source, Variety, format_errors
from l2_errata.schema import EntrySchema
from l2_errata.stats import Group, Period, Stats, StatsReport

app = typer.Typer(help="Classify language-learning mistakes with ERRANT and log them.", no_args_is_help=True,
                  add_completion=False)
classifier = ErrantClassifier()

LogOpt = Annotated[Path, typer.Option(help="JSONL log file")]
DateOpt = Annotated[Optional[dt.datetime], typer.Option(formats=["%Y-%m-%d"], show_default="today")]
DryRunOpt = Annotated[bool, typer.Option("--dry-run", help="show what would be added without writing it")]


def fail(lines: list[str], header: str, code: int = 1) -> typer.Exit:
    typer.echo(header, err=True)
    for line in lines:
        typer.echo(f"  {line}", err=True)
    return typer.Exit(code)


def load(log: Log) -> list[Entry]:
    try:
        return log.entries()
    except LogError as err:
        raise fail(err.problems, f"{log.path} has invalid entries (run scripts/validate.py):")


@app.command()
def classify(
    original: str,
    corrected: str,
    context: Annotated[Optional[str], typer.Option(help="full original sentence containing the mistake")] = None,
):
    """Show the ERRANT type for an original → corrected pair."""
    r = classifier.classify(original, corrected, context)
    typer.echo(r.type)
    for e in r.edits:
        typer.echo(f"  {e}")
    if r.note:
        typer.echo(f"  note: {r.note}")


@app.command()
def add(
    original: Annotated[str, typer.Option()],
    corrected: Annotated[str, typer.Option(help='use "" for a pure deletion')],
    cause: Annotated[Cause, typer.Option(help="see taxonomy.yaml")],
    context: Annotated[Optional[str], typer.Option(help="full original sentence")] = None,
    source: Source = Source.OTHER,
    note: Optional[str] = None,
    variety: Annotated[Optional[Variety], typer.Option(help="English variety the correction follows (for VARIETY_MIX)")] = None,
    lang: str = "en",
    l1: str = "es",
    date: DateOpt = None,
    type_: Annotated[Optional[str], typer.Option("--type", help="override the ERRANT type (required when --lang is not en)")] = None,
    log: LogOpt = DEFAULT_LOG,
    dry_run: DryRunOpt = False,
):
    """Classify a mistake and append it to the log as a validated entry."""
    if type_ is None and lang != "en":
        raise fail([], "ERRANT only classifies English; pass --type for other languages.", code=2)
    try:
        draft = EntryDraft(original=original, corrected=corrected, cause=cause, context=context, source=source,
                           note=note, variety=variety, lang=lang, l1=l1, errant_type=type_)
    except ValidationError as err:
        raise fail(format_errors(err), "Entry not added:")
    recorder = Recorder(Log(log), classifier)
    try:
        [r] = recorder.record([draft], date=(date or dt.datetime.now()).date(), source=source,
                              dry_run=dry_run, number_lines=False)
    except (RecordError, LogError) as err:
        raise fail(err.problems, "Entry not added:")

    if r.classification:
        for e in r.classification.edits:
            typer.echo(f"  {e}")
    if dry_run:
        typer.echo(json.dumps(r.entry.to_dict(), ensure_ascii=False, indent=2))
    else:
        typer.echo(f"Added {r.entry.id}  {r.entry.errant_type}  {r.entry.cause.value}  ({r.why})")


@app.command("import")
def import_(
    file: Annotated[Path, typer.Argument(help='JSONL file, or "-" for stdin', allow_dash=True)],
    source: Annotated[Source, typer.Option(help="default source for lines without one")] = Source.OTHER,
    date: Annotated[Optional[dt.datetime], typer.Option(formats=["%Y-%m-%d"], show_default="today",
                                                        help="default date for lines without one")] = None,
    log: LogOpt = DEFAULT_LOG,
    dry_run: DryRunOpt = False,
):
    """Append many partial entries from a JSONL file at once (all-or-nothing).

    Each line needs original, corrected and cause. Missing id, date, lang, l1 and
    errant_type are filled in (errant_type via ERRANT for English).
    """
    text = sys.stdin.read() if str(file) == "-" else file.read_text(encoding="utf-8")
    recorder = Recorder(Log(log), classifier)
    try:
        drafts = recorder.read_drafts(text)
        recorded = recorder.record(drafts, date=(date or dt.datetime.now()).date(), source=source, dry_run=dry_run)
    except (RecordError, LogError) as err:
        raise fail(err.problems, "Nothing imported:")

    for r in recorded:
        e = r.entry
        typer.echo(f"  {e.id}  {e.errant_type:<14} {e.cause.value:<18} {e.original!r} → {e.corrected!r}")
    if dry_run:
        typer.echo(f"{len(recorded)} entries would be added (dry run)")
    else:
        typer.echo(f"Imported {len(recorded)} entries into {log}")


@app.command()
def check(
    log: LogOpt = DEFAULT_LOG,
    strict: Annotated[bool, typer.Option(help="exit 1 when any label disagrees")] = False,
):
    """Re-classify every English entry in the log and list disagreements."""
    entries = [e for e in load(Log(log)) if e.lang == "en"]
    disagreements = 0
    for e in entries:
        r = classifier.classify(e.original, e.corrected, e.context)
        if r.type != e.errant_type:
            disagreements += 1
            typer.echo(f"{e.id}  log={e.errant_type:<14} errant={r.type:<14} {e.original!r} → {e.corrected!r}")
            if r.note:
                typer.echo(f"{'':14}note: {r.note}")
    typer.echo(f"{len(entries)} entries checked, {disagreements} disagreement(s)")
    if strict and disagreements:
        raise typer.Exit(1)


@app.command()
def stats(
    log: LogOpt = DEFAULT_LOG,
    by: Annotated[Period, typer.Option(help="trend period")] = Period.WEEK,
    group: Annotated[Group, typer.Option(help="what the trend columns count: cause, main ERRANT type, or full type")] = Group.CAUSE,
    top: Annotated[int, typer.Option(help="rows/columns to show before grouping the rest")] = 5,
    since: Annotated[Optional[dt.datetime], typer.Option(formats=["%Y-%m-%d"], help="inclusive")] = None,
    until: Annotated[Optional[dt.datetime], typer.Option(formats=["%Y-%m-%d"], help="inclusive")] = None,
    lang: Annotated[str, typer.Option(help='target language, or "all"')] = "en",
    as_json: Annotated[bool, typer.Option("--json", help="machine-readable output")] = False,
):
    """Top causes and types, trend by week or month, repeated mistakes."""
    entries = load(Log(log))
    if lang != "all":
        entries = [e for e in entries if e.lang == lang]
    if since:
        entries = [e for e in entries if e.date >= since.date()]
    if until:
        entries = [e for e in entries if e.date <= until.date()]
    if not entries:
        typer.echo("No entries match.")
        return

    s = Stats(entries, by=by, group=group, top=top).compute()
    if as_json:
        typer.echo(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        typer.echo(StatsReport(s, lang=lang, top=top).render())


@app.command()
def schema(check: Annotated[bool, typer.Option("--check", help="exit 1 if the file is out of date instead of writing it")] = False):
    """Write schema/entry.schema.yaml from the pydantic models."""
    s = EntrySchema()
    if check:
        if problems := s.problems():
            raise fail(problems, "Schema check failed:")
        typer.echo(f"{s.path.name} is up to date")
        return
    s.write()
    typer.echo(f"Wrote {s.path}")


if __name__ == "__main__":
    app()
