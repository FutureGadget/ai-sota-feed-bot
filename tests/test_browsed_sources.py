"""Browsed sources: the registry contract and the x_watch collector type."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "collectors"))

import collect  # noqa: E402
from pipeline import editorial  # noqa: E402
from pipeline.sources_config import load_sources  # noqa: E402

NOW = datetime(2026, 11, 29, 6, 0, 0, tzinfo=timezone.utc)


def _slot_sources(path: Path, slot: str) -> set[str]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return set(cfg["slots"][slot]["sources"])


def _write_day(base: Path, day: str, posts: list[dict]) -> None:
    (base / "x").mkdir(parents=True, exist_ok=True)
    (base / "x" / f"{day}.json").write_text(json.dumps({"posts": posts}))


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "x_watch_script", ROOT / ".agents" / "skills" / "x-watch" / "scripts" / "x_watch.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RegistryTest(unittest.TestCase):
    def test_every_browsed_source_is_an_x_watch_entry_named_after_its_handle(self):
        browsed = load_sources("browsed")
        self.assertTrue(browsed)
        for src in browsed:
            self.assertEqual(src["type"], "x_watch")
            self.assertEqual(src["name"], f"x_{src['handle'].lower()}")

    def test_every_x_watch_source_is_mapped_to_the_posts_lane_in_both_configs(self):
        names = {s["name"] for s in load_sources() if s.get("type") == "x_watch"}
        for path in (ROOT / "config" / "ranking.yaml", ROOT / "config" / "presets" / "balanced.yaml"):
            self.assertLessEqual(names, _slot_sources(path, "practitioner_posts"), path.name)

    def test_fetched_and_browsed_registries_do_not_share_names(self):
        fetched = {s["name"] for s in load_sources("fetched")}
        browsed = {s["name"] for s in load_sources("browsed")}
        self.assertTrue(fetched and browsed)
        self.assertFalse(fetched & browsed)

    def test_duplicate_names_across_registries_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = Path(tmp) / "config" / "sources"
            sources.mkdir(parents=True)
            (sources / "fetched.yaml").write_text("sources:\n  - name: a\n    type: rss\n")
            (sources / "browsed.yaml").write_text("sources:\n  - name: a\n    type: x_watch\n")
            with self.assertRaisesRegex(ValueError, "duplicate_source_name:a"):
                load_sources(root=Path(tmp))

    def test_x_sources_get_the_practitioner_role(self):
        self.assertEqual(editorial.source_role("x_karpathy"), "practitioner")


class XWatchCollectorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        patcher = mock.patch.object(collect.sources_config, "BROWSED_DATA_DIR", self.base)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_reads_the_handles_posts_from_recent_day_files(self):
        long_line = "Agents " + "word " * 40
        _write_day(self.base, "2026-11-29", [
            {"handle": "karpathy", "author": "Andrej Karpathy", "url": "https://x.com/karpathy/status/2",
             "text": f"{long_line}\nsecond line", "published": "2026-11-29T01:00:00Z",
             "quoted": {"handle": "@simonw", "text": "quoted text", "url": "https://x.com/simonw/status/9"}},
            {"handle": "bcherny", "url": "https://x.com/bcherny/status/3", "text": "not mine"},
        ])
        _write_day(self.base, "2026-11-28", [
            {"handle": "Karpathy", "url": "https://x.com/karpathy/status/1", "text": "older post"},
            {"handle": "karpathy", "url": "https://x.com/karpathy/status/2", "text": "duplicate"},
        ])
        _write_day(self.base, "2026-11-25", [
            {"handle": "karpathy", "url": "https://x.com/karpathy/status/0", "text": "outside lookback"},
        ])

        items = collect.collect_from_x_watch({"name": "x_karpathy", "type": "x_watch", "handle": "karpathy"}, NOW)

        self.assertEqual([i["url"] for i in items],
                         ["https://x.com/karpathy/status/2", "https://x.com/karpathy/status/1"])
        first = items[0]
        self.assertTrue(first["title"].endswith("…"))
        self.assertLessEqual(len(first["title"]), collect.X_TITLE_CHARS + 1)
        self.assertIn("second line", first["summary"])
        self.assertIn("Quoting @simonw: quoted text (https://x.com/simonw/status/9)", first["summary"])
        self.assertEqual(first["publisher_name"], "Andrej Karpathy (@karpathy)")
        self.assertEqual(first["publisher_domain"], "x.com")
        self.assertEqual(items[1]["published"], NOW.isoformat())

    def test_returns_nothing_when_no_day_file_exists(self):
        self.assertEqual(collect.collect_from_x_watch({"handle": "karpathy"}, NOW), [])


class XWatchScriptTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.mod = _load_script()
        patcher = mock.patch.object(self.mod, "X_DIR", self.base / "x")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, *argv) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.mod.main(list(argv), now=NOW)
        return code, out.getvalue()

    def test_merge_validates_then_merges_idempotently(self):
        posts = self.base / "posts.json"
        posts.write_text(json.dumps([{"handle": "KARPATHY", "url": "https://x.com/karpathy/status/12",
                                      "text": "hi", "published": "2026-11-29T01:00:00+00:00"}]))
        self.assertEqual(self._run("merge", "--in", str(posts))[0], 0)
        code, out = self._run("merge", "--in", str(posts))
        self.assertEqual(code, 0)
        self.assertIn("added=0 total=1", out)
        saved = json.loads((self.base / "x" / "2026-11-29.json").read_text())["posts"]
        self.assertEqual([p["handle"] for p in saved], ["karpathy"])
        self.assertEqual(self._run("check")[0], 0)

    def test_merge_rejects_unknown_accounts_and_mismatched_urls(self):
        posts = self.base / "posts.json"
        posts.write_text(json.dumps([
            {"handle": "nobody", "url": "https://x.com/nobody/status/1", "text": "x",
             "published": "2026-11-29T01:00:00Z"},
            {"handle": "karpathy", "url": "https://x.com/bcherny/status/1", "text": "x",
             "published": "2026-11-29"},
        ]))
        code, out = self._run("merge", "--in", str(posts))
        self.assertEqual(code, 1)
        self.assertIn("unknown_handle:nobody", out)
        self.assertIn("bad_url:https://x.com/bcherny/status/1", out)
        self.assertIn("bad_published", out)
        self.assertFalse((self.base / "x").exists())

    def test_plan_starts_each_account_after_its_newest_saved_post(self):
        _write_day(self.base, "2026-11-28", [
            {"handle": "karpathy", "url": "https://x.com/karpathy/status/1", "text": "a",
             "published": "2026-11-28T20:00:00+00:00"},
        ])
        code, out = self._run("plan")
        self.assertEqual(code, 0)
        by_handle = {a["handle"]: a for a in json.loads(out)["accounts"]}
        self.assertEqual(by_handle["karpathy"]["since"], "2026-11-28T20:00:00+00:00")
        self.assertEqual(by_handle["bcherny"]["since"], "2026-11-27T06:00:00+00:00")
        self.assertEqual(by_handle["HamelHusain"]["url"], "https://x.com/HamelHusain")


if __name__ == "__main__":
    unittest.main()
