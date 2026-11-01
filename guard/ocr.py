"""Tesseract OCR → text runs.

A *run* is a horizontal group of words on one line with no large gap between them, so a form row
like  "Surname        Okafor"  becomes two runs: the label and the value. Boxes are in screenshot pixels.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pytesseract
from PIL import Image

UPSCALE = 2          # Tesseract is noticeably more accurate on 2× images for 15px UI text
PSM = 3              # full automatic layout; sparse modes (11/12) skipped text inside a focus-ringed input
GAP_FACTOR = 1.5     # split a line into runs where the horizontal gap exceeds this × line height
MIN_CONF = 0         # fail-safe: a low-confidence word is still masked; a missed value costs more than an extra box


def neutralise_focus_ring(image: Image.Image) -> Image.Image:
    """Paint Chromium's blue focus ring (≈ rgb(0,95,204)) white. Tesseract's layout analysis otherwise
    skips the text inside a ringed input — and the ringed input is exactly the one the agent just typed into."""
    x = np.asarray(image.convert("RGB")).copy()
    r, g, b = x[:, :, 0].astype(int), x[:, :, 1].astype(int), x[:, :, 2].astype(int)
    x[(b > 140) & (r < 120) & (b - g > 40)] = 255
    return Image.fromarray(x)


@dataclass
class Run:
    text: str
    x: float
    y: float
    w: float
    h: float
    words: list = field(default_factory=list)

    @property
    def x2(self): return self.x + self.w
    @property
    def y2(self): return self.y + self.h
    def bbox(self): return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


def ocr_runs(image: Image.Image) -> list[Run]:
    big = neutralise_focus_ring(image).convert("L").resize((image.width * UPSCALE, image.height * UPSCALE), Image.LANCZOS)
    d = pytesseract.image_to_data(big, output_type=pytesseract.Output.DICT, config=f"--psm {PSM}")
    lines: dict[tuple, list[dict]] = {}
    for i, txt in enumerate(d["text"]):
        txt = txt.strip()
        if not txt or float(d["conf"][i]) < MIN_CONF or set(txt) <= set("|[]"):
            continue  # drop empty tokens and input-border artefacts that Tesseract reads as "|"
        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        lines.setdefault(key, []).append({
            "text": txt, "x": d["left"][i] / UPSCALE, "y": d["top"][i] / UPSCALE,
            "w": d["width"][i] / UPSCALE, "h": d["height"][i] / UPSCALE,
        })
    runs: list[Run] = []
    for words in lines.values():
        words.sort(key=lambda w: w["x"])
        cur = [words[0]]
        for w in words[1:]:
            prev = cur[-1]
            line_h = max(x["h"] for x in cur)
            if w["x"] - (prev["x"] + prev["w"]) > GAP_FACTOR * line_h:
                runs.append(_make(cur)); cur = [w]
            else:
                cur.append(w)
        runs.append(_make(cur))
    runs.sort(key=lambda r: (r.y, r.x))
    return runs


def _make(words: list[dict]) -> Run:
    x = min(w["x"] for w in words); y = min(w["y"] for w in words)
    x2 = max(w["x"] + w["w"] for w in words); y2 = max(w["y"] + w["h"] for w in words)
    return Run(" ".join(w["text"] for w in words), x, y, x2 - x, y2 - y, words)
