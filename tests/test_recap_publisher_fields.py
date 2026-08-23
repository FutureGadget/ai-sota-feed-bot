from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_common(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


daily = load_common(
    "daily_common_publisher_test",
    ".agents/skills/daily-summary/scripts/daily_common.py",
)
weekly = load_common(
    "weekly_common_publisher_test",
    ".agents/skills/weekly-summary/scripts/weekly_common.py",
)


class RecapPublisherFieldsTest(unittest.TestCase):
    INPUT = {
        "title": "A syndicated platform story",
        "url": "https://news.google.com/rss/articles/example",
        "source": "search_agent_engineering_news",
        "type": "news",
        "publisher_name": "Bloomberg",
        "publisher_domain": "bloomberg.com",
    }

    def test_daily_input_preserves_captured_publisher_fields(self) -> None:
        article = daily.clean_article(self.INPUT)

        self.assertEqual(article.get("publisher_name"), "Bloomberg")
        self.assertEqual(article.get("publisher_domain"), "bloomberg.com")

    def test_weekly_input_preserves_captured_publisher_fields(self) -> None:
        article = weekly.clean_article(self.INPUT)

        self.assertEqual(article.get("publisher_name"), "Bloomberg")
        self.assertEqual(article.get("publisher_domain"), "bloomberg.com")


if __name__ == "__main__":
    unittest.main()
