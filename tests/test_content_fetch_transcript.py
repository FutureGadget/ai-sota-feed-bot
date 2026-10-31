"""Transcript parsing and video digest tests for content_fetch."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline import content_fetch

VTT = """WEBVTT

00:00:00.160 --> 00:00:04.000
<v SPEAKER_01>We shipped the inference cache.

00:00:04.240 --> 00:00:09.359
<v SPEAKER_02>It cut p95 latency in half.

00:00:09.599 --> 00:00:12.000
<v SPEAKER_01>Here is the failure mode.
"""

SRT = """1
00:00:00,160 --> 00:00:04,000
The first sentence.

2
00:00:04,240 --> 00:00:09,359
The second sentence.
"""


class ParseTranscriptTest(unittest.TestCase):
    def test_vtt_strips_cues_and_speaker_tags(self) -> None:
        text = content_fetch.parse_transcript(VTT, "https://example.com/ep.vtt")
        self.assertIn("We shipped the inference cache.", text)
        self.assertIn("It cut p95 latency in half.", text)
        self.assertNotIn("-->", text)
        self.assertNotIn("WEBVTT", text)
        self.assertNotIn("SPEAKER_01", text)

    def test_srt_strips_indices_and_timestamps(self) -> None:
        text = content_fetch.parse_transcript(SRT, "https://example.com/ep.srt")
        self.assertEqual(text, "The first sentence. The second sentence.")

    def test_json_segment_list(self) -> None:
        raw = '{"segments":[{"body":"one"},{"body":"two"},{"text":"three"}]}'
        text = content_fetch.parse_transcript(raw, "https://example.com/ep.json")
        self.assertEqual(text, "one two three")

    def test_html_is_stripped(self) -> None:
        text = content_fetch.parse_transcript("<p>Hello <b>world</b></p>", "https://example.com/ep")
        self.assertEqual(text, "Hello world")


class VideoDigestTest(unittest.TestCase):
    def test_short_transcript_is_kept_whole(self) -> None:
        digest = content_fetch.build_video_digest("A short episode.", "One two three.", 2500)
        self.assertIn("Show notes: A short episode.", digest)
        self.assertIn("Transcript: One two three.", digest)

    def test_long_transcript_is_sampled_across_the_whole_talk(self) -> None:
        transcript = " ".join(f"segment{i:02d} " + ("filler " * 120) for i in range(10))
        digest = content_fetch.build_video_digest("The host explains the mechanism.", transcript, 2500)
        self.assertLessEqual(len(digest), 2500)
        self.assertIn("Show notes:", digest)
        self.assertIn("Transcript (sampled):", digest)
        self.assertIn("segment05", digest)
        self.assertNotIn("segment00", digest)

    def test_empty_transcript_returns_show_notes_only(self) -> None:
        digest = content_fetch.build_video_digest("Show notes only.", "", 2500)
        self.assertEqual(digest, "Show notes: Show notes only.")


class VideoFetchTest(unittest.TestCase):
    def test_video_with_transcript_bypasses_the_800_char_summary_skip(self) -> None:
        item = {
            "source": "ai_native_dev",
            "type": "video",
            "url": "https://youtu.be/AAAAAAAAAAA",
            "summary": "x" * 1200,
            "transcript_url": "https://example.com/ep.vtt",
        }
        transcript = "real transcript content " * 80
        with (
            patch.object(content_fetch, "_load_transcript_cache", return_value={}),
            patch.object(content_fetch, "_save_transcript_cache"),
            patch.object(content_fetch, "fetch_transcript_text", return_value=transcript) as fetch,
        ):
            out = content_fetch.build_paragraph_map([item], max_chars=2500)
        self.assertIn(item["url"], out)
        self.assertIn("Show notes:", out[item["url"]])
        self.assertIn("transcript content", out[item["url"]])
        fetch.assert_called_once()

    def test_video_without_transcript_never_fetches_html(self) -> None:
        item = {
            "source": "ai_native_dev",
            "type": "video",
            "url": "https://youtu.be/BBBBBBBBBBB",
            "summary": "A video description.",
        }
        with (
            patch.object(content_fetch, "_load_transcript_cache", return_value={}),
            patch.object(content_fetch, "_save_transcript_cache"),
            patch.object(content_fetch, "fetch_paragraph_text", side_effect=AssertionError("must not fetch")),
        ):
            out = content_fetch.build_paragraph_map([item], max_chars=2500)
        self.assertEqual(out, {})

    def test_video_detection(self) -> None:
        self.assertTrue(content_fetch._is_video({"type": "video"}))
        self.assertTrue(content_fetch._is_video({"video_id": "AAAAAAAAAAA"}))
        self.assertFalse(content_fetch._is_video({"type": "news"}))


if __name__ == "__main__":
    unittest.main()
