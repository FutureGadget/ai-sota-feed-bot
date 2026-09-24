from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from publish import publish_follows as follows

# The signing spec both sides implement (tests/test_follow_api.mjs checks the
# JavaScript signer against the same formula).
TOKEN_VECTOR = hmac.new(b"test-key", b"unfollow:c-123:gemini-3-8", hashlib.sha256).hexdigest()[:32]
CFG = {"provider": "resend", "site_base": "https://www.llm-digest.com", "utm_source": "email"}
READER_ID = "anon_0b3c9a3e-5d1f-4c1e-9a55-2f1f0c7d9e11"


def thread(slug: str, last_updated: str) -> dict:
    return {"slug": slug, "label": slug.title(), "last_updated": last_updated, "latest_title": f"{slug} news"}


class FollowHelpersTest(unittest.TestCase):
    def test_token_follows_the_shared_signing_spec(self) -> None:
        self.assertEqual(follows.unfollow_token("test-key", "c-123", "gemini-3-8"), TOKEN_VECTOR)

    def test_parse_follows_dedupes_and_drops_junk(self) -> None:
        self.assertEqual(follows.parse_follows("a, b,,a,Bad Slug,c"), ["a", "b", "c"])

    def test_moved_storylines_filters_by_cursor_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "storylines").mkdir(parents=True)
            (root / "data" / "storylines" / "index.json").write_text(json.dumps({"storylines": [
                thread("old", "2026-09-20T00:00:00+00:00"),
                thread("new", "2026-09-23T00:00:00+00:00"),
                thread("newer", "2026-09-24T00:00:00+00:00"),
                {"slug": "../bad", "last_updated": "2026-09-25T00:00:00+00:00"},
            ]}))
            with mock.patch.object(follows, "ROOT", root):
                moved = follows.moved_storylines("2026-09-21T00:00:00+00:00")
                latest = follows.latest_storyline_update()
        self.assertEqual([t["slug"] for t in moved], ["newer", "new"])
        self.assertEqual(latest, "2026-09-24T00:00:00+00:00")


class FollowMessagesTest(unittest.TestCase):
    moved = [thread("gemini-3-8", "2026-09-24T00:00:00+00:00"), thread("gpt-6-astra", "2026-09-23T00:00:00+00:00")]

    def build(self, followers: list[dict]) -> list[dict]:
        return follows.build_messages(CFG, "test-key", "LLM Digest <digest@example.com>", followers, self.moved)

    def test_only_followed_moved_stories_reach_each_follower(self) -> None:
        messages = self.build([
            {"id": "c-1", "email": "a@example.com", "unsubscribed": False,
             "follows": ["gpt-6-astra", "not-moving"], "reader_id": READER_ID},
            {"id": "c-2", "email": "b@example.com", "unsubscribed": False, "follows": ["quiet"], "reader_id": ""},
            {"id": "c-3", "email": "c@example.com", "unsubscribed": True, "follows": ["gemini-3-8"], "reader_id": ""},
        ])
        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertEqual(msg["to"], ["a@example.com"])
        self.assertEqual(msg["subject"], "Gpt-6-Astra moved — LLM Digest")
        self.assertIn("/storyline/gpt-6-astra?utm_source=email&amp;rid=" + READER_ID, msg["html"])
        self.assertNotIn("gemini-3-8", msg["html"])
        self.assertIn(f"c=c-1&amp;s=gpt-6-astra&amp;t={follows.unfollow_token('test-key', 'c-1', 'gpt-6-astra')}", msg["html"])
        stop_all = follows.unfollow_url(CFG, "test-key", "c-1", "*")
        self.assertEqual(msg["headers"]["List-Unsubscribe"], f"<{stop_all}>")
        self.assertEqual(msg["headers"]["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.assertIn("Stop all story emails", msg["text"])

    def test_multiple_moved_follows_share_one_email(self) -> None:
        messages = self.build([{"id": "c-1", "email": "a@example.com", "unsubscribed": False,
                                "follows": ["gpt-6-astra", "gemini-3-8"], "reader_id": "none"}])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["subject"], "2 stories you follow moved — LLM Digest")
        self.assertNotIn("rid=", messages[0]["html"])
        self.assertLess(messages[0]["html"].index("Gemini-3-8"), messages[0]["html"].index("Gpt-6-Astra"))


class FollowMainTest(unittest.TestCase):
    def run_main(self, state: dict, env: dict, **patches) -> tuple[dict, list]:
        saved: list[dict] = []
        cfg = {**CFG, "enabled": True, "follows": {"enabled": True}}
        with mock.patch.object(follows, "load_config", return_value=cfg), \
                mock.patch.object(follows, "load_state", return_value=state), \
                mock.patch.object(follows, "save_state", side_effect=lambda s: saved.append(json.loads(json.dumps(s)))), \
                mock.patch.dict("os.environ", env, clear=False), \
                mock.patch("sys.argv", ["publish_follows.py"]):
            ctx = [mock.patch.object(follows, name, value) for name, value in patches.items()]
            for c in ctx:
                c.start()
            try:
                follows.main()
            finally:
                for c in ctx:
                    c.stop()
        return saved[-1] if saved else {}, saved

    env = {"EMAIL_API_KEY": "test-key", "EMAIL_FROM": "digest@example.com"}

    def test_first_run_only_initializes_the_cursor(self) -> None:
        send = mock.Mock()
        state, _ = self.run_main({}, self.env, latest_storyline_update=lambda: "2026-09-24T00:00:00+00:00",
                                 send_batch=send)
        self.assertEqual(state["follows"]["sent_through"], "2026-09-24T00:00:00+00:00")
        send.assert_not_called()

    def test_cursor_advances_only_after_sending(self) -> None:
        moved = [thread("gemini-3-8", "2026-09-24T00:00:00+00:00")]
        followers = [{"id": "c-1", "email": "a@example.com", "unsubscribed": False,
                      "follows": ["gemini-3-8"], "reader_id": ""}]
        send = mock.Mock()
        state, _ = self.run_main(
            {"follows": {"sent_through": "2026-09-23T00:00:00+00:00"}}, self.env,
            moved_storylines=lambda since: moved, followers_segment_id=lambda key: "seg-f",
            list_followers=lambda key, seg: followers, send_batch=send,
        )
        send.assert_called_once()
        self.assertEqual(len(send.call_args.args[1]), 1)
        self.assertEqual(state["follows"]["sent_through"], "2026-09-24T00:00:00+00:00")

    def test_send_failure_leaves_the_cursor(self) -> None:
        moved = [thread("gemini-3-8", "2026-09-24T00:00:00+00:00")]
        followers = [{"id": "c-1", "email": "a@example.com", "unsubscribed": False,
                      "follows": ["gemini-3-8"], "reader_id": ""}]
        with self.assertRaises(RuntimeError):
            self.run_main(
                {"follows": {"sent_through": "2026-09-23T00:00:00+00:00"}}, self.env,
                moved_storylines=lambda since: moved, followers_segment_id=lambda key: "seg-f",
                list_followers=lambda key, seg: followers,
                send_batch=mock.Mock(side_effect=RuntimeError("provider down")),
            )

    def test_no_op_without_credentials(self) -> None:
        with mock.patch.dict("os.environ", {"EMAIL_API_KEY": "", "EMAIL_FROM": ""}):
            state, saved = self.run_main({}, {})
        self.assertEqual(saved, [])
