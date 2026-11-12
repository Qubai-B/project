"""Figures from the result tables. Draws whatever tables exist.

out: results/figures/detection_f1.png          Exp. 1 — F1 per PII type, hybrid vs presidio baseline
     results/figures/privacy_vs_utility.png    Exp. 2 + 3 — leak rate vs step accuracy per condition
     results/figures/guard_latency.png         OCR / detect / mask time per screenshot
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common.paths import TABLES, FIGURES

FIGURES.mkdir(parents=True, exist_ok=True)
COND_LABEL = {"raw": "No redaction", "full": "Full redaction", "task_aware": "Task-aware redaction"}

if (TABLES / "detection.csv").exists():
    d = pd.read_csv(TABLES / "detection.csv")
    d = d[d.pii_type != "ALL"].pivot(index="pii_type", columns="detector", values="f1").fillna(0)
    ax = d.plot.bar(figsize=(9, 4), width=0.75, color={"hybrid": "#008751", "presidio": "#9aa5a0"})
    ax.set_ylabel("F1 (IoU ≥ 0.5)"); ax.set_xlabel(""); ax.set_ylim(0, 1.05); ax.set_title("Exp. 1 — PII detection by type")
    # Legend beside the plot: most bars reach 1.0, so anywhere inside the axes it covers data.
    ax.legend(title="detector", frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.spines[["top", "right"]].set_visible(False)
    plt.xticks(rotation=35, ha="right"); plt.tight_layout()
    plt.savefig(FIGURES / "detection_f1.png", dpi=160, bbox_inches="tight"); plt.close()
    print("detection_f1.png")

if (TABLES / "leakage.csv").exists() and (TABLES / "step_accuracy.csv").exists():
    lk = pd.read_csv(TABLES / "leakage.csv"); lk = lk[lk.pii_type == "ALL_NOT_NEEDED"].set_index("condition")["leak_rate"]
    sa = pd.read_csv(TABLES / "step_accuracy.csv"); sa = sa[sa.task == "ALL"].set_index("condition")["step_accuracy"]
    fig, ax = plt.subplots(figsize=(6, 5))
    for c in ("raw", "full", "task_aware"):
        if c in lk and c in sa:
            ax.scatter(lk[c] * 100, sa[c] * 100, s=140, color="#008751", zorder=3)
            ax.annotate(COND_LABEL[c], (lk[c] * 100, sa[c] * 100), xytext=(8, 6), textcoords="offset points")
    ax.set_xlabel("PII leaked to the model (% of non-task values recovered)  ← better")
    ax.set_ylabel("Step accuracy (%)  ↑ better"); ax.set_xlim(-5, 105); ax.set_ylim(-5, 105); ax.grid(alpha=.3)
    ax.set_title("Privacy vs utility"); ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout(); plt.savefig(FIGURES / "privacy_vs_utility.png", dpi=160); plt.close()
    print("privacy_vs_utility.png")

if (TABLES / "guard_latency.csv").exists():
    l = pd.read_csv(TABLES / "guard_latency.csv")
    m = l[["ocr_ms", "detect_ms", "mask_ms"]].median()
    ax = m.plot.barh(figsize=(7, 2.6), color="#008751")
    ax.set_xlabel("median ms per screenshot"); ax.set_title(f"Guard latency (n={len(l)}, total median {m.sum():.0f} ms)")
    ax.spines[["top", "right"]].set_visible(False); plt.tight_layout(); plt.savefig(FIGURES / "guard_latency.png", dpi=160); plt.close()
    print("guard_latency.png")
