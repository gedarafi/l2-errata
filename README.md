# l2-errata

A platform-agnostic log of language-learning mistakes, built so you can see which kinds of errors you make and whether they are going away.

Each mistake gets two labels:

| Layer | Answers | Source |
|---|---|---|
| `errant_type` | **What** changed (preposition, verb tense, spelling…) | ERRANT (Bryant, Felice & Briscoe, 2017) |
| `cause` | **Why** it probably happened (calque, false friend, slip…) | Custom to l2-errata |

The grammar layer is citable and machine-checkable; the cause layer is what makes the log useful to a learner. See [`taxonomy.yaml`](taxonomy.yaml) for every label with examples.

## Layout

```
l2-errata/
├── taxonomy.yaml             # all labels: ERRANT types + custom causes
├── schema/entry.schema.yaml  # JSON Schema (as YAML) for one log entry, generated from the models
├── data/log.jsonl            # the log: one mistake per line
├── pyproject.toml            # dependencies (uv), incl. the spaCy model
├── uv.lock
├── justfile                  # shortcuts: just add / import / stats / validate…
├── scripts/
│   ├── errata.py             # CLI (Typer): classify / add / import / check / stats / schema
│   ├── validate.py           # validates a log, the schema and the taxonomy
│   └── l2_errata/            # models (Pydantic), ERRANT classifier, log, stats
└── skills/l2-errata/SKILL.md # agent skill: correct, explain, log
```

Plain JSONL + JSON Schema keeps the data readable by any language, editor, spreadsheet or AI tool. The Pydantic models in [`scripts/l2_errata/models.py`](scripts/l2_errata/models.py) are the source of truth: they enforce the format, and `uv run scripts/errata.py schema` regenerates the YAML schema from them.

## Entry format

One mistake per line. A sentence with three mistakes becomes three entries sharing the same `context`.

```json
{"id": "20261114-004", "date": "2026-11-14", "lang": "en", "l1": "es", "source": "chat",
 "original": "count with me", "corrected": "count on me",
 "context": "If you ever need something please count with me.",
 "errant_type": "R:PREP", "cause": "CALQUE", "note": "contar conmigo = count ON me."}
```

| Field | Required | Notes |
|---|---|---|
| `id` | ✓ | `YYYYMMDD-NNN`, unique |
| `date` | ✓ | `YYYY-MM-DD` |
| `lang` | ✓ | Target language (`en`, `sv`, …) |
| `l1` | | First language, default `es` |
| `source` | | `chat`, `notebook`, `email`, `message`, `document`, `speech`, `other` |
| `original` | ✓ | The mistaken span |
| `corrected` | ✓ | The fix (`""` for a pure deletion) |
| `context` | | Full original sentence |
| `errant_type` | ✓ | `M`/`R`/`U` + ERRANT type, e.g. `R:PREP` |
| `cause` | ✓ | One of the causes in `taxonomy.yaml` |
| `variety` | | `en-US` or `en-GB`: the English variety the correction follows (set it for `VARIETY_MIX`) |
| `note` | | Rule to remember |

## Setup

```bash
uv sync
```

This creates `.venv` with ERRANT, the `en_core_web_sm` spaCy model, Pydantic and Typer. Run the scripts with `uv run`.

With [just](https://github.com/casey/just) installed, `just` lists shortcuts for the common commands (`just add "I am agree" "I agree" CALQUE --context "…"`, `just stats`, `just validate`…).

## Usage

**Log a mistake.** You give the two strings and the cause; ERRANT fills in `errant_type`, and the id and date are generated.

```bash
uv run scripts/errata.py add \
  --original "I am agree" --corrected "I agree" --cause CALQUE \
  --context "I am agree with you." --source chat --note "estoy de acuerdo = I agree"
# Added 20261115-010  U:VERB:TENSE  CALQUE  (ERRANT)
```

Pass `--context` with the full sentence when you have it: ERRANT tags parts of speech more accurately in a sentence than in a fragment. Use `--dry-run` to preview, `--type` to override the label, and `--corrected ""` for a pure deletion. ERRANT only covers English, so other languages (`--lang sv`) need `--type`.

**Log many at once.** One partial entry per line (`original`, `corrected`, `cause`, plus optional `context`, `note`, `source`, `date`). The rest is filled in, and nothing is written unless every line is valid.

```bash
uv run scripts/errata.py import batch.jsonl --source chat --date 2026-11-15
```

**Look up a type without logging.**

```bash
uv run scripts/errata.py classify "depends of" "depends on"
# R:PREP
#   R:PREP         'of' → 'on'
```

**See your progress.** Top causes and error types, a trend table, and mistakes you have logged more than once.

```bash
uv run scripts/errata.py stats                        # weekly trend by cause
uv run scripts/errata.py stats --by month --group type
uv run scripts/errata.py stats --since 2026-12-01 --json   # for charts or other tools
```

```
Trend by week (cause, % of that period's mistakes)
  period      n  SLIP  CALQUE  UNNATURAL  (rest)
  2026-W46   20   30%     20%        15%     35%
  2026-W47    6   17%     50%         0%     33%

Repeated mistakes
  2×  'count with me' → 'count on me'
```

The trend shows **shares, not raw counts**: how much you write changes from week to week, so a falling share is the real sign that a kind of mistake is going away. Options: `--by week|month`, `--group cause|type|full`, `--top N`, `--since/--until YYYY-MM-DD`, `--lang en|sv|all`.

**Audit the log.** Re-classifies every English entry and lists labels that differ from ERRANT (`--strict` exits 1 on any difference, for CI).

```bash
uv run scripts/errata.py check
```

**Validate the format.**

```bash
uv run scripts/validate.py            # defaults to data/log.jsonl
```

Every line must pass the `Entry` model, ids must be unique, and both `schema/entry.schema.yaml` and the labels in `taxonomy.yaml` must match the models. Besides the field types, the model checks that `original` appears verbatim in `context`, that the date in `id` equals `date`, and that `VARIETY_MIX` entries set `variety`.

**Change the format.** Edit `scripts/l2_errata/models.py` (and `taxonomy.yaml` for a new label), then regenerate the schema:

```bash
uv run scripts/errata.py schema
```

When a span contains several edits of different types, `errata.py` labels it `R:OTHER` and prints each edit; splitting it into one entry per edit gives cleaner stats.

## Skill

[`skills/l2-errata/SKILL.md`](skills/l2-errata/SKILL.md) teaches an AI agent the whole loop: correct the text, explain each fix (naming the Spanish source of carry-overs), turn each mistake into an entry, run `import`, commit, and point out repeated mistakes. It is plain Markdown in the Agent Skills format, so any agent that can read a file and run a shell can follow it; without a shell, the agent hands back the batch as JSONL to import later.

## Roadmap

- [x] Taxonomy, schema, seed log
- [x] Auto-fill `errant_type` from `original` → `corrected` with ERRANT
- [x] Stats: top types and causes per week/month, repeated mistakes, JSON output
- [x] Skill: proofread text and append entries to the log ([`skills/l2-errata/SKILL.md`](skills/l2-errata/SKILL.md))
- [ ] Licensing decision before any public release

## Citation

Bryant, C., Felice, M., & Briscoe, T. (2017). Automatic Annotation and Evaluation of Error Types for Grammatical Error Correction. *Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*, 793–805. https://doi.org/10.18653/v1/P17-1074 · Code: https://github.com/chrisjbryant/errant
