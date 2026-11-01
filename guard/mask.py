"""Paint opaque boxes over selected regions. The public entry point of the guard."""
from __future__ import annotations
import time
from PIL import Image, ImageDraw
from .ocr import ocr_runs
from .detect import detect
from .policy import select

PAD = 4


def paint(image: Image.Image, boxes: list[dict]) -> Image.Image:
    out = image.convert("RGB").copy()
    dr = ImageDraw.Draw(out)
    for b in boxes:
        bb = b["bbox"]
        dr.rectangle([bb["x"] - PAD, bb["y"] - PAD, bb["x"] + bb["w"] + PAD, bb["y"] + bb["h"] + PAD], fill="black")
    return out


def redact(image: Image.Image, mode: str = "full", needs: set[str] | None = None, detector: str = "hybrid"):
    """Returns (redacted_image, detections, masked, timings_ms)."""
    t0 = time.perf_counter()
    runs = ocr_runs(image)
    t1 = time.perf_counter()
    dets = detect(runs, detector)
    t2 = time.perf_counter()
    masked = select(dets, mode, needs)
    img = paint(image, masked)
    t3 = time.perf_counter()
    return img, dets, masked, {"ocr_ms": (t1 - t0) * 1e3, "detect_ms": (t2 - t1) * 1e3, "mask_ms": (t3 - t2) * 1e3}
