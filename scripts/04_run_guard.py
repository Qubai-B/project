"""Run the guard over every screenshot under data/ and save both policies' outputs.

out: results/redacted/<same path as under data/>/{full.png, task_aware.png, guard.json}
     results/tables/guard_latency.csv

guard.json holds the raw detections (pre-policy) and timings; task_aware uses the trajectory's task,
or the form's first task for benchmark samples (recorded in guard.json as task_id/needs).

--detector presidio writes guard.presidio.json only (no images): the generic baseline for Exp. 1.
"""
import argparse, csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
from common.paths import DATA, BENCHMARK, TRAJECTORIES, REDACTED, TABLES
from common.forms import load_manifest
from guard.ocr import ocr_runs
from guard.detect import detect
from guard.policy import select
from guard.mask import paint

ap = argparse.ArgumentParser()
ap.add_argument("--detector", choices=["hybrid", "presidio"], default="hybrid")
ap.add_argument("--only", choices=["benchmark", "trajectories"], default=None)
ap.add_argument("--states", default="empty,partial,filled", help="benchmark fill states to include")
ap.add_argument("--limit", type=int, default=None, help="max benchmark identities per form")
args = ap.parse_args()

manifests = {}
def needs_for(ann):
    m = manifests.setdefault(ann["form_id"], load_manifest(ann["form_id"]))
    if "task_id" in ann:
        return ann["task_id"], set(json.loads((TRAJECTORIES / f"{ann['task_id']}_{ann['form_id']}_{ann['identity_id']}" / "task.json").read_text())["needs"])
    tid, task = next(iter(m["tasks"].items()))
    return tid, set(task["needs"])

samples = []
states = set(args.states.split(","))
if args.only != "trajectories":
    for p in sorted(BENCHMARK.glob("*/*/*/screenshot.png")):
        form, ident, state = p.parts[-4:-1]
        if state in states and (args.limit is None or int(ident[1:]) <= args.limit):
            samples.append(p)
if args.only != "benchmark":
    samples += sorted(TRAJECTORIES.glob("*/steps/*/screenshot.png"))

TABLES.mkdir(parents=True, exist_ok=True)
lat_path = TABLES / f"guard_latency{'' if args.detector == 'hybrid' else '.presidio'}.csv"
with open(lat_path, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["path", "detector", "n_runs", "n_detections", "ocr_ms", "detect_ms", "mask_ms"])
    for i, p in enumerate(samples, 1):
        rel = p.parent.relative_to(DATA)
        out = REDACTED / rel; out.mkdir(parents=True, exist_ok=True)
        ann = json.loads((p.parent / "annotations.json").read_text())
        img = Image.open(p)
        import time; t0 = time.perf_counter()
        runs = ocr_runs(img); t1 = time.perf_counter()
        dets = detect(runs, args.detector); t2 = time.perf_counter()
        task_id, needs = needs_for(ann)
        mask_ms = 0.0
        if args.detector == "hybrid":
            for mode in ("full", "task_aware"):
                t = time.perf_counter()
                paint(img, select(dets, mode, needs)).save(out / f"{mode}.png")
                mask_ms += (time.perf_counter() - t) * 1e3
        rec = {"detector": args.detector, "task_id": task_id, "needs": sorted(needs), "detections": dets,
               "timings_ms": {"ocr": (t1 - t0) * 1e3, "detect": (t2 - t1) * 1e3, "mask": mask_ms}}
        (out / ("guard.json" if args.detector == "hybrid" else "guard.presidio.json")).write_text(json.dumps(rec, indent=1))
        w.writerow([str(rel), args.detector, len(runs), len(dets), round((t1 - t0) * 1e3), round((t2 - t1) * 1e3), round(mask_ms)])
        if i % 25 == 0 or i == len(samples):
            print(f"[{i}/{len(samples)}] {rel}", flush=True)
print(f"done: {len(samples)} screenshots -> results/redacted/, latency -> {lat_path.relative_to(TABLES.parent.parent)}")
