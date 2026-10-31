"""YouTube identity: youtu.be URLs survive dedupe; watch URLs do not."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import build_digest  # noqa: E402


class YoutubeDedupeTest(unittest.TestCase):
    def _items(self, url_for) -> list[dict]:
        return [
            {
                "source": "ai_native_dev",
                "title": f"Episode {index}",
                "url": url_for(index),
                "published": "2026-10-28T00:00:00+00:00",
            }
            for index in range(3)
        ]

    def test_youtu_be_ids_stay_distinct(self) -> None:
        items = self._items(lambda i: f"https://youtu.be/AAAAAAAAAA{i}")
        self.assertEqual(len(build_digest.dedupe(items)), 3)

    def test_watch_query_urls_collapse(self) -> None:
        items = self._items(lambda i: f"https://www.youtube.com/watch?v=AAAAAAAAAA{i}")
        self.assertEqual(len(build_digest.dedupe(items)), 1)


if __name__ == "__main__":
    unittest.main()
