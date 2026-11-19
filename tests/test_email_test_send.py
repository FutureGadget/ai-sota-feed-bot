"""`publish_email.py --test` sends each edition to one address and nothing else."""

from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

import publish.publish_email as email  # noqa: E402

BUILT = ("subject", '<p>body <a href="{{{RESEND_UNSUBSCRIBE_URL}}}">u</a> {{{contact.reader_id|none}}}</p>', [], "2026-11-18")


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None


class TestSendTest(unittest.TestCase):
    def run_main(self, argv, env):
        posts = []

        def fake_post(url, headers=None, json=None, timeout=None):
            posts.append((url, json))
            return FakeResponse()

        state = {"daily": {"last_sent_date": "2026-11-18"}}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(email, "build_daily", return_value=BUILT), \
             mock.patch.object(email.requests, "post", side_effect=fake_post), \
             mock.patch.object(email, "load_state", return_value=state), \
             mock.patch.object(email, "save_state") as save, \
             mock.patch.object(email, "send_broadcast") as broadcast, \
             mock.patch.object(sys, "argv", ["publish_email.py", *argv]), \
             redirect_stdout(out):
            code = email.main()
        return code, posts, save, broadcast, out.getvalue(), state

    def env(self, **extra):
        base = {"EMAIL_API_KEY": "k", "EMAIL_FROM": "LLM Digest <brief@example.com>", "EMAIL_TEST_TO": "owner@example.com"}
        base.update(extra)
        return base

    def test_sends_every_edition_to_the_test_address_only(self):
        code, posts, save, broadcast, out, state = self.run_main(["--kind", "daily", "--test"], self.env())
        self.assertEqual(code, 0)
        self.assertEqual([url for url, _ in posts], ["https://api.resend.com/emails"] * 2)
        self.assertEqual([p["to"] for _, p in posts], [["owner@example.com"]] * 2)
        self.assertEqual([p["subject"] for _, p in posts], ["[TEST daily en] subject", "[TEST daily ko] subject"])
        broadcast.assert_not_called()
        save.assert_not_called()
        self.assertEqual(state, {"daily": {"last_sent_date": "2026-11-18"}})
        self.assertIn("email_test_sent=true kind=daily locale=ko", out)
        self.assertNotIn("owner@example.com", out)

    def test_ignores_the_already_sent_guard_and_fills_broadcast_tokens(self):
        _, posts, *_ = self.run_main(["--kind", "daily", "--locale", "ko", "--test"], self.env())
        self.assertEqual(len(posts), 1)
        html = posts[0][1]["html"]
        self.assertNotIn("{{{", html)
        self.assertIn("/subscribe", html)

    def test_refuses_without_a_test_address(self):
        code, posts, *_ , out, _ = self.run_main(["--kind", "daily", "--test"], self.env(EMAIL_TEST_TO=""))
        self.assertEqual(code, 1)
        self.assertEqual(posts, [])
        self.assertIn("reason=no_EMAIL_TEST_TO", out)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.wf = yaml.safe_load((ROOT / ".github" / "workflows" / "email-digest.yml").read_text(encoding="utf-8"))
        self.steps = {s.get("name"): s for s in self.wf["jobs"]["email-digest"]["steps"]}

    def test_test_send_skips_follow_alerts_and_cursor_commit(self):
        inputs = self.wf[True]["workflow_dispatch"]["inputs"] if True in self.wf else self.wf["on"]["workflow_dispatch"]["inputs"]
        self.assertIn("test_send", inputs)
        self.assertEqual(inputs["locale"]["default"], "all")
        for name in ("Send storyline follow alerts", "Commit send cursor"):
            self.assertIn("test_send != 'true'", self.steps[name]["if"])
        self.assertIn("locale != 'ko'", self.steps["Send storyline follow alerts"]["if"])
        self.assertIn("slot != 'us'", self.steps["Send storyline follow alerts"]["if"])
        send = self.steps["Send digest"]
        self.assertIn('--slot "${INPUT_SLOT:-kst}"', send["run"])
        self.assertEqual(send["env"]["EMAIL_SEGMENT_ID_EN_US"], "${{ secrets.EMAIL_SEGMENT_ID_EN_US }}")
        self.assertEqual(inputs["slot"]["default"], "kst")
        self.assertEqual(send["env"]["EMAIL_TEST_TO"], "${{ secrets.EMAIL_TEST_TO }}")
        self.assertIn('--locale "${INPUT_LOCALE:-all}"', send["run"])


if __name__ == "__main__":
    unittest.main()
