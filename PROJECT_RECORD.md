# Project record — data minimization at the perception layer for screenshot-driven agents

A running record of every decision, method, result and conclusion in this proof of concept, kept in
the order they happened so the methodology and results chapters can be written from it directly.
Numbers are from the run of **15 October 2026**; `results/REPORT.md` regenerates them from the tables.

---

## 1. Problem and starting point

Chapter One of the project proposes a *visual redaction framework* for AI agents that operate on
screenshots of government web portals. Such agents send screenshots to a cloud-hosted
vision-language model (VLM); the screenshots contain personally identifiable information (PII), and
nothing in current governance frameworks addresses this visual channel. The aim is to design,
implement and evaluate a guard that masks sensitive information in a screenshot *before* it leaves
the user's machine, while preserving the agent's ability to complete the task.

Objectives from Chapter One and how this PoC maps to them:

| # | Objective | Realised as |
|---|-----------|-------------|
| 1 | Benchmark dataset of screenshots annotated with PII | `data/benchmark/` — 450 screenshots, DOM-exact boxes |
| 2 | Real-time visual redaction guard | `guard/` package, ~0.5 s per screenshot on CPU |
| 3 | Evaluate reduction of privacy leakage | Experiment 1 (detection) and Experiment 2 (VLM leakage) |
| 4 | Assess impact on agent task completion | Experiment 3 (offline step accuracy) |
| 5 | Integrate into an agent as middleware | `redact()` is a single call on the screenshot path; demonstrated with side-by-side composites |

## 2. Scoping decisions

These were made before any code was written and shape everything below.

1. **Nigerian context.** All forms, identifiers and tasks are Nigerian. Housing benefit (an early
   candidate) was dropped as not applicable. The three services chosen are ones citizens actually use
   online: personal income tax self-assessment (State IRS), driver's licence renewal (FRSC), and
   international passport application (NIS). This brings in identifiers that generic PII tools do not
   know: NIN, BVN, TIN, NUBAN account numbers, Nigerian passport and licence number formats.
2. **No autonomous browser agent is built.** Building and debugging a closed-loop agent is a project in
   itself and its non-determinism would swamp the measurement. Instead the agent is *demonstrated*:
   utility is measured offline on recorded gold trajectories (the model predicts one step at a time,
   as in Mind2Web-style evaluation), and the middleware integration is shown with side-by-side
   composites of browser view versus model input.
3. **Synthetic identities, mock portals.** No real PII is used anywhere, which removes the need for
   ethics approval and lets ground truth come straight from the DOM instead of manual annotation.
   The cost is realism: one layout family, clean rendering. This is stated as a limitation.
4. **Reproducibility first.** A pinned lock file, a one-command `setup.sh`, deterministic seeds and
   on-disk caching of every model reply, so the whole pipeline re-runs identically on another machine.

## 3. Materials

### 3.1 Environment
- macOS, Python 3.9.6 (only interpreter available; spaCy pinned to `<3.8` for that reason).
- Playwright + Chromium for rendering, Tesseract 5.5.2 for OCR, Microsoft Presidio for generic PII
  recognition, Pillow/NumPy for image work, pandas/matplotlib for analysis.
- `requirements.lock` pins 78 packages; `./setup.sh` rebuilds the environment and was verified from a
  clean copy of the repository.

### 3.2 Mock portals (`forms/`)
Three HTML forms styled like Nigerian federal/state e-service pages (green header, plain inputs),
written as Jinja2 templates with one placeholder per field. Each form ships a manifest `form.json`
that declares every field's CSS selector, PII type, source key in the identity record, fill order, and
the tasks defined on that form.

| form_id | fields | tasks |
|---|---|---|
| `tax_self_assessment` | 12 (name, DOB, TIN, NIN, address/LGA/state, income, BVN, NUBAN, email) | T01 address · T02 income + bank details |
| `drivers_licence_renewal` | 10 (licence no, name, DOB, NIN, phone, email, address/LGA/state) | T03 phone + email · T04 licence no + NIN |
| `passport_application` | 10 (name, DOB, NIN, passport no, phone, email, address/LGA/state) | T05 NIN + previous passport no |

Twelve PII types in total: PERSON, DOB, NIN, BVN, TIN, PHONE, EMAIL, ADDRESS, FINANCIAL,
BANK_ACCOUNT, PASSPORT, LICENCE_NO. Formats are in `schemas/pii_formats.md`.

### 3.3 Synthetic identities (`scripts/01_gen_identities.py`)
50 identities, seeded. Names are drawn from Yoruba, Igbo, Hausa and Niger-Delta name lists; addresses
from real street/area names across 12 states with their LGAs; identifiers follow the national formats
(NIN 11 digits, BVN 11 digits starting 22, TIN `8-4`, NUBAN 10 digits, passport `A12345678`, licence
`LAG12345AB67`, phone `+234 8xx xxx xxxx`). Faker supplies dates of birth.

## 4. Methodology

### 4.1 Benchmark construction (`scripts/02_render_benchmark.py`)
Every form × identity × fill state (`empty`, `partial` = first half of fields, `filled`) is rendered in
headless Chromium at 1280 px width and screenshotted full-page. For each field with a value the script
reads the input's bounding rectangle from the DOM and measures the rendered text width with the
input's own font via a canvas, giving a tight box around the *text*, not the whole input. Output per
sample: `page.html` (the exact HTML, stylesheet inlined), `screenshot.png`, `annotations.json`.
A manifest indexes all samples.

Result: 450 screenshots, 2,400 annotated PII values (0 in empty, half the fields in partial, all in filled).

### 4.2 Trajectory recording (`scripts/03_record_trajectories.py`)
For each of the 5 tasks and the first 3 identities, the form is loaded with every field *outside* the
task already filled (the agent has reached this section), then the gold path is replayed: type each
needed field in fill order, then click "Save and Continue". Before each action a snapshot is taken
(same three files plus `action.json`), so each step's screenshot is the state the model would see
when choosing that action. Typed values are mirrored into the HTML `value` attribute so `page.html`
reproduces the screen.

Result: 15 trajectories, 51 decision steps (4+4+3+3+3 per identity), 495 annotated values.

### 4.3 The guard (`guard/`)
Four stages, each a module:

1. **OCR** (`ocr.py`). The screenshot is upscaled 2× and passed to Tesseract in full-layout mode
   (`--psm 3`). Words are grouped into *runs*: words on one line are split wherever the horizontal gap
   exceeds 1.5× the line height, so a form row becomes a label run and a separate value run. Tokens
   consisting only of `|` (input borders read as glyphs) are dropped. No confidence cutoff is applied:
   an uncertain word is still a candidate for masking.
2. **Detection** (`detect.py`), two selectable detectors:
   - **hybrid** — the guard's own method. For each run, look for the nearest run to its left that
     vertically overlaps it and reads as a field label (shared keyword vocabulary in
     `common/forms.py`). If found, the run is a value of that field and inherits the field's PII
     type. This is what distinguishes a NIN from a BVN (both 11 digits). Runs with no label context
     are tested against format patterns (email, +234 phone, TIN, passport, licence, date, 11/10-digit
     numbers, 5–9-digit amounts) and finally Presidio NER. Runs that themselves read as labels or
     headings are never masked.
   - **presidio** — baseline: Presidio's built-in recognizers alone, no form context.
3. **Policy** (`policy.py`). `full` masks every detection. `task_aware` masks every detection except
   those attributed to a field the current task needs; detections with no field attribution are
   always masked (unknown is treated as sensitive).
4. **Mask** (`mask.py`). Opaque black rectangles with 4 px padding.

Public API: `redact(image, mode, needs)` → redacted image, detections, masked boxes, timings.
Inserting that one call between screenshot capture and the model request is the middleware.

### 4.4 Experimental protocol
All 501 screenshots are processed by `scripts/04_run_guard.py`, which stores both policy outputs and
the raw detections per screenshot under `results/redacted/`, mirroring the data paths.

**Experiment 1 — detection quality** (`05_eval_detection.py`). Each ground-truth text box is matched
to the detection with highest IoU; a match at IoU ≥ 0.5 is a true positive, and a *typed* true
positive if the PII type also agrees. Unmatched detections are false positives, unmatched ground
truth are false negatives. Reported per PII type and overall: precision, recall, F1, type accuracy,
and mean *coverage* (fraction of each ground-truth text box painted over under `full`). The hybrid
detector runs on all 501 screenshots; the Presidio baseline on the 30 filled screenshots of the
first 10 identities.

**Experiment 2 — leakage** (`06_eval_leakage.py`). For each partial/filled benchmark sample of the
first 10 identities and each condition (raw, full, task-aware), a VLM is asked to transcribe every
piece of personal data it can read. A ground-truth value counts as leaked if its normalised form
appears in the reply. Under task-aware, values of task-needed fields are reported separately because
they are intentionally visible. 180 calls, replies cached.

**Experiment 3 — offline step accuracy** (`07_eval_step_accuracy.py`). For each of the 51 steps and
each condition, the model sees the screenshot, the task goal and the user's data for the task, and
must output the next action as JSON. Scored against the gold action: for `type` steps the field
(label → field via the shared vocabulary) and the value must match; for the final `click` step the
model must choose to submit. 153 calls, cached. The headline comparison is leakage (Exp. 2) against
step accuracy (Exp. 3) across the three conditions.

**Latency.** OCR, detect and mask times are recorded per screenshot.

## 5. Results

### 5.1 Experiment 1 — detection

Hybrid guard, 501 screenshots, 2,895 ground-truth values:

| PII type | n | precision | recall | F1 | type accuracy | coverage |
|---|---|---|---|---|---|---|
| PERSON | 702 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| ADDRESS | 635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| DOB | 351 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| NIN | 342 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| EMAIL | 195 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| PHONE | 124 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| TIN | 124 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| LICENCE_NO | 115 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| PASSPORT | 103 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| FINANCIAL | 71 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| BVN | 68 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| BANK_ACCOUNT | 65 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| **ALL** | **2,895** | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

Presidio baseline, 30 screenshots, 320 values:

| PII type | n | precision | recall | F1 | type accuracy |
|---|---|---|---|---|---|
| EMAIL | 30 | 1.000 | 1.000 | 1.000 | 1.000 |
| PHONE | 20 | 1.000 | 0.900 | 0.947 | 1.000 |
| DOB | 30 | 0.744 | 0.967 | 0.841 | 1.000 |
| ADDRESS | 90 | 1.000 | 0.633 | 0.776 | 0.579 |
| BANK_ACCOUNT | 10 | 1.000 | 0.600 | 0.750 | 0.000 |
| NIN | 30 | 1.000 | 0.500 | 0.667 | 0.000 |
| PERSON | 60 | 1.000 | 0.500 | 0.667 | 0.900 |
| LICENCE_NO | 10 | 1.000 | 0.300 | 0.462 | 0.000 |
| PASSPORT | 10 | 1.000 | 0.100 | 0.182 | 0.000 |
| BVN | 10 | 0.000 | 0.000 | 0.000 | — |
| TIN | 10 | 0.000 | 0.000 | 0.000 | — |
| FINANCIAL | 10 | 0.000 | 0.000 | 0.000 | — |
| **ALL** | **320** | **0.950** | **0.591** | **0.728** | **0.725** |

Reading: a generic PII detector finds under 60 % of the values on these forms. It never finds a BVN,
TIN or income figure, finds half of NINs and names, and even when it finds a NIN, bank account or
licence number it labels it as something else (type accuracy 0). The form-aware detector finds and
types everything. Figure: `results/figures/detection_f1.png`.

### 5.2 Latency
Median per screenshot over 501 (CPU, no GPU): OCR 447 ms, detect 17 ms, mask 24 ms — **488 ms
total**. The guard adds about half a second per agent step, which is well inside the several seconds
a VLM call already takes.

### 5.3 Experiments 2 and 3
Not yet run: they require a VLM API key, which is not on the development machine. The scripts are
complete and their scoring logic is unit-checked. Once a key is placed in `.env`, `./run_all.sh`
runs both, regenerates `results/figures/privacy_vs_utility.png` and updates `results/REPORT.md`.
This section is to be filled in from `results/tables/leakage.csv` and `step_accuracy.csv`.

### 5.4 Demonstration
`demo/T02_tax_self_assessment_I0001.gif` and `demo/T04_drivers_licence_renewal_I0002.gif` show, for
each step of a trajectory, the browser view beside the image the model receives under the task-aware
policy: the fields the task needs stay readable, everything else is black.

## 6. Development log (what was tried, what changed, and why)

| Date | Event | Consequence |
|---|---|---|
| 2026-10-14 | Latest spaCy no longer supports Python 3.9 | Pinned `spacy<3.8`; recorded in `requirements.lock` |
| 2026-10-15 | First full guard run: F1 0.973, 90 FP / 66 FN, *all* in trajectory steps after typing | Investigated |
| 2026-10-15 | Cause found: the browser's focus ring on the just-typed input. In sparse OCR mode Tesseract read the input borders as `\|` glyphs (gluing onto values and dropping IoU below 0.5) and skipped the ringed field entirely | Switched to full-layout OCR and dropped bar-only tokens |
| 2026-10-15 | Tried binarising the image (threshold 128) to remove borders: borders gone, but real values fell to OCR confidence 5–26 and were discarded | Rejected binarisation; removed the confidence cutoff instead (fail-safe: mask the uncertain) |
| 2026-10-15 | Second full run: precision 1.000, recall 0.997 — 9 misses, every one the focused field | Added `neutralise_focus_ring`: paints Chromium's blue ring (≈ rgb 0,95,204) white before OCR |
| 2026-10-15 | Third full run: 0 errors on 501 screenshots | Final configuration |

The focus-ring failure is the most important thing the PoC produced so far. It is a perception-layer
failure that hits precisely the value the agent has just entered, i.e. the freshest PII on screen, and
it would not have appeared with static mock-ups. It argues for evaluating any screenshot guard on
screenshots captured from live browser state.

## 7. Limitations

- **Realism of the forms.** One layout family, clean rendering, consistent fonts. Real portals have
  denser layouts, varying contrast, pop-ups and scrolling. Expect lower OCR recall there.
- **Label dependence.** The hybrid detector's strength comes from label context; a form whose labels
  are icons, placeholders inside the input, or in a language outside the keyword vocabulary degrades
  to pattern + Presidio performance.
- **Nigerian names and generic NER.** Presidio's spaCy model recognised only half the names; the
  guard sidesteps this with labels, but a free-text page with a Nigerian name would be at risk.
- **One OCR engine, one VLM, no adversarial inputs.** Not tested against deliberately obfuscated
  text, screenshots at other scales, or dark mode.
- **Small utility set.** 51 decision steps across 5 tasks is enough to show a trend, not to
  quantify it tightly.
- **Perfect scores invite suspicion.** They are real for this benchmark and were reached only after
  fixing a genuine failure, but they reflect the benchmark's cleanliness as much as the method.

## 8. Conclusion (to date)

1. A perception-layer guard that masks PII in screenshots before they reach a VLM is cheap to build
   and fast enough for real-time use: about half a second per screenshot on a laptop CPU.
2. Generic PII detection is not sufficient for government forms in a Nigerian context. Presidio alone
   recovers 59 % of values and mislabels most national identifiers; a detector that reads the form's
   own labels recovers 100 % on this benchmark. Data minimization at the perception layer needs
   *form-aware* detection, not just NER.
3. Task-aware policy is implementable with the same mechanism: once a value is attributed to a field,
   the policy can keep exactly the fields the task needs visible. Whether that preserves agent utility
   is what Experiment 3 will quantify.
4. Live browser state matters. The one failure mode found (focus ring hiding the just-typed value)
   was invisible in static screenshots and would have leaked the most recent user input every step.

## 9. Next steps

1. Add a VLM key and run Experiments 2 and 3; fill §5.3 and produce the privacy-versus-utility figure.
2. Add a second layout family per form (different fonts, two-column layout, placeholder labels) to test
   the label-context assumption.
3. Plug `redact()` into an off-the-shelf agent loop (Playwright + VLM) and record one live run for the
   demo, to make the middleware claim concrete.
4. If Paperasse source is available, repeat step 3 inside it.

## 10. Reproduction

```
git clone https://github.com/Qubai-B/project.git && cd project
./setup.sh                     # venv from requirements.lock, spaCy model, Chromium; checks Tesseract
cp .env.example .env           # add ANTHROPIC_API_KEY for Experiments 2 and 3
./run_all.sh                   # ~20 min CPU for the guard pass; VLM stages skipped without a key
```

Outputs land in `results/` and `demo/`; `results/REPORT.md` is the numeric summary.
