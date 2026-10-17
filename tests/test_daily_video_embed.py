from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from pipeline import render_static_pages as render

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "daily_common", ROOT / ".agents" / "skills" / "daily-summary" / "scripts" / "daily_common.py"
)
daily_common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(daily_common)

VID = "xJtYHEhQ8NY"


def recap(video=None) -> dict:
    data = {
        "date": "2026-10-04",
        "title": "t",
        "categories": [{"name": "c", "articles": [{"title": "a", "url": "https://example.com"}]}],
    }
    if video is not None:
        data["video"] = video
    return data


class DailyVideoEmbedTest(unittest.TestCase):
    def test_no_video_renders_nothing(self) -> None:
        self.assertEqual(render.render_video(recap()), "")

    def test_valid_video_is_click_to_load(self) -> None:
        html = render.render_video(recap({"youtube_id": VID, "title": "T <x>", "duration_s": 107.8}))
        self.assertIn(f'data-video-id="{VID}"', html)
        self.assertIn("1:48", html)
        self.assertIn("T &lt;x&gt;", html)
        self.assertIn("youtube-nocookie.com/embed/", html)
        self.assertNotIn("<iframe src", html)  # iframe is created on click only

    def test_bad_id_renders_nothing(self) -> None:
        self.assertEqual(render.render_video(recap({"youtube_id": 'x"><script>'})), "")

    def test_validation(self) -> None:
        self.assertEqual(daily_common.validate_recap(recap({"youtube_id": VID})), [])
        self.assertTrue(daily_common.validate_recap(recap({"youtube_id": "short"})))
        self.assertTrue(daily_common.validate_recap(recap("nope")))

    def test_shell_supports_video(self) -> None:
        html = (ROOT / "web" / "daily.html").read_text(encoding="utf-8")
        self.assertIn("renderVideo(recap)", html)


if __name__ == "__main__":
    unittest.main()
