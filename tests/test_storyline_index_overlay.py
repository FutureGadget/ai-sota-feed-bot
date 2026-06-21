from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import build_storylines


class StorylineIndexOverlayTest(unittest.TestCase):
    def test_index_receives_compact_editorial_fields(self) -> None:
        sid = "aaaaaaaaaaaaaaaa"
        entry = {
            "last_updated": "2026-06-20T10:00:00+00:00",
            "member_sids": [sid],
        }
        detail = {"days": [{"date": "2026-06-20", "items": [{"sid": sid}]}]}
        narrative = {
            "slug": "example-thread",
            "generated_at": "2026-06-20T11:00:00+00:00",
            "covers_last_updated": entry["last_updated"],
            "covers_member_sids": [sid],
            "tldr": "Background context.",
            "whats_new": "The latest consequential change.",
            "why_it_matters": "Why this affects platform engineering.",
            "take_for_builders": "Check the changed deployment terms.",
            "status": {"state": "Available", "tone": "now"},
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example-thread.json").write_text(json.dumps(narrative), encoding="utf-8")
            with patch.object(build_storylines, "NARRATIVE_DIR", root):
                build_storylines.apply_narrative("example-thread", detail, entry)

        self.assertEqual(entry["editorial"]["whats_new"], narrative["whats_new"])
        self.assertEqual(entry["editorial"]["take_for_builders"], narrative["take_for_builders"])
        self.assertEqual(entry["editorial"]["status"]["state"], "Available")
        self.assertFalse(entry["editorial"]["stale"])


if __name__ == "__main__":
    unittest.main()
