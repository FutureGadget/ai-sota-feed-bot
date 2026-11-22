"""scripts/translate.py (static pages): one Claude job per page, shared USD ledger, partial progress kept."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import persist_static_i18n as persistence  # noqa: E402
import translate as static_translate  # noqa: E402
import translator  # noqa: E402
from claude_fakes import PREFIX, EchoClient  # noqa: E402


def _candidate(ident: str, text: str, **extra) -> dict:
    return {
        "surface": "daily",
        "locale": "ko",
        "source_path": f"data/daily/{ident}.json",
        "source_hash": "h",
        "id": ident,
        "status": "missing",
        "title": ident,
        "source": {"title": text, **extra},
        "contract": {"translated_fields": ["title"]},
        "artifact_path": f"data/i18n/ko/daily/{ident}.json",
    }


class StaticTranslateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for stack in (
            patch.object(static_translate, "ROOT", self.root),
            patch.object(static_translate, "_rebuild_playbook_i18n_index"),
            patch.dict("os.environ", {translator.CAP_ENV: "60"}),
        ):
            stack.start()
            self.addCleanup(stack.stop)

    def run_translate(self, items, client, *, include_fresh=False) -> int:
        with patch.object(static_translate.exporter, "build_export", return_value={"items": items}):
            return static_translate.translate_candidates(
                locale="ko", surfaces=None, target_id=None, limit=10,
                dry_run=False, include_fresh=include_fresh, client=client,
            )

    def artifact(self, candidate) -> dict:
        return json.loads((self.root / candidate["artifact_path"]).read_text())

    def ledger(self) -> dict:
        return json.loads((self.root / "data/i18n/translation_spend.json").read_text())

    def write_receipts(self, receipt: dict) -> None:
        path = self.root / persistence.RECEIPTS
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"static_runs": {"actions-123-1": receipt}}))

    def test_a_page_is_one_job_keyed_by_field_index_with_its_title_as_context(self):
        page = _candidate("2026-07-05", "Agents ship", categories=[
            {"name": "Tools", "articles": [{"title": "First"}, {"title": "Second"}]},
            {"name": "Models", "articles": []},
        ])
        page["title"] = "Daily brief for July 5"
        page["contract"]["translated_fields"] = ["title", "categories[].name", "categories[].articles[].title"]
        client = EchoClient()

        self.assertEqual(self.run_translate([page], client), 0)

        (call,) = client.calls
        self.assertEqual(
            client.requested_fields(call),
            {"0": "Agents ship", "1": "Tools", "2": "Models", "3": "First", "4": "Second"},  # contract path order
        )
        self.assertIn("Daily brief for July 5", call["messages"][0]["content"])
        self.assertEqual(call["model"], translator.model_for("static"))
        artifact = self.artifact(page)
        self.assertEqual(artifact["title"], PREFIX + "Agents ship")
        self.assertEqual(artifact["categories"][0]["name"], PREFIX + "Tools")
        self.assertEqual(
            [a["title"] for a in artifact["categories"][0]["articles"]], [PREFIX + "First", PREFIX + "Second"]
        )
        self.assertEqual(artifact["categories"][1]["name"], PREFIX + "Models")
        self.assertEqual(artifact["source_hash"], "h")
        self.assertEqual(artifact["model"], translator.model_for("static"))
        self.assertEqual(self.ledger()["history"][0]["surface"], "static")

    def test_reaching_the_cap_stops_cleanly_and_keeps_finished_pages(self):
        pages = [_candidate(name, f"Text {name}") for name in "abc"]
        # Each reply costs about $0.50, so a $1 cap fits two pages and refuses the third.
        client = EchoClient(output_tokens=50_000)
        with patch.dict("os.environ", {translator.CAP_ENV: "1.0"}):
            code = self.run_translate(pages, client)

        self.assertEqual(code, 0)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(self.artifact(pages[0])["title"], PREFIX + "Text a")
        self.assertEqual(self.artifact(pages[1])["title"], PREFIX + "Text b")
        self.assertFalse((self.root / pages[2]["artifact_path"]).exists())
        self.assertAlmostEqual(self.ledger()["usd"], 1.0, places=2)

    def test_a_failed_page_does_not_discard_the_others(self):
        pages = [_candidate(name, f"Text {name}") for name in "abc"]
        client = EchoClient(fail_when=lambda fields: fields["0"] == "Text b")

        code = self.run_translate(pages, client)

        self.assertEqual(code, 1)
        self.assertEqual(self.artifact(pages[0])["title"], PREFIX + "Text a")
        self.assertFalse((self.root / pages[1]["artifact_path"]).exists())
        self.assertEqual(self.artifact(pages[2])["title"], PREFIX + "Text c")
        # The bad page was still paid for twice; the ledger sees every call.
        self.assertEqual(len(self.ledger()["history"]), 4)

    def test_pages_without_latin_text_make_no_call(self):
        page = _candidate("numbers", "2026")
        client = EchoClient()

        self.assertEqual(self.run_translate([page], client), 0)

        self.assertEqual(client.calls, [])
        self.assertEqual(self.artifact(page)["title"], "2026")

    def test_metadata_only_rebuild_cannot_buy_a_lost_translation_again(self):
        candidate = _candidate("a", "already billed")
        candidate["source"]["generated_at"] = "before"
        original_hash = static_translate._candidate_payload_hash(candidate)
        self.write_receipts({
            "lost_outputs": {candidate["artifact_path"]: "original-source-hash"},
            "lost_payloads": {candidate["artifact_path"]: original_hash},
        })
        candidate["source"]["generated_at"] = "after"
        candidate["source_hash"] = "rebuilt-source-hash"
        self.assertEqual(static_translate._candidate_payload_hash(candidate), original_hash)
        client = EchoClient()

        self.assertEqual(self.run_translate([candidate], client, include_fresh=True), 0)

        self.assertEqual(client.calls, [])
        self.assertFalse((self.root / candidate["artifact_path"]).exists())
        candidate["source"]["title"] = "new translation text"
        self.assertNotEqual(static_translate._candidate_payload_hash(candidate), original_hash)

    def test_acknowledged_lost_output_is_not_bought_again(self):
        candidate = _candidate("a", "already billed")
        self.write_receipts({"lost_outputs": {candidate["artifact_path"]: candidate["source_hash"]}})
        client = EchoClient()

        self.assertEqual(self.run_translate([candidate], client, include_fresh=True), 0)

        self.assertEqual(client.calls, [])
        self.assertFalse((self.root / candidate["artifact_path"]).exists())
        self.assertFalse((self.root / "data/i18n/translation_spend.json").exists())


if __name__ == "__main__":
    unittest.main()
