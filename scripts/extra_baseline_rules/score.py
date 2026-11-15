"""Baseline sensitivity run, part 2: score the stored Presidio results under several counting rules.

usage: python -I score.py <project root> <output dir>

Rules (a run is a detection if ...):
  A  the highest-scoring entity scores >= 0.4 and is one of the eight mapped types   (the rule in the thesis)
  B  any entity scores >= 0.4, whatever its type
  C  Presidio reports any entity at all, whatever its score or type                  (mask everything flagged)
The matching is that of scripts/05_eval_detection.py: IoU >= 0.5, each detection used once.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
MAP = {"PERSON": "PERSON", "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE", "DATE_TIME": "DOB",
       "LOCATION": "ADDRESS", "IBAN_CODE": "BANK_ACCOUNT", "CREDIT_CARD": "FINANCIAL", "US_PASSPORT": "PASSPORT"}


def iou(a, b):
    ix = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def rule_a(ents):
    res = [e for e in ents if e["score"] >= 0.4]
    if not res:
        return None
    return MAP.get(max(res, key=lambda e: e["score"])["type"])


def rule_b(ents):
    res = [e for e in ents if e["score"] >= 0.4]
    if not res:
        return None
    mapped = [e for e in res if e["type"] in MAP]
    return MAP[max(mapped, key=lambda e: e["score"])["type"]] if mapped else "OTHER"


def rule_c(ents):
    if not ents:
        return None
    mapped = [e for e in ents if e["type"] in MAP]
    return MAP[max(mapped, key=lambda e: e["score"])["type"]] if mapped else "OTHER"


RULES = {"A": rule_a, "B": rule_b, "C": rule_c}
files = sorted((OUT / "raw").glob("*.json"))
agg = {k: defaultdict(lambda: {"n": 0, "tp": 0, "typed": 0, "fn": 0}) for k in RULES}
fp = {k: defaultdict(int) for k in RULES}            # false positives by the text of the run
fp_empty = {k: 0 for k in RULES}                     # false positives on screenshots with no personal data
raw_types = defaultdict(lambda: defaultdict(int))    # annotated type -> Presidio's top entity type (rule C), for found values
n_runs = 0
for f in files:
    rec = json.loads(f.read_text(encoding="utf-8"))
    ann = json.loads((ROOT / "data" / rec["path"] / "annotations.json").read_text())
    n_runs += len(rec["runs"])
    for k, rule in RULES.items():
        dets = [{"bbox": r["bbox"], "pii_type": t, "text": r["text"], "ents": r["entities"]}
                for r in rec["runs"] for t in [rule(r["entities"])] if t]
        used = set()
        for g in ann["pii"]:
            a = agg[k][g["pii_type"]]; a["n"] += 1
            best, best_i = 0.0, None
            for i, d in enumerate(dets):
                if i in used:
                    continue
                v = iou(g["bbox"], d["bbox"])
                if v > best:
                    best, best_i = v, i
            if best >= 0.5:
                used.add(best_i); a["tp"] += 1
                a["typed"] += dets[best_i]["pii_type"] == g["pii_type"]
                if k == "C":
                    top = max(dets[best_i]["ents"], key=lambda e: e["score"])
                    raw_types[g["pii_type"]][f'{top["type"]} ({top["score"]:.2f})'] += 1
            else:
                a["fn"] += 1
        for i, d in enumerate(dets):
            if i not in used:
                fp[k][d["text"]] += 1
                fp_empty[k] += not ann["pii"]

print(f"screenshots={len(files)} runs={n_runs}")
rows = []
for k in RULES:
    tot = {x: sum(a[x] for a in agg[k].values()) for x in ("n", "tp", "typed", "fn")}
    nfp = sum(fp[k].values())
    p = tot["tp"] / (tot["tp"] + nfp); r = tot["tp"] / tot["n"]
    print(f"\nRULE {k}: values={tot['n']} found={tot['tp']} missed={tot['fn']} false_pos={nfp} (on empty forms {fp_empty[k]}) "
          f"precision={p:.3f} recall={r:.3f} f1={2 * p * r / (p + r):.3f} type_acc={tot['typed'] / tot['tp']:.3f}")
    for t, a in sorted(agg[k].items(), key=lambda kv: -kv[1]["tp"] / kv[1]["n"]):
        print(f"   {t:13} n={a['n']:4} recall={a['tp'] / a['n']:.3f} type_acc={(a['typed'] / a['tp']) if a['tp'] else 0:.3f}")
        rows.append({"rule": k, "pii_type": t, "n": a["n"], "found": a["tp"], "missed": a["fn"],
                     "recall": round(a["tp"] / a["n"], 3), "type_accuracy": round(a["typed"] / a["tp"], 3) if a["tp"] else ""})
    rows.append({"rule": k, "pii_type": "ALL", "n": tot["n"], "found": tot["tp"], "missed": tot["fn"],
                 "recall": round(r, 3), "type_accuracy": round(tot["typed"] / tot["tp"], 3),
                 "false_positives": nfp, "precision": round(p, 3), "f1": round(2 * p * r / (p + r), 3)})
    print("   false positives by text:", sorted(fp[k].items(), key=lambda kv: -kv[1])[:12])

print("\nRULE C, what Presidio called the values it flagged (annotated type -> top entity):")
for t, d in sorted(raw_types.items()):
    print(f"   {t:13}", sorted(d.items(), key=lambda kv: -kv[1])[:5])

with open(OUT / "baseline_counting_rules.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["rule", "pii_type", "n", "found", "missed", "recall", "type_accuracy",
                                       "false_positives", "precision", "f1"])
    w.writeheader(); w.writerows(rows)
