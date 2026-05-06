"""Tests for benchmark/run.py.

Required by the spec:
  1. CSV parsing (load_videos / Video.from_csv_row)
  2. Cost estimate (estimate_cost_usd / estimate_run_cost)

Plus a few extras to keep the suite useful (resume detection, model resolution).

Run:
    cd benchmark && pytest -q
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from benchmark.run import (
    MODEL_REGISTRY,
    PRICING_USD_PER_MTOK,
    Video,
    aggregate_stats,
    append_row,
    estimate_cost_usd,
    estimate_run_cost,
    load_existing_pairs,
    load_videos,
    render_markdown_table,
    resolve_models,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SAMPLE_HEADERS = [
    "video_id", "task_family", "title", "channel", "url",
    "duration_seconds", "language", "transcript_path", "notes",
]
SAMPLE_ROWS = [
    {
        "video_id": "tc-01", "task_family": "technical_conference",
        "title": "The Foundations of LLM Scaling", "channel": "Stanford MLSys Seminar",
        "url": "https://www.youtube.com/watch?v=AaTRHFaaPG8",
        "duration_seconds": "6300", "language": "en",
        "transcript_path": "transcripts/tc-01.txt", "notes": "scaling laws recall",
    },
    {
        "video_id": "bp-04", "task_family": "business_podcast",
        "title": "GDIY — Octave Klaba", "channel": "Matthieu Stefani",
        "url": "https://www.youtube.com/watch?v=8rR6gEvZeC0",
        "duration_seconds": "7200", "language": "fr",
        "transcript_path": "", "notes": "OVH founder",
    },
]


@pytest.fixture
def videos_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "videos.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=SAMPLE_HEADERS)
        writer.writeheader()
        for row in SAMPLE_ROWS:
            writer.writerow(row)
    return csv_path


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------
class TestVideoFromCsvRow:
    def test_minimal_valid_row(self) -> None:
        v = Video.from_csv_row({
            "video_id": "x-1", "task_family": "tutorial_howto",
            "title": "T", "channel": "C", "url": "https://x",
            "duration_seconds": "100", "language": "en",
            "transcript_path": "", "notes": "",
        })
        assert v.video_id == "x-1"
        assert v.duration_seconds == 100
        assert v.language == "en"

    def test_strips_whitespace(self) -> None:
        v = Video.from_csv_row({
            "video_id": "  x-1 ", "task_family": " technical_conference ",
            "title": " Title ", "channel": " ", "url": " ",
            "duration_seconds": "50", "language": "fr",
            "transcript_path": "", "notes": "",
        })
        assert v.video_id == "x-1"
        assert v.task_family == "technical_conference"
        assert v.title == "Title"

    def test_invalid_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid duration"):
            Video.from_csv_row({
                "video_id": "x-1", "task_family": "x",
                "title": "T", "channel": "C", "url": "u",
                "duration_seconds": "not-a-number", "language": "en",
                "transcript_path": "", "notes": "",
            })

    def test_invalid_language_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid language"):
            Video.from_csv_row({
                "video_id": "x-1", "task_family": "x",
                "title": "T", "channel": "C", "url": "u",
                "duration_seconds": "10", "language": "es",
                "transcript_path": "", "notes": "",
            })


class TestLoadVideos:
    def test_loads_two_rows(self, videos_csv: Path) -> None:
        videos = load_videos(videos_csv)
        assert len(videos) == 2
        assert videos[0].video_id == "tc-01"
        assert videos[1].video_id == "bp-04"
        assert videos[0].duration_seconds == 6300
        assert videos[1].language == "fr"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_videos(tmp_path / "missing.csv")

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.csv"
        with empty.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=SAMPLE_HEADERS)
            writer.writeheader()
        with pytest.raises(ValueError, match="empty"):
            load_videos(empty)


# ---------------------------------------------------------------------------
# Cost estimate
# ---------------------------------------------------------------------------
class TestEstimateCostUsd:
    def test_mistral_small(self) -> None:
        # 30k in × $0.40/Mtok + 3k out × $2/Mtok = 0.012 + 0.006 = 0.018
        assert estimate_cost_usd("mistral-medium-2508", 30_000, 3_000) == pytest.approx(0.018)

    def test_anthropic_haiku_small(self) -> None:
        # 30k in × $1/Mtok + 3k out × $5/Mtok = 0.03 + 0.015 = 0.045
        assert estimate_cost_usd("claude-haiku-4-5-20251001", 30_000, 3_000) == pytest.approx(0.045)

    def test_gemini_cheapest(self) -> None:
        # 30k × 0.075 + 3k × 0.30 = 0.00225 + 0.0009 = 0.003150
        cost = estimate_cost_usd("gemini-2.0-flash", 30_000, 3_000)
        assert cost == pytest.approx(0.003150, rel=1e-3)

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(KeyError, match="no pricing entry"):
            estimate_cost_usd("not-a-real-model", 100, 100)

    def test_zero_tokens(self) -> None:
        assert estimate_cost_usd("mistral-medium-2508", 0, 0) == 0.0

    @pytest.mark.parametrize("model_id", list(PRICING_USD_PER_MTOK.keys()))
    def test_all_models_have_pricing(self, model_id: str) -> None:
        cost = estimate_cost_usd(model_id, 1_000_000, 1_000_000)
        # Sanity: cost = price_in + price_out for 1M+1M tokens.
        expected = PRICING_USD_PER_MTOK[model_id]["in"] + PRICING_USD_PER_MTOK[model_id]["out"]
        assert cost == pytest.approx(expected)


class TestEstimateRunCost:
    def test_run_cost_falls_back_when_transcript_missing(self, videos_csv: Path, tmp_path: Path) -> None:
        videos = load_videos(videos_csv)
        # No transcripts dir populated → fallback heuristic kicks in.
        empty_transcripts = tmp_path / "transcripts"
        empty_transcripts.mkdir()
        estimate = estimate_run_cost(videos, empty_transcripts, ["mistral", "openai"])
        assert estimate["videos"] == 2
        assert len(estimate["per_model"]) == 2
        # Total cost is positive and bounded — sanity only.
        assert 0.0 < estimate["total_cost_usd"] < 200.0
        # Both models present.
        assert "mistral-medium-2508" in estimate["per_model"]
        assert "gpt-4o-mini-2024-07-18" in estimate["per_model"]

    def test_run_cost_uses_real_transcripts_when_present(self, videos_csv: Path, tmp_path: Path) -> None:
        videos = load_videos(videos_csv)
        # Populate one transcript ~ 4k chars (~1k tokens).
        dataset_root = videos_csv.parent
        (dataset_root / "transcripts").mkdir()
        (dataset_root / "transcripts" / "tc-01.txt").write_text("a" * 4000, encoding="utf-8")
        # Also populate the bp-04 one (no transcript_path → fallback to <transcripts>/<id>.txt).
        (dataset_root / "transcripts" / "bp-04.txt").write_text("b" * 4000, encoding="utf-8")
        estimate = estimate_run_cost(videos, dataset_root / "transcripts", ["mistral"])
        # Each transcript is ~1k tokens + 300 prompt overhead = ~1300 tokens × 2 videos = ~2600.
        # Across 2 videos × 1 model that should land well under $1.
        assert estimate["total_cost_usd"] < 1.0


# ---------------------------------------------------------------------------
# Resume + aggregation
# ---------------------------------------------------------------------------
class TestResumeAndAggregate:
    def test_load_existing_pairs_skips_errors(self, tmp_path: Path) -> None:
        out = tmp_path / "results.csv"
        append_row(out, {
            "video_id": "tc-01", "task_family": "technical_conference",
            "model": "mistral", "model_id": "mistral-medium-2508",
            "latency_ms": 1200, "cost_usd": 0.018, "tokens_in": 30000, "tokens_out": 3000,
            "output_text": "stuff", "status": "ok", "error": "", "timestamp_utc": "2026-05-06T00:00:00Z",
        })
        append_row(out, {
            "video_id": "tc-01", "task_family": "technical_conference",
            "model": "openai", "model_id": "gpt-4o-mini-2024-07-18",
            "latency_ms": 0, "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0,
            "output_text": "", "status": "error", "error": "boom",
            "timestamp_utc": "2026-05-06T00:00:00Z",
        })
        done = load_existing_pairs(out)
        assert ("tc-01", "mistral-medium-2508") in done
        assert ("tc-01", "gpt-4o-mini-2024-07-18") not in done  # error rows are NOT skipped

    def test_aggregate_and_render(self, tmp_path: Path) -> None:
        out = tmp_path / "results.csv"
        for i in range(3):
            append_row(out, {
                "video_id": f"v-{i}", "task_family": "tutorial_howto",
                "model": "mistral", "model_id": "mistral-medium-2508",
                "latency_ms": 1000 + i * 100, "cost_usd": 0.01,
                "tokens_in": 30000, "tokens_out": 3000,
                "output_text": "x" * 500, "status": "ok", "error": "",
                "timestamp_utc": "2026-05-06T00:00:00Z",
            })
        stats = aggregate_stats(out)
        assert "mistral-medium-2508" in stats
        s = stats["mistral-medium-2508"]
        assert s["n"] == 3
        assert sorted(s["latencies"]) == [1000, 1100, 1200]
        md = render_markdown_table(stats)
        assert "mistral-medium-2508" in md
        assert "| 3 |" in md  # n=3 column


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
class TestResolveModels:
    def test_all(self) -> None:
        assert sorted(resolve_models("all")) == sorted(MODEL_REGISTRY.keys())

    def test_subset(self) -> None:
        assert resolve_models("mistral,openai") == ["mistral", "openai"]

    def test_unknown_exits(self) -> None:
        with pytest.raises(SystemExit):
            resolve_models("not-a-provider")
