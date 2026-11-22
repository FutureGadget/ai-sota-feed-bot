"""scripts/r2_sync.py publishes exactly the files the API can read."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

_spec = importlib.util.spec_from_file_location("r2_sync", ROOT / "scripts" / "r2_sync.py")
r2_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r2_sync)

import locales  # noqa: E402


class R2SyncListTest(unittest.TestCase):
    def test_every_localized_locale_publishes_its_feed_snapshot_status_and_cards(self) -> None:
        for code in locales.others(locales.DEFAULT):
            for name in ("latest.json", "status.json", "cards.json"):
                self.assertIn(f"i18n/{code}/feed/{name}", r2_sync.EXACT_FILES)


if __name__ == "__main__":
    unittest.main()
