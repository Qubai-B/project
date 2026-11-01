from __future__ import annotations
import re


def iou(a: dict, b: dict) -> float:
    ix = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def coverage(gt: dict, masks: list[dict], pad: float = 0.0) -> float:
    """Fraction of the ground-truth box area covered by the union of (padded) mask boxes, on a 1px grid."""
    x0, y0 = int(gt["x"]), int(gt["y"]); x1, y1 = int(gt["x"] + gt["w"] + 0.999), int(gt["y"] + gt["h"] + 0.999)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    covered = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            for m in masks:
                if m["x"] - pad <= x < m["x"] + m["w"] + pad and m["y"] - pad <= y < m["y"] + m["h"] + pad:
                    covered += 1; break
    return covered / ((x1 - x0) * (y1 - y0))


def norm(s: str) -> str:
    """Normalise a value for leakage matching: lowercase, strip everything but letters/digits/@."""
    return re.sub(r"[^a-z0-9@]", "", str(s).lower())


def value_in(value: str, text: str) -> bool:
    v = norm(value)
    return len(v) >= 3 and v in norm(text)
