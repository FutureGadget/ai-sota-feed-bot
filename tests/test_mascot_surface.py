from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MascotSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "web" / "mascot" / "mascot.js").read_text(encoding="utf-8")

    def test_right_anchor_keeps_css_safe_area_expression(self) -> None:
        self.assertIn(
            "calc(100% - ${opts.width}px - ${cssLen(opts.offsetX)})",
            self.source,
        )
        self.assertNotIn("const offsetXPx", self.source)

    def test_scroll_lifecycle_is_wired_before_the_first_appearance(self) -> None:
        self.assertIn("function wireLifecycleListeners()", self.source)
        start_at = self.source.index("function start()")
        wire_at = self.source.index("wireLifecycleListeners();", start_at)
        boot_at = self.source.index("const boot =", start_at)
        self.assertLess(wire_at, boot_at)

    def test_interactive_touch_devices_receive_direct_pointer_events(self) -> None:
        self.assertIn(
            "const HOVER_INTENT = opts.interactive && matchMedia('(hover: hover) and (pointer: fine)').matches;",
            self.source,
        )
        self.assertIn("const directPointer = opts.interactive && !HOVER_INTENT;", self.source)
        self.assertIn("`pointer-events:${directPointer ? 'auto' : 'none'}`", self.source)

    def test_interactive_mascot_is_keyboard_and_screen_reader_accessible(self) -> None:
        self.assertIn("container.removeAttribute('aria-hidden');", self.source)
        self.assertIn("canvas.setAttribute('role', 'button');", self.source)
        self.assertIn("canvas.setAttribute('tabindex', '0');", self.source)
        self.assertIn("canvas.addEventListener('keydown', onPokeKeydown);", self.source)
        self.assertIn("container.addEventListener('focusin', showDismiss);", self.source)
        self.assertIn("container.contains(document.activeElement)", self.source)

    def test_mascot_does_not_auto_hide_while_it_contains_focus(self) -> None:
        self.assertIn("const focusHeld = opts.interactive", self.source)
        self.assertIn("if (t - stateAt > dwell && !focusHeld)", self.source)
        self.assertIn("container.addEventListener('focusin', holdMascotForFocus);", self.source)

    def test_appear_now_bypasses_scroll_deferral(self) -> None:
        self.assertIn("async function appear({ deferForScroll = true } = {})", self.source)
        self.assertIn("if (deferForScroll && now() - lastScrollT < 1500)", self.source)
        self.assertIn("appear({ deferForScroll: false });", self.source)


if __name__ == "__main__":
    unittest.main()
