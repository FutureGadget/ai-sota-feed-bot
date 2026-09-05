#!/usr/bin/env python3
"""Validate and index Agent Skill Lab pilot records.

Published records live in ``data/playbook/lab/<slug>.json``. Drafts live in
``data/playbook/lab/drafts/`` and are intentionally ignored. The builder
validates every published source record before replacing either derived file:

- ``index.json`` contains compact newest-first summaries.
- ``latest.json`` contains the highest published pilot edition in full.

Usage:
    python3 pipeline/build_skill_lab.py
    python3 pipeline/build_skill_lab.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_DIR = ROOT / "data" / "playbook" / "lab"
DEFAULT_ARTIFACT_ROOT = ROOT / "web"

LAB_ID_RE = re.compile(r"^lab-[a-z0-9][a-z0-9-]{0,76}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
MEASURE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
CONDITION_ORDER = ("no-skill", "minimal-instructions", "full-skill")
REQUIRED_MEASURE_IDS = {"task-success", "final-quality", "trajectory", "efficiency"}
RESERVED_SLUGS = {"drafts", "index", "latest", "list"}
LAB_ARTIFACT_PREFIX = "/lab-artifacts/"
INERT_ARTIFACT_SUFFIXES = {".json", ".jsonl", ".md", ".txt"}
ARTIFACT_URL_REQUIREMENT = (
    f"a {LAB_ARTIFACT_PREFIX} path with an inert extension "
    "or credential-free HTTPS URL without query or fragment"
)
METRIC_FIELDS = {
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "tool_calls",
    "interventions",
    "recovery_events",
    "unnecessary_actions",
}
DERIVED_TOP_LEVEL_FIELDS = {"aggregates", "winner"}
DERIVED_CONDITION_FIELDS = {"aggregate", "success_rate", "median_quality", "median_cost"}


class SkillLabValidationError(ValueError):
    """Raised when any published Skill Lab source record is invalid."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _number(value: Any, *, minimum: float = 0) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= minimum
    )


def _non_finite_paths(value: Any, prefix: str = "record") -> list[str]:
    """Return paths to every non-finite number, including unknown fields."""
    paths: list[str] = []
    if isinstance(value, float) and not math.isfinite(value):
        paths.append(prefix)
    elif isinstance(value, dict):
        for key, item in value.items():
            paths.extend(_non_finite_paths(item, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_non_finite_paths(item, f"{prefix}[{index}]"))
    return paths


def _iso_timestamp(value: Any) -> bool:
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _date(value: Any) -> date | None:
    if not _text(value):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _decoded_url_path(value: str) -> str | None:
    """Decode bounded nested escapes and reject controls or suspicious depth."""
    decoded = value
    for _ in range(8):
        next_path = unquote(decoded)
        if next_path == decoded:
            if any(ord(character) < 32 or ord(character) == 127 for character in decoded):
                return None
            return decoded
        decoded = next_path
    return None


def is_safe_public_url(value: Any) -> bool:
    """Allow only same-origin root paths or credential-free HTTPS URLs."""
    if not _text(value):
        return False
    raw = str(value).strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        return False
    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        _ = parsed.port  # Access validates malformed and out-of-range ports.
    except ValueError:
        return False
    decoded_path = _decoded_url_path(parsed.path)
    if decoded_path is None:
        return False
    if raw.startswith("/"):
        if (
            raw.startswith("//")
            or parsed.scheme
            or parsed.netloc
            or "\\" in raw
            or "\\" in decoded_path
        ):
            return False
        return ".." not in decoded_path.split("/")
    return (
        parsed.scheme == "https"
        and bool(hostname)
        and parsed.username is None
        and parsed.password is None
    )


def is_safe_artifact_url(value: Any) -> bool:
    """Accept immutable HTTPS evidence or a staged Lab artifact path."""
    if not is_safe_public_url(value):
        return False
    raw = str(value).strip()
    parsed = urlsplit(raw)
    if parsed.query or parsed.fragment or "?" in raw or "#" in raw:
        return False
    if raw.startswith("/"):
        decoded_path = _decoded_url_path(parsed.path)
        return (
            decoded_path is not None
            and decoded_path.startswith(LAB_ARTIFACT_PREFIX)
            and Path(decoded_path).suffix.lower() in INERT_ARTIFACT_SUFFIXES
        )
    return True


def _require_text(container: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not _text(container.get(field)):
        errors.append(f"{prefix}.{field} must be a non-empty string")


def _validate_environment(environment: Any, errors: list[str]) -> None:
    prefix = "method.environment"
    if not isinstance(environment, dict):
        errors.append(f"{prefix} must be an object")
        return
    for name in ("model", "harness"):
        item = environment.get(name)
        if not isinstance(item, dict):
            errors.append(f"{prefix}.{name} must be an object")
            continue
        _require_text(item, "name", f"{prefix}.{name}", errors)
        _require_text(item, "version", f"{prefix}.{name}", errors)
    _require_text(environment, "reasoning_effort", prefix, errors)
    fixture = environment.get("repository_fixture")
    if not isinstance(fixture, dict):
        errors.append(f"{prefix}.repository_fixture must be an object")
    else:
        _require_text(fixture, "name", f"{prefix}.repository_fixture", errors)
        _require_text(fixture, "revision", f"{prefix}.repository_fixture", errors)
    if not _text_list(environment.get("permissions")):
        errors.append(f"{prefix}.permissions must be a non-empty string array")
    budget = environment.get("budget")
    if not isinstance(budget, dict):
        errors.append(f"{prefix}.budget must be an object")
        return
    for field in ("timeout_seconds", "max_tokens_per_run"):
        if not _number(budget.get(field), minimum=1):
            errors.append(f"{prefix}.budget.{field} must be a positive number")
    if not _number(budget.get("max_cost_usd_per_run")):
        errors.append(f"{prefix}.budget.max_cost_usd_per_run must be a non-negative number")


def _validate_skill(skill: Any, state: str, errors: list[str]) -> str | None:
    prefix = "method.skill"
    if state == "protocol":
        if skill is not None:
            errors.append(f"protocol {prefix} must be omitted until a result pins one skill")
        return None
    if not isinstance(skill, dict):
        errors.append(f"{prefix} must be an object")
        return None
    for field in ("name", "revision"):
        _require_text(skill, field, prefix, errors)
    if not is_safe_artifact_url(skill.get("source_url")):
        errors.append(f"{prefix}.source_url must be {ARTIFACT_URL_REQUIREMENT}")
    digest = str(skill.get("sha256") or "")
    if not SHA256_RE.match(digest):
        errors.append(f"{prefix}.sha256 must be a lowercase SHA-256 digest")
        return None
    return digest


def _validate_task(task: Any, errors: list[str]) -> None:
    if not isinstance(task, dict):
        errors.append("method.task must be an object")
        return
    _require_text(task, "description", "method.task", errors)
    _require_text(task, "evaluation_method", "method.task", errors)
    if not _text_list(task.get("success_criteria")):
        errors.append("method.task.success_criteria must be a non-empty string array")


def _validate_measures(measures: Any, errors: list[str]) -> None:
    if not isinstance(measures, list) or not measures:
        errors.append("method.measures must be a non-empty array")
        return
    seen: set[str] = set()
    for index, measure in enumerate(measures):
        prefix = f"method.measures[{index}]"
        if not isinstance(measure, dict):
            errors.append(f"{prefix} must be an object")
            continue
        measure_id = str(measure.get("id") or "")
        if not MEASURE_ID_RE.match(measure_id):
            errors.append(f"{prefix}.id must be URL-safe")
        elif measure_id in seen:
            errors.append(f"{prefix}.id duplicates {measure_id}")
        seen.add(measure_id)
        _require_text(measure, "label", prefix, errors)
        _require_text(measure, "description", prefix, errors)
    missing = REQUIRED_MEASURE_IDS - seen
    if missing:
        errors.append(f"method.measures must include required measure ids {sorted(missing)}")


def _validate_run(run: Any, prefix: str, seen_run_ids: set[str], errors: list[str]) -> None:
    if not isinstance(run, dict):
        errors.append(f"{prefix} must be an object")
        return
    run_id = str(run.get("id") or "")
    if not SLUG_RE.match(run_id):
        errors.append(f"{prefix}.id must be URL-safe")
    elif run_id in seen_run_ids:
        errors.append(f"{prefix}.id duplicates run id {run_id}")
    seen_run_ids.add(run_id)
    if not isinstance(run.get("success"), bool):
        errors.append(f"{prefix}.success must be a boolean")
    quality = run.get("quality_score")
    if not _number(quality) or quality > 100:
        errors.append(f"{prefix}.quality_score must be a number from 0 to 100")
    metrics = run.get("metrics")
    if not isinstance(metrics, dict):
        errors.append(f"{prefix}.metrics must be an object")
    else:
        for field in sorted(METRIC_FIELDS):
            if not _number(metrics.get(field)):
                errors.append(f"{prefix}.metrics.{field} must be a non-negative number")
    _require_text(run, "trajectory_summary", prefix, errors)
    if not is_safe_artifact_url(run.get("artifact_url")):
        errors.append(f"{prefix}.artifact_url must be {ARTIFACT_URL_REQUIREMENT}")


def _validate_conditions(
    conditions: Any,
    state: str,
    runs_per_condition: int | None,
    skill_sha256: str | None,
    errors: list[str],
) -> None:
    if not isinstance(conditions, list):
        errors.append("method.conditions must be an array")
        return
    ids = [str(item.get("id") or "") for item in conditions if isinstance(item, dict)]
    if ids != list(CONDITION_ORDER) or len(conditions) != len(CONDITION_ORDER):
        errors.append(
            f"method.conditions must contain the exact condition ids in order {list(CONDITION_ORDER)}"
        )
    seen_run_ids: set[str] = set()
    instruction_evidence: dict[str, tuple[str, str]] = {}
    for index, condition in enumerate(conditions):
        prefix = f"method.conditions[{index}]"
        if not isinstance(condition, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _require_text(condition, "label", prefix, errors)
        _require_text(condition, "setup", prefix, errors)
        for field in sorted(DERIVED_CONDITION_FIELDS):
            if field in condition:
                errors.append(f"{prefix}.{field} is derived and must not be authored")
        if state == "protocol":
            if "runs" in condition:
                errors.append(f"protocol {prefix}.runs must be omitted")
            if "finding" in condition:
                errors.append(f"protocol {prefix}.finding must be omitted")
            continue
        _require_text(condition, "finding", prefix, errors)
        condition_id = str(condition.get("id") or "")
        if condition_id == "no-skill":
            for field in ("instruction_artifact_url", "instruction_sha256"):
                if field in condition:
                    errors.append(f"{prefix}.{field} must be omitted for no-skill")
        else:
            artifact_url = str(condition.get("instruction_artifact_url") or "").strip()
            if not is_safe_artifact_url(artifact_url):
                errors.append(
                    f"{prefix}.instruction_artifact_url must be {ARTIFACT_URL_REQUIREMENT}"
                )
            digest = str(condition.get("instruction_sha256") or "")
            if not SHA256_RE.match(digest):
                errors.append(f"{prefix}.instruction_sha256 must be a lowercase SHA-256 digest")
            if artifact_url and digest:
                instruction_evidence[condition_id] = (artifact_url, digest)
        runs = condition.get("runs")
        if not isinstance(runs, list):
            errors.append(f"{prefix}.runs must be an array")
            continue
        if runs_per_condition is None or len(runs) != runs_per_condition:
            errors.append(f"{prefix}.runs must match method.runs_per_condition")
        for run_index, run in enumerate(runs):
            _validate_run(run, f"{prefix}.runs[{run_index}]", seen_run_ids, errors)
    if state == "published":
        minimal = instruction_evidence.get("minimal-instructions")
        full = instruction_evidence.get("full-skill")
        if minimal and full:
            if minimal[0] == full[0]:
                errors.append("published conditions must use distinct instruction artifact URLs")
            if minimal[1] == full[1]:
                errors.append("published conditions must use distinct instruction digests")
            if skill_sha256 and full[1] != skill_sha256:
                errors.append("full-skill instruction digest must match method.skill.sha256")


def validate_record(data: Any) -> list[str]:
    """Return validation errors for one protocol or published result record."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["record must be a JSON object"]
    errors.extend(f"{path} must be finite" for path in _non_finite_paths(data))
    if data.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if data.get("kind") != "agent-skill-lab":
        errors.append("kind must equal agent-skill-lab")
    lab_id = str(data.get("id") or "")
    if not LAB_ID_RE.match(lab_id):
        errors.append("id must start with lab- and be URL-safe")
    slug = str(data.get("slug") or "")
    if not SLUG_RE.match(slug):
        errors.append("slug must be URL-safe")
    elif slug in RESERVED_SLUGS:
        errors.append(f"slug {slug!r} is reserved by the Lab store or API")
    if data.get("pilot_size") != 3:
        errors.append("pilot_size must equal 3")
    edition = data.get("pilot_edition")
    if not isinstance(edition, int) or isinstance(edition, bool) or edition not in range(0, 4):
        errors.append("pilot_edition must be an integer from 0 to 3")
    state = str(data.get("state") or "")
    if state not in {"protocol", "published"}:
        errors.append("state must be protocol or published")
    elif state == "protocol" and edition != 0:
        errors.append("protocol state is valid only for pilot_edition 0")
    elif state == "published" and edition not in {1, 2, 3}:
        errors.append("published state is valid only for pilot editions 1 to 3")
    published_date = _date(data.get("date"))
    if published_date is None:
        errors.append("date must be a real YYYY-MM-DD date")
    featured_until = _date(data.get("featured_until"))
    if featured_until is None:
        errors.append("featured_until must be a real YYYY-MM-DD date")
    elif published_date is not None:
        days = (featured_until - published_date).days
        if days < 0 or days > 21:
            errors.append("featured_until must be from 0 to 21 days after date")
    if not _iso_timestamp(data.get("generated_at")):
        errors.append("generated_at must be an ISO timestamp with a timezone")
    for field in ("title", "question", "summary"):
        _require_text(data, field, "record", errors)
    if not _text_list(data.get("limitations")):
        errors.append("record.limitations must be a non-empty string array")
    for field in sorted(DERIVED_TOP_LEVEL_FIELDS):
        if field in data:
            errors.append(f"record.{field} is derived and must not be authored")

    method = data.get("method")
    if not isinstance(method, dict):
        errors.append("method must be an object")
        return errors
    _validate_task(method.get("task"), errors)
    _validate_environment(method.get("environment"), errors)
    skill_sha256 = _validate_skill(method.get("skill"), state, errors)
    runs_value = method.get("runs_per_condition")
    runs_per_condition = (
        runs_value
        if isinstance(runs_value, int) and not isinstance(runs_value, bool) and runs_value >= 3
        else None
    )
    if runs_per_condition is None:
        errors.append("method.runs_per_condition must be an integer of at least 3")
    if not _text_list(method.get("held_constant")):
        errors.append("method.held_constant must be a non-empty string array")
    _validate_measures(method.get("measures"), errors)
    _validate_conditions(
        method.get("conditions"), state, runs_per_condition, skill_sha256, errors
    )

    if state == "protocol":
        for field in ("verdict", "recommendation", "tested_at"):
            if field in data:
                errors.append(f"protocol record.{field} must be omitted")
        _require_text(data, "publication_rule", "record", errors)
    elif state == "published":
        for field in ("verdict", "recommendation"):
            _require_text(data, field, "record", errors)
        if not _iso_timestamp(data.get("tested_at")):
            errors.append("record.tested_at must be an ISO timestamp with a timezone")
        if "publication_rule" in data:
            errors.append("published record.publication_rule must be omitted")
    return errors


def _read_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard numeric constant {value}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
        )
    except (OSError, ValueError) as exc:
        raise SkillLabValidationError([f"{path.name}: invalid JSON ({exc})"]) from exc


def _summary(record: dict[str, Any], content_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": record["schema_version"],
        "id": record["id"],
        "slug": record["slug"],
        "pilot_edition": record["pilot_edition"],
        "pilot_size": record["pilot_size"],
        "state": record["state"],
        "date": record["date"],
        "generated_at": record["generated_at"],
        "featured_until": record["featured_until"],
        "title": record["title"],
        "question": record["question"],
        "summary": record["summary"],
        "url": f"/playbook/lab/{record['slug']}",
        "content_sha256": content_sha256,
    }


def _json_text(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise SkillLabValidationError([f"derived JSON is not serializable ({exc})"]) from exc


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _artifact_references(record: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """Return every durable evidence URL and any digest it must match."""
    references: list[tuple[str, str, str | None]] = []
    method = record.get("method")
    if not isinstance(method, dict):
        return references
    skill = method.get("skill")
    if isinstance(skill, dict) and _text(skill.get("source_url")):
        references.append(
            (
                "method.skill.source_url",
                str(skill["source_url"]).strip(),
                str(skill.get("sha256") or "") or None,
            )
        )
    conditions = method.get("conditions")
    if not isinstance(conditions, list):
        return references
    for condition_index, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            continue
        prefix = f"method.conditions[{condition_index}]"
        if _text(condition.get("instruction_artifact_url")):
            references.append(
                (
                    f"{prefix}.instruction_artifact_url",
                    str(condition["instruction_artifact_url"]).strip(),
                    str(condition.get("instruction_sha256") or "") or None,
                )
            )
        runs = condition.get("runs")
        if not isinstance(runs, list):
            continue
        for run_index, run in enumerate(runs):
            if isinstance(run, dict) and _text(run.get("artifact_url")):
                references.append(
                    (
                        f"{prefix}.runs[{run_index}].artifact_url",
                        str(run["artifact_url"]).strip(),
                        None,
                    )
                )
    return references


def _validate_same_origin_artifacts(
    record: dict[str, Any],
    source_name: str,
    artifact_root: Path,
    errors: list[str],
) -> None:
    """Prove root-relative evidence will be staged and matches pinned digests."""
    artifact_root = Path(artifact_root).resolve()
    allowed_root = (artifact_root / LAB_ARTIFACT_PREFIX.strip("/")).resolve()
    for field, url, expected_digest in _artifact_references(record):
        if not url.startswith("/") or not is_safe_artifact_url(url):
            continue
        decoded_path = _decoded_url_path(urlsplit(url).path)
        if decoded_path is None:
            errors.append(f"{source_name}: {field}: same-origin artifact path is unsafe")
            continue
        artifact_path = (artifact_root / decoded_path.lstrip("/")).resolve()
        try:
            artifact_path.relative_to(allowed_root)
        except ValueError:
            errors.append(
                f"{source_name}: {field}: same-origin artifact escapes {LAB_ARTIFACT_PREFIX}"
            )
            continue
        if not artifact_path.is_file():
            errors.append(f"{source_name}: {field}: missing same-origin artifact {url}")
            continue
        if expected_digest:
            actual_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if actual_digest != expected_digest:
                errors.append(
                    f"{source_name}: {field}: same-origin artifact SHA-256 does not match"
                )


def referenced_same_origin_artifacts(
    directory: Path = DEFAULT_LAB_DIR,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
) -> list[Path]:
    """Return only validated, referenced same-origin evidence files."""
    directory = Path(directory)
    artifact_root = Path(artifact_root).resolve()
    selected: set[Path] = set()
    errors: list[str] = []
    for source_path in sorted(
        path
        for path in directory.glob("*.json")
        if path.name not in {"index.json", "latest.json"}
    ):
        try:
            record = _read_json(source_path)
        except SkillLabValidationError as exc:
            errors.extend(exc.errors)
            continue
        record_errors = validate_record(record)
        errors.extend(f"{source_path.name}: {error}" for error in record_errors)
        if not isinstance(record, dict) or record_errors:
            continue
        _validate_same_origin_artifacts(record, source_path.name, artifact_root, errors)
        for _field, url, _digest in _artifact_references(record):
            if not url.startswith("/"):
                continue
            decoded_path = _decoded_url_path(urlsplit(url).path)
            if decoded_path is not None:
                selected.add((artifact_root / decoded_path.lstrip("/")).resolve())
    if errors:
        raise SkillLabValidationError(errors)
    return sorted(selected, key=str)


def build_store(
    directory: Path = DEFAULT_LAB_DIR,
    *,
    check: bool = False,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
) -> list[dict[str, Any]]:
    """Validate source records and optionally replace both derived artifacts."""
    directory = Path(directory)
    paths = sorted(
        path
        for path in directory.glob("*.json")
        if path.name not in {"index.json", "latest.json"}
    )
    records: list[dict[str, Any]] = []
    source_digests: dict[str, str] = {}
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_editions: dict[int, str] = {}
    for path in paths:
        try:
            record = _read_json(path)
        except SkillLabValidationError as exc:
            errors.extend(exc.errors)
            continue
        record_errors = validate_record(record)
        errors.extend(f"{path.name}: {error}" for error in record_errors)
        if not isinstance(record, dict):
            continue
        if not record_errors:
            _validate_same_origin_artifacts(record, path.name, artifact_root, errors)
        slug = str(record.get("slug") or "")
        source_digests[slug] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stem != slug:
            errors.append(f"{path.name}: filename must match slug {slug!r}")
        lab_id = str(record.get("id") or "")
        if lab_id in seen_ids:
            errors.append(f"{path.name}: duplicate id {lab_id!r} also used by {seen_ids[lab_id]}")
        elif lab_id:
            seen_ids[lab_id] = path.name
        edition = record.get("pilot_edition")
        if (
            isinstance(edition, int)
            and not isinstance(edition, bool)
            and edition in range(0, 4)
        ):
            if edition in seen_editions:
                errors.append(
                    f"{path.name}: duplicate pilot_edition {edition} also used by {seen_editions[edition]}"
                )
            else:
                seen_editions[edition] = path.name
        records.append(record)
    if len(records) > 4:
        errors.append("store contains more than edition zero plus three pilot results")
    editions = set(seen_editions)
    if editions and editions != set(range(max(editions) + 1)):
        errors.append("store pilot editions must form a contiguous protocol-first sequence")
    if errors:
        raise SkillLabValidationError(errors)

    records.sort(key=lambda item: (item["pilot_edition"], item["date"]), reverse=True)
    entries = [_summary(record, source_digests[record["slug"]]) for record in records]
    if check:
        check_errors: list[str] = []
        try:
            current_index = _read_json(directory / "index.json")
        except SkillLabValidationError:
            current_index = None
        if current_index != entries:
            check_errors.append("index.json is missing or stale; rebuild the Skill Lab store")
        latest_path = directory / "latest.json"
        if records:
            try:
                current_latest = _read_json(latest_path)
            except SkillLabValidationError:
                current_latest = None
            if current_latest != records[0]:
                check_errors.append("latest.json is missing or stale; rebuild the Skill Lab store")
        elif latest_path.exists():
            check_errors.append("latest.json is stale for an empty Skill Lab store")
        if check_errors:
            raise SkillLabValidationError(check_errors)
    else:
        index_text = _json_text(entries)
        latest_text = _json_text(records[0]) if records else None
        _write_text_atomic(directory / "index.json", index_text)
        if records:
            _write_text_atomic(directory / "latest.json", latest_text or "")
        else:
            (directory / "latest.json").unlink(missing_ok=True)
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without writing derived files")
    parser.add_argument("--directory", type=Path, default=DEFAULT_LAB_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        entries = build_store(args.directory, check=args.check)
    except SkillLabValidationError as exc:
        for error in exc.errors:
            print(f"[invalid] {error}", file=sys.stderr)
        print(f"skill_lab_validation_failed={len(exc.errors)}", file=sys.stderr)
        return 1
    action = "validated" if args.check else "indexed"
    print(f"skill_lab_{action}=true records={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
