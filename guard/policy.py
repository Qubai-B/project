"""Decide which detections to mask.

full:       every detection.
task_aware: every detection except those belonging to a field the current task needs
            (the agent must see those to fill and verify them). Detections with no field
            attribution are always masked — unknown is treated as sensitive.
"""
from __future__ import annotations


def select(detections: list[dict], mode: str, needs: set[str] | None = None) -> list[dict]:
    if mode == "full":
        return list(detections)
    if mode == "task_aware":
        needs = needs or set()
        return [d for d in detections if d.get("field") not in needs]
    raise ValueError(mode)
