"""Reading, validating and appending to the JSONL log."""
import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .classifier import Classification, ErrantClassifier
from .models import Entry, EntryDraft, Source, format_errors


class LogError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__(f"{len(problems)} problem(s)")
        self.problems = problems


class Log:
    """A JSONL file with one validated Entry per line."""

    def __init__(self, path: Path):
        self.path = path

    def scan(self) -> tuple[list[Entry], list[str]]:
        """Parse every line; return the valid entries and a problem per invalid line or duplicate id."""
        entries, problems, seen = [], [], set()
        if not self.path.exists():
            return entries, problems
        for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = Entry.model_validate_json(line)
            except ValidationError as err:
                problems += [f"line {n}: {p}" for p in format_errors(err)]
                continue
            if entry.id in seen:
                problems.append(f"line {n}: duplicate id {entry.id}")
            seen.add(entry.id)
            entries.append(entry)
        return entries, problems

    def entries(self) -> list[Entry]:
        """All entries; raises LogError if any line is invalid."""
        entries, problems = self.scan()
        if problems:
            raise LogError(problems)
        return entries

    def append(self, entries: Sequence[Entry]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.writelines(e.to_json_line() + "\n" for e in entries)

    @staticmethod
    def next_id(date: dt.date, taken: Iterable[str]) -> str:
        prefix = date.strftime("%Y%m%d")
        used = [int(i.split("-")[1]) for i in taken if i.startswith(prefix + "-")]
        return f"{prefix}-{max(used, default=0) + 1:03d}"


@dataclass
class Recorded:
    entry: Entry
    classification: Classification | None  # None when errant_type was given

    @property
    def why(self) -> str:
        if self.classification is None:
            return "set manually"
        return self.classification.note or "ERRANT"


class RecordError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


class Recorder:
    """Turns drafts into validated entries (filling id, date, lang, errant_type) and logs them."""

    def __init__(self, log: Log, classifier: ErrantClassifier):
        self.log = log
        self.classifier = classifier

    def build(self, draft: EntryDraft, *, taken: set[str], date: dt.date, source: Source) -> Recorded:
        """Complete one draft. Values in the draft win over the defaults passed in."""
        lang = draft.lang or "en"
        date = draft.date or date
        classification = None
        errant_type = draft.errant_type
        if errant_type is None:
            if lang != "en":
                raise RecordError([f"lang {lang} needs errant_type (ERRANT is English-only)"])
            classification = self.classifier.classify(draft.original, draft.corrected, draft.context)
            errant_type = classification.type

        fields = draft.model_dump(exclude_none=True) | {
            "id": draft.id or Log.next_id(date, taken),
            "date": date,
            "lang": lang,
            "l1": draft.l1 or "es",
            "source": draft.source or source,
            "errant_type": errant_type,
        }
        try:
            entry = Entry.model_validate(fields)
        except ValidationError as err:
            raise RecordError(format_errors(err)) from None
        if entry.id in taken:
            raise RecordError([f"duplicate id {entry.id}"])
        return Recorded(entry, classification)

    def record(self, drafts: Sequence[EntryDraft], *, date: dt.date, source: Source,
               dry_run: bool = False, number_lines: bool = True) -> list[Recorded]:
        """Build every draft, then append them all; all-or-nothing (raises RecordError).

        With number_lines, problems are prefixed with the draft's line number.
        """
        taken = {e.id for e in self.log.entries()}
        recorded, problems = [], []
        for n, draft in enumerate(drafts, 1):
            try:
                r = self.build(draft, taken=taken, date=date, source=source)
            except RecordError as err:
                prefix = f"line {n}: " if number_lines else ""
                problems += [prefix + p for p in err.problems]
                continue
            taken.add(r.entry.id)
            recorded.append(r)
        if problems:
            raise RecordError(problems)
        if not dry_run:
            self.log.append([r.entry for r in recorded])
        return recorded

    @staticmethod
    def read_drafts(text: str) -> list[EntryDraft]:
        """Parse a JSONL batch; raises RecordError listing every bad line."""
        drafts, problems = [], []
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                drafts.append(EntryDraft.model_validate_json(line))
            except ValidationError as err:
                problems += [f"line {n}: {p}" for p in format_errors(err)]
        if problems:
            raise RecordError(problems)
        return drafts
