from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
SITE_CHROME_VERSION = render.SITE_CHROME_ASSET_VERSION
POSTHOG_CLIENT_VERSION = render.POSTHOG_CLIENT_ASSET_VERSION
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

    def test_update_indicators_are_the_shared_script_everywhere(self) -> None:
        # One copy of the freshness logic: every shell that shows indicators
        # loads /nav-updates.js instead of embedding a private fork of it.
        for filename in (
            "index.html",
            "daily.html",
            "weekly.html",
            "storyline.html",
            "playbook.html",
            "voices.html",
            "map.html",
            "foundations.html",
        ):
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn('src="/nav-updates.js', html)
                self.assertNotIn("ai_feed_seen_daily_v1", html)
        self.assertIn('src="/nav-updates.js', render.NAV_UPDATES_TAG)

    def test_posthog_page_view_init_is_shared_site_wide(self) -> None:
        for filename in (
            "index.html",
            "daily.html",
            "weekly.html",
            "storyline.html",
            "playbook.html",
            "voices.html",
            "subscribe.html",
            "map.html",
            "foundations.html",
        ):
            with self.subTest(filename=filename):
                html = (ROOT / "web" / filename).read_text(encoding="utf-8")
                self.assertIn(f'src="/posthog-client.js?v={POSTHOG_CLIENT_VERSION}"', html)
                self.assertNotIn("async function initClientConfig()", html)
                self.assertNotIn("posthog-array-js", html)

        js = (ROOT / "web" / "posthog-client.js").read_text(encoding="utf-8")
        self.assertIn("ai_feed_anon_user_id", js)
        self.assertIn("sdk.identify(anon)", js)
        self.assertIn("sdk.capture('page_view'", js)
        self.assertIn("capture('scroll_depth'", js)
        self.assertIn("startScrollDepthTracking()", js)
        self.assertIn("var thresholds = [25, 50, 75, 90, 100]", js)
        self.assertIn("capture_pageview: false", js)
        self.assertIn("autocapture: false", js)
        self.assertIn("person_profiles: 'identified_only'", js)
        self.assertIn('src="/posthog-client.js', render.POSTHOG_CLIENT_TAG)

    def test_update_indicator_script_keeps_core_invariants(self) -> None:
        js = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        # Decorates the semantic nav Editor's Desk adopts.
        self.assertIn("querySelectorAll('.site-nav-fallback a[href]')", js)
        # Skips the current section before decorating, then marks it seen.
        self.assertIn("var cur = currentSection();", js)
        self.assertIn("if (section === cur) return;", js)
        self.assertLess(
            js.index("var cur = currentSection();"),
            js.index("Object.keys(ROUTE).forEach"),
        )
        # Every editorial section has a seen marker and a route, foundations
        # included (it was missing before the shared script existed).
        for section in ("daily", "weekly", "storylines", "playbook", "map", "foundations"):
            self.assertIn(f"ai_feed_seen_{section}_v1", js)
        self.assertIn("'/foundations': 'foundations'", js)

    def test_feed_strip_is_gated_to_returning_readers(self) -> None:
        js = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        # The "Fresh from the Editor's Desk" strip renders only on the feed,
        # only for sections with an existing seen marker (a reader who has
        # engaged before), and stays dismissible for the session.
        self.assertIn("isFeedPage()", js)
        self.assertIn("if (getItem(SEEN[section])) stripEligible.push(section);", js)
        self.assertIn("ai_feed_whats_new_dismissed_v1", js)
        self.assertIn("whats-new-chip", js)

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
        self.assertIn(f'src="/posthog-client.js?v={POSTHOG_CLIENT_VERSION}"', html)
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
