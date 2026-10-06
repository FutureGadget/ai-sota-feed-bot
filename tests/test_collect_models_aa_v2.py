"""Artificial Analysis v2 list endpoint: pagination, failure classes, and the
exit status that keeps /models from freezing quietly.

unittest-based so `python -m unittest discover` (the CI runner) executes it.
"""

import argparse
import contextlib
import io
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import collect_models as cm  # noqa: E402

BASE_URL = "https://artificialanalysis.ai/api/v2/language/models/free"


def _cfg(**aa_overrides) -> dict:
    aa = {"base_url": BASE_URL, "api_key_env": "AA_API_KEY", "max_pages": 5}
    aa.update(aa_overrides)
    return {"sources": {"artificial_analysis": aa}, "request_timeout_seconds": 5, "trust_env_proxies": False}


def _model(i: int) -> dict:
    """One model in the documented Free v2 shape."""
    return {
        "id": f"id-{i}",
        "name": f"Model {i} (high)",
        "slug": f"model-{i}",
        "release_date": "2026-09-01",
        "model_creator": {"id": "creator-1", "name": "OpenAI"},
        "evaluations": {
            "artificial_analysis_intelligence_index": 40.0 + i,
            "artificial_analysis_coding_index": 30.0 + i,
            "artificial_analysis_agentic_index": 20.0,
        },
        "artificial_analysis_intelligence_index_cost": {"total_cost": 20.0, "cost_per_task": {"total_cost": 0.1}},
        "pricing": {
            "price_1m_input_tokens": 1.0,
            "price_1m_output_tokens": 5.0,
            "price_1m_cache_hit_tokens": 0.1,
            "price_1m_cache_write_tokens": 1.25,
        },
        "performance": {"median_output_tokens_per_second": 123.45, "median_time_to_first_token_seconds": 0.5},
    }


def _page(page: int, models: list[dict], has_more: bool, total_pages: int = 2) -> dict:
    return {
        "tier": "free",
        "intelligence_index_version": 4.3,
        "pagination": {"page": page, "page_size": 200, "total_pages": total_pages, "has_more": has_more},
        "data": models,
    }


class FakeResponse:
    def __init__(self, status_code: int = 200, body=None, remaining: str = "97"):
        self.status_code = status_code
        self._body = body
        self.headers = {"X-RateLimit-Remaining": remaining}

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeGet:
    """Stand-in for cm._get_with_retry that serves responses in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, session, url, **kwargs):
        self.calls.append((url, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FetchAAModelsTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"AA_API_KEY": "test-key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _fetch(self, responses, **aa_overrides):
        fake = FakeGet(responses)
        with mock.patch.object(cm, "_get_with_retry", fake):
            result = cm.fetch_aa_models(_cfg(**aa_overrides))
        return result, fake

    def test_walks_every_page_until_has_more_is_false(self):
        result, fake = self._fetch(
            [
                FakeResponse(body=_page(1, [_model(1), _model(2)], has_more=True)),
                FakeResponse(body=_page(2, [_model(3)], has_more=False), remaining="95"),
            ]
        )
        self.assertIsNone(result["failure"])
        self.assertEqual([m["slug"] for m in result["models"]], ["model-1", "model-2", "model-3"])
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["tier"], "free")
        self.assertEqual(result["intelligence_index_version"], 4.3)
        self.assertEqual(result["ratelimit_remaining"], "95")
        urls = [url for url, _ in fake.calls]
        self.assertEqual(urls, [f"{BASE_URL}?page=1", f"{BASE_URL}?page=2"])
        _, kwargs = fake.calls[0]
        self.assertEqual(kwargs["headers"], {"x-api-key": "test-key"})
        self.assertNotIn(429, kwargs["retry_statuses"])

    def test_retired_endpoint_is_a_permanent_failure(self):
        result, _ = self._fetch([FakeResponse(status_code=410, body={"error": "Gone"})])
        self.assertIsNone(result["models"])
        self.assertEqual(result["failure"], "permanent")
        self.assertEqual(result["reason"], "http_410")

    def test_rejected_key_is_a_permanent_failure(self):
        for status in (401, 403, 404):
            result, _ = self._fetch([FakeResponse(status_code=status, body={"error": "x"})])
            self.assertEqual(result["failure"], "permanent", status)

    def test_quota_exhausted_is_transient(self):
        result, _ = self._fetch([FakeResponse(status_code=429, body={"error": "rate"})])
        self.assertEqual(result["failure"], "transient")
        self.assertIsNone(result["models"])

    def test_failure_on_a_later_page_returns_no_partial_catalog(self):
        result, _ = self._fetch(
            [
                FakeResponse(body=_page(1, [_model(1)], has_more=True)),
                FakeResponse(status_code=503, body={"error": "down"}),
            ]
        )
        self.assertIsNone(result["models"])
        self.assertEqual(result["failure"], "transient")
        self.assertEqual(result["pages"], 2)

    def test_network_error_is_transient(self):
        result, _ = self._fetch([requests.ConnectionError("boom")])
        self.assertEqual(result["failure"], "transient")
        self.assertEqual(result["reason"], "network_ConnectionError")

    def test_legacy_unpaginated_body_is_rejected(self):
        legacy = {"status": 200, "prompt_options": {}, "data": [_model(1)]}
        result, _ = self._fetch([FakeResponse(body=legacy)])
        self.assertIsNone(result["models"])
        self.assertEqual(result["failure"], "permanent")
        self.assertEqual(result["reason"], "unexpected_shape")

    def test_non_json_body_is_rejected(self):
        result, _ = self._fetch([FakeResponse(body=ValueError("not json"))])
        self.assertEqual(result["failure"], "permanent")
        self.assertEqual(result["reason"], "unexpected_shape")

    def test_replayed_page_is_rejected(self):
        # A server that ignores ?page= would echo page 1 forever; the guard
        # catches the replay even if it also echoes the requested page number.
        result, _ = self._fetch(
            [
                FakeResponse(body=_page(1, [_model(1)], has_more=True)),
                FakeResponse(body=_page(2, [_model(1)], has_more=True)),
            ]
        )
        self.assertIsNone(result["models"])
        self.assertEqual(result["reason"], "pagination_not_advancing")

    def test_page_cap_fails_instead_of_truncating(self):
        result, fake = self._fetch(
            [FakeResponse(body=_page(p, [_model(p)], has_more=True)) for p in (1, 2)],
            max_pages=2,
        )
        self.assertIsNone(result["models"])
        self.assertEqual(result["failure"], "permanent")
        self.assertEqual(result["reason"], "page_cap_exceeded")
        self.assertEqual(len(fake.calls), 2)

    def test_missing_key_makes_no_request(self):
        fake = FakeGet([])
        with mock.patch.dict(os.environ, {"AA_API_KEY": ""}), mock.patch.object(cm, "_get_with_retry", fake):
            result = cm.fetch_aa_models(_cfg())
        self.assertEqual(result["failure"], "missing_key")
        self.assertEqual(fake.calls, [])


class ClassifyAndParseTest(unittest.TestCase):
    def test_classify_aa_status(self):
        self.assertEqual(cm.classify_aa_status(429), "transient")
        self.assertEqual(cm.classify_aa_status(500), "transient")
        self.assertEqual(cm.classify_aa_status(503), "transient")
        for status in (400, 401, 403, 404, 410):
            self.assertEqual(cm.classify_aa_status(status), "permanent")

    def test_parse_aa_page_rejects_a_page_mismatch(self):
        with self.assertRaises(ValueError):
            cm.parse_aa_page(_page(1, [], has_more=False), requested_page=2)

    def test_parse_aa_page_requires_has_more(self):
        body = _page(1, [], has_more=False)
        del body["pagination"]["has_more"]
        with self.assertRaises(ValueError):
            cm.parse_aa_page(body, requested_page=1)


class FreeShapeIndexTest(unittest.TestCase):
    def test_free_shape_maps_without_unmapped_fields(self):
        idx, missing = cm.build_aa_index([_model(1)], ["gpqa", "tau2"])
        record = idx["model1"]
        self.assertEqual(record["organization"], "openai")
        self.assertEqual(record["median_output_tokens_per_second"], 123.45)
        self.assertEqual(record["aa_intelligence_index"], 41.0)
        self.assertEqual(record["benchmarks"], {})
        unmapped, known = cm.split_missing_aa_fields(missing)
        self.assertEqual(unmapped, set())
        self.assertIn("price_blended_per_1m", known)

    def test_multi_word_creator_name_becomes_a_slug(self):
        raw = _model(1)
        raw["model_creator"] = {"id": "c", "name": "Moonshot AI"}
        idx, _ = cm.build_aa_index([raw])
        self.assertEqual(idx["model1"]["organization"], "moonshot-ai")

    def test_legacy_creator_slug_is_unchanged(self):
        raw = _model(1)
        raw["model_creator"] = {"id": "c", "name": "China Mobile", "slug": "china-mobile"}
        idx, _ = cm.build_aa_index([raw])
        self.assertEqual(idx["model1"]["organization"], "china-mobile")

    def test_blend_is_computed_locally_when_free_tier_omits_it(self):
        idx, _ = cm.build_aa_index([_model(1)])
        row = dict(idx["model1"], joined_sources=["artificial_analysis"])
        out = cm.finalize_model(row)
        self.assertEqual(out["price_blended_per_1m"], 2.0)  # (3*1 + 5) / 4


class ExitCodeTest(unittest.TestCase):
    NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)

    def _code(self, **kwargs):
        defaults = dict(wrote=False, aa_failure=None, aa_reason=None, previous_output=None, now=self.NOW, max_age_hours=48)
        defaults.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = cm.collect_exit_code(**defaults)
        return code, out.getvalue()

    def _previous(self, hours_old: float) -> dict:
        return {"generated_at": (self.NOW - timedelta(hours=hours_old)).isoformat()}

    def test_permanent_aa_failure_is_red_even_with_fresh_data(self):
        code, out = self._code(aa_failure="permanent", aa_reason="http_410", previous_output=self._previous(6))
        self.assertEqual(code, 1)
        self.assertIn("reason=aa_permanent_error cause=http_410", out)

    def test_transient_skip_inside_the_window_stays_green(self):
        code, _ = self._code(aa_failure="transient", previous_output=self._previous(12))
        self.assertEqual(code, 0)

    def test_skip_that_leaves_stale_data_is_red(self):
        code, out = self._code(aa_failure="transient", previous_output=self._previous(49))
        self.assertEqual(code, 1)
        self.assertIn("reason=artifact_stale", out)

    def test_missing_key_skip_eventually_goes_red(self):
        code, _ = self._code(aa_failure="missing_key", previous_output=self._previous(60))
        self.assertEqual(code, 1)

    def test_skip_with_nothing_published_is_red(self):
        code, _ = self._code(previous_output=None)
        self.assertEqual(code, 1)

    def test_a_write_is_green(self):
        code, _ = self._code(wrote=True, previous_output=self._previous(500))
        self.assertEqual(code, 0)

    def test_age_check_can_be_disabled(self):
        code, _ = self._code(previous_output=self._previous(500), max_age_hours=0)
        self.assertEqual(code, 0)

    def test_naive_timestamp_is_read_as_utc(self):
        prev = {"generated_at": (self.NOW - timedelta(hours=3)).replace(tzinfo=None).isoformat()}
        self.assertAlmostEqual(cm.artifact_age_hours(prev, self.NOW), 3.0)
        self.assertIsNone(cm.artifact_age_hours({"generated_at": "garbage"}, self.NOW))


class CmdCollectTest(unittest.TestCase):
    """End to end with every network fetch stubbed."""

    NOW = datetime(2026, 11, 5, 2, 20, tzinfo=timezone.utc)

    def _run(self, aa_fetch: dict, previous: dict | None):
        saved = []
        lmarena_rows = {
            "overall": [
                {"model_name": "model-1", "organization": "openai", "license": "Proprietary",
                 "rating": 1400.0, "rank": 1, "vote_count": 100, "leaderboard_publish_date": "2026-11-01"}
            ],
            "coding": [],
        }
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(cm, "fetch_lmarena_rows", lambda cfg, cats: lmarena_rows))
            stack.enter_context(mock.patch.object(cm, "fetch_aa_models", lambda cfg: aa_fetch))
            stack.enter_context(mock.patch.object(cm, "fetch_first_party_releases", lambda cfg: []))
            stack.enter_context(mock.patch.object(cm, "fetch_deepswe_html", lambda cfg: None))
            stack.enter_context(mock.patch.object(cm, "load_output", lambda *a, **k: previous))
            stack.enter_context(mock.patch.object(cm, "save_output", lambda output, *a, **k: saved.append(output)))
            stack.enter_context(mock.patch.object(cm, "utc_now", lambda: self.NOW))
            out = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            code = cm.cmd_collect(argparse.Namespace())
        return code, saved, out.getvalue()

    def test_retired_endpoint_keeps_last_good_data_and_turns_red(self):
        previous = {
            "generated_at": "2026-11-04T20:20:00+00:00",
            "sources": {"lmarena": {"available": True}, "artificial_analysis": {"available": True}},
            "models": [{"slug": "model1"}],
        }
        aa_fetch = {"models": None, "failure": "permanent", "reason": "http_410", "detail": None,
                    "tier": None, "intelligence_index_version": None, "pages": 1, "ratelimit_remaining": None}
        code, saved, out = self._run(aa_fetch, previous)
        self.assertEqual(code, 1)
        self.assertEqual(saved, [])
        self.assertIn("models_collect_skipped_write reason=source_regression sources=artificial_analysis", out)
        self.assertIn("models_collect_failed reason=aa_permanent_error cause=http_410", out)

    def test_successful_v2_fetch_publishes_tier_and_public_attribution_link(self):
        aa_fetch = {"models": [_model(1)], "failure": None, "reason": None, "detail": None,
                    "tier": "free", "intelligence_index_version": 4.3, "pages": 1, "ratelimit_remaining": "99"}
        code, saved, out = self._run(aa_fetch, previous=None)
        self.assertEqual(code, 0)
        self.assertEqual(len(saved), 1)
        aa_meta = saved[0]["sources"]["artificial_analysis"]
        self.assertTrue(aa_meta["available"])
        self.assertEqual(aa_meta["tier"], "free")
        self.assertEqual(aa_meta["intelligence_index_version"], 4.3)
        self.assertEqual(aa_meta["url"], "https://artificialanalysis.ai/")
        self.assertTrue(aa_meta["api_url"].endswith("/api/v2/language/models/free"))
        row = next(m for m in saved[0]["models"] if m["slug"] == "model1")
        self.assertEqual(row["joined_sources"], ["lmarena", "artificial_analysis"])
        self.assertEqual(row["median_output_tokens_per_second"], 123.5)
        self.assertIn("models_collect_aa_fetched models=1 pages=1 tier=free", out)
        self.assertIn("models_collect_aa_benchmarks_unavailable tier=free", out)


if __name__ == "__main__":
    unittest.main()
