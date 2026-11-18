# l2-errata shortcuts. Run `just` to list them.
# Extra flags pass through, e.g. `just stats --since 2026-11-01`.

set positional-arguments
set shell := ["bash", "-c"]

errata := "uv run scripts/errata.py"

# List recipes
default:
    @just --list --unsorted

# Install dependencies (first time, or after pulling)
setup:
    uv sync

# ERRANT type for a pair: just classify "depends of" "depends on" [--context "..."]
classify original corrected *flags:
    @{{errata}} classify "$@"

# Log one mistake: just add "I am agree" "I agree" CALQUE --context "I am agree with you." --note "..."
add original corrected cause *flags:
    @{{errata}} add --original "$1" --corrected "$2" --cause "$3" "${@:4}"

# Log a JSONL batch: just import batch.jsonl --source chat
import file *flags:
    @{{errata}} import "$@"

# Weekly stats (add --by month, --group type, --since YYYY-MM-DD, --lang all…)
stats *flags:
    @{{errata}} stats "$@"

# Monthly stats
monthly *flags:
    @{{errata}} stats --by month "$@"

# Validate the log, schema and taxonomy
validate *flags:
    @uv run scripts/validate.py "$@"

# Compare logged labels with what ERRANT says now
check *flags:
    @{{errata}} check "$@"

# Regenerate schema/entry.schema.yaml after editing the models
schema:
    @{{errata}} schema
