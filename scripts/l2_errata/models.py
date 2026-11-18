"""Pydantic models for a log entry: the source of truth for schema/entry.schema.yaml."""
import datetime as dt
import json
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any

from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

ERRANT_OPERATIONS = ("M", "R", "U")
ERRANT_TYPES = (
    "ADJ", "ADJ:FORM", "ADV", "CONJ", "CONTR", "DET", "MORPH", "NOUN", "NOUN:INFL",
    "NOUN:NUM", "NOUN:POSS", "ORTH", "OTHER", "PART", "PREP", "PRON", "PUNCT", "SPELL",
    "UNK", "VERB", "VERB:FORM", "VERB:INFL", "VERB:SVA", "VERB:TENSE", "WO",
)
ERRANT_TYPE_PATTERN = f"^({'|'.join(ERRANT_OPERATIONS)}):({'|'.join(ERRANT_TYPES)})$"

ErrantType = Annotated[str, StringConstraints(pattern=ERRANT_TYPE_PATTERN)]


class Source(str, Enum):
    """Where the mistake was written."""
    CHAT = "chat"
    NOTEBOOK = "notebook"
    EMAIL = "email"
    MESSAGE = "message"
    DOCUMENT = "document"
    SPEECH = "speech"
    OTHER = "other"


class Cause(str, Enum):
    """Likely reason for the mistake, see taxonomy.yaml."""
    CALQUE = "CALQUE"
    FALSE_FRIEND = "FALSE_FRIEND"
    L1_SYNTAX = "L1_SYNTAX"
    L1_CONVENTION = "L1_CONVENTION"
    OVERGENERALIZATION = "OVERGENERALIZATION"
    PHONETIC_SPELLING = "PHONETIC_SPELLING"
    UNNATURAL = "UNNATURAL"
    SLIP = "SLIP"
    VARIETY_MIX = "VARIETY_MIX"
    UNKNOWN = "UNKNOWN"


class Variety(str, Enum):
    """English variety a correction follows."""
    EN_US = "en-US"
    EN_GB = "en-GB"


class _SpanRules(BaseModel):
    """Rules shared by full entries and import drafts (subclasses define the fields)."""
    model_config = ConfigDict(extra="forbid")

    if TYPE_CHECKING:  # declared by subclasses, so each keeps its own field order
        original: str
        context: str | None

    @model_validator(mode="after")
    def _original_in_context(self) -> Self:
        if self.context and self.original not in self.context:
            raise ValueError(f"original {self.original!r} is not verbatim in context")
        return self


ENTRY_DESCRIPTION = (
    "One mistake = one entry = one line in a JSONL log. A sentence with three mistakes "
    "produces three entries that share the same context. Rules beyond the field types: "
    "`original` appears verbatim in `context`, the date in `id` equals `date`, VARIETY_MIX "
    "entries set `variety`, and ids are unique within a log."
)


class Entry(_SpanRules):
    """One logged mistake. See ENTRY_DESCRIPTION."""

    model_config = ConfigDict(extra="forbid", title="l2-errata log entry",
                              json_schema_extra={"description": ENTRY_DESCRIPTION})

    id: str = Field(pattern=r"^[0-9]{8}-[0-9]{3}$", description="YYYYMMDD-NNN, unique within the log.")
    date: dt.date = Field(description="Date the mistake was written (YYYY-MM-DD).")
    lang: str = Field(description="Target language being learned (BCP-47), e.g. en, sv.")
    l1: str = Field("es", description="Writer's first language (BCP-47).")
    source: Source | None = Field(None, description="Where the mistake was written.")
    original: str = Field(min_length=1, description="The mistaken span as written.")
    corrected: str = Field(description="The correction for that span. Empty string when the fix is a pure deletion.")
    context: str | None = Field(None, description="Full original sentence, for review later.")
    errant_type: ErrantType = Field(description="ERRANT operation and type, see taxonomy.yaml.")
    cause: Cause = Field(description="Likely reason for the mistake, see taxonomy.yaml.")
    variety: Variety | None = Field(
        None,
        description="English variety the correction follows (American or British). "
                    "Set it for VARIETY_MIX entries; optional elsewhere.",
    )
    note: str | None = Field(None, description="Short explanation or rule to remember.")

    @model_validator(mode="after")
    def _id_matches_date(self) -> Self:
        if not self.id.startswith(self.date.strftime("%Y%m%d") + "-"):
            raise ValueError(f"id {self.id} does not match date {self.date}")
        return self

    @model_validator(mode="after")
    def _variety_mix_has_variety(self) -> Self:
        if self.cause is Cause.VARIETY_MIX and self.variety is None:
            raise ValueError("VARIETY_MIX entries need a variety (en-US or en-GB)")
        return self

    @property
    def main_type(self) -> str:
        """R:PREP → PREP, R:VERB:TENSE → VERB:TENSE."""
        return self.errant_type.split(":", 1)[1]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EntryDraft(_SpanRules):
    """A partial entry, as written in an import batch: missing fields are filled in."""

    id: str | None = None
    date: dt.date | None = None
    lang: str | None = None
    l1: str | None = None
    source: Source | None = None
    original: str
    corrected: str
    context: str | None = None
    errant_type: str | None = None
    cause: Cause
    variety: Variety | None = None
    note: str | None = None


def format_errors(err: ValidationError) -> list[str]:
    """Turn a pydantic ValidationError into short 'field: message' lines."""
    lines = []
    for e in err.errors():
        where = ".".join(map(str, e["loc"])) or "(root)"
        lines.append(f"{where}: {e['msg'].removeprefix('Value error, ')}")
    return lines
