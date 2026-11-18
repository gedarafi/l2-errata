"""ERRANT classification of one original → corrected pair."""
import re
from functools import cached_property

from pydantic import BaseModel


class Edit(BaseModel):
    type: str
    original: str
    corrected: str

    def __str__(self) -> str:
        return f"{self.type:<14} {self.original!r} → {self.corrected!r}"


class Classification(BaseModel):
    type: str               # single label for the log entry
    edits: list[Edit] = []  # every edit ERRANT found inside the span
    note: str = ""          # why the label was chosen when it is not a single edit


class ErrantClassifier:
    """Wraps ERRANT; the English model is loaded on first use (it takes a few seconds)."""

    @cached_property
    def annotator(self):
        import errant
        return errant.load("en")

    @staticmethod
    def tidy(text: str) -> str:
        """Collapse spaces left behind by deletions, e.g. 'go  as' → 'go as'."""
        return re.sub(r"\s+([,.;:!?])", r"\1", re.sub(r" {2,}", " ", text)).strip()

    def classify(self, original: str, corrected: str, context: str | None = None) -> Classification:
        """Return the ERRANT type for one mistake.

        With a context sentence, ERRANT sees the whole sentence (more accurate POS
        tags) and only edits overlapping the mistaken span are kept.
        """
        ann = self.annotator

        if context and original in context:
            start = context.index(original)
            end = start + len(original)
            orig_text = context
            cor_text = self.tidy(context[:start] + corrected + context[end:])
        else:
            start, end = 0, len(original)
            orig_text, cor_text = original, corrected

        orig_doc = ann.parse(orig_text, tokenise=True)
        cor_doc = ann.parse(cor_text, tokenise=True)
        edits = []
        for e in ann.annotate(orig_doc, cor_doc):
            # Character position of the edit in the original text.
            e_start = orig_doc[e.o_start].idx if e.o_start < len(orig_doc) else len(orig_text)
            if e.o_end > e.o_start:
                e_end = orig_doc[e.o_end - 1].idx + len(orig_doc[e.o_end - 1])
            else:
                e_end = e_start
            if e_start <= end and e_end >= start:
                edits.append(Edit(type=e.type, original=e.o_str, corrected=e.c_str))

        if not edits:
            return Classification(type="R:OTHER", note="ERRANT found no edit; defaulted to R:OTHER")
        if len(edits) == 1:
            return Classification(type=edits[0].type, edits=edits)
        if len({e.type for e in edits}) == 1:
            return Classification(type=edits[0].type, edits=edits, note=f"{len(edits)} edits of the same type")
        return Classification(
            type="R:OTHER", edits=edits,
            note="several edit types in one span; defaulted to R:OTHER (or split the entry)",
        )
