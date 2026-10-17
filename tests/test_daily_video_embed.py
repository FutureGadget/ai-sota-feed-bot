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
_wspec = importlib.util.spec_from_file_location(
    "weekly_common", ROOT / ".agents" / "skills" / "weekly-summary" / "scripts" / "weekly_common.py"
)
weekly_common = importlib.util.module_from_spec(_wspec)
_wspec.loader.exec_module(weekly_common)

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

    def test_section_has_video_anchor(self) -> None:
        html = render.render_video({"video": {"youtube_id": "KNEGLmDOnLc"}})
        self.assertIn('id="video"', html)

    def test_bad_id_renders_nothing(self) -> None:
        self.assertEqual(render.render_video(recap({"youtube_id": 'x"><script>'})), "")

    def test_validation(self) -> None:
        self.assertEqual(daily_common.validate_recap(recap({"youtube_id": VID})), [])
        self.assertTrue(daily_common.validate_recap(recap({"youtube_id": "short"})))
        self.assertTrue(daily_common.validate_recap(recap("nope")))

    def test_shell_supports_video(self) -> None:
        html = (ROOT / "web" / "daily.html").read_text(encoding="utf-8")
        self.assertIn("renderVideo(recap)", html)


def weekly_recap(video=None) -> dict:
    data = {
        "week": "2026-W42", "start": "2026-10-10", "end": "2026-10-16", "title": "t",
        "categories": [{"name": "c", "articles": [{"title": "a", "url": "https://example.com"}]}],
    }
    if video is not None:
        data["video"] = video
    return data


class WeeklyVideoEmbedTest(unittest.TestCase):
    def test_no_video_renders_nothing(self) -> None:
        self.assertEqual(render.render_video(weekly_recap(), "weekly"), "")

    def test_weekly_copy_anchor_and_tracking(self) -> None:
        html = render.render_video(weekly_recap({"youtube_id": VID, "duration_s": 165}), "weekly")
        self.assertIn('id="video"', html)
        self.assertIn("stories connect, in 2:45", html)
        self.assertIn("Weekly explainer video", html)
        self.assertIn('data-track="weekly-video"', html)

    def test_daily_copy_is_unchanged(self) -> None:
        html = render.render_video(recap({"youtube_id": VID}))
        self.assertIn("stories work", html)
        self.assertIn('data-track="daily-video"', html)

    def test_weekly_validation(self) -> None:
        self.assertEqual(weekly_common.validate_recap(weekly_recap({"youtube_id": VID})), [])
        self.assertEqual(weekly_common.validate_recap(weekly_recap()), [])
        self.assertTrue(weekly_common.validate_recap(weekly_recap({"youtube_id": "short"})))
        self.assertTrue(weekly_common.validate_recap(weekly_recap("nope")))

    def test_weekly_shell_supports_video(self) -> None:
        html = (ROOT / "web" / "weekly.html").read_text(encoding="utf-8")
        self.assertIn("renderVideo(recap)", html)
        self.assertIn('id="video"', html)
        self.assertEqual(html.count("youtube-nocookie.com/embed/"), 1)


if __name__ == "__main__":
    unittest.main()
