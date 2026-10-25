from __future__ import annotations

import unittest

from pipeline.release_policy import classify_release_tier, is_release_item


def _release(title: str, highlights: list[str] | None = None, **extra):
    payload = {
        "id": title,
        "source": "vllm_releases",
        "title": title,
        "type": "release",
        "source_role": "release",
        "summary": "",
        "release_highlights": highlights or [],
    }
    payload.update(extra)
    return payload


class ReleaseTierTest(unittest.TestCase):
    def test_substantive_changelog_is_major(self) -> None:
        item = _release(
            "vllm v0.32.0",
            [
                "Structured decisions and generic parsers : the new POST /v1/systemone endpoint answers choice , noul and score questions",
                "Low-precision KV cache everywhere : NVFP4 KV cache now runs on SM8x",
            ],
        )
        self.assertEqual(classify_release_tier(item), "major")

    def test_patch_release_with_real_fixes_is_major(self) -> None:
        item = _release(
            "langgraph==1.2.17",
            [
                "release(langgraph): 1.2.17",
                "fix(langgraph): apply an explicit recursion_limit equal to the default",
                "fix(langgraph): keep the caller's namespace in RemoteGraph.stream(subgraphs=True)",
            ],
        )
        self.assertEqual(classify_release_tier(item), "major")

    def test_bare_prerelease_is_minor(self) -> None:
        item = _release("codex 0.165.0-alpha.1")
        self.assertEqual(classify_release_tier(item), "minor")

    def test_prerelease_stays_minor_even_with_a_substantive_changelog(self) -> None:
        item = _release(
            "vllm v0.33.0-rc1",
            ["Added a new endpoint for structured decisions with a configurable parser"],
        )
        self.assertEqual(classify_release_tier(item), "minor")

    def test_dependency_bump_is_minor(self) -> None:
        item = _release(
            "claude-agent-sdk-python v0.2.174",
            ["Updated bundled Claude CLI to version 2.1.310"],
        )
        self.assertEqual(classify_release_tier(item), "minor")

    def test_generic_release_note_is_minor(self) -> None:
        item = _release("vllm v1.2.3", ["Bug fixes and performance improvements"])
        self.assertEqual(classify_release_tier(item), "minor")

    def test_version_only_changelog_is_minor(self) -> None:
        item = _release("vllm v1.2.3", ["release(vllm): 1.2.3", "v1.2.3"])
        self.assertEqual(classify_release_tier(item), "minor")

    def test_short_fix_is_not_enough_for_the_brief(self) -> None:
        item = _release("vllm v1.2.3", ["Fixed a typo"])
        self.assertEqual(classify_release_tier(item), "minor")

    def test_major_version_bump_is_major_without_highlights(self) -> None:
        self.assertEqual(classify_release_tier(_release("vllm v2.0.0")), "major")

    def test_open_weight_model_drop_is_major(self) -> None:
        item = _release(
            "tencent/Hy-Nomas released on Hugging Face",
            source="hf_tencent_hunyuan_releases",
        )
        self.assertEqual(classify_release_tier(item), "major")

    def test_non_release_item_has_no_tier(self) -> None:
        item = {
            "source": "simon_willison",
            "title": "Agent evaluation patterns",
            "summary": "A practical eval harness.",
            "type": "news",
        }
        self.assertIsNone(classify_release_tier(item))
        self.assertFalse(is_release_item(item))

    def test_release_detection_covers_roles_types_and_sources(self) -> None:
        self.assertTrue(is_release_item({"source_role": "release"}))
        self.assertTrue(is_release_item({"type": "release"}))
        self.assertTrue(is_release_item({"source": "vllm_releases"}))
        self.assertTrue(is_release_item({"source": "hf_qwen_releases"}))
        self.assertFalse(is_release_item({"source": "openai_blog", "type": "news"}))


if __name__ == "__main__":
    unittest.main()
