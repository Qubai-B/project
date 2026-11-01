"""Replay the gold path for each task in forms/*/form.json and snapshot every step.

in:  forms/**, data/identities/identities.jsonl
out: data/trajectories/<task_id>/task.json
     data/trajectories/<task_id>/steps/<NNN>/{page.html, screenshot.png, annotations.json, action.json}

A trajectory starts with every field *outside* the task already filled (the agent has reached this
section of the form), then types each needed field in fill order, then clicks "Save and Continue".
Step NNN's screenshot is the state *before* action.json is applied.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from common.paths import IDENTITIES, TRAJECTORIES
from common.forms import list_forms, load_manifest, render
from common.capture import VIEWPORT, snapshot, set_field

ap = argparse.ArgumentParser()
ap.add_argument("--identities", type=int, default=3, help="identities per task")
args = ap.parse_args()

identities = [json.loads(l) for l in IDENTITIES.read_text().splitlines() if l.strip()][: args.identities]
n_traj = n_steps = 0
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport=VIEWPORT)
    for form_id in list_forms():
        m = load_manifest(form_id)
        by_name = {f["name"]: f for f in m["fields"]}
        for task_id, task in m["tasks"].items():
            needs = [f["name"] for f in m["fields"] if f["name"] in task["needs"]]  # fill order
            for ident in identities:
                tdir = TRAJECTORIES / f"{task_id}_{form_id}_{ident['id']}"
                values = {f["name"]: ("" if f["name"] in needs else ident[f["identity_key"]]) for f in m["fields"]}
                page.set_content(render(form_id, values))
                meta = {"form_id": form_id, "identity_id": ident["id"], "task_id": task_id}
                actions = [{"action": "type", "target_field": n, "selector": by_name[n]["selector"],
                            "value": ident[by_name[n]["identity_key"]]} for n in needs]
                actions.append({"action": "click", "target_field": "btn_next", "selector": "#btn_next", "value": None})
                for i, act in enumerate(actions):
                    sdir = tdir / "steps" / f"{i:03d}"
                    snapshot(page, sdir, m, {**meta, "step": i}, needed=set(needs))
                    (sdir / "action.json").write_text(json.dumps({"step": i, **act}, indent=2))
                    if act["action"] == "type":
                        set_field(page, act["selector"], act["value"])
                    n_steps += 1
                (tdir / "task.json").write_text(json.dumps({
                    "task_id": tdir.name, "form_id": form_id, "identity_id": ident["id"], "goal": task["goal"],
                    "needs": needs, "values": {n: ident[by_name[n]["identity_key"]] for n in needs},
                    "n_steps": len(actions)}, indent=2))
                n_traj += 1
    browser.close()
print(f"wrote {n_traj} trajectories, {n_steps} steps -> data/trajectories/")
