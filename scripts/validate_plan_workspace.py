"""Check a generated planning workspace for structural and routing drift."""

from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import datetime
from pathlib import Path

import yaml

from build_plan_workspace import (
    REGISTER_FIELDS,
    SIGNOFF_FIELDS,
    UniqueKeyLoader,
    read_split_config,
    validate_manifest,
    validate_split_config,
)


def _csv(path: Path, expected_fields: list[str]) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != expected_fields:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        return list(reader)


def validate(root: Path) -> tuple[int, int]:
    config = root / "configuration"
    manifest = yaml.load(
        (config / "manifest.yaml").read_text(encoding="utf-8"),
        Loader=UniqueKeyLoader,
    )
    tasks = validate_manifest(manifest)
    split_config = read_split_config(config / "splitting.yaml")
    validate_split_config(split_config, manifest)
    project = yaml.safe_load((config / "project.yaml").read_text(encoding="utf-8"))
    source_text = (root / "source" / "ORIGINAL_PLAN.md").read_text(encoding="utf-8")
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if project["source_sha256"] != digest:
        raise ValueError("Preserved source hash does not match project.yaml")
    catalog = yaml.load(
        (config / "model_catalog.yaml").read_text(encoding="utf-8"),
        Loader=UniqueKeyLoader,
    )
    if catalog.get("version") != 1 or not isinstance(catalog.get("models"), dict):
        raise ValueError("Invalid model catalog")
    policy = yaml.load(
        (config / "model_policy.yaml").read_text(encoding="utf-8"),
        Loader=UniqueKeyLoader,
    )
    if policy.get("version") != 1 or set(policy.get("tasks", {})) != set(tasks):
        raise ValueError("Model policy task IDs do not match manifest")

    register_rows = _csv(config / "task_register.csv", REGISTER_FIELDS)
    register = {row["Task ID"]: row for row in register_rows}
    if len(register) != len(register_rows) or set(register) != set(tasks):
        raise ValueError("Task register IDs do not match manifest")
    allowed_statuses = {"PLANNED", "READY", "IN_PROGRESS", "DONE", "BLOCKED", "PAUSED"}
    for plan_number, plan in enumerate(manifest["plans"], 1):
        plan_dir = root / "plans" / f"{plan_number:02d}_{plan['id']}"
        for name in ("PLAN.md", "VALIDATION.md", "EVIDENCE.md"):
            if not (plan_dir / name).is_file():
                raise ValueError(f"Missing {plan_dir / name}")
        for wave in plan["waves"]:
            wave_dir = plan_dir / "waves" / wave["id"]
            if not (wave_dir / "WAVE.md").is_file():
                raise ValueError(f"Missing {wave_dir / 'WAVE.md'}")
            for task in wave["tasks"]:
                task_id = task["id"]
                task_path = wave_dir / "tasks" / f"{task_id}.md"
                text = task_path.read_text(encoding="utf-8")
                route = policy["tasks"][task_id]
                model = route.get("model")
                if model not in catalog["models"]:
                    raise ValueError(f"Unknown policy model for {task_id}: {model}")
                if route.get("effort") not in catalog["models"][model].get("supported_efforts", []):
                    raise ValueError(f"Unsupported policy effort for {task_id}")
                if type(route.get("escalation_eligible")) is not bool:
                    raise ValueError(f"Invalid escalation eligibility for {task_id}")
                route_line = (
                    f"Starting model: `{route['model']}` · Effort: `{route['effort']}`."
                )
                if route_line not in text:
                    raise ValueError(f"Task file model/effort differs for {task_id}")
                row = register[task_id]
                if row["Plan"] != plan["id"] or row["Wave"] != wave["id"]:
                    raise ValueError(f"Task register location differs for {task_id}")
                dependencies = row["Dependencies"].split(";") if row["Dependencies"] else []
                if any(item not in tasks for item in dependencies):
                    raise ValueError(f"Task register has an unknown dependency for {task_id}")
                expected_dependencies = ", ".join(dependencies) or "None"
                if f"Dependencies: {expected_dependencies}" not in text:
                    raise ValueError(f"Task file dependencies differ for {task_id}")
                if row["Status"] not in allowed_statuses:
                    raise ValueError(f"Invalid status for {task_id}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"Register dependency cycle includes {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in filter(None, register[task_id]["Dependencies"].split(";")):
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in register:
        visit(task_id)

    signoffs = _csv(config / "ownership_signoff.csv", SIGNOFF_FIELDS)
    active: dict[str, str] = {}
    completed: set[str] = set()
    for row in signoffs:
        task_id = row["Task ID"]
        event = row["Event"]
        worker = row["Worker"]
        if task_id not in tasks:
            raise ValueError(f"Sign-off references unknown task {task_id}")
        if event not in {"CLAIM", "COMPLETE", "BLOCK", "HANDOFF"}:
            raise ValueError(f"Invalid sign-off event for {task_id}")
        if not all(row[field].strip() for field in ("Worker", "Actual Model", "Actual Effort", "Timestamp UTC")):
            raise ValueError(f"Incomplete sign-off row for {task_id}")
        try:
            timestamp = datetime.fromisoformat(row["Timestamp UTC"].replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"Invalid sign-off timestamp for {task_id}") from error
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError(f"Sign-off timestamp must be UTC for {task_id}")
        if event == "CLAIM":
            if task_id in active:
                raise ValueError(f"Task already claimed: {task_id}")
            active[task_id] = worker
        else:
            if active.get(task_id) != worker:
                raise ValueError(f"Sign-off event has no matching owner for {task_id}")
            del active[task_id]
            if event == "COMPLETE":
                if not row["Evidence"].strip():
                    raise ValueError(f"Completion lacks evidence for {task_id}")
                completed.add(task_id)
    for task_id, row in register.items():
        status = row["Status"]
        if status == "IN_PROGRESS":
            if active.get(task_id) != row["Owner"] or not row["Actual Model"]:
                raise ValueError(f"In-progress task lacks matching claim: {task_id}")
        elif task_id in active:
            raise ValueError(f"Active claim disagrees with register status for {task_id}")
        if status == "DONE" and (task_id not in completed or not row["Evidence"].strip()):
            raise ValueError(f"Done task lacks completion sign-off or evidence: {task_id}")
    if not (config / "OWNERSHIP_PROTOCOL.md").is_file():
        raise ValueError("Missing ownership protocol")
    if not (root / "README.md").is_file():
        raise ValueError("Missing workspace index")
    return len(manifest["plans"]), len(tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    plans, tasks = validate(args.workspace.resolve())
    print(f"Validated {plans} workstream plans and {tasks} tasks")


if __name__ == "__main__":
    main()
