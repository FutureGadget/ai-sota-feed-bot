from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
SITE_CHROME_VERSION = render.SITE_CHROME_ASSET_VERSION
SHELLS = (
    "index.html",
    "daily.html",
    "weekly.html",
    "storyline.html",
    "playbook.html",
    "voices.html",
    "subscribe.html",
)
DESTINATIONS = (
    ("/", "Live feed"),
    ("/daily", "Daily recap"),
    ("/weekly", "Weekly recap"),
    ("/storylines", "Storylines"),
    ("/playbook", "Playbook"),
    ("/map", "Knowledge map"),
    ("/foundations", "Foundations"),
    ("/voices", "Voices"),
    ("/subscribe", "Email digest"),
)


def assert_destination_order(test: unittest.TestCase, html: str) -> None:
    positions = []
    for href, label in DESTINATIONS:
        marker = f'data-site-destination="{href}"'
        test.assertIn(marker, html, f"missing {label} destination")
        positions.append(html.index(marker))
    test.assertEqual(positions, sorted(positions))


class SiteChromeContractTest(unittest.TestCase):
    def test_shared_assets_define_progressive_chrome(self) -> None:
        css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")

        self.assertIn(".site-chrome", css)
        self.assertIn(".site-chrome-enhanced", css)
        self.assertIn("safe-area-inset-bottom", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn(".site-nav-fallback { overflow-x: auto", css)
        self.assertIn("showModal", js)
        self.assertIn("site-chrome-enhanced", js)
        self.assertIn("aria-current", js)

    def test_every_hand_written_shell_uses_shared_chrome(self) -> None:
        for filename in SHELLS:
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn(f'href="/site-chrome.css?v={SITE_CHROME_VERSION}"', html)
                self.assertIn(f'src="/site-chrome.js?v={SITE_CHROME_VERSION}"', html)
                self.assertIn('class="site-chrome"', html)
                self.assertIn("data-site-browse-open", html)
                self.assertIn("Open Editor's Desk", html)
                self.assertIn('class="site-nav-fallback', html)
                self.assertIn('class="site-actions-fallback', html)
                assert_destination_order(self, html)

    def test_subscribe_is_visible_header_action(self) -> None:
        for filename in SHELLS:
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn('class="site-subscribe-action"', html)
                self.assertIn('data-subscribe-placement="header"', html)

    def test_update_indicators_target_navigation_after_it_moves_to_editor_desk(self) -> None:
        for filename in (
            "index.html",
            "daily.html",
            "weekly.html",
            "storyline.html",
            "playbook.html",
            "voices.html",
        ):
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn(
                    "querySelectorAll('.site-nav-fallback a[href]')",
                    html,
                )
        self.assertIn(
            "querySelectorAll('.site-nav-fallback a[href]')",
            render.NAV_UPDATES_JS,
        )

    def test_update_indicators_skip_the_current_section_before_decorating(self) -> None:
        for filename in (
            "index.html",
            "daily.html",
            "weekly.html",
            "storyline.html",
            "playbook.html",
            "voices.html",
        ):
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn("var cur = currentSection();", html)
                self.assertIn("if (section === cur) return;", html)
                self.assertLess(
                    html.index("var cur = currentSection();"),
                    html.index("Object.keys(ROUTE).forEach"),
                )
                self.assertLess(
                    html.index("if (section === cur) return;"),
                    html.index("if (signal && isUnread(section, signal)"),
                )

        self.assertIn("var cur = currentSection();", render.NAV_UPDATES_JS)
        self.assertIn("if (section === cur) return;", render.NAV_UPDATES_JS)

    def test_dynamic_archive_surfaces_keep_visible_direction_controls(self) -> None:
        for filename in ("daily.html", "weekly.html", "playbook.html"):
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn('class="site-context"', html)
                self.assertIn('id="archivePrev"', html)
                self.assertIn('id="archiveNext"', html)
                self.assertIn("configureDirection", html)

    def test_generated_page_uses_shared_chrome(self) -> None:
        html = render.render_page(
            title="Test",
            description="Test",
            canonical="https://www.llm-digest.com/daily/2026-06-22",
            published=None,
            h1="AI Daily Recap",
            meta_line="15 articles · 5 categories",
            json_href="/api/daily?date=2026-06-22",
            archive=render.render_archive_select(
                [
                    ("/daily/2026-06-22", "2026-06-22"),
                    ("/daily/2026-06-21", "2026-06-21"),
                ],
                "/daily/2026-06-22",
                "Day",
            ),
            recap_title="Test",
            recap_range="",
            intro_html="",
            body_html="",
        )

        self.assertIn(f'href="/site-chrome.css?v={SITE_CHROME_VERSION}"', html)
        self.assertIn(f'src="/site-chrome.js?v={SITE_CHROME_VERSION}"', html)
        self.assertIn('class="site-chrome"', html)
        self.assertIn('data-site-section="/daily"', html)
        self.assertIn('class="site-context"', html)
        self.assertIn('class="site-subscribe-action"', html)
        self.assertIn('data-subscribe-placement="header"', html)
        self.assertIn('href="/daily/2026-06-21"', html)
        self.assertIn('class="site-context-disabled"', html)
        assert_destination_order(self, html)

    def test_detail_routes_map_to_parent_destinations(self) -> None:
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")
        for prefix in (
            "/daily/",
            "/weekly/",
            "/storyline/",
            "/topic/",
            "/foundations/",
            "/story/",
            "/playbook/",
        ):
            self.assertIn(prefix, js)

    def test_editor_desk_dialog_groups_navigation_and_actions(self) -> None:
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")
        self.assertIn('["Apply", ["/playbook"]]', js)
        self.assertIn('["Understand", ["/map", "/foundations"]]', js)
        self.assertIn("site-actions-group", js)
        self.assertIn('"Editor\'s Desk"', js)
        self.assertIn('querySelectorAll(":scope > a[data-site-destination]")', js)

    def test_theme_toggle_is_compact_header_action_not_editor_desk_content(self) -> None:
        css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")

        self.assertIn('actions?.querySelector("#themeToggle")', js)
        self.assertIn('themeButton.classList.add("site-theme-toggle")', js)
        self.assertIn("browseButton.before(themeButton)", js)
        self.assertIn(".site-bar-actions > .site-theme-toggle", css)
        self.assertNotIn(".site-dialog #themeToggle", css)

        for filename in SHELLS:
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn('id="themeToggle"', html)
                self.assertIn('title="Toggle theme"', html)
                self.assertIn("btn.textContent = theme === 'dark' ? '☀️' : '🌙';", html)
                self.assertNotIn("Use light theme", html)
                self.assertNotIn("Use dark theme", html)


if __name__ == "__main__":
    unittest.main()
