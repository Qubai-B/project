"""Render every form × identity × fill_state and screenshot it with Playwright.

in:  forms/<form_id>/index.html, forms/<form_id>/form.json, data/identities/identities.jsonl
out: data/benchmark/<form_id>/<identity_id>/<fill_state>/{page.html, screenshot.png, annotations.json}
     data/benchmark/manifest.jsonl

Ground-truth boxes come from the DOM (bounding rect + measured text width), so annotations.json
is exact and needs no manual labelling.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from common.paths import IDENTITIES, BENCHMARK
from common.forms import FILL_STATES, list_forms, load_manifest, render, values_for_state
from common.capture import VIEWPORT, snapshot

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=None, help="identities per form (default: all)")
args = ap.parse_args()

identities = [json.loads(l) for l in IDENTITIES.read_text().splitlines() if l.strip()]
if args.limit:
    identities = identities[: args.limit]

manifest_rows = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport=VIEWPORT)
    for form_id in list_forms():
        m = load_manifest(form_id)
        for ident in identities:
            for state in FILL_STATES:
                page.set_content(render(form_id, values_for_state(m, ident, state)))
                out = BENCHMARK / form_id / ident["id"] / state
                ann = snapshot(page, out, m, {"form_id": form_id, "identity_id": ident["id"], "fill_state": state})
                manifest_rows.append({"path": f"{form_id}/{ident['id']}/{state}", "form_id": form_id,
                                      "identity_id": ident["id"], "fill_state": state, "n_pii": len(ann["pii"])})
        print(f"{form_id}: {len(identities) * len(FILL_STATES)} samples")
    browser.close()

(BENCHMARK / "manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in manifest_rows))
print(f"wrote {len(manifest_rows)} samples, manifest -> data/benchmark/manifest.jsonl")
