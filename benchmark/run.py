#!/usr/bin/env python3
"""
DeepSight Benchmark — run.py

Runs the 4-LLM benchmark over the 20-video corpus declared in dataset/videos.csv.

Production-ready:
  - Idempotent + resumable (skip pairs already in the output CSV when --resume).
  - Exception handling with exponential backoff on rate-limit / transient errors.
  - Structured JSON logging (one record per provider call).
  - tqdm progress bar.
  - --dry-run computes cost estimate without calling APIs.
  - Type hints everywhere; provider clients lazily imported so users don't need all 4 SDKs.

Models (pinned, May 2026):
  - mistral-medium-2508         via mistralai      ($MISTRAL_API_KEY)
  - gpt-4o-mini-2024-07-18      via openai         ($OPENAI_API_KEY)
  - claude-haiku-4-5-20251001   via anthropic      ($ANTHROPIC_API_KEY)
  - gemini-2.0-flash            via google.genai   ($GOOGLE_API_KEY)

CLI:
    python -m benchmark.run \
        --dataset ./dataset/videos.csv \
        --transcripts-dir ./dataset/transcripts \
        --models all \
        --output ./results/run-1-2026-05-DD.csv \
        --resume

    python -m benchmark.run --dry-run     # cost estimate only

Exit codes: 0 success, 1 config error, 2 partial failure (some pairs failed).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

# tqdm is the only required runtime dep beyond stdlib. Provider SDKs are imported lazily.
try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - tqdm is in requirements.txt, but fall back gracefully
    def tqdm(iterable: Iterable, **_kwargs: Any) -> Iterable:
        return iterable


# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens) — pinned to public list price 2026-05-06.
# Update CAREFULLY: this drives the cost estimate and the per-pair cost column.
# ---------------------------------------------------------------------------
PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "mistral-medium-2508":      {"in": 0.40, "out": 2.00},
    "gpt-4o-mini-2024-07-18":   {"in": 0.15, "out": 0.60},
    "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00},
    "gemini-2.0-flash":         {"in": 0.075, "out": 0.30},
}

# Model id -> (provider, sdk-friendly model id). Provider drives env-var + client init.
MODEL_REGISTRY: dict[str, dict[str, str]] = {
    "mistral":   {"provider": "mistral",   "model_id": "mistral-medium-2508",       "env": "MISTRAL_API_KEY"},
    "openai":    {"provider": "openai",    "model_id": "gpt-4o-mini-2024-07-18",    "env": "OPENAI_API_KEY"},
    "anthropic": {"provider": "anthropic", "model_id": "claude-haiku-4-5-20251001", "env": "ANTHROPIC_API_KEY"},
    "google":    {"provider": "google",    "model_id": "gemini-2.0-flash",          "env": "GOOGLE_API_KEY"},
}

# Hard-coded prompts per task. Frozen for run #1 — changing these invalidates comparability.
SYSTEM_PROMPT = (
    "You are an expert video analyst. Given a YouTube transcript, produce a structured "
    "Markdown analysis: 1) Executive summary (3-5 bullets), 2) Key points with timestamps "
    "in [HH:MM:SS] format, 3) Actionable takeaways (3-7 bullets). "
    "Cite timestamps for every claim. Do not hallucinate. If the transcript is unclear "
    "on a point, say so explicitly."
)

USER_PROMPT_TEMPLATE = (
    "Title: {title}\n"
    "Channel: {channel}\n"
    "Duration: {duration_seconds}s\n"
    "Language: {language}\n"
    "Task family: {task_family}\n\n"
    "Transcript:\n"
    "---\n"
    "{transcript}\n"
    "---\n\n"
    "Produce the structured analysis described in the system prompt."
)

OUTPUT_CSV_HEADERS = [
    "video_id",
    "task_family",
    "model",
    "model_id",
    "latency_ms",
    "cost_usd",
    "tokens_in",
    "tokens_out",
    "output_text",
    "status",
    "error",
    "timestamp_utc",
]


# ---------------------------------------------------------------------------
# Logging setup — JSON lines to stderr; readable INFO to stdout via tqdm.
# ---------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Pass-through structured fields if attached via extra={"data": {...}}.
        data = getattr(record, "data", None)
        if data:
            payload.update(data)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(verbose: bool = False) -> logging.Logger:
    log = logging.getLogger("deepsight.benchmark")
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    if not log.handlers:
        log.addHandler(handler)
    return log


# ---------------------------------------------------------------------------
# Dataset I/O
# ---------------------------------------------------------------------------
@dataclass
class Video:
    video_id: str
    task_family: str
    title: str
    channel: str
    url: str
    duration_seconds: int
    language: str
    transcript_path: str
    notes: str = ""

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "Video":
        # Trim whitespace and coerce duration. Raise ValueError early on bad data.
        try:
            duration = int(row["duration_seconds"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"invalid duration for {row.get('video_id')}: {exc}") from exc
        if row.get("language") not in {"en", "fr"}:
            raise ValueError(f"invalid language for {row.get('video_id')}: {row.get('language')!r}")
        return cls(
            video_id=row["video_id"].strip(),
            task_family=row["task_family"].strip(),
            title=row.get("title", "").strip(),
            channel=row.get("channel", "").strip(),
            url=row.get("url", "").strip(),
            duration_seconds=duration,
            language=row["language"].strip(),
            transcript_path=row.get("transcript_path", "").strip(),
            notes=row.get("notes", "").strip(),
        )


def load_videos(dataset_csv: Path) -> list[Video]:
    """Parse dataset/videos.csv into Video objects. Raises FileNotFoundError + ValueError early."""
    if not dataset_csv.exists():
        raise FileNotFoundError(f"dataset CSV not found: {dataset_csv}")
    videos: list[Video] = []
    with dataset_csv.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            videos.append(Video.from_csv_row(row))
    if not videos:
        raise ValueError(f"dataset CSV is empty: {dataset_csv}")
    return videos


def load_transcript(video: Video, transcripts_dir: Path) -> str:
    """Load the frozen transcript for a video. Path resolution rule:
    1. If video.transcript_path is set, treat as relative to the dataset CSV's parent.
    2. Else fall back to <transcripts_dir>/<video_id>.txt.
    """
    candidate = (
        Path(video.transcript_path)
        if video.transcript_path
        else transcripts_dir / f"{video.video_id}.txt"
    )
    if not candidate.is_absolute():
        # Re-anchor relative to transcripts_dir's parent (the dataset/ dir).
        candidate = transcripts_dir.parent / candidate if not candidate.exists() else candidate
    if not candidate.exists():
        raise FileNotFoundError(
            f"transcript missing for {video.video_id}: tried {candidate}"
        )
    return candidate.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    """Cheap token estimate: 1 token ≈ 4 characters for English/French. Good enough for budget math.
    Real usage is read from the SDK response after the call."""
    return max(1, len(text) // 4)


def estimate_cost_usd(model_id: str, tokens_in: int, tokens_out: int) -> float:
    """Compute USD cost for a single call given model id + token counts.

    >>> estimate_cost_usd("mistral-medium-2508", 30000, 3000)
    0.018
    """
    if model_id not in PRICING_USD_PER_MTOK:
        raise KeyError(f"no pricing entry for model {model_id!r}")
    p = PRICING_USD_PER_MTOK[model_id]
    cost = (tokens_in / 1_000_000) * p["in"] + (tokens_out / 1_000_000) * p["out"]
    # Round to 6 decimals for storage; aggregate sums are still accurate to 4-5 sig figs at scale.
    return round(cost, 6)


def estimate_run_cost(
    videos: list[Video],
    transcripts_dir: Path,
    selected_models: list[str],
    avg_output_tokens: int = 3_000,
) -> dict[str, Any]:
    """Walk the dataset and produce a per-model + total cost estimate.

    Used by --dry-run. Reads transcripts to get accurate input token counts; if a transcript is
    missing the call falls back to estimating from duration (1 hour ≈ 12k tokens of speech)."""
    per_model: dict[str, dict[str, float]] = {}
    for key in selected_models:
        spec = MODEL_REGISTRY[key]
        per_model[spec["model_id"]] = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

    total_tokens_in = 0
    for video in videos:
        try:
            transcript = load_transcript(video, transcripts_dir)
            tokens_in_per_call = estimate_tokens(transcript)
        except FileNotFoundError:
            # Fallback: 1h ≈ 12k tokens spoken speech is a defensible heuristic.
            tokens_in_per_call = max(5_000, (video.duration_seconds // 3600 + 1) * 12_000)
        # Add system + user prompt overhead (~300 tokens combined).
        tokens_in_per_call += 300
        total_tokens_in += tokens_in_per_call
        for key in selected_models:
            spec = MODEL_REGISTRY[key]
            entry = per_model[spec["model_id"]]
            entry["tokens_in"] += tokens_in_per_call
            entry["tokens_out"] += avg_output_tokens
            entry["cost_usd"] += estimate_cost_usd(
                spec["model_id"], tokens_in_per_call, avg_output_tokens
            )

    total_cost = sum(m["cost_usd"] for m in per_model.values())
    return {
        "videos": len(videos),
        "models": [MODEL_REGISTRY[k]["model_id"] for k in selected_models],
        "total_input_tokens_per_video_avg": total_tokens_in // max(1, len(videos)),
        "per_model": per_model,
        "total_cost_usd": round(total_cost, 4),
    }


# ---------------------------------------------------------------------------
# Provider call adapters
# ---------------------------------------------------------------------------
@dataclass
class CallResult:
    output_text: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


def _call_mistral(model_id: str, system: str, user: str) -> CallResult:
    from mistralai import Mistral  # type: ignore

    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    t0 = time.perf_counter()
    resp = client.chat.complete(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    tokens_in = getattr(usage, "prompt_tokens", 0) if usage else estimate_tokens(user) + estimate_tokens(system)
    tokens_out = getattr(usage, "completion_tokens", 0) if usage else estimate_tokens(text)
    return CallResult(text, tokens_in, tokens_out, latency_ms)


def _call_openai(model_id: str, system: str, user: str) -> CallResult:
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = resp.choices[0].message.content or ""
    tokens_in = resp.usage.prompt_tokens if resp.usage else estimate_tokens(user) + estimate_tokens(system)
    tokens_out = resp.usage.completion_tokens if resp.usage else estimate_tokens(text)
    return CallResult(text, tokens_in, tokens_out, latency_ms)


def _call_anthropic(model_id: str, system: str, user: str) -> CallResult:
    from anthropic import Anthropic  # type: ignore

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    t0 = time.perf_counter()
    resp = client.messages.create(
        model=model_id,
        system=system,
        max_tokens=4096,
        temperature=0.2,
        messages=[{"role": "user", "content": user}],
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    # Anthropic returns content blocks; concatenate text blocks.
    text_chunks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    text = "".join(text_chunks)
    tokens_in = resp.usage.input_tokens if resp.usage else estimate_tokens(user) + estimate_tokens(system)
    tokens_out = resp.usage.output_tokens if resp.usage else estimate_tokens(text)
    return CallResult(text, tokens_in, tokens_out, latency_ms)


def _call_google(model_id: str, system: str, user: str) -> CallResult:
    import google.generativeai as genai  # type: ignore

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(model_id, system_instruction=system)
    t0 = time.perf_counter()
    resp = model.generate_content(
        user,
        generation_config={"temperature": 0.2, "max_output_tokens": 4096},
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = resp.text or ""
    usage = getattr(resp, "usage_metadata", None)
    tokens_in = getattr(usage, "prompt_token_count", 0) if usage else estimate_tokens(user) + estimate_tokens(system)
    tokens_out = getattr(usage, "candidates_token_count", 0) if usage else estimate_tokens(text)
    return CallResult(text, tokens_in, tokens_out, latency_ms)


PROVIDER_DISPATCH: dict[str, Callable[[str, str, str], CallResult]] = {
    "mistral": _call_mistral,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "google": _call_google,
}


# ---------------------------------------------------------------------------
# Retry wrapper — exponential backoff on transient errors / rate limits.
# ---------------------------------------------------------------------------
def call_with_retry(
    provider: str,
    model_id: str,
    system: str,
    user: str,
    *,
    max_attempts: int = 5,
    log: logging.Logger,
) -> CallResult:
    fn = PROVIDER_DISPATCH[provider]
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(model_id, system, user)
        except Exception as exc:  # noqa: BLE001 — provider SDKs raise heterogeneous exceptions
            last_exc = exc
            cls_name = type(exc).__name__.lower()
            # Heuristic: rate-limit / 5xx / connection errors are retried; auth/4xx aren't.
            is_retryable = any(
                kw in cls_name for kw in ("rate", "timeout", "connection", "apierror", "service")
            ) or "429" in str(exc) or "503" in str(exc) or "502" in str(exc)
            if not is_retryable or attempt == max_attempts:
                log.error(
                    "provider call failed (no retry)",
                    extra={"data": {"provider": provider, "model": model_id, "attempt": attempt, "error": str(exc)}},
                )
                raise
            # Exponential backoff with jitter — base 2s, cap 60s.
            sleep_s = min(60.0, 2.0 ** attempt) + random.uniform(0, 1.5)
            log.warning(
                "provider call retrying",
                extra={"data": {"provider": provider, "model": model_id, "attempt": attempt, "sleep_s": round(sleep_s, 2), "error": str(exc)}},
            )
            time.sleep(sleep_s)
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Output CSV: idempotent append + resume support.
# ---------------------------------------------------------------------------
def load_existing_pairs(output_csv: Path) -> set[tuple[str, str]]:
    """Return the set of (video_id, model_id) already present in output_csv with status=='ok'.
    Used by --resume to skip what's already done."""
    if not output_csv.exists():
        return set()
    done: set[tuple[str, str]] = set()
    with output_csv.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if row.get("status") == "ok":
                done.add((row["video_id"], row["model_id"]))
    return done


def append_row(output_csv: Path, row: dict[str, Any]) -> None:
    """Append one row to the output CSV, creating the file with headers if missing."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    is_new = not output_csv.exists()
    with output_csv.open("a", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=OUTPUT_CSV_HEADERS)
        if is_new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in OUTPUT_CSV_HEADERS})


# ---------------------------------------------------------------------------
# Aggregation — Markdown table for direct paste into BENCHMARK.md
# ---------------------------------------------------------------------------
def aggregate_stats(output_csv: Path) -> dict[str, dict[str, Any]]:
    """Compute per-model aggregates from a completed run CSV."""
    by_model: dict[str, dict[str, Any]] = {}
    if not output_csv.exists():
        return by_model
    with output_csv.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if row.get("status") != "ok":
                continue
            mid = row["model_id"]
            entry = by_model.setdefault(
                mid,
                {"latencies": [], "costs": [], "tokens_in": [], "tokens_out": [], "output_chars": [], "n": 0},
            )
            entry["latencies"].append(int(row["latency_ms"]))
            entry["costs"].append(float(row["cost_usd"]))
            entry["tokens_in"].append(int(row["tokens_in"]))
            entry["tokens_out"].append(int(row["tokens_out"]))
            entry["output_chars"].append(len(row["output_text"]))
            entry["n"] += 1
    return by_model


def _mean(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 3) if xs else 0.0


def _p50(xs: list[int]) -> int:
    if not xs:
        return 0
    s = sorted(xs)
    return s[len(s) // 2]


def render_markdown_table(stats: dict[str, dict[str, Any]]) -> str:
    """Render a Markdown table compatible with replacement in BENCHMARK.md."""
    lines = [
        "| Model | n pairs | Mean latency (ms) | p50 latency (ms) | Total cost (USD) | Mean tokens in | Mean tokens out | Mean output chars |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for mid in sorted(stats):
        s = stats[mid]
        lines.append(
            f"| `{mid}` | {s['n']} | {int(_mean([float(x) for x in s['latencies']]))} "
            f"| {_p50(s['latencies'])} | {round(sum(s['costs']), 4)} "
            f"| {int(_mean([float(x) for x in s['tokens_in']]))} | {int(_mean([float(x) for x in s['tokens_out']]))} "
            f"| {int(_mean([float(x) for x in s['output_chars']]))} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main run loop
# ---------------------------------------------------------------------------
def resolve_models(arg: str) -> list[str]:
    if arg == "all":
        return list(MODEL_REGISTRY.keys())
    keys = [k.strip() for k in arg.split(",") if k.strip()]
    unknown = [k for k in keys if k not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model selector(s): {unknown}. Valid: {list(MODEL_REGISTRY) + ['all']}")
    return keys


def assert_env_keys(model_keys: list[str]) -> None:
    missing = [
        MODEL_REGISTRY[k]["env"]
        for k in model_keys
        if not os.environ.get(MODEL_REGISTRY[k]["env"])
    ]
    if missing:
        raise SystemExit(
            f"missing environment variable(s): {missing}. "
            f"Set them before running, e.g. `export {missing[0]}=...`"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="deepsight-benchmark",
        description="Run the DeepSight 4-LLM benchmark on the 20-video corpus.",
    )
    p.add_argument("--dataset", type=Path, default=Path("./dataset/videos.csv"))
    p.add_argument("--transcripts-dir", type=Path, default=Path("./dataset/transcripts"))
    p.add_argument("--models", type=str, default="all", help="all | comma-separated subset of mistral,openai,anthropic,google")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p.add_argument("--output", type=Path, default=Path(f"./results/run-1-{today}.csv"))
    p.add_argument("--dry-run", action="store_true", help="Print cost estimate and exit, no API calls.")
    p.add_argument("--resume", action="store_true", help="Skip pairs already in --output with status=ok.")
    p.add_argument("--cost-warn-usd", type=float, default=200.0, help="Warn if estimated total cost exceeds this.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log = configure_logging(args.verbose)
    selected = resolve_models(args.models)
    log.info("starting benchmark", extra={"data": {"models": selected, "output": str(args.output)}})

    videos = load_videos(args.dataset)
    log.info("loaded videos", extra={"data": {"n": len(videos)}})

    estimate = estimate_run_cost(videos, args.transcripts_dir, selected)
    print(json.dumps(estimate, indent=2))
    if estimate["total_cost_usd"] > args.cost_warn_usd:
        print(
            f"WARNING: estimated total cost ${estimate['total_cost_usd']} exceeds budget "
            f"of ${args.cost_warn_usd}. Pass --cost-warn-usd to override.",
            file=sys.stderr,
        )

    if args.dry_run:
        log.info("dry-run; exiting")
        return 0

    assert_env_keys(selected)

    done_pairs = load_existing_pairs(args.output) if args.resume else set()
    if args.resume and done_pairs:
        log.info("resuming run", extra={"data": {"already_done": len(done_pairs)}})

    total_pairs = len(videos) * len(selected)
    failures = 0

    pbar = tqdm(total=total_pairs, desc="benchmark", unit="call")
    for video in videos:
        try:
            transcript = load_transcript(video, args.transcripts_dir)
        except FileNotFoundError as exc:
            log.error("transcript missing; skipping video", extra={"data": {"video_id": video.video_id, "error": str(exc)}})
            pbar.update(len(selected))
            failures += len(selected)
            continue

        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=video.title,
            channel=video.channel,
            duration_seconds=video.duration_seconds,
            language=video.language,
            task_family=video.task_family,
            transcript=transcript,
        )

        for key in selected:
            spec = MODEL_REGISTRY[key]
            model_id = spec["model_id"]
            if (video.video_id, model_id) in done_pairs:
                log.debug("skipping done pair", extra={"data": {"video_id": video.video_id, "model_id": model_id}})
                pbar.update(1)
                continue
            row: dict[str, Any] = {
                "video_id": video.video_id,
                "task_family": video.task_family,
                "model": key,
                "model_id": model_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            try:
                result = call_with_retry(spec["provider"], model_id, SYSTEM_PROMPT, user_prompt, log=log)
                row.update(
                    latency_ms=result.latency_ms,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    cost_usd=estimate_cost_usd(model_id, result.tokens_in, result.tokens_out),
                    output_text=result.output_text,
                    status="ok",
                    error="",
                )
                log.info(
                    "pair done",
                    extra={"data": {
                        "video_id": video.video_id, "model_id": model_id,
                        "latency_ms": result.latency_ms, "cost_usd": row["cost_usd"],
                    }},
                )
            except Exception as exc:  # noqa: BLE001
                failures += 1
                row.update(
                    latency_ms=0, tokens_in=0, tokens_out=0, cost_usd=0.0,
                    output_text="", status="error", error=str(exc),
                )
                log.error("pair failed", extra={"data": {"video_id": video.video_id, "model_id": model_id, "error": str(exc)}})
            finally:
                append_row(args.output, row)
                pbar.update(1)
    pbar.close()

    stats = aggregate_stats(args.output)
    md_table = render_markdown_table(stats)
    print("\n=== Aggregate stats (Markdown table) ===\n")
    print(md_table)

    if failures:
        log.warning("run completed with failures", extra={"data": {"failures": failures}})
        return 2
    log.info("run completed cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
