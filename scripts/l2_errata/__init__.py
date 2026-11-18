"""l2-errata: log language-learning mistakes, classified with ERRANT."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "data" / "log.jsonl"
SCHEMA_PATH = ROOT / "schema" / "entry.schema.yaml"
TAXONOMY_PATH = ROOT / "taxonomy.yaml"
