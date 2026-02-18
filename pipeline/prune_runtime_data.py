from __future__ import annotations

import argparse
import json
from collections import defaultdict
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


def compact_entries(entries: list[dict[str, Any]], retain_days: int) -> tuple[list[dict[str, Any]], set[str]]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(0, retain_days))

    normalized = []
    for e in entries:
        run_at = parse_ts(e.get("run_at"))
        path = e.get("path") or e.get("file")
        if not path:
            continue
        normalized.append((run_at, str(path), e))

    normalized.sort(key=lambda x: (x[0] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

    kept: list[dict[str, Any]] = []
    kept_paths: set[str] = set()
    older_kept_by_day: set[str] = set()

    for run_at, rel_path, e in normalized:
        if run_at is None:
            # keep unknown timestamps conservatively
            if rel_path not in kept_paths:
                kept.append(e)
                kept_paths.add(rel_path)
            continue

        if run_at >= cutoff:
            kept.append(e)
            kept_paths.add(rel_path)
            continue

        day = run_at.strftime("%Y-%m-%d")
        if day not in older_kept_by_day:
            kept.append(e)
            kept_paths.add(rel_path)
            older_kept_by_day.add(day)

    kept.sort(key=lambda x: str(x.get("run_at") or ""), reverse=True)
    return kept, kept_paths


def prune_family(base_dir: Path, retain_days: int, dry_run: bool = False) -> dict[str, Any]:
    runs_dir = base_dir / "runs"
    index_file = base_dir / "runs_index.json"

    entries = load_index(index_file)
    kept_entries, kept_paths = compact_entries(entries, retain_days)

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
        "index_before": len(entries),
        "index_after": len(kept_entries),
        "files_before": len(all_files),
        "files_deleted": len(to_delete),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed-days", type=int, default=7)
    ap.add_argument("--tier1-days", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    processed = prune_family(ROOT / "data" / "processed", retain_days=args.processed_days, dry_run=args.dry_run)
    tier1 = prune_family(ROOT / "data" / "tier1", retain_days=args.tier1_days, dry_run=args.dry_run)

    print(
        "runtime_prune "
        f"processed(index {processed['index_before']}->{processed['index_after']}, deleted={processed['files_deleted']}) "
        f"tier1(index {tier1['index_before']}->{tier1['index_after']}, deleted={tier1['files_deleted']}) "
        f"dry_run={str(args.dry_run).lower()}"
    )


if __name__ == "__main__":
    main()
