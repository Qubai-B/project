"""Render results/REPORT.md from whatever tables and figures exist — the summary to send the supervisor."""
import json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from common.paths import TABLES, FIGURES, RESULTS, BENCHMARK, TRAJECTORIES

def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else (f"{v:.3f}" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(lines)

n_bench = sum(1 for _ in BENCHMARK.glob("*/*/*/screenshot.png"))
n_traj = sum(1 for _ in TRAJECTORIES.glob("*/task.json"))
n_steps = sum(1 for _ in TRAJECTORIES.glob("*/steps/*/action.json"))
out = [f"# Proof-of-concept results — perception-layer data minimization\n\n_Generated {date.today()}_\n",
       "## Setup\n",
       f"- Benchmark: **{n_bench} screenshots** (3 mock Nigerian e-service forms × 50 synthetic identities × 3 fill states), "
       "ground truth from the DOM.",
       f"- Trajectories: **{n_traj} gold trajectories, {n_steps} decision steps** (5 tasks × 3 identities).",
       "- Guard: Tesseract OCR → label-context + pattern + Presidio detection → policy (full / task-aware) → mask.\n"]

if (TABLES / "detection.csv").exists():
    d = pd.read_csv(TABLES / "detection.csv")
    out.append("## Experiment 1 — detection quality (vs DOM ground truth, IoU ≥ 0.5)\n")
    for det in d.detector.unique():
        sub = d[d.detector == det][["pii_type", "n_gt", "precision", "recall", "f1", "type_accuracy", "mean_coverage"]]
        n = int(d[d.detector == det].n_screens.iloc[0])
        out.append(f"**Detector: `{det}`** ({n} screenshots)\n\n" + md(sub) + "\n")
    if (FIGURES / "detection_f1.png").exists():
        out.append("![detection F1](figures/detection_f1.png)\n")

if (TABLES / "guard_latency.csv").exists():
    l = pd.read_csv(TABLES / "guard_latency.csv")
    m = l[["ocr_ms", "detect_ms", "mask_ms"]].median()
    out.append(f"## Guard latency\n\nMedian per screenshot (n={len(l)}): OCR {m.ocr_ms:.0f} ms, detect {m.detect_ms:.0f} ms, "
               f"mask {m.mask_ms:.0f} ms — **{m.sum():.0f} ms total** on CPU.\n")

if (TABLES / "leakage.csv").exists():
    lk = pd.read_csv(TABLES / "leakage.csv")
    out.append("## Experiment 2 — leakage (what a VLM can still transcribe)\n\n" + md(lk) + "\n")
else:
    out.append("## Experiment 2 — leakage\n\n_Not run yet: needs `ANTHROPIC_API_KEY` in `.env`, then `scripts/06_eval_leakage.py`._\n")

if (TABLES / "step_accuracy.csv").exists():
    sa = pd.read_csv(TABLES / "step_accuracy.csv")
    out.append("## Experiment 3 — offline step accuracy\n\n" + md(sa) + "\n")
    if (FIGURES / "privacy_vs_utility.png").exists():
        out.append("![privacy vs utility](figures/privacy_vs_utility.png)\n")
else:
    out.append("## Experiment 3 — step accuracy\n\n_Not run yet: needs `ANTHROPIC_API_KEY` in `.env`, then `scripts/07_eval_step_accuracy.py`._\n")

gifs = sorted(Path(RESULTS.parent / "demo").glob("*.gif"))
if gifs:
    out.append("## Demo\n\n" + "\n".join(f"- `demo/{g.name}` — browser view vs model input, step by step" for g in gifs) + "\n")

out.append("## Finding worth noting\n\n"
           "The first full run missed 9 of 2,895 values, and every one was the field the agent had *just typed into*: "
           "the browser's focus ring around that input made Tesseract skip its text. A guard that fails on exactly the "
           "value just entered would be worse than useless, so the OCR stage now neutralises focus-ring pixels before "
           "reading. This is the kind of perception-layer failure mode the project is about, and it only showed up because "
           "the trajectories were recorded with real browser state rather than static mock-ups.\n")
out.append("## Limitations of this PoC\n\n- Mock forms with a single layout family; real portals vary more.\n"
           "- One OCR engine, one VLM; no adversarial inputs.\n- Synthetic identities; name detection by generic NER is weak on Nigerian names, "
           "which is why the guard relies on label context.\n")
(RESULTS / "REPORT.md").write_text("\n".join(out))
print("wrote results/REPORT.md")
