"""Experiment 3 — offline step accuracy: can the agent still pick the right next action?

For every trajectory step and condition (raw / full / task_aware) the model sees the screenshot, the task
goal and the user's data for that task, and must output the next action as JSON. It is scored against
action.json: for `type` steps the field must match (label → field via the shared vocabulary) and the value
must match; for the final `click` step the model must choose to submit.

in:  data/trajectories/**, results/redacted/trajectories/**
out: results/tables/step_accuracy.csv          per condition (+ per task)
     results/tables/step_accuracy_samples.csv  per step × condition
Needs ANTHROPIC_API_KEY in .env. Replies are cached.
"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.paths import TRAJECTORIES, REDACTED, TABLES
from common.forms import field_from_label
from common.metrics import norm
from common import vlm

PROMPT = """You are a web agent filling in a Nigerian government e-service form on behalf of a user.
Some parts of the screenshot may be blacked out for privacy; that is expected.

Task: {goal}
Data the user has given you for this task:
{data}

Look at the screenshot and decide the SINGLE next action. Rules:
- If a field this task needs is still empty or shows a wrong value, type into it. Type the fields in top-to-bottom order.
- Only when every field this task needs already shows the correct value, click "Save and Continue".
- Do not touch fields the task does not mention.

Reply with JSON only: {{"action": "type", "field_label": "<label text next to the field>", "value": "<text to type>"}}
or {{"action": "click", "field_label": "Save and Continue", "value": null}}"""

ap = argparse.ArgumentParser()
ap.add_argument("--conditions", default="raw,full,task_aware")
args = ap.parse_args()
if not vlm.have_key():
    sys.exit("ANTHROPIC_API_KEY not set — add it to .env (see .env.example)")

conds = args.conditions.split(",")
agg = defaultdict(lambda: {"n": 0, "correct": 0, "field_ok": 0})
rows = []
tasks = sorted(TRAJECTORIES.glob("*/task.json"))
for ti, tpath in enumerate(tasks, 1):
    task = json.loads(tpath.read_text())
    data = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in task["values"].items())
    for spath in sorted(tpath.parent.glob("steps/*/action.json")):
        gold = json.loads(spath.read_text())
        rel = spath.parent.relative_to(TRAJECTORIES)
        for cond in conds:
            img = spath.parent / "screenshot.png" if cond == "raw" else REDACTED / "trajectories" / rel / f"{cond}.png"
            reply = vlm.ask(img, PROMPT.format(goal=task["goal"], data=data))
            pred = vlm.extract_json(reply) or {}
            p_action = str(pred.get("action", "")).lower()
            p_field = field_from_label(str(pred.get("field_label", ""))) if p_action == "type" else None
            if gold["action"] == "click":
                field_ok = correct = p_action == "click"
            else:
                field_ok = p_action == "type" and p_field == gold["target_field"]
                correct = field_ok and norm(pred.get("value", "")) == norm(gold["value"])
            for key in (("ALL", cond), (task["task_id"].split("_")[0], cond)):
                agg[key]["n"] += 1; agg[key]["correct"] += correct; agg[key]["field_ok"] += field_ok
            rows.append({"condition": cond, "path": str(rel), "gold_action": gold["action"], "gold_field": gold["target_field"],
                         "pred_action": p_action, "pred_field": p_field, "pred_value": pred.get("value"),
                         "field_ok": int(field_ok), "correct": int(correct), "model": vlm.MODEL})
    print(f"[{ti}/{len(tasks)}] {task['task_id']}", flush=True)

out = [{"task": t, "condition": c, "n_steps": a["n"], "field_accuracy": round(a["field_ok"] / a["n"], 3),
        "step_accuracy": round(a["correct"] / a["n"], 3)} for (t, c), a in sorted(agg.items(), key=lambda kv: (kv[0][0] != "ALL", kv[0]))]
TABLES.mkdir(parents=True, exist_ok=True)
for name, rs in (("step_accuracy.csv", out), ("step_accuracy_samples.csv", rows)):
    with open(TABLES / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rs[0].keys())); w.writeheader(); w.writerows(rs)
for r in out:
    print(f"{r['task']:5} {r['condition']:11} n={r['n_steps']:3} field_acc={r['field_accuracy']:.3f} step_acc={r['step_accuracy']:.3f}")
