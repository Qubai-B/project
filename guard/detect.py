"""Classify OCR runs as PII.

Two detectors, selectable so the evaluation can compare them:

  hybrid   (default) — form-aware. A run is a *value* if a field label sits to its left on the same
             row; the label decides the field and therefore the PII type. Pattern rules and Presidio
             fill in anything the label context misses. This is what the guard ships with.
  presidio — generic baseline. Presidio's built-in recognizers only, no form context. Expected to
             miss Nigerian identifiers (NIN, BVN, TIN, NUBAN, licence numbers) — see results.

Returns a list of detections: {pii_type, field, text, bbox, source}.
"""
from __future__ import annotations
import re
from .ocr import Run
from common.forms import field_from_label, FIELD_PII_TYPE

PATTERNS = [  # (pii_type, regex, field) — order = priority
    ("EMAIL",        re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "email"),
    ("PHONE",        re.compile(r"\+?234[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{4}|\b0[789]\d{9}\b"), "phone"),
    ("TIN",          re.compile(r"\b\d{8}-\d{4}\b"), "tin"),
    ("PASSPORT",     re.compile(r"\b[A-C]\d{8}\b"), "passport_no"),
    ("LICENCE_NO",   re.compile(r"\b[A-Z]{3}\d{5}[A-Z]{2}\d{2}\b"), "licence_no"),
    ("DOB",          re.compile(r"\b\d{2}/\d{2}/\d{4}\b"), "date_of_birth"),
    ("NIN",          re.compile(r"\b\d{11}\b"), "nin"),          # NIN and BVN share a shape; label context disambiguates
    ("BANK_ACCOUNT", re.compile(r"\b\d{10}\b"), "bank_account"),
    ("FINANCIAL",    re.compile(r"\b\d{5,9}\b"), "annual_income"),
]

_PRESIDIO_MAP = {"PERSON": "PERSON", "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE", "DATE_TIME": "DOB",
                 "LOCATION": "ADDRESS", "IBAN_CODE": "BANK_ACCOUNT", "CREDIT_CARD": "FINANCIAL", "US_PASSPORT": "PASSPORT"}
_analyzer = None


def _presidio():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        _analyzer = AnalyzerEngine()
    return _analyzer


def _presidio_type(text: str) -> str | None:
    res = _presidio().analyze(text=text, language="en", score_threshold=0.4)
    if not res:
        return None
    best = max(res, key=lambda r: r.score)
    return _PRESIDIO_MAP.get(best.entity_type)


def _pattern(text: str):
    for pii_type, rx, fld in PATTERNS:
        if rx.search(text):
            return pii_type, fld
    return None


def _label_left_of(run: Run, runs: list[Run]) -> Run | None:
    """Nearest run to the left that vertically overlaps `run` and reads as a field label."""
    best = None
    for r in runs:
        if r is run or r.x2 > run.x:
            continue
        overlap = min(r.y2, run.y2) - max(r.y, run.y)
        if overlap < 0.5 * min(r.h, run.h):
            continue
        if field_from_label(r.text) is None:
            continue
        if best is None or r.x2 > best.x2:
            best = r
    return best


def detect(runs: list[Run], detector: str = "hybrid") -> list[dict]:
    out = []
    for run in runs:
        if detector == "presidio":
            t = _presidio_type(run.text)
            if t:
                out.append(_det(run, t, None, "presidio"))
            continue
        # hybrid
        label = _label_left_of(run, runs)
        if label is not None:
            fld = field_from_label(label.text)
            out.append(_det(run, FIELD_PII_TYPE[fld], fld, "label"))
            continue
        if field_from_label(run.text) is not None and not _pattern(run.text):
            continue  # this run *is* a label (or a heading); never mask labels
        hit = _pattern(run.text)
        if hit:
            out.append(_det(run, hit[0], hit[1], "pattern"))
            continue
        t = _presidio_type(run.text)
        if t:
            out.append(_det(run, t, None, "presidio"))
    return out


def _det(run: Run, pii_type: str, fld: str | None, source: str) -> dict:
    return {"pii_type": pii_type, "field": fld, "text": run.text, "bbox": run.bbox(), "source": source}
