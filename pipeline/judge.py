"""Shared quality-judge client and policy for the feed.

The judge is a typed decision model (Jev) behind OpenRouter's System One API.
It is deliberately separate from the benchmark so the production builder and
the offline evaluation use exactly the same request shape, cache, and policy.

The provider is fail-open at the call site: this module raises on a missing
key or a malformed response, and the caller decides whether to continue with
the deterministic policy. It never invents a score.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "judge.yaml"


def load_judge_config(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_CONFIG
    if not path.exists():
        return {"enabled": False, "provider": "openrouter"}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _clip(text: Any, limit: int) -> str:
    value = str(text or "").strip()
    return value[: max(1, int(limit))].rstrip()


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
    excerpt = _clip(item.get("excerpt") or item.get("content_excerpt") or item.get("summary_1line") or item.get("summary"), max(200, int(limit)))
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


def _systemone_questions(cfg: dict[str, Any]) -> dict[str, Any]:
    or_cfg = cfg.get("openrouter", {}) or {}
    configured = or_cfg.get("questions")
    if isinstance(configured, dict) and configured:
        out = {}
        for question_id, question in configured.items():
            if not isinstance(question, dict):
                continue
            spec: dict[str, Any] = {
                "type": str(question.get("type") or "noul"),
                "instructions": str(question.get("instructions") or "").strip(),
            }
            if isinstance(question.get("criteria"), dict):
                spec["criteria"] = dict(question.get("criteria") or {})
            out[str(question_id)] = spec
        if out:
            if or_cfg.get("use_holistic_keep", False):
                out["keep"] = {
                    "type": "noul",
                    "instructions": _systemone_instructions(cfg),
                }
            return out
    question_id = str(or_cfg.get("question_id") or cfg.get("question_id") or "keep")
    return {
        question_id: {
            "type": "noul",
            "instructions": _systemone_instructions(cfg),
        }
    }


def build_systemone_payload(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    or_cfg = cfg.get("openrouter", {}) or {}
    state_chars = int(or_cfg.get("state_chars") or cfg.get("context_chars", 6000) or 6000)
    return {
        "model": str(or_cfg.get("model") or cfg.get("model") or "jev-1.14"),
        "state": build_systemone_state(item, state_chars),
        "questions": _systemone_questions(cfg),
    }


def build_payload(item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Structured payload for the direct TypeSafe Decisions API."""
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
            "excerpt": _clip(item.get("excerpt") or item.get("content_excerpt") or item.get("summary_1line"), context_chars),
        },
    }
    extra = cfg.get("extra_payload") or {}
    if isinstance(extra, dict):
        payload.update(extra)
    payload_key = str(cfg.get("payload_key") or "").strip()
    if payload_key:
        return {payload_key: payload}
    return payload


def extract_systemone_answers(response: Any) -> dict[str, float]:
    if not isinstance(response, dict):
        raise ValueError(f"Unsupported System One response: {type(response).__name__}")
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise ValueError(f"No answers in System One response keys={sorted(response.keys())[:10]}")
    out: dict[str, float] = {}
    for question_id, answer in answers.items():
        if not isinstance(answer, dict):
            continue
        value = _as_score(answer.get("noul"))
        if value is None:
            value = _as_score(answer.get("probability"))
        if value is not None:
            out[str(question_id)] = value
    if not out:
        raise ValueError(f"No noul probabilities in System One answers={list(answers)[:10]}")
    return out


def extract_systemone_choices(response: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(response, dict):
        return {}
    answers = response.get("answers")
    if not isinstance(answers, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for question_id, answer in answers.items():
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            continue
        choice = answer.get("choice")
        if choice is None:
            continue
        probabilities = answer.get("probabilities") if isinstance(answer.get("probabilities"), dict) else {}
        out[str(question_id)] = {
            "choice": str(choice),
            "confidence": _as_score(answer.get("confidence")) or 0.0,
            "probabilities": {str(k): _clamp(float(v)) for k, v in probabilities.items() if isinstance(v, (int, float))},
        }
    return out


def extract_systemone_score(response: Any, question_id: str = "keep") -> float:
    answers = extract_systemone_answers(response)
    if question_id in answers:
        return answers[question_id]
    if len(answers) == 1:
        return next(iter(answers.values()))
    raise ValueError(f"No System One answer for {question_id}; got {sorted(answers)}")


def extract_score(response: Any) -> float:
    """Pull a probability out of the common direct-API response shapes."""
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


def hybrid_score(signals: dict[str, float], hybrid: dict[str, Any]) -> float:
    primary_key = str(hybrid.get("primary") or "keep")
    primary = float(signals.get(primary_key, 0.5))
    gate_score = _clamp(float(hybrid.get("gate_score", 0.1)))
    for question, threshold in (hybrid.get("drop_if_above") or {}).items():
        if question in signals and signals[question] >= float(threshold):
            return min(primary, gate_score)
    for question, threshold in (hybrid.get("drop_if_below") or {}).items():
        if question in signals and signals[question] < float(threshold):
            return min(primary, gate_score)
    return primary


def composite_score(signals: dict[str, float], composite: dict[str, Any]) -> float:
    positive = [str(q) for q in (composite.get("positive") or []) if str(q) in signals]
    negative = [str(q) for q in (composite.get("negative") or []) if str(q) in signals]
    if not positive:
        positive = list(signals)
    combine = str(composite.get("combine") or "product").strip().lower()
    if combine == "min":
        values = [signals[q] for q in positive] + [1.0 - signals[q] for q in negative]
        return _clamp(min(values) if values else 0.5)
    if combine == "weighted":
        weights = composite.get("weights") or {}
        score = 1.0
        for question in positive:
            score *= max(0.0, signals[question]) ** float(weights.get(question, 1.0))
        for question in negative:
            score *= max(0.0, 1.0 - signals[question]) ** float(weights.get(question, 1.0))
        return _clamp(score)
    score = 1.0
    for question in positive:
        score *= signals[question]
    for question in negative:
        score *= 1.0 - signals[question]
    return _clamp(score)


def judge_verdict(score: float | None, drop_below: float = 0.15, keep_at: float = 0.5) -> str:
    if score is None:
        return "unjudged"
    if score < float(drop_below):
        return "drop"
    if score < float(keep_at):
        return "review"
    return "keep"


def judge_adjustment(item: dict[str, Any], cfg: dict[str, Any] | None = None) -> float:
    """Bounded ranking adjustment. The judge never owns the global rank."""
    cfg = cfg or {}
    policy = cfg.get("adjustment") or cfg.get("judge_adjustment") or {}
    score = item.get("judge_score")
    if score is None:
        return 0.0
    if float(score) >= float(policy.get("keep_at", 0.6)):
        return float(policy.get("keep_bonus", 0.15))
    if float(score) <= float(policy.get("drop_at", 0.25)):
        return -abs(float(policy.get("drop_penalty", 0.30)))
    return 0.0


class OpenRouterSystemOneProvider:
    """Jev on OpenRouter's typed System One API."""

    name = "openrouter"

    def __init__(self, cfg: dict[str, Any]) -> None:
        or_cfg = cfg.get("openrouter", {}) or {}
        self.cfg = cfg
        self.endpoint = (
            os.getenv("OPENROUTER_SYSTEMONE_ENDPOINT", "").strip()
            or str(or_cfg.get("endpoint") or "https://openrouter.ai/api/v1/systemone").strip()
        )
        self.api_key = os.getenv(str(or_cfg.get("api_key_env") or "OPENROUTER_API_KEY"), "").strip()
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
            "X-Title": "llm-digest-quality-judge",
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
                "signals": cached.get("signals") or {},
                "choices": cached.get("choices") or {},
                "latency_ms": int(cached.get("latency_ms", 0)),
                "raw": cached.get("raw", {}),
                "cached": True,
            }
        raw, latency = self._post(payload)
        signals = extract_systemone_answers(raw)
        choices = extract_systemone_choices(raw)
        or_cfg = cfg.get("openrouter", {}) or {}
        score_mode = str(or_cfg.get("score_mode") or "single").strip().lower()
        if score_mode == "composite":
            score = composite_score(signals, or_cfg.get("composite", {}) or {})
        elif score_mode == "hybrid":
            score = hybrid_score(signals, or_cfg.get("hybrid", {}) or {})
        else:
            score = signals.get(self.question_id)
            if score is None:
                score = extract_systemone_score(raw, self.question_id)
        cache_path.write_text(
            json.dumps(
                {
                    "model": self.model,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": latency,
                    "score": score,
                    "signals": signals,
                    "choices": choices,
                    "raw": raw,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "score": score,
            "signals": signals,
            "choices": choices,
            "latency_ms": latency,
            "raw": raw,
            "cached": False,
        }


class JevProvider:
    """Direct TypeSafe Decisions API (optional alternative to OpenRouter)."""

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

    def payload(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        return build_payload(item, cfg)

    def score(self, item: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        if not self.configured():
            raise RuntimeError("jev_not_configured: set judge.endpoint and JEV_API_KEY")
        payload = build_payload(item, cfg)
        cache_path = self._cache_path(payload)
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return {
                "score": float(cached["score"]),
                "signals": cached.get("signals") or {},
                "choices": cached.get("choices") or {},
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
                    "signals": {},
                    "choices": {},
                    "raw": raw,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"score": score, "signals": {}, "choices": {}, "latency_ms": latency, "raw": raw, "cached": False}


def provider_from_config(cfg: dict[str, Any]) -> OpenRouterSystemOneProvider | JevProvider:
    provider = str(cfg.get("provider") or "openrouter").strip().lower()
    if provider == "jev":
        return JevProvider(cfg)
    return OpenRouterSystemOneProvider(cfg)
