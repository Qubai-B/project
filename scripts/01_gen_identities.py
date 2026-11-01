"""Generate N synthetic Nigerian identities (formats in schemas/pii_formats.md).

out: data/identities/identities.jsonl   (schema: schemas/identity.example.json)
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.nigeria import generate
from common.paths import IDENTITIES

ap = argparse.ArgumentParser()
ap.add_argument("-n", type=int, default=50)
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

IDENTITIES.parent.mkdir(parents=True, exist_ok=True)
rows = generate(args.n, args.seed)
IDENTITIES.write_text("".join(json.dumps(r) + "\n" for r in rows))
print(f"wrote {len(rows)} identities -> {IDENTITIES.relative_to(IDENTITIES.parents[2])}")
