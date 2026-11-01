"""Playwright helpers shared by the benchmark renderer and the trajectory recorder."""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import Page
from .forms import FIELD_PII_TYPE

VIEWPORT = {"width": 1280, "height": 1000}

# Tight box around the *text* inside an input (not the whole box), measured with the input's own font.
_MEASURE_JS = """
(selectors) => selectors.map(sel => {
  const el = document.querySelector(sel);
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  const c = document.createElement('canvas').getContext('2d');
  c.font = cs.font;
  const w = c.measureText(el.value).width;
  const bl = parseFloat(cs.borderLeftWidth), bt = parseFloat(cs.borderTopWidth), bb = parseFloat(cs.borderBottomWidth);
  const pl = parseFloat(cs.paddingLeft), pt = parseFloat(cs.paddingTop), pb = parseFloat(cs.paddingBottom);
  return {
    value: el.value,
    input_bbox: {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height},
    bbox: {x: r.left + scrollX + bl + pl, y: r.top + scrollY + bt + pt, w: Math.min(w, r.width - bl - pl), h: r.height - bt - bb - pt - pb},
  };
})
"""


def snapshot(page: Page, out_dir: Path, manifest: dict, meta: dict, needed: set[str] = frozenset()) -> dict:
    """Write page.html, screenshot.png and annotations.json for the page's current state."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # Mirror typed values into the value attribute so the saved HTML reproduces what was on screen.
    page.evaluate("() => document.querySelectorAll('input').forEach(i => i.setAttribute('value', i.value))")
    (out_dir / "page.html").write_text(page.content())
    page.screenshot(path=str(out_dir / "screenshot.png"), full_page=True)
    fields = manifest["fields"]
    boxes = page.evaluate(_MEASURE_JS, [f["selector"] for f in fields])
    pii = []
    for f, b in zip(fields, boxes):
        if not b["value"]:
            continue
        pii.append({
            "field": f["name"], "pii_type": FIELD_PII_TYPE[f["name"]], "value": b["value"],
            "bbox": {k: round(v, 1) for k, v in b["bbox"].items()},
            "input_bbox": {k: round(v, 1) for k, v in b["input_bbox"].items()},
            "needed": f["name"] in needed, "visible": True,
        })
    size = page.evaluate("() => ({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})")
    ann = {
        "source_html": "page.html", "screenshot": "screenshot.png",
        "viewport": {"width": size["w"], "height": size["h"], "device_scale_factor": 1},
        **meta, "pii": pii,
    }
    (out_dir / "annotations.json").write_text(json.dumps(ann, indent=2))
    return ann


def set_field(page: Page, selector: str, value: str) -> None:
    page.fill(selector, value)
    page.eval_on_selector(selector, "(el, v) => el.setAttribute('value', v)", value)
