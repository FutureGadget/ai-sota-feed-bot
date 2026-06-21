from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "storyline-editor"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from storyline_common import validate_narrative  # noqa: E402


class StorylineNarrativeValidationTest(unittest.TestCase):
    def _narrative(self) -> dict:
        return {
            "slug": "example",
            "generated_at": "2026-06-21T00:00:00+00:00",
            "covers_last_updated": "2026-06-20T00:00:00+00:00",
            "covers_member_sids": ["a", "b"],
            "tldr": "Background.",
            "beats": [
                {
                    "headline": "First beat",
                    "tone": "launch",
                    "sids": ["a"],
                }
            ],
        }

    def test_beats_must_cover_every_displayed_sid(self) -> None:
        errors = validate_narrative(
            self._narrative(),
            valid_sids={"a", "b"},
            required_beat_sids={"a", "b"},
        )

        self.assertTrue(any("unassigned" in error and "b" in error for error in errors))

    def test_beats_must_not_assign_sid_twice(self) -> None:
        narrative = self._narrative()
        narrative["beats"].append(
            {"headline": "Second beat", "tone": "now", "sids": ["a", "b"]}
        )

        errors = validate_narrative(
            narrative,
            valid_sids={"a", "b"},
            required_beat_sids={"a", "b"},
        )

        self.assertTrue(any("more than once" in error and "a" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
