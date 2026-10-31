from __future__ import annotations

import unittest

from pipeline import judge


class SystemOnePayloadTest(unittest.TestCase):
    def cfg(self):
        return judge.load_judge_config(judge.DEFAULT_CONFIG)

    def test_category_question_has_criteria(self) -> None:
        payload = judge.build_systemone_payload(
            {
                "title": "A concrete serving optimization",
                "source": "vllm_blog",
                "source_role": "first_party",
                "published": "2026-10-24T00:00:00Z",
                "url": "https://example.com/post",
                "excerpt": "x" * 1000,
            },
            self.cfg(),
        )
        self.assertIn("questions", payload)
        self.assertIn("keep", payload["questions"])
        self.assertIn("category", payload["questions"])
        self.assertEqual(payload["questions"]["category"]["type"], "choice")
        self.assertGreaterEqual(len(payload["questions"]["category"]["criteria"]), 6)
        self.assertIn("agent_engineering", payload["questions"]["category"]["criteria"])

    def test_answers_and_choices_are_split(self) -> None:
        response = {
            "answers": {
                "keep": {"type": "noul", "noul": 0.75},
                "category": {
                    "type": "choice",
                    "choice": "inference_serving",
                    "confidence": 0.81,
                    "probabilities": {"inference_serving": 0.81, "agent_engineering": 0.12},
                },
            }
        }
        signals = judge.extract_systemone_answers(response)
        choices = judge.extract_systemone_choices(response)
        self.assertEqual(signals, {"keep": 0.75})
        self.assertEqual(choices["category"]["choice"], "inference_serving")
        self.assertAlmostEqual(choices["category"]["confidence"], 0.81)
        self.assertAlmostEqual(choices["category"]["probabilities"]["agent_engineering"], 0.12)

    def test_hybrid_primary_and_gates(self) -> None:
        hybrid = {
            "primary": "keep",
            "drop_if_above": {"release_lane": 0.6},
            "drop_if_below": {"platform_relevant": 0.35},
            "gate_score": 0.1,
        }
        self.assertAlmostEqual(
            judge.hybrid_score({"keep": 0.7, "release_lane": 0.1, "platform_relevant": 0.9}, hybrid),
            0.7,
        )
        self.assertAlmostEqual(
            judge.hybrid_score({"keep": 0.7, "release_lane": 0.8, "platform_relevant": 0.9}, hybrid),
            0.1,
        )
        self.assertAlmostEqual(
            judge.hybrid_score({"keep": 0.7, "release_lane": 0.1, "platform_relevant": 0.2}, hybrid),
            0.1,
        )

    def test_verdict_and_adjustment(self) -> None:
        self.assertEqual(judge.judge_verdict(0.05), "drop")
        self.assertEqual(judge.judge_verdict(0.35), "review")
        self.assertEqual(judge.judge_verdict(0.75), "keep")
        self.assertEqual(judge.judge_verdict(None), "unjudged")
        cfg = {"judge_adjustment": {"keep_at": 0.6, "keep_bonus": 0.15, "drop_at": 0.25, "drop_penalty": 0.30}}
        self.assertAlmostEqual(judge.judge_adjustment({"judge_score": 0.8}, cfg), 0.15)
        self.assertAlmostEqual(judge.judge_adjustment({"judge_score": 0.1}, cfg), -0.30)
        self.assertEqual(judge.judge_adjustment({"judge_score": 0.4}, cfg), 0.0)
        self.assertEqual(judge.judge_adjustment({}, cfg), 0.0)

    def test_openrouter_requires_configuration(self) -> None:
        provider = judge.OpenRouterSystemOneProvider(
            {"openrouter": {"endpoint": "https://openrouter.ai/api/v1/systemone", "api_key_env": "MISSING_OPENROUTER_KEY"}}
        )
        self.assertFalse(provider.configured())
        with self.assertRaises(RuntimeError):
            provider.score({"title": "x"}, {})


if __name__ == "__main__":
    unittest.main()


class SystemOneStateTest(unittest.TestCase):
    def test_video_state_declares_the_medium(self) -> None:
        state = judge.build_systemone_state(
            {
                "title": "A talk",
                "source": "ai_native_dev",
                "source_role": "practitioner",
                "published": "2026-10-28T00:00:00Z",
                "url": "https://youtu.be/AAAAAAAAAAA",
                "type": "video",
                "content_excerpt": "Show notes: " + ("x" * 1000),
            }
        )
        self.assertIn("Medium: video", state)
        self.assertIn("Show notes:", state)

    def test_article_state_has_no_medium_line(self) -> None:
        state = judge.build_systemone_state(
            {
                "title": "An article",
                "source": "vllm_blog",
                "source_role": "first_party",
                "url": "https://example.com/post",
                "content_excerpt": "x" * 1000,
            }
        )
        self.assertNotIn("Medium: video", state)
