"""Baseline sensitivity run, part 1: keep everything Presidio reports for every OCR run of every screenshot.

usage: python run_raw.py <project root> <output dir>

Nothing under the project is written. For each screenshot one JSON file is saved in the output dir with
every run (text, box) and every entity Presidio reports for it at a score cut-off of 0. A screenshot that
already has its file is skipped, so the run can be restarted.
"""
import json
import sys
import time
from pathlib import Path

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402
from common.paths import DATA, BENCHMARK, TRAJECTORIES  # noqa: E402
from guard.ocr import ocr_runs  # noqa: E402
from guard.detect import _presidio  # noqa: E402

samples = sorted(BENCHMARK.glob("*/*/*/screenshot.png")) + sorted(TRAJECTORIES.glob("*/steps/*/screenshot.png"))
OUT.mkdir(parents=True, exist_ok=True)
log = open(OUT / "progress.log", "a", encoding="utf-8")
print(f"start {time.strftime('%H:%M:%S')} screenshots={len(samples)}", file=log, flush=True)
analyzer = _presidio()
for i, p in enumerate(samples, 1):
    rel = p.parent.relative_to(DATA)
    dest = OUT / "raw" / (str(rel).replace("\\", "__").replace("/", "__") + ".json")
    if not dest.exists():
        runs = ocr_runs(Image.open(p))
        rec = {"path": rel.as_posix(), "runs": []}
        for run in runs:
            res = analyzer.analyze(text=run.text, language="en", score_threshold=0.0)
            rec["runs"].append({"text": run.text, "bbox": run.bbox(),
                                "entities": [{"type": r.entity_type, "score": r.score} for r in res]})
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec), encoding="utf-8")
        tmp.replace(dest)
    if i % 25 == 0 or i == len(samples):
        print(f"[{i}/{len(samples)}] {time.strftime('%H:%M:%S')} {rel}", file=log, flush=True)
print(f"done {time.strftime('%H:%M:%S')}", file=log, flush=True)
