"""Tests for pipeline/build_localized_updates.py, the Editor's Desk translation store.

The builder runs as a script, so import it by its bare name. The catalog fetch is
mocked, English pages and Korean artifacts are written under a temp ROOT, and
translation goes through a fake Anthropic client; no test calls the API.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))

import build_localized_updates as updates  # noqa: E402
import render_static_pages as render  # noqa: E402
import translator  # noqa: E402
from claude_fakes import PREFIX, EchoClient  # noqa: E402

NOW = datetime(2026, 11, 23, 3, 0, tzinfo=timezone.utc)


def _item(section: str, key: str, title: str, summary: str = "", day: int = 1) -> dict:
    return {
        "id": f"{section}:{key}", "section": section, "section_label": section.title(),
        "href": f"/{section}/{key}", "title": title, "summary": summary,
        "updated_at": f"2026-11-{30 - day:02d}T00:00:00Z", "version": "a" * 24,
    }


class DeskWindowTest(unittest.TestCase):
    def test_keeps_the_newest_items_of_each_section(self) -> None:
        catalog = [_item("daily", f"2026-11-{20 - i}", f"d{i}", day=i) for i in range(9)]
        catalog += [_item("weekly", f"2026-W{40 + i}", f"w{i}", day=i) for i in range(2)]
        window = updates.desk_window(catalog)
        self.assertEqual(
            window,
            {c["id"] for c in catalog[: updates.DESK_PER_SECTION]} | {c["id"] for c in catalog[9:]},
        )


class SourceHashTest(unittest.TestCase):
    def test_hash_covers_the_title_and_summary_and_nothing_else(self) -> None:
        item = _item("storylines", "a", "Activation  Steering", "Summary.")
        self.assertEqual(updates.source_hash(item), updates.source_hash({**item, "title": " Activation Steering ", "version": "b" * 24}))
        self.assertNotEqual(updates.source_hash(item), updates.source_hash({**item, "summary": "Other."}))
        self.assertNotEqual(updates.source_hash(item), updates.source_hash({**item, "title": "Activation Steering 2"}))


class BuildLocalizedUpdatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.store_path = self.root / "data" / "i18n" / "ko" / "updates" / "titles.json"
        self.ledger_path = self.root / "data" / "i18n" / "translation_spend.json"
        self._patches = [
            patch.object(updates, "ROOT", self.root),
            patch.object(updates, "datetime", _fixed(NOW)),
            patch.dict(os.environ, {translator.CAP_ENV: "60"}),
        ]
        for p in self._patches:
            p.start()
        self.client = EchoClient()
        self.catalog: list[dict] = []

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def write(self, relative: str, payload: dict) -> dict:
        path = self.root / "data" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def write_recap(self, date: str, english: dict, korean: dict, *, fresh: bool = True) -> None:
        """An English daily recap and its Korean artifact, hashed against it (or not)."""
        self.write(f"daily/{date}.json", english)
        stamp = render.i18n_source_hash(english) if fresh else "stale"
        self.write(f"i18n/ko/daily/{date}.json", {"source_path": f"/daily/{date}", "source_hash": stamp, **korean})

    def run_main(self, *, client=None, dry_run: bool = False) -> None:
        argv = ["build_localized_updates.py", "--locale", "ko"] + (["--dry-run"] if dry_run else [])
        with patch.object(sys, "argv", argv), patch.object(updates, "_fetch_catalog", return_value=self.catalog):
            updates.main(client=client or self.client)

    def stored(self) -> dict:
        return json.loads(self.store_path.read_text(encoding="utf-8"))["items"]

    # -- reuse ----------------------------------------------------------------

    def test_a_current_korean_recap_supplies_its_title_and_summary_without_a_call(self) -> None:
        english = {"title": "What happened in AI — Nov 22, 2026", "highlights": ["Together AI disclosed a leak."], "intro": ["x"]}
        self.write_recap("2026-11-22", english, {"title": "11월 22일 AI 데일리", "highlights": ["Together AI, 유출 공개"]})
        item = _item("daily", "2026-11-22", english["title"], "Together AI disclosed a leak.")
        self.catalog = [item]

        self.run_main()

        self.assertEqual(self.client.calls, [])
        entry = self.stored()[item["id"]]
        self.assertEqual((entry["title"], entry["summary"]), ("11월 22일 AI 데일리", "Together AI, 유출 공개"))
        self.assertEqual(entry["origin"], {"title": "artifact", "summary": "artifact"})
        self.assertEqual(entry["source_hash"], updates.source_hash(item))

    def test_a_stale_korean_artifact_is_not_reused(self) -> None:
        english = {"title": "What happened in AI — Nov 22, 2026", "highlights": ["A leak."]}
        self.write_recap("2026-11-22", english, {"title": "옛 제목", "highlights": ["옛 요약"]}, fresh=False)
        self.catalog = [_item("daily", "2026-11-22", english["title"], "A leak.")]

        self.run_main()

        self.assertEqual(self.client.requested, [{"title": english["title"], "summary": "A leak."}])
        self.assertEqual(self.stored()["daily:2026-11-22"]["title"], PREFIX + english["title"])

    def test_an_artifact_text_left_in_english_is_translated_instead(self) -> None:
        english = {"slug": "activation-steering", "label": "Activation Steering", "days": [{}], "editorial": {"whats_new": "A paper."}}
        self.write("storylines/activation-steering.json", english)
        self.write("i18n/ko/storyline/activation-steering.json", {
            "source_hash": render.i18n_source_hash(english),
            "label": "Activation Steering", "editorial": {"whats_new": "A paper."},
        })
        self.catalog = [_item("storylines", "activation-steering", "Activation Steering", "A paper.")]

        self.run_main()

        self.assertEqual(self.client.requested, [{"title": "Activation Steering", "summary": "A paper."}])

    def test_only_the_fields_the_artifact_lacks_are_translated(self) -> None:
        english = {"title": "Playbook — Nov 17", "intro": ["The week is about checks."]}
        self.write("playbook/2026-11-17.json", english)
        self.write("i18n/ko/playbook/2026-11-17.json", {
            "source_hash": render.i18n_source_hash(english), "title": "플레이북 — 11월 17일", "intro": ["The week is about checks."],
        })
        self.catalog = [_item("playbook", "2026-11-17", "Playbook — Nov 17", "The week is about checks.")]

        self.run_main()

        self.assertEqual(self.client.requested, [{"summary": "The week is about checks."}])
        entry = self.stored()["playbook:2026-11-17"]
        self.assertEqual(entry["title"], "플레이북 — 11월 17일")
        self.assertEqual(entry["summary"], PREFIX + "The week is about checks.")
        self.assertEqual(entry["origin"], {"title": "artifact", "summary": translator.model_for("feed")})

    # -- the store ------------------------------------------------------------

    def test_translated_items_land_in_the_documented_store_shape(self) -> None:
        item = _item("storylines", "a", "Shared Memory", "Loom reached Hacker News.")
        self.catalog = [item]

        self.run_main()

        store = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.assertEqual((store["locale"], store["updated_at"]), ("ko", NOW.isoformat()))
        self.assertEqual(store["items"], {item["id"]: {
            "source_hash": updates.source_hash(item), "translated_at": NOW.isoformat(),
            "title": PREFIX + "Shared Memory", "summary": PREFIX + "Loom reached Hacker News.",
            "origin": {"title": translator.model_for("feed"), "summary": translator.model_for("feed")},
        }})

    def test_an_item_without_an_english_summary_is_stored_without_one(self) -> None:
        self.catalog = [_item("map", "agent-cost", "Agent token costs run away")]
        self.run_main()
        self.assertEqual(self.client.requested, [{"title": "Agent token costs run away"}])
        self.assertEqual(self.stored()["map:agent-cost"]["summary"], "")

    def test_the_call_carries_the_summary_as_context_to_ground_a_terse_title(self) -> None:
        self.catalog = [_item("storylines", "a", "Shared Memory", "Loom reached Hacker News.")]
        self.run_main()
        (call,) = self.client.calls
        self.assertEqual(call["model"], translator.model_for("feed"))
        self.assertIn("Loom reached Hacker News.", call["messages"][0]["content"])

    def test_unchanged_items_are_not_translated_again_and_changed_text_is(self) -> None:
        a = _item("storylines", "a", "Shared Memory", "One.")
        b = _item("storylines", "b", "Loom Memory", "Two.")
        self.catalog = [a, b]
        self.run_main()
        first = self.store_path.read_text(encoding="utf-8")

        again = EchoClient()
        self.catalog = [a, {**b, "summary": "Two, rewritten."}]
        self.run_main(client=again)

        self.assertEqual(again.requested, [{"title": "Loom Memory", "summary": "Two, rewritten."}])
        self.assertEqual(self.stored()["storylines:a"]["title"], PREFIX + "Shared Memory")
        self.assertEqual(self.stored()["storylines:b"]["summary"], PREFIX + "Two, rewritten.")
        self.assertNotEqual(first, self.store_path.read_text(encoding="utf-8"))

    def test_a_run_that_changes_nothing_leaves_the_file_untouched(self) -> None:
        self.catalog = [_item("storylines", "a", "Shared Memory", "One.")]
        self.run_main()
        before = self.store_path.stat().st_mtime_ns
        later = EchoClient()
        with patch.object(updates, "datetime", _fixed(datetime(2026, 11, 23, 5, 0, tzinfo=timezone.utc))):
            self.run_main(client=later)
        self.assertEqual(later.calls, [])
        self.assertEqual(self.store_path.stat().st_mtime_ns, before)

    def test_a_translation_is_replaced_by_a_korean_artifact_that_appears_later(self) -> None:
        english = {"title": "What happened in AI — Nov 22, 2026", "highlights": ["A leak."]}
        self.write("daily/2026-11-22.json", english)
        self.catalog = [_item("daily", "2026-11-22", english["title"], "A leak.")]
        self.run_main()
        self.assertEqual(self.stored()["daily:2026-11-22"]["title"], PREFIX + english["title"])

        self.write_recap("2026-11-22", english, {"title": "11월 22일 AI 데일리", "highlights": ["유출 공개"]})
        again = EchoClient()
        self.run_main(client=again)

        self.assertEqual(again.calls, [])
        self.assertEqual(self.stored()["daily:2026-11-22"]["title"], "11월 22일 AI 데일리")

    def test_items_that_left_the_catalog_leave_the_store(self) -> None:
        self.catalog = [_item("storylines", "a", "Shared Memory", "One."), _item("storylines", "b", "Loom Memory", "Two.")]
        self.run_main()
        self.catalog = self.catalog[:1]
        self.run_main(client=EchoClient())
        self.assertEqual(list(self.stored()), ["storylines:a"])

    # -- caps and budget ------------------------------------------------------

    def test_only_the_newest_items_of_a_section_are_translated(self) -> None:
        self.catalog = [_item("storylines", f"s{i}", f"Story {i}", "x", day=i) for i in range(updates.DESK_PER_SECTION + 3)]
        self.run_main()
        self.assertEqual(
            [r["title"] for r in self.client.requested],
            [f"Story {i}" for i in range(updates.DESK_PER_SECTION)],
        )

    def test_one_run_translates_at_most_max_translations_items(self) -> None:
        self.catalog = [_item("storylines", f"s{i}", f"Story {i}", "x", day=i) for i in range(5)]
        with patch.object(updates, "MAX_TRANSLATIONS", 2):
            self.run_main()
        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(sorted(self.stored()), ["storylines:s0", "storylines:s1"])

    def test_cap_already_reached_still_stores_what_artifacts_supply(self) -> None:
        english = {"title": "What happened in AI — Nov 22, 2026", "highlights": ["A leak."]}
        self.write_recap("2026-11-22", english, {"title": "11월 22일 AI 데일리", "highlights": ["유출 공개"]})
        self.catalog = [_item("daily", "2026-11-22", english["title"], "A leak."), _item("storylines", "a", "Shared Memory", "One.")]

        with patch.dict(os.environ, {translator.CAP_ENV: "0.0001"}):
            self.run_main()

        self.assertEqual(self.client.calls, [])
        self.assertEqual(list(self.stored()), ["daily:2026-11-22"])

    def test_cap_reached_mid_run_keeps_the_items_translated_so_far(self) -> None:
        self.catalog = [_item("storylines", f"s{i}", f"Story {i}", "x", day=i) for i in range(3)]
        # One call costs about $0.003 (the fake client's usage); room for one.
        with patch.dict(os.environ, {translator.CAP_ENV: "0.0045"}):
            self.run_main()
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(list(self.stored()), ["storylines:s0"])
        self.assertGreater(json.loads(self.ledger_path.read_text())["usd"], 0)

    def test_spend_lands_in_the_shared_ledger_under_the_feed_surface(self) -> None:
        self.catalog = [_item("storylines", "a", "Shared Memory", "One.")]
        self.run_main()
        ledger = json.loads(self.ledger_path.read_text())
        self.assertEqual({h["surface"] for h in ledger["history"]}, {"feed"})

    def test_a_failed_item_does_not_stop_the_others(self) -> None:
        self.catalog = [_item("storylines", f"s{i}", f"Story {i}", "x", day=i) for i in range(3)]
        self.run_main(client=EchoClient(fail_when=lambda fields: fields["title"] == "Story 1"))
        self.assertEqual(sorted(self.stored()), ["storylines:s0", "storylines:s2"])

    def test_dry_run_calls_nothing_and_writes_nothing(self) -> None:
        self.catalog = [_item("storylines", "a", "Shared Memory", "One.")]
        self.run_main(dry_run=True)
        self.assertEqual(self.client.calls, [])
        self.assertFalse(self.store_path.exists())


def _fixed(fixed_now: datetime):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    return FixedDatetime


if __name__ == "__main__":
    unittest.main()
