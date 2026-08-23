from __future__ import annotations

import unittest
from pathlib import Path

from pipeline import render_static_pages as render


ROOT = Path(__file__).resolve().parents[1]
VIEWPORT_POLICY = 'content="width=device-width, initial-scale=1.0"'


def _shell_pages() -> list[Path]:
    """Every hand-authored page shell, including the localized ones.

    Discovered rather than enumerated: a hard-coded list of ``web/*.html``
    silently skipped ``web/ko/playbook.html`` (hand-committed, written by no
    renderer), which kept the zoom lock after the site-wide unlock. Locale
    shells live at ``web/<locale>/*.html``; everything deeper is renderer
    output covered by ``test_generated_pages_allow_pinch_zoom`` instead.
    """
    web = ROOT / "web"
    locales = sorted(p.name for p in (ROOT / "data" / "i18n").iterdir() if p.is_dir())
    pages = list(web.glob("*.html"))
    for locale in locales:
        pages.extend((web / locale).glob("*.html"))
    return sorted(pages)


class ViewportPolicyTest(unittest.TestCase):
    def test_hand_authored_pages_allow_pinch_zoom(self) -> None:
        pages = _shell_pages()
        self.assertGreater(len(pages), 10)
        for path in pages:
            with self.subTest(page=str(path.relative_to(ROOT))):
                html = path.read_text(encoding="utf-8")
                self.assertIn(VIEWPORT_POLICY, html)
                self.assertNotIn("user-scalable", html)

    def test_generated_pages_allow_pinch_zoom(self) -> None:
        head = render.render_head(
            title="Example",
            description="Example page",
            canonical="https://www.llm-digest.com/example",
            published=None,
        )
        redirect = render.render_redirect_page(
            "https://www.llm-digest.com",
            "old-thread",
            "current-thread",
        )

        self.assertIn(VIEWPORT_POLICY, head)
        self.assertIn(VIEWPORT_POLICY, redirect)

    def test_share_fallback_allows_pinch_zoom(self) -> None:
        source = (ROOT / "api" / "share.js").read_text(encoding="utf-8")
        self.assertIn(VIEWPORT_POLICY, source)


if __name__ == "__main__":
    unittest.main()
