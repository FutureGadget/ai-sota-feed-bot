"""The home page is generated from one template for every language.

``ui/templates/index.html`` is the source; ``web/index.html`` and
``web/<prefix>/index.html`` are committed build output of
``pipeline/render_home.py``. These tests keep the output and the source from
drifting apart.
"""

from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
