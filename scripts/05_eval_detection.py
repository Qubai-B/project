"""Experiment 1 — detection quality of the guard vs DOM ground truth.

Matching: a detection matches a ground-truth PII box if IoU ≥ 0.5 (type-agnostic box match);
a *typed* match additionally requires the same pii_type. Coverage = fraction of each GT text box
area painted over under the `full` policy (what actually matters for leakage).

in:  data/**/annotations.json, results/redacted/**/guard.json  [guard.presidio.json for the baseline]
out: results/tables/detection.csv           per detector × pii_type (+ ALL)
     results/tables/detection_samples.csv   per screenshot
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.paths import DATA, REDACTED, TABLES
from common.metrics import iou, coverage
from guard.mask import PAD

IOU_T = 0.5
rows_type = []
rows_sample = []
for detector, fname in (("hybrid", "guard.json"), ("presidio", "guard.presidio.json")):
    agg = defaultdict(lambda: {"tp": 0, "tp_typed": 0, "fp": 0, "fn": 0, "cov": [], "n": 0})
    files = sorted(REDACTED.glob(f"**/{fname}"))
    if not files:
        continue
    for gpath in files:
        rel = gpath.parent.relative_to(REDACTED)
        ann = json.loads((DATA / rel / "annotations.json").read_text())
        dets = json.loads(gpath.read_text())["detections"]
        used = set()
        s_tp = s_tpt = 0
        for g in ann["pii"]:
            a = agg[g["pii_type"]]; a["n"] += 1
            best, best_i = 0.0, None
            for i, d in enumerate(dets):
                if i in used:
                    continue
                v = iou(g["bbox"], d["bbox"])
                if v > best:
                    best, best_i = v, i
            if best >= IOU_T:
                used.add(best_i); a["tp"] += 1; s_tp += 1
                if dets[best_i]["pii_type"] == g["pii_type"]:
                    a["tp_typed"] += 1; s_tpt += 1
            else:
                a["fn"] += 1
            a["cov"].append(coverage(g["bbox"], [d["bbox"] for d in dets], pad=PAD))
        for i, d in enumerate(dets):
            if i not in used:
                agg[d["pii_type"]]["fp"] += 1
        rows_sample.append({"detector": detector, "path": str(rel), "n_gt": len(ann["pii"]), "n_det": len(dets),
                            "tp": s_tp, "tp_typed": s_tpt, "fp": len(dets) - len(used), "fn": len(ann["pii"]) - s_tp})
    tot = {"tp": 0, "tp_typed": 0, "fp": 0, "fn": 0, "cov": [], "n": 0}
    for t, a in sorted(agg.items()):
        for k in ("tp", "tp_typed", "fp", "fn", "n"):
            tot[k] += a[k]
        tot["cov"] += a["cov"]
    for t, a in list(sorted(agg.items())) + [("ALL", tot)]:
        p = a["tp"] / (a["tp"] + a["fp"]) if a["tp"] + a["fp"] else 0.0
        r = a["tp"] / (a["tp"] + a["fn"]) if a["tp"] + a["fn"] else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        rows_type.append({"detector": detector, "pii_type": t, "n_gt": a["n"], "tp": a["tp"], "fp": a["fp"], "fn": a["fn"],
                          "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
                          "type_accuracy": round(a["tp_typed"] / a["tp"], 3) if a["tp"] else None,
                          "mean_coverage": round(sum(a["cov"]) / len(a["cov"]), 3) if a["cov"] else None,
                          "n_screens": len(files)})

TABLES.mkdir(parents=True, exist_ok=True)
for name, rows in (("detection.csv", rows_type), ("detection_samples.csv", rows_sample)):
    with open(TABLES / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"{'detector':9} {'pii_type':13} {'n':>5} {'P':>6} {'R':>6} {'F1':>6} {'typeAcc':>8} {'cover':>6}")
for r in rows_type:
    print(f"{r['detector']:9} {r['pii_type']:13} {r['n_gt']:5} {r['precision']:6.3f} {r['recall']:6.3f} {r['f1']:6.3f} "
          f"{str(r['type_accuracy']):>8} {str(r['mean_coverage']):>6}")
