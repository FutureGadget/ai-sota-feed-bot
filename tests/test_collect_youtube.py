"""Unit tests for the youtube_channel collector (collectors/collect.py).

The network calls are mocked; the feed shapes are the real Atom / RSS shapes
(YouTube long-form playlist feed and a podcast feed with `podcast:transcript`).
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collectors"))

import collect  # noqa: E402

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)

PLAYLIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
  <title>Videos</title>
  <author><name>Test Channel</name></author>
  <entry>
    <yt:videoId>AAAAAAAAAAA</yt:videoId>
    <title>Episode One</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=AAAAAAAAAAA"/>
    <published>2026-10-28T10:00:00+00:00</published>
    <media:group><media:description>Video description one</media:description></media:group>
  </entry>
  <entry>
    <yt:videoId>BBBBBBBBBBB</yt:videoId>
    <title>Episode Two</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=BBBBBBBBBBB"/>
    <published>2026-10-27T10:00:00+00:00</published>
    <media:group><media:description>Video description two</media:description></media:group>
  </entry>
  <entry>
    <yt:videoId>DDDDDDDDDDD</yt:videoId>
    <title>Episode Three</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=DDDDDDDDDDD"/>
    <published>2026-10-26T10:00:00+00:00</published>
    <media:group><media:description>Video description three</media:description></media:group>
  </entry>
  <entry>
    <yt:videoId>CCCCCCCCCCC</yt:videoId>
    <title>A short clip</title>
    <link rel="alternate" href="https://www.youtube.com/shorts/CCCCCCCCCCC"/>
    <published>2026-10-29T10:00:00+00:00</published>
    <media:group><media:description>Watch the full episode</media:description></media:group>
  </entry>
</feed>
"""

PODCAST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Test Channel Podcast</title>
    <item>
      <title>Episode One</title>
      <itunes:duration>3600</itunes:duration>
      <description>Short teaser</description>
      <content:encoded><![CDATA[<p>Long show notes with the actual claims and chapters.</p>]]></content:encoded>
      <podcast:transcript url="https://example.com/ep1.vtt" type="text/vtt"/>
    </item>
    <item>
      <title>Episode Two</title>
      <itunes:duration>54:52</itunes:duration>
      <description>Another teaser</description>
      <podcast:transcript url="https://example.com/ep2.srt" type="application/x-subrip"/>
    </item>
  </channel>
</rss>
"""


def _source(**overrides):
    source = {
        "name": "test_channel",
        "type": "youtube_channel",
        "channel_id": "UC1234567890123456789012",
        "publisher_name": "Test Channel",
        "transcript_feed": "https://example.com/podcast.xml",
    }
    source.update(overrides)
    return source


class YoutubeUrlTest(unittest.TestCase):
    def test_extracts_all_common_forms(self) -> None:
        self.assertEqual(collect.youtube_video_id("https://youtu.be/AAAAAAAAAAA"), "AAAAAAAAAAA")
        self.assertEqual(collect.youtube_video_id("https://www.youtube.com/watch?v=AAAAAAAAAAA"), "AAAAAAAAAAA")
        self.assertEqual(collect.youtube_video_id("https://www.youtube.com/shorts/AAAAAAAAAAA"), "AAAAAAAAAAA")
        self.assertEqual(collect.youtube_video_id("https://www.youtube.com/embed/AAAAAAAAAAA"), "AAAAAAAAAAA")

    def test_rejects_non_video_urls(self) -> None:
        self.assertEqual(collect.youtube_video_id("https://www.youtube.com/@tessl-ai"), "")
        self.assertEqual(collect.youtube_video_id("https://example.com/watch?v=AAAAAAAAAAA"), "")

    def test_longform_playlist_id(self) -> None:
        self.assertEqual(
            collect.youtube_longform_playlist_id("UCg3pI4p6OKSFrDVZcwRIx8A"),
            "UULFg3pI4p6OKSFrDVZcwRIx8A",
        )
        self.assertEqual(collect.youtube_longform_playlist_id("not-a-channel"), "")


class TranscriptMapTest(unittest.TestCase):
    def test_parses_vtt_and_srt_transcripts(self) -> None:
        parsed = feedparser.parse(PODCAST_XML)
        by_title = {collect._normalize_match_title(e.title): e for e in parsed.entries}
        self.assertEqual(
            collect._podcast_transcript_url(by_title["episode one"]),
            "https://example.com/ep1.vtt",
        )
        self.assertEqual(
            collect._podcast_transcript_url(by_title["episode two"]),
            "https://example.com/ep2.srt",
        )

    def test_full_show_notes_beat_the_short_summary(self) -> None:
        parsed = feedparser.parse(PODCAST_XML)
        entry = parsed.entries[0]
        self.assertIn("Long show notes", collect._podcast_entry_description(entry))

    def test_duration_formats(self) -> None:
        parsed = feedparser.parse(PODCAST_XML)
        self.assertEqual(collect._podcast_duration_seconds(parsed.entries[0]), 3600)
        self.assertEqual(collect._podcast_duration_seconds(parsed.entries[1]), 3292)

    def test_normalizes_youtube_suffix_and_case(self) -> None:
        self.assertEqual(
            collect._normalize_match_title("Episode One | YouTube"),
            collect._normalize_match_title("episode one"),
        )


class YoutubeCollectorTest(unittest.TestCase):
    def _fetch(self, playlist_xml=PLAYLIST_XML, channel_xml=None):
        def fake_fetch(url: str, timeout: int = 15):
            if "transcript" in url or "example.com/podcast" in url:
                return feedparser.parse(PODCAST_XML)
            if "playlist_id" in url:
                return feedparser.parse(playlist_xml)
            if "channel_id" in url:
                return feedparser.parse(channel_xml or "")
            return feedparser.parse("")

        return fake_fetch

    def test_longform_playlist_skips_shorts_and_attaches_transcript(self) -> None:
        with patch.object(collect, "_fetch_feed", side_effect=self._fetch()):
            items = collect.collect_from_youtube_channel(_source(), NOW)

        self.assertEqual([item["url"] for item in items], [
            "https://youtu.be/AAAAAAAAAAA",
            "https://youtu.be/BBBBBBBBBBB",
            "https://youtu.be/DDDDDDDDDDD",
        ])
        first = items[0]
        self.assertEqual(first["title"], "Episode One")
        self.assertEqual(first["type"], "video")
        self.assertEqual(first["publisher_name"], "Test Channel")
        self.assertEqual(first["image_url"], "https://i.ytimg.com/vi/AAAAAAAAAAA/hq720.jpg")
        self.assertEqual(first["transcript_url"], "https://example.com/ep1.vtt")
        self.assertEqual(first["duration_s"], 3600)
        self.assertIn("Long show notes", first["summary"])
        self.assertNotIn("transcript_url", items[2])  # no matching podcast episode

    def test_channel_feed_fallback_still_skips_shorts(self) -> None:
        with patch.object(collect, "_fetch_feed", side_effect=self._fetch(playlist_xml="", channel_xml=PLAYLIST_XML)):
            items = collect.collect_from_youtube_channel(_source(), NOW)

        self.assertEqual([item["url"] for item in items], [
            "https://youtu.be/AAAAAAAAAAA",
            "https://youtu.be/BBBBBBBBBBB",
            "https://youtu.be/DDDDDDDDDDD",
        ])

    def test_include_shorts_opt_in(self) -> None:
        with patch.object(collect, "_fetch_feed", side_effect=self._fetch()):
            items = collect.collect_from_youtube_channel(_source(include_shorts=True), NOW)

        self.assertEqual(len(items), 4)
        self.assertIn("https://youtu.be/CCCCCCCCCCC", [item["url"] for item in items])

    def test_missing_transcript_feed_keeps_video_description(self) -> None:
        with patch.object(collect, "_fetch_feed", side_effect=self._fetch()):
            items = collect.collect_from_youtube_channel(_source(transcript_feed=""), NOW)

        self.assertFalse(any(item.get("transcript_url") for item in items))
        self.assertEqual(items[0]["summary"], "Video description one")


if __name__ == "__main__":
    unittest.main()
