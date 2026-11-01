# Project log

Chronological record of the steps taken on the proof of concept, from the first reading of
Chapter One to the current day. Each entry says what was done, what came out of it, and where the
result lives in the repository. The technical reasoning behind the decisions is in
`PROJECT_RECORD.md`; the supervisor-facing summary is in `POC.md`.

| Date | Step | Outcome / where it lives |
|---|---|---|
| 2026-10-01 | Read Chapter One (`CHAPTER ONE(Project).docx`) and restated the problem: screenshot-driven agents on government portals send the whole screen, including personal data, to a cloud vision model; the project proposes a visual redaction guard at the perception layer. | Working definition of the five objectives (benchmark, guard, leakage, task impact, middleware). |
| 2026-10-01 | Asked how the project could be tested within an undergraduate scope. | Decision: synthetic identities and self-built mock portals instead of real portals and real data; evaluation on screenshots rather than a full agent. |
| 2026-10-15 | Drew up the proof-of-concept plan to produce results for the supervisor. | Plan: three Nigerian e-service forms, five tasks, benchmark of filled-form screenshots, recorded trajectories, guard with two policies, three experiments, side-by-side demo. |
| 2026-10-15 | Scoping decisions fixed: Nigeria as the context for every use case (housing benefit dropped as not applicable); the browser agent is not built but its use is demonstrated offline. | `POC.md` §3, `PROJECT_RECORD.md` §2. |
| 2026-10-15 | Directory convention agreed: one sample = one folder holding `page.html`, `screenshot.png`, `annotations.json`; redacted outputs mirror the same path. | `README.md` layout section; `data/`, `results/redacted/`. |
| 2026-10-15 | Reproducible environment built: `setup.sh`, `requirements.txt`, `requirements.lock` (78 pins), `.python-version`, `.env.example`. spaCy pinned below 3.8 because only Python 3.9.6 is available. | Verified by rebuilding from a clean copy. |
| 2026-10-15 | Mock portals written: tax self-assessment (12 fields), driver's licence renewal (10), passport application (10), with field manifests and a shared stylesheet. | `forms/`. |
| 2026-10-15 | Synthetic identity generator for Nigerian identifiers (NIN, BVN, TIN, NUBAN account, FRSC licence, NIS passport, +234 phone) and 50 identities generated. | `common/nigeria.py`, `scripts/01_gen_identities.py`, `schemas/pii_formats.md`, `data/identities.json`. |
| 2026-10-15 | Benchmark rendered: 450 screenshots with exact ground-truth boxes measured from the DOM (2,400 annotated PII values). | `scripts/02_render_benchmark.py`, `data/benchmark/`. |
| 2026-10-15 | Trajectories recorded from live browser state: 15 trajectories, 51 decision steps, 495 PII values. | `scripts/03_record_trajectories.py`, `data/trajectories/`. |
| 2026-10-15 | Guard implemented: OCR (Tesseract, 2× upscale) → hybrid detection (form-label context, regex, Presidio NER) → policy (full or task-aware) → mask. Presidio-only baseline added for comparison. | `guard/ocr.py`, `guard/detect.py`, `guard/policy.py`, `guard/mask.py`. |
| 2026-10-15 | First full guard run: F1 0.973. All errors were in trajectory steps just after typing. | Investigation started; see `PROJECT_RECORD.md` §6. |
| 2026-10-15 | Cause found: the browser's blue focus ring on the just-typed input. OCR read the borders as `\|` glyphs and skipped the field. Switched to full-layout OCR and dropped bar-only tokens. | Second run: precision 1.000, recall 0.997 (9 misses, all the focused field). |
| 2026-10-15 | Tried binarising the image to remove borders; real values dropped to OCR confidence 5–26 and were lost. Rejected. Removed the confidence cutoff instead (mask the uncertain). | Fail-safe principle recorded in `PROJECT_RECORD.md`. |
| 2026-10-15 | Added `neutralise_focus_ring` (paints the ring white before OCR). Third full run over 501 screenshots and 2,895 values: precision 1.000, recall 1.000, 0 error screens. | Final configuration; `results/tables/detection.csv`. |
| 2026-10-15 | Presidio baseline evaluated on 30 filled screenshots: F1 0.728, never finds BVN, TIN or income; mislabels NIN, account, licence and passport numbers. | `results/tables/detection.csv`, `results/figures/detection_f1.png`. |
| 2026-10-15 | Latency measured on all 501 screenshots: median 488 ms per screenshot on CPU. | `results/tables/guard_latency.csv`, `results/figures/guard_latency.png`. |
| 2026-10-15 | Experiments 2 (leakage) and 3 (offline step accuracy) written and logic-tested; not run because no vision-model API key is available. | `scripts/06_eval_leakage.py`, `scripts/07_eval_step_accuracy.py`, `common/vlm.py` (replies cached under `results/cache/`). |
| 2026-10-15 | Side-by-side demonstration produced: browser view versus model input for two recorded tasks. | `demo/*.gif`, `demo/side_by_side.py`. |
| 2026-10-15 | Automated report generated. | `scripts/09_report.py` → `results/REPORT.md`. |
| 2026-10-15 | Documentation written: `PROJECT_RECORD.md` (problem, decisions, materials, methodology, results, development log, limitations, conclusion, next steps) and the supervisor progress report, narrated in the first person, exported to PDF. | `PROJECT_RECORD.md`, `POC.md` (then named `POF.md`), `~/Downloads/POC.pdf`. |
| 2026-11-01 | Repository published: first commit of the whole proof of concept pushed to GitHub. | https://github.com/Qubai-B/project (`main`). |
| 2026-11-01 | Documents made location-independent: references to the local folder name replaced by the repository URL and a generic root. | `README.md`, `POC.md`, `PROJECT_RECORD.md`. |
| 2026-11-01 | Progress report renamed from `POF.md` to `POC.md`; PDF regenerated. | `POC.md`, `~/Downloads/POC.pdf`. |
| 2026-11-01 | This log added. | `LOG.md`. |

## Open items as of 2026-11-01

1. Obtain a vision-model API key, then run `./run_all.sh` to complete Experiments 2 and 3, and update `POC.md` §4–5 and `PROJECT_RECORD.md` §5.3.
2. Confirm the four-week plan in `POC.md` §8 against the real submission deadline before sending.
3. Decisions needed from the supervisor are listed in `POC.md` §7 and §10.
