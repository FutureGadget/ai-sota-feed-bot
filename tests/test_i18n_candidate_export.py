from __future__ import annotations

import unittest

from pipeline import export_i18n_candidates as export


class I18nCandidateExportTest(unittest.TestCase):
    def test_export_covers_all_supported_surfaces(self) -> None:
        payload = export.build_export(locale="zz", include_fresh=True, limit=None)
        surfaces = {item["surface"] for item in payload["items"]}

        self.assertEqual(
            surfaces,
            {"daily", "weekly", "story", "storyline", "topic", "foundations"},
        )

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


if __name__ == "__main__":
    unittest.main()
