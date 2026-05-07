# DeepSight — Architecture Overview

DeepSight is an AI-powered YouTube/TikTok video analysis SaaS, built by Maxime Robathe (DeepSight Synthesis SAS, France) for European users who need source-grounded, nuanced video synthesis with privacy compliance.

This document explains how the stack is built, why we made specific technical choices (Mistral, Hetzner, Vercel), and how DeepSight differs from a "wrapper" around any single LLM API.

## Stack at a glance

```
┌──────────────────────────────────────────────────────────────┐
│  USER SURFACES (TypeScript)                                  │
├──────────────────────────────────────────────────────────────┤
│  • Chrome Extension v2.0 (Webpack 5, MV3)                    │
│  • Mobile App (React Native + Expo SDK 54)                   │
│  • Web App (React 18 + Vite 5)                               │
└──────────────────────────────────────────────────────────────┘
                            │
                  HTTPS + JWT Bearer
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  BACKEND (Python 3.11)                                       │
│  FastAPI async, 4 workers, port 8080                         │
├──────────────────────────────────────────────────────────────┤
│  15 routers: auth, videos, chat, billing, playlists, study,  │
│  academic, debate, history, admin, analytics, batch,         │
│  notifications, search, transcripts                          │
└──────────────────────────────────────────────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  PostgreSQL 17    Redis 7      Mistral AI    Perplexity AI
  (Hetzner DE)   (Hetzner DE)   (France EU)   (US — only for fact-check)
```

All compute and data live in the European Economic Area (Hetzner Falkenstein Germany + Mistral France). The only US dependency is Perplexity (used for optional fact-check enrichment when user activates web search) — which is explicitly opt-in per user/per query.

## Why DeepSight is NOT a Mistral wrapper

**The honest answer**: DeepSight uses Mistral as its LLM, but the value of DeepSight is in everything **around** Mistral, not the LLM call itself.

### What DeepSight adds on top of any LLM

1. **Multi-method transcript extraction** (the hardest problem) — 7 methods in 3 phases:
   - Phase 0: Supadata API (paid, reliable, our priority)
   - Phase 1 (parallel): youtube-transcript-api + 10 Invidious instances + 8 Piped
   - Phase 2 (sequential): yt-dlp manual subtitles + auto-captions
   - Phase 3 (audio STT fallback): Groq Whisper → OpenAI Whisper → Deepgram → AssemblyAI

   With circuit breaker, exponential backoff, health-check instance manager, user-agent rotation, DB cache L2 (chunked + embeddings), 12+ language support. No single LLM API gives you reliable YouTube transcripts.

2. **Hierarchical chunking and analysis pipeline (v6)** — videos are not uniformly long. Our pipeline routes content through 6 duration tiers (sub-15min → 15-30 → 30-60 → 60-120 → 120-240 → 240+) with adaptive chunking strategies. A 4-hour conference doesn't get analyzed like a 5-min short. This is product engineering, not LLM API.

3. **Chat v4.0 with optional Perplexity enrichment** — context-aware: detects when web search is genuinely needed (current events, contradicting claims) vs when video transcript alone suffices. Saves cost and latency when not needed.

4. **Compliance and data sovereignty layer** — EU hosting (Hetzner Germany), Mistral France LLM, encryption at rest (LUKS) and in transit (TLS 1.3), GDPR Art 22 disclosure, subprocessor list (see `/trust`), DPA (Clauses Contractuelles Type EU 2021/914). This is not what a "wrapper" does.

5. **Domain-specific products** built on the analysis primitive:
   - AI Debate (compare 2 videos with opposition + complement + nuance)
   - Quick Voice Call (talk to a video via ElevenLabs voice)
   - Semantic search across user history
   - Mind Maps (Cytoscape graphs)
   - Spaced repetition flashcards
   - Academic paper search linking (arXiv, Crossref, Semantic Scholar, OpenAlex)

A wrapper passes prompts to an API. DeepSight is a video intelligence platform that uses Mistral as one component.

## Why Mistral specifically (vs OpenAI)

We chose Mistral for 4 reasons, in priority order:

### 1. EU data sovereignty for European users (the binding constraint)

Mistral AI is a French company, GDPR-native, with EU data residency by default. For our target users (consultants in EU regulated sectors, researchers, privacy-conscious creators), this is not a "nice-to-have" — it's a binding constraint that disqualifies any US-hosted LLM API.

Concretely: DeepSight customers in banking, insurance, legal, public sector cannot use a tool routing prompts to OpenAI US under their internal compliance policies (DORA, NIS2, sectoral regulations).

### 2. Tiered models per pricing plan, optimized cost/quality

Mistral 2026 catalog (as of May 2026):
- `mistral-small-2603` — Free tier, fast, sufficient for short videos
- `mistral-medium-2508` — Pro tier, good quality/cost ratio
- `mistral-large-2512` — Expert tier, 262K context for long videos
- `magistral-medium-2509` — reasoning model (used for AI Debate)
- `voxtral-mini-2602` — audio model (used for Quick Voice Call)
- `mistral-embed` v23.12 — embeddings for Semantic Search

We use the right model for each task. A 5-min YouTube short doesn't need the same model as a 4-hour conference, and AI Debate reasoning needs a different model than chat enrichment.

### 3. Cost structure compatible with our pricing v2

Mistral's pricing on `mistral-medium` is competitive enough to support our 8.99 €/month Pro tier with healthy margin. OpenAI gpt-4o-mini is also viable but the EU data residency would still be unsolved.

### 4. Active product development from a vendor we can talk to

Mistral has European business hours, French support, and an active roadmap (Voxtral, Magistral, embeddings). We have a direct relationship that an OpenAI-via-Stripe SaaS doesn't give us.

## Why we don't (currently) offer OpenAI alternative

Three reasons:

1. **Coherence of compliance promise** — if we offer "OpenAI fallback" we break the "your data stays in Europe" promise. The promise is the product for a chunk of our market.
2. **Maintenance burden** — supporting two LLM providers means doubling our test surface, prompt tuning, model-specific edge cases.
3. **Honest positioning** — we're not trying to be the lowest common denominator. We're explicitly the European AI YouTube tool.

If a user requires OpenAI specifically, we recommend they use ChatGPT Plus directly. We're not for everyone.

**That said**, our LLM layer is OpenAI SDK compatible (Mistral exposes an OpenAI-format API). If a future Enterprise tier requires customer-side OpenAI keys for legal reasons, the integration cost is hours, not weeks.

## Why Hetzner (vs AWS or GCP)

1. **EU data residency** — Hetzner is German, no Schrems II / Cloud Act concerns. AWS Frankfurt is technically EU but the parent company is subject to US legal compulsion.
2. **Cost** — Hetzner is 5-10× cheaper than AWS for equivalent compute, which lets us keep the 8.99 €/month price point sustainable.
3. **Simplicity** — bare metal-equivalent VPS, Docker stack, Caddy reverse proxy. No vendor lock-in. Migration to OVH or Scaleway possible in days if Hetzner ever fails us.

Tradeoff: less managed services. We run our own PostgreSQL 17, Redis 7, Caddy reverse proxy, monitoring. This is acceptable engineering cost for the price/sovereignty equation.

## Why Vercel for frontend

Vercel for the React/Vite web app, because:

1. **Instant global CDN** — we want the marketing landing fast worldwide
2. **Atomic deployments** — git push → preview URL → promote to prod in minutes
3. **Zero infrastructure management** for static + edge-compute frontend

We don't host backend on Vercel — Functions cold-start and execution limits don't fit our long-running async tasks (4-hour video analysis).

## Pipeline data flow — analyzing a YouTube video

```
1. User pastes URL on web/mobile/extension
   POST /api/videos/analyze {url, mode, model}
                ↓
2. Cache check (L1 Redis + L2 Postgres) — if hit, return immediately
                ↓ (miss)
3. Transcript extraction — 7-method chain with circuit breakers
                ↓
4. Duration-based routing — chunk size & strategy per video length
                ↓
5. Mistral analysis — model selected by user's plan + analysis depth
                ↓
6. Optional fact-check via Perplexity (if user enabled web search)
                ↓
7. Result persistence — Postgres + Redis cache + analytics events
                ↓
8. SSE streaming to frontend with progress updates
```

End-to-end target: 30s for a 5-min video, 2 minutes for a 1-hour video, 8 minutes for a 4-hour conference.

## What's open vs closed

**Open** (this document, GitHub repo):
- Architecture
- Pipeline design and tradeoffs
- Choice of Mistral, Hetzner, Vercel justifications
- Deployment runbook

**Closed** (proprietary):
- Specific prompt engineering for analysis v6 chunking
- Cache key strategy and invalidation logic
- Custom fact-check confidence scoring
- Premium features under active development (planned semi-open after market consolidation)

We're not open-source for the same reason most SaaS aren't — but we believe transparency about architecture builds trust without giving away the product.

## Frequently asked technical questions

### Why isn't DeepSight just an OpenAI wrapper?

Because the value is the pipeline (transcript extraction, chunking, domain features) not the LLM call. And because EU data sovereignty is a binding constraint for our target market. OpenAI cannot satisfy both.

### What happens if Mistral goes down?

Our cache layer absorbs short outages (~5-10 min) for already-analyzed videos. For new analyses, we'd return a 503 with retry guidance until Mistral comes back. We don't currently fail over to another provider — this is a deliberate tradeoff for compliance coherence (see above).

### Is the LLM running locally?

No. Mistral is called via their hosted API. For users who specifically want local LLM inference, we recommend Ollama + LM Studio + a YouTube transcript tool — it's a different product. We may offer Enterprise on-premise deployment later (not on the current roadmap).

### What's the latency overhead of going through your stack?

For a 5-min video on Pro tier (mistral-medium):
- Cache hit: <500ms (Redis lookup + serialization)
- Cache miss, transcript cached: 8-15s (Mistral call)
- Cold (no cache): 25-45s (transcript extraction + Mistral)

We add maybe 500ms-2s of orchestration overhead vs raw Mistral, mostly in transcript reliability and chunking logic. Worth it.

### Can I export my analyses?

Yes — PDF, DOCX, Markdown, XLSX. On Pro tier and above. Notion + Linear integration coming Q3 2026.

### Where can I read the privacy/compliance details?

See [deepsightsynthesis.com/trust](https://deepsightsynthesis.com/trust) (Trust Center) for subprocessor list, DPA, security whitepaper, and GDPR Art 22 disclosure.

### How does Mistral compare to OpenAI / Anthropic / Google on your specific tasks?

We publish a reproducible benchmark protocol comparing Mistral against OpenAI, Anthropic and Google on our actual video-analysis task families. See [BENCHMARK.md](./BENCHMARK.md). The protocol is published first; numerical results from the first run land end of May 2026.

## Get involved

- Bug reports / feature requests: [GitHub Issues](https://github.com/Fonira/deepsight-architecture/issues)
- Direct contact founder: maxime@deepsightsynthesis.com
- Product: [deepsightsynthesis.com](https://deepsightsynthesis.com)

---

*Last updated: 2026-05-06. This document is versioned in [github.com/Fonira/deepsight-architecture](https://github.com/Fonira/deepsight-architecture). PRs welcome on the architecture documentation itself even if the code isn't open-source.*

*Copyright © 2026 Maxime Leparc — Entrepreneur Individuel (SIRET 994 558 898 00015), trading as DeepSight. Licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](./LICENSE).*
