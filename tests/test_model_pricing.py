import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import model_pricing as pricing
import collect_models
import render_static_pages as render

NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
MODEL_ID = "anthropic/claude-sonnet-5.5"
ENDPOINT = {
    "provider_name": "Anthropic", "tag": "anthropic", "status": 0,
    "context_length": 1000000, "max_completion_tokens": 128000,
    "pricing": {"prompt": "0.000002", "completion": "0.00001", "input_cache_read": "0.0000002",
                "input_cache_write": "0.0000025", "input_cache_write_1h": "0.000004"},
}
CATALOG_ROW = {"id": MODEL_ID, "name": "Anthropic: Claude Sonnet 5.5",
               "created": NOW.timestamp(), "architecture": {"output_modalities": ["text"]},
               "pricing": ENDPOINT["pricing"]}


def snapshot():
    return {"version": 1, "catalog_checked_at": NOW.isoformat(), "models": {
        MODEL_ID: {"id": MODEL_ID, "name": CATALOG_ROW["name"], "created": NOW.timestamp(),
                   "source_url": "https://openrouter.ai/api/v1/models/" + MODEL_ID + "/endpoints",
                   "checked_at": NOW.isoformat(),
                   "offers": [pricing.normalize_offer(ENDPOINT, "anthropic", NOW.isoformat())]}}}


class PricingTest(unittest.TestCase):
    def test_sonnet_units_and_all_cache_durations(self):
        offer = pricing.normalize_offer(ENDPOINT, "anthropic", NOW.isoformat())
        self.assertEqual(offer["rates"], {"input": 2, "output": 10, "cache_read": .2, "cache_write": 2.5, "cache_write_1h": 4})
        self.assertEqual(offer["write_basis"], "replacement")

    def test_zero_is_preserved_and_invalid_or_missing_is_unknown(self):
        self.assertEqual(pricing.rates({"prompt": "0", "completion": "NaN", "input_cache_read": -1, "input_cache_write": True}),
                         {"input": 0, "output": None, "cache_read": None, "cache_write": None, "cache_write_1h": None})

    def test_google_storage_value_is_never_a_verified_total_write_rate(self):
        offer = pricing.normalize_offer(ENDPOINT, "google", NOW.isoformat())
        self.assertEqual(offer["write_basis"], "unverified")
        self.assertIsNone(offer["write_ttl"])

    def test_context_tiers_keep_usd_per_million_without_reapplying_discount(self):
        endpoint = copy.deepcopy(ENDPOINT)
        endpoint["pricing"].update(discount=.5, overrides=[{"min_prompt_tokens": 272000, "prompt": "0.000004", "completion": "0.000015"}])
        offer = pricing.normalize_offer(endpoint, "openai", NOW.isoformat())
        self.assertEqual(offer["rates"]["input"], 2)
        self.assertEqual(offer["tiers"][0]["rates"]["input"], 4)
        self.assertEqual(offer["tiers"][0]["rates"]["output"], 15)

    def test_original_provider_precedes_cheapest_host_and_excludes_special_service(self):
        direct = pricing.normalize_offer(ENDPOINT, "anthropic", NOW.isoformat())
        other = {**direct, "tag": "host/fp8", "rates": {**direct["rates"], "input": .01}}
        flex = {**other, "tag": "anthropic/flex"}
        self.assertEqual(pricing.select_offer([flex, other, direct], ["anthropic"]), direct)
        self.assertIsNone(pricing.select_offer([flex, {**direct, "tag": "anthropic/us"}], ["anthropic"]))
        self.assertEqual(pricing.select_offer([other], []), other)

    def test_endpoint_refresh_and_failure_preserve_last_good_atomically(self):
        cfg = {"base_url": "https://example.test/models"}
        def fetch(url):
            return {"data": [CATALOG_ROW]} if url == cfg["base_url"] else {"data": {"id": MODEL_ID, "endpoints": [ENDPOINT]}}
        first = pricing.refresh({}, cfg, NOW, fetch)
        self.assertEqual(first["models"][MODEL_ID]["offers"][0]["rates"]["input"], 2)
        def failed_endpoint(url):
            if url == cfg["base_url"]:
                return {"data": [CATALOG_ROW]}
            raise OSError("offline")
        second = pricing.refresh(first, cfg, NOW + timedelta(hours=5), failed_endpoint)
        self.assertEqual(second["models"][MODEL_ID]["offers"], first["models"][MODEL_ID]["offers"])
        self.assertEqual(second["models"][MODEL_ID]["checked_at"], NOW.isoformat())
        self.assertEqual(second["models"][MODEL_ID]["error"], "OSError")
        self.assertIsNone(first["models"][MODEL_ID]["error"])

    def test_invalid_catalog_preserves_prior_catalog_timestamp(self):
        old = snapshot()
        result = pricing.refresh(old, {"base_url": "https://example.test"}, NOW + timedelta(hours=1), lambda url: {"data": []})
        self.assertEqual(result["models"], old["models"])
        self.assertEqual(result["catalog_checked_at"], NOW.isoformat())
        self.assertEqual(result["error"], "ValueError")

    def test_changed_catalog_price_refreshes_endpoint_before_ttl(self):
        cfg = {"base_url": "https://example.test/models"}
        calls = []
        def fetch(url):
            calls.append(url)
            return {"data": [CATALOG_ROW]} if url == cfg["base_url"] else {"data": {"id": MODEL_ID, "endpoints": [ENDPOINT]}}
        first = pricing.refresh({}, cfg, NOW, fetch)
        calls.clear()
        pricing.refresh(first, cfg, NOW + timedelta(minutes=15), fetch)
        self.assertEqual(calls, [cfg["base_url"]])
        changed = copy.deepcopy(CATALOG_ROW)
        changed["pricing"]["prompt"] = "0.000003"
        calls.clear()
        def fetch_changed(url):
            if url == cfg["base_url"]:
                calls.append(url)
                return {"data": [changed]}
            return fetch(url)
        pricing.refresh(first, cfg, NOW + timedelta(minutes=15), fetch_changed)
        self.assertEqual(len(calls), 2)

    def test_bounded_refresh_does_not_lose_changes_waiting_for_next_batch(self):
        cfg = {"base_url": "https://example.test/models", "max_endpoints_per_run": 1}
        second = {**CATALOG_ROW, "id": "anthropic/second", "created": NOW.timestamp() - 60}
        def fetch(url):
            if url == cfg["base_url"]:
                return {"data": [CATALOG_ROW, second]}
            return {"data": {"id": url.removeprefix(cfg["base_url"] + "/").removesuffix("/endpoints"), "endpoints": [ENDPOINT]}}
        first = pricing.refresh({}, cfg, NOW, fetch)
        self.assertNotIn("offers", first["models"]["anthropic/second"])
        second_run = pricing.refresh(first, cfg, NOW + timedelta(minutes=15), fetch)
        self.assertEqual(second_run["models"]["anthropic/second"]["offers"][0]["rates"]["input"], 2)

    def test_wrong_endpoint_identity_never_overwrites_the_prior_offer(self):
        old = snapshot()
        def fetch(url):
            return {"data": [CATALOG_ROW]} if url == "https://example.test" else {"data": {"id": "another/model", "endpoints": [ENDPOINT]}}
        result = pricing.refresh(old, {"base_url": "https://example.test"}, NOW + timedelta(hours=5), fetch)
        self.assertEqual(result["models"][MODEL_ID]["offers"], old["models"][MODEL_ID]["offers"])
        self.assertEqual(result["models"][MODEL_ID]["error"], "ValueError")

    def test_identity_matching_does_not_strip_versions_or_cross_organizations(self):
        cfg = collect_models.load_config()
        rows = [{"url_slug": "claude-sonnet-5-5", "organization": "anthropic", "aa_intelligence_index": 56},
                {"url_slug": "claude-sonnet-5", "organization": "anthropic"},
                {"url_slug": "claude-sonnet-5-5", "organization": "another-lab"}]
        result = pricing.apply_pricing({"models": rows}, snapshot(), cfg, NOW)
        self.assertEqual(result["models"][0]["price_input_per_1m"], 2)
        self.assertEqual(result["models"][0]["price_blended_per_1m"], 4)
        self.assertIsNone(result["models"][1]["pricing"])
        self.assertIsNone(result["models"][2]["pricing"])
        self.assertNotIn("pricing", rows[0])

    def test_no_openrouter_price_cannot_fall_back_to_benchmark_price(self):
        result = pricing.apply_pricing({"models": [{"url_slug": "x", "price_input_per_1m": 2, "price_blended_per_1m": 4}]}, {}, collect_models.load_config(), NOW)
        self.assertIsNone(result["models"][0]["price_input_per_1m"])
        self.assertIsNone(result["models"][0]["price_blended_per_1m"])

    def test_new_model_is_discovered_without_inventing_score_or_release_date(self):
        result = pricing.apply_pricing({"models": []}, snapshot(), collect_models.load_config(), NOW)
        self.assertEqual(len(result["models"]), 1)
        model = result["models"][0]
        self.assertEqual(model["url_slug"], "claude-sonnet-5-5")
        self.assertIsNone(model.get("aa_intelligence_index"))
        self.assertIsNone(model.get("release_date"))
        self.assertFalse(model["frontier"])

    def test_static_detail_renders_source_and_cache_rates(self):
        model = pricing.apply_pricing({"models": []}, snapshot(), collect_models.load_config(), NOW)["models"][0]
        html = render.model_pricing_section(model)
        for text in ["USD per million", "Anthropic", "Cache read", "Cache write (5 minutes)", "Cache write (1 hour)", "$0.2", "$2.5", "$4", "/models/compare"]:
            self.assertIn(text, html)

    def test_displayed_models_refresh_ahead_of_unseen_catalog_models(self):
        cfg = {"base_url": "https://example.test/models", "max_endpoints_per_run": 1}
        other = {**CATALOG_ROW, "id": "anthropic/other", "created": NOW.timestamp() + 60}
        def fetch(url):
            if url == cfg["base_url"]:
                return {"data": [CATALOG_ROW, other]}
            return {"data": {"id": url.removeprefix(cfg["base_url"] + "/").removesuffix("/endpoints"), "endpoints": [ENDPOINT]}}
        both = pricing.refresh({}, {**cfg, "max_endpoints_per_run": 2}, NOW, fetch)
        later = NOW + timedelta(hours=5)
        # `other` is newer and equally old, so only priority can put MODEL_ID first.
        result = pricing.refresh(both, cfg, later, fetch, priority={MODEL_ID})
        self.assertEqual(result["models"][MODEL_ID]["checked_at"], later.isoformat())
        self.assertEqual(result["models"]["anthropic/other"]["checked_at"], NOW.isoformat())

    def test_radar_model_ids_join_only_models_the_radar_shows(self):
        cfg = collect_models.load_config()["sources"]["openrouter"]
        rows = [{"url_slug": "claude-sonnet-5-5", "organization": "anthropic"}]
        catalog = {"models": {**snapshot()["models"], "anthropic/unseen": {"name": "Anthropic: Unseen"}}}
        self.assertEqual(set(pricing.match_models(rows, catalog["models"], cfg)), {MODEL_ID})

    def test_top_model_keeps_its_frontier_place_while_its_offer_is_fresh(self):
        cfg = collect_models.load_config()
        rows = [{"url_slug": "claude-sonnet-5-5", "organization": "anthropic", "aa_intelligence_index": 56},
                {"url_slug": "cheap", "organization": "other", "aa_intelligence_index": 40,
                 "price_blended_per_1m": 1}]
        fresh = pricing.apply_pricing({"models": rows}, snapshot(), cfg, NOW)["models"]
        self.assertTrue(fresh[0]["frontier"]["aa_intelligence_index"]["on_frontier"])
        stale = pricing.apply_pricing({"models": rows}, snapshot(), cfg, NOW + timedelta(days=2))["models"]
        self.assertFalse(stale[0]["frontier"])

    def _verified(self, **item_overrides):
        snap = snapshot()
        snap["models"][MODEL_ID].update(fingerprint="f1", catalog_fingerprint="f1", **item_overrides)
        return snap

    def _price_after(self, snap, offer_age, catalog_age):
        snap["catalog_checked_at"] = (NOW + offer_age - catalog_age).isoformat()
        rows = [{"url_slug": "claude-sonnet-5-5", "organization": "anthropic", "aa_intelligence_index": 56}]
        return pricing.apply_pricing({"models": rows}, snap, collect_models.load_config(), NOW + offer_age)["models"][0]

    def test_unchanged_catalog_keeps_a_price_valid_past_24h_without_repolling(self):
        model = self._price_after(self._verified(), timedelta(days=3), timedelta(hours=1))
        self.assertFalse(model["pricing"]["stale"])
        self.assertTrue(model["pricing"]["verified_unchanged"])
        self.assertEqual(model["price_input_per_1m"], 2)
        self.assertTrue(model["frontier"]["aa_intelligence_index"]["on_frontier"] if model["frontier"] else False)

    def test_price_goes_stale_when_upstream_changed_and_was_not_refetched(self):
        snap = self._verified()
        snap["models"][MODEL_ID]["catalog_fingerprint"] = "f2"
        model = self._price_after(snap, timedelta(days=3), timedelta(hours=1))
        self.assertTrue(model["pricing"]["stale"])
        self.assertIsNone(model["price_input_per_1m"])

    def test_price_goes_stale_when_the_catalog_itself_has_not_been_checked(self):
        model = self._price_after(self._verified(), timedelta(days=3), timedelta(days=2))
        self.assertTrue(model["pricing"]["stale"])

    def test_hard_age_backstop_applies_even_when_the_catalog_is_unchanged(self):
        model = self._price_after(self._verified(), timedelta(days=8), timedelta(hours=1))
        self.assertTrue(model["pricing"]["stale"])

    def test_within_24h_is_fresh_without_catalog_evidence(self):
        model = self._price_after(snapshot(), timedelta(hours=23), timedelta(hours=23))
        self.assertFalse(model["pricing"]["stale"])

    def test_stale_prices_remain_auditable_but_leave_token_frontier(self):
        result = pricing.apply_pricing({"models": []}, snapshot(), collect_models.load_config(), NOW + timedelta(days=2))
        model = result["models"][0]
        self.assertTrue(model["pricing"]["stale"])
        self.assertEqual(model["pricing"]["rates"]["input"], 2)
        self.assertIsNone(model["price_blended_per_1m"])


if __name__ == "__main__":
    unittest.main()
