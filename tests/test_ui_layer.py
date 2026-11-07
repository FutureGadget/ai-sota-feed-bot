"""Contract for the Tailwind CSS v4 + Basecoat UI layer (web/ui.css).

See docs/design-docs/ui-framework-migration.md. web/ui.css is a committed build
output of ui/site.css; scripts/build_ui_css.mjs --check (CI) proves it fresh.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_SHELLS = (
    "index.html", "ko/index.html", "daily.html", "weekly.html", "storyline.html",
    "playbook.html", "playbook-lab.html", "voices.html", "models.html",
    "models-compare.html", "subscribe.html",
)
UTILITY_SHELLS = ("subscribe.html",)  # pages whose markup uses utility classes
UI_VERSION = "20261107-ui-base"


class UiLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "ui" / "site.css").read_text(encoding="utf-8")
        cls.built = (ROOT / "web" / "ui.css").read_text(encoding="utf-8")

    def test_build_is_pinned_and_scripted(self) -> None:
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        for name in ("tailwindcss", "@tailwindcss/cli", "basecoat-css"):
            with self.subTest(dep=name):
                self.assertRegex(pkg["devDependencies"][name], r"^\d+\.\d+\.\d+$")
        self.assertEqual(pkg["scripts"]["check:css"], "node scripts/build_ui_css.mjs --check")
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("npm run check:css", ci)

    def test_bundled_licenses_survive_minification(self) -> None:
        self.assertIn("/*! tailwindcss v4.3.4 | MIT License", self.built)
        self.assertIn("/*! basecoat-css v1.1.0 (lyra subset) | MIT License", self.built)

    def test_geist_is_self_hosted_and_staged(self) -> None:
        css = (ROOT / "web" / "site-chrome.css").read_text(encoding="utf-8")
        for font in ("Geist-Variable.woff2", "GeistMono-Variable.woff2"):
            with self.subTest(font=font):
                self.assertTrue((ROOT / "web" / "fonts" / font).is_file())
                self.assertIn(f'url("/fonts/{font}")', css)
        self.assertIn("font-display: swap", css)
        self.assertIn("OFL", (ROOT / "web" / "fonts" / "Geist-OFL.txt").read_text(encoding="utf-8"))
        build = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
        self.assertIn('"fonts"', build)

    def test_scans_only_listed_sources(self) -> None:
        # Auto-detection would scan ~8k generated pages and data/.
        for shell in UTILITY_SHELLS:
            self.assertIn(f'@source "../web/{shell}";', self.source)
        self.assertIn('@import "tailwindcss/utilities.css" layer(utilities) source(none);', self.source)

    def test_basecoat_base_tokens_never_override_the_palette(self) -> None:
        # Basecoat's base.css sets :root --accent/--muted/--card/--border to
        # neutral shadcn values; importing it would repaint every page.
        self.assertNotIn("basecoat-css/base", self.source)
        self.assertNotIn('@import "basecoat-css";', self.source)
        self.assertNotIn("oklch(1 0 0)", self.built)
        # shadcn's --accent/--muted mean surfaces; they are mapped to --ui-*.
        self.assertIn("--color-accent: var(--ui-accent);", self.source)
        self.assertIn("--color-muted: var(--ui-muted);", self.source)

    def test_dark_variant_follows_data_theme(self) -> None:
        self.assertIn('@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));', self.source)
        self.assertNotIn("html.dark", self.built)

    def test_component_subset_is_explicit(self) -> None:
        listed = json.loads((ROOT / "ui" / "basecoat-components.json").read_text(encoding="utf-8"))["components"]
        self.assertIn("button", listed)
        self.assertNotIn("sidebar", listed)
        self.assertNotIn(".sidebar", self.built)
        # Comparable to the Oat bundle it replaces (31.6 KB + 10.4 KB raw).
        self.assertLess(len(self.built.encode("utf-8")), 90_000)

    def test_quality_floor(self) -> None:
        self.assertIn("focus-visible:ring-3", self.source)
        self.assertIn('.btn[data-size="touch"]', self.source)
        self.assertIn("h-12", self.source)  # 48px touch targets
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.source)

    def test_migrated_shells_load_ui_css_instead_of_oat(self) -> None:
        for shell in UI_SHELLS:
            with self.subTest(shell=shell):
                html = (ROOT / "web" / shell).read_text(encoding="utf-8")
                self.assertNotIn("oat.min.css", html)
                self.assertNotIn("oat.min.js", html)
                ui = html.index(f'href="/ui.css?v={UI_VERSION}"')
                chrome = html.index('href="/site-chrome.css')
                # site-chrome.css (unlayered) loads after, so it keeps owning the theme.
                self.assertLess(ui, chrome)

    def test_render_template_loads_ui_css(self) -> None:
        render = (ROOT / "pipeline" / "render_static_pages.py").read_text(encoding="utf-8")
        self.assertIn(f'href="/ui.css?v={UI_VERSION}"', render)
        self.assertLess(render.index("/ui.css"), render.index("/site-chrome.css"))

    def test_element_defaults_replace_oat_and_allow_opt_out(self) -> None:
        # Pages were written on Oat's element base; ui/site.css restores it,
        # scoped so a utility-built page can opt out.
        scope = ':where(html:not([data-ui-base="none"]))'
        for sel in (" p {", " ul,", " button,", " table {", " details {", ' [role="alert"] {'):
            with self.subTest(selector=sel):
                self.assertIn(scope + sel, self.source)
        subscribe = (ROOT / "web" / "subscribe.html").read_text(encoding="utf-8")
        self.assertIn('data-ui-base="none"', subscribe)

    def test_preflight_keeps_hidden_overridable(self) -> None:
        # Tailwind's preflight hides [hidden] with !important, which beats the
        # chrome's deliberate always-visible controls; the build copies it
        # with a normal declaration.
        self.assertIn('@import "./generated/preflight.css" layer(base);', self.source)
        self.assertNotIn("display:none!important}", self.built.split("[hidden]", 1)[1][:80])

if __name__ == "__main__":
    unittest.main()
