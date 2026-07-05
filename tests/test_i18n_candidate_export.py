from __future__ import annotations

import unittest

from pipeline import export_i18n_candidates as export


class I18nCandidateExportTest(unittest.TestCase):
    def test_export_covers_all_supported_static_surfaces(self) -> None:
        payload = export.build_export(locale="zz", include_fresh=True, limit=None)
        surfaces = {item["surface"] for item in payload["items"]}

        self.assertEqual(
            surfaces,
            {"daily", "weekly", "story", "storyline", "topic", "foundations"},
        )
        self.assertEqual(payload["excluded_surfaces"][0]["surface"], "feed")
        self.assertIn("/api/feed", payload["excluded_surfaces"][0]["reason"])

    def test_source_payload_is_optional(self) -> None:
        without_source = export.build_export(locale="ko", surfaces={"weekly"}, limit=1)
        with_source = export.build_export(
            locale="ko", surfaces={"weekly"}, include_source=True, limit=1
        )

        self.assertNotIn("source", without_source["items"][0])
        self.assertIn("source", with_source["items"][0])

    def test_surface_filter_keeps_context_small(self) -> None:
        payload = export.build_export(locale="ko", surfaces={"daily"}, limit=3)

        self.assertLessEqual(payload["item_count"], 3)
        self.assertTrue(payload["items"])
        self.assertEqual({item["surface"] for item in payload["items"]}, {"daily"})


if __name__ == "__main__":
    unittest.main()
