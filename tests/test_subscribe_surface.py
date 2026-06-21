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

    def test_uses_shared_instrument_token_system(self) -> None:
        self.assertIn("--bg:#f5f7fa;", self.html)
        self.assertIn("--accent:#2457d6;", self.html)
        self.assertIn("--bg:#11151c;", self.html)  # dark
        self.assertIn('"Avenir Next Condensed"', self.html)
        self.assertIn("ui-monospace", self.html)

    def test_signup_panel_is_the_focal_action(self) -> None:
        # Accent-ruled washed panel (not a rounded card); accent-filled button.
        self.assertIn(".signup { margin:1.8rem 0 0; padding:1.35rem 1.4rem; border-left:3px solid var(--accent);", self.html)
        self.assertIn("background:var(--brief-wash)", self.html)
        self.assertIn('button[type="submit"], .external-signup {', self.html)
        self.assertIn("background:var(--accent); color:#fff;", self.html)

    def test_delivery_spec_replaces_generic_benefit_cards(self) -> None:
        self.assertIn('class="deliveries"', self.html)
        self.assertIn('class="delivery-when"', self.html)
        # The old three benefit cards are gone.
        self.assertNotIn('class="benefits"', self.html)
        self.assertNotIn('class="benefit"', self.html)
        # Sample links preview the real products.
        self.assertIn('class="sample" href="/daily"', self.html)
        self.assertIn('class="sample" href="/weekly"', self.html)

    def test_preserves_config_paths_and_form_behavior(self) -> None:
        # Provider-config fallback + external signup option.
        self.assertIn("/api/client-config", self.html)
        self.assertIn("email_subscribe_enabled", self.html)
        self.assertIn("email_signup_url", self.html)
        self.assertIn("safeExternalUrl", self.html)
        self.assertIn('class="external-signup"', self.html)
        # Form posts to the subscribe API; honeypot + validation intact.
        self.assertIn("/api/subscribe", self.html)
        self.assertIn('name="website" class="hp"', self.html)
        self.assertIn(r"/^[^\s@]+@[^\s@]+\.[^\s@]+$/", self.html)

    def test_preserves_status_states_and_storage_keys(self) -> None:
        self.assertIn("ai_feed_email_subscribed_v1", self.html)
        self.assertIn("ai_feed_subscribe_nudge_done_v1", self.html)
        self.assertIn('.message[data-state="ok"]', self.html)
        self.assertIn('.message[data-state="err"]', self.html)
        self.assertIn("Subscription is temporarily unavailable", self.html)
        self.assertIn("You’re subscribed", self.html)
        # Privacy / provider-owns-the-list copy stays.
        self.assertIn("stored by the email provider", self.html)
        self.assertIn("unsubscribe link", self.html)

    def test_quality_floor(self) -> None:
        self.assertIn("outline:3px solid color-mix(in srgb,var(--accent) 50%,transparent)", self.html)
        self.assertIn("@media (prefers-reduced-motion:reduce)", self.html)
        self.assertIn('id="themeToggle"', self.html)
        self.assertIn("min-height:50px", self.html)  # comfortable touch targets


if __name__ == "__main__":
    unittest.main()
