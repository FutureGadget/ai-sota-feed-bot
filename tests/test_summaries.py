"""Feed-card summaries: what the cards carry, when Claude is called, and what the build survives."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import brief_ledger  # noqa: E402
import summaries  # noqa: E402
import translator  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
LONG = "RunAnywhere runs language models on phones without a network connection. " * 6


def reply(payload, **usage):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    u = {"input_tokens": 1000, "output_tokens": 50}
    u.update(usage)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=SimpleNamespace(**u))


class SummaryClient:
    """Answers each request with ``answer(title)``; records every request."""

    def __init__(self, answer=lambda title: f"{title} covers one topic in a sentence.", error=None, **usage):
        self.calls: list[dict] = []
        self.answer = answer
        self.error = error
        self.usage = usage
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        user = kwargs["messages"][0]["content"]
        title = user.split("\n", 1)[0].removeprefix("Title: ")
        answer = self.answer(title)
        return reply(answer[4:] if answer.startswith("RAW:") else {"summary": answer}, **self.usage)

    def titles(self) -> list[str]:
        return [c["messages"][0]["content"].split("\n", 1)[0].removeprefix("Title: ") for c in self.calls]


def make_item(n: int = 1, **over) -> dict:
    item = {
        "url": f"https://example.com/post-{n}",
        "title": f"Post {n}",
        "source": "hackernews",
        "summary": LONG,
        "summary_1line": "Hi HN, Sanchit here from RunAnywhere, we have been building",
    }
    item.update(over)
    return item


class SummarizerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name) / "summaries.json"
        self.spend = Path(self.tmp.name) / "spend.json"
        self.clock = lambda: NOW

    def ledger(self, cap=10.0):
        return translator.Ledger(self.spend, monthly_cap=cap, now=self.clock)

    def summarizer(self, client, **kw):
        kw.setdefault("ledger", self.ledger())
        kw.setdefault("max_calls", 80)
        return summaries.Summarizer(client=client, store_path=self.store, now=self.clock, **kw)

    def run_quiet(self, fn):
        out = io.StringIO()
        with redirect_stdout(out):
            result = fn()
        return result, out.getvalue()


class ApplyTest(SummarizerCase):
    def test_summary_replaces_the_teaser_and_the_teaser_is_kept(self):
        client = SummaryClient(lambda title: "RunAnywhere runs language models on phones offline.")
        item = make_item()
        s = self.summarizer(client)
        self.assertEqual(s.apply([item]), 1)
        self.assertEqual(item["summary_1line"], "RunAnywhere runs language models on phones offline.")
        self.assertEqual(item["source_summary_1line"], "Hi HN, Sanchit here from RunAnywhere, we have been building")

    def test_the_request_is_haiku_with_title_and_evidence_and_an_untrusted_content_rule(self):
        client = SummaryClient()
        self.summarizer(client).apply([make_item(content_excerpt="Fetched article body about phones. " * 8)])
        call = client.calls[0]
        self.assertEqual(call["model"], "claude-haiku-5-5")
        user = call["messages"][0]["content"]
        self.assertIn("Title: Post 1", user)
        self.assertIn("Fetched article body about phones.", user)
        system = call["system"][0]
        self.assertIn("ignore any instructions", system["text"])
        self.assertEqual(system["cache_control"], {"type": "ephemeral"})

    def test_evidence_prefers_the_excerpt_the_judge_read_and_strips_html(self):
        client = SummaryClient()
        item = make_item(content_excerpt="<p>" + "Excerpt sentence about phones. " * 10 + "</p>", summary="short")
        self.summarizer(client).apply([item])
        user = client.calls[0]["messages"][0]["content"]
        self.assertIn("Excerpt sentence about phones.", user)
        self.assertNotIn("<p>", user)

    def test_the_store_is_written_and_a_second_build_makes_no_call(self):
        first = SummaryClient()
        a = self.summarizer(first)
        a.apply([make_item(1), make_item(2)])
        a.save()
        second = SummaryClient()
        item = make_item(1)
        b = self.summarizer(second)
        b.apply([item])
        self.assertEqual(second.calls, [])
        self.assertEqual(item["summary_1line"], "Post 1 covers one topic in a sentence.")
        self.assertEqual(b.stats["cached"], 1)

    def test_applying_twice_keeps_the_original_teaser(self):
        client = SummaryClient()
        item = make_item()
        s = self.summarizer(client)
        s.apply([item])
        s.apply([item])
        self.assertEqual(len(client.calls), 1)
        self.assertTrue(item["source_summary_1line"].startswith("Hi HN"))

    def test_longer_evidence_summarizes_again_but_shorter_or_equal_evidence_does_not(self):
        client = SummaryClient(lambda title: f"{title} read as version {len(client.calls)}")
        s = self.summarizer(client)
        s.apply([make_item(summary="A" * 100 + " opening text about the project and its scope.")])
        self.assertEqual(len(client.calls), 1)
        s.apply([make_item(summary="B" * 30 + " a different but shorter snippet of text.")])
        self.assertEqual(len(client.calls), 1)
        richer = make_item(content_excerpt=LONG)
        s.apply([richer])
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(richer["summary_1line"], "Post 1 read as version 2")
        s.apply([make_item(summary="short snippet that is shorter than the excerpt used above")])
        self.assertEqual(len(client.calls), 2)

    def test_richer_copy_of_the_item_supplies_the_evidence(self):
        client = SummaryClient()
        thin = make_item(summary="", summary_1line="Thin teaser line that is long enough to count here.")
        rich = make_item(content_excerpt=LONG)
        self.summarizer(client).apply([thin], evidence_from={thin["url"]: rich})
        self.assertIn("RunAnywhere runs language models", client.calls[0]["messages"][0]["content"])

    def test_items_without_a_key_are_ignored(self):
        client = SummaryClient()
        self.assertEqual(self.summarizer(client).apply([{"summary_1line": "x"}]), 0)
        self.assertEqual(client.calls, [])


class RejectionTest(SummarizerCase):
    def test_an_answer_that_echoes_the_title_or_is_empty_keeps_the_old_value(self):
        for answer in ("Post 1", "Post 1 - ", "", "   "):
            with self.subTest(answer=answer):
                item = make_item()
                old = item["summary_1line"]
                s = self.summarizer(SummaryClient(lambda title, a=answer: a))
                self.assertEqual(s.apply([item]), 0)
                self.assertEqual(item["summary_1line"], old)
                self.assertNotIn("source_summary_1line", item)
                self.assertEqual(s.stats["rejected"], 1)

    def test_an_overlong_answer_is_rejected(self):
        item = make_item()
        s = self.summarizer(SummaryClient(lambda title: "word " * 80))
        self.assertEqual(s.apply([item]), 0)
        self.assertTrue(item["summary_1line"].startswith("Hi HN"))

    def test_a_rejected_item_is_not_retried_until_its_evidence_grows(self):
        client = SummaryClient(lambda title: "Post 1")
        s = self.summarizer(client)
        s.apply([make_item()])
        s.save()
        again = self.summarizer(client)
        again.apply([make_item()])
        self.assertEqual(len(client.calls), 1)
        again.apply([make_item(content_excerpt=LONG * 3)])
        self.assertEqual(len(client.calls), 2)

    def test_an_unparseable_reply_skips_that_item_and_the_next_still_runs(self):
        client = SummaryClient(lambda title: "RAW:not json" if title == "Post 1" else f"{title} covers one post.")
        items = [make_item(1), make_item(2)]
        s = self.summarizer(client)
        s.apply(items)
        self.assertTrue(items[0]["summary_1line"].startswith("Hi HN"))
        self.assertEqual(items[1]["summary_1line"], "Post 2 covers one post.")
        self.assertEqual(s.stats["errors"], 1)
        self.assertNotIn(items[0]["url"], s.entries)


class LimitsTest(SummarizerCase):
    def test_the_call_cap_covers_the_whole_build_across_apply_calls(self):
        client = SummaryClient()
        s = self.summarizer(client, max_calls=3)
        first = [make_item(n) for n in range(1, 3)]
        second = [make_item(n) for n in range(3, 6)]
        s.apply(first)
        s.apply(second)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(s.stats["skipped_cap"], 2)
        self.assertTrue(all(i["summary_1line"].endswith("a sentence.") for i in first + second[:1]))
        self.assertTrue(all(i["summary_1line"].startswith("Hi HN") for i in second[1:]))

    def test_the_cap_comes_from_the_policy_file(self):
        policy = json.loads((ROOT / "config" / "translation.json").read_text())
        self.assertEqual(policy["summaries"]["max_calls_per_run"], 80)
        self.assertEqual(summaries.Summarizer(client=SummaryClient(), store_path=self.store).max_calls, 80)

    def test_budget_exceeded_keeps_old_values_stops_calling_and_does_not_raise(self):
        client = SummaryClient()
        cached = make_item(1)
        warm = self.summarizer(client)
        warm.apply([cached])
        warm.save()
        client.calls.clear()
        items = [make_item(1), make_item(2), make_item(3)]
        s = self.summarizer(client, ledger=self.ledger(cap=0.0))
        out = io.StringIO()
        with redirect_stdout(out):
            s.apply(items)
        self.assertEqual(client.calls, [])
        self.assertEqual(items[0]["summary_1line"], "Post 1 covers one topic in a sentence.")  # cached still applies
        self.assertTrue(items[1]["summary_1line"].startswith("Hi HN"))
        self.assertTrue(items[2]["summary_1line"].startswith("Hi HN"))
        self.assertIn("summary_budget_cap_reached", out.getvalue())
        self.assertEqual(s.blocked, "budget")
        self.assertEqual(s.stats["skipped_budget"], 2)

    def test_budget_that_runs_out_midway_keeps_the_summaries_already_written(self):
        # Haiku costs about $0.000125 for the fake usage; the cap admits one call.
        client = SummaryClient()
        items = [make_item(n) for n in range(1, 4)]
        s = self.summarizer(client, ledger=self.ledger(cap=0.00025))
        s.apply(items)
        done = [i for i in items if i["summary_1line"].endswith("a sentence.")]
        self.assertGreaterEqual(len(done), 1)
        self.assertLess(len(done), 3)
        s.save()
        self.assertEqual(len(summaries.load_store(self.store)), len(done))

    def test_without_credentials_nothing_is_called_and_the_skip_is_logged(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
        cached = make_item(1)
        warm = self.summarizer(SummaryClient())
        warm.apply([cached])
        warm.save()
        with patch.dict(os.environ, env, clear=True), patch.object(
            translator, "make_client", side_effect=AssertionError("client built without credentials")
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                s = summaries.Summarizer(store_path=self.store, ledger=self.ledger(), now=self.clock)
                items = [make_item(1), make_item(2)]
                s.apply(items)
        self.assertIn("summary_skipped reason=not_configured", out.getvalue())
        self.assertEqual(items[0]["summary_1line"], "Post 1 covers one topic in a sentence.")
        self.assertTrue(items[1]["summary_1line"].startswith("Hi HN"))
        self.assertEqual(s.stats["skipped_not_configured"], 1)

    def test_a_build_that_cannot_persist_spend_applies_the_cache_and_calls_nothing(self):
        client = SummaryClient()
        warm = self.summarizer(client)
        warm.apply([make_item(1)])
        warm.save()
        client.calls.clear()
        items = [make_item(1), make_item(2)]
        out = io.StringIO()
        with redirect_stdout(out):
            self.summarizer(client, spend_allowed=False).apply(items)
        self.assertEqual(client.calls, [])
        self.assertEqual(items[0]["summary_1line"], "Post 1 covers one topic in a sentence.")
        self.assertIn("summary_skipped reason=spend_not_allowed", out.getvalue())

    def test_for_build_follows_the_run_full_recovery_switch(self):
        with patch.dict(os.environ, {"STATIC_I18N_RECOVERY_BLOCKED": "1"}):
            self.assertEqual(summaries.for_build(client=SummaryClient()).blocked, "spend_not_allowed")
        with patch.dict(os.environ, {"STATIC_I18N_RECOVERY_BLOCKED": "0"}):
            self.assertIsNone(summaries.for_build(client=SummaryClient()).blocked)

    def test_an_api_error_stops_further_calls_and_does_not_raise(self):
        client = SummaryClient(error=RuntimeError("503 overloaded"))
        items = [make_item(1), make_item(2)]
        s = self.summarizer(client)
        self.run_quiet(lambda: s.apply(items))
        self.assertEqual(len(client.calls), 1)
        self.assertTrue(all(i["summary_1line"].startswith("Hi HN") for i in items))

    def test_spend_lands_in_the_shared_ledger_under_the_summary_surface(self):
        client = SummaryClient()
        s = self.summarizer(client)
        s.apply([make_item(1), make_item(2)])
        state = json.loads(self.spend.read_text())
        self.assertEqual([h["surface"] for h in state["history"]], ["summary", "summary"])
        self.assertEqual([h["key"] for h in state["history"]], ["https://example.com/post-1", "https://example.com/post-2"])
        # 1000 input + 50 output tokens at Haiku 5.5 prices, twice
        self.assertAlmostEqual(state["usd"], 2 * (1000 * 0.10 + 50 * 0.50) / 1_000_000, places=6)
        self.assertAlmostEqual(s.cost_usd, state["usd"], places=6)


class EvidenceTest(SummarizerCase):
    def test_title_only_items_are_not_sent_and_are_not_refetched_next_build(self):
        client = SummaryClient()
        fetches: list[int] = []

        def fetch(rows):
            fetches.append(len(rows))
            return {}

        item = make_item(summary="", summary_1line="Post 1")
        s = self.summarizer(client, fetch_evidence=fetch)
        s.apply([item])
        s.save()
        self.summarizer(client, fetch_evidence=fetch).apply([make_item(summary="", summary_1line="Post 1")])
        self.assertEqual(client.calls, [])
        self.assertEqual(fetches, [1])
        self.assertEqual(item["summary_1line"], "Post 1")

    def test_an_empty_evidence_item_is_summarized_from_the_fetched_article(self):
        client = SummaryClient()
        item = make_item(summary="", summary_1line="Post 1")
        s = self.summarizer(client, fetch_evidence=lambda rows: {rows[0]["url"]: LONG})
        s.apply([item])
        self.assertIn("RunAnywhere runs language models", client.calls[0]["messages"][0]["content"])
        self.assertEqual(item["summary_1line"], "Post 1 covers one topic in a sentence.")
        self.assertEqual(s.stats["fetched"], 1)

    def test_a_failing_fetch_does_not_fail_the_build(self):
        def boom(rows):
            raise OSError("network down")

        item = make_item(summary="", summary_1line="Post 1")
        s = self.summarizer(SummaryClient(), fetch_evidence=boom)
        self.run_quiet(lambda: s.apply([item]))
        self.assertEqual(item["summary_1line"], "Post 1")

    def test_no_fetch_is_made_when_every_item_has_evidence(self):
        s = self.summarizer(SummaryClient(), fetch_evidence=lambda rows: self.fail("fetched"))
        s.apply([make_item()])

    def test_evidence_text_ignores_the_title_echo_and_the_too_short(self):
        item = {"title": "Zero Trust for AI Agents", "summary_1line": "Zero Trust for AI Agents", "content_excerpt": ""}
        self.assertEqual(summaries.evidence_text(item), "")
        self.assertEqual(summaries.evidence_text({"title": "x", "summary": "Release 0.171.0"}), "")
        self.assertEqual(summaries.evidence_text({"title": "x", "summary": LONG}, max_chars=100), LONG[:100])

    def test_echoes_title(self):
        self.assertTrue(summaries.echoes_title("Show HN: Codeint", "Show HN: Codeint"))
        self.assertTrue(summaries.echoes_title("Zero Trust for AI Agents", "Zero trust for AI agents."))
        self.assertTrue(summaries.echoes_title("Zero Trust for AI Agents", "Zero Trust for AI Agents | Tessl"))
        self.assertFalse(summaries.echoes_title("Claude Code 2.1", "Claude Code 2.1 adds hooks for tool calls."))
        self.assertFalse(summaries.echoes_title("Codeint", "Codeint measures duplication drift in AI-written code."))


class StoreTest(SummarizerCase):
    def test_entries_unseen_for_30_days_are_pruned_and_seen_ones_kept(self):
        s = self.summarizer(SummaryClient())
        s.apply([make_item(1), make_item(2)])
        s.save()
        later = lambda: NOW + timedelta(days=31)  # noqa: E731
        s2 = summaries.Summarizer(client=SummaryClient(), store_path=self.store, now=later, ledger=self.ledger())
        s2.apply([make_item(1)])  # seen again
        self.assertEqual(s2.save(), 1)
        self.assertEqual(list(summaries.load_store(self.store)), ["https://example.com/post-1"])

    def test_a_corrupt_store_starts_empty(self):
        self.store.write_text("{not json")
        self.assertEqual(summaries.load_store(self.store), {})

    def test_the_store_file_has_the_documented_shape(self):
        s = self.summarizer(SummaryClient())
        s.apply([make_item(1)])
        s.save()
        entry = json.loads(self.store.read_text())["entries"]["https://example.com/post-1"]
        self.assertEqual(entry["model"], "claude-haiku-5-5")
        self.assertEqual(entry["summary"], "Post 1 covers one topic in a sentence.")
        self.assertEqual(entry["evidence_chars"], len(summaries.evidence_text(make_item(1))))
        self.assertEqual(set(entry), {"summary", "evidence_hash", "evidence_chars", "model", "summarized_at", "last_seen", "title"})


class LedgerTest(SummarizerCase):
    def _ledger_file(self, items: dict) -> Path:
        brief_dir = Path(self.tmp.name) / "brief"
        brief_dir.mkdir()
        (brief_dir / "2026-11-20.json").write_text(
            json.dumps({"date": "2026-11-20", "items": items}), encoding="utf-8"
        )
        return brief_dir

    def test_ledger_cards_get_summaries_from_the_richer_candidate_evidence(self):
        ledger_item = {"url": "https://example.com/post-1", "title": "Post 1", "summary_1line": "Hi HN, Sanchit here",
                       "content_excerpt": "", "story_key": "s1"}
        brief_dir = self._ledger_file({"s1": ledger_item})
        client = SummaryClient()
        candidate = make_item(1)
        s = self.summarizer(client)
        changed = summaries.apply_to_ledger(
            s, "2026-11-20T12:00:00+00:00", {candidate["url"]: candidate}, brief_dir=brief_dir
        )
        self.assertEqual(changed, 1)
        saved = json.loads((brief_dir / "2026-11-20.json").read_text())["items"]["s1"]
        self.assertEqual(saved["summary_1line"], "Post 1 covers one topic in a sentence.")
        self.assertEqual(saved["source_summary_1line"], "Hi HN, Sanchit here")
        self.assertIn("RunAnywhere runs language models", client.calls[0]["messages"][0]["content"])

    def test_a_ledger_card_already_summarized_in_the_edition_pass_costs_no_second_call(self):
        client = SummaryClient()
        s = self.summarizer(client)
        edition = [make_item(1)]
        s.apply(edition)
        brief_dir = self._ledger_file(
            {"s1": {"url": edition[0]["url"], "title": "Post 1", "summary_1line": "Hi HN, Sanchit here", "story_key": "s1"}}
        )
        summaries.apply_to_ledger(s, "2026-11-20T12:00:00+00:00", {edition[0]["url"]: edition[0]}, brief_dir=brief_dir)
        self.assertEqual(len(client.calls), 1)
        saved = json.loads((brief_dir / "2026-11-20.json").read_text())["items"]["s1"]
        self.assertEqual(saved["summary_1line"], "Post 1 covers one topic in a sentence.")

    def test_an_unchanged_ledger_is_not_rewritten(self):
        brief_dir = self._ledger_file({})
        path = brief_dir / "2026-11-20.json"
        before = path.stat().st_mtime_ns
        self.assertEqual(summaries.apply_to_ledger(self.summarizer(SummaryClient()), "2026-11-20T12:00:00+00:00", {}, brief_dir=brief_dir), 0)
        self.assertEqual(path.stat().st_mtime_ns, before)


class BuildWiringTest(SummarizerCase):
    """build_digest.run(): summaries reach latest.json and the ledger; a failing summarizer never fails the build."""

    def _run_build(self, for_build):
        import build_digest
        import ranking

        root = Path(self.tmp.name) / "repo"
        brief_dir = root / "data" / "brief"
        brief_dir.mkdir(parents=True)
        run_at = "2026-11-20T12:00:00+00:00"
        ledger_card = {"url": "https://example.com/post-1", "title": "Post 1", "story_key": "s1",
                       "summary_1line": "Hi HN, Sanchit here"}
        (brief_dir / "2026-11-20.json").write_text(json.dumps({"date": "2026-11-20", "items": {"s1": ledger_card}}))
        edition = [make_item(1)]
        patches = [
            patch.object(build_digest, "ROOT", root),
            patch.object(build_digest, "load_profile", return_value={}),
            patch.object(build_digest, "load_items_for_tier0", return_value=([make_item(1)], "raw", Path("items.json"))),
            patch.object(build_digest, "apply_pre_ranking", side_effect=lambda items: (items, {})),
            patch.object(build_digest, "load_source_health", return_value={}),
            patch.object(build_digest, "load_llm_cfg", return_value={}),
            patch.object(build_digest, "write_editorial_artifact"),
            patch.object(build_digest, "write_run_snapshot", return_value=(run_at, "run.json")),
            patch.object(build_digest, "record_judged_pool", return_value={}),
            patch.object(build_digest, "record_brief_ledger", return_value={}),
            patch.object(build_digest.summaries, "for_build", for_build),
            patch.object(brief_ledger, "BRIEF_DIR", brief_dir),
            patch.object(ranking, "run_ranking", return_value=(edition, {})),
            patch.dict(os.environ, {"TIER0_INCREMENTAL": "0"}),
        ]
        out = io.StringIO()
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        with redirect_stdout(out):
            build_digest.run()
        latest = json.loads((root / "data" / "processed" / "latest.json").read_text())
        ledger = json.loads((brief_dir / "2026-11-20.json").read_text())["items"]["s1"]
        return latest[0], ledger, out.getvalue()

    def test_latest_json_and_the_ledger_card_carry_the_summary(self):
        client = SummaryClient(lambda title: "RunAnywhere runs language models on phones offline.")
        card, ledger_card, log = self._run_build(lambda: self.summarizer(client))
        self.assertEqual(card["summary_1line"], "RunAnywhere runs language models on phones offline.")
        self.assertEqual(card["source_summary_1line"], "Hi HN, Sanchit here from RunAnywhere, we have been building")
        self.assertEqual(ledger_card["summary_1line"], card["summary_1line"])
        self.assertEqual(len(client.calls), 1)  # the edition pass paid; the ledger pass hit the cache
        self.assertIn("summary_stats", log)
        self.assertEqual(list(summaries.load_store(self.store)), ["https://example.com/post-1"])

    def test_a_summarizer_that_cannot_start_leaves_the_build_and_the_text_alone(self):
        def broken():
            raise RuntimeError("policy file unreadable")

        card, ledger_card, log = self._run_build(broken)
        self.assertTrue(card["summary_1line"].startswith("Hi HN"))
        self.assertEqual(ledger_card["summary_1line"], "Hi HN, Sanchit here")
        self.assertIn("summary_step_failed stage=edition", log)


if __name__ == "__main__":
    unittest.main()
