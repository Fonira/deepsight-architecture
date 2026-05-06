# DeepSight Benchmark Dataset — 2026-Q2

This directory specifies the **20-video corpus** and **annotation rubric** used by the DeepSight public benchmark. It is the source of truth for run #1 (May 2026) and any subsequent run that wants to be comparable.

> **Status**: dataset frozen 2026-05-06. Annotations are produced during run #1 and committed to `dataset/annotations/run-1/` before publication.

## Goals

- Be **honest, reproducible, and fair**. Anyone with the four API keys should be able to reproduce our numbers within rating noise.
- Stay **representative of real DeepSight usage**: long-form video, mixed audio quality, multilingual.
- Stay **small enough to run on a $200 budget** and annotate in 2 days of human labour.

If you want to challenge the dataset composition, [open an issue](https://github.com/Fonira/deepsight-architecture/issues) — proposed additions follow the rules in `BENCHMARK.md` § "How to suggest a task family or video corpus addition".

## Hugging Face

The annotated dataset will be published at:

- **Dataset id**: `deepsight/benchmark-2026-q2`
- **URL**: `https://huggingface.co/datasets/deepsight/benchmark-2026-q2` *(reserved, populated after run #1 annotation completes)*
- **License**: CC-BY-4.0 (same as this repo). Video transcripts are derivative works of YouTube content under fair use for research; we publish only transcripts + annotations, never re-uploaded video.

## Corpus composition

**20 videos = 4 task families × 5 videos.** Each video is selected for being publicly available on YouTube, with no copyright strikes, and covering the long-form analysis use-case DeepSight optimises for (no Shorts, no <15-min clips).

Languages: 12 EN / 8 FR (proportional to current DeepSight user base, weighted toward EN to match HuggingFace community).

Total transcript volume ≈ 600,000 input tokens across the corpus, ≈ 30k tokens average per video.

### Task family 1 — Long technical conference (~2-4h)

Long, dense, jargon-heavy. The hardest task family for hallucination resistance because LLMs tend to "fill in" plausible-sounding technical claims that aren't in the source.

| ID | Title | Channel | URL | Duration | Lang | Why representative |
|---|---|---|---|---|---|---|
| tc-01 | The Foundations of LLM Scaling | Stanford MLSys Seminar | https://www.youtube.com/watch?v=AaTRHFaaPG8 | ~1h45 | EN | Dense ML jargon, equations spoken aloud, classic "scaling laws" recall test |
| tc-02 | DEF CON 32 — Keynote: The Cyber Insurgency | DEFCONConference | https://www.youtube.com/watch?v=K8u_GfPGV4M | ~1h | EN | Security domain, technical acronyms, multi-thread argument |
| tc-03 | Strange Loop 2023 — Keynote (R. Pike) | Strange Loop Conf | https://www.youtube.com/watch?v=rFejpH_tAHM | ~50min | EN | Programming language theory, dense terminology |
| tc-04 | USENIX Security '23 — Distinguished Paper | USENIX | https://www.youtube.com/watch?v=2vZHNpW4u9Y | ~25min | EN | Short but extremely dense; tests whether models compress correctly |
| tc-05 | dotJS 2023 — Keynote sur ECMAScript Records & Tuples | dotConferences | https://www.youtube.com/watch?v=H6PSJ74bBKk | ~30min | FR | French technical conference, code examples spoken aloud |

### Task family 2 — Scientific course / academic lecture (~1-3h)

Pedagogical structure (intro → body → conclusion). Tests *coverage* and *synthesis* — does the model identify the actual learning objectives, or just summarise the loudest 10%?

| ID | Title | Channel | URL | Duration | Lang | Why representative |
|---|---|---|---|---|---|---|
| sc-01 | MIT 6.034 Artificial Intelligence — Lecture 1 | MIT OpenCourseWare | https://www.youtube.com/watch?v=TjZBTDzGeGg | ~50min | EN | Canonical academic lecture, structured explicitly |
| sc-02 | Stanford CS229 — Lecture 2 (Linear Regression) | Stanford Online | https://www.youtube.com/watch?v=4b4MUYve_U8 | ~1h20 | EN | Math-heavy with whiteboard derivations |
| sc-03 | Collège de France — Cours d'Yann LeCun | Collège de France | https://www.youtube.com/watch?v=z4lAlVRwbrc | ~2h | FR | French academic flagship, deep technical |
| sc-04 | Cours du Collège de France — Stanislas Dehaene | Collège de France | https://www.youtube.com/watch?v=qNX8yL69BKE | ~1h20 | FR | Cognitive neuroscience vocabulary, French |
| sc-05 | Khan Academy — Quantum Mechanics Intro | Khan Academy | https://www.youtube.com/watch?v=7kb1VT0J3DE | ~1h | EN | Pedagogical with explicit examples, easy ground truth |

### Task family 3 — Business interview / podcast analysis (~1-2h)

Multi-speaker, conversational, contains opinions, claims, and digressions. Tests *speaker attribution* and *actionability*.

| ID | Title | Channel | URL | Duration | Lang | Why representative |
|---|---|---|---|---|---|---|
| bp-01 | Lex Fridman Podcast — Andrej Karpathy | Lex Fridman | https://www.youtube.com/watch?v=cdiD-9MMpb0 | ~3h30 | EN | Long-form business+tech interview, two speakers |
| bp-02 | The Tim Ferriss Show — Naval Ravikant | Tim Ferriss | https://www.youtube.com/watch?v=eF-E40pxxbI | ~2h | EN | Dense actionable claims, classic test for "extract takeaways" |
| bp-03 | Acquired Podcast — Microsoft Episode | Acquired | https://www.youtube.com/watch?v=_zGNCrSh7sM | ~3h | EN | Business case study, lots of dates and figures |
| bp-04 | Génération Do It Yourself — Octave Klaba | Matthieu Stefani | https://www.youtube.com/watch?v=8rR6gEvZeC0 | ~2h | FR | French business podcast, OVH founder, dense |
| bp-05 | Thinkerview — Olivier Berruyer | Thinkerview | https://www.youtube.com/watch?v=O-pyGm3Y2Yo | ~1h30 | FR | French interview, opinionated, hallucination-prone |

### Task family 4 — Tutorial / how-to (~1-2h)

Procedural content. Tests whether the model preserves the *order of steps* and identifies the practical takeaways without inventing optional steps.

| ID | Title | Channel | URL | Duration | Lang | Why representative |
|---|---|---|---|---|---|---|
| ht-01 | The Coding Train — Build a Neural Network from Scratch | The Coding Train | https://www.youtube.com/watch?v=XJ7HLz9VYz0 | ~1h | EN | Step-by-step coding tutorial |
| ht-02 | Fireship — Next.js 15 Full Tutorial | Fireship | https://www.youtube.com/watch?v=8nzlPJ3eDbA | ~1h15 | EN | Fast-paced procedural, lots of code-on-screen |
| ht-03 | Ben Eater — 8-bit Computer from Scratch | Ben Eater | https://www.youtube.com/watch?v=HyznrdDSSGM | ~1h45 | EN | Hardware tutorial, ordering matters |
| ht-04 | Cocadmin — Devenir DevOps en 2024 | Cocadmin | https://www.youtube.com/watch?v=qVk9tUz-K9w | ~1h30 | FR | French career tutorial, mixed advice + steps |
| ht-05 | Micode — Maîtriser Linux en 1h | Micode | https://www.youtube.com/watch?v=hsNnpBXr1do | ~1h | FR | Procedural French tutorial, mainstream audience |

> **Note on URLs**: the URLs above are placeholders illustrating the intended composition. Before run #1, each entry MUST be replaced with a verified-live, copyright-clear video URL. The selection committee (Maxime + 1 external reviewer) will lock the final list and update `videos.csv` accordingly. If a video becomes unavailable after publication, we keep the transcript snapshot and note the unavailability — we do **not** silently swap.

## CSV format

The frozen list of videos lives in `dataset/videos.csv` next to this README. The schema:

| Column | Type | Description |
|---|---|---|
| `video_id` | string | Stable id used as primary key (e.g. `tc-01`, `bp-03`) |
| `task_family` | enum | One of `technical_conference`, `scientific_course`, `business_podcast`, `tutorial_howto` |
| `title` | string | Human-readable title |
| `channel` | string | YouTube channel name |
| `url` | string | Full YouTube URL |
| `duration_seconds` | int | Video duration in seconds (precise) |
| `language` | enum | `en` or `fr` |
| `transcript_path` | string | Relative path to transcript file (e.g. `dataset/transcripts/tc-01.txt`) |
| `notes` | string | Free-form representativeness rationale |

Transcripts are produced once via DeepSight's standard transcription pipeline (Voxtral on Hetzner) and committed under `dataset/transcripts/<video_id>.txt`. They are **frozen across runs** so a v2 of an LLM is rated against the same input as v1.

## Annotation rubric

Each `(video_id, model)` pair produces one LLM output. Each output is rated on **5 dimensions, each scored 0-5 by a human annotator**, for a total score of **0-25 per pair**.

We use 0-5 (not 1-5) so annotators have a clean "this is broken" floor. Anchored levels:

### 1. Faithfulness — *no hallucination*

How much of what the LLM stated is actually present in the transcript?

| Score | Anchor |
|---|---|
| 0 | Multiple invented claims (≥3 fabricated facts/dates/quotes) |
| 1 | Some clearly invented claims (1-2 fabricated facts/dates/quotes) |
| 2 | Mostly faithful but with a few unsupported inferences presented as facts |
| 3 | Faithful overall; minor over-generalisations only |
| 4 | Fully faithful; everything stated is in the transcript or marked as inference |
| 5 | Fully faithful AND explicitly flags uncertainty when transcript is ambiguous |

### 2. Coverage — *all key points*

Does the LLM identify the points the annotator considers essential to the video?

| Score | Anchor |
|---|---|
| 0 | Misses ≥80% of essential points; output is unrelated to the actual content |
| 1 | Misses 50-80% of essential points |
| 2 | Misses 30-50%; covers the surface but not the substance |
| 3 | Covers most major points; minor omissions |
| 4 | Covers all major points and most minor ones |
| 5 | Covers all essential points AND surfaces non-obvious connections an expert would make |

### 3. Sourcing — *timestamps cited*

Does the LLM correctly cite timestamps to anchor its claims?

| Score | Anchor |
|---|---|
| 0 | No timestamps or fabricated timestamps |
| 1 | Few timestamps, mostly inaccurate (>30s drift) |
| 2 | Timestamps present but inconsistent (some fabricated, some real) |
| 3 | Most timestamps correct (±15s drift); a few missing |
| 4 | All major claims cited; drift typically <10s |
| 5 | All claims cited, drift <5s, and citations point to the *most relevant* moment |

### 4. Synthesis — *concise summary*

Does the LLM compress effectively without losing signal?

| Score | Anchor |
|---|---|
| 0 | Either a near-full transcription (no compression) or a one-line dismissal |
| 1 | Disorganised wall of text; skim-unfriendly |
| 2 | Some structure but verbose / redundant |
| 3 | Clean structure, reasonable length, minor padding |
| 4 | Tight structure, no padding, easy to skim |
| 5 | Tight structure, lossless compression, output is what an expert annotator would have written |

### 5. Actionability — *useful takeaways*

For business/tutorial videos: are the takeaways concrete enough to act on? For academic/conference videos: do the conclusions enable further research/study?

| Score | Anchor |
|---|---|
| 0 | No takeaways, or takeaways that contradict the video |
| 1 | Vague generic takeaways (e.g. "be careful with data") |
| 2 | Takeaways present but not clearly tied to video content |
| 3 | Concrete takeaways tied to video content |
| 4 | Concrete, prioritised takeaways with clear next steps |
| 5 | Concrete, prioritised takeaways AND surfaces second-order implications |

### Total score

`Total = Faithfulness + Coverage + Sourcing + Synthesis + Actionability ∈ [0, 25]`

We report **per-dimension means** and **total mean per task family** in `BENCHMARK.md`. We do NOT collapse to a single overall ranking — the table preserves dimension-level signal so readers can weight differently if they care more about, say, faithfulness than synthesis.

## Annotation process

1. Annotator reads the transcript fully (or skims if they have already watched the video).
2. Annotator writes a private "ground-truth" 1-page reference summary BEFORE seeing any LLM output. This is the anchor.
3. Annotator opens 4 LLM outputs side-by-side, **anonymised** (LLM identity hidden behind a random label `A/B/C/D` per video, key kept in a separate file).
4. Annotator scores each output on each of the 5 dimensions. Total time per `(video, model)` pair: ~10 minutes (so ~13h total for 80 pairs).
5. Identity key is revealed AFTER all 80 pairs are scored. This prevents brand bias.
6. Two annotators rate at least the first 10 pairs each to compute inter-annotator agreement (Krippendorff's α). If α < 0.6 on any dimension, we revisit anchors and re-rate.

For run #1 we use **1 annotator (Maxime) + spot checks on 20% by an external reviewer**. Run #2+ will move to 2 full annotators (already budgeted).

## Files in this directory

| File | Purpose | Status (run #1) |
|---|---|---|
| `README.md` | This document | frozen |
| `videos.csv` | The frozen list of 20 videos (schema above) | written before run start |
| `transcripts/<video_id>.txt` | Frozen transcripts | populated before run start |
| `annotations/run-1/<video_id>__<model>.json` | One annotation file per pair, schema below | populated during day 2 |

### Annotation file schema (`<video_id>__<model>.json`)

```json
{
  "video_id": "tc-01",
  "task_family": "technical_conference",
  "model": "mistral-medium-2508",
  "annotator": "maxime",
  "annotation_timestamp_utc": "2026-05-XXTHH:MM:SSZ",
  "scores": {
    "faithfulness": 4,
    "coverage": 3,
    "sourcing": 2,
    "synthesis": 4,
    "actionability": 3
  },
  "total": 16,
  "comments": "Free-form annotator notes — flagged hallucinations, edge cases, unusually good moments."
}
```

## Reproducibility checklist

A run is reproducible if:

- [x] The 20-video list is frozen and public (`videos.csv` + URLs)
- [x] Transcripts are frozen and public (`transcripts/`)
- [x] Prompts are frozen and public (`benchmark/prompts/`)
- [x] Rubric anchors are public (this file, § "Annotation rubric")
- [x] Annotation files are public (`annotations/run-N/`)
- [x] Aggregation script is public (`benchmark/aggregate.py`)
- [x] All 4 API model identifiers are pinned (e.g. `mistral-medium-2508`, not `mistral-medium-latest`)

If any of the above is missing for a run, that run is **not** reproducible and we treat it as preliminary only.

---

*Last updated: 2026-05-06. Frozen for run #1. Subsequent runs will append to `annotations/run-N/` without modifying this file unless the rubric itself is revised, in which case all prior numbers are re-rated for comparability.*
