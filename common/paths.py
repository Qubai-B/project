from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMS = ROOT / "forms"
DATA = ROOT / "data"
IDENTITIES = DATA / "identities" / "identities.jsonl"
BENCHMARK = DATA / "benchmark"
TRAJECTORIES = DATA / "trajectories"
RESULTS = ROOT / "results"
REDACTED = RESULTS / "redacted"
TABLES = RESULTS / "tables"
FIGURES = RESULTS / "figures"
CACHE = RESULTS / "cache"
