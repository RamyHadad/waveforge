"""Meaningful smoke tests for plan generation and live configuration edits."""

from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

import yaml

from build_plan_workspace import REGISTER_FIELDS, SIGNOFF_FIELDS, build, validate_manifest
from validate_plan_workspace import validate


def sample_manifest() -> dict:
    def task(task_id: str, dependency: list[str], model: str) -> dict:
        return {
            "id": task_id,
            "title": f"Implement {task_id}",
            "description": f"A bounded result for {task_id}",
            "source_refs": ["L2-L4"],
            "dependencies": dependency,
            "acceptance": ["Result can be reopened"],
            "validation": ["Run focused fixture"],
            "evidence": ["Fixture output"],
            "file_scope": [f"src/{task_id}/**"],
            "model": model,
            "effort": "medium",
            "escalation_eligible": False,
        }

    return {
        "version": 1,
        "project": {"id": "sample", "title": "Sample", "assumptions": [], "open_decisions": []},
        "models": {
            "small-model": {"role": "efficient", "supported_efforts": ["medium"]},
            "large-model": {"role": "balanced", "supported_efforts": ["medium", "high"]},
        },
        "plans": [
            {
                "id": "foundation", "title": "Foundation", "goal": "Create contract",
                "source_refs": ["L2"], "validation": ["Contract test"],
                "evidence": ["Contract report"],
                "waves": [{"id": "wave-1", "title": "First", "tasks": [task("T-001", [], "small-model")]}],
            },
            {
                "id": "integration", "title": "Integration", "goal": "Use contract",
                "source_refs": ["L3-L4"], "validation": ["Integration test"],
                "evidence": ["Integration report"],
                "waves": [{"id": "wave-2", "title": "Second", "tasks": [task("T-002", ["T-001"], "large-model")]}],
            },
        ],
    }


class PlanWorkspaceTests(unittest.TestCase):
    def test_build_validate_and_edit_model_policy(self) -> None:
        base = Path.cwd() / f".skill-test-{uuid.uuid4().hex}"
        base.mkdir()
        try:
            source = base / "source.md"
            source.write_text("# Source\nContract\nIntegration\n", encoding="utf-8")
            manifest = base / "manifest.yaml"
            manifest.write_text(yaml.safe_dump(sample_manifest(), sort_keys=False), encoding="utf-8")
            output = base / "workspace"
            build(source, manifest, output)
            self.assertEqual(validate(output), (2, 2))
            splitting = yaml.safe_load(
                (output / "configuration" / "splitting.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(splitting["mode"], "model_decides")
            with (output / "configuration" / "ownership_signoff.csv").open(
                newline="", encoding="utf-8-sig"
            ) as stream:
                self.assertEqual(list(csv.DictReader(stream)), [])
            policy_path = output / "configuration" / "model_policy.yaml"
            policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            policy["tasks"]["T-001"]["model"] = "large-model"
            policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
            task_path = output / "plans" / "01_foundation" / "waves" / "wave-1" / "tasks" / "T-001.md"
            task_path.write_text(
                task_path.read_text(encoding="utf-8").replace(
                    "Starting model: `small-model`", "Starting model: `large-model`"
                ),
                encoding="utf-8",
            )
            self.assertEqual(validate(output), (2, 2))
            register_path = output / "configuration" / "task_register.csv"
            with register_path.open(newline="", encoding="utf-8-sig") as stream:
                register_rows = list(csv.DictReader(stream))
            register_rows[0]["Status"] = "IN_PROGRESS"
            register_rows[0]["Owner"] = "worker-1"
            register_rows[0]["Actual Model"] = "large-model"
            with register_path.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=REGISTER_FIELDS)
                writer.writeheader()
                writer.writerows(register_rows)
            signoff_path = output / "configuration" / "ownership_signoff.csv"
            claim = dict.fromkeys(SIGNOFF_FIELDS, "")
            claim.update(
                {
                    "Task ID": "T-001", "Event": "CLAIM", "Worker": "worker-1",
                    "Actual Model": "large-model", "Actual Effort": "medium",
                    "Timestamp UTC": "2026-10-02T12:00:00Z",
                }
            )
            with signoff_path.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=SIGNOFF_FIELDS)
                writer.writeheader()
                writer.writerow(claim)
            self.assertEqual(validate(output), (2, 2))
            completion = dict(claim)
            completion.update(
                {"Event": "COMPLETE", "Timestamp UTC": "2026-10-02T13:00:00Z", "Evidence": "tests.txt", "Commit": "abc123"}
            )
            with signoff_path.open("a", newline="", encoding="utf-8") as stream:
                csv.DictWriter(stream, fieldnames=SIGNOFF_FIELDS).writerow(completion)
            register_rows[0]["Status"] = "DONE"
            register_rows[0]["Owner"] = ""
            register_rows[0]["Evidence"] = "tests.txt"
            (output / "tests.txt").write_text("Focused fixture passed\n", encoding="utf-8")
            with register_path.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=REGISTER_FIELDS)
                writer.writeheader()
                writer.writerows(register_rows)
            self.assertEqual(validate(output), (2, 2))
            with self.assertRaises(FileExistsError):
                build(source, manifest, output)
            split_path = base / "split.yaml"
            split_path.write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "mode": "configured",
                        "required_workstreams": ["foundation", "integration"],
                        "max_tasks_per_wave": 1,
                        "rules": ["Keep the two outcomes separate"],
                    }
                ),
                encoding="utf-8",
            )
            configured_output = base / "configured"
            build(source, manifest, configured_output, split_path)
            self.assertEqual(validate(configured_output), (2, 2))
            split_path.write_text(
                yaml.safe_dump({"version": 1, "max_workstreams": 1}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "more workstreams"):
                build(source, manifest, base / "invalid", split_path)
            self.assertFalse((base / "invalid").exists())
        finally:
            if base.resolve().parent != Path.cwd().resolve():
                raise RuntimeError("Refusing to remove test files outside the working directory")
            shutil.rmtree(base)

    def test_reject_dependency_cycle(self) -> None:
        manifest = sample_manifest()
        manifest["plans"][0]["waves"][0]["tasks"][0]["dependencies"] = ["T-002"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
