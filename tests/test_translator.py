"""Claude translator: parsing, retry, cost, budget ledger, prompt shape."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import translator as tr  # noqa: E402


def reply(payload, **usage):
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    u = {"input_tokens": 1000, "output_tokens": 100}
    u.update(usage)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=SimpleNamespace(**u))


class FakeClient:
    """Plays back queued replies and records every request."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)

    @property
    def user_text(self) -> str:
        return self.calls[-1]["messages"][0]["content"]


def clock(year: int, month: int):
    return lambda: datetime(year, month, 15, 12, 0, tzinfo=timezone.utc)


class TranslateTest(unittest.TestCase):
    def test_output_budget_grows_with_the_job_and_stays_within_the_sdk_limit(self):
        small = FakeClient(reply({"title": "제목"}))
        tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=small)
        self.assertEqual(small.calls[0]["max_tokens"], tr.MIN_OUTPUT_TOKENS)
        page = FakeClient(reply({"0": "본문"}))
        tr.translate([tr.Job("k", {"0": "word " * 3000})], "ko", "static", client=page)
        self.assertGreater(page.calls[0]["max_tokens"], tr.MIN_OUTPUT_TOKENS)
        huge = FakeClient(reply({"0": "본문"}))
        tr.translate([tr.Job("k", {"0": "word " * 30000})], "ko", "static", client=huge)
        self.assertEqual(huge.calls[0]["max_tokens"], tr.MAX_OUTPUT_TOKENS)

    def test_returns_parsed_fields_in_job_order(self):
        client = FakeClient(reply({"title": "에이전트 공개", "summary": "요약"}))
        job = tr.Job("k1", {"title": "Agents ship", "summary": "A summary"})
        [res] = tr.translate([job], "ko", "feed", client=client)
        self.assertEqual(res.key, "k1")
        self.assertEqual(res.fields, {"title": "에이전트 공개", "summary": "요약"})
        self.assertEqual(len(client.calls), 1)

    def test_accepts_a_fenced_json_reply(self):
        client = FakeClient(reply('```json\n{"title": "제목"}\n```'))
        [res] = tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)
        self.assertEqual(res.fields, {"title": "제목"})

    def test_strings_without_latin_letters_skip_the_call(self):
        client = FakeClient()
        job = tr.Job("k", {"title": "이미 한국어", "n": "2026", "empty": ""})
        [res] = tr.translate([job], "ko", "feed", client=client)
        self.assertEqual(client.calls, [])
        self.assertEqual(res.fields, job.fields)
        self.assertEqual(res.cost_usd, 0.0)

    def test_only_latin_fields_are_sent_and_the_rest_kept(self):
        client = FakeClient(reply({"title": "제목"}))
        job = tr.Job("k", {"title": "Title", "note": "이미 한국어"})
        [res] = tr.translate([job], "ko", "feed", client=client)
        self.assertEqual(res.fields, {"title": "제목", "note": "이미 한국어"})
        self.assertNotIn("이미 한국어", client.user_text)

    def test_bad_json_retries_once_then_succeeds(self):
        client = FakeClient(reply("not json"), reply({"title": "제목"}))
        [res] = tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)
        self.assertEqual(res.fields, {"title": "제목"})
        self.assertEqual(len(client.calls), 2)

    def test_bad_json_twice_raises(self):
        client = FakeClient(reply("nope"), reply("still nope"))
        with self.assertRaises(tr.TranslationError):
            tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)
        self.assertEqual(len(client.calls), 2)

    def test_wrong_keys_are_rejected(self):
        for bad in ({"titel": "x"}, {"title": "x", "extra": "y"}, {}, {"title": 3}, ["title"]):
            with self.subTest(bad=bad):
                client = FakeClient(reply(bad), reply(bad))
                with self.assertRaises(tr.TranslationError):
                    tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)

    def test_cost_comes_from_usage_including_cache_tokens(self):
        usage = dict(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_read_input_tokens=1_000_000,
            cache_creation_input_tokens=1_000_000,
        )
        client = FakeClient(reply({"title": "제목"}, **usage))
        [res] = tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)
        self.assertAlmostEqual(res.cost_usd, 2.00 + 10.00 + 0.10 + 2.50)

    def test_cost_sums_a_retry(self):
        client = FakeClient(reply("bad", input_tokens=1_000_000, output_tokens=0),
                            reply({"title": "제목"}, input_tokens=1_000_000, output_tokens=0))
        [res] = tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)
        self.assertAlmostEqual(res.cost_usd, 4.00)

    def test_system_prompt_is_cached_and_carries_glossary_and_style(self):
        client = FakeClient(reply({"title": "제목"}))
        tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client)
        [block] = client.calls[0]["system"]
        self.assertEqual(block["cache_control"], {"type": "ephemeral"})
        for term in ("Claude Opus", "MCP", "Hugging Face"):
            self.assertIn(term, block["text"])
        self.assertIn("Korean", block["text"])
        self.assertIn("-다", block["text"])
        self.assertEqual(client.calls[0]["model"], "claude-sonnet-5-5")

    def test_context_is_truncated_to_the_policy_limit(self):
        client = FakeClient(reply({"title": "제목"}))
        limit = json.loads((ROOT / "config" / "translation.json").read_text())["max_context_chars"]
        job = tr.Job("k", {"title": "Title"}, context="a" * limit + "TAILMARK")
        tr.translate([job], "ko", "feed", client=client)
        self.assertIn("a" * limit, client.user_text)
        self.assertNotIn("TAILMARK", client.user_text)

    def test_context_comes_before_the_fields(self):
        client = FakeClient(reply({"title": "제목"}))
        tr.translate([tr.Job("k", {"title": "Title"}, context="CTXMARK")], "ko", "feed", client=client)
        text = client.user_text
        self.assertLess(text.index("CTXMARK"), text.index('"title"'))


class LedgerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "spend.json"
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(tr.CAP_ENV, None)

    def ledger(self, cap=1.0, month=(2026, 11)):
        return tr.Ledger(self.path, monthly_cap=cap, now=clock(*month))

    def test_translate_records_actual_cost(self):
        ledger = self.ledger()
        client = FakeClient(reply({"title": "제목"}, input_tokens=1_000_000, output_tokens=0))
        tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client, ledger=ledger)
        state = json.loads(self.path.read_text())
        self.assertEqual(state["month"], "2026-11")
        self.assertAlmostEqual(state["usd"], 2.0)
        self.assertEqual(state["history"][0]["key"], "k")

    def test_blocks_before_calling_when_over_the_cap(self):
        ledger = self.ledger(cap=0.50)
        ledger.record(0.50)
        client = FakeClient(reply({"title": "제목"}))
        with self.assertRaises(tr.BudgetExceeded):
            tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client, ledger=ledger)
        self.assertEqual(client.calls, [])

    def test_estimate_alone_can_exceed_the_cap(self):
        ledger = self.ledger(cap=0.000001)
        client = FakeClient(reply({"title": "제목"}))
        with self.assertRaises(tr.BudgetExceeded):
            tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client, ledger=ledger)
        self.assertEqual(client.calls, [])

    def test_stops_midway_when_spend_reaches_the_cap(self):
        ledger = self.ledger(cap=2.0)
        big = dict(input_tokens=1_000_000, output_tokens=0)  # $2.00 per call
        client = FakeClient(reply({"title": "a"}, **big), reply({"title": "b"}, **big))
        jobs = [tr.Job("k1", {"title": "One"}), tr.Job("k2", {"title": "Two"})]
        with self.assertRaises(tr.BudgetExceeded):
            tr.translate(jobs, "ko", "feed", client=client, ledger=ledger)
        self.assertEqual(len(client.calls), 1)
        self.assertAlmostEqual(ledger.spent, 2.0)

    def test_env_cap_overrides_the_configured_cap(self):
        ledger = self.ledger(cap=100.0)
        os.environ[tr.CAP_ENV] = "0.000001"
        client = FakeClient(reply({"title": "제목"}))
        with self.assertRaises(tr.BudgetExceeded):
            tr.translate([tr.Job("k", {"title": "Title"})], "ko", "feed", client=client, ledger=ledger)

    def test_cap_defaults_to_the_policy_file(self):
        cap = json.loads((ROOT / "config" / "translation.json").read_text())["monthly_usd_cap"]
        self.assertEqual(tr.Ledger(self.path).monthly_cap, cap)

    def test_a_new_month_resets_spend_and_keeps_history(self):
        self.ledger(month=(2026, 10)).record(0.9, key="old")
        november = self.ledger(month=(2026, 11))
        self.assertEqual(november.spent, 0.0)
        november.reserve(0.9)  # fits again
        november.record(0.1, key="new")
        state = json.loads(self.path.read_text())
        self.assertEqual(state["month"], "2026-11")
        self.assertAlmostEqual(state["usd"], 0.1)
        self.assertEqual([h["key"] for h in state["history"]], ["old", "new"])

    def test_history_is_capped(self):
        ledger = self.ledger(cap=1000)
        for i in range(tr.LEDGER_HISTORY_CAP + 5):
            ledger.record(0.001, key=str(i))
        history = json.loads(self.path.read_text())["history"]
        self.assertEqual(len(history), tr.LEDGER_HISTORY_CAP)
        self.assertEqual(history[-1]["key"], str(tr.LEDGER_HISTORY_CAP + 4))

    def test_write_leaves_no_temp_files(self):
        self.ledger().record(0.1)
        self.assertEqual([p.name for p in self.path.parent.iterdir()], [self.path.name])



class RequestJsonTest(unittest.TestCase):
    def _call(self, client, **extra):
        return tr.request_json(
            model="claude-haiku-5-5",
            system_text="sys",
            user="user",
            keys={"summary"},
            field_chars=100,
            key="k",
            surface="summary",
            client=client,
            **extra,
        )

    def test_returns_parsed_fields_and_cost_and_records_the_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = tr.Ledger(Path(tmp) / "spend.json", monthly_cap=1.0, now=clock(2026, 11))
            fields, cost = self._call(FakeClient(reply({"summary": "One sentence."})), ledger=ledger)
            self.assertEqual(fields, {"summary": "One sentence."})
            self.assertGreater(cost, 0)
            entry = json.loads((Path(tmp) / "spend.json").read_text())["history"][0]
            self.assertEqual((entry["key"], entry["surface"]), ("k", "summary"))
            self.assertAlmostEqual(ledger.spent, cost, places=6)

    def test_retries_once_then_raises_and_both_attempts_are_charged(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = tr.Ledger(Path(tmp) / "spend.json", monthly_cap=1.0, now=clock(2026, 11))
            client = FakeClient(reply("nope"), reply("still nope"))
            with self.assertRaises(tr.TranslationError):
                self._call(client, ledger=ledger)
            self.assertEqual(len(client.calls), 2)
            self.assertGreater(ledger.spent, 0)

    def test_budget_exceeded_is_raised_before_any_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = tr.Ledger(Path(tmp) / "spend.json", monthly_cap=0.0, now=clock(2026, 11))
            client = FakeClient()
            with self.assertRaises(tr.BudgetExceeded):
                self._call(client, ledger=ledger)
            self.assertEqual(client.calls, [])

    def test_max_tokens_override(self):
        client = FakeClient(reply({"summary": "x"}))
        self._call(client, max_tokens=300)
        self.assertEqual(client.calls[0]["max_tokens"], 300)


class IsConfiguredTest(unittest.TestCase):
    def _env(self, **env):
        keep = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
        return patch.dict(os.environ, {**keep, **env}, clear=True)

    def test_false_without_any_credential(self):
        with self._env():
            self.assertFalse(tr.is_configured())

    def test_api_key_or_auth_token(self):
        with self._env(ANTHROPIC_API_KEY="k"):
            self.assertTrue(tr.is_configured())
        with self._env(ANTHROPIC_AUTH_TOKEN="t"):
            self.assertTrue(tr.is_configured())

    def test_identity_token_file_must_exist_and_have_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "jwt"
            with self._env(ANTHROPIC_IDENTITY_TOKEN_FILE=str(token)):
                self.assertFalse(tr.is_configured())
                token.write_text("\n")
                self.assertFalse(tr.is_configured())
                token.write_text("eyJ...")
                self.assertTrue(tr.is_configured())


if __name__ == "__main__":
    unittest.main()
