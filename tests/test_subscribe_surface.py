from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SubscribeSurfaceTest(unittest.TestCase):
    """Structural guards for the redesigned /subscribe conversion utility.

    The page must keep the signup action unmistakable and preserve every data
    behavior (provider-config fallback, external signup, honeypot, validation,
    status states, local-storage keys, privacy copy). These assertions pin the
    visual hierarchy and that the conversion JS was not altered by the restyle.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "subscribe.html").read_text(encoding="utf-8")

    def test_uses_shared_broadsheet_tokens(self) -> None:
        # Broadsheet theme: palette comes from site-chrome.css; components and
        # utilities come from the Tailwind + Basecoat layer (ui/site.css).
        self.assertNotIn("--bg:", self.html)
        self.assertNotIn("--accent:", self.html)
        self.assertIn("/site-chrome.css", self.html)
        self.assertIn("/ui.css", self.html)
        self.assertNotIn("oat.min", self.html)
        self.assertIn("font-display", self.html)
        self.assertIn('class="kicker', self.html)

    def test_signup_panel_is_the_focal_action(self) -> None:
        # Accent-ruled washed panel (not a rounded card); accent-filled button.
        self.assertIn('class="signup card', self.html)
        self.assertIn("border-l-3 border-l-brand bg-wash", self.html)
        self.assertIn('<button type="submit" class="btn w-full sm:w-auto" data-size="touch">Subscribe</button>', self.html)
        self.assertIn('class="external-signup btn', self.html)

    def test_delivery_spec_replaces_generic_benefit_cards(self) -> None:
        self.assertIn('class="deliveries', self.html)
        self.assertIn('class="delivery-when', self.html)
        # The old three benefit cards are gone.
        self.assertNotIn('class="benefits"', self.html)
        self.assertNotIn('class="benefit"', self.html)
        # Sample links preview the real products.
        self.assertIn('href="/daily">See today', self.html)
        self.assertIn('href="/weekly">See this week', self.html)

    def test_preserves_config_paths_and_form_behavior(self) -> None:
        # Provider-config fallback + external signup option.
        self.assertIn("/api/client-config", self.html)
        self.assertIn("email_subscribe_enabled", self.html)
        self.assertIn("email_signup_url", self.html)
        self.assertIn("safeExternalUrl", self.html)
        self.assertIn('class="external-signup', self.html)
        # Form posts to the subscribe API; honeypot + validation intact.
        self.assertIn("/api/subscribe", self.html)
        self.assertIn('name="website" class="hp"', self.html)
        self.assertIn(".hp { position:absolute; left:-9999px;", self.html)
        self.assertIn(r"/^[^\s@]+@[^\s@]+\.[^\s@]+$/", self.html)

    def test_preserves_status_states_and_storage_keys(self) -> None:
        self.assertIn("ai_feed_email_subscribed_v1", self.html)
        self.assertIn("ai_feed_subscribe_nudge_done_v1", self.html)
        ui = (ROOT / "ui" / "site.css").read_text(encoding="utf-8")
        self.assertIn('.message[data-state="ok"]', ui)
        self.assertIn('.message[data-state="err"]', ui)
        self.assertIn('class="message" role="status"', self.html)
        self.assertIn("Subscription is temporarily unavailable", self.html)
        self.assertIn("You’re subscribed", self.html)
        # Privacy / provider-owns-the-list copy stays.
        self.assertIn("stored by the email provider", self.html)
        self.assertIn("unsubscribe link", self.html)

    def test_quality_floor(self) -> None:
        # 3px focus ring and 48px touch targets live in ui/site.css.
        self.assertIn('data-size="touch"', self.html)
        self.assertIn('id="themeToggle"', self.html)

    def test_success_event_attributes_skill_lab_without_email(self) -> None:
        self.assertIn("function subscribeAttribution()", self.html)
        self.assertIn("function captureSubscribeSuccess(weeklyOnly)", self.html)
        self.assertIn("'subscribe_success'", self.html)
        self.assertIn("cadence: weeklyOnly ? 'weekly' : 'both'", self.html)
        self.assertIn("ref: attribution.ref", self.html)
        self.assertIn("lab_id: attribution.labId", self.html)
        self.assertNotIn("'subscribe_success', { email", self.html)
        self.assertIn("captureSubscribeSuccess(weeklyOnly);", self.html)
        self.assertIn("function shouldRecordSubscribeSuccess(honeypot)", self.html)
        self.assertIn("if (shouldRecordSubscribeSuccess(honeypot))", self.html)

    def test_attribution_is_allowlisted_and_bounded(self) -> None:
        self.assertIn("const ALLOWED_SUBSCRIBE_REFS = new Set(['skill_lab']);", self.html)
        self.assertIn("/^lab-[a-z0-9][a-z0-9-]{0,76}$/", self.html)
        self.assertIn("subscribe_external_handoff", self.html)

    def test_attribution_is_sanitized_before_analytics_loads(self) -> None:
        sanitizer = self.html.index("function sanitizedSubscribePath(rawHref)")
        analytics = self.html.index('src="/posthog-client.js')

        self.assertLess(sanitizer, analytics)
        self.assertIn("window.history.replaceState", self.html)
        self.assertIn("const clean = new URLSearchParams();", self.html)


if __name__ == "__main__":
    unittest.main()
