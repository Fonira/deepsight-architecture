# DeepSight — LLM Benchmark Protocol

This document describes how DeepSight benchmarks Mistral against alternative LLMs (OpenAI, Anthropic, Google) on real video analysis tasks.

It is meant to be **honest, reproducible, and fair** — not marketing.

> **Status (2026-05-06)**: This is the **protocol** specification. The first benchmark run is scheduled for end of May 2026. Numerical results below are explicitly marked _not yet measured_. We are publishing the protocol first so the community can audit and challenge the methodology before any numbers are produced — that way you can trust the numbers when they land.

We intend to publish benchmark results quarterly.

## Why we benchmark publicly

DeepSight runs on Mistral. Users in the AI community (especially r/LocalLLaMA, AI Twitter) reasonably ask: *is Mistral really the best choice for this use case, or is it just convenient?*

Three options for answering:

1. **Hand-wave** ("trust us, Mistral is great"). Doesn't work for technical audiences.
2. **Cherry-pick** ("Mistral wins on these 3 tasks!"). Worse — gets demolished publicly when audited.
3. **Publish a fair, reproducible benchmark.** This document.

We chose option 3.

We are **not a neutral party**. We picked Mistral for non-benchmark reasons (EU data sovereignty, cost structure, vendor relationship — see [`README.md`](./README.md)). The benchmark exists to inform users about where Mistral does and doesn't outperform alternatives.

If the benchmark shows Mistral underperforming on a specific task family, we publish that fact. We don't filter results to look favorable. If a future run reveals a regression we need to address (e.g., a new `gpt-4o-mini-2025-XX-XX` is materially better on some task), we publish both the result and our roadmap response.

## Benchmark dimensions

We test 4 LLMs on 4 task families using 20 videos in 2 languages.

### LLMs tested

| LLM | Provider | Model used (May 2026) | Hosting region |
|---|---|---|---|
| Mistral | Mistral AI (FR) | `mistral-medium-2508` | EU (France) |
| OpenAI | OpenAI Inc. (US) | `gpt-4o-mini-2024-07-18` | US |
| Anthropic | Anthropic PBC (US) | `claude-haiku-4-5-20251001` | US |
| Google | Google LLC (US) | `gemini-2.0-flash` | US |

We chose the "small/fast" tier of each provider for fair comparison on cost-sensitive deployments. We don't test the largest tier (`mistral-large` vs `gpt-4o` vs `claude-opus-4-7` vs `gemini-2.0-pro`) because they're not the working models for our €8.99/month Pro tier — but we'll add a Pro/Expert benchmark in Q3 2026.

### Task families

1. **Factual recall** — given a 30-min business interview, can the LLM correctly extract 10 specific quantitative facts (dates, numbers, names) without hallucination?
2. **Synthesis quality** — given a 1-hour academic talk, produce a structured summary. Rated by 3 human evaluators on a 1-5 Likert scale for accuracy, completeness, structure, readability.
3. **Multilingual handling** — same task families 1+2 on French videos (academic + interview). Important because we have a strong French user base.
4. **Reasoning under contradiction** — given debate-style content where speakers disagree, can the LLM correctly attribute claims to speakers and identify the actual point of disagreement?

### Test corpus

- 10 English videos (5 short interviews, 5 long academic talks)
- 10 French videos (5 short interviews, 5 long academic talks)
- All videos publicly available on YouTube under permissive license
- All videos manually annotated by 2 evaluators with ground-truth facts and reference summaries

The corpus will be published on Hugging Face for full reproducibility once annotation is complete. _Hugging Face dataset link: not yet published._

### Metrics

- **Factual accuracy** — % of ground-truth facts correctly extracted
- **Hallucination rate** — % of claimed facts not present in the transcript
- **Synthesis quality score** — averaged human rating (1-5 scale)
- **Latency p50** — median first-token latency
- **Latency p95** — 95th percentile latency (long-tail)
- **Cost per analysis** — token cost in USD/EUR

## Reproducibility

Each benchmark run will be published with:

- The exact prompts used (committed to this repo under `benchmarks/<run-date>/prompts/`)
- The transcripts used (link to Hugging Face dataset)
- The raw LLM outputs (so other evaluators can re-rate them)
- The evaluator scoring rubric
- The Python notebook that generated the final tables

Anyone should be able to re-run the benchmark in roughly 6 hours of LLM API time at an estimated cost of ~$50 USD and verify our numbers.

## Reproducing this benchmark

To reproduce the benchmark, you will need:

| Resource | Status |
|---|---|
| Test corpus (20 annotated videos, EN + FR) | _to be published on Hugging Face — TODO_ |
| Prompt set (4 task families × 4 LLMs) | _to be published in this repo — TODO_ |
| Evaluator rubric (1-5 Likert scale, anchored) | _to be published in this repo — TODO_ |
| Aggregation notebook (Python, pandas) | _to be published in this repo — TODO_ |
| API credentials (Mistral, OpenAI, Anthropic, Google) | bring your own |
| Estimated compute cost | ~$50 USD (4 LLMs × 20 videos × 2 runs) |
| Estimated wall-clock | ~6 hours (mostly LLM latency + human rating) |

Once published, the protocol for a single run will be:

```bash
git clone https://github.com/Fonira/deepsight-architecture
cd deepsight-architecture/benchmarks/<run-date>
pip install -r requirements.txt
export MISTRAL_API_KEY=...
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export GOOGLE_API_KEY=...
python run_benchmark.py --corpus huggingface://deepsight/benchmark-2026-q2
python aggregate_results.py
```

Output: `results.csv` + `results.md` matching the tables in this document.

If anything in the protocol is unclear or unfair, [open an issue](https://github.com/Fonira/deepsight-architecture/issues) and we'll either fix the protocol or document why we kept it as-is.

## Results

> The first benchmark run is scheduled for end of May 2026. Until then, all cells below are explicitly marked _not yet measured_. We are not filling these with estimates or vendor claims.

### Factual recall — English (10 videos)

| LLM | Accuracy | Hallucination rate | Latency p50 | Cost per analysis |
|---|---|---|---|---|
| Mistral medium | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| OpenAI gpt-4o-mini | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Claude Haiku 4.5 | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Gemini 2.0 Flash | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |

### Synthesis quality — English (averaged across 3 evaluators)

| LLM | Accuracy (1-5) | Completeness (1-5) | Structure (1-5) | Readability (1-5) |
|---|---|---|---|---|
| Mistral medium | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| OpenAI gpt-4o-mini | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Claude Haiku 4.5 | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Gemini 2.0 Flash | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |

### Factual recall — French (10 videos)

| LLM | Accuracy | Hallucination rate | Latency p50 | Cost per analysis |
|---|---|---|---|---|
| Mistral medium | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| OpenAI gpt-4o-mini | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Claude Haiku 4.5 | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Gemini 2.0 Flash | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |

### Synthesis quality — French (averaged across 3 evaluators)

| LLM | Accuracy (1-5) | Completeness (1-5) | Structure (1-5) | Readability (1-5) |
|---|---|---|---|---|
| Mistral medium | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| OpenAI gpt-4o-mini | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Claude Haiku 4.5 | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Gemini 2.0 Flash | _not yet measured_ | _not yet measured_ | _not yet measured_ | _not yet measured_ |

### Reasoning under contradiction (debate-style content)

| LLM | Speaker attribution accuracy | Disagreement identification (1-5) | Latency p50 |
|---|---|---|---|
| Mistral medium | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| OpenAI gpt-4o-mini | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Claude Haiku 4.5 | _not yet measured_ | _not yet measured_ | _not yet measured_ |
| Gemini 2.0 Flash | _not yet measured_ | _not yet measured_ | _not yet measured_ |

## Caveats and known limitations

1. **Sample size** — 20 videos is a useful indicator but not a definitive answer. We will increase to 100 videos in Q4 2026.
2. **Ground-truth annotation** — 2 evaluators is below ideal (3+ would reduce annotation noise). We're recruiting more.
3. **Prompt sensitivity** — small prompt changes can shift rankings by 5-10 points. Our prompts are tuned for our use case and may not generalize.
4. **Time decay** — LLM versions change. A benchmark in May 2026 doesn't tell you about November 2026. We re-run quarterly.
5. **Task selection bias** — we benchmark on tasks that matter for DeepSight (video analysis). The numbers will not generalize to coding, math, or other domains.
6. **Cost figures are list price, not effective price** — committed-spend discounts and batch APIs can change the cost picture by 20-50%. We use list prices for fairness.

## How to suggest a task family or video corpus addition

Open an [issue](https://github.com/Fonira/deepsight-architecture/issues) with:

- The task family description
- 5+ example videos under public license
- A proposed evaluation metric

We'll review and add to the next quarterly benchmark run if the proposal is well-formed.

## Acknowledgments

Methodology inspired by:

- HELM (Holistic Evaluation of Language Models, Stanford CRFM)
- Chatbot Arena (LMSYS)
- Long-form summarization eval traditions in the NLP community

We are not affiliated with any of the above. _Specific paper citations to be added in the first published run._

## Compliance and trust

For privacy, subprocessor list, DPA, and GDPR Art 22 disclosure, see [deepsightsynthesis.com/trust](https://deepsightsynthesis.com/trust).

---

*Last updated: 2026-05-06. Protocol-only; first run results scheduled end of May 2026.*

*Code and data for benchmark runs will live under `benchmarks/<run-date>/` in this repo. Hugging Face dataset link will be added once the annotated corpus is published.*

*This document is licensed under [CC BY 4.0](./LICENSE), same as the rest of the repository.*
