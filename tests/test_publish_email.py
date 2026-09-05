from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from publish import publish_email as email
from tests.test_skill_lab_contract import published_record


class DailyEmailRenderingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = {
            "provider": "resend",
            "site_base": "https://www.llm-digest.com",
            "utm_source": "email",
        }
        self.recap = {
            "date": "2026-06-24",
            "intro": ["A concise lead."],
            "highlights": ["One useful thing happened."],
            "categories": [
                {
                    "name": "Hardening agents",
                    "summary": "Identity and isolation work moved forward.",
                    "articles": [
                        {
                            "title": "Agent identity access model",
                            "summary": "Agents get a governed identity.",
                            "source": "claude_blog",
                            "url": "https://example.com/agent-identity",
                        },
                        {
                            "title": "Hardware-isolated agent harness",
                            "summary": "Run agents as untrusted code.",
                            "source": "hackernews_ai",
                            "url": "https://example.com/harness",
                        },
                    ],
                },
                {
                    "name": "Coding-agent toolchain",
                    "summary": "Builder tooling keeps filling in.",
                    "articles": [
                        {
                            "title": "Declare agent config once",
                            "summary": "Sync one config across providers.",
                            "source": "hackernews_ai",
                            "url": "https://example.com/config",
                        }
                    ],
                },
            ],
        }

    def test_daily_email_has_visible_category_headers(self) -> None:
        _, body = email.render_daily(self.cfg, self.recap, [])

        self.assertIn("Theme 1 · 2 items", body)
        self.assertIn("Hardening agents", body)
        self.assertIn("Identity and isolation work moved forward.", body)
        self.assertLess(body.index("Hardening agents"), body.index("Agent identity access model"))
        self.assertIn("Theme 2 · 1 item", body)
        self.assertLess(body.index("Coding-agent toolchain"), body.index("Declare agent config once"))

    def test_daily_email_text_alternative_keeps_category_headers(self) -> None:
        _, body = email.render_daily(self.cfg, self.recap, [])
        text = email.html_to_text(body)

        self.assertIn("Theme 1 · 2 items", text)
        self.assertIn("Hardening agents", text)
        self.assertLess(text.index("Hardening agents"), text.index("Agent identity access model"))
        self.assertIn("Theme 2 · 1 item", text)
        self.assertLess(text.index("Coding-agent toolchain"), text.index("Declare agent config once"))

    def test_daily_email_does_not_add_skill_lab_promotion(self) -> None:
        _, body = email.render_daily(self.cfg, self.recap, [])
        self.assertNotIn("Agent Skill Lab", body)


class WeeklySkillLabEmailTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = {
            "provider": "resend",
            "site_base": "https://www.llm-digest.com",
            "utm_source": "email",
            "weekly": {"articles_per_category": 3, "max_favorites": 0},
        }
        self.week = {
            "week": "2026-W36",
            "start": "2026-09-05",
            "end": "2026-09-11",
            "title": "What happened in AI this week",
            "intro": ["A concise week."],
            "highlights": ["One useful thing happened."],
            "categories": [],
        }
        self.lab = json.loads(
            (email.ROOT / "data/playbook/lab/protocol.json").read_text(encoding="utf-8")
        )
        self.lab["summary"] = "Nine runs per result, with the failed runs included."

    def write_lab_store(self, directory: Path, records: list[dict]) -> None:
        summaries = []
        for record in records:
            source = json.dumps(record, sort_keys=True).encode()
            (directory / f"{record['slug']}.json").write_bytes(source)
            summary = {
                field: record[field]
                for field in (
                    "id", "slug", "pilot_edition", "pilot_size", "state", "date",
                    "generated_at", "featured_until", "title", "question", "summary",
                )
            }
            summary.update({
                "schema_version": 1,
                "url": f"/playbook/lab/{record['slug']}",
                "content_sha256": hashlib.sha256(source).hexdigest(),
            })
            summaries.append(summary)
        summaries.sort(
            key=lambda row: (row["pilot_edition"], row["date"]),
            reverse=True,
        )
        (directory / "index.json").write_text(json.dumps(summaries), encoding="utf-8")
        if records:
            latest = max(
                records,
                key=lambda row: (row["pilot_edition"], row["date"]),
            )
            (directory / "latest.json").write_text(json.dumps(latest), encoding="utf-8")

    def test_weekly_email_includes_current_lab_with_attributed_durable_link(self) -> None:
        _, body = email.render_weekly(self.cfg, self.week, [], [], self.lab)

        self.assertIn("Agent Skill Lab · Pilot 0/3", body)
        self.assertIn("Agent skills need receipts", body)
        self.assertIn("Nine runs per result", body)
        self.assertIn("/playbook/lab/protocol?utm_source=email", body)
        self.assertIn("utm_campaign=skill_lab_0", body)
        self.assertIn("ref=weekly_email", body)

    def test_weekly_email_without_current_lab_is_unchanged(self) -> None:
        _, body = email.render_weekly(self.cfg, self.week, [], [], None)
        self.assertNotIn("Agent Skill Lab", body)

    def test_skill_lab_selector_carries_an_unsent_record_into_the_next_week(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.write_lab_store(directory, [self.lab])

            with mock.patch.object(email, "SKILL_LAB_DIR", directory):
                selected = email.skill_lab_in_window("2026-09-05", "2026-09-11")
                already_sent = email.skill_lab_in_window(
                    "2026-09-05", "2026-09-11", {"lab-protocol"}
                )

            self.assertEqual(selected["id"], "lab-protocol")
            self.assertIsNone(already_sent)

    def test_skill_lab_selector_honors_feature_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            expired = {**self.lab, "featured_until": "2026-09-04"}
            self.write_lab_store(directory, [expired])

            with mock.patch.object(email, "SKILL_LAB_DIR", directory):
                selected = email.skill_lab_in_window("2026-09-05", "2026-09-11")

            self.assertIsNone(selected)

    def test_skill_lab_selector_rejects_a_valid_result_in_an_invalid_store_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            result = published_record(3, "context-skill")
            self.write_lab_store(directory, [result])

            with mock.patch.object(email, "SKILL_LAB_DIR", directory):
                selected = email.skill_lab_in_window("2026-09-13", "2026-09-19")

            self.assertIsNone(selected)

    def test_malformed_or_stale_lab_data_fails_soft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.write_lab_store(directory, [self.lab])
            index_path = directory / "index.json"
            malformed = json.loads(index_path.read_text())
            malformed[0]["pilot_edition"] = "corrupt"
            index_path.write_text(json.dumps(malformed), encoding="utf-8")

            with mock.patch.object(email, "SKILL_LAB_DIR", directory):
                self.assertIsNone(email.skill_lab_in_window("2026-09-05", "2026-09-11"))

            self.write_lab_store(directory, [self.lab])
            changed = {**self.lab, "summary": "Changed after indexing."}
            (directory / "protocol.json").write_text(json.dumps(changed), encoding="utf-8")
            with mock.patch.object(email, "SKILL_LAB_DIR", directory):
                self.assertIsNone(email.skill_lab_in_window("2026-09-05", "2026-09-11"))

            invalid = {**self.lab}
            invalid.pop("method")
            self.write_lab_store(directory, [invalid])
            with mock.patch.object(email, "SKILL_LAB_DIR", directory):
                self.assertIsNone(email.skill_lab_in_window("2026-09-05", "2026-09-11"))

    def test_successful_weekly_send_records_the_lab_id_without_losing_week_state(self) -> None:
        state = {
            "weekly": {
                "last_sent_week": "2026-W35",
                "sent_skill_lab_ids": ["lab-older"],
                "future_field": "preserve",
            }
        }

        email.advance_weekly_state(state, "2026-W36", "lab-protocol")

        self.assertEqual(state["weekly"]["last_sent_week"], "2026-W36")
        self.assertEqual(
            state["weekly"]["sent_skill_lab_ids"], ["lab-older", "lab-protocol"]
        )
        self.assertEqual(state["weekly"]["future_field"], "preserve")


if __name__ == "__main__":
    unittest.main()
