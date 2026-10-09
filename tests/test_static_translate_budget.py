"""Budget guard for scripts/translate.py (static page translation)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts"))

import google_translate as gt  # noqa: E402
import translate as static_translate  # noqa: E402


def _candidate(ident: str, text: str) -> dict:
    return {
        "surface": "daily",
        "locale": "ko",
        "source_path": f"data/daily/{ident}.json",
        "source_hash": "h",
        "id": ident,
        "status": "missing",
        "title": ident,
        "source": {"title": text},
        "contract": {"translated_fields": ["title"]},
        "artifact_path": f"data/i18n/ko/daily/{ident}.json",
    }


class StaticTranslateBudgetTests(unittest.TestCase):
    def test_metadata_only_rebuild_cannot_buy_a_lost_translation_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = _candidate("a", "already billed")
            candidate["source"]["generated_at"] = "before"
            original_hash = static_translate._candidate_payload_hash(candidate)
            guard = root / "data/i18n/spend_guard.json"
            guard.parent.mkdir(parents=True)
            guard.write_text(json.dumps({"static_runs": {"actions-123-1": {
                "lost_outputs": {candidate["artifact_path"]: "original-source-hash"},
                "lost_payloads": {candidate["artifact_path"]: original_hash},
            }}}))
            candidate["source"]["generated_at"] = "after"
            candidate["source_hash"] = "rebuilt-source-hash"
            self.assertEqual(static_translate._candidate_payload_hash(candidate), original_hash)
            with (
                patch.object(static_translate, "ROOT", root),
                patch.object(static_translate.exporter, "build_export", return_value={"items": [candidate]}),
                patch.object(static_translate.google_translate, "translate_fields") as paid,
                patch.dict("os.environ", {}, clear=True),
            ):
                code = static_translate.translate_candidates(
                    locale="ko", surfaces=None, target_id=None, limit=10,
                    dry_run=False, include_fresh=True,
                )
            self.assertEqual(code, 0)
            paid.assert_not_called()
            self.assertFalse((root / candidate["artifact_path"]).exists())
            candidate["source"]["title"] = "new translation text"
            self.assertNotEqual(static_translate._candidate_payload_hash(candidate), original_hash)

    def test_acknowledged_lost_output_is_not_bought_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = _candidate("a", "already billed")
            guard = root / "data/i18n/spend_guard.json"
            guard.parent.mkdir(parents=True)
            guard.write_text(json.dumps({"static_runs": {"actions-123-1": {
                "lost_outputs": {candidate["artifact_path"]: candidate["source_hash"]},
            }}}))
            with (
                patch.object(static_translate, "ROOT", root),
                patch.object(static_translate.exporter, "build_export", return_value={"items": [candidate]}),
                patch.object(static_translate.google_translate, "translate_fields") as paid,
                patch.dict("os.environ", {}, clear=True),
            ):
                code = static_translate.translate_candidates(
                    locale="ko", surfaces=None, target_id=None, limit=10,
                    dry_run=False, include_fresh=True,
                )
            self.assertEqual(code, 0)
            paid.assert_not_called()
            self.assertFalse((root / candidate["artifact_path"]).exists())
            self.assertFalse((root / "data/i18n/ko/feed/static_budget.json").exists())

    def test_estimate_matches_payload_chars(self):
        text = "OpenAI & friends"
        self.assertEqual(
            gt.estimate_billed_chars([text]),
            len(gt.protect_terms("OpenAI &amp; friends")),
        )

    def test_candidates_over_budget_are_skipped_and_spend_is_metered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = [_candidate("a", "x" * 60), _candidate("b", "y" * 60)]
            calls: list[str] = []

            def fake_fields(source, fields, locale, *, stats=None, **_):
                calls.append(source["title"])
                if stats is not None:
                    stats["chars_sent"] = stats.get("chars_sent", 0) + len(source["title"])
                return {"title": "t"}

            with (
                patch.object(static_translate, "ROOT", root),
                patch.object(static_translate.exporter, "build_export", return_value={"items": items}),
                patch.object(static_translate.google_translate, "translate_fields", side_effect=fake_fields),
                patch.object(static_translate, "_rebuild_playbook_i18n_index"),
                patch.dict("os.environ", {"GOOGLE_TRANSLATE_STATIC_MONTHLY_CHAR_CAP": "100"}),
            ):
                code = static_translate.translate_candidates(
                    locale="ko", surfaces=None, target_id=None, limit=10,
                    dry_run=False, include_fresh=False,
                )

            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)  # second candidate would exceed the 100 cap
            ledger = json.loads((root / "data/i18n/ko/feed/static_budget.json").read_text())
            self.assertEqual(ledger["chars_used"], 60)
            self.assertEqual(ledger["monthly_cap"], 100)

    def test_daily_quota_reserves_room_for_the_feed(self):
        from datetime import datetime, timezone

        now = datetime(2026, 10, 4, 3, 0, tzinfo=timezone.utc)  # 20:00 PT on Oct 3
        with tempfile.TemporaryDirectory() as tmp:
            feed = Path(tmp) / "budget.json"
            feed.write_text(json.dumps({"history": [
                {"at": "2026-10-04T01:00:00+00:00", "chars": 9000, "run": "r"},  # today (PT)
                {"at": "2026-10-03T05:00:00+00:00", "chars": 5000, "run": "r"},  # yesterday (PT)
            ]}))
            static = {"history": [{"at": "2026-10-04T02:00:00+00:00", "chars": 500, "run": "s"}]}
            # 16000 quota - 6000 reserve - 9000 feed - 500 static
            self.assertEqual(static_translate._daily_headroom(feed, static, now), 500)

    def test_partial_failure_still_meters_billed_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def failing(source, fields, locale, *, stats=None, **_):
                stats["chars_sent"] = 40
                raise ConnectionError("boom")

            with (
                patch.object(static_translate, "ROOT", root),
                patch.object(static_translate.exporter, "build_export", return_value={"items": [_candidate("a", "x" * 40)]}),
                patch.object(static_translate.google_translate, "translate_fields", side_effect=failing),
            ):
                code = static_translate.translate_candidates(
                    locale="ko", surfaces=None, target_id=None, limit=10,
                    dry_run=False, include_fresh=False,
                )

            self.assertEqual(code, 1)
            ledger = json.loads((root / "data/i18n/ko/feed/static_budget.json").read_text())
            self.assertEqual(ledger["chars_used"], 40)


if __name__ == "__main__":
    unittest.main()
