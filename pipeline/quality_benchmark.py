"""Benchmark harness for the feed quality judge (Jev or a fixture).

The benchmark is a small, stratified sample of the candidate pool:
first-party engineering, first-party marketing, practitioner analysis, search
SEO, search business/gossip, off-topic domain science, research, and releases.

The harness is deliberately provider-agnostic:

* `jev` sends the structured decision request and parses a probability.
* `fixture` reads pre-recorded scores, so the report and review packet can be
  validated without an API key.
* `heuristic` is a deterministic baseline built from source roles and title
  patterns. It is a sanity check, not a real judge.

Usage:

    python3 pipeline/quality_benchmark.py run --provider fixture \
        --scores data/quality/benchmark/fixture_scores.json

    python3 pipeline/quality_benchmark.py run --provider jev

    python3 pipeline/quality_benchmark.py run --provider jev --request-only

The output directory contains `report.md` (metrics and slices), `report.json`
(machine-readable), `predictions.json`, and `review.md` (a compact packet for
adjudicating label errors vs judge errors).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ITEMS = ROOT / "data" / "quality" / "benchmark" / "items.json"
DEFAULT_CONFIG = ROOT / "config" / "judge.yaml"
DEFAULT_OUT = ROOT / "data" / "quality" / "benchmark" / "runs"

try:
    from editorial import load_config as load_editorial_config, source_role
except Exception:
    from pipeline.editorial import load_config as load_editorial_config, source_role


# ---------------------------------------------------------------------------
# Configuration and payload


def load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list) or not items:
        raise ValueError(f"No benchmark items in {path}")
    return [item for item in items if isinstance(item, dict)]


def load_judge_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"enabled": False, "provider": "jev"}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _clip(text: Any, limit: int) -> str:
    value = str(text or "").strip()
    return value[: max(1, int(limit))].rstrip()


def build_payload(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    context_chars = int(cfg.get("context_chars", 2500) or 2500)
    payload = {
        "version": str(cfg.get("version", "feed-quality-v1")),
        "question_id": str(cfg.get("question_id", "is_substantive_platform_content")),
        "type": str(cfg.get("type", "noul")),
        "instructions": cfg.get("instructions", {}),
        "criteria": cfg.get("criteria", {}),
        "input": {
            "title": str(item.get("title") or ""),
            "source": str(item.get("source") or ""),
            "source_role": str(item.get("source_role") or ""),
            "published": str(item.get("published") or ""),
            "url": str(item.get("url") or ""),
            "excerpt": _clip(item.get("excerpt") or item.get("summary_1line"), context_chars),
        },
    }
    extra = cfg.get("extra_payload") or {}
    if isinstance(extra, dict):
        payload.update(extra)
    payload_key = str(cfg.get("payload_key") or "").strip()
    if payload_key:
        return {payload_key: payload}
    return payload


def _systemone_instructions(cfg: dict[str, Any]) -> str:
    instructions = cfg.get("instructions", {}) or {}
    criteria = cfg.get("criteria", {}) or {}
    lines = []
    task = str(instructions.get("task") or "").strip()
    context = str(instructions.get("context") or "").strip()
    if task:
        lines.append(f"Task: {task}")
    if context:
        lines.append(f"Context: {context}")
    rules = instructions.get("evaluation_rules") or []
    if rules:
        lines.append("Evaluation rules:")
        lines.extend(f"- {rule}" for rule in rules)
    true_def = str((criteria.get("true") or {}).get("definition") or "").strip()
    false_def = str((criteria.get("false") or {}).get("definition") or "").strip()
    if true_def:
        lines.append(f"Answer yes when: {true_def}")
    if false_def:
        lines.append(f"Answer no when: {false_def}")
    return "\n".join(lines)


def build_systemone_state(item: dict[str, Any], limit: int = 6000) -> str:
    excerpt = _clip(item.get("excerpt") or item.get("summary_1line"), max(200, int(limit)))
    lines = [
        f"Title: {item.get('title') or ''}",
        f"Source: {item.get('source') or ''}",
        f"Source role: {item.get('source_role') or ''}",
        f"Published: {item.get('published') or ''}",
        f"URL: {item.get('url') or ''}",
        "",
        "Excerpt:",
        excerpt,
    ]
    return "\n".join(lines)[: max(200, int(limit))]


def build_systemone_payload(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the OpenRouter System One request for a Jev `noul` question."""
    or_cfg = cfg.get("openrouter", {}) or {}
    question_id = str(or_cfg.get("question_id") or cfg.get("question_id") or "keep")
    state_chars = int(or_cfg.get("state_chars") or cfg.get("context_chars", 6000) or 6000)
    return {
        "model": str(or_cfg.get("model") or cfg.get("model") or "jev-1.14"),
        "state": build_systemone_state(item, state_chars),
        "questions": {
            question_id: {
                "type": "noul",
                "instructions": _systemone_instructions(cfg),
            }
        },
    }


def extract_systemone_score(response: Any, question_id: str = "keep") -> float:
    """Read the `noul` probability from a System One response."""
    if not isinstance(response, dict):
        raise ValueError(f"Unsupported System One response: {type(response).__name__}")
    answers = response.get("answers")
    if isinstance(answers, dict):
        answer = answers.get(question_id)
        if answer is None and len(answers) == 1:
            answer = next(iter(answers.values()))
        if isinstance(answer, dict):
            value = _as_score(answer.get("noul"))
            if value is not None:
                return value
            value = _as_score(answer.get("probability"))
            if value is not None:
                return value
    for key in ("noul", "probability", "score"):
        value = _as_score(response.get(key))
        if value is not None:
            return value
    raise ValueError(f"No noul probability in System One response keys={sorted(response.keys())[:10]}")


# ---------------------------------------------------------------------------
# Providers


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _as_score(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return _clamp(float(value))
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "keep", "pass", "1"}:
            return 1.0
        if text in {"false", "no", "drop", "fail", "0"}:
            return 0.0
        try:
            return _clamp(float(text))
        except ValueError:
            return None
    return None


def extract_score(response: Any) -> float:
    """Pull a probability out of the common response shapes."""
    direct = _as_score(response)
    if direct is not None:
        return direct
    if not isinstance(response, dict):
        raise ValueError(f"Unsupported judge response: {type(response).__name__}")

    for key in ("probability", "score", "confidence", "p", "probability_true"):
        if key in response:
            value = _as_score(response[key])
            if value is not None:
                return value

    for container in ("answer", "data", "result", "prediction", "output"):
        nested = response.get(container)
        if isinstance(nested, dict):
            try:
                return extract_score(nested)
            except ValueError:
                pass

    for key in ("outputs", "results", "predictions"):
        rows = response.get(key)
        if isinstance(rows, list) and rows:
            try:
                return extract_score(rows[0])
            except ValueError:
                pass

    if "label" in response:
        value = _as_score(response["label"])
        if value is not None:
            return value
    raise ValueError(f"No probability in judge response keys={sorted(response.keys())[:10]}")


class FixtureProvider:
    name = "fixture"

    def __init__(self, scores_path: Path) -> None:
        payload = json.loads(scores_path.read_text(encoding="utf-8"))
        self.scores: dict[str, Any] = payload.get("scores", payload) if isinstance(payload, dict) else {}
        self.note = payload.get("note") if isinstance(payload, dict) else None

    def score(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        raw = self.scores.get(str(item.get("id")))
        if isinstance(raw, dict):
            raw = raw.get("score", raw.get("probability"))
        score = _as_score(raw)
        if score is None:
            raise ValueError(f"fixture score missing for {item.get('id')}")
        return {"score": score, "latency_ms": 0, "raw": {"fixture": True}}


class HeuristicProvider:
    """Deterministic baseline, not a quality judge.

    It exists to prove the harness and to show what a cheap source/title rule
    can do. It never reads the expected label or the benchmark slice.
    """

    name = "heuristic"

    ENGINEERING = re.compile(
        r"\b(?:inference|serving|latency|throughput|quantization|benchmark|eval|evaluation|"
        r"agent|agentic|harness|memory|retrieval|kv cache|kernel|gpu|training|fine-tun|"
        r"distillation|tool use|mcp|context window|architecture|optimization|cost)\b",
        re.I,
    )
    MARKETING = re.compile(
        r"\b(?:ads?|advertisers?|customer|partnership|partner|office|mou|funding|raises?|"
        r"valuation|ipo|stock|ipo|appoints?|joins?|award|wins?)\b",
        re.I,
    )
    SEO = re.compile(r"\b(?:vs\.?|versus|top \d+|best|guide|explained|what is|how to|comparison|review)\b", re.I)
    GOSSIP = re.compile(r"\b(?:teen|prodigy|leaves?|outage|ipo|funding|stock|glasses|dispute)\b", re.I)
    OFF_TOPIC = re.compile(
        r"\b(?:clinical|nutrition|antimicrobial|biological data|forest|proteina|"
        r"peptide|medical|patient|php|rts|math)\b",
        re.I,
    )

    def __init__(self) -> None:
        self.editorial_cfg = load_editorial_config()

    def score(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        title = str(item.get("title") or "")
        text = f"{title} {item.get('excerpt') or ''}"
        role = str(item.get("source_role") or source_role(item.get("source", ""), self.editorial_cfg))
        score = 0.45
        if role == "first_party":
            score = 0.72
        elif role in {"practitioner", "research"}:
            score = 0.62
        elif role == "search":
            score = 0.12
        elif role in {"release", "community"}:
            score = 0.25
        if self.ENGINEERING.search(text):
            score += 0.20
        if self.MARKETING.search(title):
            score -= 0.45
        if self.SEO.search(title):
            score -= 0.40
        if self.GOSSIP.search(title):
            score -= 0.40
        if self.OFF_TOPIC.search(title):
            score -= 0.35
        if role in {"release", "community"} and not self.ENGINEERING.search(text):
            score -= 0.20
        return {"score": _clamp(score), "latency_ms": 0, "raw": {"heuristic": True}}


class OpenRouterSystemOneProvider:
    """Jev on OpenRouter's System One API.

    OpenRouter exposes Jev as a typed decision model, not a chat model:
    `POST https://openrouter.ai/api/v1/systemone` with `model`, `state`, and
    a map of typed `questions`. A `noul` question returns the probability of
    yes, which is exactly the keep/drop gate we need.
    """

    name = "openrouter"

    def __init__(self, cfg: dict[str, Any]) -> None:
        or_cfg = cfg.get("openrouter", {}) or {}
        self.endpoint = (
            os.getenv("OPENROUTER_SYSTEMONE_ENDPOINT", "").strip()
            or str(or_cfg.get("endpoint") or "https://openrouter.ai/api/v1/systemone").strip()
        )
        self.api_key = os.getenv(
            str(or_cfg.get("api_key_env") or "OPENROUTER_API_KEY"),
            "",
        ).strip()
        self.model = (
            os.getenv("OPENROUTER_JEV_MODEL", "").strip()
            or str(or_cfg.get("model") or cfg.get("model") or "jev-1.14")
        )
        self.question_id = str(or_cfg.get("question_id") or cfg.get("question_id") or "keep")
        self.cache_dir = ROOT / str(or_cfg.get("cache_dir") or "data/quality/cache/openrouter")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = float(or_cfg.get("timeout_seconds", cfg.get("timeout_seconds", 60)) or 60)
        self.max_retries = int(or_cfg.get("max_retries", cfg.get("max_retries", 2)) or 0)

    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def _cache_path(self, payload: dict[str, Any]) -> Path:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]
        return self.cache_dir / f"openrouter-{digest}.json"

    def _post(self, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://www.llm-digest.com",
            "X-Title": "llm-digest-quality-benchmark",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.monotonic()
            req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                    latency = int((time.monotonic() - started) * 1000)
                    return json.loads(raw), latency
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    detail = exc.read().decode("utf-8", errors="replace")[:1000]
                    raise RuntimeError(f"openrouter_http_{exc.code}: {detail}") from exc
                time.sleep(1.5 ** (attempt + 1))
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(1.5 ** (attempt + 1))
        raise RuntimeError(f"openrouter_request_failed: {last_error}")

    def payload(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        return build_systemone_payload(item, cfg)

    def score(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        if not self.configured():
            raise RuntimeError("openrouter_not_configured: set OPENROUTER_API_KEY")
        payload = self.payload(item, cfg)
        cache_path = self._cache_path(payload)
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return {
                "score": float(cached["score"]),
                "latency_ms": int(cached.get("latency_ms", 0)),
                "raw": cached.get("raw", {}),
                "cached": True,
            }
        raw, latency = self._post(payload)
        score = extract_systemone_score(raw, self.question_id)
        cache_path.write_text(
            json.dumps(
                {
                    "model": self.model,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": latency,
                    "score": score,
                    "raw": raw,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"score": score, "latency_ms": latency, "raw": raw, "cached": False}


class JevProvider:
    name = "jev"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.endpoint = os.getenv("JEV_ENDPOINT", "").strip() or str(cfg.get("endpoint") or "").strip()
        self.api_key = os.getenv(str(cfg.get("api_key_env") or "JEV_API_KEY"), "").strip()
        self.cache_dir = ROOT / str(cfg.get("cache_dir") or "data/quality/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = os.getenv("JEV_MODEL", "").strip() or str(cfg.get("model") or "jev")
        self.timeout = float(cfg.get("timeout_seconds", 30) or 30)
        self.max_retries = int(cfg.get("max_retries", 2) or 0)

    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def _cache_path(self, payload: dict[str, Any]) -> Path:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]
        return self.cache_dir / f"jev-{digest}.json"

    def _post(self, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        headers = {"Content-Type": "application/json"}
        auth_header = str(self.cfg.get("auth_header") or "Authorization")
        auth_prefix = str(self.cfg.get("auth_prefix") or "Bearer ")
        if self.api_key:
            headers[auth_header] = f"{auth_prefix}{self.api_key}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.monotonic()
            req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                    latency = int((time.monotonic() - started) * 1000)
                    return json.loads(raw), latency
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    detail = exc.read().decode("utf-8", errors="replace")[:1000]
                    raise RuntimeError(f"jev_http_{exc.code}: {detail}") from exc
                time.sleep(1.5 ** (attempt + 1))
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                time.sleep(1.5 ** (attempt + 1))
        raise RuntimeError(f"jev_request_failed: {last_error}")

    def score(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        if not self.configured():
            raise RuntimeError("jev_not_configured: set judge.endpoint and JEV_API_KEY")
        payload = build_payload(item, cfg)
        cache_path = self._cache_path(payload)
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return {
                "score": float(cached["score"]),
                "latency_ms": int(cached.get("latency_ms", 0)),
                "raw": cached.get("raw", {}),
                "cached": True,
            }
        raw, latency = self._post(payload)
        score = extract_score(raw)
        cache_path.write_text(
            json.dumps(
                {
                    "model": self.model,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": latency,
                    "score": score,
                    "raw": raw,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"score": score, "latency_ms": latency, "raw": raw, "cached": False}


# ---------------------------------------------------------------------------
# Metrics


def _label(value: Any) -> int:
    return 1 if str(value).strip().lower() in {"keep", "1", "true", "yes"} else 0


def compute_metrics(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    brier_terms: list[float] = []
    bins: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for row in rows:
        score = _clamp(row["score"])
        expected = int(row["expected"])
        predicted = 1 if score >= threshold else 0
        if expected and predicted:
            tp += 1
        elif expected and not predicted:
            fn += 1
        elif not expected and predicted:
            fp += 1
        else:
            tn += 1
        brier_terms.append((score - expected) ** 2)
        bins[min(9, int(score * 10))].append((score, expected))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    total = len(rows)
    accuracy = (tp + tn) / total if total else 0.0
    positives = sum(1 for row in rows if int(row["expected"]) == 1)
    negatives = total - positives
    sensitivity = recall
    specificity = tn / (tn + fp) if tn + fp else 0.0
    balanced_accuracy = (sensitivity + specificity) / 2 if positives and negatives else accuracy
    brier = sum(brier_terms) / total if total else 0.0
    ece = 0.0
    for bucket in bins.values():
        if not bucket:
            continue
        mean_score = sum(score for score, _ in bucket) / len(bucket)
        mean_label = sum(label for _, label in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(mean_score - mean_label)
    return {
        "n": total,
        "threshold": round(threshold, 3),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "balanced_accuracy": round(balanced_accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "specificity": round(specificity, 4),
        "brier": round(brier, 4),
        "ece_10": round(ece, 4),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def roc_auc(rows: list[dict[str, Any]]) -> float:
    positives = [float(row["score"]) for row in rows if int(row["expected"]) == 1]
    negatives = [float(row["score"]) for row in rows if int(row["expected"]) == 0]
    if not positives or not negatives:
        return 0.0
    wins = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return round(wins / (len(positives) * len(negatives)), 4)


def threshold_sweep(rows: list[dict[str, Any]], step: float = 0.05) -> tuple[list[dict[str, Any]], float]:
    candidates: list[dict[str, Any]] = []
    threshold = step
    while threshold < 1.0 - 1e-9:
        metrics = compute_metrics(rows, threshold)
        candidates.append(metrics)
        threshold = round(threshold + step, 4)
    if not candidates:
        return [], 0.5
    # Prefer a threshold that clears both 80% precision and 80% recall.
    qualified = [m for m in candidates if m["precision"] >= 0.8 and m["recall"] >= 0.8]
    pool = qualified or candidates
    best = max(pool, key=lambda m: (m["f1"], m["balanced_accuracy"], m["precision"]))
    return candidates, float(best["threshold"])


def baseline_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    total = len(rows)
    positives = sum(1 for row in rows if int(row["expected"]) == 1)
    negatives = total - positives
    always_drop = {
        "accuracy": round(negatives / total, 4) if total else 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
    }
    keep_precision = positives / total if total else 0.0
    always_keep = {
        "accuracy": round(keep_precision, 4),
        "precision": round(keep_precision, 4),
        "recall": 1.0 if positives else 0.0,
        "f1": round(2 * keep_precision / (1 + keep_precision), 4) if keep_precision else 0.0,
    }
    return {"always_drop": always_drop, "always_keep": always_keep}


def slice_metrics(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("slice") or "unknown")].append(row)
    out = []
    for name, group in sorted(grouped.items()):
        metrics = compute_metrics(group, threshold)
        metrics["slice"] = name
        metrics["keep_expected"] = sum(1 for row in group if int(row["expected"]) == 1)
        metrics["drop_expected"] = len(group) - metrics["keep_expected"]
        out.append(metrics)
    return out


# ---------------------------------------------------------------------------
# Report


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _review_items(rows: list[dict[str, Any]], threshold: float) -> dict[str, list[dict[str, Any]]]:
    false_positives = [
        row for row in rows
        if int(row["expected"]) == 0 and float(row["score"]) >= threshold
    ]
    false_negatives = [
        row for row in rows
        if int(row["expected"]) == 1 and float(row["score"]) < threshold
    ]
    ambiguous = [
        row for row in rows
        if 0.35 <= float(row["score"]) <= 0.65
    ]
    false_positives.sort(key=lambda row: float(row["score"]), reverse=True)
    false_negatives.sort(key=lambda row: float(row["score"]))
    ambiguous.sort(key=lambda row: abs(float(row["score"]) - 0.5), reverse=True)
    return {
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "ambiguous": ambiguous,
    }


def _review_section(title: str, rows: list[dict[str, Any]], threshold: float) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        lines += ["None.", ""]
        return lines
    for row in rows:
        lines += [
            f"### {row['id']} | score {row['score']:.3f} | expected {row['expected_label']} ({'keep' if row['expected'] else 'drop'}) | predicted {'keep' if row['score'] >= threshold else 'drop'}",
            f"**{row['title']}**",
            "",
            f"- source: `{row['source']}` · slice: `{row['slice']}` · published: {row.get('published') or 'unknown'}",
            f"- why labeled this way: {row.get('notes') or '(no note)'}",
            f"- url: {row.get('url') or ''}",
            "",
            f"> {_clip(row.get('excerpt') or '', 700)}",
            "",
        ]
    return lines


def write_reports(
    out_dir: Path,
    rows: list[dict[str, Any]],
    provider: str,
    model: str,
    threshold: float,
    sweep: list[dict[str, Any]],
    slices: list[dict[str, Any]],
    benchmark_version: str,
    provider_note: str = "",
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    at_050 = compute_metrics(rows, 0.5)
    tuned = compute_metrics(rows, threshold)
    auc = roc_auc(rows)
    review = _review_items(rows, threshold)
    baselines = baseline_metrics(rows)
    distribution = Counter(
        "0.0-0.2" if row["score"] < 0.2 else
        "0.2-0.4" if row["score"] < 0.4 else
        "0.4-0.6" if row["score"] < 0.6 else
        "0.6-0.8" if row["score"] < 0.8 else
        "0.8-1.0"
        for row in rows
    )
    summary = {
        "provider": provider,
        "model": model,
        "provider_note": provider_note,
        "benchmark_version": benchmark_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "at_0_5": {**at_050, "auc": auc},
        "tuned": {**tuned, "auc": auc},
        "score_distribution": dict(sorted(distribution.items())),
        "baselines": baselines,
        "slices": slices,
        "review_counts": {key: len(value) for key, value in review.items()},
    }

    predictions = {"summary": summary, "rows": rows}
    (out_dir / "predictions.json").write_text(json.dumps(predictions, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Jev quality benchmark",
        "",
        f"- provider: `{provider}`",
        f"- model: `{model}`",
        f"- benchmark: `{benchmark_version}`",
        *([f"- note: {provider_note}"] if provider_note else []),
        f"- generated: {summary['generated_at']}",
        f"- items: {len(rows)}",
        f"- tuned threshold: {threshold:.2f}",
        "",
        "## Headline",
        "",
        f"- AUC: **{auc:.3f}**",
        f"- Brier: **{tuned['brier']:.3f}** · ECE(10): **{tuned['ece_10']:.3f}**",
        f"- At 0.50: precision {at_050['precision']:.3f} · recall {at_050['recall']:.3f} · F1 {at_050['f1']:.3f}",
        f"- Tuned: precision {tuned['precision']:.3f} · recall {tuned['recall']:.3f} · F1 {tuned['f1']:.3f} · balanced acc {tuned['balanced_accuracy']:.3f}",
        "",
        "## Baselines",
        "",
        _md_table(
            ["baseline", "accuracy", "precision", "recall", "F1"],
            [
                ["always drop", f"{baselines['always_drop']['accuracy']:.3f}", "0.000", "0.000", "0.000"],
                ["always keep", f"{baselines['always_keep']['accuracy']:.3f}", f"{baselines['always_keep']['precision']:.3f}", "1.000", f"{baselines['always_keep']['f1']:.3f}"],
            ],
        ),
        "",
        "## Threshold sweep",
        "",
        _md_table(
            ["threshold", "precision", "recall", "F1", "balanced acc"],
            [
                [f"{row['threshold']:.2f}", f"{row['precision']:.3f}", f"{row['recall']:.3f}", f"{row['f1']:.3f}", f"{row['balanced_accuracy']:.3f}"]
                for row in sweep
            ],
        ),
        "",
        "## By slice",
        "",
        _md_table(
            ["slice", "n", "keep", "drop", "precision", "recall", "F1"],
            [
                [row["slice"], row["n"], row["keep_expected"], row["drop_expected"], f"{row['precision']:.3f}", f"{row['recall']:.3f}", f"{row['f1']:.3f}"]
                for row in slices
            ],
        ),
        "",
        "## Review",
        "",
        f"- false positives: {len(review['false_positives'])}",
        f"- false negatives: {len(review['false_negatives'])}",
        f"- ambiguous (0.35-0.65): {len(review['ambiguous'])}",
        "",
        "Open `review.md` to adjudicate label errors vs judge errors.",
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    review_lines = [
        "# Judge review packet",
        "",
        "Mark each case as `label_error`, `judge_error`, or `ambiguous`.",
        "If the label is wrong, edit `data/quality/benchmark/items.json` and rerun.",
        "If the judge is wrong, keep the label and record the failure mode.",
        "",
        f"- provider: `{provider}` · model: `{model}` · threshold: {threshold:.2f}",
        f"- AUC {auc:.3f} · precision {tuned['precision']:.3f} · recall {tuned['recall']:.3f} · F1 {tuned['f1']:.3f}",
        "",
    ]
    review_lines += _review_section("False positives: judge kept, label says drop", review["false_positives"], threshold)
    review_lines += _review_section("False negatives: judge dropped, label says keep", review["false_negatives"], threshold)
    review_lines += _review_section("Ambiguous scores", review["ambiguous"], threshold)
    (out_dir / "review.md").write_text("\n".join(review_lines), encoding="utf-8")
    return summary


# ---------------------------------------------------------------------------
# Runner


def run(args: argparse.Namespace) -> int:
    items = load_items(Path(args.items))
    cfg = load_judge_config(Path(args.config))
    benchmark_version = json.loads(Path(args.items).read_text(encoding="utf-8")).get("benchmark_version", "unknown")
    if args.limit:
        items = items[: max(1, int(args.limit))]

    if args.provider == "fixture":
        if not args.scores:
            raise SystemExit("--scores is required for --provider fixture")
        provider = FixtureProvider(Path(args.scores))
    elif args.provider == "heuristic":
        provider = HeuristicProvider()
    elif args.provider == "openrouter":
        provider = OpenRouterSystemOneProvider(cfg)
        if not provider.configured() and not args.request_only:
            print(
                "openrouter_not_configured: export OPENROUTER_API_KEY",
                file=sys.stderr,
            )
            return 2
    elif args.provider == "jev":
        provider = JevProvider(cfg)
        if not provider.configured() and not args.request_only:
            print(
                "jev_not_configured: set config/judge.yaml endpoint and export "
                f"{cfg.get('api_key_env', 'JEV_API_KEY')}",
                file=sys.stderr,
            )
            return 2
    else:
        raise SystemExit(f"unknown provider: {args.provider}")

    out_dir = Path(args.out) if args.out else DEFAULT_OUT / f"{args.provider}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.request_only:
        request_dir = out_dir / "requests"
        request_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            if args.provider == "openrouter":
                payload = build_systemone_payload(item, cfg)
            else:
                payload = build_payload(item, cfg)
            (request_dir / f"{item['id']}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        print(f"request_only=true dir={request_dir}")
        return 0

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        expected = _label(item.get("expected"))
        row = {
            "id": str(item.get("id")),
            "slice": item.get("slice"),
            "source": item.get("source"),
            "source_role": item.get("source_role"),
            "title": item.get("title"),
            "url": item.get("url"),
            "published": item.get("published"),
            "expected": expected,
            "expected_label": item.get("expected_label"),
            "notes": item.get("notes"),
            "excerpt": item.get("excerpt"),
        }
        try:
            result = provider.score(item, cfg)
            row.update(
                {
                    "score": _clamp(result["score"]),
                    "latency_ms": int(result.get("latency_ms", 0)),
                    "cached": bool(result.get("cached", False)),
                    "error": None,
                }
            )
        except Exception as exc:
            row.update({"score": 0.0, "latency_ms": 0, "cached": False, "error": str(exc)})
            print(f"score_failed id={row['id']} err={exc}", file=sys.stderr)
        rows.append(row)
        if index % 10 == 0 or index == len(items):
            print(f"scored={index}/{len(items)}")

    errors = [row for row in rows if row.get("error")]
    if args.provider == "jev" and errors:
        print(f"jev_failed rows={len(errors)}; first={errors[0]['error']}", file=sys.stderr)
        return 3

    if args.threshold is not None:
        threshold = float(args.threshold)
        sweep = []
    else:
        sweep, threshold = threshold_sweep(rows)
    slices = slice_metrics(rows, threshold)
    if provider.name == "openrouter":
        model_name = str((cfg.get("openrouter", {}) or {}).get("model") or cfg.get("model") or "jev-1.14")
    elif provider.name == "jev":
        model_name = str(cfg.get("model") or "jev")
    else:
        model_name = provider.name
    summary = write_reports(
        out_dir=out_dir,
        rows=rows,
        provider=provider.name,
        model=model_name,
        threshold=threshold,
        sweep=sweep,
        slices=slices,
        benchmark_version=benchmark_version,
        provider_note=str(getattr(provider, "note", "") or ""),
    )
    tuned = summary["tuned"]
    print(
        "BENCHMARK_OK "
        f"provider={provider.name} items={summary['at_0_5']['n']} "
        f"auc={summary['at_0_5']['auc']} "
        f"precision={tuned['precision']} recall={tuned['recall']} f1={tuned['f1']} "
        f"threshold={threshold} brier={tuned['brier']} ece10={tuned['ece_10']} "
        f"false_pos={summary['review_counts']['false_positives']} "
        f"false_neg={summary['review_counts']['false_negatives']} "
        f"report={out_dir / 'report.md'}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the feed quality judge")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="score the benchmark and write a report")
    run_parser.add_argument("--provider", choices=["fixture", "heuristic", "openrouter", "jev"], default="fixture")
    run_parser.add_argument("--items", default=str(DEFAULT_ITEMS))
    run_parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    run_parser.add_argument("--scores", help="fixture scores JSON (provider=fixture)")
    run_parser.add_argument("--out", help="output directory")
    run_parser.add_argument("--threshold", type=float, help="fixed keep threshold (default: tune)")
    run_parser.add_argument("--limit", type=int, help="score only the first N items")
    run_parser.add_argument("--request-only", action="store_true", help="write payloads, do not call the API")
    run_parser.set_defaults(func=run)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
