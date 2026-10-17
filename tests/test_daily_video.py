from __future__ import annotations

import base64
import io
import sys
import unittest
import wave
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import build_daily_video as bdv  # noqa: E402

RECAP = {
    "date": "2026-10-16",
    "title": "What happened in AI — Oct 16, 2026",
    "intro": ["One.", "Two."],
    "highlights": ["Headline A.", "Headline B."],
    "categories": [
        {"name": "Cat A", "summary": "Sum A.", "articles": [{"title": f"T{i}"} for i in range(5)]},
        {"name": "Empty", "summary": "x", "articles": []},
    ],
}


def _wav(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(bdv.SAMPLE_RATE)
        w.writeframes(b"\x00\x00" * int(seconds * bdv.SAMPLE_RATE))
    return buf.getvalue()


class DailyVideoTest(unittest.TestCase):
    def test_scenes_open_highlights_category_close(self) -> None:
        scenes = bdv.build_scenes(RECAP)
        self.assertEqual([s["kind"] for s in scenes], ["open", "highlights", "category", "close"])
        self.assertIn("Friday, October 16", scenes[0]["narration"])
        cat = scenes[2]
        self.assertEqual(len(cat["bullets"]), bdv.MAX_CATEGORY_ARTICLES + 1)
        self.assertEqual(cat["bullets"][-1], "+2 more in the full brief")

    def test_silent_scene_timing_and_vtt(self) -> None:
        scenes = bdv.build_scenes(RECAP)
        for s in scenes:
            s["pcm"] = b""
            self.assertGreaterEqual(bdv.scene_seconds(s), bdv.MIN_SCENE_SECONDS)
        self.assertEqual(bdv._ts(3661.5), "01:01:01.500")

    def test_synthesize_decodes_wav(self) -> None:
        body = {"steps": [{"type": "model_output", "content": [{"type": "audio", "data": base64.b64encode(_wav(1.0)).decode()}]}]}
        resp = mock.Mock(status_code=200, json=lambda: body)
        resp.raise_for_status = lambda: None
        with mock.patch.object(bdv.requests, "post", return_value=resp) as post:
            pcm = bdv.synthesize("hi", "key")
        self.assertEqual(len(pcm), bdv.SAMPLE_RATE * 2)
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "key")

    def test_quota_failure_stops_calls_and_stays_silent(self) -> None:
        scenes = bdv.build_scenes(RECAP)
        err = requests.HTTPError(response=mock.Mock(status_code=429))
        with mock.patch.object(bdv, "synthesize", side_effect=err) as syn, mock.patch.object(bdv.time, "sleep"):
            bdv.narrate(scenes, "key")
        self.assertEqual(syn.call_count, 1)
        self.assertTrue(all(s["pcm"] == b"" for s in scenes))

    def test_no_key_makes_no_requests(self) -> None:
        scenes = bdv.build_scenes(RECAP)
        with mock.patch.object(bdv, "synthesize") as syn:
            bdv.narrate(scenes, None)
        syn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
