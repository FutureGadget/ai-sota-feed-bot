from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def parse_ts(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def load_index(index_file: Path) -> list[dict[str, Any]]:
    if not index_file.exists():
        return []
    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def compact_entries(
    entries: list[dict[str, Any]],
    retain_days: int,
    weekly_archive_after_days: int,
    max_age_days: int | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    """
    Retention policy:
    - Newer than retain_days: keep all (high-res)
    - Older than retain_days and newer than weekly_archive_after_days: keep 1 per day
    - Older than weekly_archive_after_days: keep 1 per ISO week

    When ``max_age_days`` is set, any entry older than it is dropped outright —
    a hard cap that overrides the daily/weekly archive tail. Used for tier1,
    whose snapshots are heavy (~1.5 MB each, bundled into the Vercel feed/rss
    functions) and which no endpoint reads beyond ~7 days, so an open-ended
    archive tail is pure deploy-bundle ballast. Entries with an unknown
    timestamp are kept conservatively regardless.
    """
    now = datetime.now(timezone.utc)
    high_res_cutoff = now - timedelta(days=max(0, retain_days))
    weekly_cutoff = now - timedelta(days=max(0, weekly_archive_after_days))
    max_age_cutoff = (
        now - timedelta(days=max(0, max_age_days)) if max_age_days is not None else None
    )

    normalized: list[tuple[datetime | None, str, dict[str, Any]]] = []
    for e in entries:
        run_at = parse_ts(e.get("run_at"))
        path = e.get("path") or e.get("file")
        if not path:
            continue
        normalized.append((run_at, str(path), e))

    normalized.sort(key=lambda x: (x[0] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

    kept: list[dict[str, Any]] = []
    kept_paths: set[str] = set()
    kept_daily_keys: set[str] = set()
    kept_weekly_keys: set[str] = set()

    for run_at, rel_path, e in normalized:
        if run_at is None:
            # Keep unknown timestamps conservatively.
            if rel_path not in kept_paths:
                kept.append(e)
                kept_paths.add(rel_path)
            continue

        if max_age_cutoff is not None and run_at < max_age_cutoff:
            # Hard cap: drop outright, no daily/weekly archive.
            continue

        if run_at >= high_res_cutoff:
            kept.append(e)
            kept_paths.add(rel_path)
            continue

        if run_at >= weekly_cutoff:
            day_key = run_at.strftime("%Y-%m-%d")
            if day_key in kept_daily_keys:
                continue
            kept_daily_keys.add(day_key)
            kept.append(e)
            kept_paths.add(rel_path)
            continue

        iso = run_at.isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"
        if week_key in kept_weekly_keys:
            continue
        kept_weekly_keys.add(week_key)
        kept.append(e)
        kept_paths.add(rel_path)

    kept.sort(key=lambda x: str(x.get("run_at") or ""), reverse=True)
    return kept, kept_paths


def prune_family(
    base_dir: Path,
    retain_days: int,
    weekly_archive_after_days: int,
    max_age_days: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    runs_dir = base_dir / "runs"
    index_file = base_dir / "runs_index.json"

    entries = load_index(index_file)
    kept_entries, kept_paths = compact_entries(
        entries, retain_days, weekly_archive_after_days, max_age_days=max_age_days
    )

    all_files: set[str] = set()
    if runs_dir.exists():
        for p in runs_dir.rglob("*.json"):
            all_files.add(str(p.relative_to(runs_dir)))

    to_delete = sorted(all_files - kept_paths)

    if not dry_run:
        for rel in to_delete:
            p = runs_dir / rel
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

        if runs_dir.exists():
            for d in sorted([x for x in runs_dir.rglob("*") if x.is_dir()], key=lambda x: len(str(x)), reverse=True):
                try:
                    d.rmdir()
                except Exception:
                    pass

        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(kept_entries, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "base": str(base_dir.relative_to(ROOT)),
        "retain_days": retain_days,
        "weekly_archive_after_days": weekly_archive_after_days,
        "max_age_days": max_age_days,
        "index_before": len(entries),
        "index_after": len(kept_entries),
        "files_before": len(all_files),
        "files_deleted": len(to_delete),
    }


def prune_dated_dir(
    directory: Path,
    max_age_days: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delete `<YYYY-MM-DD>.json` snapshots older than `max_age_days`.

    For flat dated directories that carry no runs index, so `prune_family`
    does not apply - today that is data/models/history, written once per
    Model Release Radar refresh. Nothing reads a historical snapshot at
    request time (api/models.js pins includeFiles to latest.json); they exist
    for score-delta work and audit, so an unbounded pile is pure growth in
    both git and the deployment. 0/negative disables the cap.
    """
    out: dict[str, Any] = {"files_deleted": 0, "kept": 0, "max_age_days": max_age_days}
    if max_age_days <= 0 or not directory.is_dir():
        return out
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).date()
    for path in sorted(directory.glob("*.json")):
        try:
            stamp = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue  # not a dated snapshot - leave it alone
        if stamp < cutoff:
            if not dry_run:
                path.unlink()
            out["files_deleted"] += 1
        else:
            out["kept"] += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed-days", type=int, default=45)
    ap.add_argument("--tier1-days", type=int, default=3)
    ap.add_argument("--weekly-archive-after-days", type=int, default=365)
    # Hard delete cutoff for tier1 runs. Both consumers (feed.js + rss.js) read
    # tier1 only for a 24h "fresh-blend" overlay; RSS's 7-day window is built from
    # processed/runs, not tier1. So nothing reads a tier1 snapshot older than ~24h.
    # 3 days = the read window + a generous buffer; keeps the bundled tier1 dir at
    # ~20-30 MB instead of 100+ MB. 0/negative disables the cap.
    ap.add_argument("--tier1-max-age-days", type=int, default=3)
    # Dated Model Release Radar snapshots (data/models/history). ~290 KB each,
    # one per refresh; 90 days is plenty for score-delta work.
    ap.add_argument("--models-history-days", type=int, default=90)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    processed = prune_family(
        ROOT / "data" / "processed",
        retain_days=args.processed_days,
        weekly_archive_after_days=args.weekly_archive_after_days,
        dry_run=args.dry_run,
    )
    tier1_max_age = args.tier1_max_age_days if args.tier1_max_age_days > 0 else None
    tier1 = prune_family(
        ROOT / "data" / "tier1",
        retain_days=args.tier1_days,
        weekly_archive_after_days=args.weekly_archive_after_days,
        max_age_days=tier1_max_age,
        dry_run=args.dry_run,
    )

    models_history = prune_dated_dir(
        ROOT / "data" / "models" / "history",
        max_age_days=args.models_history_days,
        dry_run=args.dry_run,
    )

    print(
        "runtime_prune "
        f"processed(index {processed['index_before']}->{processed['index_after']}, deleted={processed['files_deleted']}, keep={processed['retain_days']}d) "
        f"tier1(index {tier1['index_before']}->{tier1['index_after']}, deleted={tier1['files_deleted']}, keep={tier1['retain_days']}d, max_age={tier1['max_age_days']}d) "
        f"models_history(deleted={models_history['files_deleted']}, kept={models_history['kept']}, max_age={models_history['max_age_days']}d) "
        f"weekly_after={args.weekly_archive_after_days}d "
        f"dry_run={str(args.dry_run).lower()}"
    )


if __name__ == "__main__":
    main()
