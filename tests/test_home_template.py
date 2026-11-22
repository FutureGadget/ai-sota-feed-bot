"""The home page is generated from one template for every language.

``ui/templates/index.html`` is the source; ``web/index.html`` and
``web/<prefix>/index.html`` are committed build output of
``pipeline/render_home.py``. These tests keep the output and the source from
drifting apart.
"""

from __future__ import annotations

import json
import re
import unittest
from unittest import mock

from pipeline import render_home

DEFAULT = "en"


class GeneratedPagesTest(unittest.TestCase):
    def test_committed_pages_match_what_the_build_produces(self) -> None:
        stale = [str(p.relative_to(render_home.ROOT)) for p in render_home.stale_pages()]
        self.assertEqual(
            stale, [], "regenerate with: python3 pipeline/render_home.py (edit ui/templates/index.html, not the output)"
        )

    def test_generated_page_says_where_it_comes_from(self) -> None:
        html = render_home.output_path(DEFAULT).read_text(encoding="utf-8")
        self.assertIn("ui/templates/index.html", html.split("<html", 1)[0])
        self.assertTrue(html.startswith("<!doctype html>\n"))

    def test_a_rebuild_keeps_the_feed_snapshot_the_page_already_has(self) -> None:
        template = render_home.TEMPLATE_PATH.read_text(encoding="utf-8")
        committed = render_home.output_path(DEFAULT).read_text(encoding="utf-8")
        self.assertEqual(render_home.render(DEFAULT, template), committed)
        self.assertIn('class="feed-seed"', committed)

    def test_a_new_snapshot_replaces_only_the_marked_region(self) -> None:
        template = render_home.TEMPLATE_PATH.read_text(encoding="utf-8")
        seed = f"{render_home.FEED_SEED_START}\n<p>fresh seed</p>\n{render_home.FEED_SEED_END}"
        page = render_home.substitute(template, DEFAULT)
        html = render_home.render(DEFAULT, template, seed=seed)
        self.assertIn("<p>fresh seed</p>", html)
        self.assertEqual(html.count(render_home.FEED_SEED_START), 1)
        before, after = page.split(render_home.FEED_SEED_START)[0], page.split(render_home.FEED_SEED_END)[1]
        self.assertIn(before.split("\n", 1)[1], html)
        self.assertTrue(html.endswith(after))

    def test_the_template_keeps_one_pair_of_seed_markers(self) -> None:
        template = render_home.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertEqual(template.count(render_home.FEED_SEED_START), 1)
        self.assertEqual(template.count(render_home.FEED_SEED_END), 1)


class TokenTest(unittest.TestCase):
    def build(self, template: str, strings: dict[str, str]) -> str:
        with mock.patch.object(render_home.locales, "ui", return_value=strings):
            return render_home.substitute(template, DEFAULT)

    def test_a_missing_key_fails_the_build_and_names_it(self) -> None:
        with self.assertRaisesRegex(KeyError, "no.such.key"):
            self.build("<p>{{t:no.such.key}}</p>", {})

    def test_text_is_escaped_for_html_and_for_json(self) -> None:
        strings = {"a.quote": 'Say <b>"hi"</b> & go'}
        html = self.build('<p title="{{t:a.quote}}">{{t:a.quote}}</p>', strings)
        self.assertNotIn("<b>", html)
        self.assertIn("&quot;hi&quot;", html)
        script = self.build("<script>var s = \"{{json:a.quote}}\";</script>", {"a.quote": 'a "q" </script>'})
        self.assertEqual(json.loads('"' + re.search(r'var s = "(.*)";', script).group(1) + '"'), 'a "q" </script>')
        self.assertNotIn("</script>\";", script)

    def test_a_page_embeds_only_the_keys_its_scripts_name(self) -> None:
        template = "<script>window.UI = {{var:ui_data}}; t('used.key');</script><p>{{t:static.key}}</p>"
        html = self.build(template, {"used.key": "one", "static.key": "two", "other.key": "three"})
        embedded = json.loads(re.search(r"window\.UI = (\{.*?\n    \});", html, re.S).group(1))
        self.assertEqual(embedded["strings"], {"used.key": "one"})


if __name__ == "__main__":
    unittest.main()
