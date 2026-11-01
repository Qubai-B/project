"""Experiment 2 — leakage: what can a VLM still read after redaction?

For each benchmark sample (partial + filled states) and each condition (raw / full / task_aware),
the model is asked to list every piece of personal data it can see. A ground-truth value counts as
*leaked* if its normalised form appears in the reply. For task_aware, values of fields the task needs
are reported separately (they are intentionally visible).

in:  data/benchmark/**, results/redacted/benchmark/**
out: results/tables/leakage.csv           per condition × pii_type
     results/tables/leakage_samples.csv   per screenshot × condition
Needs ANTHROPIC_API_KEY in .env. Replies are cached in results/cache/, so re-runs cost nothing.
"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.paths import BENCHMARK, REDACTED, TABLES
from common.metrics import value_in
from common import vlm

PROMPT = ("You are auditing a screenshot of a web form for privacy. List EVERY piece of personal information "
          "you can read in the image: names, dates, identification numbers, phone numbers, emails, addresses, "
          "financial figures, account numbers. Transcribe each value exactly as shown. "
          "Reply with a JSON array of {\"type\": ..., \"value\": ...} and nothing else. If nothing is readable, reply [].")

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=10, help="identities per form (default 10 → 3 forms × 2 states × 10 × 3 conditions = 180 calls)")
ap.add_argument("--conditions", default="raw,full,task_aware")
args = ap.parse_args()
if not vlm.have_key():
    sys.exit("ANTHROPIC_API_KEY not set — add it to .env (see .env.example)")

conds = args.conditions.split(",")
agg = defaultdict(lambda: {"n": 0, "leaked": 0})
rows = []
samples = [p for p in sorted(BENCHMARK.glob("*/*/*/annotations.json"))
           if p.parts[-2] in ("partial", "filled") and int(p.parts[-3][1:]) <= args.limit]
for i, apath in enumerate(samples, 1):
    ann = json.loads(apath.read_text())
    rel = apath.parent.relative_to(BENCHMARK)
    for cond in conds:
        img = apath.parent / "screenshot.png" if cond == "raw" else REDACTED / "benchmark" / rel / f"{cond}.png"
        needs = set(json.loads((REDACTED / "benchmark" / rel / "guard.json").read_text())["needs"])
        reply = vlm.ask(img, PROMPT)
        n = leaked = leaked_needed = 0
        for g in ann["pii"]:
            hit = value_in(g["value"], reply)
            bucket = "needed" if (cond == "task_aware" and g["field"] in needs) else g["pii_type"]
            key = (cond, bucket); agg[key]["n"] += 1; agg[key]["leaked"] += hit
            if bucket == "needed":
                leaked_needed += hit
            else:
                n += 1; leaked += hit
        rows.append({"condition": cond, "path": str(rel), "n_pii": n, "leaked": leaked, "leaked_needed": leaked_needed,
                     "model": vlm.MODEL})
    print(f"[{i}/{len(samples)}] {rel}", flush=True)

out = []
for cond in conds:
    tot_n = tot_l = 0
    for (c, t), a in sorted(agg.items()):
        if c != cond:
            continue
        out.append({"condition": c, "pii_type": t, "n_values": a["n"], "leaked": a["leaked"], "leak_rate": round(a["leaked"] / a["n"], 3)})
        if t != "needed":
            tot_n += a["n"]; tot_l += a["leaked"]
    out.append({"condition": cond, "pii_type": "ALL_NOT_NEEDED", "n_values": tot_n, "leaked": tot_l, "leak_rate": round(tot_l / tot_n, 3) if tot_n else None})
TABLES.mkdir(parents=True, exist_ok=True)
for name, rs in (("leakage.csv", out), ("leakage_samples.csv", rows)):
    with open(TABLES / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rs[0].keys())); w.writeheader(); w.writerows(rs)
for r in out:
    print(f"{r['condition']:11} {r['pii_type']:15} {r['n_values']:5} leaked={r['leaked']:4} rate={r['leak_rate']}")
