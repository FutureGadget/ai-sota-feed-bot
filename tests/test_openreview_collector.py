from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "collectors"))

import collect  # noqa: E402


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _fixture(name: str) -> dict:
    path = ROOT / "tests" / "fixtures" / "openreview" / name
    return json.loads(path.read_text(encoding="utf-8"))


class OpenReviewVenueCollectionTest(unittest.TestCase):
    def test_iclr_source_is_configured_and_mapped_to_research_watch(self) -> None:
        sources = yaml.safe_load(
            (ROOT / "config" / "sources.yaml").read_text(encoding="utf-8")
        )["sources"]
        source = next(source for source in sources if source["name"] == "openreview_iclr_accepted")
        self.assertEqual(source["type"], "openreview_venue")
        self.assertEqual(source["venue_id"], "ICLR.cc/2026/Conference")
        self.assertTrue(source["accepted_only"])

        for path in (ROOT / "config" / "ranking.yaml", ROOT / "config" / "presets" / "balanced.yaml"):
            config = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIn("openreview_iclr_accepted", config["slots"]["research_watch"]["sources"])
            self.assertIn("openreview_iclr_accepted", config["source_bias"])

    def test_collects_public_acceptances_and_uses_decision_timestamp(self) -> None:
        source = {
            "name": "openreview_iclr_accepted",
            "type": "openreview_venue",
            "venue_id": "ICLR.cc/2026/Conference",
            "accepted_only": True,
            "max_results": 100,
        }
        now = datetime(2026, 10, 10, tzinfo=timezone.utc)

        with patch.object(
            collect.urllib.request,
            "urlopen",
            return_value=FakeResponse(_fixture("accepted_page_1.json")),
        ):
            items = collect.collect_from_openreview_venue(source, now)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Reliable Tool Use for Agent Systems")
        self.assertEqual(items[0]["summary"], "A practical study of tool-use reliability.")
        self.assertEqual(items[0]["url"], "https://openreview.net/forum?id=forum-accepted")
        self.assertEqual(items[0]["published"], "2025-10-09T14:20:00+00:00")

    def test_paginates_and_accepts_scalar_content_values(self) -> None:
        source = {
            "name": "openreview_iclr_accepted",
            "type": "openreview_venue",
            "venue_id": "ICLR.cc/2026/Conference",
            "accepted_only": True,
            "max_results": 2,
            "page_size": 1,
        }
        now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        calls = []

        def fake_urlopen(request, timeout=0):
            query = parse_qs(urlparse(request.full_url).query)
            calls.append(query)
            offset = int(query["offset"][0])
            if offset == 0:
                first_page = _fixture("accepted_page_1.json")
                payload = {"count": 6, "notes": first_page["notes"][:1]}
            else:
                payload = _fixture("accepted_page_2.json")
            return FakeResponse(payload)

        with patch.object(collect.urllib.request, "urlopen", side_effect=fake_urlopen):
            items = collect.collect_from_openreview_venue(source, now)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[1]["title"], "Accepted on the second page")
        self.assertEqual(items[1]["published"], "2026-10-09T12:00:00+00:00")
        self.assertEqual([int(query["offset"][0]) for query in calls], [0, 1])
        self.assertEqual(calls[0]["invitation"], ["ICLR.cc/2026/Conference/-/Submission"])
        self.assertEqual(calls[0]["details"], ["directReplies"])

    def test_accepts_public_venueid_when_decision_reply_is_not_returned(self) -> None:
        payload = _fixture("accepted_page_1.json")
        payload["notes"][0].pop("details")
        payload["notes"][0]["pdate"] = 1760019600000
        source = {
            "name": "openreview_iclr_accepted",
            "type": "openreview_venue",
            "venue_id": "ICLR.cc/2026/Conference",
            "accepted_only": True,
            "max_results": 100,
        }

        with patch.object(
            collect.urllib.request,
            "urlopen",
            return_value=FakeResponse(payload),
        ):
            items = collect.collect_from_openreview_venue(
                source, datetime(2026, 10, 10, tzinfo=timezone.utc)
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["published"], "2025-10-09T14:20:00+00:00")

    def test_requires_venue_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "venue_id"):
            collect.collect_from_openreview_venue({"name": "missing"}, datetime.now(timezone.utc))

    def test_rejects_malformed_api_response(self) -> None:
        with patch.object(
            collect.urllib.request,
            "urlopen",
            return_value=FakeResponse(_fixture("malformed.json")),
        ):
            with self.assertRaisesRegex(ValueError, "unexpected API response shape"):
                collect.collect_from_openreview_venue(
                    {
                        "name": "openreview_iclr_accepted",
                        "venue_id": "ICLR.cc/2026/Conference",
                    },
                    datetime.now(timezone.utc),
                )


if __name__ == "__main__":
    unittest.main()
