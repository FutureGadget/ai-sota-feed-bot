"""Offline publication tests with a real local Git remote; no translation API."""

from __future__ import annotations

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import persist_static_i18n as persistence  # noqa: E402

AT = "2026-10-09T03:08:29+00:00"
ARTIFACT = "data/i18n/ko/storyline/claude-5-5.json"
STATIC = "data/i18n/ko/feed/static_budget.json"
BASE = {"month": "2026-10", "month_chars": 49829, "day": "2026-10-08", "day_chars": 8370}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(encoded(value), encoding="utf-8")


def guard_plus(chars):
    return {**BASE, "month_chars": BASE["month_chars"] + chars,
            "day_chars": BASE["day_chars"] + chars, "updated_at": AT}


def bundle(chars=1509):
    return {
        "version": 1, "run_id": "actions-123-1", "locale": "ko", "started_at": AT,
        "base_commit": "0" * 40,
        "checkpoint_complete": True,
        "files": {
            persistence.GUARD: {"before": encoded(BASE), "after": encoded(guard_plus(chars))},
            STATIC: {"before": None, "after": encoded({
                "month": "2026-10", "chars_used": chars, "monthly_cap": 100000,
                "history": [{"at": AT, "chars": chars, "run": "static-run"}], "updated_at": AT,
            })},
            ARTIFACT: {"before": None, "after": encoded({"source_hash": "a" * 64, "title": "클로드"})},
        },
    }


class LedgerMergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def read(self, path):
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def test_delta_preserves_feed_and_static_usage_and_replays_once(self):
        write(self.root, persistence.GUARD, guard_plus(1459))
        write(self.root, STATIC, {
            "month": "2026-10", "chars_used": 23, "monthly_cap": 90000,
            "seeded_from": "existing seed", "history": [{"at": AT, "chars": 23, "run": "other"}],
        })
        saved = bundle()
        self.assertTrue(persistence.apply_bundle(self.root, saved))
        guard = self.read(persistence.GUARD)
        self.assertEqual((guard["day_chars"], guard["month_chars"]), (11338, 52797))
        ledger = self.read(STATIC)
        self.assertEqual(ledger["chars_used"], 1532)
        self.assertEqual(ledger["monthly_cap"], 90000)
        self.assertEqual(ledger["seeded_from"], "existing seed")
        self.assertEqual(len(ledger["history"]), 2)
        self.assertFalse(persistence.apply_bundle(self.root, saved))
        self.assertEqual(self.read(persistence.GUARD), guard)
        changed = copy.deepcopy(saved)
        changed["files"][ARTIFACT]["after"] = encoded({"title": "different"})
        with self.assertRaisesRegex(persistence.PersistenceError, "different checkpoint"):
            persistence.apply_bundle(self.root, changed)

    def test_old_recovery_does_not_roll_new_day_or_month_back(self):
        write(self.root, persistence.GUARD, {
            "month": "2026-11", "month_chars": 50, "day": "2026-11-01", "day_chars": 30,
        })
        write(self.root, STATIC, {"month": "2026-11", "chars_used": 20, "history": []})
        persistence.apply_bundle(self.root, bundle())
        self.assertEqual(self.read(persistence.GUARD)["month_chars"], 50)
        self.assertEqual(self.read(persistence.GUARD)["day_chars"], 30)
        self.assertEqual(self.read(STATIC)["chars_used"], 20)
        self.assertEqual(self.read(STATIC)["history"][0]["chars"], 1509)
        self.assertEqual(self.read(persistence.GUARD)["static_runs"]["actions-123-1"]["usage"]["month"]["chars"], 1509)

    def test_same_month_new_day_charges_only_month(self):
        write(self.root, persistence.GUARD, {
            "month": "2026-10", "month_chars": 51288, "day": "2026-10-09", "day_chars": 90,
        })
        persistence.apply_bundle(self.root, bundle())
        self.assertEqual(self.read(persistence.GUARD)["month_chars"], 52797)
        self.assertEqual(self.read(persistence.GUARD)["day_chars"], 90)

    def test_new_period_applies_its_full_usage_without_old_month_usage(self):
        saved = bundle(60)
        after = {"month": "2026-11", "month_chars": 60, "day": "2026-11-01", "day_chars": 60}
        saved["files"][persistence.GUARD]["after"] = encoded(after)
        write(self.root, persistence.GUARD, BASE)
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(persistence.GUARD)["month_chars"], 60)
        self.assertEqual(self.read(persistence.GUARD)["day_chars"], 60)

    def test_provider_day_trip_is_a_floor_not_a_second_charge(self):
        saved = bundle(5)
        after = {**guard_plus(5), "day_chars": 16000, "tripped_at": AT}
        saved["files"][persistence.GUARD]["after"] = encoded(after)
        write(self.root, persistence.GUARD, guard_plus(1459))
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(persistence.GUARD)["month_chars"], 51293)
        self.assertEqual(self.read(persistence.GUARD)["day_chars"], 16000)

    def test_concurrent_artifact_change_fails_without_mutating_ledgers(self):
        write(self.root, persistence.GUARD, BASE)
        write(self.root, ARTIFACT, {"source_hash": "b" * 64, "title": "concurrent translation"})
        with self.assertRaisesRegex(persistence.PersistenceError, "concurrent source artifact"):
            persistence.apply_bundle(self.root, bundle())
        self.assertEqual(self.read(persistence.GUARD), BASE)
        self.assertFalse((self.root / STATIC).exists())

    def test_corrupt_and_negative_ledgers_fail_closed(self):
        for after in ["{bad", encoded(guard_plus(-1)), encoded({**BASE, "month_chars": "1509"})]:
            saved = bundle()
            saved["files"][persistence.GUARD]["after"] = after
            write(self.root, persistence.GUARD, BASE)
            with self.assertRaises(persistence.PersistenceError):
                persistence.apply_bundle(self.root, saved)
            self.assertEqual(self.read(persistence.GUARD), BASE)

    def test_path_escape_and_feed_changes_are_refused(self):
        for path in ["../secret.json", "data/i18n/ko/../../secret.json", "data/i18n/ko/feed/budget.json"]:
            saved = bundle()
            saved["files"][path] = {"before": None, "after": "{}"}
            with self.assertRaisesRegex(persistence.PersistenceError, "unexpected checkpoint path"):
                persistence.apply_bundle(self.root, saved)

    def test_playbook_array_indexes_are_checkpointable(self):
        saved = bundle()
        saved["files"]["data/i18n/ko/playbook/index.json"] = {"before": None, "after": "[]\n"}
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read("data/i18n/ko/playbook/index.json"), [])

    def test_ambiguous_guard_charges_survive_without_an_output(self):
        saved = bundle(120)
        del saved["files"][ARTIFACT]
        del saved["files"][STATIC]
        write(self.root, persistence.GUARD, guard_plus(1459))
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(persistence.GUARD)["month_chars"], 51408)

    def test_lost_output_receipt_blocks_only_the_billed_source_version(self):
        saved = bundle()
        del saved["files"][ARTIFACT]
        saved["lost_outputs"] = {ARTIFACT: "a" * 64}
        persistence.apply_bundle(self.root, saved)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(persistence.lost_output_run(self.root, ARTIFACT, "a" * 64), "actions-123-1")
            self.assertIsNone(persistence.lost_output_run(self.root, ARTIFACT, "b" * 64))

    def test_lost_payload_receipt_survives_metadata_only_source_changes(self):
        saved = bundle()
        del saved["files"][ARTIFACT]
        saved["lost_outputs"] = {ARTIFACT: "a" * 64}
        saved["lost_payloads"] = {ARTIFACT: "c" * 64}
        persistence.apply_bundle(self.root, saved)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(persistence.lost_output_run(self.root, ARTIFACT, "b" * 64, "c" * 64), "actions-123-1")
            self.assertIsNone(persistence.lost_output_run(self.root, ARTIFACT, "b" * 64, "d" * 64))
        saved["lost_payloads"] = {"../secret.json": "c" * 64}
        with self.assertRaisesRegex(persistence.PersistenceError, "unexpected lost output path"):
            persistence.validate_bundle(saved)

    def test_partial_manual_reconciliation_is_reported_not_charged_twice(self):
        saved = bundle()
        write(self.root, persistence.GUARD, BASE)
        write(self.root, STATIC, json.loads(saved["files"][STATIC]["after"]))
        with self.assertRaisesRegex(persistence.PersistenceError, "accounting is uncertain"):
            persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(persistence.GUARD), BASE)

    def test_incomplete_checkpoint_cannot_publish_or_acknowledge_usage(self):
        saved = bundle()
        saved["checkpoint_complete"] = False
        with self.assertRaisesRegex(persistence.PersistenceError, "incomplete"):
            persistence.apply_bundle(self.root, saved)
        self.assertFalse((self.root / persistence.GUARD).exists())


class GitHubReadTests(unittest.TestCase):
    def test_artifact_redirect_does_not_forward_github_token(self):
        redirect = urllib.error.HTTPError(
            "https://api.github.com/", 302, "Found",
            {"Location": "https://storage.example.invalid/checkpoint.zip"}, io.BytesIO(b""),
        )
        with (
            patch.dict(os.environ, {"GH_TOKEN": "offline-test-token"}, clear=True),
            patch.object(persistence.urllib.request, "build_opener") as opener,
            patch.object(persistence.urllib.request, "urlopen", return_value=io.BytesIO(b"zip")) as download,
        ):
            opener.return_value.open.side_effect = redirect
            self.assertEqual(persistence._github("owner/repo", "actions/artifacts/1/zip", binary=True), b"zip")
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer offline-test-token")
            download.assert_called_once_with("https://storage.example.invalid/checkpoint.zip", timeout=30)

    def test_repository_path_is_validated_before_a_network_read(self):
        with patch.dict(os.environ, {"GH_TOKEN": "offline"}), patch.object(persistence.urllib.request, "build_opener") as opener:
            with self.assertRaises(persistence.PersistenceError):
                persistence._github("../../outside", "actions/runs")
            opener.assert_not_called()


class FeedRecoveryGateTests(unittest.TestCase):
    def test_unrecovered_static_usage_skips_paid_step_and_completes_english_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "skills/ai-feed-digest-local/scripts/run_full.sh"
            script.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / "skills/ai-feed-digest-local/scripts/run_full.sh", script)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            binary_dir = root / "bin"
            binary_dir.mkdir()
            stub = binary_dir / "python"
            stub.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "with open(os.environ['OFFLINE_CALL_LOG'], 'a') as log:\n"
                "    log.write(json.dumps(sys.argv[1:])+'\\n')\n"
                "if sys.argv[1] == 'pipeline/build_tier1.py':\n"
                "    p = Path('data/tier1/latest.json')\n"
                "    p.parent.mkdir(parents=True, exist_ok=True)\n"
                "    p.write_text('{}')\n"
            )
            stub.chmod(0o755)
            activate = root / ".venv/bin/activate"
            activate.parent.mkdir(parents=True)
            activate.write_text(f'export PATH="{binary_dir}:$PATH"\n')
            write(root, "data/processed/latest.json", {})
            calls = root / "calls.jsonl"
            environment = {**os.environ, "AUTO_PUSH_RUNTIME": "0", "STATIC_I18N_RECOVERY_BLOCKED": "1",
                           "OFFLINE_CALL_LOG": str(calls)}
            environment.pop("GOOGLE_TRANSLATE_API_KEY", None)
            result = subprocess.run(["bash", str(script)], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FULL_RUN_OK", result.stdout)
            self.assertIn("reason=unpersisted_static_usage_or_dry_run", result.stdout)
            commands = [json.loads(line)[0] for line in calls.read_text().splitlines()]
            self.assertIn("collectors/collect.py", commands)
            self.assertIn("pipeline/render_static_pages.py", commands)
            self.assertNotIn("pipeline/build_localized_feed.py", commands)


class GitPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / "origin.git"
        self.feed = self.root / "feed"
        self.static = self.root / "static"
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.feed))
        self.identity(self.feed)
        write(self.feed, persistence.GUARD, BASE)
        write(self.feed, "data/i18n/ko/feed/budget.json", {"chars_used": 79420})
        write(self.feed, "data/processed/latest.json", {"version": "base"})
        (self.feed / "web").mkdir()
        write(self.feed, "web/source.json", {"version": "base"})
        self.commit(self.feed, "base")
        self.git(self.feed, "push", "origin", "main")
        self.git(self.root, "clone", str(self.remote), str(self.static))
        self.identity(self.static)
        self.saved_path = self.root / "checkpoint.json"
        persistence.prepare(self.static, self.saved_path, "actions-123-1", "ko")
        for path, change in bundle()["files"].items():
            target = self.static / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change["after"], encoding="utf-8")
        self.saved = persistence.checkpoint(self.static, self.saved_path)

    def git(self, root, *args, check=True):
        result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
        if check and result.returncode:
            self.fail(result.stderr)
        return result

    def identity(self, root):
        self.git(root, "config", "user.name", "Offline Test")
        self.git(root, "config", "user.email", "test@example.invalid")

    def commit(self, root, message):
        self.git(root, "add", "data", "web")
        self.git(root, "commit", "-m", message)

    def latest(self, path):
        return json.loads(self.git(self.remote, "show", f"main:{path}").stdout)

    def advance_feed(self, extra=0):
        write(self.feed, persistence.GUARD, guard_plus(1459 + extra))
        write(self.feed, "data/i18n/ko/feed/budget.json", {"chars_used": 80879 + extra})
        write(self.feed, "data/processed/latest.json", {"version": "fresh-feed"})
        write(self.feed, "web/source.json", {"version": "fresh-feed"})
        self.commit(self.feed, f"feed usage {extra}")
        self.git(self.feed, "push", "origin", "main")

    def render(self, root):
        # The real renderer is deterministic/offline. This fixture proves it
        # sees current feed sources rather than the paid run's stale checkout.
        localized = json.loads((root / ARTIFACT).read_text())
        feed = json.loads((root / "data/processed/latest.json").read_text())
        write(root, "web/rendered.json", {"title": localized["title"], "feed": feed["version"]})

    def test_old_workflow_reproduces_conflict_and_leaves_remote_output_missing(self):
        self.commit(self.static, "static output")
        self.advance_feed()
        result = self.git(self.static, "pull", "--rebase", "origin", "main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CONFLICT (content): Merge conflict in data/i18n/spend_guard.json", result.stdout)
        self.assertNotEqual(self.git(self.remote, "show", f"main:{ARTIFACT}", check=False).returncode, 0)
        self.assertTrue(self.saved_path.exists())

    def test_new_publisher_preserves_feed_and_output_and_charges_once(self):
        self.advance_feed()
        with patch.object(persistence.urllib.request, "urlopen", side_effect=AssertionError("no network")):
            persistence.publish(self.static, self.saved, render=self.render)
            persistence.publish(self.static, self.saved, render=lambda _: self.fail("replay rendered twice"))
        self.assertEqual(self.latest(persistence.GUARD)["month_chars"], 52797)
        self.assertEqual(self.latest(persistence.GUARD)["day_chars"], 11338)
        self.assertEqual(self.latest("data/i18n/ko/feed/budget.json")["chars_used"], 80879)
        self.assertEqual(self.latest(STATIC)["chars_used"], 1509)
        self.assertEqual(self.latest("web/rendered.json")["feed"], "fresh-feed")
        self.assertEqual(self.latest(ARTIFACT)["title"], "클로드")
        self.assertEqual(json.loads(self.saved_path.read_text()), self.saved)
        self.assertTrue((self.static / ARTIFACT).exists())

    def test_push_race_rebuilds_on_fresh_main_without_new_translation(self):
        self.advance_feed()
        renders = []

        def render_with_race(root):
            renders.append(root)
            self.render(root)
            if len(renders) == 1:
                self.advance_feed(extra=17)

        persistence.publish(self.static, self.saved, render=render_with_race)
        self.assertEqual(len(renders), 2)
        self.assertEqual(self.latest(persistence.GUARD)["month_chars"], 52814)
        self.assertEqual(self.latest("data/i18n/ko/feed/budget.json")["chars_used"], 80896)
        self.assertEqual(self.latest(STATIC)["chars_used"], 1509)

    def test_render_failure_leaves_checkpoint_for_later_replay(self):
        self.advance_feed()
        with self.assertRaises(RuntimeError):
            persistence.publish(self.static, self.saved, render=lambda _: (_ for _ in ()).throw(RuntimeError("render failed")))
        self.assertEqual(json.loads(self.saved_path.read_text()), self.saved)
        self.assertEqual(self.latest(persistence.GUARD)["month_chars"], 51288)
        persistence.publish(self.static, self.saved, render=self.render)
        self.assertEqual(self.latest(persistence.GUARD)["month_chars"], 52797)

    def test_prepare_refuses_dirty_checkout_instead_of_discarding_outputs(self):
        with self.assertRaisesRegex(persistence.PersistenceError, "dirty checkout"):
            persistence.prepare(self.static, self.root / "other.json", "actions-456-1", "ko")
        self.assertTrue((self.static / ARTIFACT).exists())

    def test_prepare_refreshes_a_stale_trigger_sha_before_spending(self):
        self.advance_feed()
        fresh = self.root / "fresh"
        self.git(self.root, "clone", str(self.remote), str(fresh))
        self.git(fresh, "checkout", "--detach", self.saved["base_commit"])
        persistence.prepare(fresh, self.root / "fresh.json", "actions-456-1", "ko")
        self.assertEqual(json.loads((fresh / persistence.GUARD).read_text())["month_chars"], 51288)

    def test_recovery_restores_checkpoint_before_another_paid_run(self):
        self.advance_feed()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("checkpoint.json", encoded(self.saved))

        def github(_, suffix, **kwargs):
            if "workflows/" in suffix:
                if "page=2" in suffix:
                    return {"workflow_runs": []}
                return {"workflow_runs": [{"id": 123, "run_attempt": 1}]}
            if "runs/123/artifacts" in suffix:
                return {"artifacts": [{"name": "static-i18n-123-1", "id": 4, "expired": False}]}
            if "artifacts/4/zip" in suffix:
                return archive.getvalue()
            self.fail(suffix)

        original_publish = persistence.publish
        with patch.object(persistence, "_github", side_effect=github), patch.object(
            persistence, "publish", side_effect=lambda root, saved: original_publish(root, saved, render=self.render)
        ):
            persistence.recover_pending(self.static, "owner/repo", "456")
        self.assertEqual(self.latest(STATIC)["chars_used"], 1509)

    def test_missing_checkpoint_after_paid_step_blocks_further_charges(self):
        def github(_, suffix, **kwargs):
            if "workflows/" in suffix:
                return {"workflow_runs": [{"id": 123, "run_attempt": 1}]}
            if "/artifacts" in suffix:
                return {"artifacts": []}
            return {"jobs": [{"steps": [
                {"name": "Translate static pages", "conclusion": "success"},
                {"name": persistence.CHECKPOINT_STEP, "conclusion": "failure"},
            ]}]}

        with patch.object(persistence, "_github", side_effect=github):
            with self.assertRaisesRegex(persistence.PersistenceError, "no recovery checkpoint"):
                persistence.recover_pending(self.static, "owner/repo", "456")

    def test_expired_unpublished_checkpoint_blocks_further_charges(self):
        def github(_, suffix, **kwargs):
            if "workflows/" in suffix:
                return {"workflow_runs": [{"id": 123, "run_attempt": 1}]}
            return {"artifacts": [{"name": "static-i18n-123-1", "id": 4, "expired": True}]}

        with patch.object(persistence, "_github", side_effect=github):
            with self.assertRaisesRegex(persistence.PersistenceError, "expired"):
                persistence.recover_pending(self.static, "owner/repo", "456")

    def test_recovery_replays_oldest_first_until_an_acknowledged_run(self):
        write(self.feed, persistence.GUARD, {**BASE, "static_runs": {"actions-100-1": {"sha256": "known"}}})
        self.commit(self.feed, "acknowledged frontier")
        self.git(self.feed, "push", "origin", "main")
        archives = {}
        for ident in (123, 125):
            saved = copy.deepcopy(self.saved)
            saved["run_id"] = f"actions-{ident}-1"
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("checkpoint.json", encoded(saved))
            archives[ident] = archive.getvalue()

        def github(_, suffix, **kwargs):
            if "workflows/" in suffix:
                return {"workflow_runs": [{"id": ident, "run_attempt": 1} for ident in (125, 123, 100)]}
            if "/zip" in suffix:
                return archives[int(suffix.split("/")[2])]
            ident = int(suffix.split("/")[2])
            return {"artifacts": [{"name": f"static-i18n-{ident}-1", "id": ident, "expired": False}]}

        with patch.object(persistence, "_github", side_effect=github), patch.object(persistence, "publish") as replay:
            persistence.recover_pending(self.static, "owner/repo", "456")
        self.assertEqual([call.args[1]["run_id"] for call in replay.call_args_list], ["actions-123-1", "actions-125-1"])


if __name__ == "__main__":
    unittest.main()
