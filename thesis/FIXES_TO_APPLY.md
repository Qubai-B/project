# Fixes to apply to the write-up

A running list of corrections found while checking the chapters against each other.

## Status: applied on 13 November 2026

The author gave the word to fix everything, and items 1 to 33, 35 and 36 were applied in
`thesis/THESIS_Chapters_One_to_Five_v1.docx`, the single document that now holds all five chapters
with one reference list. The separate chapter files (One v5, Two v2, Three v6, Four v1, Five v1) are
the versions the list was written against and are superseded by it.

How the open points were settled:

- **Item 26 (MacBook removed), timing.** The guard was run over all 501 screenshots on the HP laptop.
  Its detections and both masked images are identical to the committed results for every screenshot,
  so the thesis can describe one computer. The timing reported is the HP laptop's own: optical
  character recognition 1,453 ms, detection 66 ms, policy and masking 108 ms, 1,627 ms in all
  ("about 1.6 seconds"), kept in `results/tables/guard_latency.hp.csv`. The earlier half-second
  figure no longer appears in the thesis.
- **Item 27 (tech stack).** Table 3.10 lists main tools only. Besides pandas, Matplotlib, NumPy and
  Pillow, the same rule removed Faker, Jinja2, pytesseract, spaCy and the Anthropic Python library.
  The author had not named those five; they can be put back.
- **Item 28 (coding agent).** Table 3.10 has a row for Claude Code, and Section 3.6.2 says it was used
  "to assist with programming, testing, and documentation, under the direction of the researcher".
  The author should check that sentence against the department's rule on declaring AI assistance.
- **Item 34 (optional experiment asking the model to guess masked values).** Not done; it needs the
  author's decision.
- **Chapter One, Section 1.4.** The limitation found in Chapter Four (a visible field can disclose a
  masked one) was added to the list of limitations.

The tables below are kept as the record of what was found.

Chapters checked: One v5, Two v2, Three v6, Four v1, Five v1.

## A. Contradictions and stale statements (found 13 November 2026, check of Chapters One to Five)

| # | Where | What it says | What it conflicts with | Fix |
|---|---|---|---|---|
| 1 | Ch. 1, §1.1 | The design "is developed in detail in Chapters Two and Three" | Chapter Two is the literature review; the design is in Chapter Three | Say Chapter Three |
| 2 | Ch. 1, §1.2 | "In a preliminary evaluation ... fewer than 60 per cent" | Ch. 4 reports it as Experiment 1 on all 501 screenshots: 56.1 per cent | Drop "preliminary"; give the figure |
| 3 | Ch. 1, §1.4 | Paperasse is "drawn from the literature" | Ch. 2, §2.3.2: a commercial product known from its vendor's documentation, "not a research system" | Reword as an existing product used as an illustration |
| 4 | Ch. 4, §4.1.6; Ch. 5, §5.3 | Presidio "is supplied without recognisers for Nigerian identifiers"; tools "should be extended" with one for the NIN | Ch. 2, §2.5.1: a later release has an optional NIN recogniser, off by default | Qualify to "the version tested"; recommend the remaining identifiers and turning the NIN recogniser on |
| 5 | Ch. 4, §4.1.1; Ch. 5, §5.1 | "fifteen tasks were recorded" | Ch. 3 and Table 4.1: five tasks, fifteen trajectories | Say fifteen trajectories of five tasks |
| 6 | Ch. 3, Table 3.10, §3.6.3, §3.6.4 | The Windows laptop was used for "replication"; the system "was rebuilt and checked" on it | It also ran the baseline on all 501 screenshots and Experiments 2 and 3. Table 4.3 therefore compares guard results from the development computer (Tesseract 5.5.2) with baseline results from the second computer (Tesseract 5.5.3), and no chapter says so | State which computer produced which result, in Ch. 3 and Ch. 4 |
| 7 | Ch. 3, §3.1 and §3.4 | "two of the design decisions" came from errors found in earlier cycles; keeping low-confidence words is presented as a choice made in favour of privacy | Table 4.2 lists four changes made after errors, including the removal of the confidence cut-off | Make the count and the account agree |

## B. Promises in Chapter Three that Chapter Four only partly keeps

| # | Chapter Three says | Chapter Four does | Fix |
|---|---|---|---|
| 8 | §3.7.3: leakage "is reported for each condition and each type" | Table by condition only; types in one sentence | Add a table of leakage by type |
| 9 | §3.7.2: coverage is reported | For the guard only | Give the baseline's coverage (0.561) |
| 10 | §3.7.3, §3.7.4, Table 3.12: 180 and 153 requests | Silent that 308 distinct requests were sent (25 identical image-and-prompt pairs were answered from stored replies) | State it in Ch. 4 |
| 11 | Nothing about a demonstration page | §4.1.3 presents one with two figures | Introduce it in Ch. 3 (§3.6), with what it is built from |

## C. Wording that differs between chapters

| # | Mismatch | Fix |
|---|---|---|
| 12 | The unmasked condition is "raw" in Ch. 3 and "no redaction" in Chs. 1 and 4 | Use one name |
| 13 | Objective i is "Develop a benchmark dataset" in Ch. 1 and "construct a benchmark" in Ch. 4 (text and Table 4.8) | Use Ch. 1's wording |
| 14 | §3.7.3 defines the leakage rate over "annotated values shown"; Table 4.6 counts masked values too ("Values counted") | Define it over the annotated values on the screenshot |
| 15 | Types are codes (PERSON, FINANCIAL) in Table 3.2 and Fig. 4.1, plain names in Table 4.4 | Give the code beside the name once |
| 16 | Ch. 3, §3.1.1: "did not build an autonomous agent, as stated in Section 1.4"; §1.4 says performance is measured offline, "not with a live agent" | Match the wording of §1.4 |

## D. Conflicts between the methodology and the results (found 13 November 2026, check of Chapter Three against Chapter Four)

| # | Where | What it says | What it conflicts with | Fix |
|---|---|---|---|---|
| 17 | Ch. 3, §3.4, Tables 3.4 and 3.5, algorithm steps 5 to 7, §3.7.6 | The guard has three rules: label, format pattern, general-purpose detector; on a real portal it "would then fall back on" the last two | In the evaluation every one of the 2,895 detections came from the label rule. The pattern rule and the Presidio fallback never fired, so the results say nothing about them. Ch. 4 does not report this | Report the count by rule in Ch. 4; say in §3.7.6 that the fallback rules were not exercised |
| 18 | Ch. 3, §3.7.6 | The leakage measure "may understate what the model can see" | §4.1.8: the 20 leaks are counted because a masked name occurs inside a visible email address once both are reduced to letters and digits (§3.7.3). The measure can also count a value the model did not read from its own field | Say in §3.7.6 that the matching rule cuts both ways |
| 19 | Ch. 4, §4.1.4 | "For every recorded step" the browser view was set beside the model's view | Composites exist for two of the fifteen trajectories only (T02 for identity I0001, T04 for I0002) | Say two trajectories, or build the rest |
| 20 | Ch. 3, Table 3.2 | Example email "chiamaka.okonkwo@example.com" | The emails in the dataset carry two digits (Fig. 4.4: "nnamdi.okafor36@example.com") | Use an example in the real format |
| 21 | Ch. 4, §4.1.9 | Explains the 36 correct typing steps by the visibly empty field | Does not recall that the prompt gives the model the values to type (§3.7.4), which is why masking cannot affect the typed value | Add one sentence |

## E. Tech stack: gaps between Chapter Three and Chapter Four

| # | Gap | Fix |
|---|---|---|
| 22 | Ch. 4 names only two tools: Presidio (§4.1.6) and Claude Haiku 5.5 (§4.1.8). The OCR engine is never named in Ch. 4 (Tesseract appears in Ch. 3 and Ch. 5) | Name Tesseract at first mention in Ch. 4 |
| 23 | The demonstration page (§4.1.3) is served by a small web server from Python's standard library and viewed in a browser. Neither chapter says what it is built with, and Table 3.10 has no row for it | Add a row to Table 3.10 with item 11 |
| 24 | Table 3.11 gives no specification for the development computer, yet §4.1.7 and Table 4.5 report its timing (488 ms) | Superseded by item 26: the MacBook is to be removed, so no specification is needed |
| 25 | Ch. 4 does not say that Experiments 2 and 3 and the baseline run were made on the second computer with Python 3.11 and Tesseract 5.5.3 | Covered by item 6 |

## F. Author's decisions (13 November 2026)

| # | Decision | What it touches | Notes |
|---|---|---|---|
| 26 | **Remove the MacBook Pro from the write-up.** | Ch. 3: Table 3.10 row 1 ("macOS (development)"), row 2 ("Python 3.9.6"), row 6 ("Tesseract 5.5.2"); §3.6.3 last paragraph ("rebuilt ... on a second computer"); §3.6.4 and Table 3.11 rows 1 to 4 ("development computer", "second computer"). Ch. 4: §4.1.7, Table 4.5 and Table 4.8 ("development computer", 447 / 17 / 24 / 488 ms). Ch. 5: §5.1 ("about half a second ... on the development computer"). | **Prerequisite, not yet done:** the guard's results and the timings in Table 4.5 were produced on the MacBook. They cannot be attributed to the HP laptop. Before the Mac is removed, the guard must be run over all 501 screenshots on the HP laptop, to confirm the detections are the same and to obtain its own timings (its OCR median alone is 1,376 ms, so "about half a second" would become roughly one and a half seconds). Once done, this also settles items 6, 24 and 25. **Author's position (13 November 2026):** which computer produced the results does not matter, and the MacBook is to be removed in any case. That holds for the detection, leakage and step-accuracy results, which do not depend on the machine. **One point left open:** the timing in Table 4.5 does depend on the machine (§3.7.6 says so). With the HP laptop as the only computer described, 488 ms would read as its timing, and it is not. Either the guard is timed on the HP laptop and those figures are reported, or the half-second figure is kept and attributed to an unnamed second laptop. |
| 27 | **Tech stack at a high level only.** Remove pandas, Matplotlib, NumPy and Pillow. Keep Presidio, Tesseract and Playwright. | Ch. 3: Table 3.10 rows 8 ("Image processing") and 9 ("Analysis and charts") | **To confirm with the author:** by the same rule these supporting libraries would also go: Faker (row 5), Jinja2 (row 3), pytesseract (row 6), spaCy (row 7) and the Anthropic Python library (row 10). The lock file mentioned in §3.6.3 still records every exact version. Item 23 (a row for the demonstration page) should be worded at the same level. |

| 28 | **Include the coding agent that was used.** | Ch. 3: a new row in Table 3.10 and a sentence in §3.6.2 or §3.6.3 | The commit history credits one coding agent throughout: Claude Code (Anthropic), with the model Claude Fable 5.1 on the five commits of 1 November 2026 and Claude Fable 5.2 on the seven commits from 12 November 2026. **Confirmed by the author (13 November 2026):** the same coding agent was used during the October development. **Still to confirm:** how the department requires the use of an AI assistant to be declared (the row states the tool; a sentence on what it was used for must match what was actually done, including any drafting of the chapters). |

| 35 | **Present the web interface as the system's user interface**, through which evaluators interact with the system and see how it works. It is not to be played down as a mere aid. | Ch. 4, §4.1.3: rename "The Demonstration Page" and drop "It is an aid to demonstration and took no part in the evaluation"; keep one accurate sentence that the figures of the three experiments were produced by the scripts, and that the interface calls the same guard functions. Ch. 3: introduce the interface in §3.6.1 (architecture) and add the evaluator's use of it to the use-case diagram and its text (§3.1.1, Fig. 3.2); a row in Table 3.10 (with items 11 and 23). Ch. 5, §5.1: "shown through a demonstration page" to match. | Author's point (13 November 2026). It also bears on item 30: the interface is where an evaluator sees, side by side, the original screenshot and the copy sent to the model, with each value marked masked or visible. **Also to align outside the thesis:** README.md, LOG.md and the docstring of `demo/live_app.py` call it "a demonstration aid ... not part of the evaluated system". |

| 36 | **If the web interface is hosted for supervisors, say so in one sentence.** | Ch. 3, §3.6.1 (with item 35); Ch. 4, §4.1.3 | The thesis argues that the guard runs on the user's own device so that the unmasked screenshot never leaves it. A hosted copy receives the screenshots visitors load. The sentence: the hosted copy exists so that evaluators can try the system with the synthetic sample forms, and in real use the guard runs locally. Only needed once a hosted copy exists. Figs. 4.3 and 4.4 were captured from the local page and remain valid. |

## G. Proposed additions, from the author's question on what Experiment 2 proves (13 November 2026)

These are proposals, not errors. The author asked how the study knows that the model does not know a masked value, and whether the model would give a value back if it were not asked.

| # | Proposal | Where |
|---|---|---|
| 29 | State what is being protected against. The disclosure happens when the image is transmitted, whatever the model later says. "Leakage" in the study means what can be read from the image that was sent, and the request to the model to transcribe is a probe for that, not a claim about what the model would volunteer. | Ch. 3, §3.7.3; Ch. 1 definition of privacy leakage already agrees |
| 30 | Present the direct evidence first. A masked value is absent from the image by construction, and this was checked without any model: in all 501 fully masked images, every pixel inside each of the 2,895 annotated text boxes is pure black, and the image files carry no embedded text. The model's empty replies corroborate this; they are not the proof. | Ch. 3, §3.7.2 (coverage); Ch. 4, §4.1.6 and §4.1.8 |
| 31 | Name the unredacted condition as the control. The same prompt that returned nothing from the masked images returned 99.8 per cent from the unmasked ones, so the empty replies are not explained by the model declining to answer. | Ch. 4, §4.1.8 |
| 32 | Add to the limitations what the probe does not test: values the model could infer or guess from what stays visible (the email address and the name is one found case; the length of a mask is another), a prompt that asks for inference instead of transcription, and what could be pieced together across the steps of a task. | Ch. 3, §3.7.6; Ch. 4, §4.1.8 |
| 33 | Say in Ch. 4 that in Experiment 3 the values the task needs are given to the model in the prompt (for task T02 this includes the BVN). The model knows those by design. | Ch. 4, §4.1.9 (with item 21) |
| 34 | Optional extra experiment: ask the model to infer or guess the masked values. It would measure the residual channel in item 32 directly, at a cost of a few cents. | New; needs the author's decision |

## H. Reference list checked against APA 7th edition (14 November 2026) — applied in version 2

The author asked for these to be applied, and they are in `thesis/THESIS_Chapters_One_to_Five_v2.docx`,
which supersedes version 1:

- **37 applied.** Chapter One now cites its sources: Anthropic (2024) and OpenAI (2025a) for
  screenshot-driven agents, EverydayMoney SAS (2026) for Paperasse, Cen et al. (2026) and N. Zhao (2026)
  for "recent studies", Bagdasarian et al. (2024) for AirGapAgent, Microsoft (2025) for Presidio,
  the GDPR and the Nigeria Data Protection Act, and Hoepman (2014) for data minimization.
- **38 left as it is.** The heading stays "REFERENCES" in bold capitals at the left, to match the
  chapter headings of the document and the department's sample. To follow APA strictly it would be
  "References", centred.
- **39 applied.** All arXiv entries use the DOI form of the link.
- **40 applied.** The Central Bank of Nigeria (2019) entry links to the document itself. The link was
  opened and the document checked: it is the bank's circular of 9 March 2020 carrying the standards,
  whose cover is dated 2019.
- **41 not resolved.** The registry of DOIs (Crossref) gives pages 75–106 for Hevner et al. (2004); the
  publisher's own page gives no page numbers, and the article could not be opened. The entry still
  says 75–105, the range usually cited. To settle it, look at the last page number of the article.
- **42 and 43 left as they are**, as acceptable.

The 59 entries and the in-text citations follow APA 7th edition in the main. These points were found:

| # | Point | Where | Fix |
|---|---|---|---|
| 37 | Chapter One has no in-text citations at all, although it names AirGapAgent, Microsoft Presidio, Paperasse, the GDPR and the Nigeria Data Protection Act, and says "Recent studies highlight". All of these have entries in the reference list. | Ch. 1, §1.1, §1.2, §1.5 | Add the citations: Bagdasarian et al. (2024), Microsoft (2025), EverydayMoney SAS (2026), the two statutes, and the studies meant by "recent studies" |
| 38 | The heading is "REFERENCES", bold, capitals, at the left. APA has "References", bold and centred. | Reference list | Keep if the department's format asks for capitals (the sample project has its own style); otherwise change |
| 39 | arXiv links are given in two forms: `https://doi.org/10.48550/arXiv...` for most, `https://arxiv.org/abs/...` for Lin et al. (2025), Mishra et al. (2020) and Y. Zhao et al. (2026). | Reference list | Use the DOI form for all three |
| 40 | Central Bank of Nigeria (2019) links to the bank's home page, not to the document. | Reference list | Give the document's own address |
| 41 | Hevner et al. (2004) is given as pages 75–105; the publisher's record says 75–106. | Reference list | Confirm against the article and correct |
| 42 | The two Nigerian Acts and the GDPR are set out in an adapted form. APA sends legal sources to a legal citation style, so there is no single correct APA form for them. | Reference list | Leave unless the department has a rule for statutes |
| 43 | Several conference papers (NeurIPS, ICLR) and one journal article (Ji et al., 2025) link to their arXiv copies and carry no page numbers. | Reference list | Acceptable; link to the published version where one exists |

## I. Raised on 14 November 2026

The current document is `thesis/THESIS_Chapters_One_to_Five_v3.docx` (99 pages). It is version 2 with
item 45 applied and nothing else changed.

| # | Point | Where | Status |
|---|---|---|---|
| 44 | The closing sentence of a chapter that points to the next one ("Chapter Five summarises the study ...") stays at the end of Chapters Two, Three and Four. The author agreed. Chapter One has no such sentence; one could be added so that all four match. | Ch. 1, §1.7 | Keeping the three is decided; adding one to Chapter One awaits the author's word |
| 45 | The thesis has no source code in its appendices. Appendix A holds the two prompts and Appendix B two screenshots. The address of the repository is not given anywhere in the text either. Proposal: an Appendix C with the source code of the guard itself (the four modules and the label vocabulary, about 250 lines, six or seven pages), and the repository address for the rest (1,666 lines in all, which would run to some forty pages if printed in full). | New Appendix C; Ch. 3, §3.6.3 | **Applied in version 3** (14 November 2026), on the author's word. Appendix C prints `guard/ocr.py`, `guard/detect.py`, the first 43 lines of `common/forms.py` (the label vocabulary), `guard/policy.py` and `guard/mask.py`: 267 lines on four pages (96 to 99), in 7-point Courier New. A check compared every printed line with the files and found them identical. Section 3.0 names the appendix, and Section 3.6.3 gives the repository address, https://github.com/Qubai-B/project. Eight lines of code are longer than the page is wide and continue on the line below; the appendix says so. The repository must stay public for the address to be of use to an examiner. |

## Still open, not contradictions

- Ch. 1, §1.4 does not list the limitation found in Ch. 4 (a visible field can disclose a masked one). To consider in the Chapter One fine-tune.
