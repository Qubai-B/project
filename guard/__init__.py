"""Visual redaction guard: screenshot in, redacted screenshot out.

    from guard import redact
    img, detections, masked, timings = redact(Image.open("screenshot.png"), mode="task_aware", needs={"lga", "state"})

Pipeline:  ocr.py  →  detect.py  →  policy.py  →  mask.py
           runs       PII dets      keep/mask     painted PNG
"""
from .mask import redact, paint  # noqa: F401
