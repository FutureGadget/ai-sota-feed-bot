#!/usr/bin/env python3
"""Model Release Radar - Step 1: collect + join model data.

Decision (docs/ideas/model-release-radar.md, 2026-08-05): a `/models` page
answers "a new model just dropped - is it real, what does it cost, and
should I route to it?" in one screen. This module is the deterministic data
layer feeding that page: it pulls community-voted Elo from LMArena (keyless,
via the Hugging Face datasets-server REST API) and, when a key is available,
capability/price/spec data from Artificial Analysis, then joins the two on a
normalized model-name slug.

Artificial Analysis is OPTIONAL. When AA_API_KEY is absent, `collect` still
succeeds using LMArena alone: AA-derived fields are written as null and
sources.artificial_analysis.available is false. The collector never crashes
and never exits nonzero for a missing key - see `cmd_collect`.

Blended price: Artificial Analysis publishes `pricing.price_1m_blended_3_to_1`
- a 3:1 input:output token weighting that matches a typical RAG/agent
workload where prompts (context, retrieved docs, tool results) dominate
token volume over completions - and `finalize_model` prefers that published
value when present. When AA is unavailable or omits it, the collector falls
back to computing the same 3:1 blend itself locally
(`(3 * price_input + price_output) / 4`, see `blended_price`). This blended
number drives the Pareto-chart X axis in later steps, so the weighting is
documented here rather than buried in a constant.

Joining: LMArena and Artificial Analysis spell model names differently, and
AA's own `slug` and `name` disagree with each other about how much of a
model's variant they carry (AA slug "gpt-5-6-sol-medium" vs AA name
"GPT-5.6 Sol (medium)", vs a max variant only the slug "gpt-5-6-luna" spells
out - AA's name for that one drops the variant entirely). `build_aa_index`
handles this by indexing every AA model under BOTH its normalized slug
(primary key) and its normalized name (secondary key, which never overwrites
a slug-claimed entry - see the function docstring). `normalize_slug`
collapses case/punctuation/separators into one comparable key so separator
style never causes a false mismatch. `config/models.yaml`'s `aliases` map is
the final hand-maintained override for whatever normalization still misses.
Unjoined models still appear in the output with `joined_sources` showing
what did and did not match, so join gaps are visible rather than silently
dropped.

open_weights: Artificial Analysis is the only source with an explicit
open-weights boolean, but it is confirmed absent on our (free) tier - see
`AA_FIELDS_UNAVAILABLE_ON_FREE_TIER`. LMArena's `license` field already
answers this for every model with no key required (e.g. "Proprietary" vs
"MIT"/"Apache 2.0"). `classify_open_weights` uses AA's boolean when present
(so a future higher tier that adds this field is picked up automatically,
no code change needed); otherwise it derives the value from `license` via
the `license_classification` block in `config/models.yaml` (a
case-insensitive `proprietary_markers` substring denylist, plus an
`unknown_markers` escape hatch that forces null instead of guessing); a
missing/unrecognized license also stays null. This means open_weights is
populated in the default no-AA-key path, not just once a key is configured.

recency_days: only Artificial Analysis supplies `release_date` - LMArena
rows never carry one. In the no-AA-key path every model's release_date is
null, so `select_models` falls back entirely to LMArena overall rank and
`max_models` is what actually bounds inclusion. `recency_days` is not dead
code: it activates automatically, with no code change, once AA_API_KEY is
configured and models start carrying real release dates.

base_slug / variant_label: both sources publish one catalog row per
reasoning-effort variant of the same underlying model ("GPT-5.6 Sol
(medium)", "gpt-5.6-sol-xhigh", "GPT-5.6 Sol (high)" are three rows for one
model). `derive_base_variant` splits a row's `name` into a `base_slug` (the
model identity with the variant stripped) and a `variant_label`, using the
`variant_vocabulary` block of config/models.yaml - never a hardcoded list in
Python, since labs keep inventing new effort names. It is conservative: a
trailing parenthetical or suffix is only ever stripped when it normalizes to
a token the vocabulary recognizes, so real distinguishing tokens (Gemini's
"-lite", Qwen's "-max" tier, GPT's "-instant"/"-mini") are left alone and
that model keeps its own base_slug. These are additive grouping keys only -
every row keeps its own full identity and no row is ever dropped from the
artifact; `web/models.html` and the feed sidebar use base_slug to collapse
the *presentation* to one row per real model.

display_name: once variants collapse to one row per model (see above), that
surviving row's own `name` is whichever source it happened to come from -
an AA verbose string ("Claude Opus 5 (Adaptive Reasoning, Max Effort)"), an
AA name with a plain parenthetical ("GPT-5.6 Sol (medium)"), or a LMArena
lowercase-dashed slug ("claude-fable-5", "gpt-5.6-sol-xhigh") - so a single
list mixes three naming conventions, and the surviving variant text is
redundant with the "+N variants" badge the collapse already renders.
`derive_display_name` computes a clean, human-readable BASE name once per
row, purely additive (the raw `name` field is never touched - callers that
depend on it, e.g. the join key or API consumers, are unaffected). It
prefers Artificial Analysis's own `name` (title-cased, human-written) when
the model has any AA contribution - even on a row joined via LMArena, where
the *emitted* `name` field is intentionally the LMArena slug (see
`AA_ROW_MERGE_EXCLUDED_FIELDS`) - by threading AA's raw name through
`join_models` as the additional `aa_name` key (internal to this module,
never part of the published row). On that path the only work is stripping a
*recognized* variant (reusing `derive_base_variant`'s own matching, via the
shared `_split_recognized_variant` helper, so display_name and
variant_label always agree on what counts as a variant) and trimming
whitespace - AA's casing is trusted as-is. When no AA name is available,
`name` is a LMArena slug and needs conversion: `_display_case_words` splits
it on separators and titlecases each word, except (a) a word already
containing any uppercase letter is left untouched (never re-cases something
that was already deliberately cased, e.g. "Motif" or "OpenAI"), (b) a word
found in `config/models.yaml`'s `acronym_casing` map (never a hardcoded
Python list - labs keep inventing new brand names) uses that casing exactly
("gpt" -> "GPT", "deepseek" -> "DeepSeek"), and (c) a version-shaped token
(digits with optional dot groups, optionally prefixed with a bare "v") is
never re-cased beyond capitalizing a leading "v" ("5.2" stays "5.2", "v4"
becomes "V4") and is joined to an immediately preceding acronym-cased word
with a dash rather than a space, matching the conventional brand-version
spelling ("glm-5.2-max" -> "GLM-5.2", "deepseek-v4-flash" ->
"DeepSeek-V4 Flash") while an ordinary word before a number still gets a
space ("claude-fable-5" -> "Claude Fable 5"). `finalize_model` falls back to
the raw `name` verbatim if this ever produces nothing usable, so
display_name is never null when a name exists.

Zero prices: Artificial Analysis emits `0` (not null) for a model whose
per-token pricing simply is not published, most often small/experimental
open-weight releases. A price of exactly 0 is treated as unknown (null)
everywhere prices are read - see `zero_price_to_null` - both because "$0"
would be a lie (nothing is actually free) and because 0 is undefined on the
/models page's log-scale price axis, where it would otherwise trivially
dominate the cheap end of the Pareto frontier.

organization aliasing: LMArena and Artificial Analysis sometimes name the
same real-world lab differently (AA's "kimi" vs LMArena's "moonshot" for
Moonshot AI, etc). `config/models.yaml`'s `organization_aliases` (hand
verified against live join collisions, same spirit as `aliases`) normalizes
the organization field at finalize time so one lab never splits into two
rows on the page.

benchmarks: Artificial Analysis's `evaluations` block carries the two
blended composites this module has always captured (`aa_intelligence_index`,
`aa_coding_index`) alongside a long tail of individual raw benchmark scores
(`livecodebench`, `tau2`, `terminalbench_v2_1`, `gpqa`, ...) at no extra
request cost. `extract_aa_benchmarks` persists whichever of those the
`sources.artificial_analysis.benchmarks` list in `config/models.yaml` names
(never a hardcoded Python list, since AA adds/renames benchmarks over time)
into a per-row `benchmarks` dict, omitting any AA reports as null for that
model rather than zero-filling or inventing a value - a model AA has no
benchmark data for at all gets `benchmarks: {}`. SCALE WARNING: these raw
benchmarks are 0-1 fractions, a different scale from the ~0-100 blended
indices - see `config/models.yaml` for the full rationale. This is purely
additive: `aa_intelligence_index`/`aa_coding_index` are unchanged and remain
the fields the page and sidebar already consume.

url_slug: the stable, human-readable, URL-safe identifier a later step's
`/models/<slug>` detail page reads and `api/models.js`'s `?slug=` lookup
already validates against `SLUG_RE`. Assigned ONE PER BASE MODEL (per
`base_slug` group), not per row: the product is one detail page per real
model, and every reasoning-effort variant row of that model - already
collapsed together in the `web/models.html` presentation layer's "+N
variants" badge - shares the SAME `url_slug`. `assign_url_slugs` derives
each group's slug from a deterministically-chosen representative row's
`display_name` (falling back to `name`, then the existing normalized
`slug` - never empty while any of the three has a value on any row in the
group), lowercasing and collapsing every non-alphanumeric run to a single
dash via `slugify`. Per-row grouping was tried first and rejected: it
minted a separate URL per variant (`claude-opus-5`, `claude-opus-5-2`, ...
one per effort level), which is both meaningless to a reader (which
variant "wins" the bare slug is arbitrary) and NOT stable in the way that
matters for a public URL - retiring one upstream variant renumbers its
surviving siblings and breaks every previously-published link to them (see
the "drop a row from a variant group" stability test). Grouping by
`base_slug` avoids that: a collision can now only happen between two
genuinely DIFFERENT base models whose clean display names happen to match
(rare), and every group is still processed in a STABLE order - sorted by
its candidate slug text, tiebroken by its `base_slug` - with a colliding
candidate getting a numeric "-2", "-3", ... suffix appended until free.
Deriving purely from each group's own identity (never list position,
index, ordering, or run timestamp) and resolving collisions in that same
identity-sorted order is what keeps a slug STABLE across refresh runs, and
what makes a genuine collision's resolution depend only on one of the two
colliding base models disappearing entirely - never on variant churn
within either one. No row is ever dropped to avoid a collision.

frontier: server-side Pareto frontier membership, computed once here so the
ranked list, the detail pages, the static renderer, and the chart all read
ONE answer instead of each re-deriving it (and risking disagreement) -
mirrors the ascending-cost walk `web/models.html`'s `paretoFrontier()` has
always run client-side, now also computed in the data layer. Emitted as
`frontier: {<metric_key>: {cost_field, cost_basis, on_frontier,
dominated_by}, ...}` per BASE MODEL (one entry per `url_slug`, matching the
one-slug-per-model contract above), one metric key per entry in
`config/models.yaml`'s `frontier_metrics` list (config-driven, never
hardcoded).

The `cost_field`/`cost_basis` pair on every entry exists because a raw
per-1M-token price is NOT a fair X axis for an agentic benchmark score: the
cost of running a task depends on how many tokens and steps a model actually
spends, not just its per-token rate (proof from live DeepSWE data,
2026-08-16: claude-opus-5 costs $11.84/task at "max" reasoning effort and
$3.29/task at "medium", yet both price identically at $10/1M tokens - a
per-token axis cannot see that difference at all). A frontier is therefore
only ever computed for a metric whose `cost_basis` is a genuine MEASURED
per-task cost (`cost_basis: "measured_per_task"`) - today that is exactly
one entry, `deepswe_pass_at_1` paired with `deepswe_cost_per_task_usd` (see
the "DeepSWE" section below). Every AA-scored metric (`aa_intelligence_index`,
`aa_coding_index`, the raw benchmarks) previously carried a
`cost_basis: "per_token_price_proxy"` frontier entry paired against
`price_blended_per_1m`; those entries are gone from `config/models.yaml`
entirely (2026-08-17), not merely relabeled - a benchmark with no measured
per-task cost source no longer gets an "on/behind frontier" claim, even
though its score still displays everywhere it always has (the ranked list
still ranks by AA intelligence index by default, the scores table still
shows every AA benchmark). The `cost_basis` machinery itself is unchanged
and stays config-driven for exactly this reason: a future benchmark that
gains a real per-task cost source lights up here automatically with a
`config/models.yaml` change, never a code change - see `compute_frontier`.

DeepSWE (added 2026-08-17): DeepSWE (Datacurve) runs real agentic
coding tasks end to end and publishes the actual dollar cost of running
them (`mean_cost_usd`/`median_cost_usd` per task), alongside `pass_at_1`,
`ci_lo`/`ci_hi`, and `n_runs`, one row per (model, reasoning_effort) - this
is the first (and so far only) source this module has for a MEASURED
per-task cost, which is what unlocks the frontier described above. DeepSWE
publishes no documented JSON API (verified 2026-08-16: `/api/leaderboard`
404s, the Hugging Face dataset `datacurve/deep-swe` is now gated, and the
GitHub repo has no aggregated results file) - the rows are parsed out of a
React Flight payload embedded in the leaderboard page's server-rendered HTML
by `parse_deepswe_html`, which is deliberately defensive: it locates each
row by its own `source:"deep-swe"` anchor (not by a `$R[n]=` reference
number, which can shift on any DeepSWE redeploy) and skips - never crashes
on - anything that fails to parse; a wholesale shape change degrades to zero
rows parsed, exactly like a failed fetch (see `fetch_deepswe_html`,
`config/models.yaml`'s `sources.deepswe` comment, and
`source_regressions`'s write-guard, which covers this source the same as
lmarena/artificial_analysis). One request per collect run.

Joining: DeepSWE's own `model` and `reasoning_effort` values already match
this module's `url_slug` and `variant_label` conventions directly (verified
live 2026-08-16: "claude-opus-5", "gpt-5-6-sol", "gpt-5-6-terra",
"claude-fable-5" as `model`; "max"/"high"/"medium"/"low"/"xhigh" as
`reasoning_effort`, matching `variant_vocabulary`'s canonical labels
exactly) - so the join (`apply_deepswe_data`, via `build_deepswe_index`) is
a direct `(url_slug, variant_label)` key match, no normalization or alias
layer needed, unlike the LMArena/AA join. A catalog row whose own
reasoning-effort variant has no exact DeepSWE match falls back to
`deepswe_by_model[url_slug]` (any DeepSWE row for that model, chosen
deterministically - first one encountered in the parsed row order) rather
than going without a cost - a less precise but still real measured figure
beats none. Persisted per model row: `deepswe_pass_at_1`, `deepswe_ci_lo`,
`deepswe_ci_hi`, `deepswe_n_runs`, `deepswe_cost_per_task_usd` (DeepSWE's
`mean_cost_usd`), `deepswe_median_cost_usd`, `deepswe_output_tokens`
(DeepSWE's `median_output_tokens`) - all null (never invented) for a model
DeepSWE has no data for. The run's own `generated_at`/`n_tasks_in_set` are
persisted in `sources.deepswe`, not per row. A DeepSWE row whose `model`
never matches any tracked catalog model's `url_slug` is visible, not
silently dropped - `deepswe_join_stats` counts it and `cmd_collect` logs the
count.

Computed in two phases (see `compute_frontier`). First, PER-VARIANT: every
row with both the metric and its paired cost is a Pareto-optimality point
(no OTHER point is cheaper-or-equal AND at least as capable, with at least
one strict improvement) - equivalent in outcome to `web/models.html`'s
ascending-cost walk on real data (verified live 2026-08-16), computed as a
direct domination check instead of a literal port of that walk because the
walk has no secondary sort key and can mark two equal-cost rows both
"frontier" even when one strictly dominates the other. A sibling variant of
the SAME model (same `url_slug`) is NEVER counted as a dominator here - a
model cannot be "dominated by itself" now that its variants share a slug.
Second, PER-MODEL aggregation: a base model is `on_frontier` for a metric
if ANY of its variant rows is; `dominated_by` is the union of every
non-frontier variant's dominators, mapped to THEIR (also now per-model)
`url_slug`s, deduplicated, nearest-cost-first, and capped by
`config/models.yaml`'s `frontier_dominated_by_cap` - populated only when
the model itself is not on the frontier, so a detail page can answer "why
isn't this model on the frontier" precisely without ever naming itself. A
model missing either the metric or its paired cost on every one of its
variant rows is simply ABSENT from that metric's frontier dict - never
written with a null/false placeholder, matching the zero-price-to-null
precedent above: a missing value is never treated as a comparable number.

Commands:
  collect  fetch LMArena (+ Artificial Analysis if AA_API_KEY is set),
           join, and write data/models/latest.json + a dated history snapshot
  summary  print the currently stored models as a table

Artificial Analysis response shape (GET /api/v2/data/llms/models, header
`x-api-key`), verified live 2026-08-05 against ~591 models: top level
{"status", "prompt_options", "data": [...]}; each model carries "id",
"name", "slug", "release_date", "model_creator": {"id", "name", "slug"},
"evaluations": {...index/benchmark scores...}, "pricing":
{"price_1m_blended_3_to_1", "price_1m_input_tokens",
"price_1m_output_tokens"}, and top-level "median_output_tokens_per_second".
Confirmed absent on this tier: context_window_tokens, parameters_total,
parameters_active, and open_weights - see
`AA_FIELDS_UNAVAILABLE_ON_FREE_TIER`. `extract_aa_field` still probes a
short list of plausible key paths per field (verified path listed first)
rather than hardcoding a single path, so a future AA response shape change -
or a higher tier that adds the fields above - degrades to "not found"
instead of crashing, and the `models_collect_aa_fields_unmapped` warning
stays meaningful for fields that are genuinely supposed to be there.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "models.yaml"
LATEST_PATH = ROOT / "data" / "models" / "latest.json"
HISTORY_DIR = ROOT / "data" / "models" / "history"

DEFAULT_CONFIG = {
    "sources": {
        "lmarena": {
            "enabled": True,
            "dataset": "lmarena-ai/leaderboard-dataset",
            "config": "text",
            "split": "latest",
            "base_url": "https://datasets-server.huggingface.co",
            "categories": ["overall", "coding"],
            "page_size": 100,
            "attribution": "LMArena (arena.ai) - community-voted model preference",
        },
        "artificial_analysis": {
            "enabled": True,
            "base_url": "https://artificialanalysis.ai/api/v2/data/llms/models",
            "api_key_env": "AA_API_KEY",
            "attribution": "Artificial Analysis (https://artificialanalysis.ai/) - independent benchmarking",
            "benchmarks": [],
        },
        "deepswe": {
            "enabled": True,
            "base_url": "https://deepswe.datacurve.ai/",
            "attribution": "DeepSWE / Datacurve (https://deepswe.datacurve.ai/) - measured cost per task on real agentic coding tasks",
        },
    },
    "request_timeout_seconds": 20,
    "trust_env_proxies": False,
    "recency_days": 90,
    "max_models": 200,
    "aliases": {},
    "license_classification": {
        "proprietary_markers": ["proprietary"],
        "unknown_markers": ["unknown", "unspecified"],
    },
    "variant_vocabulary": {"tokens": {}, "effort_phrases": []},
    "organization_aliases": {},
    "acronym_casing": {},
    "axis_metric_options": [],
    "frontier_metrics": [],
    "frontier_dominated_by_cap": 5,
}

# Plausible key paths (each a tuple of nested keys) to probe for each
# Artificial Analysis field. Verified path listed first per field (see
# module docstring); the rest are defensive fallbacks in case the response
# shape changes. `extract_aa_field` returns the first match.
AA_FIELD_PATHS: dict[str, list[tuple[str, ...]]] = {
    "name": [("name",), ("model_name",), ("slug",), ("model",)],
    "slug": [("slug",), ("model_slug",)],
    "release_date": [
        ("release_date",),
        ("releaseDate",),
        ("model", "release_date"),
        ("metadata", "release_date"),
    ],
    # Prefer model_creator.slug so a joined row's organization matches the
    # lowercase-slug convention LMArena rows already use ("anthropic",
    # "openai", "google"); model_creator.name is the fallback for an AA-only
    # row if slug is ever absent.
    "organization": [
        ("model_creator", "slug"),
        ("model_creator", "name"),
    ],
    # Confirmed absent on the free tier as of 2026-08-05 - see
    # AA_FIELDS_UNAVAILABLE_ON_FREE_TIER. Kept here (not removed from the
    # probe list) so a future tier change is picked up automatically.
    "context_window_tokens": [
        ("context_window_tokens",),
        ("context_window",),
        ("specs", "context_window_tokens"),
        ("metadata", "context_window_tokens"),
    ],
    "parameters_total": [
        ("parameters", "total"),
        ("parameters_total",),
        ("total_parameters",),
        ("specs", "parameters", "total"),
    ],
    "parameters_active": [
        ("parameters", "active"),
        ("parameters_active",),
        ("active_parameters",),
        ("specs", "parameters", "active"),
    ],
    "open_weights": [
        ("open_weights",),
        ("is_open_weights",),
        ("licensing", "open_weights"),
        ("metadata", "open_weights"),
    ],
    "aa_intelligence_index": [
        ("evaluations", "artificial_analysis_intelligence_index"),
        ("artificial_analysis_intelligence_index",),
        ("intelligence_index",),
        ("scores", "intelligence_index"),
    ],
    "aa_coding_index": [
        ("evaluations", "artificial_analysis_coding_index"),
        ("artificial_analysis_coding_index",),
        ("coding_index",),
        ("scores", "coding_index"),
    ],
    "price_input_per_1m": [
        ("pricing", "price_1m_input_tokens"),
        ("pricing", "input_per_token"),
        ("pricing", "input"),
        ("price_input_per_1m",),
    ],
    "price_output_per_1m": [
        ("pricing", "price_1m_output_tokens"),
        ("pricing", "output_per_token"),
        ("pricing", "output"),
        ("price_output_per_1m",),
    ],
    # AA's own 3:1 blend - see `finalize_model` and the module docstring for
    # why this is preferred over the locally computed `blended_price`.
    "price_blended_per_1m": [
        ("pricing", "price_1m_blended_3_to_1"),
    ],
    "median_output_tokens_per_second": [
        ("median_output_tokens_per_second",),
        ("performance", "median_output_tokens_per_second"),
        ("speed", "median_output_tokens_per_second"),
    ],
}

# AA fields confirmed absent from the free tier (verified live 2026-08-05
# across all 591 models). They stay in AA_FIELD_PATHS above so probing keeps
# picking them up for free the moment a higher tier (or an AA response
# change) adds them - see `split_missing_aa_fields`, which keeps them out of
# the `models_collect_aa_fields_unmapped` anomaly warning (that warning
# firing on every single run trains the operator to ignore it) while still
# logging a calm one-line note so the gap stays visible.
AA_FIELDS_UNAVAILABLE_ON_FREE_TIER = frozenset(
    {"context_window_tokens", "parameters_total", "parameters_active", "open_weights"}
)

# Fields join_models merges with custom logic instead of the generic
# per-field copy: "name"/"slug" are join keys (the LMArena side owns the
# emitted value for a joined row), and "organization" fills a gap rather
# than blindly overwriting an LMArena organization that is already present.
AA_ROW_MERGE_EXCLUDED_FIELDS = frozenset({"name", "slug", "organization"})

BLEND_INPUT_WEIGHT = 3
BLEND_OUTPUT_WEIGHT = 1


def split_missing_aa_fields(missing_fields: set[str]) -> tuple[set[str], set[str]]:
    """Split build_aa_index's missing-field set into (genuinely_unmapped,
    known_unavailable).

    genuinely_unmapped is worth the loud models_collect_aa_fields_unmapped
    warning - those fields are supposed to be reachable and are not.
    known_unavailable is expected on this tier (AA_FIELDS_UNAVAILABLE_ON_FREE_TIER)
    and only worth a calm note, so the warning stays meaningful instead of
    firing on every run.
    """
    known_unavailable = missing_fields & AA_FIELDS_UNAVAILABLE_ON_FREE_TIER
    genuinely_unmapped = missing_fields - AA_FIELDS_UNAVAILABLE_ON_FREE_TIER
    return genuinely_unmapped, known_unavailable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        loaded = {}
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy of defaults
    cfg.update({k: v for k, v in loaded.items() if k != "sources"})
    for name, src_cfg in (loaded.get("sources") or {}).items():
        cfg["sources"].setdefault(name, {})
        cfg["sources"][name].update(src_cfg or {})
    return cfg


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without network)
# ---------------------------------------------------------------------------

def normalize_slug(name: str | None) -> str:
    """Collapse a model name into a comparable join key.

    Lowercases and strips every non-alphanumeric character, so separator
    style (dashes, dots, underscores, spaces) never causes a false mismatch:
    "GPT-5.6 Sol" and "gpt_5_6_sol" both normalize to "gpt56sol".
    """
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def normalize_variant_token(raw: str | None) -> str:
    """Same collapsing as normalize_slug, named separately for callers
    matching against the variant vocabulary rather than joining models."""
    if not raw:
        return ""
    return re.sub(r"[^a-z0-9]", "", raw.lower())


# Trailing "(...)" group, e.g. "GPT-5.6 Sol (medium)" -> "medium".
_PAREN_TAIL_RE = re.compile(r"\(([^()]+)\)\s*$")


def _split_recognized_variant(name: str | None, vocab: dict | None) -> tuple[str, str | None]:
    """Split `name` into (base_text, variant_label), same matching rules as
    `derive_base_variant` (see its docstring for the two conventions tried),
    but returning the base portion in its ORIGINAL casing/separators rather
    than normalized into a join key. Shared by `derive_base_variant` (which
    normalizes the result into a slug) and `derive_display_name` (which
    title-cases it for presentation) so both always agree on what counts as
    a recognized variant.
    """
    vocab = vocab or {}
    tokens: dict = vocab.get("tokens") or {}
    phrases: list = vocab.get("effort_phrases") or []
    name = (name or "").strip()
    if not name:
        return "", None

    m = _PAREN_TAIL_RE.search(name)
    if m:
        paren_lower = m.group(1).strip().lower()
        variant = None
        for entry in phrases:
            pattern = (entry or {}).get("pattern")
            if not pattern:
                continue
            pm = re.match(pattern, paren_lower)
            if not pm:
                continue
            literal = entry.get("variant")
            if literal:
                variant = literal
            else:
                level = pm.groupdict().get("level")
                variant = tokens.get(normalize_variant_token(level)) if level else None
            break
        if variant is None:
            variant = tokens.get(normalize_variant_token(paren_lower))
        if variant is not None:
            base = name[: m.start()].strip()
            if base:
                return base, variant
        # Unrecognized parenthetical (e.g. "(Beta)", "(June 2026)"): never
        # guessed - falls through and stays part of the base below.

    words = [w for w in re.split(r"[-_ ]+", name) if w]
    for tail_len in (2, 1):
        if len(words) <= tail_len:
            continue
        key = normalize_variant_token("".join(words[-tail_len:]))
        variant = tokens.get(key)
        if variant is not None:
            base_words = words[:-tail_len]
            if base_words:
                return " ".join(base_words), variant

    return name, None


def derive_base_variant(name: str | None, vocab: dict | None) -> tuple[str, str | None]:
    """Split a model name into (base_slug, variant_label) via `vocab` (the
    `variant_vocabulary` block of config/models.yaml) - see the module
    docstring for the rationale.

    Tries two conventions, in order, and only ever acts when a match is
    found in the vocabulary - never on a bare word guess:
      1. AA-style trailing parenthetical ("GPT-5.6 Sol (medium)", "Claude
         Opus 5 (Adaptive Reasoning, High Effort)"). `vocab["effort_phrases"]`
         handles multi-word phrasing a single-token lookup can't parse;
         otherwise the parenthetical's own normalized text is looked up
         directly in `vocab["tokens"]`.
      2. LMArena-style trailing suffix ("gpt-5.6-sol-xhigh",
         "claude-opus-4-6-thinking"): the name is split on separators and
         the last two words, then the last word alone, are tried against
         `vocab["tokens"]" (two-word first so multi-word tokens like
         "non-thinking" resolve as one variant rather than misreading their
         last word alone).
    A parenthetical or suffix that matches nothing recognized is left in
    place - it becomes part of the base_slug, and variant_label is null.
    """
    base_text, variant = _split_recognized_variant(name, vocab)
    return normalize_slug(base_text), variant


# A version-shaped token: digits with optional dot groups, optionally
# prefixed with a bare "v" ("5", "5.2", "4", "v4"). Used by
# `_display_case_words` to (a) never re-case digits and (b) join it to an
# immediately preceding acronym-cased word with a dash rather than a space,
# matching the conventional brand-version spelling ("GLM-5.2", "GPT-5.6").
_VERSION_TOKEN_RE = re.compile(r"^[vV]?\d+(?:\.\d+)*$")


def _format_version_token(word: str) -> str | None:
    """Return `word` formatted as a version token, or None if it isn't one.

    A leading "v"/"V" is capitalized ("v4" -> "V4"); a purely numeric token
    is returned unchanged ("5.2" -> "5.2") - a version number is never
    re-cased or otherwise mangled.
    """
    if not _VERSION_TOKEN_RE.match(word):
        return None
    if word[0] in ("v", "V"):
        return "V" + word[1:]
    return word


def _display_case_words(words: list[str], acronym_casing: dict) -> str:
    """Join `words` (already split on separators) into a titlecased display
    string, conservatively:
      - a word matching `acronym_casing` (config-driven, normalized
        lowercase key -> exact casing to emit) uses that casing exactly;
      - a word already carrying any uppercase letter is left untouched
        (never re-cases something already deliberately cased, e.g. a
        LMArena name that happens to already read "Motif" or "OpenAI");
      - a version-shaped token (`_format_version_token`) is never re-cased
        beyond capitalizing a leading "v", and is joined to an immediately
        preceding acronym-cased word with a dash rather than a space
        ("glm" + "5.2" -> "GLM-5.2"); every other join uses a space
        ("claude" + "fable" + "5" -> "Claude Fable 5");
      - any other word is titlecased only if it is currently all-lowercase;
        a mixed-case or all-uppercase word is left as-is.
    """
    parts: list[str] = []
    prev_is_acronym = False
    for i, word in enumerate(words):
        key = re.sub(r"[^a-z0-9]", "", word.lower())
        mapped = acronym_casing.get(key)
        if mapped is not None:
            text, is_acronym, is_version = mapped, True, False
        else:
            version_text = _format_version_token(word)
            if version_text is not None:
                text, is_acronym, is_version = version_text, False, True
            elif word.islower():
                text, is_acronym, is_version = word[:1].upper() + word[1:], False, False
            else:
                text, is_acronym, is_version = word, False, False
        if i == 0:
            parts.append(text)
        else:
            parts.append(("-" if (is_version and prev_is_acronym) else " ") + text)
        prev_is_acronym = is_acronym
    return "".join(parts)


def strip_configuration_parenthetical(text: str, variant_vocab: dict | None) -> str:
    """Drop a trailing parenthetical that only describes model configuration.

    `_split_recognized_variant` removes a parenthetical only when the WHOLE of
    it is a known variant, which leaves multi-clause configuration strings
    intact: Artificial Analysis publishes "Claude Fable 5 (Adaptive Reasoning,
    Max Effort, Opus 4.8 Fallback)", a 66-character name for a row that
    already carries a "+N variants" badge. Such a parenthetical is settings
    metadata, not part of the model's identity.

    Deliberately narrow: strip only when the parenthetical CONTAINS a known
    variant token, so genuinely identifying parentheticals with no variant
    vocabulary in them - a dated snapshot like "GPT-5.5 Instant (June 2026)",
    which distinguishes one release from another - are preserved. Stripping
    every parenthetical would collapse distinct models onto one name.
    """
    match = re.search(r"\s*\(([^()]*)\)\s*$", text)
    if not match:
        return text
    tokens = ((variant_vocab or {}).get("tokens") or {})
    inner_words = {normalize_slug(w) for w in re.split(r"[\s,]+", match.group(1)) if w}
    if inner_words & set(tokens):
        stripped = text[: match.start()].strip()
        return stripped or text
    return text


def derive_display_name(
    name: str | None,
    aa_name: str | None,
    variant_vocab: dict | None,
    acronym_casing: dict | None,
) -> str | None:
    """Compute the clean, human-readable BASE model name for presentation
    (the /models table, the chart tooltip, and the feed sidebar) - see the
    module docstring's "display_name" section for the full rationale.
    Purely additive: never mutates or replaces the raw `name` field.

    Prefers `aa_name` (Artificial Analysis's own verbose, title-cased name)
    when present, stripping only a *recognized* variant via
    `_split_recognized_variant` (same vocabulary as `derive_base_variant`,
    so the two never disagree) and trimming incidental whitespace - AA's own
    casing is trusted as-is, never re-cased. Falls back to `name` run
    through `_display_case_words` for the LMArena lowercase-dashed-slug
    case. Returns None (never a misleading guess) when neither input yields
    anything usable - callers (see `finalize_model`) fall back to the raw
    `name` field so the emitted value is never null while a name exists.
    """
    source_is_aa = bool(aa_name)
    source_text = aa_name if source_is_aa else name
    if not source_text:
        return None

    base_text, _variant = _split_recognized_variant(source_text, variant_vocab)
    base_text = (base_text or "").strip()
    if not base_text:
        return None

    if source_is_aa:
        base_text = strip_configuration_parenthetical(base_text, variant_vocab)
        return re.sub(r"\s+", " ", base_text)

    words = [w for w in re.split(r"[-_ ]+", base_text) if w]
    if not words:
        return None
    return _display_case_words(words, acronym_casing or {})


def zero_price_to_null(value):
    """A per-token price of exactly 0 means "not published", not "free" -
    Artificial Analysis emits 0 rather than null/absent for models it has
    not priced (mostly small/experimental open-weight releases), and 0 is
    also undefined on the /models page's log-scale price axis, where it
    would otherwise trivially dominate the cheap end of the Pareto frontier.
    Applied to every price field at read time (see `finalize_model`) so the
    dishonest zero can never reach the API, the chart, the table, or the
    sidebar - the model still appears, just with an honest "undisclosed".
    """
    if value is None:
        return None
    try:
        return None if float(value) == 0 else value
    except (TypeError, ValueError):
        return value


def round_or_none(value, digits: int):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def blended_price(price_input, price_output):
    """3:1 input:output token blend - see module docstring for rationale."""
    if price_input is None or price_output is None:
        return None
    try:
        total_weight = BLEND_INPUT_WEIGHT + BLEND_OUTPUT_WEIGHT
        return (BLEND_INPUT_WEIGHT * float(price_input) + BLEND_OUTPUT_WEIGHT * float(price_output)) / total_weight
    except (TypeError, ValueError):
        return None


def classify_open_weights(license_value, aa_open_weights, classification_cfg: dict | None = None):
    """Derive open_weights, preferring an explicit Artificial Analysis bool.

    Precedence: an explicit AA boolean always wins (even a surprising one -
    AA is the more authoritative source when present). Otherwise derive from
    the LMArena `license` string using `classification_cfg` (the
    `license_classification` block in config/models.yaml):
      - license matches an `unknown_markers` entry (case-insensitive
        substring) -> None (explicit escape hatch, never guessed).
      - license matches a `proprietary_markers` entry -> False.
      - any other non-empty license -> True (open-weights).
      - missing/empty license -> None.
    Never invents a value: the only way out is an explicit AA bool or a
    non-empty LMArena license string.
    """
    if isinstance(aa_open_weights, bool):
        return aa_open_weights

    if not license_value:
        return None

    classification_cfg = classification_cfg or {}
    license_lower = str(license_value).lower()

    for marker in classification_cfg.get("unknown_markers") or []:
        if marker and str(marker).lower() in license_lower:
            return None

    for marker in classification_cfg.get("proprietary_markers") or []:
        if marker and str(marker).lower() in license_lower:
            return False

    return True


def merge_lmarena_rows(rows_by_category: dict[str, list[dict]]) -> dict[str, dict]:
    """Fold per-category LMArena rows into one record per model slug.

    `rows_by_category` maps category name ("overall", "coding") to the raw
    row dicts returned by the datasets-server /filter endpoint. Returns a
    dict keyed by normalized slug.
    """
    idx: dict[str, dict] = {}
    for category, rows in rows_by_category.items():
        for row in rows or []:
            name = row.get("model_name")
            slug = normalize_slug(name)
            if not slug:
                continue
            entry = idx.setdefault(
                slug,
                {
                    "slug": slug,
                    "name": name,
                    "organization": row.get("organization"),
                    "license": row.get("license"),
                    "arena_elo_overall": None,
                    "arena_elo_coding": None,
                    "arena_votes": None,
                    "arena_rank_overall": None,
                    "arena_rank_coding": None,
                    "publish_date": None,
                },
            )
            # Prefer the richest organization/license value seen so far.
            if not entry.get("organization") and row.get("organization"):
                entry["organization"] = row.get("organization")
            if not entry.get("license") and row.get("license"):
                entry["license"] = row.get("license")
            rating = row.get("rating")
            rank = row.get("rank")
            if category == "overall":
                entry["arena_elo_overall"] = rating
                entry["arena_rank_overall"] = rank
                entry["arena_votes"] = row.get("vote_count")
                entry["publish_date"] = row.get("leaderboard_publish_date")
            elif category == "coding":
                entry["arena_elo_coding"] = rating
                entry["arena_rank_coding"] = rank
                if entry["arena_votes"] is None:
                    entry["arena_votes"] = row.get("vote_count")
                if entry["publish_date"] is None:
                    entry["publish_date"] = row.get("leaderboard_publish_date")
            else:
                # Future categories: keep the raw rating/rank under a
                # category-prefixed key without breaking the known fields.
                entry[f"arena_elo_{category}"] = rating
                entry[f"arena_rank_{category}"] = rank
    return idx


def get_path(d: dict, path: tuple[str, ...]):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def extract_aa_field(model: dict, field: str) -> tuple:
    """Probe AA_FIELD_PATHS for `field` in `model`.

    Returns (value, found) so callers can distinguish "found but null" from
    "no candidate path matched" for the missing-field warning log.
    """
    for path in AA_FIELD_PATHS.get(field, []):
        value = get_path(model, path)
        if value is not None:
            return value, True
    return None, False


def extract_aa_benchmarks(model: dict, benchmark_names: list[str]) -> dict:
    """Pull AA's raw per-benchmark scores from `evaluations` for whichever
    names `benchmark_names` lists (`config/models.yaml`'s
    `sources.artificial_analysis.benchmarks` - never hardcoded here, since AA
    adds/renames benchmarks over time).

    A benchmark AA reports as null for this model (not attempted, or
    withheld) is OMITTED from the result rather than zero-filled or
    invented - never zero-fill, never guess, matching `zero_price_to_null`'s
    sibling rationale. A model with no benchmark data at all yields `{}`, not
    a dict of null-padded keys.
    """
    out: dict = {}
    for name in benchmark_names or []:
        value = get_path(model, ("evaluations", name))
        if value is not None:
            out[name] = value
    return out


def build_aa_index(
    raw_models: list[dict], benchmark_names: list[str] | None = None
) -> tuple[dict[str, dict], set[str]]:
    """Turn raw Artificial Analysis model dicts into a slug-and-name-keyed index.

    AA's own `slug` is the primary join key ("gpt-5-6-sol-medium" ->
    "gpt56solmedium") and usually carries the variant; AA's verbose `name`
    ("GPT-5.6 Sol (medium)") is indexed too as a secondary key for the join
    cases the slug misses - e.g. a max variant only the slug spells out
    ("gpt-5-6-luna"), where the name carries it instead for other variants
    ("GPT-5.6 Sol (medium)" -> "gpt56solmedium").

    Each model is indexed under both of its normalized keys in two passes:
    slug first (primary, first model to claim a key wins), then name
    (secondary, only fills a key the slug pass left untouched). A
    name-derived write can therefore never overwrite a slug-derived entry -
    from this model or any other - and within a pass no model can silently
    clobber another model that already claimed the same key.

    `benchmark_names` (config/models.yaml's
    sources.artificial_analysis.benchmarks) is threaded through to
    `extract_aa_benchmarks` so every record also carries a `benchmarks` dict
    of that model's raw AA scores - see the module docstring's "benchmarks"
    section.

    Returns (index, missing_fields) where missing_fields is the set of AA
    field names that could not be located on ANY model (see
    `split_missing_aa_fields` for how `cmd_collect` logs this).
    """
    fields = [f for f in AA_FIELD_PATHS if f not in ("name", "slug")]
    found_any: dict[str, bool] = {f: False for f in fields}

    records: list[tuple[str, str, dict]] = []
    for raw in raw_models or []:
        slug_raw, slug_found = extract_aa_field(raw, "slug")
        name_raw, name_found = extract_aa_field(raw, "name")
        norm_slug = normalize_slug(slug_raw if slug_found else None)
        norm_name = normalize_slug(name_raw if name_found else None)
        record = {"slug": norm_slug, "name": name_raw if name_found else None}
        for field in fields:
            value, found = extract_aa_field(raw, field)
            record[field] = value
            if found:
                found_any[field] = True
        record["benchmarks"] = extract_aa_benchmarks(raw, benchmark_names)
        records.append((norm_slug, norm_name, record))

    idx: dict[str, dict] = {}
    for norm_slug, _norm_name, record in records:
        if norm_slug and norm_slug not in idx:
            idx[norm_slug] = record
    for _norm_slug, norm_name, record in records:
        if norm_name and norm_name not in idx:
            idx[norm_name] = record

    missing_fields = {f for f, found in found_any.items() if not found and raw_models}
    return idx, missing_fields


# ---------------------------------------------------------------------------
# DeepSWE: measured per-task cost (see the module docstring's "DeepSWE"
# section for the full rationale). Parsed out of a React Flight payload
# embedded in the leaderboard page's HTML, not a documented API - every
# function below is written to degrade to "no data" rather than crash on a
# shape change.
# ---------------------------------------------------------------------------

# Every DeepSWE row is a FLAT JS object literal (bare/unquoted keys, no
# nested braces) that always carries `source:"deep-swe"` - verified live
# 2026-08-16 against the full 61-row payload. Anchoring on that literal
# marker (rather than a surrounding array or a `$R[n]=` reference number,
# both of which can shift on any DeepSWE redeploy) is what keeps this
# resilient to everything except the row shape itself changing.
_DEEPSWE_ROW_RE = re.compile(r'\{[^{}]*?source:"deep-swe"[^{}]*\}')

# Turns a bare JS object-literal key ("model:") into a JSON-quoted one
# ("\"model\":") so the row can be parsed with json.loads instead of a
# hand-rolled JS evaluator. Only fires directly after `{` or `,`, so a
# string VALUE that happens to contain "word:" is never mistaken for a key.
_DEEPSWE_BARE_KEY_RE = re.compile(r'(?<=[{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:')

_DEEPSWE_GENERATED_AT_RE = re.compile(r'generated_at:"([^"]*)"')
_DEEPSWE_N_TASKS_RE = re.compile(r'n_tasks_in_set:(\d+)')

# The exact fields this module persists per row (see the module docstring) -
# anything else DeepSWE's payload carries is parsed but discarded, so an
# upstream field ADDITION never breaks anything here.
_DEEPSWE_ROW_FIELDS = (
    "model",
    "reasoning_effort",
    "harness",
    "pass_at_1",
    "ci_lo",
    "ci_hi",
    "n_runs",
    "mean_cost_usd",
    "median_cost_usd",
    "median_output_tokens",
)


def parse_deepswe_html(html: str | None) -> tuple[list[dict], dict]:
    """Extract DeepSWE leaderboard rows + run metadata from the leaderboard
    page's raw HTML - see the module docstring's "DeepSWE" section.

    Returns `(rows, meta)`. `rows` is a list of dicts carrying only
    `_DEEPSWE_ROW_FIELDS` (never the full raw payload); a row whose `model`
    is missing/blank, or whose object text fails to parse as JSON once bare
    keys are quoted, is silently skipped - never raised. `meta` is
    `{"generated_at": ..., "n_tasks_in_set": ...}`, each key present only
    when its pattern actually matched (best-effort, never guessed).

    Defensive by construction: `html` being None/empty, or the page no
    longer containing any `source:"deep-swe"` row at all (a wholesale
    DeepSWE shape change), both yield `([], {})` - the same "no data" shape
    a failed fetch produces, so callers never need to distinguish the two.
    """
    if not html:
        return [], {}

    rows: list[dict] = []
    for raw in _DEEPSWE_ROW_RE.findall(html):
        quoted = _DEEPSWE_BARE_KEY_RE.sub(r'"\1":', raw)
        try:
            obj = json.loads(quoted)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        model = obj.get("model")
        if not isinstance(model, str) or not model.strip():
            continue
        rows.append({field: obj.get(field) for field in _DEEPSWE_ROW_FIELDS})

    meta: dict = {}
    gen_match = _DEEPSWE_GENERATED_AT_RE.search(html)
    if gen_match:
        meta["generated_at"] = gen_match.group(1)
    tasks_match = _DEEPSWE_N_TASKS_RE.search(html)
    if tasks_match:
        try:
            meta["n_tasks_in_set"] = int(tasks_match.group(1))
        except ValueError:
            pass
    return rows, meta


def build_deepswe_index(rows: list[dict]) -> tuple[dict[tuple, dict], dict[str, dict]]:
    """Index parsed DeepSWE rows two ways for `apply_deepswe_data`:

    `by_key`: `(model, reasoning_effort) -> row`, the primary join key - a
    direct match against a catalog row's `(url_slug, variant_label)`, since
    DeepSWE's own naming already matches this module's conventions (see the
    module docstring). `by_model`: `model -> row`, retained only as a
    last-resort lookup for `best_deepswe_row_for_model`. It is NOT a
    per-variant fallback: a catalog variant whose own effort has no DeepSWE
    row keeps its nulls, because attaching another effort's run attributed
    one configuration's measured cost to a different one (see
    `apply_deepswe_data`).

    First occurrence wins either index - deterministic, matching this
    module's other join indices (see `build_aa_index`); the live data has no
    duplicate `(model, reasoning_effort)` pairs, but this stays correct even
    if a future scrape ever produced one.
    """
    by_key: dict[tuple, dict] = {}
    by_model: dict[str, dict] = {}
    for row in rows or []:
        model = row.get("model")
        if not model:
            continue
        key = (model, row.get("reasoning_effort"))
        if key not in by_key:
            by_key[key] = row
        if model not in by_model:
            by_model[model] = row
    return by_key, by_model


def apply_deepswe_data(
    models: list[dict],
    deepswe_by_key: dict[tuple, dict],
    deepswe_by_model: dict[str, dict],
) -> None:
    """Attach DeepSWE measured-cost fields onto every model row with a
    match, mutating `models` IN PLACE - see the module docstring's "DeepSWE"
    section. Must run after `assign_url_slugs` (needs `url_slug`) and
    `finalize_model` (needs `variant_label`), before `compute_frontier`
    (reads `deepswe_pass_at_1`/`deepswe_cost_per_task_usd`).

    Join key is `(url_slug, variant_label)` - a direct match against
    DeepSWE's own `(model, reasoning_effort)`, no normalization needed (see
    module docstring).

    The match must be EXACT on the variant. A measured result belongs to the
    exact configuration that produced it: DeepSWE reports claude-opus-5 at
    $11.84/task for "max" and $3.29/task for "medium", a 3.6x spread on one
    model. An earlier per-model fallback attached DeepSWE's "max" row to
    GPT-5.6 Sol's "non-reasoning" variant, claiming pass@1 0.727 at $8.39 for
    a configuration that never ran - the exact misattribution this measured
    cost axis exists to prevent. A variant with no DeepSWE row of its own
    keeps its nulls.

    An UNVERSIONED catalog row is the one place a differently-labelled
    DeepSWE row may attach. DeepSWE measures efforts that neither LMArena nor
    Artificial Analysis publishes as separate rows (it has five efforts for
    claude-fable-5, which we track as a single entry), so requiring an exact
    match there would discard real measurements for ~9 models. Such a row
    takes DeepSWE's best-scoring run for that model together with THAT run's
    own cost, so the (score, cost) pair still describes one real execution -
    never a score from one run beside a cost from another.

    `deepswe_effort` always records which configuration was measured, so the
    number is never presented as if it were the model's only behavior.
    A model absent from the index keeps every `deepswe_*` field at its
    `finalize_model`-assigned null - never invented.
    """
    for m in models:
        slug = m.get("url_slug")
        if not slug:
            continue
        variant = m.get("variant_label")
        row = deepswe_by_key.get((slug, variant))
        if row is None and variant is None:
            row = best_deepswe_row_for_model(deepswe_by_key, deepswe_by_model, slug)
        if row is None:
            continue
        m["deepswe_effort"] = row.get("reasoning_effort") or None
        m["deepswe_pass_at_1"] = round_or_none(row.get("pass_at_1"), 4)
        m["deepswe_ci_lo"] = round_or_none(row.get("ci_lo"), 4)
        m["deepswe_ci_hi"] = round_or_none(row.get("ci_hi"), 4)
        n_runs = row.get("n_runs")
        m["deepswe_n_runs"] = int(n_runs) if isinstance(n_runs, (int, float)) and not isinstance(n_runs, bool) else None
        m["deepswe_cost_per_task_usd"] = round_or_none(row.get("mean_cost_usd"), 4)
        m["deepswe_median_cost_usd"] = round_or_none(row.get("median_cost_usd"), 4)
        m["deepswe_output_tokens"] = round_or_none(row.get("median_output_tokens"), 1)


def best_deepswe_row_for_model(
    deepswe_by_key: dict[tuple, dict],
    deepswe_by_model: dict[str, dict],
    slug: str,
) -> dict | None:
    """DeepSWE's highest-scoring run for a model, for an unversioned row.

    Returns the whole row, so the caller takes that run's score AND its own
    measured cost together - the pair stays internally consistent. Picking the
    best score (rather than, say, the cheapest) states what the model can do
    at its best, which is what an unversioned catalog entry implies; the
    caller records `deepswe_effort` so the configuration is always disclosed.
    Ties break on the lower cost, then on the effort name, so repeated runs
    over the same input never flip a published page.
    """
    candidates = [row for (row_slug, _effort), row in deepswe_by_key.items() if row_slug == slug]
    if not candidates:
        fallback = deepswe_by_model.get(slug)
        return fallback
    def rank(row: dict) -> tuple:
        score = row.get("pass_at_1")
        cost = row.get("mean_cost_usd")
        return (
            -(score if isinstance(score, (int, float)) else -1),
            cost if isinstance(cost, (int, float)) else float("inf"),
            str(row.get("reasoning_effort") or ""),
        )
    return sorted(candidates, key=rank)[0]


def deepswe_join_stats(models: list[dict], deepswe_rows: list[dict]) -> tuple[int, int]:
    """`(joined, unjoined)` for the collect log line (WORK ITEM 1: unjoined
    DeepSWE entries must be visible, never silently dropped).

    `joined` counts catalog rows that ended up with a `deepswe_pass_at_1`
    value (via either the exact-effort or per-model fallback join).
    `unjoined` counts distinct DeepSWE `(model, reasoning_effort)` rows whose
    `model` never matches ANY tracked catalog `url_slug` at all - i.e. a
    DeepSWE-covered model this deployment doesn't track, which contributed
    nothing even via the per-model fallback.
    """
    joined = sum(1 for m in models if m.get("deepswe_pass_at_1") is not None)
    claimed_slugs = {m.get("url_slug") for m in models if m.get("deepswe_pass_at_1") is not None}
    seen_keys: set = set()
    unjoined = 0
    for row in deepswe_rows or []:
        model = row.get("model")
        if not model:
            continue
        key = (model, row.get("reasoning_effort"))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if model not in claimed_slugs:
            unjoined += 1
    return joined, unjoined


def join_models(
    lmarena_idx: dict[str, dict],
    aa_idx: dict[str, dict],
    aliases: dict[str, str],
) -> list[dict]:
    """Join LMArena and Artificial Analysis indices on normalized slug (or name).

    `aa_idx` keys each AA model under both its normalized slug and its
    normalized name (see `build_aa_index`), so an LMArena slug may hit
    either. `aliases` maps an LMArena slug to the AA key it should join
    against, for the cases neither normalization can bridge. Unjoined
    LMArena entries are still emitted (AA fields null,
    `joined_sources=["lmarena"]`); AA entries no LMArena row claimed are
    emitted too (`joined_sources=["artificial_analysis"]`) - deduplicated by
    object identity so a model reachable under both a slug key and a name
    key is never emitted twice.

    `organization` merges by fill-if-missing rather than blind overwrite: a
    joined row keeps its LMArena organization if it has one, and only takes
    AA's `model_creator`-derived value when LMArena's was null.

    Every row also carries an internal `aa_name` key: Artificial Analysis's
    own raw `name` string whenever the row has any AA contribution, None
    otherwise. This exists solely so `finalize_model`/`derive_display_name`
    can prefer AA's well-cased name for *display* even on a row joined via
    LMArena, where the *emitted* `name` field is intentionally the LMArena
    slug (see `AA_ROW_MERGE_EXCLUDED_FIELDS` above) - `aa_name` is never
    part of the published row shape.

    Every row also carries `benchmarks`: the AA record's raw per-benchmark
    dict (see `extract_aa_benchmarks`) when the row has any AA contribution,
    `{}` otherwise - handled explicitly here (like `aa_name`) rather than via
    the generic `AA_FIELD_PATHS` copy loop below, since it is not itself an
    AA_FIELD_PATHS entry.
    """
    merged: list[dict] = []
    used_aa_ids: set[int] = set()

    for slug, arena in lmarena_idx.items():
        aa_key = aliases.get(slug, slug)
        aa = aa_idx.get(aa_key)
        joined_sources = ["lmarena"]
        row = dict(arena)
        row["aa_name"] = aa.get("name") if aa is not None else None
        row["benchmarks"] = (aa.get("benchmarks") or {}) if aa is not None else {}
        if aa is not None:
            used_aa_ids.add(id(aa))
            joined_sources.append("artificial_analysis")
            for field in AA_FIELD_PATHS:
                if field in AA_ROW_MERGE_EXCLUDED_FIELDS:
                    continue
                row[field] = aa.get(field)
            if not row.get("organization") and aa.get("organization"):
                row["organization"] = aa.get("organization")
        else:
            for field in AA_FIELD_PATHS:
                if field in AA_ROW_MERGE_EXCLUDED_FIELDS:
                    continue
                row.setdefault(field, None)
        row["joined_sources"] = joined_sources
        merged.append(row)

    emitted_aa_ids: set[int] = set()
    for slug, aa in aa_idx.items():
        if id(aa) in used_aa_ids or id(aa) in emitted_aa_ids:
            continue
        emitted_aa_ids.add(id(aa))
        row = {
            "slug": aa.get("slug") or slug,
            "name": aa.get("name"),
            "aa_name": aa.get("name"),
            "benchmarks": aa.get("benchmarks") or {},
            "organization": aa.get("organization"),
            "license": None,
            "arena_elo_overall": None,
            "arena_elo_coding": None,
            "arena_votes": None,
            "arena_rank_overall": None,
            "arena_rank_coding": None,
            "publish_date": None,
            "joined_sources": ["artificial_analysis"],
        }
        for field in AA_FIELD_PATHS:
            if field in AA_ROW_MERGE_EXCLUDED_FIELDS:
                continue
            row[field] = aa.get(field)
        merged.append(row)

    return merged


def select_models(models: list[dict], recency_days: int, max_models: int, now: datetime) -> list[dict]:
    """Rank and cap the joined model list per the recency/max_models policy.

    Models with a known release_date within `recency_days` sort first;
    everything else sorts by LMArena overall rank (unranked models last).
    Caps the result to `max_models`.
    """

    def sort_key(model: dict):
        is_recent = False
        release_date = model.get("release_date")
        if release_date:
            try:
                is_recent = (now.date() - date.fromisoformat(str(release_date))).days <= recency_days
            except ValueError:
                is_recent = False
        rank = model.get("arena_rank_overall")
        rank_key = rank if isinstance(rank, (int, float)) else float("inf")
        return (0 if is_recent else 1, rank_key)

    ordered = sorted(models, key=sort_key)
    return ordered[:max_models] if max_models else ordered


def finalize_model(
    row: dict,
    classification_cfg: dict | None = None,
    organization_aliases: dict | None = None,
    variant_vocab: dict | None = None,
    acronym_casing: dict | None = None,
) -> dict:
    """Round/shape a merged row into the final output-contract model dict."""
    # A published 0 means "not priced", not "free" - null it before it ever
    # reaches a blend computation or the output - see zero_price_to_null.
    price_input = zero_price_to_null(row.get("price_input_per_1m"))
    price_output = zero_price_to_null(row.get("price_output_per_1m"))
    # Prefer AA's own published 3:1 blend when present; otherwise fall back
    # to computing the same weighting locally - see module docstring.
    aa_blended = zero_price_to_null(row.get("price_blended_per_1m"))
    blended = aa_blended if aa_blended is not None else blended_price(price_input, price_output)

    organization = row.get("organization")
    if organization and organization_aliases:
        organization = organization_aliases.get(str(organization).strip().lower(), organization)

    base_slug, variant_label = derive_base_variant(row.get("name"), variant_vocab)
    # display_name is purely additive presentation of the base model's clean
    # name - see the module docstring's "display_name" section. Never null
    # while a name exists: fall back to the raw name field verbatim if the
    # computation ever yields nothing usable.
    display_name = derive_display_name(row.get("name"), row.get("aa_name"), variant_vocab, acronym_casing)
    if not display_name:
        display_name = row.get("name")

    return {
        "slug": row.get("slug"),
        "name": row.get("name"),
        "display_name": display_name,
        "base_slug": base_slug,
        "variant_label": variant_label,
        "organization": organization,
        "license": row.get("license"),
        "open_weights": classify_open_weights(row.get("license"), row.get("open_weights"), classification_cfg),
        "release_date": row.get("release_date"),
        "context_window_tokens": row.get("context_window_tokens"),
        "parameters_total": row.get("parameters_total"),
        "parameters_active": row.get("parameters_active"),
        "price_input_per_1m": round_or_none(price_input, 4),
        "price_output_per_1m": round_or_none(price_output, 4),
        "price_blended_per_1m": round_or_none(blended, 4),
        "arena_elo_overall": round_or_none(row.get("arena_elo_overall"), 2),
        "arena_elo_coding": round_or_none(row.get("arena_elo_coding"), 2),
        "arena_votes": int(row["arena_votes"]) if isinstance(row.get("arena_votes"), (int, float)) else None,
        "arena_rank_overall": int(row["arena_rank_overall"]) if isinstance(row.get("arena_rank_overall"), (int, float)) else None,
        "arena_rank_coding": int(row["arena_rank_coding"]) if isinstance(row.get("arena_rank_coding"), (int, float)) else None,
        "aa_intelligence_index": round_or_none(row.get("aa_intelligence_index"), 2),
        "aa_coding_index": round_or_none(row.get("aa_coding_index"), 2),
        "median_output_tokens_per_second": round_or_none(row.get("median_output_tokens_per_second"), 1),
        "official_url": row.get("official_url"),
        "joined_sources": row.get("joined_sources") or [],
        # Raw per-benchmark AA scores, stored exactly as AA reports them
        # (0-1 fractions - see the module docstring's "benchmarks" section
        # and config/models.yaml's SCALE WARNING). Never rounded here: the
        # presentation layer, not this data layer, owns display formatting.
        "benchmarks": row.get("benchmarks") or {},
        # DeepSWE measured-per-task-cost fields (module docstring's
        # "DeepSWE" section) - always present as a key, defaulted to null
        # here since the DeepSWE join runs AFTER finalize_model (it needs
        # `url_slug`, assigned later by `assign_url_slugs`); `build_output`
        # overwrites these via `apply_deepswe_data` when a match exists.
        "deepswe_pass_at_1": None,
        "deepswe_ci_lo": None,
        "deepswe_ci_hi": None,
        "deepswe_n_runs": None,
        "deepswe_cost_per_task_usd": None,
        "deepswe_median_cost_usd": None,
        "deepswe_output_tokens": None,
        # Which reasoning effort DeepSWE actually measured. Always disclosed
        # so a score is never read as the model's only behavior - effort
        # swings measured cost several-fold on one model.
        "deepswe_effort": None,
    }


# ---------------------------------------------------------------------------
# url_slug (WORK ITEM 1) + server-side Pareto frontier (WORK ITEM 2)
# ---------------------------------------------------------------------------

# Matches api/models.js's SLUG_RE (^[a-z0-9][a-z0-9-]{0,80}$) minus the
# length cap, which slugify() enforces separately via max_len so a suffix
# appended later for collision resolution never pushes a slug over the
# regex's limit.
_SLUG_COLLAPSE_RE = re.compile(r"[^a-z0-9]+")

# Reserve room for a numeric collision suffix ("-2".."-9999") under the
# regex's 81-char ceiling. Collisions are rare (only once two different
# rows' display_name/name/slug all normalize identically) and a run of
# thousands of them on one base is not realistic, so 6 reserved characters
# is generous.
_SLUG_MAX_BASE_LEN = 81 - 6


def slugify(text: str | None, max_len: int = _SLUG_MAX_BASE_LEN) -> str:
    """Lowercase `text` and collapse every run of non-alphanumeric characters
    into a single dash, trimming leading/trailing dashes - the shape
    `api/models.js`'s `SLUG_RE` requires. Returns "" for empty/punctuation-only
    input (callers fall through their own fallback chain - see
    `assign_url_slugs`), never a guess.
    """
    if not text:
        return ""
    collapsed = _SLUG_COLLAPSE_RE.sub("-", text.strip().lower())
    stripped = collapsed.strip("-")
    if not stripped:
        return ""
    return stripped[:max_len].rstrip("-") or stripped[:1]


def propagate_group_licensing(models: list[dict]) -> None:
    """Share a known `license` / `open_weights` across a model's variant group.

    Licensing is a property of the MODEL, not of a reasoning-effort setting:
    every variant of Claude Opus 5 is proprietary. But only LMArena publishes a
    license, so an AA-only variant row carries none. Because the presentation
    layer collapses a group to one representative row and picks it by
    capability, the representative is often the AA-only variant - which made
    `/models` render "weights unknown" for the top-ranked models (Claude Opus 5,
    GPT-5.6 Sol, Kimi K3, GLM 5.2, GPT-5.6 Terra), even though a sibling row in
    the same group knew the answer.

    Fills a row's missing value from its group, never overwrites a value the
    row already has, and stays silent when the group genuinely disagrees -
    a conflict means the grouping is wrong, and guessing would launder that
    bug into confident-looking output. Runs after `assign_url_slugs`, which
    defines the groups.
    """
    by_slug: dict[str, list[dict]] = {}
    for row in models:
        by_slug.setdefault(row.get("url_slug") or "", []).append(row)

    for group in by_slug.values():
        for field in ("open_weights", "license"):
            known = {row.get(field) for row in group if row.get(field) is not None}
            if len(known) != 1:
                continue
            value = known.pop()
            for row in group:
                if row.get(field) is None:
                    row[field] = value


def assign_url_slugs(models: list[dict]) -> None:
    """Compute a stable, unique, URL-safe `url_slug` PER BASE MODEL and write
    it onto every row in that model's group IN PLACE - see the module
    docstring's "url_slug" section for the full contract.

    One slug per `base_slug` GROUP, not per row: the product is one detail
    page per real model (`/models/<slug>`), and every row sharing a
    `base_slug` - every reasoning-effort variant of the same underlying
    model - is the SAME model for that purpose, exactly like the
    `web/models.html` presentation layer already collapses them (the
    "+N variants" badge). Grouping by row would mint a separate URL per
    variant (`claude-opus-5`, `claude-opus-5-2`, ... one per effort level),
    which is both meaningless to a reader (which variant "wins" the bare
    slug is arbitrary) and NOT actually stable: when an upstream variant is
    retired, a per-row numbering scheme renumbers its surviving siblings and
    breaks every previously-published link to them. Grouping by `base_slug`
    avoids that failure mode entirely, because a surviving variant's own
    `base_slug` - and therefore its group's candidate slug - never depends
    on which OTHER variants of the same model happen to still exist this
    run (see the "drop a row from the middle of a group" stability test).

    Fallback chain per GROUP: a deterministically-chosen representative row
    (sorted by its own normalized `slug`, then `name` - never list
    position) supplies `display_name` -> `name` -> the existing normalized
    `slug` (never empty while any of the three is non-blank on any row in
    the group). In practice every row in a `base_slug` group already shares
    the same `display_name` (variant text is stripped from it - see
    `derive_display_name`), so which row is "representative" rarely
    matters; the deterministic tiebreak only bites in the rare case they
    disagree.

    Groups (not rows) are then processed in an order derived purely from
    each group's own identity - sorted by its candidate slug text, tiebroken
    by its `base_slug` - never by list position, index, or iteration order,
    so re-running against the same input set always resolves collisions the
    same way. After per-model grouping, a collision can only happen between
    two genuinely DIFFERENT base models whose clean display names happen to
    match (rare), and resolving it is stable because it no longer depends on
    variant churn within either model - only on one of the two colliding
    base models disappearing entirely. A collision gets a numeric "-2",
    "-3", ... suffix appended until free; no row is ever dropped and no
    slug is ever assigned randomly.
    """
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for m in models:
        key = m.get("base_slug") or m.get("slug") or f"__row_{id(m)}__"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(m)

    group_candidates: list[tuple[str, str, list[dict]]] = []
    for group_key in order:
        rows = groups[group_key]
        rep = sorted(rows, key=lambda r: (r.get("slug") or "", r.get("name") or ""))[0]
        base = (
            slugify(rep.get("display_name"))
            or slugify(rep.get("name"))
            or slugify(rep.get("slug"))
            or "model"
        )
        group_candidates.append((base, group_key, rows))

    group_candidates.sort(key=lambda c: (c[0], c[1]))

    used: set[str] = set()
    for base, _group_key, rows in group_candidates:
        slug = base
        n = 2
        while slug in used:
            slug = f"{base}-{n}"
            n += 1
        used.add(slug)
        for m in rows:
            m["url_slug"] = slug


def _read_metric_value(model: dict, metric_cfg: dict):
    """Read a frontier_metrics entry's capability value off `model`: a
    top-level field for source "top", or a lookup under `model["benchmarks"]`
    for source "benchmarks" (see config/models.yaml's frontier_metrics)."""
    key = metric_cfg.get("key")
    if metric_cfg.get("source") == "benchmarks":
        return (model.get("benchmarks") or {}).get(key)
    return model.get(key)


def compute_frontier(
    models: list[dict],
    frontier_metrics: list[dict] | None,
    dominated_by_cap: int = 5,
) -> dict[str, dict]:
    """Compute the server-side Pareto frontier for every metric in
    `frontier_metrics` (config/models.yaml's `frontier_metrics` - see the
    module docstring's "frontier" section) over `models` (already carrying
    `url_slug` - see `assign_url_slugs`, which must run first and now
    assigns ONE `url_slug` per base model, shared across every
    reasoning-effort variant row - see its docstring).

    Returns `{url_slug: {metric_key: entry, ...}, ...}` - one entry per BASE
    MODEL, matching the one-`url_slug`-per-model contract `assign_url_slugs`
    now guarantees (a detail page at `/models/<slug>` needs exactly one
    frontier answer for that model, not one per variant). A `url_slug`/metric
    pair is OMITTED entirely (not written with a null/false placeholder)
    whenever NONE of that model's variant rows carry both the metric value
    and its paired cost field with numeric values - never treated as a
    comparable 0, matching `zero_price_to_null`'s sibling rationale
    elsewhere in this module.

    Two-phase computation:

    1. PER-VARIANT domination. Every row with both the metric and its
       paired cost is one point (`cost`, `cap`). A point is dominated by
       another point `q` when `q.cost <= p.cost` AND `q.cap >= p.cap`, with
       at least one strict inequality - the standard Pareto-optimality
       definition, and equivalent in OUTCOME to web/models.html's
       `paretoFrontier()` (sort ascending by cost, keep a point only when
       it strictly beats the best capability seen so far) for every point
       set with no exact cost tie, the overwhelming majority of real data
       (verified live 2026-08-16, see docs/design-docs/decision-log.md). A
       direct domination check is used instead of a literal port of that
       walk because the walk has no secondary sort key and can call two
       equal-cost points both "frontier" even when one strictly dominates
       the other; a domination check has no such blind spot, and
       `dominated_by` needs the full relationship anyway, so both answers
       come from the same computation instead of two that could drift
       apart. CRITICAL: a candidate dominator sharing THIS row's `url_slug`
       (i.e. a sibling variant of the same model) is never counted - a
       model can never be "dominated by itself" now that variants share a
       slug, so this exclusion is checked directly by comparing `url_slug`,
       not inferred from row identity.

    2. Per-model AGGREGATION. A base model is `on_frontier` for a metric if
       ANY of its variant rows is (the reader picks whichever variant is
       competitive - the detail page shows all of them). `dominated_by` is
       the UNION of every non-frontier variant row's dominators, mapped to
       THEIR `url_slug`s (also now per-base-model) and deduplicated - so two
       dominating variants of the same other model collapse to one entry,
       keeping whichever instance is nearest in cost. `dominated_by` is only
       populated when the model is NOT on the frontier (i.e. every one of
       its variants was dominated); a model that IS on the frontier gets
       `dominated_by: []` even if some of its weaker variants were
       individually dominated - once one variant clears the bar, "why isn't
       this model on the frontier" no longer applies.

    `dominated_by` is capped at `dominated_by_cap`, nearest-cost-first
    (smallest absolute distance between the dominating variant's cost and
    the dominated variant's own cost - the most directly comparable
    substitution).
    """
    out: dict[str, dict] = {}
    for metric_cfg in frontier_metrics or []:
        metric_key = metric_cfg.get("key")
        cost_field = metric_cfg.get("cost_field")
        cost_basis = metric_cfg.get("cost_basis")
        if not metric_key or not cost_field:
            continue

        points = []
        for m in models:
            slug = m.get("url_slug")
            if not slug:
                continue
            cap = _read_metric_value(m, metric_cfg)
            cost = m.get(cost_field)
            if cap is None or cost is None:
                continue
            if isinstance(cap, bool) or isinstance(cost, bool):
                continue
            if not isinstance(cap, (int, float)) or not isinstance(cost, (int, float)):
                continue
            points.append({
                "slug": slug,
                "cap": float(cap),
                "cost": float(cost),
                "variant": m.get("variant_label"),
            })

        # Phase 1: per-variant domination, excluding sibling variants of the
        # SAME model (same url_slug) from ever counting as a dominator - see
        # docstring above.
        by_slug: dict[str, dict] = {}
        for p in points:
            dominators = [
                q
                for q in points
                if q["slug"] != p["slug"]
                and q["cost"] <= p["cost"]
                and q["cap"] >= p["cap"]
                and (q["cost"] < p["cost"] or q["cap"] > p["cap"])
            ]
            agg = by_slug.setdefault(
                p["slug"], {"on_frontier": False, "dominators": {}, "qualifying": None}
            )
            if not dominators:
                agg["on_frontier"] = True
                # Remember WHICH variant earned it, and that variant's own
                # (cap, cost) pair. Without this every surface picked its own
                # representative by a different heuristic - the ranked list by
                # intelligence index, the detail page by identity completeness
                # - so the same model was published with two different costs
                # beside the same "on frontier" claim. The most CAPABLE
                # qualifying point wins, cheaper breaking a tie: picking the
                # cheapest instead selected GPT-5.6 Luna's 1.6%-pass@1 run at
                # $0.01 as the model's frontier showing - non-dominated, but a
                # meaningless headline for a badge meant to say the model is
                # worth routing to.
                best = agg["qualifying"]
                if (
                    best is None
                    or p["cap"] > best["metric_value"]
                    or (p["cap"] == best["metric_value"] and p["cost"] < best["cost"])
                ):
                    agg["qualifying"] = {
                        "variant": p["variant"],
                        "metric_value": p["cap"],
                        "cost": p["cost"],
                    }
            for q in dominators:
                dist = abs(q["cost"] - p["cost"])
                best = agg["dominators"].get(q["slug"])
                if best is None or dist < best:
                    agg["dominators"][q["slug"]] = dist

        # Phase 2: aggregate to one entry per url_slug (base model).
        for slug, agg in by_slug.items():
            on_frontier = agg["on_frontier"]
            dominated_by: list[str] = []
            if not on_frontier:
                ranked = sorted(agg["dominators"].items(), key=lambda kv: kv[1])
                dominated_by = [s for s, _dist in ranked[:dominated_by_cap]]
            qualifying = agg["qualifying"] if on_frontier else None
            out.setdefault(slug, {})[metric_key] = {
                "cost_field": cost_field,
                "cost_basis": cost_basis,
                "on_frontier": on_frontier,
                "dominated_by": dominated_by,
                # The variant that actually cleared the bar, and its own
                # score/cost - so no surface has to guess a representative.
                "qualifying_variant": (qualifying or {}).get("variant"),
                "qualifying_metric_value": (qualifying or {}).get("metric_value"),
                "qualifying_cost": (qualifying or {}).get("cost"),
            }

    return out


def build_output(
    lmarena_idx: dict[str, dict],
    aa_idx: dict[str, dict],
    aliases: dict[str, str],
    recency_days: int,
    max_models: int,
    now: datetime,
    lmarena_meta: dict,
    aa_meta: dict,
    classification_cfg: dict | None = None,
    organization_aliases: dict | None = None,
    variant_vocab: dict | None = None,
    acronym_casing: dict | None = None,
    axis_metric_options: list | None = None,
    frontier_metrics: list | None = None,
    frontier_dominated_by_cap: int = 5,
    deepswe_meta: dict | None = None,
    deepswe_by_key: dict[tuple, dict] | None = None,
    deepswe_by_model: dict[str, dict] | None = None,
) -> dict:
    merged = join_models(lmarena_idx, aa_idx, aliases)
    selected = select_models(merged, recency_days, max_models, now)
    models = [
        finalize_model(row, classification_cfg, organization_aliases, variant_vocab, acronym_casing)
        for row in selected
    ]
    # url_slug needs a global view across every row to resolve collisions
    # deterministically (see assign_url_slugs), so it can't be computed
    # per-row inside finalize_model - same reason compute_frontier runs
    # after, keyed on the url_slug this pass just assigned.
    assign_url_slugs(models)
    propagate_group_licensing(models)
    # DeepSWE join needs url_slug/variant_label (both just assigned above)
    # and must land before compute_frontier, which reads deepswe_pass_at_1/
    # deepswe_cost_per_task_usd once frontier_metrics names them.
    apply_deepswe_data(models, deepswe_by_key or {}, deepswe_by_model or {})
    frontier_by_slug = compute_frontier(models, frontier_metrics, frontier_dominated_by_cap)
    for m in models:
        m["frontier"] = frontier_by_slug.get(m["url_slug"], {})
    return {
        "generated_at": now.isoformat(),
        "sources": {
            "lmarena": lmarena_meta,
            "artificial_analysis": aa_meta,
            "deepswe": deepswe_meta or {},
        },
        "models": models,
        # Config-driven Y-axis toggle options for web/models.html's chart -
        # see config/models.yaml's axis_metric_options. Emitted verbatim so
        # the page never hardcodes which benchmarks it offers (it keeps a
        # small fallback constant only for an older cached artifact written
        # before this field existed).
        "axis_metric_options": axis_metric_options or [],
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _make_session(cfg: dict):
    """A requests session, proxy behavior controlled by `trust_env_proxies`.

    Picking up a stale or slow system/env HTTP proxy (observed in local dev)
    can turn a sub-second public API call into a multi-second timeout, so
    the config default is false. A deployment that legitimately needs
    HTTP_PROXY/HTTPS_PROXY routing can set `trust_env_proxies: true` in
    config/models.yaml rather than have that silently disabled in code.
    """
    import requests

    session = requests.Session()
    session.trust_env = bool(cfg.get("trust_env_proxies", False))
    return session


RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def is_retryable_status(status_code: int) -> bool:
    """Whether an HTTP status is worth retrying.

    The datasets-server answers a cold cache with `500 {"error": "the dataset
    index is loading, this may take longer than usual"}`. That is transient and
    self-healing, so it must be retried rather than failing the run. Client
    errors (AA's 401 for a bad key, a 404 for a renamed dataset) are real and
    are surfaced immediately instead of being retried pointlessly.
    """
    return status_code in RETRYABLE_STATUSES


def _get_with_retry(session, url: str, *, timeout: float, headers: dict | None = None, max_attempts: int = 4):
    """GET with exponential backoff for transient network errors and 5xx.

    Both source APIs are read-only and idempotent, so retrying is safe.
    """
    import requests

    last_exc: Exception | None = None
    response = None
    for attempt in range(max_attempts):
        try:
            response = session.get(url, timeout=timeout, headers=headers)
            if not is_retryable_status(response.status_code):
                return response
            last_exc = None
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            response = None
        if attempt < max_attempts - 1:
            time.sleep(2**attempt)
    if last_exc is not None:
        raise last_exc
    # Out of attempts on a retryable status: hand the last response back so the
    # caller's raise_for_status reports the real upstream status.
    return response


def fetch_lmarena_category(cfg: dict, category: str) -> list[dict]:
    session = _make_session(cfg)

    src = cfg["sources"]["lmarena"]
    base_url = src["base_url"].rstrip("/")
    dataset = src["dataset"]
    config_name = src["config"]
    split = src["split"]
    page_size = int(src["page_size"])
    timeout = cfg["request_timeout_seconds"]

    where = quote(f'"category"=\'{category}\'')
    rows: list[dict] = []
    offset = 0
    total = None
    # Safety cap on pages so a malformed response can't loop forever.
    for _ in range(200):
        url = (
            f"{base_url}/filter?dataset={quote(dataset, safe='')}&config={config_name}"
            f"&split={split}&where={where}&offset={offset}&length={page_size}"
        )
        resp = _get_with_retry(session, url, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        page_rows = [r.get("row", {}) for r in payload.get("rows", [])]
        rows.extend(page_rows)
        total = payload.get("num_rows_total")
        offset += page_size
        if not page_rows or len(page_rows) < page_size:
            break
        if total is not None and offset >= total:
            break
    return rows


def fetch_aa_models(cfg: dict) -> list[dict] | None:
    """Return raw AA model dicts, or None when the key is missing/request fails."""
    src = cfg["sources"]["artificial_analysis"]
    api_key_env = src.get("api_key_env", "AA_API_KEY")
    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        return None

    import requests

    session = _make_session(cfg)
    try:
        resp = _get_with_retry(
            session,
            src["base_url"],
            headers={"x-api-key": api_key},
            timeout=cfg["request_timeout_seconds"],
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        print(f"models_collect_aa_fetch_failed error={exc!r}")
        return None

    if isinstance(payload, list):
        return payload
    for key in ("data", "models", "results"):
        value = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(value, list):
            return value
    print(f"models_collect_aa_unexpected_shape keys={list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}")
    return []


def fetch_deepswe_html(cfg: dict) -> str | None:
    """Fetch the DeepSWE leaderboard page's raw HTML - one GET request,
    reusing the shared retrying session (see the module docstring's
    "DeepSWE" section). Returns None on any fetch failure so the caller
    degrades to "no DeepSWE data" instead of raising.
    """
    src = cfg["sources"].get("deepswe") or {}
    base_url = src.get("base_url")
    if not base_url:
        return None

    import requests

    session = _make_session(cfg)
    try:
        resp = _get_with_retry(session, base_url, timeout=cfg["request_timeout_seconds"])
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"models_collect_deepswe_fetch_failed error={exc!r}")
        return None


def save_output(output: dict, latest_path: Path = LATEST_PATH, history_dir: Path = HISTORY_DIR) -> Path:
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    latest_path.write_text(text, encoding="utf-8")

    history_dir.mkdir(parents=True, exist_ok=True)
    day = output["generated_at"][:10]
    history_path = history_dir / f"{day}.json"
    history_path.write_text(text, encoding="utf-8")
    return history_path


def load_output(latest_path: Path = LATEST_PATH) -> dict | None:
    if not latest_path.exists():
        return None
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def source_regressions(
    new_output: dict,
    previous_output: dict | None,
    enabled_sources: set[str] | None = None,
) -> list[str]:
    """Names of ENABLED sources that were available last run but are missing now.

    Pure function so the write-guard is testable without any network. An
    empty list means the new artifact is safe to publish.

    `enabled_sources` is the set of sources still switched on in config. A
    source the operator has deliberately disabled is NOT a regression: the
    documented remedy for the fragile DeepSWE scrape is
    `sources.deepswe.enabled: false`, and counting that as a regression made
    the guard refuse every subsequent write - the collector would keep
    exiting 0 while data/models/latest.json silently froze forever. Passing
    None keeps the old "check every source" behavior for callers that have
    no config handy.
    """
    if not previous_output:
        return []
    prev_sources = previous_output.get("sources") or {}
    new_sources = new_output.get("sources") or {}
    regressed = [
        name
        for name, prev in prev_sources.items()
        if isinstance(prev, dict)
        and prev.get("available")
        and not (new_sources.get(name) or {}).get("available")
        and (enabled_sources is None or name in enabled_sources)
    ]
    return sorted(regressed)


def cmd_collect(args: argparse.Namespace) -> int:
    cfg = load_config()
    now = utc_now()

    lmarena_cfg = cfg["sources"]["lmarena"]
    lmarena_idx: dict[str, dict] = {}
    lmarena_meta = {
        "available": False,
        "attribution": lmarena_cfg.get("attribution", ""),
        "url": f"{lmarena_cfg['base_url']}/filter?dataset={lmarena_cfg['dataset']}",
        "publish_date": None,
    }
    if lmarena_cfg.get("enabled", True):
        # The datasets-server /filter endpoint is markedly slower than /rows or
        # /splits and intermittently exceeds the request timeout under load. A
        # transient upstream failure must not fail the scheduled refresh: log
        # it, leave the previously committed artifact in place, and exit 0 so
        # the site keeps serving last-good data and the workflow stays green.
        try:
            rows_by_category = {}
            for category in lmarena_cfg.get("categories", []):
                rows_by_category[category] = fetch_lmarena_category(cfg, category)
        except Exception as exc:
            print(f"models_collect_partial reason=lmarena_fetch_failed detail={type(exc).__name__}")
            rows_by_category = {}
        lmarena_idx = merge_lmarena_rows(rows_by_category)
        publish_dates = {e["publish_date"] for e in lmarena_idx.values() if e.get("publish_date")}
        lmarena_meta["available"] = bool(lmarena_idx)
        lmarena_meta["publish_date"] = max(publish_dates) if publish_dates else None

    aa_cfg = cfg["sources"]["artificial_analysis"]
    aa_idx: dict[str, dict] = {}
    aa_meta = {
        "available": False,
        "attribution": aa_cfg.get("attribution", ""),
        "url": aa_cfg.get("base_url", ""),
    }
    aa_raw = None
    aa_key_present = bool(os.environ.get(aa_cfg.get("api_key_env", "AA_API_KEY"), "").strip())
    if aa_cfg.get("enabled", True):
        aa_raw = fetch_aa_models(cfg)
    if aa_raw is None:
        reason = "aa_fetch_failed" if aa_key_present else "missing_aa_key"
        print(f"models_collect_partial reason={reason}")
    else:
        aa_idx, missing_fields = build_aa_index(aa_raw, aa_cfg.get("benchmarks") or [])
        aa_meta["available"] = bool(aa_idx)
        if missing_fields:
            genuinely_unmapped, known_unavailable = split_missing_aa_fields(missing_fields)
            if genuinely_unmapped:
                print(f"models_collect_aa_fields_unmapped fields={','.join(sorted(genuinely_unmapped))}")
            if known_unavailable:
                print(f"models_collect_aa_fields_known_unavailable fields={','.join(sorted(known_unavailable))}")

    deepswe_cfg = cfg["sources"].get("deepswe") or {}
    deepswe_meta = {
        "available": False,
        "attribution": deepswe_cfg.get("attribution", ""),
        "url": deepswe_cfg.get("base_url", ""),
        "generated_at": None,
        "n_tasks_in_set": None,
    }
    deepswe_rows: list[dict] = []
    if deepswe_cfg.get("enabled", True):
        # Scraped, not an API (see module docstring / config/models.yaml's
        # sources.deepswe comment) - a page-shape change must degrade to
        # "no DeepSWE data" and never fail the scheduled refresh, exactly
        # like the LMArena block above.
        try:
            html = fetch_deepswe_html(cfg)
            deepswe_rows, deepswe_run_meta = parse_deepswe_html(html)
        except Exception as exc:
            print(f"models_collect_partial reason=deepswe_parse_failed detail={type(exc).__name__}")
            deepswe_rows, deepswe_run_meta = [], {}
        deepswe_meta["generated_at"] = deepswe_run_meta.get("generated_at")
        deepswe_meta["n_tasks_in_set"] = deepswe_run_meta.get("n_tasks_in_set")
        deepswe_meta["available"] = bool(deepswe_rows)
        if not deepswe_rows:
            print("models_collect_partial reason=deepswe_no_rows_parsed")
    deepswe_by_key, deepswe_by_model = build_deepswe_index(deepswe_rows)

    output = build_output(
        lmarena_idx=lmarena_idx,
        aa_idx=aa_idx,
        aliases=cfg.get("aliases") or {},
        recency_days=int(cfg["recency_days"]),
        max_models=int(cfg["max_models"]),
        now=now,
        lmarena_meta=lmarena_meta,
        aa_meta=aa_meta,
        classification_cfg=cfg.get("license_classification") or {},
        organization_aliases=cfg.get("organization_aliases") or {},
        variant_vocab=cfg.get("variant_vocabulary") or {},
        acronym_casing=cfg.get("acronym_casing") or {},
        axis_metric_options=cfg.get("axis_metric_options") or [],
        frontier_metrics=cfg.get("frontier_metrics") or [],
        frontier_dominated_by_cap=int(cfg.get("frontier_dominated_by_cap") or 5),
        deepswe_meta=deepswe_meta,
        deepswe_by_key=deepswe_by_key,
        deepswe_by_model=deepswe_by_model,
    )

    if not output["models"]:
        print("models_collect_failed reason=no_models_from_any_source")
        return 0

    enabled_sources = {
        name
        for name, src_cfg in (cfg.get("sources") or {}).items()
        if isinstance(src_cfg, dict) and src_cfg.get("enabled", True)
    }
    regressed = source_regressions(output, load_output(), enabled_sources)
    if regressed:
        # Degrading gracefully must never mean publishing worse data. A source
        # that succeeded last run but failed this one would strip its whole
        # column (Elo, org, open-weights) from every row, so keep the previous
        # artifact and let the next run recover.
        print(f"models_collect_skipped_write reason=source_regression sources={','.join(regressed)}")
        return 0

    save_output(output)
    joined = sum(1 for m in output["models"] if len(m["joined_sources"]) > 1)
    deepswe_joined, deepswe_unjoined = deepswe_join_stats(output["models"], deepswe_rows)
    print(
        "models_collect_done "
        f"models={len(output['models'])} joined={joined} aa={str(aa_meta['available']).lower()} "
        f"deepswe={str(deepswe_meta['available']).lower()} deepswe_rows={len(deepswe_rows)} "
        f"deepswe_joined={deepswe_joined} deepswe_unjoined={deepswe_unjoined}"
    )
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    output = load_output()
    if not output or not output.get("models"):
        print("No model data yet - run `collect` first.")
        return 0

    models = output["models"]
    if args.limit:
        models = models[: args.limit]

    print(f"generated_at={output.get('generated_at')}")
    lmarena_src = output.get("sources", {}).get("lmarena", {})
    aa_src = output.get("sources", {}).get("artificial_analysis", {})
    print(f"lmarena_available={lmarena_src.get('available')} aa_available={aa_src.get('available')}")
    print()
    print(f"{'rank':>4} {'name':<28} {'org':<16} {'elo':>8} {'coding_elo':>10} {'price/1m':>9} {'sources':<24}")
    for m in models:
        print(
            f"{str(m.get('arena_rank_overall') or '-'):>4} "
            f"{(m.get('name') or '-')[:28]:<28} "
            f"{(m.get('organization') or '-')[:16]:<16} "
            f"{m.get('arena_elo_overall') if m.get('arena_elo_overall') is not None else '-':>8} "
            f"{m.get('arena_elo_coding') if m.get('arena_elo_coding') is not None else '-':>10} "
            f"{m.get('price_blended_per_1m') if m.get('price_blended_per_1m') is not None else '-':>9} "
            f"{','.join(m.get('joined_sources') or []):<24}"
        )

    print()
    print(f"models_summary total={len(output['models'])} shown={len(models)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="fetch LMArena (+ AA if keyed) and write data/models/latest.json")
    p_collect.set_defaults(func=cmd_collect)

    p_summary = sub.add_parser("summary", help="print the currently stored models as a table")
    p_summary.add_argument("--limit", type=int, default=25, help="only show the top N rows")
    p_summary.set_defaults(func=cmd_summary)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
