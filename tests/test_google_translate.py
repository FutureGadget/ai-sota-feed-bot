"""Tests for pipeline/google_translate.py — glossary protection and field extraction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import google_translate as gt


class TestGlossary(unittest.TestCase):
    """Test glossary loading and term protection."""

    def setUp(self):
        gt._glossary_cache = None

    def tearDown(self):
        gt._glossary_cache = None

    def test_glossary_loads(self):
        terms = gt._load_glossary()
        self.assertIsInstance(terms, list)
        self.assertGreater(len(terms), 0)
        # Should be sorted longest-first
        for i in range(len(terms) - 1):
            self.assertGreaterEqual(len(terms[i]), len(terms[i + 1]))

    def test_protect_known_terms(self):
        text = "OpenAI released GPT-4o with RAG support"
        protected = gt.protect_terms(text)
        self.assertIn('<span class="notranslate">OpenAI</span>', protected)
        self.assertIn('<span class="notranslate">GPT-4o</span>', protected)
        self.assertIn('<span class="notranslate">RAG</span>', protected)

    def test_protect_preserves_plain_text(self):
        text = "This is a normal sentence with no special terms."
        protected = gt.protect_terms(text)
        # No notranslate wrappers for non-glossary text
        self.assertNotIn("notranslate", protected)

    def test_unprotect_strips_spans(self):
        text = '<span class="notranslate">OpenAI</span> is great'
        clean = gt.unprotect_terms(text)
        self.assertEqual(clean, "OpenAI is great")

    def test_roundtrip(self):
        original = "Claude by Anthropic uses RLHF"
        protected = gt.protect_terms(original)
        restored = gt.unprotect_terms(protected)
        self.assertEqual(restored, original)


class TestParsePath(unittest.TestCase):
    """Test field path parsing."""

    def test_simple(self):
        self.assertEqual(gt._parse_path("title"), ["title"])

    def test_nested(self):
        self.assertEqual(
            gt._parse_path("categories[].name"),
            ["categories", "[]", "name"],
        )

    def test_deep_nested(self):
        self.assertEqual(
            gt._parse_path("categories[].articles[].title"),
            ["categories", "[]", "articles", "[]", "title"],
        )


class TestCollectStrings(unittest.TestCase):
    """Test string collection from nested structures."""

    def test_simple_field(self):
        source = {"title": "Hello", "url": "https://example.com"}
        entries = []
        gt._collect_strings(source, ["title"], [], entries)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], (["title"], "Hello"))

    def test_array_field(self):
        source = {
            "categories": [
                {"name": "AI", "slug": "ai"},
                {"name": "ML", "slug": "ml"},
            ]
        }
        entries = []
        gt._collect_strings(
            source, ["categories", "[]", "name"], [], entries
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0], (["categories", 0, "name"], "AI"))
        self.assertEqual(entries[1], (["categories", 1, "name"], "ML"))

    def test_nested_array_field(self):
        source = {
            "categories": [
                {
                    "name": "AI",
                    "articles": [
                        {"title": "Article 1"},
                        {"title": "Article 2"},
                    ],
                }
            ]
        }
        entries = []
        gt._collect_strings(
            source,
            ["categories", "[]", "articles", "[]", "title"],
            [],
            entries,
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(
            entries[0],
            (["categories", 0, "articles", 0, "title"], "Article 1"),
        )

    def test_missing_field_skipped(self):
        source = {"other": "value"}
        entries = []
        gt._collect_strings(source, ["title"], [], entries)
        self.assertEqual(len(entries), 0)

    def test_empty_string_skipped(self):
        source = {"title": "  "}
        entries = []
        gt._collect_strings(source, ["title"], [], entries)
        self.assertEqual(len(entries), 0)


class TestSetAtAddress(unittest.TestCase):
    """Test setting values at nested addresses."""

    def test_simple(self):
        root = {}
        gt._set_at_address(root, ["title"], "Hello")
        self.assertEqual(root, {"title": "Hello"})

    def test_nested(self):
        root = {}
        gt._set_at_address(root, ["categories", 0, "name"], "AI")
        self.assertEqual(root, {"categories": [{"name": "AI"}]})

    def test_deep_nested(self):
        root = {}
        gt._set_at_address(
            root, ["categories", 0, "articles", 1, "title"], "Article 2"
        )
        expected = {"categories": [{"articles": [{}, {"title": "Article 2"}]}]}
        self.assertEqual(root, expected)


class TestTranslateFields(unittest.TestCase):
    """Test field-level translation (with mocked API)."""

    @patch("google_translate.translate_texts")
    def test_simple_fields(self, mock_translate):
        mock_translate.return_value = ["제목", "설명"]
        source = {"title": "Title", "description": "Description", "url": "https://ex.com"}
        result = gt.translate_fields(
            source, ["title", "description"], "ko", api_key="fake"
        )
        self.assertEqual(result["title"], "제목")
        self.assertEqual(result["description"], "설명")
        # url should not be in result (not in field_paths)
        self.assertNotIn("url", result)

    @patch("google_translate.translate_texts")
    def test_array_fields(self, mock_translate):
        mock_translate.return_value = ["카테고리1", "기사1", "기사2"]
        source = {
            "categories": [
                {
                    "name": "Category 1",
                    "articles": [
                        {"title": "Article 1"},
                        {"title": "Article 2"},
                    ],
                }
            ]
        }
        result = gt.translate_fields(
            source,
            ["categories[].name", "categories[].articles[].title"],
            "ko",
            api_key="fake",
        )
        self.assertEqual(result["categories"][0]["name"], "카테고리1")
        self.assertEqual(result["categories"][0]["articles"][0]["title"], "기사1")
        self.assertEqual(result["categories"][0]["articles"][1]["title"], "기사2")

    @patch("google_translate.translate_texts")
    def test_empty_source(self, mock_translate):
        result = gt.translate_fields({}, ["title"], "ko", api_key="fake")
        self.assertEqual(result, {})
        mock_translate.assert_not_called()


class TestTranslateTexts(unittest.TestCase):
    """Test the translate_texts function with mocked HTTP."""

    def test_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ConnectionError):
                gt.translate_texts(["hello"], "ko")

    def test_empty_input(self):
        result = gt.translate_texts([], "ko", api_key="fake")
        self.assertEqual(result, [])

    @patch("google_translate.urllib.request.urlopen")
    def test_successful_call(self, mock_urlopen):
        response_body = {
            "data": {
                "translations": [
                    {"translatedText": "안녕하세요"}
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            __import__("json").dumps(response_body).encode("utf-8")
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = gt.translate_texts(["hello"], "ko", api_key="test-key")
        self.assertEqual(result, ["안녕하세요"])

    @patch("google_translate.urllib.request.urlopen")
    def test_html_entity_decoding(self, mock_urlopen):
        response_body = {
            "data": {
                "translations": [
                    {"translatedText": "Tom &amp; Jerry&#39;s &quot;show&quot;"}
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            __import__("json").dumps(response_body).encode("utf-8")
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = gt.translate_texts(["Tom & Jerry's \"show\""], "ko", api_key="test-key")
        self.assertEqual(result, ["Tom & Jerry's \"show\""])

    @patch("google_translate.urllib.request.urlopen")
    @patch("time.sleep")
    def test_transient_error_retry(self, mock_sleep, mock_urlopen):
        import json
        import io
        from urllib.error import HTTPError
        fp = io.BytesIO(b"Rate Limit")
        exc = HTTPError("https://translation.googleapis.com", 429, "Too Many Requests", {}, fp)
        
        response_body = {
            "data": {
                "translations": [
                    {"translatedText": "안녕하세요"}
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_body).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        
        # 1st call fails with 429, 2nd call succeeds
        mock_urlopen.side_effect = [exc, mock_resp]
        
        result = gt.translate_texts(["hello"], "ko", api_key="test-key")
        self.assertEqual(result, ["안녕하세요"])
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("google_translate.urllib.request.urlopen")
    @patch("time.sleep")
    def test_network_error_retry(self, mock_sleep, mock_urlopen):
        import json
        from urllib.error import URLError
        exc = URLError("DNS lookup failed")
        
        response_body = {
            "data": {
                "translations": [
                    {"translatedText": "안녕하세요"}
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_body).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        
        # 1st call fails with URLError, 2nd call succeeds
        mock_urlopen.side_effect = [exc, mock_resp]
        
        result = gt.translate_texts(["hello"], "ko", api_key="test-key")
        self.assertEqual(result, ["안녕하세요"])
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("google_translate.urllib.request.urlopen")
    def test_html_safety_escaping(self, mock_urlopen):
        import json
        # When input has "<3" and "&", it should be escaped to "&lt;3" and "&amp;" before API call
        def side_effect(req, timeout=30):
            # Inspect payload
            data = json.loads(req.data.decode("utf-8"))
            texts = data["q"]
            self.assertEqual(texts[0], "love &lt;3 &amp; <span class=\"notranslate\">OpenAI</span>")
            
            response_body = {
                "data": {
                    "translations": [
                        {"translatedText": "사랑 &lt;3 &amp; <span class=\"notranslate\">OpenAI</span>"}
                    ]
                }
            }
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(response_body).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        mock_urlopen.side_effect = side_effect
        result = gt.translate_texts(["love <3 & OpenAI"], "ko", api_key="test-key")
        # Should decode back to original characters
        self.assertEqual(result, ["사랑 <3 & OpenAI"])


if __name__ == "__main__":
    unittest.main()
