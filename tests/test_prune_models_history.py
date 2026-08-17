import sys, tempfile, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.path.insert(0, str(Path.cwd() / "pipeline"))
import prune_runtime_data as pr

def test_prune_dated_dir_deletes_only_old_snapshots():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        today = datetime.now(timezone.utc).date()
        old = (today - timedelta(days=120)).isoformat()
        recent = (today - timedelta(days=5)).isoformat()
        for name in (f"{old}.json", f"{recent}.json", "latest.json", "notes.txt"):
            (d / name).write_text("{}")
        out = pr.prune_dated_dir(d, max_age_days=90)
        assert out["files_deleted"] == 1, out
        assert not (d / f"{old}.json").exists()
        assert (d / f"{recent}.json").exists()
        # non-dated files are never touched
        assert (d / "latest.json").exists() and (d / "notes.txt").exists()

def test_prune_dated_dir_disabled_and_missing_dir_are_noops():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "2000-01-01.json").write_text("{}")
        assert pr.prune_dated_dir(d, max_age_days=0)["files_deleted"] == 0
        assert (d / "2000-01-01.json").exists()
    assert pr.prune_dated_dir(Path("/nonexistent-dir-xyz"), max_age_days=30)["files_deleted"] == 0

def test_prune_dated_dir_dry_run_reports_without_deleting():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        old = (datetime.now(timezone.utc).date() - timedelta(days=200)).isoformat()
        (d / f"{old}.json").write_text("{}")
        out = pr.prune_dated_dir(d, max_age_days=90, dry_run=True)
        assert out["files_deleted"] == 1
        assert (d / f"{old}.json").exists()
