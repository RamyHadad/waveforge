"""Behavior checks for dependency states, ownership history, and evidence."""

from __future__ import annotations

import csv
import shutil
import unittest
import uuid
from pathlib import Path

import yaml

from build_plan_workspace import REGISTER_FIELDS, SIGNOFF_FIELDS, build
from test_plan_workspace import sample_manifest
from validate_plan_workspace import validate


class WorkspaceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path.cwd() / f".skill-test-{uuid.uuid4().hex}"
        self.base.mkdir()
        source = self.base / "source.md"
        source.write_text("# Source\nContract\nIntegration\n", encoding="utf-8")
        manifest = self.base / "manifest.yaml"
        manifest.write_text(yaml.safe_dump(sample_manifest(), sort_keys=False), encoding="utf-8")
        self.root = build(source, manifest, self.base / "workspace")
        self.register_path = self.root / "configuration/task_register.csv"
        self.ledger_path = self.root / "configuration/ownership_signoff.csv"
        with self.register_path.open(newline="", encoding="utf-8-sig") as stream:
            self.register = {row["Task ID"]: row for row in csv.DictReader(stream)}
        self.events: list[dict] = []

    def tearDown(self) -> None:
        if self.base.resolve().parent != Path.cwd().resolve():
            raise RuntimeError("Refusing to remove test files outside the working directory")
        shutil.rmtree(self.base)

    def event(self, task: str, kind: str, worker: str = "worker-1", hour: int = 12,
              evidence: str = "", **changes: str) -> None:
        row = dict.fromkeys(SIGNOFF_FIELDS, "")
        row.update({
            "Task ID": task, "Event": kind, "Worker": worker,
            "Actual Model": "small-model" if task == "T-001" else "large-model",
            "Actual Effort": "medium", "Timestamp UTC": f"2026-10-02T{hour:02}:00:00Z",
            "Evidence": evidence,
        })
        row.update(changes)
        self.events.append(row)

    def claim(self, task: str, worker: str = "worker-1", hour: int = 12) -> None:
        self.event(task, "CLAIM", worker, hour)
        self.register[task].update({
            "Status": "IN_PROGRESS", "Owner": worker,
            "Actual Model": self.events[-1]["Actual Model"],
        })

    def finish(self, task: str, hour: int = 13) -> None:
        worker = self.register[task]["Owner"]
        evidence = f"evidence/{task}.txt"
        target = self.root / evidence
        target.parent.mkdir(exist_ok=True)
        target.write_text("Acceptance fixture passed\n", encoding="utf-8")
        self.event(task, "COMPLETE", worker, hour, evidence)
        self.register[task].update({"Status": "DONE", "Owner": "", "Evidence": evidence})

    def check(self) -> tuple[int, int]:
        for path, fields, rows in (
            (self.register_path, REGISTER_FIELDS, self.register.values()),
            (self.ledger_path, SIGNOFF_FIELDS, self.events),
        ):
            with path.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        return validate(self.root)

    def complete_first(self) -> None:
        self.claim("T-001")
        self.finish("T-001")

    def test_planned_with_unfinished_dependency(self) -> None:
        self.assertEqual(self.check(), (2, 2))

    def test_ready_with_unfinished_dependency(self) -> None:
        self.register["T-002"]["Status"] = "READY"
        with self.assertRaisesRegex(ValueError, "T-002 is READY.*T-001.*PLANNED"):
            self.check()

    def test_ready_with_completed_dependency(self) -> None:
        self.complete_first()
        self.register["T-002"]["Status"] = "READY"
        self.assertEqual(self.check(), (2, 2))

    def test_in_progress_with_unfinished_dependency(self) -> None:
        self.claim("T-002")
        with self.assertRaisesRegex(ValueError, "T-002 is IN_PROGRESS.*T-001"):
            self.check()

    def test_in_progress_without_claim(self) -> None:
        self.register["T-001"].update({"Status": "IN_PROGRESS", "Owner": "worker-1", "Actual Model": "small-model"})
        with self.assertRaisesRegex(ValueError, "lacks matching claim"):
            self.check()

    def test_in_progress_with_completed_dependency_and_claim(self) -> None:
        self.complete_first()
        self.claim("T-002", hour=14)
        self.assertEqual(self.check(), (2, 2))

    def test_in_progress_with_wrong_register_owner(self) -> None:
        self.claim("T-001")
        self.register["T-001"]["Owner"] = "other-worker"
        with self.assertRaisesRegex(ValueError, "lacks matching claim"):
            self.check()

    def test_in_progress_with_wrong_register_model(self) -> None:
        self.claim("T-001")
        self.register["T-001"]["Actual Model"] = "large-model"
        with self.assertRaisesRegex(ValueError, "actual model differs"):
            self.check()

    def test_done_with_unfinished_dependency(self) -> None:
        self.claim("T-002")
        self.finish("T-002")
        with self.assertRaisesRegex(ValueError, "T-002 is DONE.*T-001"):
            self.check()

    def test_done_without_completion(self) -> None:
        self.register["T-001"].update({"Status": "DONE", "Evidence": "Fixture passed"})
        with self.assertRaisesRegex(ValueError, "lacks completion sign-off"):
            self.check()

    def test_done_without_register_evidence(self) -> None:
        self.complete_first()
        self.register["T-001"]["Evidence"] = ""
        with self.assertRaisesRegex(ValueError, "Done task T-001 lacks evidence"):
            self.check()

    def test_done_without_completion_evidence(self) -> None:
        self.complete_first()
        self.events[-1]["Evidence"] = ""
        with self.assertRaisesRegex(ValueError, "Completion for T-001 lacks evidence"):
            self.check()

    def test_done_with_valid_completion_and_evidence(self) -> None:
        self.complete_first()
        self.assertEqual(self.check(), (2, 2))

    def test_duplicate_active_claims(self) -> None:
        self.claim("T-001")
        self.event("T-001", "CLAIM", "worker-2")
        with self.assertRaisesRegex(ValueError, "already claimed"):
            self.check()

    def test_unknown_task_in_ledger(self) -> None:
        self.event("T-999", "CLAIM")
        with self.assertRaisesRegex(ValueError, "unknown task T-999"):
            self.check()

    def test_malformed_task_id_in_ledger(self) -> None:
        self.event("../T-001", "CLAIM")
        with self.assertRaisesRegex(ValueError, "unknown task"):
            self.check()

    def test_completion_without_prior_claim(self) -> None:
        self.event("T-001", "COMPLETE", evidence="Fixture passed")
        with self.assertRaisesRegex(ValueError, "no matching owner"):
            self.check()

    def test_completion_by_other_worker(self) -> None:
        self.claim("T-001")
        self.event("T-001", "COMPLETE", "worker-2", evidence="Fixture passed")
        with self.assertRaisesRegex(ValueError, "no matching owner"):
            self.check()

    def test_duplicate_completion(self) -> None:
        self.complete_first()
        self.events.append(dict(self.events[-1]))
        with self.assertRaisesRegex(ValueError, "Duplicate completion"):
            self.check()

    def test_claim_after_completion(self) -> None:
        self.complete_first()
        self.event("T-001", "CLAIM", hour=14)
        with self.assertRaisesRegex(ValueError, "already completed"):
            self.check()

    def test_completion_timestamp_before_claim(self) -> None:
        self.claim("T-001", hour=13)
        self.finish("T-001", hour=12)
        with self.assertRaisesRegex(ValueError, "timestamp goes backwards"):
            self.check()

    def test_equal_claim_and_completion_timestamps(self) -> None:
        self.claim("T-001", hour=12)
        self.finish("T-001", hour=12)
        self.assertEqual(self.check(), (2, 2))

    def test_empty_worker_identity(self) -> None:
        self.claim("T-001")
        self.events[0]["Worker"] = "  "
        with self.assertRaisesRegex(ValueError, "Incomplete sign-off"):
            self.check()

    def test_missing_and_invalid_timestamps(self) -> None:
        self.claim("T-001")
        for timestamp, message in (
            ("", "Incomplete sign-off"), ("invalid", "Invalid sign-off timestamp"),
            ("2026-10-02T12:00:00", "must be UTC"),
            ("2026-10-02T12:00:00+02:00", "must be UTC"),
        ):
            with self.subTest(timestamp=timestamp):
                self.events[0]["Timestamp UTC"] = timestamp
                with self.assertRaisesRegex(ValueError, message):
                    self.check()

    def test_handoff_requires_new_claim(self) -> None:
        self.claim("T-001")
        self.event("T-001", "HANDOFF", hour=13)
        self.event("T-001", "COMPLETE", "worker-2", hour=14, evidence="Fixture passed")
        with self.assertRaisesRegex(ValueError, "no matching owner"):
            self.check()

    def test_valid_handoff_and_reclaim(self) -> None:
        self.claim("T-001")
        self.event("T-001", "HANDOFF", hour=13)
        self.claim("T-001", "worker-2", hour=14)
        self.finish("T-001", hour=15)
        self.assertEqual(self.check(), (2, 2))

    def test_handoff_chronology(self) -> None:
        self.claim("T-001", hour=13)
        self.event("T-001", "HANDOFF", hour=12)
        with self.assertRaisesRegex(ValueError, "timestamp goes backwards"):
            self.check()

    def test_block_releases_claim(self) -> None:
        self.claim("T-001")
        self.event("T-001", "BLOCK", hour=13)
        self.register["T-001"].update({"Status": "BLOCKED", "Owner": ""})
        self.assertEqual(self.check(), (2, 2))

    def test_active_claim_disagrees_with_status(self) -> None:
        self.claim("T-001")
        self.register["T-001"]["Status"] = "PAUSED"
        with self.assertRaisesRegex(ValueError, "Active claim disagrees"):
            self.check()

    def test_invalid_event(self) -> None:
        self.event("T-001", "SIGN")
        with self.assertRaisesRegex(ValueError, "Invalid sign-off event"):
            self.check()

    def test_missing_empty_and_directory_evidence(self) -> None:
        self.complete_first()
        target = self.root / self.events[-1]["Evidence"]
        target.unlink()
        with self.assertRaisesRegex(ValueError, "file does not exist"):
            self.check()
        target.touch()
        with self.assertRaisesRegex(ValueError, "file is empty"):
            self.check()
        target.unlink()
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "file does not exist"):
            self.check()

    def test_register_evidence_file_checked(self) -> None:
        self.complete_first()
        self.register["T-001"]["Evidence"] = "missing.txt"
        with self.assertRaisesRegex(ValueError, "Done task T-001 evidence file does not exist"):
            self.check()

    def test_evidence_paths_cannot_escape(self) -> None:
        self.complete_first()
        (self.base / "outside.txt").write_text("Outside evidence", encoding="utf-8")
        for reference in ("../outside.txt", "..\\outside.txt", "/tmp/evidence.txt", "C:\\evidence.txt", "C:evidence.txt", "\\\\server\\share\\evidence.txt"):
            with self.subTest(reference=reference):
                self.events[-1]["Evidence"] = reference
                with self.assertRaisesRegex(ValueError, "escapes|workspace-relative"):
                    self.check()

    def test_symlink_evidence_cannot_escape(self) -> None:
        self.complete_first()
        outside = self.base / "outside.txt"
        outside.write_text("Outside evidence", encoding="utf-8")
        link = self.root / "linked.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Creating symlinks is unavailable in this environment")
        self.events[-1]["Evidence"] = "linked.txt"
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.check()

    def test_duplicate_evidence_references(self) -> None:
        self.complete_first()
        evidence = self.events[-1]["Evidence"]
        for duplicate in (f"{evidence};{evidence}", f"{evidence};./{evidence}", "Fixture passed;Fixture passed"):
            with self.subTest(duplicate=duplicate):
                self.events[-1]["Evidence"] = duplicate
                with self.assertRaisesRegex(ValueError, "duplicate evidence"):
                    self.check()

    def test_empty_evidence_list_entry(self) -> None:
        self.complete_first()
        self.events[-1]["Evidence"] += ";"
        with self.assertRaisesRegex(ValueError, "empty evidence entry"):
            self.check()

    def test_legacy_notes_urls_and_markdown_evidence(self) -> None:
        self.complete_first()
        for reference in ("Focused fixture passed", "text:fixture.result",
                          "https://example.invalid/report;version=1",
                          "[report](https://example.invalid/report)",
                          "[report](evidence/T-001.txt)", "file:evidence/T-001.txt"):
            with self.subTest(reference=reference):
                self.events[-1]["Evidence"] = reference
                self.register["T-001"]["Evidence"] = reference
                self.assertEqual(self.check(), (2, 2))

    def test_explicit_note_must_not_be_empty(self) -> None:
        self.complete_first()
        self.events[-1]["Evidence"] = "text:"
        with self.assertRaisesRegex(ValueError, "empty evidence note"):
            self.check()

    def test_malformed_ledger_csv(self) -> None:
        self.check()
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            stream.write("T-001,CLAIM\n")
        with self.assertRaisesRegex(ValueError, "Malformed CSV row"):
            validate(self.root)

    def test_valid_multitask_dependency_chain(self) -> None:
        self.complete_first()
        self.claim("T-002", "worker-2", hour=14)
        self.finish("T-002", hour=15)
        self.assertEqual(self.check(), (2, 2))

    def test_official_example_and_source_hash(self) -> None:
        repo = Path(__file__).resolve().parent.parent
        example = build(repo / "examples/source-plan.md", repo / "examples/decomposition.yaml",
                        self.base / "example", repo / "examples/splitting.yaml")
        self.assertEqual(validate(example), (2, 3))
        (example / "source/ORIGINAL_PLAN.md").write_text("Altered source", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash"):
            validate(example)


if __name__ == "__main__":
    unittest.main()
