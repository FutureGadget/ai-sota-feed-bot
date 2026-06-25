from __future__ import annotations

import unittest

from publish import publish_email as email


class DailyEmailRenderingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = {
            "provider": "resend",
            "site_base": "https://www.llm-digest.com",
            "utm_source": "email",
        }
        self.recap = {
            "date": "2026-06-24",
            "intro": ["A concise lead."],
            "highlights": ["One useful thing happened."],
            "categories": [
                {
                    "name": "Hardening agents",
                    "summary": "Identity and isolation work moved forward.",
                    "articles": [
                        {
                            "title": "Agent identity access model",
                            "summary": "Agents get a governed identity.",
                            "source": "claude_blog",
                            "url": "https://example.com/agent-identity",
                        },
                        {
                            "title": "Hardware-isolated agent harness",
                            "summary": "Run agents as untrusted code.",
                            "source": "hackernews_ai",
                            "url": "https://example.com/harness",
                        },
                    ],
                },
                {
                    "name": "Coding-agent toolchain",
                    "summary": "Builder tooling keeps filling in.",
                    "articles": [
                        {
                            "title": "Declare agent config once",
                            "summary": "Sync one config across providers.",
                            "source": "hackernews_ai",
                            "url": "https://example.com/config",
                        }
                    ],
                },
            ],
        }

    def test_daily_email_has_visible_category_headers(self) -> None:
        _, body = email.render_daily(self.cfg, self.recap, [])

        self.assertIn("Theme 1 · 2 items", body)
        self.assertIn("Hardening agents", body)
        self.assertIn("Identity and isolation work moved forward.", body)
        self.assertLess(body.index("Hardening agents"), body.index("Agent identity access model"))
        self.assertIn("Theme 2 · 1 item", body)
        self.assertLess(body.index("Coding-agent toolchain"), body.index("Declare agent config once"))

    def test_daily_email_text_alternative_keeps_category_headers(self) -> None:
        _, body = email.render_daily(self.cfg, self.recap, [])
        text = email.html_to_text(body)

        self.assertIn("Theme 1 · 2 items", text)
        self.assertIn("Hardening agents", text)
        self.assertLess(text.index("Hardening agents"), text.index("Agent identity access model"))
        self.assertIn("Theme 2 · 1 item", text)
        self.assertLess(text.index("Coding-agent toolchain"), text.index("Declare agent config once"))


if __name__ == "__main__":
    unittest.main()
