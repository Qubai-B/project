# Project record — data minimization at the perception layer for screenshot-driven agents

A running record of every decision, method, result and conclusion in this proof of concept, kept in
the order they happened so the methodology and results chapters can be written from it directly.
Numbers are from the run of **15 October 2026**; `results/REPORT.md` regenerates them from the tables.
The objectives, scope and limitations were aligned with the revised Chapter One
(`thesis/CHAPTER_ONE_Project_Revised_v4.docx`) on **9 November 2026**; no result changed.
Experiments 2 and 3 were run on **13 November 2026** (§5.3).

---

## 1. Problem and starting point

Chapter One of the project proposes a *visual redaction framework* for AI agents that operate on
screenshots of government web portals. Such agents send screenshots to a cloud-hosted
vision-language model (VLM); the screenshots contain personally identifiable information (PII), and
nothing in current governance frameworks addresses this visual channel. The aim is to design,
implement and evaluate a guard that masks sensitive information in a screenshot *before* it leaves
the user's machine, while preserving the agent's ability to complete the task.

Objectives from the revised Chapter One (§1.3) and how this PoC maps to them:

| # | Objective | Realised as |
|---|-----------|-------------|
| 1 | Benchmark of screenshots of mock Nigerian e-service forms, filled with synthetic identities and automatically annotated with the location, type and form field of every PII item | `data/benchmark/` — 450 screenshots, DOM-exact boxes; `data/trajectories/` — 51 recorded steps |
| 2 | Lightweight visual redaction guard that identifies PII from its form-field label and masks it before transmission, under a full and a task-aware policy | `guard/` package, ~0.5 s per screenshot on the development laptop's CPU |
| 3 | Evaluate the guard's detection accuracy against the benchmark and compare it with a general-purpose PII detector | Experiment 1 (hybrid guard vs Presidio baseline) — **done** |
| 4 | Evaluate the reduction of privacy leakage, measured by what a VLM can still read from redacted screenshots | Experiment 2 (VLM leakage) — **done** (13 November 2026, one model) |
| 5 | Assess the impact of redaction on agent performance, measured by next-action choice on recorded trajectories | Experiment 3 (offline step accuracy) — **done** (13 November 2026, one model) |

Integration into an existing agent is **not** an objective. Chapter One (§1.4) uses Paperasse only as
an illustrative reference system and excludes integration into or deployment on its codebase. The
guard is offered as a reference design: `redact()` is a single call on the screenshot path, and its
place in the loop is illustrated with side-by-side composites (§5.4).

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
   as in Mind2Web-style evaluation), and the guard's place in an agent loop is illustrated with
   side-by-side composites of browser view versus model input. Human-in-the-loop controls are
   discussed in Chapter One as context and are not implemented.
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
Inserting that one call between screenshot capture and the model request is all an integration
would require; carrying out that integration in a real agent is outside the project's scope.

### 4.4 Experimental protocol
All 501 screenshots are processed by `scripts/04_run_guard.py`, which stores both policy outputs and
the raw detections per screenshot under `results/redacted/`, mirroring the data paths.

**Experiment 1 — detection quality** (`05_eval_detection.py`). Each ground-truth text box is matched
to the detection with highest IoU; a match at IoU ≥ 0.5 is a true positive, and a *typed* true
positive if the PII type also agrees. Unmatched detections are false positives, unmatched ground
truth are false negatives. Reported per PII type and overall: precision, recall, F1, type accuracy,
and mean *coverage* (fraction of each ground-truth text box painted over under `full`). Both the
hybrid detector and the Presidio baseline run on all 501 screenshots. (Until 10 November 2026 the
baseline ran only on the 30 filled screenshots of the first 10 identities; see §6.)

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

**Model settings for Experiments 2 and 3.** One request is one screenshot followed by one prompt,
with no earlier messages. The model is named by `VLM_MODEL` in `.env`; the reported run used
Claude Haiku 5.5 (`claude-haiku-5-5`, Anthropic, released 7 October 2026) with its default settings.
Each reply is limited to 4,000 tokens. The limit was 800 until 13 November 2026 and was raised
because on current models the reasoning counts towards it as well as the answer. A reply that does
not finish normally (cut off or refused) is not cached or scored; the run stops instead. Replies are
cached in `results/cache/` under a key of model name, image and prompt, with the token counts.

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

Presidio baseline, same 501 screenshots and 2,895 values (run of 10 November 2026):

| PII type | n | precision | recall | F1 | type accuracy |
|---|---|---|---|---|---|
| EMAIL | 195 | 1.000 | 1.000 | 1.000 | 1.000 |
| PHONE | 124 | 1.000 | 0.919 | 0.958 | 0.877 |
| ADDRESS | 635 | 1.000 | 0.709 | 0.829 | 0.660 |
| BANK_ACCOUNT | 65 | 1.000 | 0.692 | 0.818 | 0.000 |
| DOB | 351 | 0.667 | 0.991 | 0.797 | 1.000 |
| PERSON | 702 | 1.000 | 0.484 | 0.653 | 0.859 |
| NIN | 342 | 1.000 | 0.281 | 0.438 | 0.000 |
| LICENCE_NO | 115 | 1.000 | 0.148 | 0.258 | 0.000 |
| BVN | 68 | 1.000 | 0.088 | 0.162 | 0.000 |
| TIN | 124 | 1.000 | 0.081 | 0.149 | 0.000 |
| PASSPORT | 103 | 1.000 | 0.019 | 0.038 | 0.000 |
| FINANCIAL | 71 | 1.000 | 0.014 | 0.028 | 0.000 |
| **ALL** | **2,895** | **0.903** | **0.561** | **0.692** | **0.759** |

Baseline by part of the dataset:

| Part | screenshots | values | precision | recall | F1 |
|---|---|---|---|---|---|
| Benchmark, filled | 150 | 1,600 | 0.950 | 0.595 | 0.732 |
| Benchmark, partial | 150 | 800 | 0.890 | 0.504 | 0.643 |
| Benchmark, empty | 150 | 0 | — | — | — |
| Trajectory steps | 51 | 495 | 0.918 | 0.543 | 0.683 |

Reading: a generic PII detector finds 56 % of the values on these forms. It finds about half of the
names, under a third of NINs, fewer than one in ten BVNs and TINs, and almost no passport numbers or
income figures. When it does find a NIN, BVN, TIN, bank account, licence or passport number it
labels it as something else every time (type accuracy 0). Its 174 false positives are all the same
thing: the label "Annual Income" read as a date, once on every screenshot of the tax form, including
the 50 empty ones. The form-aware detector finds and types everything. Figure:
`results/figures/detection_f1.png`.

The earlier baseline (30 filled screenshots of the first 10 identities, 320 values) gave precision
0.950, recall 0.591, F1 0.728 and type accuracy 0.725. The new run reproduces those 30 screenshots
exactly, detection for detection, although it was made on the Windows laptop with Tesseract 5.5.3
and the earlier one on the Mac with 5.5.2. The overall figures are lower on the full set because the
partly filled screenshots and the trajectory steps carry a higher share of identifiers, which is
where the baseline is weakest. On the small sample the baseline found no BVN, TIN or income figure
at all; on the full set it finds a few, never with the right type.

### 5.2 Latency
Median per screenshot over 501 (CPU, no GPU): OCR 447 ms, detect 17 ms, mask 24 ms — **488 ms
total**. The guard adds about half a second per agent step, which is well inside the several seconds
a VLM call already takes. The figure depends on hardware: on a second, slower Windows laptop
(1 November 2026) OCR alone took 1.3 to 2.8 s per screenshot. Chapter One therefore describes the
guard as *lightweight* and does not claim real-time operation.

### 5.3 Experiments 2 and 3
Run of 13 November 2026 with Claude Haiku 5.5 (`claude-haiku-5-5`). Tables:
`results/tables/leakage.csv`, `leakage_samples.csv`, `step_accuracy.csv`,
`step_accuracy_samples.csv`. Figure: `results/figures/privacy_vs_utility.png`.

**Experiment 2 — leakage.** 60 screenshots (partial and filled, first 10 identities, three forms),
480 annotated values, three conditions.

| Condition | Values counted | Read by the model | Leakage rate |
|---|---|---|---|
| Raw (no redaction) | 480 | 479 | 0.998 |
| Full policy | 480 | 0 | 0.000 |
| Task-aware policy, values the task does not need | 380 | 20 | 0.053 |
| Task-aware policy, values the task needs (left visible on purpose) | 100 | 99 | 0.990 |

By type, the only non-zero rate under either policy is PERSON under task-aware: 20 of 120 (0.167).
Every other type is 0 under both policies.

Reading:

- On unredacted screenshots the model transcribes essentially everything. The one miss is a reading
  error by the model ("119 Ogui Road, GRA" returned as "119 Ogu Road, GRA").
- Under the full policy nothing is read: the reply is an empty list on every one of the 60
  screenshots.
- The 20 values read under the task-aware policy are the first name and surname on the 10 filled
  driver's licence screenshots. The guard masked both name fields. The benchmark redacts that form
  for task T03, which needs the phone number and the email address, so the email stays visible, and
  the synthetic email addresses are built from the name (`nnamdi.okafor36@example.com`). The scoring
  rule finds the name inside the transcribed email. This is not a detection miss. It is a field the
  task needs disclosing a field that was masked, which masking field by field cannot prevent.
- The one needed value not counted is a passport number the model misread by one digit
  (`A78159587` returned as `A78159287`, `passport_application/I0007/filled`).
- The task-aware condition here covers tasks T01, T03 and T05 only (the first task of each form).

**Experiment 3 — offline step accuracy.** 51 recorded steps, three conditions.

| Task | Steps | Raw | Full policy | Task-aware policy |
|---|---|---|---|---|
| T01 address | 12 | 1.000 | 0.750 | 1.000 |
| T02 income and bank details | 12 | 1.000 | 0.917 | 1.000 |
| T03 phone and email | 9 | 1.000 | 0.778 | 1.000 |
| T04 licence number and NIN | 9 | 1.000 | 0.889 | 1.000 |
| T05 NIN and passport number | 9 | 1.000 | 0.889 | 1.000 |
| **All** | **51** | **1.000** | **0.843** | **1.000** |

Field accuracy equals step accuracy in every cell. Reading:

- With the raw screenshot and with the task-aware screenshot the model chose the recorded action at
  all 51 steps.
- Under the full policy it was wrong at 8 steps. All 8 are the final step of a trajectory, where the
  recorded action is to click "Save and Continue": the model typed one of the task's values again
  instead. With every value masked it cannot confirm that the needed fields already show the right
  values. It still clicked correctly on 7 of the 15 final steps, and it chose the right field and
  value on all 36 typing steps, because an empty field is visibly empty even when the rest is masked.
- With 51 steps, one step is about two percentage points and no statistical test is applied.

**Privacy against utility.** No redaction: leakage 0.998, step accuracy 1.000. Full policy: 0.000
and 0.843. Task-aware policy: 0.053 and 1.000. On this benchmark and this model the task-aware
policy keeps the agent's step accuracy at the unredacted level while hiding all but the names that
the visible email address gives away.

**Run details.** 308 distinct calls: 25 of the 333 planned requests had the same image and prompt
as another and were answered from the cache: where no field the task needs is filled yet, the full
and task-aware images are identical (10 partly filled licence screenshots in Experiment 2, 15 steps
in Experiment 3). 587,486 input and 60,687 output tokens, about 0.09 US dollars at the listed price of
0.10 and 0.50 dollars per million. Every reply ended normally; the longest used 712 tokens, so the
change of the reply limit from 800 to 4,000 affected no reply in this run. Experiment 2 was
interrupted once by a connection timeout at call 100 and resumed from the cache.

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
| 2026-11-09 | Chapter One revised to match what was built (`thesis/CHAPTER_ONE_Project_Revised_v4.docx`): five objectives, with detection accuracy against a generic baseline added as its own objective; Paperasse kept as an illustrative reference only | §1 objectives table renumbered; agent integration moved from an objective to future work (§9); two limitations added (§7) |
| 2026-11-10 | Presidio baseline re-run on all 501 screenshots (it had covered 30) so that Experiment 1 compares both detectors on the same material | Baseline recall 0.561, F1 0.692 on 2,895 values (was 0.591 and 0.728 on 320); the 30 original screenshots are reproduced exactly; §4.4 and §5.1 updated; `run_all.sh` and `run_all.ps1` now run the baseline on everything |
| 2026-11-13 | First test calls to the model: one reply used 648 of the 800 tokens allowed, because the model's reasoning counts towards the limit | Reply limit raised to 4,000 in `common/vlm.py`; replies that do not end normally are no longer cached or scored |
| 2026-11-13 | Experiments 2 and 3 run on Claude Haiku 5.5 | Leakage 0.998 raw, 0.000 full, 0.053 task-aware; step accuracy 1.000 raw, 0.843 full, 1.000 task-aware; §5.3 filled; names found to be recoverable from the visible email address (§7) |

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
  text, screenshots at other scales, or dark mode. Experiments 2 and 3 used one model, Claude Haiku
  5.5, the lowest-priced model of its family; a larger model was not tested.
- **A visible field can disclose a masked one.** Under the task-aware policy the email address left
  visible for task T03 contains the user's name, so the masked name fields were recovered from it
  (20 of 380 non-task values in Experiment 2). The guard decides field by field and has no notion of
  one value being derivable from another.
- **Small utility set.** 51 decision steps across 5 tasks is enough to show a trend, not to
  quantify it tightly.
- **Offline utility, no live agent.** Agent performance is measured one step at a time on recorded
  trajectories, not with an agent completing tasks end to end, and the guard is not integrated into
  Paperasse or any other agent.
- **Text only.** The guard masks text it can read. Photographs, signatures and other non-textual
  personal data are not covered.
- **Perfect scores invite suspicion.** They are real for this benchmark and were reached only after
  fixing a genuine failure, but they reflect the benchmark's cleanliness as much as the method.

## 8. Conclusion (to date)

1. A perception-layer guard that masks PII in screenshots before they reach a VLM is cheap to build
   and light enough to sit inside an agent loop: about half a second per screenshot on the
   development laptop's CPU, with no GPU.
2. Generic PII detection is not sufficient for government forms in a Nigerian context. Presidio alone
   recovers 56 % of values and mislabels every national identifier it finds; a detector that reads the form's
   own labels recovers 100 % on this benchmark. Data minimization at the perception layer needs
   *form-aware* detection, not just NER.
3. Task-aware policy is implementable with the same mechanism: once a value is attributed to a field,
   the policy can keep exactly the fields the task needs visible. On the 51 recorded steps and one
   model it preserved step accuracy completely (1.000, the same as with no redaction), where masking
   everything lowered it to 0.843 because the model could no longer tell that a task was finished.
   The price was that 5.3 % of the values the task did not need could still be read, all of them
   names disclosed by a visible email address.
4. Live browser state matters. The one failure mode found (focus ring hiding the just-typed value)
   was invisible in static screenshots and would have leaked the most recent user input every step.

## 9. Next steps

1. Optional: repeat Experiments 2 and 3 on a second, larger model to see whether the results of §5.3
   hold beyond one model.
2. Add a second layout family per form (different fonts, two-column layout, placeholder labels) to test
   the label-context assumption.
3. Optional, beyond the Chapter One objectives: plug `redact()` into an off-the-shelf agent loop
   (Playwright + VLM) and record one live run for the demo.
4. Future work, out of scope for this project (Chapter One §1.4): integration into Paperasse or
   another production agent.

## 10. Reproduction

```
git clone https://github.com/Qubai-B/project.git && cd project
./setup.sh                     # venv from requirements.lock, spaCy model, Chromium; checks Tesseract
cp .env.example .env           # add ANTHROPIC_API_KEY for Experiments 2 and 3
./run_all.sh                   # ~20 min CPU for the guard pass; VLM stages skipped without a key
```

Outputs land in `results/` and `demo/`; `results/REPORT.md` is the numeric summary.
