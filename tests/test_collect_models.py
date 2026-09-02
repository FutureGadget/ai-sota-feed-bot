"""Unit tests for the Model Release Radar collector (pipeline/collect_models.py).

Covers only the pure normalize/merge/join/select logic - the LMArena and
Artificial Analysis HTTP calls are exercised manually against live
endpoints, not in CI.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import collect_models as cm  # noqa: E402


# ---------------------------------------------------------------------------
# normalize_slug
# ---------------------------------------------------------------------------

def test_normalize_slug_lowercases_and_strips_punctuation():
    assert cm.normalize_slug("Claude-Opus-5-Max") == "claudeopus5max"


def test_normalize_slug_collapses_separator_style_differences():
    assert cm.normalize_slug("GPT-5.6 Sol") == cm.normalize_slug("gpt_5_6_sol")


def test_normalize_slug_handles_none_and_empty():
    assert cm.normalize_slug(None) == ""
    assert cm.normalize_slug("") == ""


# ---------------------------------------------------------------------------
# derive_base_variant (Problem 1: variant-spam collapsing)
# ---------------------------------------------------------------------------

# Same shape as the real variant_vocabulary block in config/models.yaml -
# kept as a local fixture so these tests pin the *contract* Python code
# relies on, independent of how the live config happens to be tuned.
VARIANT_VOCAB = {
    "tokens": {
        "low": "low",
        "medium": "medium",
        "med": "medium",
        "high": "high",
        "xhigh": "xhigh",
        "max": "max",
        "min": "minimal",
        "minimal": "minimal",
        "thinking": "thinking",
        "thinkingminimal": "thinking-minimal",
        "nonthinking": "non-thinking",
        "nothinking": "non-thinking",
        "nonreasoning": "non-reasoning",
        "reasoning": "reasoning",
    },
    "effort_phrases": [
        {"pattern": r"^adaptive reasoning,\s*(?P<level>[a-z]+)\s*effort$"},
        {"pattern": r"^non-reasoning,\s*[a-z]+\s*effort$", "variant": "non-reasoning"},
    ],
    "ignorable_qualifiers": [r"^(?:[a-z0-9][a-z0-9.\- ]*\s+)?fallback$"],
}

# Same shape as the real acronym_casing block in config/models.yaml - see
# derive_display_name tests below.
ACRONYM_CASING = {
    "gpt": "GPT",
    "glm": "GLM",
    "deepseek": "DeepSeek",
    "k2": "K2",
    "k3": "K3",
    "o3": "o3",
    "xai": "xAI",
}


def test_derive_base_variant_aa_parenthetical_convention():
    # "GPT-5.6 Sol (medium)" -> base "gpt56sol", variant "medium" - the exact
    # example from the Model Release Radar variant-spam bug report.
    assert cm.derive_base_variant("GPT-5.6 Sol (medium)", VARIANT_VOCAB) == ("gpt56sol", "medium")


def test_derive_base_variant_aa_adaptive_reasoning_phrase():
    assert cm.derive_base_variant(
        "Claude Opus 5 (Adaptive Reasoning, High Effort)", VARIANT_VOCAB
    ) == ("claudeopus5", "high")


def test_derive_base_variant_non_reasoning_effort_phrase_collapses_to_non_reasoning():
    # The reasoning-on/off distinction is the salient one here, not the
    # effort level named alongside it in the same parenthetical.
    assert cm.derive_base_variant(
        "Claude Sonnet 5 (Non-reasoning, High Effort)", VARIANT_VOCAB
    ) == ("claudesonnet5", "non-reasoning")


def test_derive_base_variant_lmarena_suffix_convention():
    # "gpt-5.6-sol-xhigh" -> the same base as the AA parenthetical form above,
    # because both name the same underlying model.
    assert cm.derive_base_variant("gpt-5.6-sol-xhigh", VARIANT_VOCAB) == ("gpt56sol", "xhigh")


def test_derive_base_variant_lmarena_multiword_suffix():
    assert cm.derive_base_variant("claude-opus-4-6-thinking", VARIANT_VOCAB) == ("claudeopus46", "thinking")


def test_derive_base_variant_both_conventions_agree_on_the_same_base():
    paren_base, _ = cm.derive_base_variant("GPT-5.6 Sol (medium)", VARIANT_VOCAB)
    suffix_base, _ = cm.derive_base_variant("gpt-5.6-sol-xhigh", VARIANT_VOCAB)
    assert paren_base == suffix_base == "gpt56sol"


def test_derive_base_variant_bare_reasoning_phrase_without_adaptive_prefix():
    # AA phrases some rows "Reasoning, Max Effort" (no "Adaptive" prefix) -
    # verified live 2026-08-05 against DeepSeek V4 Flash/Pro. Same effort
    # level extraction as the "Adaptive Reasoning, X Effort" phrase, via a
    # separate, more specific-first pattern so it never intercepts that one.
    vocab = dict(VARIANT_VOCAB, effort_phrases=VARIANT_VOCAB["effort_phrases"] + [
        {"pattern": r"^reasoning,\s*(?P<level>[a-z]+)\s*effort$"},
    ])
    assert cm.derive_base_variant("DeepSeek V4 Flash 0731 (Reasoning, Max Effort)", vocab) == (
        cm.normalize_slug("DeepSeek V4 Flash 0731"), "max",
    )
    # The more specific "adaptive reasoning" pattern still wins when present.
    assert cm.derive_base_variant("Claude Opus 5 (Adaptive Reasoning, High Effort)", vocab) == (
        "claudeopus5", "high",
    )


def test_derive_base_variant_ignores_a_trailing_configuration_clause():
    # Regression (live 2026-09-01): AA started appending a fallback clause to
    # the effort parenthetical it has always published. The three-clause text
    # matched no effort_phrases pattern, so each effort level kept the whole
    # parenthetical in its base_slug and /models listed five separate
    # "Claude Fable 5.1" rows instead of one with a "+4 variants" badge.
    for level, label in (
        ("High", "high"),
        ("Low", "low"),
        ("Max", "max"),
        ("Medium", "medium"),
        ("Xhigh", "xhigh"),
    ):
        name = f"Claude Fable 5.1 (Adaptive Reasoning, {level} Effort, Default Fallback)"
        assert cm.derive_base_variant(name, VARIANT_VOCAB) == ("claudefable51", label)


def test_derive_base_variant_ignores_a_model_named_fallback_clause():
    # The clause names the model that answers when the primary is
    # unavailable - a routing detail, not this row's identity.
    assert cm.derive_base_variant(
        "Claude Fable 5 (Adaptive Reasoning, Max Effort, Opus 4.8 Fallback)", VARIANT_VOCAB
    ) == ("claudefable5", "max")


def test_derive_base_variant_configuration_clause_does_not_break_literal_phrases():
    # "Non-reasoning, X Effort" collapses to non-reasoning regardless of the
    # effort named alongside it - and regardless of a trailing fallback clause.
    assert cm.derive_base_variant(
        "Claude Sonnet 5 (Non-reasoning, High Effort, Default Fallback)", VARIANT_VOCAB
    ) == ("claudesonnet5", "non-reasoning")


def test_derive_base_variant_configuration_clause_alone_is_still_not_a_variant():
    # Dropping the qualifier leaves nothing to match: no variant is invented,
    # and the parenthetical stays part of the base rather than being guessed away.
    base, variant = cm.derive_base_variant("Claude Fable 5.1 (Default Fallback)", VARIANT_VOCAB)
    assert variant is None
    assert base == cm.normalize_slug("Claude Fable 5.1 (Default Fallback)")


def test_derive_base_variant_never_drops_an_unconfigured_clause():
    # Only a clause matching a configured pattern is ever dropped - an
    # identity-bearing clause keeps the whole parenthetical unrecognized.
    base, variant = cm.derive_base_variant(
        "Claude Fable 5.1 (Adaptive Reasoning, High Effort, June 2026)", VARIANT_VOCAB
    )
    assert variant is None
    assert base == cm.normalize_slug("Claude Fable 5.1 (Adaptive Reasoning, High Effort, June 2026)")


def test_derive_display_name_strips_effort_phrase_with_configuration_clause():
    assert cm.derive_display_name(
        "claude-fable-5-1-high",
        "Claude Fable 5.1 (Adaptive Reasoning, High Effort, Default Fallback)",
        VARIANT_VOCAB,
        {},
    ) == "Claude Fable 5.1"


def test_derive_base_variant_never_strips_an_unrecognized_suffix():
    # "-lite" is a real Gemini model-size tier, not a reasoning effort - it
    # must never be stripped just because it sits at the end of the name.
    base, variant = cm.derive_base_variant("gemini-3.5-flash-lite", VARIANT_VOCAB)
    assert variant is None
    assert base == cm.normalize_slug("gemini-3.5-flash-lite")


def test_derive_base_variant_never_strips_an_unrecognized_parenthetical():
    # "(Beta)" is a maturity label, not a recognized variant token.
    base, variant = cm.derive_base_variant("Motif 3 (Beta)", VARIANT_VOCAB)
    assert variant is None
    assert base == cm.normalize_slug("Motif 3 (Beta)")


def test_derive_base_variant_never_strips_a_dated_snapshot_parenthetical():
    base, variant = cm.derive_base_variant("GPT-5.5 Instant (June 2026)", VARIANT_VOCAB)
    assert variant is None
    assert base == cm.normalize_slug("GPT-5.5 Instant (June 2026)")


def test_derive_base_variant_empty_vocabulary_never_strips_anything():
    # No config loaded (or an empty vocabulary block): every name passes
    # through untouched rather than being guessed at.
    assert cm.derive_base_variant("gpt-5.6-sol-xhigh", {}) == (cm.normalize_slug("gpt-5.6-sol-xhigh"), None)
    assert cm.derive_base_variant("GPT-5.6 Sol (medium)", None) == (cm.normalize_slug("GPT-5.6 Sol (medium)"), None)


def test_derive_base_variant_handles_none_and_empty_name():
    assert cm.derive_base_variant(None, VARIANT_VOCAB) == ("", None)
    assert cm.derive_base_variant("", VARIANT_VOCAB) == ("", None)


# ---------------------------------------------------------------------------
# zero_price_to_null (Problem 2: $0.00 is "undisclosed", not "free")
# ---------------------------------------------------------------------------

def test_zero_price_to_null_converts_exact_zero():
    assert cm.zero_price_to_null(0) is None
    assert cm.zero_price_to_null(0.0) is None


def test_zero_price_to_null_leaves_real_prices_alone():
    assert cm.zero_price_to_null(0.01) == 0.01
    assert cm.zero_price_to_null(5.0) == 5.0


def test_zero_price_to_null_passes_through_none():
    assert cm.zero_price_to_null(None) is None


def test_zero_price_to_null_defensive_against_non_numeric():
    assert cm.zero_price_to_null("undisclosed") == "undisclosed"


# ---------------------------------------------------------------------------
# blended_price
# ---------------------------------------------------------------------------

def test_blended_price_uses_3to1_input_output_weight():
    # (3 * 2.0 + 1 * 6.0) / 4 = 3.0
    assert cm.blended_price(2.0, 6.0) == 3.0


def test_blended_price_none_when_either_input_missing():
    assert cm.blended_price(None, 1.0) is None
    assert cm.blended_price(1.0, None) is None


# ---------------------------------------------------------------------------
# round_or_none
# ---------------------------------------------------------------------------

def test_round_or_none_rounds_and_passes_through_none():
    assert cm.round_or_none(1507.264, 2) == 1507.26
    assert cm.round_or_none(None, 2) is None
    assert cm.round_or_none("not-a-number", 2) is None


# ---------------------------------------------------------------------------
# classify_open_weights
# ---------------------------------------------------------------------------

DEFAULT_CLASSIFICATION_CFG = cm.DEFAULT_CONFIG["license_classification"]

# The 12 distinct LMArena license strings observed live in the artifact
# (2026-08-05), with their expected open_weights classification. Everything
# is open except "Proprietary".
LIVE_LICENSE_VALUES = [
    ("Proprietary", False),
    ("MIT", True),
    ("Apache 2.0", True),
    ("Modified MIT", True),
    ("NVIDIA Open Model", True),
    ("Gemma", True),
    ("OpenMDW-1.1", True),
    ("MiniMax Community License", True),
    ("tencent-hunyuan-community", True),
    ("Nvidia Open", True),
    ("DeepSeek", True),
    ("CC-BY-NC-4.0", True),
]


def test_classify_open_weights_explicit_aa_bool_wins_over_license():
    # AA says proprietary=False (open) even though the license string alone
    # would classify as proprietary - AA is authoritative when present.
    assert cm.classify_open_weights("Proprietary", True, DEFAULT_CLASSIFICATION_CFG) is True
    assert cm.classify_open_weights("MIT", False, DEFAULT_CLASSIFICATION_CFG) is False


def test_classify_open_weights_maps_each_live_license_value():
    for license_value, expected in LIVE_LICENSE_VALUES:
        assert cm.classify_open_weights(license_value, None, DEFAULT_CLASSIFICATION_CFG) is expected, license_value


def test_classify_open_weights_is_case_insensitive():
    assert cm.classify_open_weights("PROPRIETARY", None, DEFAULT_CLASSIFICATION_CFG) is False
    assert cm.classify_open_weights("proprietary", None, DEFAULT_CLASSIFICATION_CFG) is False
    assert cm.classify_open_weights("PrOpRiEtArY LiCeNsE", None, DEFAULT_CLASSIFICATION_CFG) is False


def test_classify_open_weights_unknown_marker_returns_null_not_open():
    assert cm.classify_open_weights("Unknown", None, DEFAULT_CLASSIFICATION_CFG) is None
    assert cm.classify_open_weights("License Unspecified", None, DEFAULT_CLASSIFICATION_CFG) is None


def test_classify_open_weights_missing_license_is_null():
    assert cm.classify_open_weights(None, None, DEFAULT_CLASSIFICATION_CFG) is None
    assert cm.classify_open_weights("", None, DEFAULT_CLASSIFICATION_CFG) is None


def test_classify_open_weights_defaults_classification_cfg_when_omitted():
    # No classification_cfg passed at all -> treated as empty -> never
    # guesses proprietary, only None (missing) or True (any non-empty
    # license), matching the "no config drives no denylist" contract.
    assert cm.classify_open_weights("Proprietary", None) is True
    assert cm.classify_open_weights(None, None) is None


# ---------------------------------------------------------------------------
# merge_lmarena_rows
# ---------------------------------------------------------------------------

def test_merge_lmarena_rows_combines_overall_and_coding():
    rows_by_category = {
        "overall": [
            {
                "model_name": "claude-opus-5-max",
                "organization": "anthropic",
                "license": "Proprietary",
                "rating": 1507.26,
                "rank": 1.0,
                "vote_count": 5124.0,
                "leaderboard_publish_date": "2026-08-03",
            }
        ],
        "coding": [
            {
                "model_name": "claude-opus-5-max",
                "organization": "anthropic",
                "license": "Proprietary",
                "rating": 1535.36,
                "rank": 2.0,
                "vote_count": 900.0,
                "leaderboard_publish_date": "2026-08-03",
            }
        ],
    }
    idx = cm.merge_lmarena_rows(rows_by_category)
    assert set(idx) == {"claudeopus5max"}
    entry = idx["claudeopus5max"]
    assert entry["name"] == "claude-opus-5-max"
    assert entry["organization"] == "anthropic"
    assert entry["arena_elo_overall"] == 1507.26
    assert entry["arena_elo_coding"] == 1535.36
    assert entry["arena_rank_overall"] == 1.0
    assert entry["arena_rank_coding"] == 2.0
    # Overall vote_count wins when both categories report one.
    assert entry["arena_votes"] == 5124.0


def test_merge_lmarena_rows_keeps_coding_only_model_with_null_overall():
    rows_by_category = {
        "overall": [],
        "coding": [
            {
                "model_name": "some-coder",
                "organization": "acme",
                "license": "MIT",
                "rating": 1400.0,
                "rank": 5.0,
                "vote_count": 300.0,
                "leaderboard_publish_date": "2026-08-01",
            }
        ],
    }
    idx = cm.merge_lmarena_rows(rows_by_category)
    entry = idx["somecoder"]
    assert entry["arena_elo_overall"] is None
    assert entry["arena_elo_coding"] == 1400.0
    assert entry["arena_votes"] == 300.0


def test_merge_lmarena_rows_skips_blank_model_name():
    rows_by_category = {"overall": [{"model_name": "", "rating": 1.0}]}
    idx = cm.merge_lmarena_rows(rows_by_category)
    assert idx == {}


# ---------------------------------------------------------------------------
# extract_aa_field / build_aa_index
# ---------------------------------------------------------------------------

def test_extract_aa_field_probes_nested_paths():
    model = {"evaluations": {"artificial_analysis_coding_index": 72.5}}
    value, found = cm.extract_aa_field(model, "aa_coding_index")
    assert found is True
    assert value == 72.5


def test_extract_aa_field_reports_not_found():
    value, found = cm.extract_aa_field({"unrelated": 1}, "aa_coding_index")
    assert found is False
    assert value is None


# ---------------------------------------------------------------------------
# extract_aa_benchmarks (Step 9: raw per-benchmark scores)
# ---------------------------------------------------------------------------

def test_extract_aa_benchmarks_pulls_only_the_configured_names():
    raw = {"evaluations": {"livecodebench": 0.878, "tau2": 0.657, "gpqa": 0.782}}
    out = cm.extract_aa_benchmarks(raw, ["livecodebench", "tau2"])
    assert out == {"livecodebench": 0.878, "tau2": 0.657}
    assert "gpqa" not in out


def test_extract_aa_benchmarks_omits_a_null_score_never_zero_fills():
    raw = {"evaluations": {"livecodebench": 0.878, "tau2": None}}
    out = cm.extract_aa_benchmarks(raw, ["livecodebench", "tau2"])
    assert out == {"livecodebench": 0.878}
    assert "tau2" not in out


def test_extract_aa_benchmarks_omits_a_name_absent_from_evaluations_entirely():
    raw = {"evaluations": {"livecodebench": 0.878}}
    out = cm.extract_aa_benchmarks(raw, ["livecodebench", "scicode"])
    assert out == {"livecodebench": 0.878}


def test_extract_aa_benchmarks_no_configured_names_yields_empty_dict():
    raw = {"evaluations": {"livecodebench": 0.878}}
    assert cm.extract_aa_benchmarks(raw, []) == {}
    assert cm.extract_aa_benchmarks(raw, None) == {}


def test_extract_aa_benchmarks_model_with_no_evaluations_block_yields_empty_dict():
    assert cm.extract_aa_benchmarks({"slug": "x"}, ["livecodebench"]) == {}


def test_build_aa_index_populates_benchmarks_per_configured_name():
    raw = [{"slug": "m1", "name": "Model 1", "evaluations": {"livecodebench": 0.878, "tau2": None}}]
    idx, _missing = cm.build_aa_index(raw, benchmark_names=["livecodebench", "tau2", "scicode"])
    assert idx["m1"]["benchmarks"] == {"livecodebench": 0.878}


def test_build_aa_index_benchmarks_default_to_empty_dict_without_benchmark_names():
    raw = [{"slug": "m1", "name": "Model 1", "evaluations": {"livecodebench": 0.878}}]
    idx, _missing = cm.build_aa_index(raw)
    assert idx["m1"]["benchmarks"] == {}


def test_build_aa_index_keys_by_normalized_slug_and_flags_missing_fields():
    raw = [
        {
            "name": "gpt-5-6-sol",
            "release_date": "2026-07-01",
            "pricing": {"price_1m_input_tokens": 1.5, "price_1m_output_tokens": 4.5},
        }
    ]
    idx, missing = cm.build_aa_index(raw)
    assert set(idx) == {"gpt56sol"}
    entry = idx["gpt56sol"]
    assert entry["release_date"] == "2026-07-01"
    assert entry["price_input_per_1m"] == 1.5
    assert entry["price_output_per_1m"] == 4.5
    # No candidate path in the fixture ever supplies these fields.
    assert "context_window_tokens" in missing
    assert "aa_intelligence_index" in missing


def test_build_aa_index_empty_input_yields_no_missing_fields():
    idx, missing = cm.build_aa_index([])
    assert idx == {}
    assert missing == set()


def test_build_aa_index_keys_by_both_slug_and_name():
    # AA's slug carries the variant ("gpt-5-6-sol-medium"); its verbose name
    # carries it too, in parentheses - both normalized keys should resolve
    # to the same record.
    raw = [{"slug": "gpt-5-6-sol-medium", "name": "GPT-5.6 Sol (medium)"}]
    idx, _missing = cm.build_aa_index(raw)
    assert set(idx) == {"gpt56solmedium"}
    assert idx["gpt56solmedium"]["slug"] == "gpt56solmedium"


def test_build_aa_index_name_key_never_overwrites_slug_key():
    # Model A's slug normalizes to the same key that model B's name would
    # also normalize to. The slug pass runs first and claims the key, so
    # model B's name-derived write must never clobber model A's entry.
    raw = [
        {"slug": "claude-opus-5-high", "name": "Claude Opus 5 (Adaptive Reasoning, High Effort)"},
        {"slug": "some-other-model", "name": "claude opus 5 high"},
    ]
    idx, _missing = cm.build_aa_index(raw)
    key = cm.normalize_slug("claude-opus-5-high")
    assert idx[key]["slug"] == "claudeopus5high"


def test_build_aa_index_first_model_keeps_a_contested_key_within_a_pass():
    # Two AA models whose slugs normalize identically (a genuine collision):
    # the first one processed keeps the key rather than being silently
    # replaced by the second.
    raw = [
        {"slug": "dup-model", "name": "Dup Model First"},
        {"slug": "dup_model", "name": "Dup Model Second"},
    ]
    idx, _missing = cm.build_aa_index(raw)
    assert idx["dupmodel"]["name"] == "Dup Model First"


def test_build_aa_index_populates_organization_from_model_creator_slug():
    raw = [{"slug": "gpt-oss-120b", "name": "gpt-oss-120b", "model_creator": {"name": "OpenAI", "slug": "openai"}}]
    idx, _missing = cm.build_aa_index(raw)
    assert idx["gptoss120b"]["organization"] == "openai"


def test_build_aa_index_extracts_verified_field_paths():
    raw = [
        {
            "slug": "gpt-oss-120b",
            "name": "gpt-oss-120b (high)",
            "release_date": "2025-08-05",
            "model_creator": {"id": "x", "name": "OpenAI", "slug": "openai"},
            "evaluations": {
                "artificial_analysis_intelligence_index": 23.8,
                "artificial_analysis_coding_index": 30.4,
            },
            "pricing": {
                "price_1m_blended_3_to_1": 0.262,
                "price_1m_input_tokens": 0.15,
                "price_1m_output_tokens": 0.6,
            },
            "median_output_tokens_per_second": 198.869,
        }
    ]
    idx, missing = cm.build_aa_index(raw)
    entry = idx["gptoss120b"]
    assert entry["release_date"] == "2025-08-05"
    assert entry["aa_intelligence_index"] == 23.8
    assert entry["aa_coding_index"] == 30.4
    assert entry["price_input_per_1m"] == 0.15
    assert entry["price_output_per_1m"] == 0.6
    assert entry["price_blended_per_1m"] == 0.262
    assert entry["median_output_tokens_per_second"] == 198.869
    assert entry["organization"] == "openai"
    # Confirmed-absent-on-tier fields are still probed but not found.
    assert "context_window_tokens" in missing
    assert "parameters_total" in missing
    assert "parameters_active" in missing
    assert "open_weights" in missing


# ---------------------------------------------------------------------------
# split_missing_aa_fields
# ---------------------------------------------------------------------------

def test_split_missing_aa_fields_separates_known_unavailable_from_unmapped():
    missing = {"context_window_tokens", "open_weights", "aa_intelligence_index"}
    genuinely_unmapped, known_unavailable = cm.split_missing_aa_fields(missing)
    assert genuinely_unmapped == {"aa_intelligence_index"}
    assert known_unavailable == {"context_window_tokens", "open_weights"}


def test_split_missing_aa_fields_all_unmapped_when_none_known_unavailable():
    missing = {"aa_intelligence_index", "aa_coding_index"}
    genuinely_unmapped, known_unavailable = cm.split_missing_aa_fields(missing)
    assert genuinely_unmapped == missing
    assert known_unavailable == set()


# ---------------------------------------------------------------------------
# join_models
# ---------------------------------------------------------------------------

def _arena_entry(slug, name, **overrides):
    entry = {
        "slug": slug,
        "name": name,
        "organization": "acme",
        "license": "Proprietary",
        "arena_elo_overall": 1500.0,
        "arena_elo_coding": None,
        "arena_votes": 100.0,
        "arena_rank_overall": 3.0,
        "arena_rank_coding": None,
        "publish_date": "2026-08-01",
    }
    entry.update(overrides)
    return entry


def test_join_models_matches_by_normalized_slug():
    lmarena_idx = {"gpt56sol": _arena_entry("gpt56sol", "gpt-5-6-sol")}
    aa_idx = {"gpt56sol": {"slug": "gpt56sol", "name": "GPT 5.6 Sol", "price_input_per_1m": 1.0, "price_output_per_1m": 2.0}}
    merged = cm.join_models(lmarena_idx, aa_idx, aliases={})
    assert len(merged) == 1
    row = merged[0]
    assert row["joined_sources"] == ["lmarena", "artificial_analysis"]
    assert row["price_input_per_1m"] == 1.0


def test_join_models_uses_alias_map_when_normalization_misses():
    lmarena_idx = {"claudeopus5max": _arena_entry("claudeopus5max", "claude-opus-5-max")}
    aa_idx = {"anthropicopus5": {"slug": "anthropicopus5", "name": "Anthropic Opus 5", "price_input_per_1m": 5.0, "price_output_per_1m": 15.0}}
    aliases = {"claudeopus5max": "anthropicopus5"}
    merged = cm.join_models(lmarena_idx, aa_idx, aliases=aliases)
    assert len(merged) == 1
    row = merged[0]
    assert row["joined_sources"] == ["lmarena", "artificial_analysis"]
    assert row["price_input_per_1m"] == 5.0


def test_join_models_keeps_unjoined_lmarena_entry_with_null_aa_fields():
    lmarena_idx = {"loneranger": _arena_entry("loneranger", "Lone Ranger")}
    merged = cm.join_models(lmarena_idx, aa_idx={}, aliases={})
    assert len(merged) == 1
    row = merged[0]
    assert row["joined_sources"] == ["lmarena"]
    assert row["price_input_per_1m"] is None


def test_join_models_keeps_unjoined_aa_entry():
    aa_idx = {"aaonly": {"slug": "aaonly", "name": "AA Only Model", "price_input_per_1m": 3.0}}
    merged = cm.join_models(lmarena_idx={}, aa_idx=aa_idx, aliases={})
    assert len(merged) == 1
    row = merged[0]
    assert row["joined_sources"] == ["artificial_analysis"]
    assert row["name"] == "AA Only Model"
    assert row["arena_elo_overall"] is None


def test_join_models_fills_organization_from_model_creator_when_lmarena_null():
    lmarena_idx = {"m1": _arena_entry("m1", "Model One", organization=None)}
    aa_idx = {"m1": {"slug": "m1", "name": "Model One", "organization": "openai"}}
    merged = cm.join_models(lmarena_idx, aa_idx, aliases={})
    assert merged[0]["organization"] == "openai"


def test_join_models_never_overwrites_existing_lmarena_organization():
    lmarena_idx = {"m1": _arena_entry("m1", "Model One", organization="anthropic")}
    aa_idx = {"m1": {"slug": "m1", "name": "Model One", "organization": "openai"}}
    merged = cm.join_models(lmarena_idx, aa_idx, aliases={})
    assert merged[0]["organization"] == "anthropic"


def test_join_models_aa_only_entry_populates_organization():
    aa_idx = {"aaonly": {"slug": "aaonly", "name": "AA Only Model", "organization": "openai"}}
    merged = cm.join_models(lmarena_idx={}, aa_idx=aa_idx, aliases={})
    assert merged[0]["organization"] == "openai"


def test_join_models_deduplicates_aa_entry_reachable_by_slug_and_name_keys():
    # build_aa_index can index one AA model under two different dict keys
    # (its slug and its name). If neither is claimed by an LMArena row, the
    # AA-only fallback must emit that model once, not twice.
    record = {"slug": "gpt56luna", "name": "GPT-5.6 Sol (max)", "price_input_per_1m": 9.0}
    aa_idx = {"gpt56luna": record, "gpt56solmax": record}
    merged = cm.join_models(lmarena_idx={}, aa_idx=aa_idx, aliases={})
    assert len(merged) == 1
    assert merged[0]["slug"] == "gpt56luna"


def test_join_models_carries_aa_benchmarks_onto_a_joined_row():
    lmarena_idx = {"m1": _arena_entry("m1", "Model One")}
    aa_idx = {"m1": {"slug": "m1", "name": "Model One", "benchmarks": {"livecodebench": 0.878}}}
    merged = cm.join_models(lmarena_idx, aa_idx, aliases={})
    assert merged[0]["benchmarks"] == {"livecodebench": 0.878}


def test_join_models_benchmarks_empty_for_unjoined_lmarena_only_row():
    lmarena_idx = {"m1": _arena_entry("m1", "Model One")}
    merged = cm.join_models(lmarena_idx, aa_idx={}, aliases={})
    assert merged[0]["benchmarks"] == {}


def test_join_models_carries_aa_benchmarks_for_an_aa_only_row():
    aa_idx = {"aaonly": {"slug": "aaonly", "name": "AA Only Model", "benchmarks": {"scicode": 0.5}}}
    merged = cm.join_models(lmarena_idx={}, aa_idx=aa_idx, aliases={})
    assert merged[0]["benchmarks"] == {"scicode": 0.5}


# ---------------------------------------------------------------------------
# select_models
# ---------------------------------------------------------------------------

def test_select_models_ranks_recent_release_ahead_of_stale_high_rank():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    models = [
        {"slug": "old-top", "arena_rank_overall": 1, "release_date": "2025-01-01"},
        {"slug": "new-lower", "arena_rank_overall": 50, "release_date": "2026-08-01"},
    ]
    selected = cm.select_models(models, recency_days=90, max_models=10, now=now)
    assert [m["slug"] for m in selected] == ["new-lower", "old-top"]


def test_select_models_falls_back_to_arena_rank_when_no_release_dates():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    models = [
        {"slug": "rank2", "arena_rank_overall": 2, "release_date": None},
        {"slug": "rank1", "arena_rank_overall": 1, "release_date": None},
        {"slug": "unranked", "arena_rank_overall": None, "release_date": None},
    ]
    selected = cm.select_models(models, recency_days=90, max_models=10, now=now)
    assert [m["slug"] for m in selected] == ["rank1", "rank2", "unranked"]


def test_select_models_caps_to_max_models():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    models = [{"slug": f"m{i}", "arena_rank_overall": i, "release_date": None} for i in range(5)]
    selected = cm.select_models(models, recency_days=90, max_models=2, now=now)
    assert len(selected) == 2


def test_select_models_ignores_malformed_release_date():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    models = [{"slug": "bad-date", "arena_rank_overall": 1, "release_date": "not-a-date"}]
    # Should not raise, and the model is still returned.
    selected = cm.select_models(models, recency_days=90, max_models=10, now=now)
    assert [m["slug"] for m in selected] == ["bad-date"]


# ---------------------------------------------------------------------------
# finalize_model
# ---------------------------------------------------------------------------

def test_finalize_model_computes_blended_price_and_rounds():
    row = {
        "slug": "s",
        "name": "S Model",
        "organization": "acme",
        "license": "MIT",
        "open_weights": True,
        "arena_elo_overall": 1500.567,
        "arena_votes": 100.0,
        "arena_rank_overall": 3.0,
        "price_input_per_1m": 2.0,
        "price_output_per_1m": 6.0,
        "joined_sources": ["lmarena", "artificial_analysis"],
    }
    out = cm.finalize_model(row)
    assert out["arena_elo_overall"] == 1500.57
    assert out["arena_votes"] == 100
    assert out["arena_rank_overall"] == 3
    assert out["price_blended_per_1m"] == 3.0
    assert out["open_weights"] is True


def test_finalize_model_carries_benchmarks_through_verbatim_never_rounded():
    # Stored exactly as AA reports it - no rounding, no rescaling. This is
    # the scale-trap-sensitive field: a 0-1 fraction must survive untouched.
    row = {"slug": "s", "name": "S", "benchmarks": {"livecodebench": 0.8776543}}
    out = cm.finalize_model(row)
    assert out["benchmarks"] == {"livecodebench": 0.8776543}


def test_finalize_model_benchmarks_defaults_to_empty_dict_when_absent():
    row = {"slug": "s", "name": "S"}
    out = cm.finalize_model(row)
    assert out["benchmarks"] == {}


def test_finalize_model_prefers_aa_published_blended_price_over_computed():
    # AA's price_1m_blended_3_to_1 (0.262) is preferred over what the local
    # 3:1 computation from price_input/price_output would produce (3.0),
    # even though both are present.
    row = {
        "slug": "s",
        "name": "S Model",
        "price_input_per_1m": 2.0,
        "price_output_per_1m": 6.0,
        "price_blended_per_1m": 0.262,
    }
    out = cm.finalize_model(row)
    assert out["price_blended_per_1m"] == 0.262


def test_finalize_model_falls_back_to_computed_blend_when_aa_value_absent():
    row = {"slug": "s", "name": "S Model", "price_input_per_1m": 2.0, "price_output_per_1m": 6.0}
    out = cm.finalize_model(row)
    assert out["price_blended_per_1m"] == 3.0


def test_finalize_model_defensive_against_non_bool_open_weights():
    row = {"slug": "s", "name": "S", "open_weights": "unknown"}
    out = cm.finalize_model(row)
    assert out["open_weights"] is None


def test_finalize_model_derives_open_weights_from_license_when_no_aa_bool():
    # No AA data (open_weights not set on the row) - falls back to the
    # LMArena license via classification_cfg, as it does in the default
    # no-AA-key path.
    row = {"slug": "s", "name": "S", "license": "Proprietary"}
    out = cm.finalize_model(row, DEFAULT_CLASSIFICATION_CFG)
    assert out["open_weights"] is False

    row_open = {"slug": "s2", "name": "S2", "license": "Apache 2.0"}
    out_open = cm.finalize_model(row_open, DEFAULT_CLASSIFICATION_CFG)
    assert out_open["open_weights"] is True


def test_finalize_model_zero_price_becomes_null_everywhere():
    row = {
        "slug": "s", "name": "S",
        "price_input_per_1m": 0.0, "price_output_per_1m": 0.0, "price_blended_per_1m": 0.0,
    }
    out = cm.finalize_model(row)
    assert out["price_input_per_1m"] is None
    assert out["price_output_per_1m"] is None
    assert out["price_blended_per_1m"] is None


def test_finalize_model_zero_input_price_nulls_the_computed_blend_too():
    # No AA-published blend to fall back to - the local 3:1 computation must
    # also treat the zero input price as unknown, not as a real $0 term.
    row = {"slug": "s", "name": "S", "price_input_per_1m": 0.0, "price_output_per_1m": 4.0}
    out = cm.finalize_model(row)
    assert out["price_input_per_1m"] is None
    assert out["price_blended_per_1m"] is None


def test_finalize_model_nonzero_price_is_unaffected():
    row = {"slug": "s", "name": "S", "price_input_per_1m": 2.0, "price_output_per_1m": 6.0}
    out = cm.finalize_model(row)
    assert out["price_input_per_1m"] == 2.0
    assert out["price_blended_per_1m"] == 3.0


def test_finalize_model_normalizes_organization_via_alias_map():
    row = {"slug": "s", "name": "Kimi K3 (max)", "organization": "kimi"}
    out = cm.finalize_model(row, organization_aliases={"kimi": "moonshot"})
    assert out["organization"] == "moonshot"


def test_finalize_model_organization_alias_lookup_is_case_insensitive():
    row = {"slug": "s", "name": "S", "organization": "KIMI"}
    out = cm.finalize_model(row, organization_aliases={"kimi": "moonshot"})
    assert out["organization"] == "moonshot"


def test_finalize_model_organization_without_alias_entry_is_unchanged():
    row = {"slug": "s", "name": "S", "organization": "anthropic"}
    out = cm.finalize_model(row, organization_aliases={"kimi": "moonshot"})
    assert out["organization"] == "anthropic"


def test_finalize_model_missing_organization_alias_map_is_a_no_op():
    row = {"slug": "s", "name": "S", "organization": "kimi"}
    out = cm.finalize_model(row)
    assert out["organization"] == "kimi"


def test_finalize_model_populates_base_slug_and_variant_label():
    row = {"slug": "s", "name": "GPT-5.6 Sol (medium)"}
    out = cm.finalize_model(row, variant_vocab=VARIANT_VOCAB)
    assert out["base_slug"] == "gpt56sol"
    assert out["variant_label"] == "medium"


def test_finalize_model_variant_label_is_null_without_a_vocabulary():
    row = {"slug": "s", "name": "gpt-5.6-sol-xhigh"}
    out = cm.finalize_model(row)
    assert out["variant_label"] is None
    assert out["base_slug"] == cm.normalize_slug("gpt-5.6-sol-xhigh")


# ---------------------------------------------------------------------------
# derive_display_name (Step 8: normalize model display names)
# ---------------------------------------------------------------------------

def test_derive_display_name_prefers_aa_name_and_strips_recognized_parenthetical():
    # AA's own name is already well-cased and human-written; the bare
    # "(medium)" parenthetical is a recognized token, so it is stripped.
    assert cm.derive_display_name(
        "gpt-5-6-sol-medium", "GPT-5.6 Sol (medium)", VARIANT_VOCAB, {}
    ) == "GPT-5.6 Sol"


def test_derive_display_name_strips_effort_phrase_from_aa_name():
    assert cm.derive_display_name(
        "claude-opus-5-max", "Claude Opus 5 (Adaptive Reasoning, Max Effort)", VARIANT_VOCAB, {}
    ) == "Claude Opus 5"


def test_derive_display_name_never_recases_an_already_well_cased_aa_name():
    # No recognized variant to strip - AA's casing passes through untouched,
    # not run through the slug-casing pipeline (which would be a no-op here
    # anyway, but the AA path must never even attempt it).
    assert cm.derive_display_name("motif-3", "Motif 3", VARIANT_VOCAB, {}) == "Motif 3"


def test_derive_display_name_titlecases_a_dashed_lmarena_slug():
    assert cm.derive_display_name("claude-fable-5", None, VARIANT_VOCAB, {}) == "Claude Fable 5"


def test_derive_display_name_strips_recognized_lmarena_suffix_variant():
    assert cm.derive_display_name(
        "gpt-5.6-sol-xhigh", None, VARIANT_VOCAB, ACRONYM_CASING
    ) == "GPT-5.6 Sol"


def test_derive_display_name_uses_acronym_casing_map_and_dashes_before_a_version():
    # "max" is a recognized variant token and is stripped first; "glm" comes
    # from the acronym_casing map and keeps its dash before the version
    # number, matching the conventional brand-version spelling.
    assert cm.derive_display_name(
        "glm-5.2-max", None, VARIANT_VOCAB, ACRONYM_CASING
    ) == "GLM-5.2"


def test_derive_display_name_deepseek_style_brand_version_dash_and_trailing_word():
    assert cm.derive_display_name(
        "deepseek-v4-flash", None, VARIANT_VOCAB, ACRONYM_CASING
    ) == "DeepSeek-V4 Flash"


def test_derive_display_name_preserves_version_numbers_never_loses_a_digit():
    # No acronym entry for "qwen" in this call's map - the version number
    # must survive regardless, just without the brand-cased dash join.
    assert cm.derive_display_name("qwen-3.8-max", None, VARIANT_VOCAB, {}) == "Qwen 3.8"
    assert cm.derive_display_name(
        "qwen-3.8-max", None, VARIANT_VOCAB, {"qwen": "Qwen"}
    ) == "Qwen-3.8"


def test_derive_display_name_passes_through_when_no_variant_is_recognized():
    # "-lite" is a real Gemini size tier, not a reasoning-effort variant -
    # nothing is stripped, and the words are still conservatively titlecased.
    assert cm.derive_display_name(
        "gemini-3.5-flash-lite", None, VARIANT_VOCAB, {}
    ) == "Gemini 3.5 Flash Lite"


def test_derive_display_name_never_mangles_a_word_that_already_has_a_capital():
    # An unrecognized parenthetical is never stripped (it becomes part of
    # the base, same as derive_base_variant), and a word already carrying a
    # capital letter (mixed case, not a plain lowercase slug word) is left
    # exactly as it was - never lowercased-then-retitled.
    assert cm.derive_display_name(
        "Motif 3 (Beta)", None, VARIANT_VOCAB, {}
    ) == "Motif 3 (Beta)"


def test_derive_display_name_returns_none_for_blank_input():
    assert cm.derive_display_name(None, None, VARIANT_VOCAB, {}) is None
    assert cm.derive_display_name("", None, VARIANT_VOCAB, {}) is None


def test_derive_display_name_returns_none_when_source_text_is_effectively_blank():
    # aa_name is whitespace-only (truthy but useless) - the AA path is
    # still preferred (aa_name is non-empty), but yields nothing usable.
    assert cm.derive_display_name("gpt-5-6-sol", "   ", VARIANT_VOCAB, {}) is None


# ---------------------------------------------------------------------------
# join_models: aa_name propagation (internal field feeding display_name)
# ---------------------------------------------------------------------------

def test_join_models_carries_aa_name_even_when_lmarena_owns_the_emitted_name():
    lmarena_idx = {"claudeopus5max": _arena_entry("claudeopus5max", "claude-opus-5-max")}
    aa_idx = {"claudeopus5max": {"slug": "claudeopus5max", "name": "Claude Opus 5 (Adaptive Reasoning, Max Effort)"}}
    merged = cm.join_models(lmarena_idx, aa_idx, aliases={})
    row = merged[0]
    assert row["name"] == "claude-opus-5-max"  # unchanged join-key ownership
    assert row["aa_name"] == "Claude Opus 5 (Adaptive Reasoning, Max Effort)"


def test_join_models_aa_name_is_null_for_an_unjoined_lmarena_only_row():
    lmarena_idx = {"loneranger": _arena_entry("loneranger", "Lone Ranger")}
    merged = cm.join_models(lmarena_idx, aa_idx={}, aliases={})
    assert merged[0].get("aa_name") is None


def test_join_models_aa_name_equals_name_for_an_unjoined_aa_only_row():
    aa_idx = {"aaonly": {"slug": "aaonly", "name": "AA Only Model"}}
    merged = cm.join_models(lmarena_idx={}, aa_idx=aa_idx, aliases={})
    assert merged[0]["name"] == "AA Only Model"
    assert merged[0]["aa_name"] == "AA Only Model"


# ---------------------------------------------------------------------------
# finalize_model: display_name assembly
# ---------------------------------------------------------------------------

def test_finalize_model_populates_display_name_from_dashed_lmarena_slug():
    row = {"slug": "s", "name": "gpt-5.6-sol-xhigh"}
    out = cm.finalize_model(row, variant_vocab=VARIANT_VOCAB, acronym_casing=ACRONYM_CASING)
    assert out["display_name"] == "GPT-5.6 Sol"
    assert out["name"] == "gpt-5.6-sol-xhigh"  # raw name field is untouched


def test_finalize_model_prefers_aa_name_over_lmarena_raw_name_for_display():
    row = {
        "slug": "s",
        "name": "claude-opus-5-max",
        "aa_name": "Claude Opus 5 (Adaptive Reasoning, Max Effort)",
    }
    out = cm.finalize_model(row, variant_vocab=VARIANT_VOCAB)
    assert out["display_name"] == "Claude Opus 5"
    assert out["name"] == "claude-opus-5-max"  # additive only - name unchanged


def test_finalize_model_no_variant_display_name_is_a_tidied_name():
    row = {"slug": "s", "name": "claude-fable-5"}
    out = cm.finalize_model(row, variant_vocab=VARIANT_VOCAB)
    assert out["display_name"] == "Claude Fable 5"
    assert out["variant_label"] is None


def test_finalize_model_falls_back_to_raw_name_when_display_name_computation_yields_nothing():
    row = {"slug": "s", "name": "gpt-5-6-sol", "aa_name": "   "}
    out = cm.finalize_model(row, variant_vocab=VARIANT_VOCAB)
    assert out["display_name"] == "gpt-5-6-sol"


def test_finalize_model_display_name_never_null_or_empty_when_name_present():
    row = {"slug": "s", "name": "some-model"}
    out = cm.finalize_model(row)
    assert out["display_name"]
    assert out["display_name"] == "Some Model"


def test_finalize_model_display_name_defaults_gracefully_without_config():
    # No variant_vocab/acronym_casing passed at all - must not crash, and
    # must still produce a non-empty, non-mangled display_name.
    row = {"slug": "s", "name": "gpt-5.6-sol-xhigh"}
    out = cm.finalize_model(row)
    assert out["display_name"]
    assert "5.6" in out["display_name"]


# ---------------------------------------------------------------------------
# build_output (end-to-end pure assembly)
# ---------------------------------------------------------------------------

def test_build_output_shape_with_aa_unavailable():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    lmarena_idx = {"m1": _arena_entry("m1", "Model One")}
    lmarena_meta = {"available": True, "attribution": "LMArena", "url": "https://x", "publish_date": "2026-08-01"}
    aa_meta = {"available": False, "attribution": "AA", "url": "https://y"}
    output = cm.build_output(
        lmarena_idx=lmarena_idx,
        aa_idx={},
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta=lmarena_meta,
        aa_meta=aa_meta,
        classification_cfg=DEFAULT_CLASSIFICATION_CFG,
    )
    assert output["generated_at"] == now.isoformat()
    assert output["sources"]["artificial_analysis"]["available"] is False
    assert len(output["models"]) == 1
    assert output["models"][0]["price_blended_per_1m"] is None
    # AA is unavailable, so open_weights falls back to the LMArena license
    # ("Proprietary" per _arena_entry's default) rather than staying null.
    assert output["models"][0]["open_weights"] is False
    # Not passed above -> defaults to an empty list, never missing entirely.
    assert output["axis_metric_options"] == []


def test_build_output_emits_axis_metric_options_verbatim():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    options = [{"key": "aa_coding_index", "label": "AA coding index", "source": "top", "scale": "index"}]
    output = cm.build_output(
        lmarena_idx={},
        aa_idx={},
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta={"available": False},
        aa_meta={"available": False},
        axis_metric_options=options,
    )
    assert output["axis_metric_options"] == options


# ---------------------------------------------------------------------------
# save_output / load_output round trip
# ---------------------------------------------------------------------------

def test_save_and_load_output_round_trip(tmp_path):
    latest_path = tmp_path / "latest.json"
    history_dir = tmp_path / "history"
    output = {
        "generated_at": "2026-08-05T00:00:00+00:00",
        "sources": {"lmarena": {"available": True}, "artificial_analysis": {"available": False}},
        "models": [{"slug": "m1", "name": "Model One"}],
    }
    history_path = cm.save_output(output, latest_path=latest_path, history_dir=history_dir)
    assert history_path == history_dir / "2026-08-05.json"
    assert history_path.exists()

    loaded = cm.load_output(latest_path=latest_path)
    assert loaded["models"][0]["slug"] == "m1"


def test_load_output_missing_file_returns_none(tmp_path):
    assert cm.load_output(latest_path=tmp_path / "missing.json") is None


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_defaults_when_file_missing(tmp_path):
    cfg = cm.load_config(path=tmp_path / "missing.yaml")
    assert cfg["recency_days"] == 90
    assert cfg["sources"]["lmarena"]["enabled"] is True
    assert cfg["trust_env_proxies"] is False
    assert cfg["license_classification"]["proprietary_markers"] == ["proprietary"]
    # Conservative empty defaults: no variant stripping, no org aliasing,
    # until config/models.yaml populates them.
    assert cfg["variant_vocabulary"] == {
        "tokens": {}, "effort_phrases": [], "ignorable_qualifiers": [],
    }
    assert cfg["organization_aliases"] == {}


def test_load_config_reads_real_variant_and_organization_config():
    # The actual checked-in config/models.yaml, not a fixture - pins that
    # the real file stays parseable and carries the collisions/tokens this
    # feature was seeded with.
    cfg = cm.load_config()
    assert cfg["organization_aliases"].get("kimi") == "moonshot"
    assert cfg["variant_vocabulary"]["tokens"].get("xhigh") == "xhigh"
    assert any(
        "adaptive reasoning" in (entry.get("pattern") or "")
        for entry in cfg["variant_vocabulary"]["effort_phrases"]
    )
    assert any(
        entry.get("pattern") == r"^reasoning,\s*(?P<level>[a-z]+)\s*effort$"
        for entry in cfg["variant_vocabulary"]["effort_phrases"]
    )
    assert cfg["acronym_casing"].get("gpt") == "GPT"
    assert cfg["acronym_casing"].get("deepseek") == "DeepSeek"
    # The live vocabulary must still collapse AA's fallback-qualified effort
    # parenthetical to one base model - the /models duplicate-rows regression.
    vocab = cfg["variant_vocabulary"]
    assert cm.derive_base_variant(
        "Claude Fable 5.1 (Adaptive Reasoning, High Effort, Default Fallback)", vocab
    ) == ("claudefable51", "high")
    assert cm.derive_base_variant(
        "Claude Fable 5.1 (Adaptive Reasoning, Max Effort, Default Fallback)", vocab
    ) == ("claudefable51", "max")


def test_load_config_trust_env_proxies_is_overridable(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("trust_env_proxies: true\n", encoding="utf-8")
    cfg = cm.load_config(path=path)
    assert cfg["trust_env_proxies"] is True


def test_load_config_merges_source_overrides(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text(
        "recency_days: 30\n"
        "sources:\n"
        "  lmarena:\n"
        "    page_size: 50\n"
        "aliases:\n"
        "  foo: bar\n",
        encoding="utf-8",
    )
    cfg = cm.load_config(path=path)
    assert cfg["recency_days"] == 30
    assert cfg["sources"]["lmarena"]["page_size"] == 50
    # Unrelated default source keys survive the shallow merge.
    assert cfg["sources"]["lmarena"]["dataset"] == "lmarena-ai/leaderboard-dataset"
    assert cfg["aliases"] == {"foo": "bar"}


# ---------------------------------------------------------------------------
# _make_session
# ---------------------------------------------------------------------------

def test_make_session_defaults_trust_env_false():
    session = cm._make_session({})
    assert session.trust_env is False


def test_make_session_honors_trust_env_proxies_true():
    session = cm._make_session({"trust_env_proxies": True})
    assert session.trust_env is True


PAREN_VOCAB = {"tokens": {"max": "max", "high": "high", "low": "low", "reasoning": "reasoning"}}


def test_strip_configuration_parenthetical_drops_multi_clause_settings():
    """AA's settings blobs are not part of a model's identity."""
    text = "Claude Fable 5 (Adaptive Reasoning, Max Effort, Opus 4.8 Fallback)"
    assert cm.strip_configuration_parenthetical(text, PAREN_VOCAB) == "Claude Fable 5"


def test_strip_configuration_parenthetical_keeps_identifying_parenthetical():
    """A dated snapshot distinguishes releases - stripping it would collide two models."""
    text = "GPT-5.5 Instant (June 2026)"
    assert cm.strip_configuration_parenthetical(text, PAREN_VOCAB) == text


def test_strip_configuration_parenthetical_passthrough_without_parenthetical():
    assert cm.strip_configuration_parenthetical("Claude Opus 5", PAREN_VOCAB) == "Claude Opus 5"


def test_strip_configuration_parenthetical_never_returns_empty():
    """A name that is nothing but a variant parenthetical keeps its original text."""
    assert cm.strip_configuration_parenthetical("(Max Effort)", PAREN_VOCAB) == "(Max Effort)"


# ---------------------------------------------------------------------------
# slugify / assign_url_slugs (WORK ITEM 1: stable public URL slugs)
# ---------------------------------------------------------------------------

# The exact shape api/models.js's ?slug= lookup already enforces
# (SLUG_RE = /^[a-z0-9][a-z0-9-]{0,80}$/) - mirrored here so the test suite
# pins the real public contract, not just "whatever slugify() happens to do".
SLUG_RE = __import__("re").compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


def test_slugify_converts_the_documented_examples():
    assert cm.slugify("GPT-5.6 Sol") == "gpt-5-6-sol"
    assert cm.slugify("Claude Opus 5") == "claude-opus-5"
    assert cm.slugify("DeepSeek-V4 Flash") == "deepseek-v4-flash"


def test_slugify_collapses_punctuation_and_whitespace_runs():
    assert cm.slugify("  Motif 3 (Beta)!!  ") == "motif-3-beta"
    assert cm.slugify("Qwen_3.8__Max") == "qwen-3-8-max"


def test_slugify_never_leaves_leading_trailing_or_double_dashes():
    slug = cm.slugify("--Weird...Name--")
    assert SLUG_RE.match(slug)
    assert "--" not in slug


def test_slugify_none_and_empty_and_punctuation_only_yield_empty_string():
    assert cm.slugify(None) == ""
    assert cm.slugify("") == ""
    assert cm.slugify("...---...") == ""


def test_slugify_truncates_to_leave_room_for_a_collision_suffix():
    slug = cm.slugify("x" * 200)
    assert len(slug) <= cm._SLUG_MAX_BASE_LEN
    assert SLUG_RE.match(slug)


def _model(slug, name=None, display_name=None, base_slug=None):
    # base_slug defaults to the row's own `slug` - i.e. "this row is its own
    # group" - matching finalize_model's real behavior for a name with no
    # recognized variant. Tests that want several rows to represent
    # different reasoning-effort variants of the SAME base model pass a
    # shared `base_slug` explicitly (see the grouping tests below).
    return {"slug": slug, "name": name, "display_name": display_name, "base_slug": base_slug or slug}


def test_assign_url_slugs_conforms_to_the_regex_across_varied_names():
    models = [
        _model("claudeopus5max", display_name="Claude Opus 5"),
        _model("gpt56solmedium", display_name="GPT-5.6 Sol"),
        _model("deepseekv4flash", display_name="DeepSeek-V4 Flash"),
        _model("weird1", display_name="  --Weird...Name!! (Beta)  "),
        _model("blank1", display_name=None, name=None),
    ]
    cm.assign_url_slugs(models)
    for m in models:
        assert SLUG_RE.match(m["url_slug"]), m["url_slug"]


def test_assign_url_slugs_falls_back_display_name_to_name_to_slug():
    models = [
        _model("s1", name="raw-name-one", display_name="Clean Name One"),
        _model("s2", name="raw-name-two", display_name=None),
        _model("s3", name=None, display_name=None),
    ]
    cm.assign_url_slugs(models)
    assert models[0]["url_slug"] == "clean-name-one"
    assert models[1]["url_slug"] == "raw-name-two"
    assert models[2]["url_slug"] == "s3"


def test_assign_url_slugs_never_empty_even_when_every_identity_field_is_blank():
    models = [{"slug": "", "name": "", "display_name": "", "base_slug": ""}]
    cm.assign_url_slugs(models)
    assert models[0]["url_slug"]


def test_assign_url_slugs_resolves_collisions_with_a_numeric_suffix_never_drops_a_row():
    # Three distinct real models (different base_slug - different labs, not
    # variants of one model) whose clean display_name collapses to the same
    # string (e.g. three labs all shipping a model called "Nova").
    models = [
        _model("labone-nova", display_name="Nova"),
        _model("labtwo-nova", display_name="Nova"),
        _model("labthree-nova", display_name="Nova"),
    ]
    cm.assign_url_slugs(models)
    slugs = [m["url_slug"] for m in models]
    assert len(slugs) == len(set(slugs)) == 3
    assert "nova" in slugs
    assert "nova-2" in slugs
    assert "nova-3" in slugs
    for s in slugs:
        assert SLUG_RE.match(s)


def test_assign_url_slugs_collision_resolution_is_independent_of_input_order():
    a = _model("labone-nova", display_name="Nova")
    b = _model("labtwo-nova", display_name="Nova")
    c = _model("labthree-nova", display_name="Nova")

    forward = [dict(a), dict(b), dict(c)]
    reversed_order = [dict(c), dict(b), dict(a)]
    cm.assign_url_slugs(forward)
    cm.assign_url_slugs(reversed_order)

    forward_by_slug = {m["slug"]: m["url_slug"] for m in forward}
    reversed_by_slug = {m["slug"]: m["url_slug"] for m in reversed_order}
    assert forward_by_slug == reversed_by_slug


def test_assign_url_slugs_stable_across_two_builds_of_the_same_input():
    # Simulates a re-collect from the same underlying source data: same rows
    # (including two Claude Opus 5 reasoning-effort variants sharing a
    # base_slug), arbitrary shuffled order (network/pagination order is not
    # guaranteed stable run-to-run). The published url_slug per model
    # identity must be bit-for-bit identical both times.
    import random

    base_models = [
        _model("claudeopus5max", display_name="Claude Opus 5", base_slug="claudeopus5"),
        _model("claudeopus5high", display_name="Claude Opus 5", base_slug="claudeopus5"),
        _model("gpt56solmedium", display_name="GPT-5.6 Sol", base_slug="gpt56sol"),
        _model("gpt56solxhigh", display_name="GPT-5.6 Sol", base_slug="gpt56sol"),
        _model("deepseekv4flash", display_name="DeepSeek-V4 Flash"),
    ]

    run1 = [dict(m) for m in base_models]
    run2 = [dict(m) for m in base_models]
    random.Random(42).shuffle(run2)

    cm.assign_url_slugs(run1)
    cm.assign_url_slugs(run2)

    run1_by_slug = {m["slug"]: m["url_slug"] for m in run1}
    run2_by_slug = {m["slug"]: m["url_slug"] for m in run2}
    assert run1_by_slug == run2_by_slug


def test_assign_url_slugs_never_derives_from_list_position():
    # Identical single-model input processed alone vs. alongside unrelated
    # siblings must yield the same slug for that model - position/context
    # in the list must never leak into the derivation.
    solo = [_model("m1", display_name="Solo Model")]
    with_siblings = [
        _model("m0", display_name="Aardvark"),
        _model("m1", display_name="Solo Model"),
        _model("m2", display_name="Zebra"),
    ]
    cm.assign_url_slugs(solo)
    cm.assign_url_slugs(with_siblings)
    solo_slug = solo[0]["url_slug"]
    sibling_slug = next(m["url_slug"] for m in with_siblings if m["slug"] == "m1")
    assert solo_slug == sibling_slug == "solo-model"


# ---------------------------------------------------------------------------
# assign_url_slugs: per-BASE-MODEL grouping (coordinator correction,
# 2026-08-16) - one url_slug per base_slug group, not per row.
# ---------------------------------------------------------------------------

def test_assign_url_slugs_groups_every_variant_of_one_model_under_the_same_slug():
    # Six reasoning-effort variants of one real model (the exact live
    # collision this fix addresses) must all resolve to ONE url_slug, not
    # six numbered ones.
    variants = ["max", "high", "low", "medium", "xhigh", "minimal"]
    models = [
        _model(f"claudeopus5{v}", display_name="Claude Opus 5", base_slug="claudeopus5")
        for v in variants
    ]
    cm.assign_url_slugs(models)
    slugs = {m["url_slug"] for m in models}
    assert slugs == {"claude-opus-5"}


def test_assign_url_slugs_different_base_models_still_get_distinct_slugs():
    models = [
        _model("claudeopus5max", display_name="Claude Opus 5", base_slug="claudeopus5"),
        _model("claudeopus5high", display_name="Claude Opus 5", base_slug="claudeopus5"),
        _model("gpt56solmedium", display_name="GPT-5.6 Sol", base_slug="gpt56sol"),
    ]
    cm.assign_url_slugs(models)
    by_slug = {m["slug"]: m["url_slug"] for m in models}
    assert by_slug["claudeopus5max"] == by_slug["claudeopus5high"] == "claude-opus-5"
    assert by_slug["gpt56solmedium"] == "gpt-5-6-sol"


def test_assign_url_slugs_collision_only_between_genuinely_different_base_models():
    # Two DIFFERENT real models (different base_slug) that happen to clean
    # up to the same display_name still collide and get a numeric suffix -
    # unlike two variants of the SAME base_slug, which never collide with
    # each other because they share one slug outright.
    models = [
        _model("labone-nova-max", display_name="Nova", base_slug="labonenova"),
        _model("labone-nova-high", display_name="Nova", base_slug="labonenova"),
        _model("labtwo-nova", display_name="Nova", base_slug="labtwonova"),
    ]
    cm.assign_url_slugs(models)
    by_slug = {m["slug"]: m["url_slug"] for m in models}
    assert by_slug["labone-nova-max"] == by_slug["labone-nova-high"]
    assert by_slug["labone-nova-max"] != by_slug["labtwo-nova"]
    assert {by_slug["labone-nova-max"], by_slug["labtwo-nova"]} == {"nova", "nova-2"}


def test_assign_url_slugs_group_representative_choice_is_deterministic_not_positional():
    # If a group's rows ever disagreed on display_name (should not happen in
    # practice - see module docstring - but must not crash or vary by
    # order), the representative is chosen by the group's own intrinsic
    # per-row identity (own `slug`, then `name`), never by which row
    # happens to appear first in the input list.
    a = _model("aaa-variant", name="A Name", display_name="Zeta Name", base_slug="grp")
    b = _model("bbb-variant", name="B Name", display_name="Alpha Name", base_slug="grp")
    forward = [dict(a), dict(b)]
    reversed_order = [dict(b), dict(a)]
    cm.assign_url_slugs(forward)
    cm.assign_url_slugs(reversed_order)
    forward_slug = forward[0]["url_slug"]
    reversed_slug = next(m["url_slug"] for m in reversed_order if m["slug"] == "aaa-variant")
    assert forward_slug == reversed_slug
    # Representative is the row with the smaller own `slug` ("aaa-variant"
    # sorts before "bbb-variant"), so its display_name ("Zeta Name") wins.
    assert forward_slug == "zeta-name"


def test_assign_url_slugs_stability_when_a_row_is_dropped_from_the_middle_of_a_variant_group():
    # THE property that matters for public URLs: retiring one upstream
    # variant must never renumber or reshape any surviving model's slug -
    # neither its own siblings nor unrelated models elsewhere in the
    # catalog. This is what a per-row (rather than per-base_slug) scheme
    # would get wrong (see the coordinator correction, 2026-08-16).
    def build():
        return [
            _model("claudeopus5low", display_name="Claude Opus 5", base_slug="claudeopus5"),
            _model("claudeopus5medium", display_name="Claude Opus 5", base_slug="claudeopus5"),
            _model("claudeopus5high", display_name="Claude Opus 5", base_slug="claudeopus5"),
            _model("unrelatedone", display_name="Unrelated One"),
            _model("unrelatedtwo", display_name="Unrelated Two"),
        ]

    full = build()
    cm.assign_url_slugs(full)
    before = {m["slug"]: m["url_slug"] for m in full}

    # Drop the MIDDLE variant ("medium") - simulates an upstream catalog
    # change between collect runs.
    dropped = [m for m in build() if m["slug"] != "claudeopus5medium"]
    cm.assign_url_slugs(dropped)
    after = {m["slug"]: m["url_slug"] for m in dropped}

    for slug, url_slug in after.items():
        assert before[slug] == url_slug, f"{slug} url_slug changed: {before[slug]} -> {url_slug}"


def test_assign_url_slugs_stability_when_a_whole_base_model_is_dropped():
    # Dropping an entire (non-colliding) base model must never perturb any
    # OTHER model's url_slug - only a genuine collision's resolution can
    # ever shift, and only when the model it collided with is the one that
    # disappears (see test below for that accepted, rare case).
    def build():
        return [
            _model("claudeopus5low", display_name="Claude Opus 5", base_slug="claudeopus5"),
            _model("claudeopus5high", display_name="Claude Opus 5", base_slug="claudeopus5"),
            _model("gpt56solmedium", display_name="GPT-5.6 Sol", base_slug="gpt56sol"),
            _model("gpt56solxhigh", display_name="GPT-5.6 Sol", base_slug="gpt56sol"),
            _model("deepseekv4flash", display_name="DeepSeek-V4 Flash"),
        ]

    full = build()
    cm.assign_url_slugs(full)
    before = {m["slug"]: m["url_slug"] for m in full}

    # Drop the entire GPT-5.6 Sol model (both its variant rows).
    dropped = [m for m in build() if m.get("base_slug") != "gpt56sol"]
    cm.assign_url_slugs(dropped)
    after = {m["slug"]: m["url_slug"] for m in dropped}

    for slug, url_slug in after.items():
        assert before[slug] == url_slug, f"{slug} url_slug changed: {before[slug]} -> {url_slug}"


def test_assign_url_slugs_collision_slot_shifts_only_when_the_colliding_sibling_model_vanishes():
    # Documents the ONE accepted, rare exception to slug stability: two
    # genuinely different base models collide on display_name, so one gets
    # a numeric suffix. If THAT SPECIFIC colliding model disappears
    # entirely (not just one of its variants), the survivor can reclaim the
    # bare slug. This is expected churn, not a bug - it depends only on a
    # whole competing model vanishing, never on ordinary variant churn.
    def build_with_both():
        return [
            _model("labone-nova", display_name="Nova", base_slug="labonenova"),
            _model("labtwo-nova", display_name="Nova", base_slug="labtwonova"),
        ]

    both = build_with_both()
    cm.assign_url_slugs(both)
    by_slug = {m["slug"]: m["url_slug"] for m in both}
    loser_slug, loser_url = ("labtwo-nova", by_slug["labtwo-nova"]) if by_slug["labone-nova"] == "nova" else ("labone-nova", by_slug["labone-nova"])
    assert loser_url == "nova-2"

    only_survivor = [m for m in build_with_both() if m["slug"] != ("labone-nova" if loser_slug == "labtwo-nova" else "labtwo-nova")]
    cm.assign_url_slugs(only_survivor)
    assert only_survivor[0]["url_slug"] == "nova"


# ---------------------------------------------------------------------------
# compute_frontier (WORK ITEM 2: server-side Pareto frontier)
# ---------------------------------------------------------------------------

FRONTIER_METRICS = [
    {
        "key": "aa_coding_index",
        "source": "top",
        "cost_field": "price_blended_per_1m",
        "cost_basis": "per_token_price_proxy",
    },
    {
        "key": "livecodebench",
        "source": "benchmarks",
        "cost_field": "price_blended_per_1m",
        "cost_basis": "per_token_price_proxy",
    },
]


def _priced_model(slug, price, coding_index=None, livecodebench=None):
    return {
        "url_slug": slug,
        "price_blended_per_1m": price,
        "aa_coding_index": coding_index,
        "benchmarks": {"livecodebench": livecodebench} if livecodebench is not None else {},
    }


def test_compute_frontier_cheapest_and_strictly_better_are_on_frontier():
    models = [
        _priced_model("cheap-weak", price=1.0, coding_index=50),
        _priced_model("mid-better", price=5.0, coding_index=70),
        _priced_model("expensive-best", price=20.0, coding_index=90),
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert frontier["cheap-weak"]["aa_coding_index"]["on_frontier"] is True
    assert frontier["mid-better"]["aa_coding_index"]["on_frontier"] is True
    assert frontier["expensive-best"]["aa_coding_index"]["on_frontier"] is True


def test_compute_frontier_dominated_model_is_excluded_and_lists_its_dominator():
    models = [
        _priced_model("cheap-strong", price=2.0, coding_index=80),
        # Same price as cheap-strong but strictly worse capability - dominated.
        _priced_model("same-price-weaker", price=2.0, coding_index=60),
        # More expensive AND no better - dominated.
        _priced_model("pricier-not-better", price=10.0, coding_index=75),
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert frontier["cheap-strong"]["aa_coding_index"]["on_frontier"] is True
    assert frontier["same-price-weaker"]["aa_coding_index"]["on_frontier"] is False
    assert frontier["same-price-weaker"]["aa_coding_index"]["dominated_by"] == ["cheap-strong"]
    assert frontier["pricier-not-better"]["aa_coding_index"]["on_frontier"] is False
    assert frontier["pricier-not-better"]["aa_coding_index"]["dominated_by"] == ["cheap-strong"]


def test_compute_frontier_model_missing_the_metric_is_absent_not_penalized():
    models = [
        _priced_model("has-both", price=2.0, coding_index=80),
        # Priced, but no aa_coding_index at all - must not appear in that
        # metric's frontier dict, and must never be treated as capability 0
        # (which would make it look dominated by everything).
        {"url_slug": "no-metric", "price_blended_per_1m": 1.0, "aa_coding_index": None, "benchmarks": {}},
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert "no-metric" not in frontier or "aa_coding_index" not in frontier.get("no-metric", {})
    assert frontier["has-both"]["aa_coding_index"]["on_frontier"] is True


def test_compute_frontier_model_missing_the_paired_cost_is_absent_not_free():
    models = [
        _priced_model("has-both", price=2.0, coding_index=80),
        # Has the metric but no price - must not appear in that metric's
        # frontier dict, and must never be treated as cost 0 (which would
        # make it falsely dominate everything on price).
        {"url_slug": "no-price", "price_blended_per_1m": None, "aa_coding_index": 95, "benchmarks": {}},
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert "no-price" not in frontier or "aa_coding_index" not in frontier.get("no-price", {})
    assert frontier["has-both"]["aa_coding_index"]["on_frontier"] is True


def test_compute_frontier_dominated_by_caps_at_configured_size_nearest_cost_first():
    dominators = [
        _priced_model(f"dom-{i}", price=1.0 + i, coding_index=99) for i in range(8)
    ]
    victim = _priced_model("victim", price=50.0, coding_index=10)
    frontier = cm.compute_frontier(dominators + [victim], FRONTIER_METRICS, dominated_by_cap=3)
    dominated_by = frontier["victim"]["aa_coding_index"]["dominated_by"]
    assert len(dominated_by) == 3
    # Nearest-cost-first: the dominators closest in price to victim's 50.0
    # (dom-7 at 8.0 is the closest of the eight) come first.
    assert dominated_by[0] == "dom-7"


def test_compute_frontier_config_drives_the_metric_and_cost_field_pairing():
    metrics = [
        {
            "key": "custom_metric",
            "source": "top",
            "cost_field": "custom_cost",
            "cost_basis": "per_task_cost",
        }
    ]
    models = [
        {"url_slug": "a", "custom_metric": 10, "custom_cost": 1.0},
        {"url_slug": "b", "custom_metric": 20, "custom_cost": 2.0},
    ]
    frontier = cm.compute_frontier(models, metrics)
    entry = frontier["a"]["custom_metric"]
    assert entry["cost_field"] == "custom_cost"
    assert entry["cost_basis"] == "per_task_cost"
    assert entry["on_frontier"] is True


def test_compute_frontier_no_metrics_configured_yields_empty_result():
    models = [_priced_model("a", price=1.0, coding_index=50)]
    assert cm.compute_frontier(models, []) == {}
    assert cm.compute_frontier(models, None) == {}


def test_compute_frontier_computes_each_metric_independently():
    # A model can be on the frontier for one metric and dominated on another
    # - the two metrics must never leak into each other's answer.
    models = [
        _priced_model("coding-star", price=5.0, coding_index=95, livecodebench=0.5),
        _priced_model("lcb-star", price=5.0, coding_index=40, livecodebench=0.95),
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert frontier["coding-star"]["aa_coding_index"]["on_frontier"] is True
    assert frontier["coding-star"]["livecodebench"]["on_frontier"] is False
    assert frontier["lcb-star"]["livecodebench"]["on_frontier"] is True
    assert frontier["lcb-star"]["aa_coding_index"]["on_frontier"] is False


# ---------------------------------------------------------------------------
# compute_frontier: per-BASE-MODEL aggregation (coordinator correction,
# 2026-08-16) - url_slug is now shared across a model's variant rows, so
# the frontier answer must aggregate to one entry per url_slug, never treat
# a sibling variant as a competitor, and never self-reference.
# ---------------------------------------------------------------------------

def _variant_point(url_slug, price, coding_index):
    return {"url_slug": url_slug, "price_blended_per_1m": price, "aa_coding_index": coding_index, "benchmarks": {}}


def test_compute_frontier_model_on_frontier_if_any_variant_clears_the_bar():
    # "model-a" has a weak variant (dominated by the external "model-b") and
    # a strong variant (undominated). The MODEL-level answer must be True -
    # a reader can pick the strong variant - not some merge/AND across
    # variants.
    models = [
        _variant_point("model-a", price=5.0, coding_index=40),   # weak variant, externally dominated
        _variant_point("model-a", price=5.0, coding_index=95),   # strong variant, undominated
        _variant_point("model-b", price=3.0, coding_index=80),   # external competitor
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert frontier["model-a"]["aa_coding_index"]["on_frontier"] is True
    # On the frontier -> no "why not" explanation needed, even though one of
    # its own variants was individually beaten.
    assert frontier["model-a"]["aa_coding_index"]["dominated_by"] == []


def test_compute_frontier_dominated_by_never_contains_the_models_own_slug():
    # Both of model-a's variants are genuinely dominated by the external
    # model-b - AND the stronger model-a variant would (without the
    # same-slug exclusion) also look like it "dominates" the weaker
    # model-a variant, since they share a price. dominated_by must contain
    # model-b only, NEVER model-a naming itself.
    models = [
        _variant_point("model-a", price=5.0, coding_index=40),  # weak variant
        _variant_point("model-a", price=5.0, coding_index=60),  # stronger sibling, still beaten by model-b
        _variant_point("model-b", price=5.0, coding_index=90),  # external, dominates both model-a variants
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    entry = frontier["model-a"]["aa_coding_index"]
    assert entry["on_frontier"] is False
    assert entry["dominated_by"] == ["model-b"]
    assert "model-a" not in entry["dominated_by"]


def test_compute_frontier_dominated_by_dedupes_across_multiple_dominating_variants_of_one_model():
    # "model-b" has two variants that both individually dominate model-a's
    # only variant - the union must collapse to ONE "model-b" entry.
    models = [
        _variant_point("model-a", price=10.0, coding_index=30),
        _variant_point("model-b", price=5.0, coding_index=90),
        _variant_point("model-b", price=8.0, coding_index=95),
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS)
    assert frontier["model-a"]["aa_coding_index"]["dominated_by"] == ["model-b"]


def test_compute_frontier_dominated_by_ranks_deduped_dominators_by_nearest_instance():
    # model-b dominates model-a via two variants at different prices; the
    # deduped model-b entry should still sort ahead of model-c using
    # whichever model-b instance is nearest to model-a's own cost.
    models = [
        _variant_point("model-a", price=10.0, coding_index=30),
        _variant_point("model-b", price=5.0, coding_index=90),   # distance 5
        _variant_point("model-b", price=9.5, coding_index=95),   # distance 0.5 - nearer instance
        _variant_point("model-c", price=1.0, coding_index=99),   # distance 9 - farther
    ]
    frontier = cm.compute_frontier(models, FRONTIER_METRICS, dominated_by_cap=5)
    dominated_by = frontier["model-a"]["aa_coding_index"]["dominated_by"]
    assert dominated_by[0] == "model-b"
    assert set(dominated_by) == {"model-b", "model-c"}


# ---------------------------------------------------------------------------
# build_output: url_slug + frontier integration
# ---------------------------------------------------------------------------

def test_build_output_assigns_the_same_url_slug_to_every_variant_of_one_model():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    lmarena_idx = {
        "m1": _arena_entry("m1", "claude-opus-5-max"),
        "m2": _arena_entry("m2", "claude-opus-5-high"),
        "m3": _arena_entry("m3", "gpt-5-6-sol-medium"),
    }
    output = cm.build_output(
        lmarena_idx=lmarena_idx,
        aa_idx={},
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta={"available": True},
        aa_meta={"available": False},
        variant_vocab=VARIANT_VOCAB,
    )
    slugs = [m["url_slug"] for m in output["models"]]
    assert all(slugs)
    by_join_key = {m["slug"]: m["url_slug"] for m in output["models"]}
    # Both Claude Opus 5 variants collapse to ONE url_slug ...
    assert by_join_key["m1"] == by_join_key["m2"] == "claude-opus-5"
    # ... while a genuinely different model gets its own.
    assert by_join_key["m3"] == "gpt-5-6-sol"
    assert len(set(slugs)) == 2


def test_build_output_attaches_frontier_dict_per_model_using_configured_metrics():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    lmarena_idx = {
        "cheap": _arena_entry("cheap", "Cheap Model", arena_elo_coding=1200.0),
        "pricey": _arena_entry("pricey", "Pricey Model", arena_elo_coding=1800.0),
    }
    aa_idx = {
        "cheap": {"slug": "cheap", "name": "Cheap Model", "price_input_per_1m": 1.0, "price_output_per_1m": 1.0, "aa_coding_index": 40.0},
        "pricey": {"slug": "pricey", "name": "Pricey Model", "price_input_per_1m": 10.0, "price_output_per_1m": 10.0, "aa_coding_index": 90.0},
    }
    metrics = [
        {"key": "aa_coding_index", "source": "top", "cost_field": "price_blended_per_1m", "cost_basis": "per_token_price_proxy"}
    ]
    output = cm.build_output(
        lmarena_idx=lmarena_idx,
        aa_idx=aa_idx,
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta={"available": True},
        aa_meta={"available": True},
        frontier_metrics=metrics,
        frontier_dominated_by_cap=5,
    )
    by_slug = {m["slug"]: m for m in output["models"]}
    assert by_slug["cheap"]["frontier"]["aa_coding_index"]["on_frontier"] is True
    assert by_slug["pricey"]["frontier"]["aa_coding_index"]["on_frontier"] is True
    assert by_slug["cheap"]["frontier"]["aa_coding_index"]["cost_field"] == "price_blended_per_1m"
    assert by_slug["cheap"]["frontier"]["aa_coding_index"]["cost_basis"] == "per_token_price_proxy"


def test_build_output_frontier_defaults_to_empty_dict_without_config():
    now = datetime(2026, 8, 5, tzinfo=timezone.utc)
    lmarena_idx = {"m1": _arena_entry("m1", "Model One")}
    output = cm.build_output(
        lmarena_idx=lmarena_idx,
        aa_idx={},
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta={"available": True},
        aa_meta={"available": False},
    )
    assert output["models"][0]["frontier"] == {}


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))


def test_propagate_group_licensing_fills_from_a_sibling_variant():
    """A model's licensing is a property of the model, not of an effort setting."""
    rows = [
        {"url_slug": "claude-opus-5", "open_weights": False, "license": "Proprietary"},
        {"url_slug": "claude-opus-5", "open_weights": None, "license": None},
    ]
    cm.propagate_group_licensing(rows)
    assert rows[1]["open_weights"] is False
    assert rows[1]["license"] == "Proprietary"


def test_propagate_group_licensing_never_overwrites_a_known_value():
    rows = [
        {"url_slug": "m", "open_weights": False, "license": "Proprietary"},
        {"url_slug": "m", "open_weights": True, "license": "MIT"},
    ]
    cm.propagate_group_licensing(rows)
    assert rows[0]["open_weights"] is False and rows[1]["open_weights"] is True


def test_propagate_group_licensing_stays_silent_on_a_conflicted_group():
    """Disagreement means the grouping is wrong; guessing would hide that."""
    rows = [
        {"url_slug": "m", "open_weights": False, "license": "Proprietary"},
        {"url_slug": "m", "open_weights": True, "license": "MIT"},
        {"url_slug": "m", "open_weights": None, "license": None},
    ]
    cm.propagate_group_licensing(rows)
    assert rows[2]["open_weights"] is None and rows[2]["license"] is None


def test_propagate_group_licensing_does_not_leak_across_models():
    rows = [
        {"url_slug": "a", "open_weights": True, "license": "MIT"},
        {"url_slug": "b", "open_weights": None, "license": None},
    ]
    cm.propagate_group_licensing(rows)
    assert rows[1]["open_weights"] is None and rows[1]["license"] is None


# ---------------------------------------------------------------------------
# DeepSWE: measured per-task cost (WORK ITEM 1-2, added 2026-08-17)
# ---------------------------------------------------------------------------

# A small captured fixture in the DeepSWE leaderboard page's real shape - a
# React Flight payload embedding flat JS object literals (bare/unquoted
# keys) inside otherwise-irrelevant HTML/script noise, never valid JSON on
# its own. Trimmed from the live page (deepswe.datacurve.ai, 2026-08-16) to
# the handful of fields this module actually persists, plus enough
# surrounding noise to prove the parser ignores everything else. The real
# page streams this via a TanStack Router payload (`self.$R[n]=`) as LITERAL
# (not JSON-string-escaped) JS source inside a <script> tag - verified
# against the live byte stream, not assumed - so this fixture's quoting
# matches that exactly. No network call in this test file.
DEEPSWE_FIXTURE_HTML = """
<html><body><script class="$tsr">(self.$R=self.$R||{})["tsr"]=[];</script>
<script>self.$R.tsr.push({data:"some unrelated leaderboard summary text",generated_at:"2026-08-13T16:11:55.708636+00:00",n_tasks_in_set:113,latest_job:$R[9]={name:"irrelevant"},rows:$R[10]=[$R[11]={model:"claude-opus-5",harness:"mini-swe-agent",reasoning_effort:"max",config:"mini_swe_agent_claude_opus_5_max",source:"deep-swe",pass_rate:0.7364864864864865,pass_at_1:0.7364864864864865,pass_at_4:0.8849557522123894,n_passed:327,n_attempted:444,n_tasks_attempted:113,n_tasks_passed_any:100,ci_passed:327,ci_attempted:444,ci_lo:0.6977633822227692,ci_hi:0.7752095907502038,ci_half:0.03872310426371729,n_runs:4,ci_method:"95% run-to-run: SE across repeated whole-benchmark passes (1.96 * std(runs)/sqrt(R))",mean_cost_usd:11.837583271396396,median_cost_usd:10.4281505,mean_output_tokens:117565.6936936937,median_output_tokens:113366.5,mean_input_tokens:15025834.39864865,median_input_tokens:12130307.5,mean_duration_seconds:1911.819866231982,median_duration_seconds:1801.1237265,mean_agent_steps:99.0427927927928,median_agent_steps:90.5,median_peak_context_tokens:215810,median_output_tokens_to_pass:112874},$R[12]={model:"claude-opus-5",harness:"mini-swe-agent",reasoning_effort:"medium",config:"mini_swe_agent_claude_opus_5_medium",source:"deep-swe",pass_rate:0.6891891891891891,pass_at_1:0.6891891891891891,n_passed:306,n_attempted:444,n_tasks_attempted:113,n_tasks_passed_any:97,ci_lo:0.65,ci_hi:0.72,n_runs:4,mean_cost_usd:3.29,median_cost_usd:3.1,mean_output_tokens:45000,median_output_tokens:44000},$R[13]={model:"gpt-5-6-sol",harness:"mini-swe-agent",reasoning_effort:"high",config:"mini_swe_agent_gpt_5_6_sol_high",source:"deep-swe",pass_rate:0.694,pass_at_1:0.694,n_passed:300,n_attempted:444,n_tasks_attempted:113,n_tasks_passed_any:95,ci_lo:0.65,ci_hi:0.74,n_runs:4,mean_cost_usd:3.47,median_cost_usd:3.2,mean_output_tokens:60000,median_output_tokens:59000}]});</script>
</body></html>
"""


def test_parse_deepswe_html_extracts_the_persisted_fields_from_a_captured_fixture():
    rows, meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    assert len(rows) == 3
    assert meta == {"generated_at": "2026-08-13T16:11:55.708636+00:00", "n_tasks_in_set": 113}

    opus_max = next(r for r in rows if r["model"] == "claude-opus-5" and r["reasoning_effort"] == "max")
    assert opus_max["pass_at_1"] == 0.7364864864864865
    assert opus_max["ci_lo"] == 0.6977633822227692
    assert opus_max["ci_hi"] == 0.7752095907502038
    assert opus_max["n_runs"] == 4
    assert opus_max["mean_cost_usd"] == 11.837583271396396
    assert opus_max["median_cost_usd"] == 10.4281505
    assert opus_max["median_output_tokens"] == 113366.5
    # Only the fields this module persists survive - not the full raw payload.
    assert set(opus_max) == set(cm._DEEPSWE_ROW_FIELDS)


def test_parse_deepswe_html_returns_empty_on_none_or_blank_input():
    assert cm.parse_deepswe_html(None) == ([], {})
    assert cm.parse_deepswe_html("") == ([], {})


def test_parse_deepswe_html_degrades_gracefully_on_a_wholesale_shape_change():
    # Simulates the DeepSWE frontend changing entirely - the leaderboard
    # anchor ('source:"deep-swe"') is gone, so nothing matches. Must yield
    # the same empty shape as a failed fetch, never raise.
    unrelated_html = "<html><body><h1>DeepSWE moved</h1><p>Nothing to see here.</p></body></html>"
    rows, meta = cm.parse_deepswe_html(unrelated_html)
    assert rows == []
    assert meta == {}


def test_parse_deepswe_html_skips_a_row_missing_a_model_field_never_crashes():
    html = '{harness:"mini-swe-agent",reasoning_effort:"max",source:"deep-swe",pass_at_1:0.5}'
    rows, _meta = cm.parse_deepswe_html(html)
    assert rows == []


def test_parse_deepswe_html_meta_absent_when_patterns_dont_match():
    html = 'rows:[{model:"x",source:"deep-swe",pass_at_1:0.5}]'
    rows, meta = cm.parse_deepswe_html(html)
    assert len(rows) == 1
    assert meta == {}


def test_build_deepswe_index_keys_by_model_and_effort_with_a_per_model_fallback():
    rows, _meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    by_key, by_model = cm.build_deepswe_index(rows)
    assert by_key[("claude-opus-5", "max")]["mean_cost_usd"] == 11.837583271396396
    assert by_key[("claude-opus-5", "medium")]["mean_cost_usd"] == 3.29
    assert by_key[("gpt-5-6-sol", "high")]["mean_cost_usd"] == 3.47
    # Fallback index: any row for that model (first one seen).
    assert by_model["claude-opus-5"]["reasoning_effort"] == "max"
    assert by_model["gpt-5-6-sol"]["reasoning_effort"] == "high"


def test_build_deepswe_index_empty_rows_yields_empty_indices():
    by_key, by_model = cm.build_deepswe_index([])
    assert by_key == {}
    assert by_model == {}
    by_key2, by_model2 = cm.build_deepswe_index(None)
    assert by_key2 == {}
    assert by_model2 == {}


def test_apply_deepswe_data_joins_on_url_slug_and_exact_variant_label():
    rows, _meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    by_key, by_model = cm.build_deepswe_index(rows)
    models = [
        {"url_slug": "claude-opus-5", "variant_label": "max"},
        {"url_slug": "claude-opus-5", "variant_label": "medium"},
        {"url_slug": "gpt-5-6-sol", "variant_label": "high"},
    ]
    cm.apply_deepswe_data(models, by_key, by_model)
    assert models[0]["deepswe_pass_at_1"] == round(0.7364864864864865, 4)
    assert models[0]["deepswe_cost_per_task_usd"] == round(11.837583271396396, 4)
    assert models[0]["deepswe_n_runs"] == 4
    assert models[1]["deepswe_cost_per_task_usd"] == 3.29
    assert models[2]["deepswe_cost_per_task_usd"] == 3.47


def test_apply_deepswe_data_does_not_borrow_another_efforts_measurement():
    """A variant with no DeepSWE row of its own must stay null.

    This previously fell back to any row for the model, which is how GPT-5.6
    Sol's "non-reasoning" variant came to claim the "max" run's pass@1 0.727
    at $8.39. Effort changes measured cost several-fold on the same model, so
    borrowing across efforts invents a result rather than reporting one.
    """
    rows, _meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    by_key, by_model = cm.build_deepswe_index(rows)
    models = [{"url_slug": "claude-opus-5", "variant_label": "xhigh"}]
    cm.apply_deepswe_data(models, by_key, by_model)
    assert models[0].get("deepswe_pass_at_1") is None


def test_apply_deepswe_data_leaves_every_field_null_for_an_unmatched_model():
    rows, _meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    by_key, by_model = cm.build_deepswe_index(rows)
    models = [
        {
            "url_slug": "totally-untracked-model",
            "variant_label": None,
            "deepswe_pass_at_1": None,
            "deepswe_cost_per_task_usd": None,
        }
    ]
    cm.apply_deepswe_data(models, by_key, by_model)
    assert models[0]["deepswe_pass_at_1"] is None
    assert models[0]["deepswe_cost_per_task_usd"] is None


def test_apply_deepswe_data_never_invents_a_value_for_a_row_with_no_url_slug():
    models = [{"url_slug": None, "variant_label": "max"}]
    by_key, by_model = cm.build_deepswe_index([{"model": "claude-opus-5", "reasoning_effort": "max", "pass_at_1": 0.5}])
    cm.apply_deepswe_data(models, by_key, by_model)
    assert "deepswe_pass_at_1" not in models[0] or models[0].get("deepswe_pass_at_1") is None


def test_deepswe_join_stats_counts_joined_models_and_unjoined_untracked_rows():
    rows, _meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    by_key, by_model = cm.build_deepswe_index(rows)
    models = [
        {"url_slug": "claude-opus-5", "variant_label": "max"},
        {"url_slug": "claude-opus-5", "variant_label": "medium"},
        # gpt-5-6-sol is intentionally absent from the catalog - its
        # DeepSWE row should be counted as unjoined.
    ]
    cm.apply_deepswe_data(models, by_key, by_model)
    joined, unjoined = cm.deepswe_join_stats(models, rows)
    assert joined == 2
    assert unjoined == 1  # gpt-5-6-sol's row never matched any catalog url_slug


def test_deepswe_join_stats_zero_rows_yields_zero_zero():
    assert cm.deepswe_join_stats([], []) == (0, 0)


def test_finalize_model_defaults_every_deepswe_field_to_null():
    row = {"slug": "s", "name": "S"}
    out = cm.finalize_model(row)
    for field in (
        "deepswe_pass_at_1",
        "deepswe_ci_lo",
        "deepswe_ci_hi",
        "deepswe_n_runs",
        "deepswe_cost_per_task_usd",
        "deepswe_median_cost_usd",
        "deepswe_output_tokens",
    ):
        assert out[field] is None


def test_build_output_threads_deepswe_data_through_the_full_pipeline():
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    lmarena_idx = {"m1": _arena_entry("m1", "claude-opus-5-max")}
    rows, _meta = cm.parse_deepswe_html(DEEPSWE_FIXTURE_HTML)
    by_key, by_model = cm.build_deepswe_index(rows)
    output = cm.build_output(
        lmarena_idx=lmarena_idx,
        aa_idx={},
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta={"available": True},
        aa_meta={"available": False},
        variant_vocab=VARIANT_VOCAB,
        frontier_metrics=[
            {"key": "deepswe_pass_at_1", "source": "top", "cost_field": "deepswe_cost_per_task_usd", "cost_basis": "measured_per_task"}
        ],
        deepswe_meta={"available": True, "attribution": "DeepSWE", "url": "https://deepswe.datacurve.ai/"},
        deepswe_by_key=by_key,
        deepswe_by_model=by_model,
    )
    assert output["sources"]["deepswe"]["available"] is True
    model = output["models"][0]
    assert model["url_slug"] == "claude-opus-5"
    assert model["deepswe_pass_at_1"] == round(0.7364864864864865, 4)
    assert model["frontier"]["deepswe_pass_at_1"]["cost_basis"] == "measured_per_task"
    assert model["frontier"]["deepswe_pass_at_1"]["on_frontier"] is True


def test_build_output_deepswe_sources_defaults_to_empty_dict_without_config():
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    output = cm.build_output(
        lmarena_idx={"m1": _arena_entry("m1", "Model One")},
        aa_idx={},
        aliases={},
        recency_days=90,
        max_models=10,
        now=now,
        lmarena_meta={"available": True},
        aa_meta={"available": False},
    )
    assert output["sources"]["deepswe"] == {}
    assert output["models"][0]["deepswe_pass_at_1"] is None


# ---------------------------------------------------------------------------
# The real config/models.yaml frontier_metrics contract (WORK ITEM 2,
# 2026-08-17): a frontier may only be claimed where the cost is a MEASURED
# per-task figure - every per_token_price_proxy entry is gone, and
# deepswe_pass_at_1/measured_per_task is the sole survivor.
# ---------------------------------------------------------------------------

def test_real_config_frontier_metrics_has_no_per_token_price_proxy_entries():
    cfg = cm.load_config()
    bases = {entry.get("cost_basis") for entry in cfg["frontier_metrics"]}
    assert "per_token_price_proxy" not in bases


def test_real_config_frontier_metrics_deepswe_pass_at_1_is_measured_per_task():
    cfg = cm.load_config()
    entries = {entry["key"]: entry for entry in cfg["frontier_metrics"]}
    assert "deepswe_pass_at_1" in entries
    entry = entries["deepswe_pass_at_1"]
    assert entry["cost_basis"] == "measured_per_task"
    assert entry["cost_field"] == "deepswe_cost_per_task_usd"
    assert entry["source"] == "top"


def test_real_config_frontier_metrics_no_longer_lists_aa_metrics():
    # AA-scored metrics still display everywhere they always have (the
    # ranked list, the scores table) - they just no longer claim a frontier,
    # since their cost pairing was never a measured per-task figure.
    cfg = cm.load_config()
    keys = {entry["key"] for entry in cfg["frontier_metrics"]}
    assert keys == {"deepswe_pass_at_1"}


def test_real_config_deepswe_source_is_present_and_config_driven():
    cfg = cm.load_config()
    deepswe_cfg = cfg["sources"]["deepswe"]
    assert deepswe_cfg["enabled"] is True
    assert deepswe_cfg["base_url"].startswith("https://")
    assert "Datacurve" in deepswe_cfg["attribution"]


def test_apply_deepswe_data_requires_an_exact_variant_match():
    """A measured result belongs to the configuration that produced it.

    DeepSWE spans $11.84/task (max) to $3.29/task (medium) on ONE model, so
    attaching one effort's row to another variant fabricates a result.
    """
    models = [
        {"url_slug": "gpt-5-6-sol", "variant_label": "max"},
        {"url_slug": "gpt-5-6-sol", "variant_label": "non-reasoning"},
    ]
    max_row = {"pass_at_1": 0.7267, "mean_cost_usd": 8.3864, "reasoning_effort": "max"}
    cm.apply_deepswe_data(models, {("gpt-5-6-sol", "max"): max_row}, {"gpt-5-6-sol": max_row})
    assert models[0]["deepswe_pass_at_1"] == 0.7267
    assert "deepswe_pass_at_1" not in models[1] or models[1]["deepswe_pass_at_1"] is None


def test_apply_deepswe_data_allows_an_unversioned_row_for_an_unversioned_model():
    models = [{"url_slug": "solo-model", "variant_label": None}]
    row = {"pass_at_1": 0.5, "mean_cost_usd": 1.0, "reasoning_effort": ""}
    cm.apply_deepswe_data(models, {}, {"solo-model": row})
    assert models[0]["deepswe_pass_at_1"] == 0.5


def test_unversioned_model_takes_a_variant_row_but_discloses_the_effort():
    """DeepSWE measures efforts our other sources do not publish as rows.

    Discarding those would lose real measurements for ~9 models, so an
    unversioned catalog row adopts the run - but `deepswe_effort` must record
    which configuration produced it, so the score is never read as the
    model's only behavior.
    """
    models = [{"url_slug": "m", "variant_label": None}]
    row = {"pass_at_1": 0.9, "mean_cost_usd": 5.0, "reasoning_effort": "max"}
    cm.apply_deepswe_data(models, {("m", "max"): row}, {"m": row})
    assert models[0]["deepswe_pass_at_1"] == 0.9
    assert models[0]["deepswe_cost_per_task_usd"] == 5.0
    assert models[0]["deepswe_effort"] == "max"


DEEPSWE_ROWS_FOR_BEST = {
    ("claude-fable-5", "max"): {"pass_at_1": 0.697, "mean_cost_usd": 21.63, "reasoning_effort": "max"},
    ("claude-fable-5", "xhigh"): {"pass_at_1": 0.699, "mean_cost_usd": 13.41, "reasoning_effort": "xhigh"},
    ("claude-fable-5", "low"): {"pass_at_1": 0.41, "mean_cost_usd": 2.10, "reasoning_effort": "low"},
}


def test_unversioned_row_takes_the_best_run_with_that_runs_own_cost():
    """Score and cost must come from ONE execution, and the effort is disclosed."""
    models = [{"url_slug": "claude-fable-5", "variant_label": None}]
    cm.apply_deepswe_data(models, dict(DEEPSWE_ROWS_FOR_BEST), {})
    m = models[0]
    assert m["deepswe_pass_at_1"] == 0.699          # best score (xhigh)
    assert m["deepswe_cost_per_task_usd"] == 13.41  # THAT run's cost, not max's 21.63
    assert m["deepswe_effort"] == "xhigh"


def test_versioned_row_still_refuses_to_borrow_another_effort():
    models = [{"url_slug": "claude-fable-5", "variant_label": "medium"}]
    cm.apply_deepswe_data(models, dict(DEEPSWE_ROWS_FOR_BEST), {})
    assert models[0].get("deepswe_pass_at_1") is None


def test_best_deepswe_row_breaks_ties_on_lower_cost():
    rows = {
        ("m", "a"): {"pass_at_1": 0.5, "mean_cost_usd": 9.0, "reasoning_effort": "a"},
        ("m", "b"): {"pass_at_1": 0.5, "mean_cost_usd": 3.0, "reasoning_effort": "b"},
    }
    assert cm.best_deepswe_row_for_model(rows, {}, "m")["reasoning_effort"] == "b"


def test_source_regressions_ignores_a_deliberately_disabled_source():
    """Disabling a source is an operator decision, not a data regression.

    Counting it as one made the write-guard refuse every later write, so the
    artifact froze silently while the collector kept exiting 0.
    """
    prev = {"sources": {"deepswe": {"available": True}, "lmarena": {"available": True}}}
    new = {"sources": {"deepswe": {"available": False}, "lmarena": {"available": True}}}
    assert cm.source_regressions(new, prev, {"lmarena"}) == []


def test_source_regressions_still_catches_an_enabled_source_going_dark():
    prev = {"sources": {"lmarena": {"available": True}}}
    new = {"sources": {"lmarena": {"available": False}}}
    assert cm.source_regressions(new, prev, {"lmarena"}) == ["lmarena"]


FRONTIER_METRIC_CFG = [{
    "key": "deepswe_pass_at_1",
    "cost_field": "deepswe_cost_per_task_usd",
    "cost_basis": "measured_per_task",
}]


def _fm_row(slug, variant, cap, cost):
    return {
        "url_slug": slug,
        "variant_label": variant,
        "deepswe_pass_at_1": cap,
        "deepswe_cost_per_task_usd": cost,
    }


def test_frontier_records_the_qualifying_variant_not_the_representative():
    """Surfaces must not have to guess which variant earned the badge.

    GPT-5.6 Sol reaches the frontier at high/xhigh while its pricier `max`
    run is dominated; publishing the badge without naming the variant let the
    ranked list quote $8.39 and the detail page $4.70 for the same claim.
    """
    rows = [
        _fm_row("gpt-5-6-sol", "max", 0.7267, 8.3864),
        _fm_row("gpt-5-6-sol", "xhigh", 0.7073, 4.7037),
        _fm_row("gpt-5-6-sol", "high", 0.6940, 3.4698),
        # Cheaper AND better than sol's `max`, so `max` is dominated and
        # xhigh becomes this model's best qualifying showing.
        _fm_row("rival", None, 0.7300, 8.0),
    ]
    out = cm.compute_frontier(rows, FRONTIER_METRIC_CFG)
    entry = out["gpt-5-6-sol"]["deepswe_pass_at_1"]
    assert entry["on_frontier"] is True
    # The most capable qualifying variant, not the cheapest: `max` is
    # dominated by the rival, so xhigh is this model's best frontier showing.
    assert entry["qualifying_variant"] == "xhigh"
    assert entry["qualifying_cost"] == 4.7037
    assert entry["qualifying_metric_value"] == 0.7073


def test_frontier_qualifying_prefers_capability_over_a_trivially_cheap_run():
    """A near-zero-score, near-zero-cost run is non-dominated but useless."""
    rows = [
        _fm_row("luna", "low", 0.0155, 0.0145),
        _fm_row("luna", "max", 0.6719, 0.6056),
    ]
    out = cm.compute_frontier(rows, FRONTIER_METRIC_CFG)
    entry = out["luna"]["deepswe_pass_at_1"]
    assert entry["qualifying_variant"] == "max"


def test_frontier_leaves_qualifying_fields_null_when_behind():
    rows = [
        _fm_row("cheap-and-better", None, 0.9, 1.0),
        _fm_row("loser", None, 0.5, 5.0),
    ]
    out = cm.compute_frontier(rows, FRONTIER_METRIC_CFG)
    entry = out["loser"]["deepswe_pass_at_1"]
    assert entry["on_frontier"] is False
    assert entry["qualifying_variant"] is None
    assert entry["qualifying_cost"] is None
