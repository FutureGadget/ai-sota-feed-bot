from __future__ import annotations

import unittest

from pipeline import export_i18n_candidates as export


class I18nCandidateExportTest(unittest.TestCase):
    def test_export_covers_all_supported_surfaces(self) -> None:
        payload = export.build_export(locale="zz", include_fresh=True, limit=None)
        surfaces = {item["surface"] for item in payload["items"]}

        self.assertEqual(
            surfaces,
            {"daily", "weekly", "playbook", "story", "storyline", "topic", "foundations"},
        )
        self.assertEqual(payload["excluded_surfaces"][0]["surface"], "feed")
        self.assertIn("/api/feed", payload["excluded_surfaces"][0]["reason"])

    def test_existing_korean_slice_is_marked_fresh_when_included(self) -> None:
        payload = export.build_export(locale="ko", include_fresh=True, limit=None)
        by_path = {item["source_path"]: item for item in payload["items"]}

        for path in [
            "/daily/2026-07-04",
            "/weekly/2026-W27",
            "/story/ee2eab4f35a2124a",
            "/storyline/claude-fable",
            "/topic/agent-cost",
            "/foundations/context-compaction-safety",
        ]:
            self.assertEqual(by_path[path]["status"], "fresh", path)

    def test_default_export_omits_fresh_artifacts(self) -> None:
        payload = export.build_export(locale="ko", surfaces={"daily"}, limit=None)
        paths = {item["source_path"] for item in payload["items"]}

        self.assertNotIn("/daily/2026-07-04", paths)

    def test_source_payload_is_optional(self) -> None:
        without_source = export.build_export(locale="ko", surfaces={"weekly"}, limit=1)
        with_source = export.build_export(
            locale="ko", surfaces={"weekly"}, include_source=True, limit=1
        )

        self.assertNotIn("source", without_source["items"][0])
        self.assertIn("source", with_source["items"][0])

    def test_is_within_days(self) -> None:
        from datetime import datetime, timedelta
        current_date_str = datetime.now().date().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        three_days_ago_str = (datetime.now().date() - timedelta(days=3)).strftime("%Y-%m-%d")

        # daily recap delta checks: threshold is days + 1
        # delta = 1 day (yesterday recap tested with days=1) -> True (1 <= 2)
        self.assertTrue(export._is_within_days("daily", "xyz", {"date": yesterday_str}, 1))
        # delta = 3 days (tested with days=1) -> False (3 <= 2 is False)
        self.assertFalse(export._is_within_days("daily", "xyz", {"date": three_days_ago_str}, 1))
        # delta = 3 days (tested with days=2) -> True (3 <= 3)
        self.assertTrue(export._is_within_days("daily", "xyz", {"date": three_days_ago_str}, 2))

        # weekly recap delta checks: threshold is days + 7
        # weekly recap usually start of week is parsed
        self.assertTrue(export._is_within_days("weekly", "xyz", {"week": "2026-W27"}, 1))  # usually matches

        # topic / foundations: always True
        self.assertTrue(export._is_within_days("topic", "xyz", {}, 1))
        self.assertTrue(export._is_within_days("foundations", "xyz", {}, 1))

        # standard surface (e.g. story): threshold is days
        self.assertTrue(export._is_within_days("story", "xyz", {"published": yesterday_str}, 1))
        self.assertFalse(export._is_within_days("story", "xyz", {"published": three_days_ago_str}, 1))


if __name__ == "__main__":
    unittest.main()
