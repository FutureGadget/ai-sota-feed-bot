"""Deterministic editorial policy for the served feed.

The collector is intentionally broad: it pulls first-party labs, practitioner
blogs, release feeds, and Google News queries into one candidate pool. Ranking
alone cannot keep that pool honest, because it scores single items and has no
memory of yesterday's edition.

This module sits between collection and ranking and does the bookkeeping that
an LLM should not be asked to do:

* classify every source by editorial role (first party, practitioner, search),
* quarantine obvious search-result noise before it can reach the pool,
* collapse the same story reported under different headlines into one card,
* stop re-serving an item after it has had its run in recent editions,
* annotate items with a stable story key so the feed API can collapse the same
  story across the accumulated run history.

Everything here is deterministic and config-driven (``config/editorial.yaml``).
The agent quality judge is a later layer; it should judge the items this module
has already cleaned up, not replace the bookkeeping.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG_FILE = ROOT / "config" / "editorial.yaml"
SOURCES_FILE = ROOT / "config" / "sources.yaml"
PROCESSED_DIR = ROOT / "data" / "processed"
RUNS_DIR = PROCESSED_DIR / "runs"
RUNS_INDEX = PROCESSED_DIR / "runs_index.json"
EDITORIAL_ARTIFACT = PROCESSED_DIR / "editorial.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "source_roles": {},
    "source_role_prefixes": {
        "search_": "search",
        "arxiv_": "research",
        "openreview_": "research",
        "paperswithcode_": "aggregator",
        "hf_": "release",
        "_releases": "release",
    },
    "caps": {
        "search": 1,
        "aggregator": 3,
        "community": 2,
        "first_party": 4,
        "practitioner": 3,
        "release": 4,
        "research": 4,
        "default": 3,
    },
    "search_quarantine": {
        "enabled": True,
        "max_candidates_per_source": 2,
        "low_quality_patterns": [],
        "rescue_keywords": [],
    },
    "first_party_quarantine": {
        "enabled": True,
        "low_value_patterns": [],
        "rescue_keywords": [],
    },
    "story_clusters": {
        "enabled": True,
        "title_jaccard": 0.62,
        "min_shared_tokens": 2,
        "max_days_apart": 14,
        "rep_freshness_hours": 72,
        "model_tokens": [],
        "variant_tokens": [],
        "event_patterns": {},
    },
    "seen": {
        "enabled": True,
        "lookback_runs": 24,
        "max_editions": {
            "first_party": 12,
            "practitioner": 8,
            "aggregator": 4,
            "community": 4,
            "search": 3,
            "release": 8,
            "research": 8,
            "default": 6,
        },
        "min_unseen_items": 10,
        "penalty_per_edition": 0.08,
        "max_penalty": 0.8,
    },
}

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[a-z][a-z0-9+#]*")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "he", "her", "here", "his", "how", "i", "if", "in", "is", "it", "its",
    "may", "me", "might", "must", "my", "new", "no", "not", "now", "of", "on",
    "or", "our", "s", "she", "should", "so", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "those", "to", "today",
    "was", "we", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your",
}
# A version needs either a decimal point ("4.1", "2.1.302") or a model size
# ("WeVisOne-VL-4B"). A bare number is usually a price, a count, or a year
# ("20 cents", "1,000 calls"), not a release. The optional pre-release suffix
# is part of the version: 0.164.0-alpha.8 and 0.164.0-alpha.12 are different
# releases, not one alpha family.
_VERSION_RE = re.compile(
    r"(?<![0-9])[a-z]?v?("
    r"\d+\.\d+(?:\.\d+)*"
    r"(?:(?:[-_][a-z0-9]+(?:\.[0-9a-z]+)*)|(?:rc|alpha|beta|dev|post|pre|preview)[0-9]*)*"
    r"|\d+(?:\.\d+)?[bBmMtT]"
    r")(?![\w])",
    re.I,
)
_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")

# Release titles are mostly template text; only the model/version part
# distinguishes one release from another. Exclude this boilerplate from the
# "shared title tokens" test, or every Hugging Face org release collapses into
# one card.
_RELEASE_BOILERPLATE = {
    "release", "released", "notes", "note", "changelog", "version", "update",
    "updates", "corresponding", "container", "ngc", "hugging", "face", "org",
    "available", "now", "announce", "announces", "announcing", "announced",
    "introduce", "introduces", "introducing", "launch", "launches", "launched",
    "ships", "shipped", "unveil", "unveils", "unveiled", "drop", "drops",
    "dropped", "day", "support",
}
_MAX_DATETIME = datetime.max.replace(tzinfo=timezone.utc)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config() -> dict[str, Any]:
    if not CFG_FILE.exists():
        return DEFAULT_CONFIG
    try:
        raw = yaml.safe_load(CFG_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return DEFAULT_CONFIG
    return _deep_merge(DEFAULT_CONFIG, raw)


def _load_source_names() -> list[str]:
    if not SOURCES_FILE.exists():
        return []
    try:
        raw = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    return [str(s.get("name") or "").strip() for s in (raw.get("sources") or []) if s.get("name")]


def source_role(source: str, cfg: dict[str, Any] | None = None) -> str:
    """Return the editorial role for a source name.

    Explicit config wins, then prefix/suffix rules, then a small set of known
    defaults so the function still behaves sensibly with an empty config.
    """
    source = str(source or "").strip()
    cfg = cfg or load_config()
    explicit = cfg.get("source_roles") or {}
    for role, names in explicit.items():
        if source in {str(n).strip() for n in (names or [])}:
            return role
    for prefix, role in (cfg.get("source_role_prefixes") or {}).items():
        prefix = str(prefix or "")
        if not prefix:
            continue
        if prefix.endswith("_"):
            if source.startswith(prefix):
                return str(role)
        elif prefix.startswith("_"):
            if source.endswith(prefix):
                return str(role)
        elif source == prefix:
            return str(role)
    if source.startswith("search_"):
        return "search"
    if source == "hackernews_ai":
        return "community"
    if source in {"infoq_ai_ml", "paperswithcode_latest"}:
        return "aggregator"
    if source.startswith(("arxiv_", "openreview_")):
        return "research"
    if source.endswith("_releases"):
        return "release"
    return "default"


def expanded_source_roles(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    """Materialize the role map for every configured source.

    The API reads this map from ``data/processed/editorial.json`` so it can
    apply the same caps without shipping PyYAML to a serverless function.
    """
    cfg = cfg or load_config()
    return {name: source_role(name, cfg) for name in _load_source_names()}


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_url(value: Any) -> str:
    return str(value or "").split("#")[0].split("?")[0].strip().lower()


def normalize_title(value: Any) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"^(?:show\s+hn|hn)\s*:\s*", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _word_tokens(value: Any) -> set[str]:
    return {
        token
        for token in _WORD_RE.findall(_clean_text(value).lower())
        if len(token) > 1 and token not in _STOPWORDS
    }


def _version_tokens(value: Any, cfg: dict[str, Any] | None = None) -> list[str]:
    text = _clean_text(value).lower()
    out: list[str] = []
    for match in _VERSION_RE.finditer(text):
        token = match.group(1).strip("-._")
        if not token or _YEAR_RE.match(token):
            continue
        out.append(token)
    cfg = cfg or load_config()
    models = {str(t).lower() for t in ((cfg.get("story_clusters", {}) or {}).get("model_tokens") or [])}
    for model in models:
        if not model or " " in model:
            continue
        for match in re.finditer(rf"\b{re.escape(model)}[\s-]+v?(\d+)(?!\.\d)\b", text):
            token = match.group(1)
            if token and not _YEAR_RE.match(token) and token not in out:
                out.append(token)
    return out


def _version_family(token: str) -> str:
    match = re.match(r"(\d+(?:\.\d+)?)", token)
    return match.group(1) if match else token


def _has_phrase(text: str, phrase: str) -> bool:
    phrase = str(phrase or "").strip().lower()
    if not phrase:
        return False
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns if pattern)


def _non_latin_ratio(text: str) -> float:
    letters = [ch for ch in str(text or "") if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if ord(ch) > 127) / len(letters)


def _event_type(title: str, cfg: dict[str, Any]) -> str:
    text = _clean_text(title).lower()
    patterns = (cfg.get("story_clusters", {}) or {}).get("event_patterns", {}) or {}
    for event, regexes in patterns.items():
        if _matches_any(text, regexes or []):
            return str(event)
    return ""


def _features(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    cluster_cfg = cfg.get("story_clusters", {}) or {}
    title = _clean_text(item.get("title"))
    tokens = _word_tokens(title)
    versions = _version_tokens(title, cfg)
    model_tokens = {str(t).lower() for t in (cluster_cfg.get("model_tokens") or [])}
    variant_tokens = {str(t).lower() for t in (cluster_cfg.get("variant_tokens") or [])}
    models = {token for token in tokens if token in model_tokens}
    variants = {token for token in tokens if token in variant_tokens}
    # Multi-word model names ("claude code", "stable diffusion") are phrases,
    # not word tokens; keep them in the model set when present.
    lower = title.lower()
    for phrase in model_tokens:
        if " " in phrase and _has_phrase(lower, phrase):
            models.add(phrase)
    return {
        "norm_title": normalize_title(title),
        "tokens": tokens,
        "models": models,
        "variants": variants,
        "versions": versions,
        "version_family": _version_family(versions[0]) if versions else "",
        "full_version": versions[0] if versions else "",
        "event": _event_type(title, cfg),
    }


def _is_release_source(item: dict[str, Any], cfg: dict[str, Any]) -> bool:
    source = str(item.get("source") or "").lower()
    url = str(item.get("url") or "").lower()
    if source.endswith("_releases") or "/releases/tag/" in url:
        return True
    return source_role(source, cfg) == "release"


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _is_subset(a: set[str], b: set[str]) -> bool:
    return bool(a) and a.issubset(b)


def _same_story_features(
    fa: dict[str, Any],
    fb: dict[str, Any],
    a: dict[str, Any],
    b: dict[str, Any],
    cfg: dict[str, Any],
) -> bool:
    cluster_cfg = cfg.get("story_clusters", {}) or {}
    a_url, b_url = canonical_url(a.get("url")), canonical_url(b.get("url"))
    if a_url and a_url == b_url:
        return True

    if fa["norm_title"] and fa["norm_title"] == fb["norm_title"] and len(fa["norm_title"]) >= 12:
        return True

    # Do not fold coverage from different editions into one card. The feed's
    # longest slot freshness window is 336h (research); comparing much older
    # items only hides the fresh member behind a stale representative.
    a_epoch, b_epoch = _published_epoch(a), _published_epoch(b)
    if a_epoch and b_epoch:
        max_gap_hours = float(cluster_cfg.get("max_days_apart", 14) or 14) * 24.0
        if abs(a_epoch - b_epoch) > max_gap_hours * 3600.0:
            return False

    if fa["event"] and fb["event"] and fa["event"] != fb["event"]:
        return False

    a_release = _is_release_source(a, cfg)
    b_release = _is_release_source(b, cfg)
    # Release feeds are mostly boilerplate. When both sides are release feeds,
    # a different model set means a different release, even if the version is
    # missing from one of the titles.
    if a_release and b_release and fa["models"] != fb["models"]:
        return False
    # A release feed compares the full version, not only the major.minor
    # family. This applies to model-less feeds (Triton) as well as model
    # releases, so v2.1.296 and v2.1.302 never collapse into one card.
    if (a_release or b_release) and fa["full_version"] and fb["full_version"] and fa["full_version"] != fb["full_version"]:
        return False

    model_words: set[str] = set()
    for feature in (fa, fb):
        for model in feature["models"]:
            model_words.update(_word_tokens(model))

    def content_tokens(feature: dict[str, Any]) -> set[str]:
        """Title tokens that identify the event, not the product or template."""
        return {
            token
            for token in feature["tokens"]
            if token not in model_words and token not in _RELEASE_BOILERPLATE
        }

    shared_models = fa["models"] & fb["models"]
    if shared_models:
        # A specific product name on one side but not the other means a
        # different subject ("DeepSeek Harness" is not "DeepSeek V4.1", and
        # "Claude Code" is not "Claude"). Both sides must name the same set.
        if fa["models"] != fb["models"]:
            return False
        if fa["version_family"] and fb["version_family"] and fa["version_family"] != fb["version_family"]:
            return False
        # A variant word on one side and not the other means two different
        # members of a family ("GPT-6 mini" vs "GPT-6"). Require both sides to
        # be variant-free or to share a variant.
        if bool(fa["variants"]) != bool(fb["variants"]):
            return False
        if fa["variants"] and fb["variants"] and not (fa["variants"] & fb["variants"]):
            return False
        # The same product and full version in a release context is the same
        # launch, even when the headline wording differs.
        if (
            fa["full_version"]
            and fb["full_version"]
            and fa["full_version"] == fb["full_version"]
            and (a_release or b_release or fa["event"] == "release" or fb["event"] == "release")
        ):
            return True
        # Search echoes often paraphrase the headline but keep the product's
        # variant word ("DeepSeek ... Flash"). That is still the same story.
        if fa["variants"] & fb["variants"] and fa["event"] and fa["event"] == fb["event"]:
            return True
        if fa["event"] == "analysis" or fb["event"] == "analysis":
            return _jaccard(fa["tokens"], fb["tokens"]) >= max(
                float(cluster_cfg.get("title_jaccard", 0.62)) + 0.08, 0.70
            )
        shared_tokens = content_tokens(fa) & content_tokens(fb)
        # Same-source posts still need real headline overlap; otherwise a
        # recurring series ("Lessons from building Claude Code") collapses.
        # Search items are exempt because paraphrased result titles are the
        # whole point of that lane.
        if str(a.get("source") or "") == str(b.get("source") or ""):
            if source_role(a.get("source", ""), cfg) != "search":
                if _jaccard(content_tokens(fa), content_tokens(fb)) < float(cluster_cfg.get("title_jaccard", 0.62)):
                    return False
        if len(shared_tokens) >= int(cluster_cfg.get("min_shared_tokens", 2)):
            return True
        return False

    shared_tokens = content_tokens(fa) & content_tokens(fb)
    if _jaccard(content_tokens(fa), content_tokens(fb)) >= float(cluster_cfg.get("title_jaccard", 0.62)) and len(shared_tokens) >= 2:
        return True
    if (_is_subset(content_tokens(fa), content_tokens(fb)) or _is_subset(content_tokens(fb), content_tokens(fa))) and len(shared_tokens) >= 4:
        return True
    return False


def same_story(a: dict[str, Any], b: dict[str, Any], cfg: dict[str, Any] | None = None) -> bool:
    """True when two items describe the same story, not merely the same topic.

    The rules are deliberately conservative: sharing a company name is not
    enough. A model release and an outage, a funding round, or a comparison
    listicle about the same company stay separate. Release feeds compare full
    versions, so v2.1.296 and v2.1.302 remain two releases even though they
    share a major.minor family.
    """
    cfg = cfg or load_config()
    return _same_story_features(_features(a, cfg), _features(b, cfg), a, b, cfg)


def _source_priority(source: str, cfg: dict[str, Any]) -> int:
    role = source_role(source, cfg)
    return {
        "first_party": 0,
        "practitioner": 1,
        "release": 2,
        "research": 2,
        "aggregator": 3,
        "community": 3,
        "default": 3,
        "search": 4,
    }.get(role, 3)


def _published_key(item: dict[str, Any]) -> datetime:
    from dateutil import parser as dt_parser

    for field in ("published", "collected_at"):
        value = item.get(field)
        if not value:
            continue
        try:
            parsed = dt_parser.parse(str(value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            continue
    return datetime.max.replace(tzinfo=timezone.utc)


def _published_epoch(item: dict[str, Any]) -> float:
    """Epoch seconds for an item's publication time, or 0 when unknown."""
    published = _published_key(item)
    if published == _MAX_DATETIME:
        return 0.0
    try:
        return published.timestamp()
    except (OverflowError, OSError, ValueError):
        return 0.0


def _published_age_hours(item: dict[str, Any]) -> float:
    """Hours since publication, or 0 when the timestamp is missing/unparseable."""
    published = _published_epoch(item)
    if not published:
        return 0.0
    return max((datetime.now(timezone.utc).timestamp() - published) / 3600.0, 0.0)


def _score_key(item: dict[str, Any]) -> float:
    for field in ("global_score", "final_score", "score"):
        try:
            value = float(item.get(field, 0) or 0)
        except (TypeError, ValueError):
            continue
        if value:
            return value
    return 0.0


def _title_quality(item: dict[str, Any], cfg: dict[str, Any]) -> int:
    features = _features(item, cfg)
    quality = 0
    if features["versions"]:
        quality += 3
    if features["event"] == "release":
        quality += 2
    elif features["event"] in {"analysis", "business", "incident", "product"}:
        quality -= 3
    if features["models"]:
        quality += 1
    if 30 <= len(features["norm_title"]) <= 120:
        quality += 1
    if re.search(r"\b(?:talks less|20 cents|everything you need|what is|top \d+)\b", features["norm_title"]):
        quality -= 2
    return quality


def _cluster_key(anchor: dict[str, Any], cfg: dict[str, Any]) -> str:
    """Readable, story-specific key.

    The model/version prefix is for debugging; the normalized title makes the
    key unique per story. Two different Claude Code stories must not share a
    key just because they share a model family.
    """
    features = _features(anchor, cfg)
    title_lower = _clean_text(anchor.get("title")).lower()
    models = sorted(features["models"], key=lambda model: title_lower.find(model))
    parts = ["model:" + models[0]] if models else ["story"]
    if features["version_family"]:
        parts.append(f"ver:{features['version_family']}")
    if features["variants"]:
        parts.append("variant:" + ",".join(sorted(features["variants"])))
    parts.append("title:" + normalize_title(anchor.get("title"))[:80])
    return "|".join(parts)


def _merge_also_covered(rep: dict[str, Any], members: list[dict[str, Any]]) -> None:
    try:
        from enrich import record_duplicate
    except Exception:
        from pipeline.enrich import record_duplicate

    for member in members:
        if member is rep:
            continue
        record_duplicate(rep, member)
        for entry in member.get("also_covered") or []:
            if isinstance(entry, dict):
                record_duplicate(
                    rep,
                    {"source": entry.get("source"), "url": entry.get("url"), "title": entry.get("title")},
                )


def _specificity(features: dict[str, Any]) -> int:
    return (
        len(features["versions"]) * 3
        + (2 if features["event"] == "release" else 0)
        + len(features["models"])
    )


def cluster_items(items: list[dict[str, Any]], cfg: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse near-duplicate items into one representative per story.

    Clustering is greedy against a cluster anchor, not single-linkage union.
    Chaining through a versionless headline would otherwise merge two different
    releases ("DeepSeek V4.1" -> "DeepSeek's new model" -> "DeepSeek Harness
    v0.2.1"). Anchoring on the most specific title keeps those apart.

    Returns the representatives in first-seen order. Each representative and
    every member carries the same ``story_key`` / ``story_cluster_id`` so the
    API can keep collapsing the story across accumulated run history.
    """
    cfg = cfg or load_config()
    if not (cfg.get("story_clusters", {}) or {}).get("enabled", True) or not items:
        return list(items), {"enabled": False, "clusters": 0, "collapsed": 0}

    features = [_features(item, cfg) for item in items]
    order = sorted(range(len(items)), key=lambda idx: (-_specificity(features[idx]), idx))
    clusters: list[dict[str, Any]] = []
    for idx in order:
        placed = False
        for cluster in clusters:
            anchor = cluster["anchor"]
            if _same_story_features(features[idx], features[anchor], items[idx], items[anchor], cfg):
                cluster["members"].append(idx)
                placed = True
                break
        if not placed:
            clusters.append({"anchor": idx, "members": [idx]})

    clusters.sort(key=lambda cluster: min(cluster["members"]))
    out: list[dict[str, Any]] = []
    collapsed = 0
    multi_clusters = 0
    for cluster in clusters:
        member_idxs = cluster["members"]
        if len(member_idxs) == 1:
            rep = dict(items[member_idxs[0]])
            key = _cluster_key(rep, cfg)
            rep["story_key"] = key
            rep["story_cluster_id"] = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
            rep["source_role"] = source_role(rep.get("source", ""), cfg)
            out.append(rep)
            continue
        multi_clusters += 1
        members = [items[i] for i in cluster["members"]]
        rep_freshness_hours = float((cfg.get("story_clusters", {}) or {}).get("rep_freshness_hours", 72) or 0)
        recent = (
            [member for member in members if _published_age_hours(member) <= rep_freshness_hours]
            if rep_freshness_hours > 0
            else members
        )
        if recent:
            rep = min(
                recent,
                key=lambda m: (
                    _source_priority(m.get("source", ""), cfg),
                    -_title_quality(m, cfg),
                    -_published_epoch(m),
                    -_score_key(m),
                ),
            )
        else:
            # All members are stale; use the newest so the cluster has the
            # best chance of surviving its slot's freshness window.
            rep = max(members, key=_published_epoch)
        rep = dict(rep)
        _merge_also_covered(rep, members)
        key = _cluster_key(items[cluster["anchor"]], cfg)
        rep["story_key"] = key
        rep["story_cluster_id"] = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        rep["source_role"] = source_role(rep.get("source", ""), cfg)
        rep["story_cluster_size"] = len(members)
        for member in members:
            member["story_key"] = key
            member["story_cluster_id"] = rep["story_cluster_id"]
            member["source_role"] = source_role(member.get("source", ""), cfg)
        collapsed += len(members) - 1
        out.append(rep)

    return out, {"enabled": True, "clusters": multi_clusters, "collapsed": collapsed}


def _quarantine_first_party(items: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    qcfg = cfg.get("first_party_quarantine", {}) or {}
    diag = {"first_party_in": 0, "first_party_dropped_low_value": 0}
    if not qcfg.get("enabled", True):
        return list(items), diag

    patterns = qcfg.get("low_value_patterns") or []
    rescue = qcfg.get("rescue_keywords") or []
    kept: list[dict[str, Any]] = []
    for item in items:
        if source_role(item.get("source", ""), cfg) != "first_party":
            kept.append(item)
            continue
        diag["first_party_in"] += 1
        title_text = _clean_text(item.get("title")).lower()
        if _matches_any(title_text, patterns) and not _matches_any(title_text, rescue):
            diag["first_party_dropped_low_value"] += 1
            continue
        kept.append(item)
    return kept, diag


def _quarantine_search(items: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    qcfg = cfg.get("search_quarantine", {}) or {}
    diag = {
        "search_in": 0,
        "search_dropped_low_quality": 0,
        "search_dropped_non_latin": 0,
        "search_dropped_over_cap": 0,
    }
    if not qcfg.get("enabled", True):
        return list(items), diag

    patterns = qcfg.get("low_quality_patterns") or []
    rescue = qcfg.get("rescue_keywords") or []
    max_non_latin = float(qcfg.get("max_non_latin_ratio", 0.3) or 0.0)
    kept: list[dict[str, Any]] = []
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if source_role(item.get("source", ""), cfg) != "search":
            kept.append(item)
            continue
        diag["search_in"] += 1
        title_text = _clean_text(item.get("title")).lower()
        text = f"{title_text} {_clean_text(item.get('summary')).lower()}"
        if max_non_latin and _non_latin_ratio(title_text) > max_non_latin:
            diag["search_dropped_non_latin"] += 1
            continue
        if _matches_any(text, patterns) and not _matches_any(title_text, rescue):
            diag["search_dropped_low_quality"] += 1
            continue
        by_source[str(item.get("source") or "")].append(item)

    cap = int(qcfg.get("max_candidates_per_source", 2) or 0)
    for source_items in by_source.values():
        source_items.sort(key=lambda it: (_published_key(it), _score_key(it)), reverse=True)
        for idx, item in enumerate(source_items):
            if cap and idx >= cap:
                diag["search_dropped_over_cap"] += 1
                continue
            kept.append(item)
    # Preserve the caller's original order; ranking uses its own scores.
    order = {id(item): idx for idx, item in enumerate(items)}
    kept.sort(key=lambda it: order.get(id(it), 10**9))
    return kept, diag


def load_recent_history(cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Count how many recent editions contained each story.

    The index is written newest-first by ``build_digest.write_run_snapshot``.
    Only the configured lookback is read, so the cost stays bounded even as the
    archive grows.
    """
    cfg = cfg or load_config()
    lookback = int((cfg.get("seen", {}) or {}).get("lookback_runs", 24) or 0)
    if lookback <= 0 or not RUNS_INDEX.exists():
        return {}
    try:
        index = json.loads(RUNS_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(index, list):
        return {}

    history: dict[str, dict[str, Any]] = {}
    for row in index[:lookback]:
        rel = row.get("path") or row.get("file")
        if not rel:
            continue
        path = RUNS_DIR / str(rel)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        run_at = payload.get("run_at") or row.get("run_at")
        for item in payload.get("items") or []:
            keys = {
                item.get("story_key"),
                item.get("story_cluster_id"),
                canonical_url(item.get("url")),
                normalize_title(item.get("title")),
            }
            keys = {str(k) for k in keys if k}
            if not keys:
                continue
            # One item increments one row once per run, even though it is
            # indexed under several aliases (story key, URL, normalized title).
            existing = []
            seen_rows = set()
            for key in keys:
                row = history.get(key)
                if row is not None and id(row) not in seen_rows:
                    seen_rows.add(id(row))
                    existing.append(row)
            if existing:
                row_hist = existing[0]
                row_hist["count"] = int(row_hist.get("count", 0)) + 1
            else:
                row_hist = {"count": 1, "last_seen": run_at, "first_seen": run_at}
            if run_at and (not row_hist.get("last_seen") or str(run_at) > str(row_hist["last_seen"])):
                row_hist["last_seen"] = run_at
            if run_at and (not row_hist.get("first_seen") or str(run_at) < str(row_hist["first_seen"])):
                row_hist["first_seen"] = run_at
            for key in keys:
                history[key] = row_hist
    return history


def _apply_seen_memory(
    items: list[dict[str, Any]],
    cfg: dict[str, Any],
    history: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    scfg = cfg.get("seen", {}) or {}
    diag = {"seen_dropped": 0, "seen_penalized": 0}
    if not scfg.get("enabled", True) or not history:
        return list(items), diag

    max_by_role = scfg.get("max_editions", {}) or {}
    source_overrides = scfg.get("source_overrides", {}) or {}
    min_unseen = int(scfg.get("min_unseen_items", 10) or 0)
    penalty_per = float(scfg.get("penalty_per_edition", 0.08) or 0.0)
    max_penalty = float(scfg.get("max_penalty", 0.8) or 0.0)

    def edition_count(item: dict[str, Any]) -> int:
        for key in (
            item.get("story_key"),
            item.get("story_cluster_id"),
            canonical_url(item.get("url")),
            normalize_title(item.get("title")),
        ):
            if not key:
                continue
            row = history.get(str(key))
            if row:
                return int(row.get("count", 0) or 0)
        return 0

    def cap_for(item: dict[str, Any]) -> int:
        source = str(item.get("source") or "")
        if source in source_overrides:
            return int(source_overrides[source] or 0)
        role = source_role(source, cfg)
        return int(max_by_role.get(role, max_by_role.get("default", 6)) or 0)

    unseen = sum(1 for item in items if edition_count(item) < cap_for(item))
    can_drop = unseen >= min_unseen

    kept: list[dict[str, Any]] = []
    for item in items:
        count = edition_count(item)
        role = source_role(item.get("source", ""), cfg)
        item = dict(item)
        item["seen_count"] = count
        item["source_role"] = role
        if count:
            item["editorial_penalty"] = round(min(max_penalty, count * penalty_per), 3)
            diag["seen_penalized"] += 1
        if can_drop and count >= cap_for(item):
            diag["seen_dropped"] += 1
            continue
        kept.append(item)
    return kept, diag


def apply_pre_ranking(
    items: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
    *,
    use_seen: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Clean the candidate pool before the ranking engine sees it.

    Order matters: quarantine search and first-party noise, collapse story
    duplicates, then apply seen-memory to the surviving representatives. The
    per-source caps in the same config are applied by the API to its
    accumulated run pool; the ranking's slot caps remain the final word here.
    """
    cfg = cfg or load_config()
    if not cfg.get("enabled", True):
        return list(items), {"enabled": False}

    first_party_kept, fpdiag = _quarantine_first_party(items, cfg)
    quarantined, qdiag = _quarantine_search(first_party_kept, cfg)
    clustered, cdiag = cluster_items(quarantined, cfg)
    if use_seen:
        history = load_recent_history(cfg)
        final, sdiag = _apply_seen_memory(clustered, cfg, history)
    else:
        final, sdiag = list(clustered), {"seen_dropped": 0, "seen_penalized": 0}
        for item in final:
            item["source_role"] = source_role(item.get("source", ""), cfg)

    diag = {
        "enabled": True,
        "input": len(items),
        "output": len(final),
        **fpdiag,
        **qdiag,
        **cdiag,
        **sdiag,
    }
    return final, diag


def write_editorial_artifact(diag: dict[str, Any] | None = None, cfg: dict[str, Any] | None = None) -> Path:
    """Write the role/cap map the feed API reads.

    ``data/processed/**`` is already bundled into the feed function, so this
    adds no deployment surface. Keeping the map in one artifact also means the
    Python pipeline and the JS API cannot disagree about which sources are
    search results.
    """
    cfg = cfg or load_config()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_roles": expanded_source_roles(cfg),
        "caps": cfg.get("caps", {}),
        "role_totals": cfg.get("role_totals", {}),
        "search_quarantine": {
            "enabled": bool((cfg.get("search_quarantine", {}) or {}).get("enabled", True)),
            "low_quality_patterns": (cfg.get("search_quarantine", {}) or {}).get("low_quality_patterns", []),
            "rescue_keywords": (cfg.get("search_quarantine", {}) or {}).get("rescue_keywords", []),
            "max_non_latin_ratio": (cfg.get("search_quarantine", {}) or {}).get("max_non_latin_ratio", 0.3),
        },
        "first_party_quarantine": {
            "enabled": bool((cfg.get("first_party_quarantine", {}) or {}).get("enabled", True)),
            "low_value_patterns": (cfg.get("first_party_quarantine", {}) or {}).get("low_value_patterns", []),
            "rescue_keywords": (cfg.get("first_party_quarantine", {}) or {}).get("rescue_keywords", []),
        },
        "story_clusters": {
            "enabled": bool((cfg.get("story_clusters", {}) or {}).get("enabled", True)),
        },
        "diagnostics": diag or {},
    }
    EDITORIAL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{EDITORIAL_ARTIFACT.name}.",
        suffix=".tmp",
        dir=str(EDITORIAL_ARTIFACT.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, EDITORIAL_ARTIFACT)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return EDITORIAL_ARTIFACT


def main() -> None:
    """Print the current policy artifact and a small cluster diagnostic."""
    cfg = load_config()
    print(json.dumps({"source_roles": expanded_source_roles(cfg), "caps": cfg.get("caps", {})}, indent=2))
    if RUNS_INDEX.exists():
        history = load_recent_history(cfg)
        print(f"history_stories={len(history)}")


if __name__ == "__main__":
    main()
