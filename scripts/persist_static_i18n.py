#!/usr/bin/env python3
"""Checkpoint and publish paid static translations without translating again.

Publication uses a disposable worktree on fresh main. Ledgers receive the
checkpoint's delta, and a receipt in spend_guard.json makes replay idempotent.
Only the offline renderer runs here; this module never calls a translation API.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
GUARD = "data/i18n/spend_guard.json"
SURFACES = {"daily", "weekly", "story", "storyline", "topic", "foundations", "playbook"}
ARTIFACT_PREFIX = "static-i18n-"
CHECKPOINT_STEP = "Checkpoint paid outputs"


class PersistenceError(RuntimeError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if check and result.returncode:
        raise PersistenceError(result.stderr.strip())
    return result


def _json(text: str | None) -> dict[str, Any]:
    if text is None:
        return {}
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise PersistenceError("invalid JSON in a checkpoint or ledger") from exc
    if not isinstance(value, dict):
        raise PersistenceError("checkpoint and ledger must be JSON objects")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _at_commit(root: Path, commit: str, path: str) -> str | None:
    result = _git(root, "show", f"{commit}:{path}", check=False)
    if result.returncode == 0:
        return result.stdout
    # A missing file is expected; an unavailable base commit is not.
    _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    return None


def _allowed_path(path: str, locale: str) -> bool:
    if path == GUARD or path == f"data/i18n/{locale}/feed/static_budget.json":
        return True
    parts = PurePosixPath(path).parts
    return (
        len(parts) == 5 and list(parts[:3]) == ["data", "i18n", locale]
        and parts[3] in SURFACES and parts[4].endswith(".json")
        and ".." not in parts and "\\" not in path
    )


def validate_bundle(bundle: dict[str, Any], *, complete: bool = True) -> None:
    if bundle.get("version") != 1:
        raise PersistenceError("unsupported static i18n checkpoint version")
    if complete and bundle.get("checkpoint_complete") is not True:
        raise PersistenceError("incomplete paid checkpoint; refusing new charges")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", str(bundle.get("run_id", ""))):
        raise PersistenceError("invalid checkpoint run_id")
    if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", str(bundle.get("locale", ""))):
        raise PersistenceError("invalid checkpoint locale")
    if not re.fullmatch(r"[0-9a-f]{40}", str(bundle.get("base_commit", ""))):
        raise PersistenceError("invalid checkpoint base commit")
    if not isinstance(bundle.get("files"), dict):
        raise PersistenceError("checkpoint files must be an object")
    for path, change in bundle["files"].items():
        if not _allowed_path(path, bundle["locale"]):
            raise PersistenceError(f"unexpected checkpoint path: {path}")
        if not isinstance(change, dict) or set(change) != {"before", "after"}:
            raise PersistenceError(f"invalid checkpoint change: {path}")
        if not isinstance(change["after"], str):
            raise PersistenceError(f"missing output in checkpoint: {path}")
        if change["before"] is not None and not isinstance(change["before"], str):
            raise PersistenceError(f"invalid base content: {path}")
        try:
            json.loads(change["after"])
        except ValueError as exc:
            raise PersistenceError(f"invalid JSON output in checkpoint: {path}") from exc
    for key in ("lost_outputs", "lost_payloads"):
        losses = bundle.get(key, {})
        if not isinstance(losses, dict):
            raise PersistenceError(f"{key} must be an object")
        for path, fingerprint in losses.items():
            if not _allowed_path(path, bundle["locale"]) or path == GUARD or "/feed/" in path:
                raise PersistenceError(f"unexpected lost output path: {path}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(fingerprint)):
                raise PersistenceError(f"invalid lost output fingerprint: {path}")


def prepare(root: Path, path: Path, run_id: str, locale: str) -> None:
    if _git(root, "status", "--porcelain").stdout:
        raise PersistenceError("refusing to refresh a dirty checkout before translation")
    _git(root, "fetch", "origin", "main")
    # A workflow's triggering SHA can be stale even with a shared concurrency
    # group. This checkout is still clean and has no paid outputs to discard.
    _git(root, "checkout", "--detach", "origin/main")
    bundle = {
        "version": 1, "run_id": run_id, "locale": locale,
        "base_commit": _git(root, "rev-parse", "HEAD").stdout.strip(),
        "started_at": datetime.now(timezone.utc).isoformat(), "files": {},
        "checkpoint_complete": False,
    }
    validate_bundle(bundle, complete=False)
    _write(path, bundle)


def checkpoint(root: Path, path: Path) -> dict[str, Any]:
    bundle = _json(path.read_text(encoding="utf-8"))
    validate_bundle(bundle, complete=False)
    changed = _git(root, "diff", "--name-only", "-z", bundle["base_commit"], "--", "data/i18n").stdout
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", "data/i18n").stdout
    try:
        for name in sorted(set((changed + untracked).split("\0")) - {""}):
            if not _allowed_path(name, bundle["locale"]):
                raise PersistenceError(f"unexpected static translation change: {name}")
            output = root / name
            bundle["files"][name] = {
                "before": _at_commit(root, bundle["base_commit"], name),
                "after": output.read_text(encoding="utf-8") if output.is_file() else None,
            }
        bundle["checkpoint_complete"] = True
    finally:
        # Save raw outputs even if validation fails, for human recovery.
        # Publication never replaces a ledger with malformed/incomplete content.
        _write(path, bundle)
    print(f"i18n_checkpoint_saved=true files={len(bundle['files'])} run={bundle['run_id']}")
    return bundle


def _count(state: dict[str, Any], key: str) -> int:
    value = state.get(key, 0)
    if type(value) is not int or value < 0:
        raise PersistenceError(f"invalid ledger counter: {key}")
    return value


def _period(state: dict[str, Any], key: str) -> str | None:
    value = state.get(key)
    if value is None:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d" if key == "day" else "%Y-%m")
    except (ValueError, TypeError) as exc:
        raise PersistenceError(f"invalid ledger period: {key}") from exc
    pattern = r"\d{4}-\d{2}-\d{2}" if key == "day" else r"\d{4}-\d{2}"
    if not re.fullmatch(pattern, value):
        raise PersistenceError(f"invalid ledger period: {key}")
    return value


def _merge_counter(
    before: dict[str, Any], after: dict[str, Any], current: dict[str, Any],
    period: str, counter: str,
) -> tuple[int, str | None]:
    new_period = _period(after, period)
    if new_period is None:
        if after or before:
            raise PersistenceError(f"missing ledger period: {period}")
        return 0, current.get(period)
    if counter not in after:
        raise PersistenceError(f"missing ledger counter: {counter}")
    base_period = _period(before, period)
    if base_period == new_period and counter not in before:
        raise PersistenceError(f"missing base ledger counter: {counter}")
    delta = _count(after, counter) - (_count(before, counter) if base_period == new_period else 0)
    if delta < 0:
        raise PersistenceError(f"negative usage delta: {counter}")
    current_period = _period(current, period)
    if current_period is None or current_period < new_period:
        current[period], current[counter] = new_period, _count(after, counter)
    elif current_period == new_period:
        if counter not in current:
            raise PersistenceError(f"missing current ledger counter: {counter}")
        current[counter] = _count(current, counter) + delta
    # A recovered old day/month belongs in its receipt/history, not today's
    # counter. Never move the active accounting period backwards.
    return delta, new_period


def _new_history(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(before.get("history", []), list) or not isinstance(after.get("history", []), list):
        raise PersistenceError("invalid ledger history")
    prior = Counter(json.dumps(entry, sort_keys=True) for entry in before.get("history", []))
    added = []
    for entry in after.get("history", []):
        key = json.dumps(entry, sort_keys=True)
        if prior[key]:
            prior[key] -= 1
        else:
            added.append(entry)
    return added


def bundle_digest(bundle: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(bundle, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def apply_bundle(root: Path, bundle: dict[str, Any]) -> bool:
    """Apply a saved delta to a clean, current checkout; return False on replay."""
    validate_bundle(bundle)
    guard_path = root / GUARD
    guard = _json(guard_path.read_text(encoding="utf-8") if guard_path.exists() else None)
    digest = bundle_digest(bundle)
    receipts = guard.setdefault("static_runs", {})
    if not isinstance(receipts, dict):
        raise PersistenceError("invalid static run receipts in spend guard")
    prior = receipts.get(bundle["run_id"])
    if prior is not None:
        if not isinstance(prior, dict) or prior.get("sha256") != digest:
            raise PersistenceError("run already accounted with a different checkpoint")
        return False

    writes: dict[str, str] = {}
    usage = {}
    for path, change in bundle["files"].items():
        target = root / path
        raw = target.read_text(encoding="utf-8") if target.exists() else None
        if path == GUARD:
            before, after = _json(change["before"]), _json(change["after"])
            for period, count in (("month", "month_chars"), ("day", "day_chars")):
                if period == "day" and after.get("tripped_at") != before.get("tripped_at") and after.get("tripped_at"):
                    # trip_day's floor is a stop signal, not additional billed
                    # usage. Preserve the floor without adding it twice.
                    day = after["day"]
                    if guard.get("day", "") <= day:
                        guard["day_chars"] = max(_count(guard, "day_chars") if guard.get("day") == day else 0,
                                                 _count(after, "day_chars"))
                        guard["day"] = day
                    guard["tripped_at"] = max(str(guard.get("tripped_at", "")), after["tripped_at"])
                    usage["day"] = {"period": day, "tripped": True}
                else:
                    delta, stamp = _merge_counter(before, after, guard, period, count)
                    usage[period] = {"period": stamp, "chars": delta}
            guard["updated_at"] = max(str(guard.get("updated_at", "")), str(after.get("updated_at", "")))
        elif path.endswith("/feed/static_budget.json"):
            before, after = _json(change["before"]), _json(change["after"])
            ledger = _json(raw)
            added = _new_history(before, after)
            if not isinstance(ledger.get("history", []), list):
                raise PersistenceError("invalid current ledger history")
            current_entries = {json.dumps(entry, sort_keys=True) for entry in ledger.get("history", [])}
            if any(json.dumps(entry, sort_keys=True) in current_entries for entry in added):
                raise PersistenceError("static usage already present without a receipt; accounting is uncertain")
            delta, month = _merge_counter(before, after, ledger, "month", "chars_used")
            history = ledger.setdefault("history", [])
            history.extend(added)
            # Preserve configured caps and seeds from the latest main.
            ledger.setdefault("monthly_cap", after.get("monthly_cap", 100_000))
            ledger["updated_at"] = max(str(ledger.get("updated_at", "")), str(after.get("updated_at", "")))
            usage["static"] = {"period": month, "chars": delta}
            writes[path] = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
        else:
            if raw not in (change["before"], change["after"]):
                raise PersistenceError(f"concurrent source artifact change: {path}; checkpoint preserved")
            writes[path] = change["after"]

    receipts[bundle["run_id"]] = {
        "sha256": digest, "locale": bundle["locale"],
        "at": bundle["started_at"], "usage": usage,
        "lost_outputs": bundle.get("lost_outputs", {}),
        "lost_payloads": bundle.get("lost_payloads", {}),
    }
    writes[GUARD] = json.dumps(guard, ensure_ascii=False, indent=2) + "\n"
    # Validate every change before writing any of them.
    for path, content in writes.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(target)
    return True


def lost_output_run(
    root: Path, path: str, source_hash: str, payload_hash: str | None = None,
) -> str | None:
    guard_path = Path(os.environ.get("GOOGLE_TRANSLATE_GUARD_PATH") or root / GUARD)
    guard = _json(guard_path.read_text(encoding="utf-8") if guard_path.exists() else None)
    receipts = guard.get("static_runs", {})
    if not isinstance(receipts, dict):
        raise PersistenceError("invalid static run receipts")
    for run, receipt in receipts.items():
        if not isinstance(receipt, dict) or any(
            not isinstance(receipt.get(key, {}), dict) for key in ("lost_outputs", "lost_payloads")
        ):
            raise PersistenceError("invalid lost output receipt")
        if receipt.get("lost_outputs", {}).get(path) == source_hash:
            return run
        if payload_hash and receipt.get("lost_payloads", {}).get(path) == payload_hash:
            return run
    return None


def _render(root: Path) -> None:
    subprocess.run([sys.executable, str(root / "pipeline/render_static_pages.py")], cwd=root, check=True)


def publish(
    root: Path, bundle: dict[str, Any], *, render: Callable[[Path], None] = _render,
    attempts: int = 4,
) -> None:
    """Retry only offline materialization/push, using a fresh main each time."""
    validate_bundle(bundle)
    for attempt in range(1, attempts + 1):
        _git(root, "fetch", "origin", "main")
        base = _git(root, "rev-parse", "origin/main").stdout.strip()
        with tempfile.TemporaryDirectory(prefix="static-i18n-publish-") as tmp:
            worktree = Path(tmp) / "tree"
            _git(root, "worktree", "add", "--detach", str(worktree), base)
            try:
                if not apply_bundle(worktree, bundle):
                    print(f"i18n_publish_skipped=true reason=already_accounted run={bundle['run_id']}")
                    return
                render(worktree)
                _git(worktree, "add", "data/i18n", "web")
                _git(worktree, "diff", "--cached", "--check")
                _git(worktree, "commit", "-m", f"i18n: persist static run {bundle['run_id']}")
                pushed = _git(worktree, "push", "origin", "HEAD:main", check=False)
                if pushed.returncode == 0:
                    print(f"i18n_publish_done=true run={bundle['run_id']} attempt={attempt}")
                    return
                _git(root, "fetch", "origin", "main")
                if _git(root, "rev-parse", "origin/main").stdout.strip() == base:
                    raise PersistenceError(f"push failed; paid checkpoint preserved: {pushed.stderr.strip()}")
                print(f"i18n_publish_retry=true reason=main_advanced attempt={attempt}")
            finally:
                _git(root, "worktree", "remove", "--force", str(worktree))
    raise PersistenceError("main kept advancing; paid checkpoint preserved for recovery")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _github(repository: str, suffix: str, *, binary: bool = False) -> Any:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise PersistenceError("GitHub repository and read token are required for recovery")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{suffix}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    # Artifact archives redirect to signed storage URLs. Never forward the
    # GitHub credential to the storage host.
    try:
        response = urllib.request.build_opener(_NoRedirect()).open(request, timeout=30)
    except urllib.error.HTTPError as exc:
        if not binary or exc.code != 302:
            raise PersistenceError(f"GitHub recovery read failed: HTTP {exc.code}") from exc
        location = exc.headers.get("Location", "")
        exc.close()
        if urllib.parse.urlsplit(location).scheme != "https":
            raise PersistenceError("invalid artifact download redirect") from exc
        response = urllib.request.urlopen(location, timeout=30)
    with response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000:
        raise PersistenceError("recovery response exceeds the size limit")
    return data if binary else json.loads(data)


def recover_pending(root: Path, repository: str, current_run: str) -> None:
    """Recover prior paid attempts before permitting any new translation work.

    Walk backwards to the latest acknowledged run. A missing/expired checkpoint
    after entering the paid step blocks the next run, rather than paying again.
    """
    _git(root, "fetch", "origin", "main")
    guard = _json(_at_commit(root, "origin/main", GUARD))
    receipts = guard.get("static_runs", {})
    pending = []
    page = 1
    while True:
        runs = _github(repository, f"actions/workflows/i18n-translate.yml/runs?branch=main&per_page=100&page={page}")["workflow_runs"]
        if not runs:
            for saved_bundle in reversed(pending):
                publish(root, saved_bundle)
            return
        for run in runs:
            if str(run["id"]) == current_run:
                # A rerun must recover its earlier attempts as well.
                latest_attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")) - 1
            else:
                latest_attempt = int(run.get("run_attempt", 1))
            artifacts = None
            for attempt in range(latest_attempt, 0, -1):
                run_id = f"actions-{run['id']}-{attempt}"
                if run_id in receipts:
                    for saved_bundle in reversed(pending):
                        publish(root, saved_bundle)
                    return
                if artifacts is None:
                    artifacts = _github(repository, f"actions/runs/{run['id']}/artifacts?per_page=100")["artifacts"]
                name = f"{ARTIFACT_PREFIX}{run['id']}-{attempt}"
                saved = next((artifact for artifact in artifacts if artifact["name"] == name), None)
                if saved:
                    if saved.get("expired"):
                        raise PersistenceError(f"unpublished paid checkpoint expired: {name}")
                    archive = _github(repository, f"actions/artifacts/{saved['id']}/zip", binary=True)
                    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                        entry = zipped.getinfo("checkpoint.json")
                        if entry.file_size > 20_000_000:
                            raise PersistenceError("recovery checkpoint exceeds the size limit")
                        bundle = _json(zipped.read(entry).decode("utf-8"))
                    if bundle.get("run_id") != run_id:
                        raise PersistenceError(f"checkpoint identity mismatch: {name}")
                    validate_bundle(bundle)
                    pending.append(bundle)
                    # Validate the backlog first and replay oldest first.
                    continue
                jobs = _github(repository, f"actions/runs/{run['id']}/attempts/{attempt}/jobs?per_page=100")["jobs"]
                steps = [step for job in jobs for step in job.get("steps", [])]
                paid = next((step for step in steps if step["name"] == "Translate static pages"), None)
                if any(step["name"] == CHECKPOINT_STEP for step in steps) and paid and paid.get("conclusion") != "skipped":
                    raise PersistenceError(f"paid attempt has no recovery checkpoint: {run_id}; refusing new charges")
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "checkpoint", "publish", "apply", "recover"])
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--locale", default="ko")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    args = parser.parse_args()
    try:
        if args.command == "recover":
            recover_pending(ROOT, args.repository, os.environ.get("GITHUB_RUN_ID", ""))
        elif args.command == "prepare":
            if args.checkpoint is None or args.run_id is None:
                parser.error("prepare needs --checkpoint and --run-id")
            prepare(ROOT, args.checkpoint, args.run_id, args.locale)
        elif args.checkpoint is None:
            parser.error("command needs --checkpoint")
        elif args.command == "checkpoint":
            checkpoint(ROOT, args.checkpoint)
        else:
            bundle = _json(args.checkpoint.read_text(encoding="utf-8"))
            if args.command == "publish":
                publish(ROOT, bundle)
            else:
                applied = apply_bundle(ROOT, bundle)
                print(f"i18n_checkpoint_applied={str(applied).lower()} run={bundle['run_id']}")
    except (PersistenceError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"i18n_persistence_failed=true reason={exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
