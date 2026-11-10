import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import watch  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "watch_match_cases.json"


class WatchMatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.entities, self.window = watch.load_entities()

    def test_shared_fixture_cases(self) -> None:
        for case in json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]:
            with self.subTest(title=case["title"]):
                got = watch.match_entities(case["title"], case["source"], self.entities)
                self.assertEqual(got, case["expect"])

    def test_normalize_keeps_inner_dots_and_drops_sentence_dots(self) -> None:
        self.assertEqual(watch.normalize("Z.ai ships GLM-5.5."), " z.ai ships glm 5.5 ")

    def test_config_slugs_are_unique_and_email_safe(self) -> None:
        slugs = [e["slug"] for e in self.entities]
        self.assertEqual(len(slugs), len(set(slugs)))
        for slug in slugs:
            self.assertRegex(slug, r"^[a-z0-9][a-z0-9-]{0,99}$")

    def test_published_web_data_matches_the_config(self) -> None:
        # web/watch-data.json carries the rules the browser matches with; a
        # config edit without `python pipeline/watch.py build` would desync it.
        web = json.loads((ROOT / "web" / "watch-data.json").read_text(encoding="utf-8"))
        rules = [{k: e[k] for k in ("slug", "label", "kind", "terms", "not", "sources")} for e in web["entities"]]
        self.assertEqual(rules, self.entities)


class WatchIndexTest(unittest.TestCase):
    def _store(self, records: dict) -> Path:
        tmp = Path(tempfile.mkdtemp())
        (tmp / "2026-11.json").write_text(json.dumps(records), encoding="utf-8")
        return tmp

    def test_index_uses_first_seen_window_and_newest_first(self) -> None:
        entities, _ = watch.load_entities()
        store = self._store({
            "a": {"sid": "a", "title": "Claude Code 2.2", "url": "https://x/a", "source": "s",
                  "first_seen": "2026-11-09T00:00:00+00:00"},
            "b": {"sid": "b", "title": "Claude Code 2.1", "url": "https://x/b", "source": "s",
                  "first_seen": "2026-11-05T00:00:00+00:00"},
            "old": {"sid": "old", "title": "Claude Code 1.0", "url": "https://x/o", "source": "s",
                    "first_seen": "2026-09-01T00:00:00+00:00"},
            "nourl": {"sid": "n", "title": "Claude Code 3", "source": "s",
                      "first_seen": "2026-11-09T00:00:00+00:00"},
        })
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        index = watch.build_index(entities, watch.load_recent_stories(30, now, store), 30)
        cc = next(e for e in index["entities"] if e["slug"] == "claude-code")
        self.assertEqual([i["sid"] for i in cc["items"]], ["a", "b"])
        self.assertEqual(cc["last_updated"], "2026-11-09T00:00:00+00:00")
        self.assertEqual(index["updated_at"], "2026-11-09T00:00:00+00:00")
        self.assertNotIn("generated_at", index)

    def test_prerelease_builds_are_left_out_but_real_releases_stay(self) -> None:
        release = lambda title: {"type": "release", "title": title}  # noqa: E731
        for title in ("codex rust-v0.169.0-alpha.8", "v0.34.0rc0: migrate backends", "langgraph 1.2.0.dev3",
                      "vllm v0.9.0-rc.1", "claude-code 3.0.0-beta"):
            self.assertTrue(watch.is_prerelease(release(title)), title)
        for title in ("claude-code v2.1.322", "langgraph-sdk==0.4.14", "vLLM v0.34.0"):
            self.assertFalse(watch.is_prerelease(release(title)), title)
        # Only release-type stories are filtered; an article about a beta is news.
        self.assertFalse(watch.is_prerelease({"type": "news", "title": "Codex beta opens to teams"}))

        entities, _ = watch.load_entities()
        store = self._store({
            "a": {"sid": "a", "title": "codex 0.169.0-alpha.7", "type": "release", "url": "https://x/a",
                  "source": "openai_codex_releases", "first_seen": "2026-11-09T00:00:00+00:00"},
            "b": {"sid": "b", "title": "codex 0.168.0", "type": "release", "url": "https://x/b",
                  "source": "openai_codex_releases", "first_seen": "2026-11-08T00:00:00+00:00"},
        })
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        index = watch.build_index(entities, watch.load_recent_stories(30, now, store), 30)
        codex = next(e for e in index["entities"] if e["slug"] == "codex")
        self.assertEqual([i["sid"] for i in codex["items"]], ["b"])

    def test_web_payload_drops_urls_and_caps_items(self) -> None:
        entities, _ = watch.load_entities()
        records = {
            f"s{i}": {"sid": f"s{i}", "title": f"vLLM v0.{i}", "url": f"https://x/{i}", "source": "s",
                      "first_seen": f"2026-11-{i + 1:02d}T00:00:00+00:00"}
            for i in range(8)
        }
        now = datetime(2026, 11, 10, tzinfo=timezone.utc)
        index = watch.build_index(entities, watch.load_recent_stories(30, now, self._store(records)), 30)
        web = watch.web_payload(index)
        vllm = next(e for e in web["entities"] if e["slug"] == "vllm")
        self.assertEqual(vllm["count"], 8)
        self.assertEqual(len(vllm["items"]), watch.WEB_ITEMS)
        self.assertNotIn("url", vllm["items"][0])


if __name__ == "__main__":
    unittest.main()


class WatchSurfaceTest(unittest.TestCase):
    def test_story_page_gets_a_slot_only_when_it_matches(self) -> None:
        from pipeline import render_static_pages as render

        html = render.story_watch_html({"title": 'Claude Code 2.2 & "hooks"', "source": "simon_willison"})
        self.assertIn('data-watch-context="story"', html)
        self.assertIn('data-watch-title="Claude Code 2.2 &amp; &quot;hooks&quot;"', html)
        self.assertIn("/watchlist.js?v=", html)
        self.assertIn("/watchlist.css?v=", html)
        self.assertIn(" hidden>", html)
        self.assertEqual(render.story_watch_html({"title": "Storage tiers explained", "source": "aws_ml_blog"}), "")

        rec = {"sid": "a" * 16, "title": "Claude Code 2.2", "url": "https://example.com/a",
               "published": "2026-11-09T00:00:00+00:00"}
        body = render.render_story_body(rec, {rec["sid"]: rec})
        # After the source exit, before the email CTA.
        self.assertLess(body.index("story-source-gate"), body.index("watch-box"))
        self.assertLess(body.index("watch-box"), body.index("subscribe-cta"))

    def test_feed_page_wires_the_module_and_card_slot(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<section id="watchHome" class="watch-home"', html)
        self.assertLess(html.index('id="watchHome"'), html.index('id="freshUpdates"'))
        self.assertIn('class="watch-card-chips" data-watch-title="${title}"', html)
        self.assertIn("/watchlist.js?v=", html)
        self.assertIn("/watchlist.css?v=", html)

    def test_watch_styles_define_no_palette_tokens(self) -> None:
        css = (ROOT / "web" / "watchlist.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"--(bg|card|border|accent|muted|fg)\s*:")
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b")
