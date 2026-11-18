---
name: l2-errata
description: Proofread text a language learner wrote (grammar check, "check this", a photo of notebook notes), explain each fix, and log every mistake to their l2-errata log so progress can be tracked.
---

# l2-errata: correct, explain, log

The learner writes in a target language (default English, `en`) with a first language of Spanish (`es`). Every correction has two outputs: a friendly explanation for the learner, and one log entry per mistake in the l2-errata repository (`github.com/gedarafi/l2-errata`). Labels are defined in the repo's `taxonomy.yaml`; the entry format is `schema/entry.schema.yaml`.

## 1. Correct and explain

Reply first, log second. The reply is what the learner reads:

1. One line verdict: correct, or how many things to fix.
2. **Corrected:** the text with only the necessary fixes.
3. Each fix in a short bullet: what changed and why, in plain words. When a mistake comes from Spanish, name the Spanish source ("contar conmigo → count **on** me"), because that is the part that sticks.
4. Optionally, **Polished:** a more natural version, kept clearly separate from the required fixes.

If the text is already correct, say so, offer at most one optional tweak, and log nothing. For handwriting you cannot read with confidence, ask rather than guess, and do not log that part.

## 2. Turn each mistake into an entry

One mistake = one entry. A sentence with three mistakes gives three entries sharing the same `context`.

| Field | Rule |
|---|---|
| `original` | Smallest span that shows the mistake, copied **verbatim** (it must appear exactly in `context`) |
| `corrected` | The fix for that span; `""` for a pure deletion |
| `context` | The full sentence as the learner wrote it, mistakes included |
| `cause` | Why it happened, from the list below |
| `note` | The rule to remember in a few words; include the Spanish source when there is one |
| `source` | `chat`, `notebook`, `email`, `message`, `document`, `speech` or `other` |

Leave `id`, `date`, `lang`, `l1` and `errant_type` out: the import command fills them in (ERRANT labels the grammar type for English).

Causes:

| Cause | Use when | Example |
|---|---|---|
| `CALQUE` | Literal translation of a Spanish phrase | count with me → count on me |
| `FALSE_FRIEND` | Looks like a Spanish word, means something else | aliments → foods |
| `L1_SYNTAX` | Spanish sentence structure or word order | While exists willing… → As long as there is… |
| `L1_CONVENTION` | Spanish spelling/punctuation convention | swedish → Swedish |
| `OVERGENERALIZATION` | An English rule applied where it does not fit | may contains → may contain |
| `PHONETIC_SPELLING` | Spelled the way it sounds | summarice → summarize |
| `UNNATURAL` | Grammatical but not what a native speaker says | exchange the call → swap the call |
| `SLIP` | Knows the rule, momentary mistake | ? maybe → ? Maybe |
| `VARIETY_MIX` | US spelling in a British text or the reverse, or both mixed; add `"variety": "en-GB"` or `"en-US"` (the variety of the correction) | program → programme (en-GB) |
| `UNKNOWN` | Cause unclear; say why in `note` | |

Log required fixes only. Optional polish is not a mistake; use `UNNATURAL` only when a native speaker would clearly not say it. Skip casual chat noise (emoji codes, deliberate stretching like "nooo").

## 3. Log the entries

Write the entries as JSONL, one object per line:

```json
{"original": "count with me", "corrected": "count on me", "cause": "CALQUE", "context": "If you ever need something please count with me.", "note": "contar conmigo = count ON me"}
```

**With a shell and access to the repo**, from the repo root:

```bash
uv sync   # first time only
uv run scripts/errata.py import batch.jsonl --source chat --date YYYY-MM-DD   # learner's local date
uv run scripts/validate.py
git add data/log.jsonl
git commit -m "Log N mistakes (<source>, YYYY-MM-DD)"
git push
```

`import` is all-or-nothing: if any line is invalid (most often an `original` that is not verbatim in `context`), nothing is written; fix the line and run it again. For a target language other than English, add `"lang"` and an `"errant_type"` to each line yourself, since ERRANT is English-only.

**Without a shell or repo access**, end the reply with the JSONL in a code block titled `batch.jsonl`, so the learner can run the import later.

## 4. Report

After the explanation, one short line: how many mistakes were logged. Then run `uv run scripts/errata.py stats --json` and, if any of today's mistakes appear in `repeats`, point it out kindly ("second time for *interested on*: it's **in**"). Repeats are the most useful signal the log gives, so never skip this check when the log is reachable.

## Adapting for another learner

Fork the repo, empty `data/log.jsonl`, and change the defaults: `l1` in `scripts/errata.py` (`add`) and `scripts/l2_errata/log.py` (`Recorder.build`), the Spanish examples above, and the repository named at the top of this file.
