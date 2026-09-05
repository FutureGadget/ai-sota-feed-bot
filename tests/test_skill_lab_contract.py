from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from pipeline import build_skill_lab as lab


def protocol_record() -> dict:
    return {
        "schema_version": 1,
        "kind": "agent-skill-lab",
        "id": "lab-protocol",
        "slug": "protocol",
        "pilot_edition": 0,
        "pilot_size": 3,
        "state": "protocol",
        "date": "2026-09-04",
        "generated_at": "2026-09-04T00:00:00Z",
        "featured_until": "2026-09-18",
        "title": "Agent skills need receipts",
        "question": "What changes when the same agent gets three instruction levels?",
        "summary": "A transparent protocol for three repeated-condition field tests.",
        "method": {
            "task": {
                "description": "One bounded repository task per result edition.",
                "success_criteria": ["The required behavior passes deterministic tests."],
                "evaluation_method": "Score the same disclosed rubric after every run.",
            },
            "environment": {
                "model": {"name": "Pinned before each result", "version": "Disclosed with the result"},
                "reasoning_effort": "Pinned before each result",
                "harness": {"name": "Pinned before each result", "version": "Disclosed with the result"},
                "repository_fixture": {"name": "Public fixture", "revision": "Pinned before each result"},
                "permissions": ["workspace-write"],
                "budget": {
                    "timeout_seconds": 1800,
                    "max_tokens_per_run": 100000,
                    "max_cost_usd_per_run": 5,
                },
            },
            "runs_per_condition": 3,
            "conditions": [
                {"id": "no-skill", "label": "No skill", "setup": "Task only."},
                {
                    "id": "minimal-instructions",
                    "label": "Minimal instructions",
                    "setup": "Task plus a short checklist.",
                },
                {"id": "full-skill", "label": "Full skill", "setup": "Task plus the pinned complete skill."},
            ],
            "held_constant": ["Model and reasoning effort", "Repository fixture and revision"],
            "measures": [
                {"id": "task-success", "label": "Task success", "description": "Passes all predeclared criteria."},
                {"id": "final-quality", "label": "Final quality", "description": "Score on the disclosed rubric."},
                {"id": "trajectory", "label": "Trajectory", "description": "Planning, recovery, and unnecessary work."},
                {"id": "efficiency", "label": "Efficiency", "description": "Time, tokens, tool calls, and cost."},
            ],
        },
        "publication_rule": "No verdict appears until all runs and artifacts pass review.",
        "limitations": ["Three tasks cannot establish universal skill superiority."],
    }


def published_record(edition: int = 1, slug: str = "debugging-skill") -> dict:
    record = protocol_record()
    record.update(
        {
            "id": f"lab-{slug}",
            "slug": slug,
            "pilot_edition": edition,
            "state": "published",
            "date": f"2026-09-{10 + edition:02d}",
            "generated_at": f"2026-09-{10 + edition:02d}T12:00:00Z",
            "featured_until": f"2026-09-{24 + edition:02d}",
            "title": "Does a debugging skill improve repository repair?",
            "verdict": "The full skill improved recovery consistency in this fixture.",
            "recommendation": "Use the full skill when the task begins with an ambiguous failing behavior.",
            "tested_at": f"2026-09-{10 + edition:02d}T10:00:00Z",
        }
    )
    record.pop("publication_rule")
    environment = record["method"]["environment"]
    environment["model"] = {"name": "Example Model", "version": "2026-09-01"}
    environment["reasoning_effort"] = "high"
    environment["harness"] = {"name": "Example Harness", "version": "1.2.3"}
    environment["repository_fixture"] = {"name": "public-debug-fixture", "revision": "abc1234"}
    record["method"]["skill"] = {
        "name": "debugging-and-error-recovery",
        "revision": "skill-revision-abc1234",
        "source_url": "https://example.com/skills/debugging/skill-revision-abc1234",
        "sha256": "a" * 64,
    }

    def runs(condition: str) -> list[dict]:
        return [
            {
                "id": f"{condition}-{n}",
                "success": n > 1,
                "quality_score": 70 + n,
                "metrics": {
                    "duration_ms": 100000 + n,
                    "input_tokens": 12000 + n,
                    "output_tokens": 3000 + n,
                    "cost_usd": 0.42 + n / 100,
                    "tool_calls": 14 + n,
                    "interventions": 0,
                    "recovery_events": 1,
                    "unnecessary_actions": 2,
                },
                "trajectory_summary": "Observed the failure, reproduced it, and verified the patch.",
                "artifact_url": f"https://example.com/lab-artifacts/{slug}/{condition}-{n}.json",
            }
            for n in range(1, 4)
        ]

    for condition in record["method"]["conditions"]:
        condition["runs"] = runs(condition["id"])
        condition["finding"] = "A bounded observation about this condition."
        if condition["id"] != "no-skill":
            condition["instruction_artifact_url"] = (
                f"https://example.com/lab-artifacts/{slug}/{condition['id']}.txt"
            )
            condition["instruction_sha256"] = (
                "a" * 64 if condition["id"] == "full-skill" else "b" * 64
            )
    return record


class SkillLabContractTest(unittest.TestCase):
    def test_accepts_protocol_without_results(self) -> None:
        self.assertEqual(lab.validate_record(protocol_record()), [])

    def test_store_and_api_selector_slugs_are_reserved(self) -> None:
        for slug in ("drafts", "index", "latest", "list"):
            with self.subTest(slug=slug):
                record = protocol_record()
                record["slug"] = slug

                self.assertTrue(
                    any("reserved" in error for error in lab.validate_record(record))
                )

    def test_protocol_rejects_result_claims_and_runs(self) -> None:
        record = protocol_record()
        record["verdict"] = "Full skill wins."
        record["method"]["conditions"][0]["runs"] = []

        errors = lab.validate_record(record)

        self.assertTrue(any("protocol" in error and "verdict" in error for error in errors))
        self.assertTrue(any("protocol" in error and "runs" in error for error in errors))

    def test_accepts_complete_published_result(self) -> None:
        self.assertEqual(lab.validate_record(published_record()), [])

    def test_result_requires_reasoning_effort_and_immutable_skill_revision(self) -> None:
        record = published_record()
        record["method"]["environment"].pop("reasoning_effort")
        record["method"]["skill"].pop("revision")
        record["method"]["skill"]["sha256"] = "not-a-digest"

        errors = lab.validate_record(record)

        self.assertTrue(any("reasoning_effort" in error for error in errors))
        self.assertTrue(any("method.skill.revision" in error for error in errors))
        self.assertTrue(any("method.skill.sha256" in error for error in errors))

    def test_result_requires_distinct_minimal_and_full_instruction_artifacts(self) -> None:
        record = published_record()
        minimal = next(
            item for item in record["method"]["conditions"] if item["id"] == "minimal-instructions"
        )
        full = next(
            item for item in record["method"]["conditions"] if item["id"] == "full-skill"
        )
        minimal["instruction_artifact_url"] = full["instruction_artifact_url"]
        minimal["instruction_sha256"] = full["instruction_sha256"]

        errors = lab.validate_record(record)

        self.assertTrue(any("distinct instruction artifact URLs" in error for error in errors))
        self.assertTrue(any("distinct instruction digests" in error for error in errors))

    def test_result_requires_exact_conditions_and_repeated_runs(self) -> None:
        record = published_record()
        record["method"]["conditions"].pop()
        record["method"]["conditions"][0]["runs"].pop()

        errors = lab.validate_record(record)

        self.assertTrue(any("exact condition ids" in error for error in errors))
        self.assertTrue(any("runs_per_condition" in error for error in errors))

    def test_condition_presentation_order_is_canonical(self) -> None:
        record = published_record()
        record["method"]["conditions"].reverse()

        errors = lab.validate_record(record)

        self.assertTrue(any("condition ids in order" in error for error in errors))

    def test_record_requires_every_disclosed_measure(self) -> None:
        record = protocol_record()
        record["method"]["measures"] = record["method"]["measures"][:-1]

        errors = lab.validate_record(record)

        self.assertTrue(any("required measure ids" in error for error in errors))

    def test_result_rejects_unsafe_artifact_url(self) -> None:
        unsafe_urls = (
            "javascript:alert(1)",
            "https://example.com/run.json?token=public-secret",
            "https://example.com/run.json?",
            "https://example.com/run.json#private-note",
            "https://example.com/run.json#",
            "/lab-artifacts/%252e%252e/private/run.json",
            "/lab-artifacts/run%00.json",
        )
        for unsafe_url in unsafe_urls:
            with self.subTest(unsafe_url=unsafe_url):
                record = published_record()
                record["method"]["conditions"][0]["runs"][0]["artifact_url"] = unsafe_url

                errors = lab.validate_record(record)

                self.assertTrue(any("artifact_url" in error and "HTTPS" in error for error in errors))

    def test_root_relative_artifacts_are_confined_to_the_staged_lab_directory(self) -> None:
        record = published_record()
        record["method"]["conditions"][0]["runs"][0]["artifact_url"] = "/private/run.json"

        errors = lab.validate_record(record)

        self.assertTrue(any("/lab-artifacts/" in error for error in errors))

    def test_numeric_metrics_reject_booleans_and_negative_values(self) -> None:
        record = published_record()
        metrics = record["method"]["conditions"][0]["runs"][0]["metrics"]
        metrics["tool_calls"] = True
        metrics["cost_usd"] = -1

        errors = lab.validate_record(record)

        self.assertTrue(any("tool_calls" in error for error in errors))
        self.assertTrue(any("cost_usd" in error for error in errors))

    def test_numeric_metrics_reject_non_finite_values(self) -> None:
        record = published_record()
        record["method"]["environment"]["budget"]["max_cost_usd_per_run"] = math.inf
        record["method"]["conditions"][0]["runs"][0]["metrics"]["cost_usd"] = math.inf

        errors = lab.validate_record(record)

        self.assertTrue(any("max_cost_usd_per_run" in error for error in errors))
        self.assertTrue(any("cost_usd" in error for error in errors))

    def test_unknown_fields_cannot_hide_non_finite_values(self) -> None:
        record = protocol_record()
        record["unknown_optional"] = math.inf

        errors = lab.validate_record(record)

        self.assertTrue(any("unknown_optional" in error and "finite" in error for error in errors))

    def test_non_standard_json_leaves_both_derived_files_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "index.json").write_text('[{"sentinel": true}]\n', encoding="utf-8")
            (directory / "latest.json").write_text('{"sentinel": true}\n', encoding="utf-8")
            record = protocol_record()
            record["unknown_optional"] = math.inf
            (directory / "protocol.json").write_text(json.dumps(record), encoding="utf-8")

            with self.assertRaises(lab.SkillLabValidationError):
                lab.build_store(directory)

            self.assertEqual(json.loads((directory / "index.json").read_text()), [{"sentinel": True}])
            self.assertEqual(json.loads((directory / "latest.json").read_text()), {"sentinel": True})

    def test_build_writes_deterministic_index_and_latest_after_full_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "drafts").mkdir()
            (directory / "protocol.json").write_text(json.dumps(protocol_record()), encoding="utf-8")
            (directory / "debugging-skill.json").write_text(
                json.dumps(published_record()), encoding="utf-8"
            )
            invalid_draft = protocol_record()
            invalid_draft.pop("title")
            (directory / "drafts" / "ignored.json").write_text(
                json.dumps(invalid_draft), encoding="utf-8"
            )

            entries = lab.build_store(directory)

            index = json.loads((directory / "index.json").read_text(encoding="utf-8"))
            latest = json.loads((directory / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(entries, index)
            self.assertEqual([row["pilot_edition"] for row in index], [1, 0])
            self.assertEqual(index[0]["url"], "/playbook/lab/debugging-skill")
            self.assertRegex(index[0]["content_sha256"], r"^[a-f0-9]{64}$")
            self.assertEqual(latest["slug"], "debugging-skill")

    def test_build_rejects_a_missing_same_origin_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "lab"
            artifact_root = Path(tmp) / "web"
            directory.mkdir()
            (directory / "protocol.json").write_text(
                json.dumps(protocol_record()), encoding="utf-8"
            )
            result = published_record()
            result["method"]["conditions"][0]["runs"][0]["artifact_url"] = (
                "/lab-artifacts/debugging-skill/missing.json"
            )
            (directory / "debugging-skill.json").write_text(
                json.dumps(result), encoding="utf-8"
            )

            with self.assertRaises(lab.SkillLabValidationError) as ctx:
                lab.build_store(directory, check=True, artifact_root=artifact_root)

            self.assertIn("missing same-origin artifact", str(ctx.exception))

    def test_build_accepts_a_deployable_same_origin_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "lab"
            artifact_root = Path(tmp) / "web"
            artifact = artifact_root / "lab-artifacts" / "debugging-skill" / "run.json"
            directory.mkdir()
            artifact.parent.mkdir(parents=True)
            artifact.write_text('{"status":"complete"}\n', encoding="utf-8")
            (directory / "protocol.json").write_text(
                json.dumps(protocol_record()), encoding="utf-8"
            )
            result = published_record()
            result["method"]["conditions"][0]["runs"][0]["artifact_url"] = (
                "/lab-artifacts/debugging-skill/run.json"
            )
            (directory / "debugging-skill.json").write_text(
                json.dumps(result), encoding="utf-8"
            )

            entries = lab.build_store(directory, artifact_root=artifact_root)

            self.assertEqual([entry["pilot_edition"] for entry in entries], [1, 0])

    def test_build_verifies_pinned_same_origin_artifact_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "lab"
            artifact_root = Path(tmp) / "web"
            artifact = artifact_root / "lab-artifacts" / "debugging-skill" / "SKILL.md"
            directory.mkdir()
            artifact.parent.mkdir(parents=True)
            artifact.write_text("# Different skill bytes\n", encoding="utf-8")
            (directory / "protocol.json").write_text(
                json.dumps(protocol_record()), encoding="utf-8"
            )
            result = published_record()
            result["method"]["skill"]["source_url"] = (
                "/lab-artifacts/debugging-skill/SKILL.md"
            )
            (directory / "debugging-skill.json").write_text(
                json.dumps(result), encoding="utf-8"
            )

            with self.assertRaises(lab.SkillLabValidationError) as ctx:
                lab.build_store(directory, artifact_root=artifact_root)

            self.assertIn("SHA-256 does not match", str(ctx.exception))

    def test_check_rejects_stale_derived_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source_path = directory / "protocol.json"
            source_path.write_text(json.dumps(protocol_record()), encoding="utf-8")
            lab.build_store(directory)
            changed = protocol_record()
            changed["summary"] = "Changed after indexing."
            source_path.write_text(json.dumps(changed), encoding="utf-8")

            with self.assertRaises(lab.SkillLabValidationError) as ctx:
                lab.build_store(directory, check=True)

            self.assertIn("stale", str(ctx.exception))

    def test_vercel_build_blocks_a_stale_lab_store(self) -> None:
        script = (lab.ROOT / "scripts" / "vercel_build.py").read_text(encoding="utf-8")

        self.assertIn('"pipeline/build_skill_lab.py", "--check"', script)
        self.assertIn("check=True", script)
        self.assertIn('"lab-artifacts"', script)

    def test_invalid_store_leaves_existing_derived_files_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "index.json").write_text('[{"sentinel": true}]\n', encoding="utf-8")
            (directory / "latest.json").write_text('{"sentinel": true}\n', encoding="utf-8")
            bad = protocol_record()
            bad.pop("question")
            (directory / "protocol.json").write_text(json.dumps(bad), encoding="utf-8")

            with self.assertRaises(lab.SkillLabValidationError):
                lab.build_store(directory)

            self.assertEqual(
                json.loads((directory / "index.json").read_text(encoding="utf-8")),
                [{"sentinel": True}],
            )
            self.assertEqual(
                json.loads((directory / "latest.json").read_text(encoding="utf-8")),
                {"sentinel": True},
            )

    def test_store_rejects_duplicate_ids_and_pilot_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = published_record(1, "debugging-skill")
            second = published_record(1, "testing-skill")
            second["id"] = first["id"]
            (directory / "debugging-skill.json").write_text(json.dumps(first), encoding="utf-8")
            (directory / "testing-skill.json").write_text(json.dumps(second), encoding="utf-8")

            with self.assertRaises(lab.SkillLabValidationError) as ctx:
                lab.build_store(directory, check=True)

            message = str(ctx.exception)
            self.assertIn("duplicate id", message)
            self.assertIn("duplicate pilot_edition", message)

    def test_store_requires_a_contiguous_protocol_first_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "debugging-skill.json").write_text(
                json.dumps(published_record()), encoding="utf-8"
            )

            with self.assertRaises(lab.SkillLabValidationError) as ctx:
                lab.build_store(directory, check=True)

            self.assertIn("contiguous", str(ctx.exception))

    def test_empty_store_removes_stale_derived_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "index.json").write_text('[{"sentinel": true}]\n', encoding="utf-8")
            (directory / "latest.json").write_text('{"sentinel": true}\n', encoding="utf-8")

            entries = lab.build_store(directory)

            self.assertEqual(entries, [])
            self.assertEqual(json.loads((directory / "index.json").read_text()), [])
            self.assertFalse((directory / "latest.json").exists())

    def test_filename_must_match_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "wrong-name.json").write_text(json.dumps(protocol_record()), encoding="utf-8")

            with self.assertRaises(lab.SkillLabValidationError) as ctx:
                lab.build_store(directory, check=True)

            self.assertIn("filename", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
