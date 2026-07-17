"""Unit tests for the hf_org_models collector (collectors/collect.py).

Covers only the pure listing→entries mapping (hf_models_to_entries) — the
Hugging Face API HTTP call is exercised by validate_source.py runs, not CI.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collectors"))

import collect  # noqa: E402

NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)


def _model(mid, created="2026-07-16T08:00:00.000Z", likes=0, downloads=0, tag="text-generation", **extra):
    m = {
        "id": mid,
        "createdAt": created,
        "likes": likes,
        "downloads": downloads,
        "pipeline_tag": tag,
    }
    m.update(extra)
    return m


def test_maps_basic_fields():
    entries = collect.hf_models_to_entries([_model("zai-org/GLM-5.2", likes=4030)], "zai-org", NOW)
    assert len(entries) == 1
    e = entries[0]
    assert e["title"] == "zai-org/GLM-5.2 released on Hugging Face"
    assert e["url"] == "https://huggingface.co/zai-org/GLM-5.2"
    assert e["published"] == "2026-07-16T08:00:00.000Z"
    assert "zai-org" in e["summary"]
    assert "text-generation" in e["summary"]


def test_collapses_quant_variant_onto_canonical_repo():
    entries = collect.hf_models_to_entries(
        [_model("zai-org/GLM-5.2", likes=4030), _model("zai-org/GLM-5.2-FP8", likes=215)],
        "zai-org",
        NOW,
    )
    assert [e["url"] for e in entries] == ["https://huggingface.co/zai-org/GLM-5.2"]


def test_prefers_canonical_even_when_variant_listed_first():
    entries = collect.hf_models_to_entries(
        [_model("MiniMaxAI/MiniMax-M3-MXFP8", likes=44), _model("MiniMaxAI/MiniMax-M3", likes=1330)],
        "MiniMaxAI",
        NOW,
    )
    assert [e["url"] for e in entries] == ["https://huggingface.co/MiniMaxAI/MiniMax-M3"]


def test_distinct_models_are_not_collapsed():
    entries = collect.hf_models_to_entries(
        [_model("moonshotai/Kimi-K2.7-Code"), _model("moonshotai/Kimi-K2.6")],
        "moonshotai",
        NOW,
    )
    assert len(entries) == 2


def test_skips_private_and_malformed_rows():
    entries = collect.hf_models_to_entries(
        [
            _model("tencent/Hy-Embodied-VLM-1.0"),
            _model("tencent/secret-model", private=True),
            {"createdAt": "2026-07-16T08:00:00.000Z"},  # no id
            "not-a-dict",
        ],
        "tencent",
        NOW,
    )
    assert [e["url"] for e in entries] == ["https://huggingface.co/tencent/Hy-Embodied-VLM-1.0"]


def test_missing_created_at_falls_back_to_now():
    entries = collect.hf_models_to_entries([_model("Qwen/Qwen4", created="")], "Qwen", NOW)
    assert entries[0]["published"] == NOW.isoformat()
