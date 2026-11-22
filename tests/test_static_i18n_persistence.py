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
FEED_CARDS = "data/i18n/ko/feed/cards.json"
LEDGER = persistence.LEDGER
RECEIPTS = persistence.RECEIPTS
# Dollar amounts are binary fractions so float sums compare exactly.
BASE = {"month": "2026-10", "usd": 4.0, "history": [{"at": AT, "key": "feed/0", "surface": "feed", "usd": 4.0}]}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(encoded(value), encoding="utf-8")


def ledger_plus(usd, key="static/x"):
    return {
        "month": BASE["month"], "usd": BASE["usd"] + usd,
        "history": BASE["history"] + [{"at": AT, "key": key, "surface": "static", "usd": usd}],
    }


def bundle(usd=0.25):
    return {
        "version": 1, "run_id": "actions-123-1", "locale": "ko", "started_at": AT,
        "base_commit": "0" * 40,
        "checkpoint_complete": True,
        "files": {
            LEDGER: {"before": encoded(BASE), "after": encoded(ledger_plus(usd))},
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

    def test_delta_preserves_feed_spend_and_replays_once(self):
        # Main already holds a feed run's spend that the static checkpoint never saw.
        write(self.root, LEDGER, {
            "month": "2026-10", "usd": 4.125,
            "history": BASE["history"] + [{"at": AT, "key": "feed/1", "surface": "feed", "usd": 0.125}],
        })
        saved = bundle()
        self.assertTrue(persistence.apply_bundle(self.root, saved))
        ledger = self.read(LEDGER)
        self.assertEqual(ledger["usd"], 4.375)
        self.assertEqual([h["surface"] for h in ledger["history"]], ["feed", "feed", "static"])
        self.assertFalse(persistence.apply_bundle(self.root, saved))
        self.assertEqual(self.read(LEDGER), ledger)
        receipt = self.read(RECEIPTS)["static_runs"]["actions-123-1"]
        self.assertEqual(receipt["usage"], {"spend": {"period": "2026-10", "usd": 0.25}})
        changed = copy.deepcopy(saved)
        changed["files"][ARTIFACT]["after"] = encoded({"title": "different"})
        with self.assertRaisesRegex(persistence.PersistenceError, "different checkpoint"):
            persistence.apply_bundle(self.root, changed)

    def test_first_run_creates_the_ledger(self):
        saved = bundle()
        saved["files"][LEDGER]["before"] = None
        saved["files"][LEDGER]["after"] = encoded({
            "month": "2026-10", "usd": 0.25, "history": [{"at": AT, "key": "static/x", "surface": "static", "usd": 0.25}],
        })
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(LEDGER)["usd"], 0.25)

    def test_old_recovery_does_not_roll_a_new_month_back(self):
        write(self.root, LEDGER, {"month": "2026-11", "usd": 0.5, "history": []})
        persistence.apply_bundle(self.root, bundle())
        self.assertEqual(self.read(LEDGER)["month"], "2026-11")
        self.assertEqual(self.read(LEDGER)["usd"], 0.5)
        self.assertEqual(self.read(LEDGER)["history"][0]["usd"], 0.25)
        self.assertEqual(self.read(RECEIPTS)["static_runs"]["actions-123-1"]["usage"]["spend"]["usd"], 0.25)

    def test_new_month_applies_its_full_usage_without_old_month_usage(self):
        saved = bundle(0.0625)
        saved["files"][LEDGER]["after"] = encoded({"month": "2026-11", "usd": 0.0625, "history": []})
        write(self.root, LEDGER, BASE)
        persistence.apply_bundle(self.root, saved)
        self.assertEqual((self.read(LEDGER)["month"], self.read(LEDGER)["usd"]), ("2026-11", 0.0625))

    def test_concurrent_artifact_change_fails_without_mutating_the_ledger(self):
        write(self.root, LEDGER, BASE)
        write(self.root, ARTIFACT, {"source_hash": "b" * 64, "title": "concurrent translation"})
        with self.assertRaisesRegex(persistence.PersistenceError, "concurrent source artifact"):
            persistence.apply_bundle(self.root, bundle())
        self.assertEqual(self.read(LEDGER), BASE)
        self.assertFalse((self.root / RECEIPTS).exists())

    def test_corrupt_and_negative_ledgers_fail_closed(self):
        for after in ["{bad", encoded(ledger_plus(-0.25)), encoded({**BASE, "usd": "0.25"}), encoded({**BASE, "month": "2026-13"})]:
            saved = bundle()
            saved["files"][LEDGER]["after"] = after
            write(self.root, LEDGER, BASE)
            with self.assertRaises(persistence.PersistenceError):
                persistence.apply_bundle(self.root, saved)
            self.assertEqual(self.read(LEDGER), BASE)

    def test_path_escape_and_non_static_files_are_refused(self):
        for path in [
            "../secret.json", "data/i18n/ko/../../secret.json", "data/i18n/ko/feed/cards.json", RECEIPTS,
        ]:
            saved = bundle()
            saved["files"][path] = {"before": None, "after": "{}"}
            with self.assertRaisesRegex(persistence.PersistenceError, "unexpected checkpoint path"):
                persistence.apply_bundle(self.root, saved)

    def test_playbook_array_indexes_are_checkpointable(self):
        saved = bundle()
        saved["files"]["data/i18n/ko/playbook/index.json"] = {"before": None, "after": "[]\n"}
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read("data/i18n/ko/playbook/index.json"), [])

    def test_ambiguous_charges_survive_without_an_output(self):
        saved = bundle(0.0625)
        del saved["files"][ARTIFACT]
        write(self.root, LEDGER, {**BASE, "usd": 4.125})
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(LEDGER)["usd"], 4.1875)

    def test_lost_output_receipt_blocks_only_the_billed_source_version(self):
        saved = bundle()
        del saved["files"][ARTIFACT]
        saved["lost_outputs"] = {ARTIFACT: "a" * 64}
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(persistence.lost_output_run(self.root, ARTIFACT, "a" * 64), "actions-123-1")
        self.assertIsNone(persistence.lost_output_run(self.root, ARTIFACT, "b" * 64))

    def test_lost_payload_receipt_survives_metadata_only_source_changes(self):
        saved = bundle()
        del saved["files"][ARTIFACT]
        saved["lost_outputs"] = {ARTIFACT: "a" * 64}
        saved["lost_payloads"] = {ARTIFACT: "c" * 64}
        persistence.apply_bundle(self.root, saved)
        self.assertEqual(persistence.lost_output_run(self.root, ARTIFACT, "b" * 64, "c" * 64), "actions-123-1")
        self.assertIsNone(persistence.lost_output_run(self.root, ARTIFACT, "b" * 64, "d" * 64))
        saved["lost_payloads"] = {"../secret.json": "c" * 64}
        with self.assertRaisesRegex(persistence.PersistenceError, "unexpected lost output path"):
            persistence.validate_bundle(saved)

    def test_partial_manual_reconciliation_is_reported_not_charged_twice(self):
        saved = bundle()
        write(self.root, LEDGER, ledger_plus(0.25))
        with self.assertRaisesRegex(persistence.PersistenceError, "accounting is uncertain"):
            persistence.apply_bundle(self.root, saved)
        self.assertEqual(self.read(LEDGER), ledger_plus(0.25))

    def test_incomplete_checkpoint_cannot_publish_or_acknowledge_usage(self):
        saved = bundle()
        saved["checkpoint_complete"] = False
        with self.assertRaisesRegex(persistence.PersistenceError, "incomplete"):
            persistence.apply_bundle(self.root, saved)
        self.assertFalse((self.root / RECEIPTS).exists())


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
    def run_full(self, **gate) -> tuple[subprocess.CompletedProcess, list[str]]:
        """Run run_full.sh offline with every python call logged; return the result and the scripts called."""
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
            )
            stub.chmod(0o755)
            activate = root / ".venv/bin/activate"
            activate.parent.mkdir(parents=True)
            activate.write_text(f'export PATH="{binary_dir}:$PATH"\n')
            write(root, "data/processed/latest.json", {})
            calls = root / "calls.jsonl"
            environment = {**os.environ, "AUTO_PUSH_RUNTIME": "0", "OFFLINE_CALL_LOG": str(calls), **gate}
            result = subprocess.run(["bash", str(script)], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FULL_RUN_OK", result.stdout)
            return result, [json.loads(line)[0] for line in calls.read_text().splitlines()]

    def test_unrecovered_static_usage_skips_paid_step_and_completes_english_pipeline(self):
        result, commands = self.run_full(STATIC_I18N_RECOVERY_BLOCKED="1")
        self.assertIn("reason=unpersisted_static_usage_or_dry_run", result.stdout)
        self.assertIn("collectors/collect.py", commands)
        self.assertIn("pipeline/render_static_pages.py", commands)
        self.assertNotIn("pipeline/build_localized_feed.py", commands)
        self.assertNotIn("pipeline/build_localized_updates.py", commands)

    def test_the_desk_titles_are_built_after_the_feed_cards(self):
        _, commands = self.run_full()
        feed, desk = "pipeline/build_localized_feed.py", "pipeline/build_localized_updates.py"
        self.assertIn(desk, commands)
        self.assertLess(commands.index(feed), commands.index(desk))

    def test_the_kill_switch_skips_both_localized_builders(self):
        result, commands = self.run_full(LOCALIZED_FEED_ENABLED="0")
        self.assertIn("reason=disabled", result.stdout)
        self.assertNotIn("pipeline/build_localized_feed.py", commands)
        self.assertNotIn("pipeline/build_localized_updates.py", commands)


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
        write(self.feed, LEDGER, BASE)
        write(self.feed, FEED_CARDS, {"run": "base"})
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

    def advance_feed(self, extra=0.0):
        usd = 0.125 + extra
        write(self.feed, LEDGER, {
            "month": BASE["month"], "usd": BASE["usd"] + usd,
            "history": BASE["history"] + [{"at": AT, "key": "feed/1", "surface": "feed", "usd": usd}],
        })
        write(self.feed, FEED_CARDS, {"run": f"feed-{extra}"})
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
        self.assertIn("CONFLICT (content): Merge conflict in data/i18n/translation_spend.json", result.stdout)
        self.assertNotEqual(self.git(self.remote, "show", f"main:{ARTIFACT}", check=False).returncode, 0)
        self.assertTrue(self.saved_path.exists())

    def test_new_publisher_preserves_feed_and_output_and_charges_once(self):
        self.advance_feed()
        with patch.object(persistence.urllib.request, "urlopen", side_effect=AssertionError("no network")):
            persistence.publish(self.static, self.saved, render=self.render)
            persistence.publish(self.static, self.saved, render=lambda _: self.fail("replay rendered twice"))
        self.assertEqual(self.latest(LEDGER)["usd"], 4.375)  # base + feed 0.125 + static 0.25
        self.assertEqual([h["surface"] for h in self.latest(LEDGER)["history"]], ["feed", "feed", "static"])
        self.assertEqual(self.latest(FEED_CARDS), {"run": "feed-0.0"})
        self.assertIn("actions-123-1", self.latest(RECEIPTS)["static_runs"])
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
                self.advance_feed(extra=0.0625)

        persistence.publish(self.static, self.saved, render=render_with_race)
        self.assertEqual(len(renders), 2)
        self.assertEqual(self.latest(LEDGER)["usd"], 4.4375)  # base + feed 0.1875 + static 0.25
        self.assertEqual(self.latest(FEED_CARDS), {"run": "feed-0.0625"})

    def test_render_failure_leaves_checkpoint_for_later_replay(self):
        self.advance_feed()
        with self.assertRaises(RuntimeError):
            persistence.publish(self.static, self.saved, render=lambda _: (_ for _ in ()).throw(RuntimeError("render failed")))
        self.assertEqual(json.loads(self.saved_path.read_text()), self.saved)
        self.assertEqual(self.latest(LEDGER)["usd"], 4.125)
        persistence.publish(self.static, self.saved, render=self.render)
        self.assertEqual(self.latest(LEDGER)["usd"], 4.375)

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
        self.assertEqual(json.loads((fresh / LEDGER).read_text())["usd"], 4.125)

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
        self.assertEqual(self.latest(LEDGER)["usd"], 4.375)

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
        write(self.feed, RECEIPTS, {"static_runs": {"actions-100-1": {"sha256": "known"}}})
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
