from __future__ import annotations

import hashlib
import re
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
    "models.html",
)
_RETIRED_OAT_SCRIPT_SHELLS = (
    "index.html",
    "daily.html",
    "weekly.html",
    "storyline.html",
    "playbook.html",
    "voices.html",
)
DESTINATIONS = (
    ("/", "Live feed"),
    ("/daily", "Daily recap"),
    ("/weekly", "Weekly recap"),
    ("/storylines", "Storylines"),
    ("/playbook", "Playbook"),
    ("/map", "Agent Know-How"),
    ("/foundations", "Foundations"),
    ("/models", "Model Radar"),
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
    def test_oat_is_retired_and_every_shell_loads_the_ui_layer(self) -> None:
        # Oat was replaced by Tailwind + Basecoat (web/ui.css) on 2026-11-07.
        for asset in ("oat.min.css", "oat.min.js", "oat.LICENSE.txt"):
            self.assertFalse((ROOT / "web" / asset).exists(), f"retired asset still present: {asset}")
        render_src = (ROOT / "pipeline" / "render_static_pages.py").read_text(encoding="utf-8")
        # Every hand-written shell, the Korean ones included: a fixed list
        # missed ko/playbook.html. map.html and foundations.html are generated.
        generated = {"map.html", "foundations.html"}
        shells = [p for p in sorted((ROOT / "web").glob("*.html")) if p.name not in generated]
        shells += sorted((ROOT / "web" / "ko").glob("*.html"))
        for name, html in [*((str(p.relative_to(ROOT / "web")), p.read_text(encoding="utf-8")) for p in shells),
                           ("render_static_pages.py", render_src)]:
            with self.subTest(shell=name):
                self.assertNotIn("oat.min", html)
                self.assertNotIn("https://oat.ink/", html)
                self.assertIn('href="/ui.css?v=', html)

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

    def test_fallback_links_stay_out_of_layout_until_chrome_boots(self) -> None:
        css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")

        # Scripted pages must not paint the open link grid and then collapse
        # it (a 0.35 layout shift on phones); no-JS pages keep the links.
        block = css.split("@media (scripting: enabled)", 1)[1].split("@keyframes", 1)[0]
        self.assertIn(
            "html:not(.site-chrome-enhanced):not(.site-chrome-static) .site-chrome .site-nav-fallback",
            block,
        )
        self.assertIn(".site-actions-fallback", block)
        self.assertIn("visibility: hidden", block)
        # The Precision rule gives the rows vertical padding; collapse it too,
        # or each hidden row still takes 11px and the page jumps 22px.
        self.assertIn("padding-block: 0;", block)
        # If the script never runs, the links come back on their own.
        self.assertIn("animation: site-chrome-fallback-reveal", block)
        self.assertIn("@keyframes site-chrome-fallback-reveal", css)
        # A browser that can't enhance shows the links immediately.
        self.assertIn('root.classList.add("site-chrome-static")', js)

    def test_floating_bar_waits_for_the_in_flow_bar_and_compacts_on_mobile(self) -> None:
        css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")

        # The sentinel belongs after the original bar. A top-of-header sentinel
        # engages after a few pixels and overlays the still-visible page heading.
        self.assertIn("bar.after(spacer, sentinel)", js)
        self.assertIn("entry.boundingClientRect.top < 0", js)
        self.assertIn("spacer.style.height", js)
        self.assertIn("const refreshFixedSpacer", js)
        self.assertIn('window.addEventListener("resize", refreshFixedSpacer', js)

        # The ordinary <=480px bar uses two rows. Its fixed form must explicitly
        # undo the 100%-width child rules before switching to a single row.
        self.assertIn(".site-bar.site-bar-fixed > .site-brand", css)
        self.assertIn(".site-bar.site-bar-fixed > .site-bar-actions", css)
        self.assertIn("flex: 1 1 auto", css)
        self.assertIn("width: auto", css)

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
        # Standard $pageview capture is the single source of pageview telemetry.
        # The legacy manual page_view capture was removed because it duplicated
        # every $pageview (decision-log.md, 2026-07-13).
        self.assertIn("capture_pageview: 'history_change'", js)
        self.assertNotIn("captureLegacyPageView", js)
        self.assertNotIn("sdk.capture('page_view'", js)
        self.assertIn("capture('scroll_depth'", js)
        self.assertIn("startScrollDepthTracking()", js)
        self.assertIn("var thresholds = [25, 50, 75, 90, 100]", js)
        self.assertIn("autocapture: false", js)
        self.assertIn("person_profiles: 'identified_only'", js)
        self.assertIn('src="/posthog-client.js', render.POSTHOG_CLIENT_TAG)

    def test_update_indicator_script_keeps_core_invariants(self) -> None:
        js = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        # Decorates the semantic nav Editor's Desk adopts.
        self.assertIn("querySelectorAll('.site-nav-fallback a[href]')", js)
        # Identity and version state replaces lossy section-wide timestamps.
        self.assertIn("ai_feed_editorial_state_v2", js)
        self.assertIn("reader.markItemOpened(memory, items(), href)", js)
        self.assertNotIn("setItem(SEEN[cur]", js)
        self.assertIn("'/foundations': 'foundations'", js)

    def test_feed_discovery_supports_first_visits_and_session_dismiss(self) -> None:
        js = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        self.assertIn("reader.initializeState(memory, items())", js)
        self.assertIn("ai_feed_whats_new_dismissed_v1", js)
        self.assertIn("Latest from the Editor’s Desk", js)
        self.assertIn("viewAll", js)

    def test_updates_shell_does_not_load_editorial_styles_twice(self) -> None:
        html = (ROOT / "web" / "updates.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        self.assertIn('href="/editorial-updates.css?v=20261107-glitch-sweep"', html)
        self.assertIn("document.querySelector('link[href^=\"/editorial-updates.css\"]')", js)

    def test_feed_editorial_panel_starts_compact_on_phones(self) -> None:
        # At phone width the Editor's Desk rows pushed every story below the
        # first screen; the feed placement collapses to one expandable line.
        js = (ROOT / "web" / "nav-updates.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "editorial-updates.css").read_text(encoding="utf-8")
        self.assertIn("matchMedia('(max-width: 640px)')", js)
        self.assertIn("'ai_feed_whats_new_expanded_v1'", js)
        self.assertIn("editorial_updates_expand", js)
        self.assertIn(".editorial-compact .editorial-list", css)

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
        self.assertNotIn('src="/local-translate.js', html)

        self.assertIn('class="site-chrome"', html)
        self.assertIn('data-site-section="/daily"', html)
        self.assertIn('class="site-context"', html)
        self.assertIn('class="site-subscribe-action"', html)
        self.assertIn('data-subscribe-placement="header"', html)
        self.assertIn('href="/daily/2026-06-21"', html)
        self.assertIn('class="site-context-disabled"', html)
        assert_destination_order(self, html)

    def test_generated_model_detail_maps_to_model_radar(self) -> None:
        html = render.render_page(
            title="Test model",
            description="Test",
            canonical="https://www.llm-digest.com/models/test-model",
            published=None,
            h1="Test model",
            meta_line="Model details",
            json_href="",
            archive="",
            recap_title="Test model",
            recap_range="",
            intro_html="",
            body_html="",
        )

        self.assertIn('data-site-section="/models"', html)
        self.assertIn(
            'data-site-destination="/models" aria-current="page">Model Radar</a>',
            html,
        )
        assert_destination_order(self, html)

    def test_generated_page_can_emit_browser_matched_language_action(self) -> None:
        html = render.render_page(
            title="Test",
            description="Test",
            canonical="https://www.llm-digest.com/daily/2026-06-22",
            published=None,
            h1="AI Daily Recap",
            meta_line="15 articles · 5 categories",
            json_href="",
            archive="",
            recap_title="Test",
            recap_range="",
            intro_html="",
            body_html="",
            language_links=[("ko", "/ko/daily/2026-06-22", "Korean")],
        )

        self.assertIn('class="site-language-action"', html)
        self.assertIn('href="/ko/daily/2026-06-22"', html)
        self.assertIn('data-language-link data-language-locale="ko" hidden', html)
        self.assertIn('aria-label="Read this page in Korean"', html)

    def test_site_chrome_reveals_language_action_for_browser_locale(self) -> None:
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")

        self.assertIn('querySelectorAll("[data-language-link]")', js)
        self.assertIn("navigator.languages", js)
        self.assertIn("dataset.languageLocale", js)
        self.assertIn("lang.startsWith(`${locale}-`)", js)
        self.assertIn("link.hidden = !matches", js)
        self.assertIn("visibleLanguageLinks", js)
        self.assertIn('link.classList.add("site-bar-language-action")', js)
        self.assertIn("browseButton.before(link)", js)

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
            "/models/",
        ):
            self.assertIn(prefix, js)

    def test_editor_desk_dialog_groups_navigation_and_actions(self) -> None:
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")
        self.assertIn('["Apply", ["/playbook"]]', js)
        self.assertIn('["Understand", ["/map", "/foundations", "/models", "/skills"]]', js)
        self.assertIn("site-actions-group", js)
        self.assertIn('"Editor\'s Desk"', js)
        self.assertIn('querySelectorAll(":scope > a[data-site-destination]")', js)

    def test_every_site_destination_is_grouped_and_described(self) -> None:
        """A new nav destination must be added to the Editor's Desk map.

        `/skills` shipped as an ungrouped link with no description, so the dialog
        rendered it as a bare label at the bottom of the panel. Groups and
        descriptions are hardcoded in site-chrome.js; this test ties them to
        SITE_DESTINATIONS so the next page cannot repeat that.
        """
        js = (ROOT / "web" / "site-chrome.js").read_text(encoding="utf-8")
        groups = js.split("const groups = [", 1)[1].split("];", 1)[0]
        descriptions = js.split("const descriptions = {", 1)[1].split("};", 1)[0]

        for href, label in render.SITE_DESTINATIONS:
            self.assertIn(f'"{href}"', groups, f"{label} is missing from the Editor's Desk groups")
            self.assertIn(f'"{href}":', descriptions, f"{label} has no Editor's Desk description")

        for href in re.findall(r'"(/[a-z0-9/-]*)"', groups):
            self.assertIn(
                href,
                {destination for destination, _ in render.SITE_DESTINATIONS},
                f"Editor's Desk groups an unknown destination: {href}",
            )

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

    def test_live_translation_script_is_not_loaded(self) -> None:
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
                self.assertNotIn('src="/local-translate.js', html)
                self.assertNotIn("data-local-translate-surface", html)
                self.assertNotIn("data-translate-ui-slot", html)



THEMED_SOURCES = (
    "web/index.html",
    "web/ko/index.html",
    "web/daily.html",
    "web/weekly.html",
    "web/storyline.html",
    "web/playbook.html",
    "web/playbook-lab.html",
    "web/voices.html",
    "web/subscribe.html",
    "web/updates.html",
    "web/models.html",
    "web/models-compare.html",
    "web/model-comparison.css",
    "web/front-page.css",
    "ui/site.css",
    "pipeline/render_static_pages.py",
)
SHARED_TOKENS = ("bg", "card", "border", "accent", "muted", "fg", "signal", "warm", "brief-wash", "brief-ink")


def _theme_block(css: str, selector: str) -> dict[str, str]:
    body = css.split(selector + " {", 1)[1].split("}", 1)[0]
    tokens = {}
    for line in body.split(";"):
        line = re.sub(r"/\*.*?\*/", "", line, flags=re.S).strip()
        if line.startswith("--") and ":" in line:
            name, value = line.split(":", 1)
            tokens[name.strip()[2:]] = value.strip()
    return tokens


def _contrast(fg: str, bg: str) -> float:
    def lum(hex_color: str) -> float:
        h = hex_color.lstrip("#")
        c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class WebFontLoadingTest(unittest.TestCase):
    """Geist swapping in late must not reflow the page (storyline CLS 0.11)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")

    def _token(self, name: str) -> str:
        match = re.search(rf"--{name}:\s*([^;]+);", self.css)
        self.assertIsNotNone(match, name)
        return match.group(1)

    def test_font_tokens_put_a_metric_matched_fallback_after_geist(self) -> None:
        for name in ("font-display", "font-serif", "font-sans"):
            with self.subTest(token=name):
                self.assertTrue(self._token(name).startswith('"Geist", "Geist Fallback",'))
        mono = self._token("font-mono")
        self.assertTrue(mono.startswith('"Geist Mono", "Geist Mono Fallback",'))
        # A custom property that names itself is invalid at computed value
        # time, which silently dropped Geist Mono from every data label.
        self.assertNotIn("var(--font-mono)", mono)
        self.assertIn("monospace", mono)

    def test_fallback_faces_are_local_and_size_adjusted(self) -> None:
        for family in ("Geist Fallback", "Geist Mono Fallback"):
            with self.subTest(family=family):
                block = self.css.split(f'font-family: "{family}";', 1)[1].split("}", 1)[0]
                self.assertIn("src: local(", block)
                for descriptor in ("size-adjust", "ascent-override", "descent-override"):
                    self.assertIn(descriptor, block)

    def test_every_page_preloads_both_fonts_before_the_stylesheet(self) -> None:
        sources = {name: (ROOT / "web" / name).read_text(encoding="utf-8") for name in SHELLS}
        sources["ko/index.html"] = (ROOT / "web" / "ko" / "index.html").read_text(encoding="utf-8")
        sources["render template"] = Path(render.__file__).read_text(encoding="utf-8")
        for name, text in sources.items():
            stylesheet = text.index('href="/site-chrome.css')
            for font in ("Geist-Variable.woff2", "GeistMono-Variable.woff2"):
                with self.subTest(page=name, font=font):
                    tag = f'<link rel="preload" href="/fonts/{font}" as="font" type="font/woff2" crossorigin />'
                    self.assertIn(tag, text)
                    self.assertLess(text.index(tag), stylesheet)


class BroadsheetThemeTest(unittest.TestCase):
    """One palette and type system for every page, owned by site-chrome.css."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        cls.light = _theme_block(cls.css, ':root,\nhtml[data-theme="light"]')
        cls.dark = _theme_block(cls.css, 'html[data-theme="dark"]')

    def test_site_chrome_defines_both_themes_and_type(self) -> None:
        for token in SHARED_TOKENS:
            with self.subTest(token=token):
                self.assertIn(token, self.light)
                self.assertIn(token, self.dark)
        for token in ("font-display", "font-serif", "font-sans"):
            self.assertIn(token, self.light)

    def test_text_tokens_hold_contrast_in_both_themes(self) -> None:
        for name, theme in (("light", self.light), ("dark", self.dark)):
            for fg in ("fg", "muted", "accent", "brief-ink"):
                for bg in ("bg", "card", "brief-wash"):
                    with self.subTest(theme=name, fg=fg, bg=bg):
                        self.assertGreaterEqual(_contrast(theme[fg], theme[bg]), 4.5)

    def test_pages_do_not_redefine_shared_tokens(self) -> None:
        # A page-local --bg/--accent would silently fork the palette again.
        pattern = re.compile(r"--(?:%s)\s*:" % "|".join(re.escape(t) for t in SHARED_TOKENS))
        for rel in THEMED_SOURCES:
            with self.subTest(source=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIsNone(pattern.search(text), pattern.search(text) and text[pattern.search(text).start() - 80 : pattern.search(text).end() + 20])
                self.assertNotIn('"Avenir Next Condensed"', text)

    def test_browser_theme_color_follows_the_palette(self) -> None:
        # The mobile browser bar tints with <meta name="theme-color">.
        for rel in THEMED_SOURCES:
            if not rel.endswith((".html", ".py")):
                continue
            text = (ROOT / rel).read_text(encoding="utf-8")
            if 'name="theme-color"' not in text:
                continue
            with self.subTest(source=rel):
                self.assertIn(f'name="theme-color" content="{self.light["bg"]}" media="(prefers-color-scheme: light)"', text)
                self.assertIn(f'name="theme-color" content="{self.dark["bg"]}" media="(prefers-color-scheme: dark)"', text)

    def test_feeds_load_front_page_css_after_their_inline_styles(self) -> None:
        for rel in ("web/index.html", "web/ko/index.html"):
            with self.subTest(source=rel):
                head = (ROOT / rel).read_text(encoding="utf-8").split("</head>", 1)[0]
                self.assertIn("/front-page.css", head)
                self.assertGreater(head.index("/front-page.css"), head.rindex("</style>"))


if __name__ == "__main__":
    unittest.main()


class UiGlitchRegressionTest(unittest.TestCase):
    """Pins the 2026-11-07 screenshot sweep fixes (decision log)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.chrome = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        cls.front = (ROOT / "web" / "front-page.css").read_text(encoding="utf-8")

    def test_every_select_keeps_its_chevron(self) -> None:
        # Page rules use the `background` shorthand, which erases the chevron;
        # this longhand rule outranks them.
        block = self.chrome.split('html:not([data-ui-base="none"]) select:not([multiple]):not([size]) {', 1)[1].split("}", 1)[0]
        self.assertIn("background-image:", block)
        self.assertIn("padding-inline-end:", block)

    def test_weekly_recap_styles_the_explainer_video(self) -> None:
        self.assertIn(".video-frame", render.WEEKLY_RECAP_CSS)
        self.assertIn(".video-frame", render.DAILY_RECAP_CSS)

    def test_storyline_paragraph_rules_skip_the_labels(self) -> None:
        src = Path(render.__file__).read_text(encoding="utf-8")
        self.assertNotIn(".sl-latest p:last-child", src)
        self.assertIn(".sl-latest > p:last-child", src)

    def test_feed_modules_and_storyline_badge_on_phones(self) -> None:
        self.assertIn("#list > .model-radar-inline { margin:1rem 0; }", self.front)
        self.assertIn("a.badge-storyline::before { content:none; }", self.front)

    def test_cta_note_clears_the_subscribe_button(self) -> None:
        self.assertIn(".subscribe-cta .subscribe-inline-note {\n  margin-top: 0.5rem;", self.chrome)

    def test_updates_theme_toggle_uses_the_shared_icons(self) -> None:
        html = (ROOT / "web" / "updates.html").read_text(encoding="utf-8")
        self.assertNotIn("◐", html)
        self.assertIn("'☀️' : '🌙'", html)
