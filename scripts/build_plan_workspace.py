"""Materialize a portable planning workspace from an authored YAML manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")
REGISTER_FIELDS = [
    "Task ID", "Plan", "Wave", "Title", "Status", "Dependencies",
    "File Scope", "Owner", "Actual Model", "Updated UTC", "Evidence",
]
SIGNOFF_FIELDS = [
    "Task ID", "Event", "Worker", "Actual Model", "Actual Effort",
    "Timestamp UTC", "File Scope", "Evidence", "Commit", "Notes",
]
DEFAULT_SPLITTING = {
    "version": 1,
    "mode": "model_decides",
    "required_workstreams": [],
    "min_workstreams": None,
    "max_workstreams": None,
    "max_waves_per_workstream": None,
    "max_tasks_per_wave": None,
    "rules": [],
}


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    result: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def read_manifest(path: Path) -> dict:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise ValueError("Manifest must be a YAML mapping")
    validate_manifest(value)
    return value


def read_split_config(path: Path | None) -> dict:
    if path is None:
        return dict(DEFAULT_SPLITTING)
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise ValueError("Splitting configuration must be a YAML mapping")
    unknown = set(value) - set(DEFAULT_SPLITTING)
    if unknown:
        raise ValueError(f"Unknown splitting configuration keys: {sorted(unknown)}")
    result = dict(DEFAULT_SPLITTING)
    result["mode"] = "configured"
    result.update(value)
    return result


def validate_split_config(config: dict, manifest: dict) -> None:
    if config.get("version") != 1:
        raise ValueError("Only splitting configuration version 1 is supported")
    if config.get("mode") not in {"model_decides", "configured"}:
        raise ValueError("Splitting mode must be model_decides or configured")
    required = _strings(config.get("required_workstreams"), "required_workstreams", required=False)
    for plan_id in required:
        _id(plan_id, "required_workstreams entry")
    if len(set(required)) != len(required):
        raise ValueError("Duplicate required workstream ID")
    limits = (
        "min_workstreams", "max_workstreams", "max_waves_per_workstream",
        "max_tasks_per_wave",
    )
    for key in limits:
        value = config.get(key)
        if value is not None and (type(value) is not int or value < 1):
            raise ValueError(f"{key} must be a positive integer or null")
    _strings(config.get("rules"), "rules", required=False)
    plans = manifest["plans"]
    plan_ids = {plan["id"] for plan in plans}
    if not set(required).issubset(plan_ids):
        raise ValueError(f"Required workstreams missing: {sorted(set(required) - plan_ids)}")
    minimum = config["min_workstreams"]
    maximum = config["max_workstreams"]
    if minimum is not None and len(plans) < minimum:
        raise ValueError("Plan has fewer workstreams than configured")
    if maximum is not None and len(plans) > maximum:
        raise ValueError("Plan has more workstreams than configured")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("min_workstreams exceeds max_workstreams")
    for plan in plans:
        wave_limit = config["max_waves_per_workstream"]
        if wave_limit is not None and len(plan["waves"]) > wave_limit:
            raise ValueError(f"Too many waves in workstream {plan['id']}")
        for wave in plan["waves"]:
            task_limit = config["max_tasks_per_wave"]
            if task_limit is not None and len(wave["tasks"]) > task_limit:
                raise ValueError(f"Too many tasks in wave {plan['id']}/{wave['id']}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value.strip()


def _id(value: object, label: str) -> str:
    result = _text(value, label)
    if not ID_PATTERN.fullmatch(result):
        raise ValueError(f"{label} has an unsafe ID: {result!r}")
    return result


def _strings(value: object, label: str, *, required: bool = True) -> list[str]:
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"{label} must be a {'nonempty ' if required else ''}list")
    return [_text(item, label) for item in value]


def validate_manifest(data: dict) -> dict[str, tuple[int, int, dict]]:
    if data.get("version") != 1:
        raise ValueError("Only manifest version 1 is supported")
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("project must be a mapping")
    _id(project.get("id"), "project.id")
    _text(project.get("title"), "project.title")
    for key in ("source_plan_model", "first_decomposition_model"):
        if key in project:
            _text(project[key], f"project.{key}")
    for key in ("assumptions", "open_decisions"):
        _strings(project.get(key, []), f"project.{key}", required=False)

    models = data.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("models must list available model IDs")
    for model_id, spec in models.items():
        _text(model_id, "model ID")
        if not isinstance(spec, dict):
            raise ValueError(f"Model {model_id} must be a mapping")
        _text(spec.get("role"), f"models.{model_id}.role")
        _strings(spec.get("supported_efforts"), f"models.{model_id}.supported_efforts")

    plans = data.get("plans")
    if not isinstance(plans, list) or not plans:
        raise ValueError("plans must be a nonempty list")
    plan_ids: set[str] = set()
    tasks: dict[str, tuple[int, int, dict]] = {}
    for plan_index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            raise ValueError("Each plan must be a mapping")
        plan_id = _id(plan.get("id"), "plan.id")
        if plan_id in plan_ids:
            raise ValueError(f"Duplicate plan ID: {plan_id}")
        plan_ids.add(plan_id)
        for key in ("title", "goal"):
            _text(plan.get(key), f"plan {plan_id}.{key}")
        for key in ("source_refs", "validation", "evidence"):
            _strings(plan.get(key), f"plan {plan_id}.{key}")
        for key in ("assumptions", "open_decisions"):
            _strings(plan.get(key, []), f"plan {plan_id}.{key}", required=False)
        waves = plan.get("waves")
        if not isinstance(waves, list) or not waves:
            raise ValueError(f"Plan {plan_id} needs at least one wave")
        wave_ids: set[str] = set()
        for wave_index, wave in enumerate(waves):
            if not isinstance(wave, dict):
                raise ValueError(f"Plan {plan_id} has a malformed wave")
            wave_id = _id(wave.get("id"), "wave.id")
            if wave_id in wave_ids:
                raise ValueError(f"Duplicate wave ID in {plan_id}: {wave_id}")
            wave_ids.add(wave_id)
            _text(wave.get("title"), f"wave {wave_id}.title")
            wave_tasks = wave.get("tasks")
            if not isinstance(wave_tasks, list) or not wave_tasks:
                raise ValueError(f"Wave {wave_id} needs at least one task")
            for task in wave_tasks:
                if not isinstance(task, dict):
                    raise ValueError(f"Wave {wave_id} has a malformed task")
                task_id = _id(task.get("id"), "task.id")
                if task_id in tasks:
                    raise ValueError(f"Duplicate task ID: {task_id}")
                for key in ("title", "description"):
                    _text(task.get(key), f"task {task_id}.{key}")
                for key in (
                    "source_refs", "acceptance", "validation", "evidence", "file_scope"
                ):
                    _strings(task.get(key), f"task {task_id}.{key}")
                for key in ("dependencies", "assumptions", "open_decisions"):
                    _strings(task.get(key, []), f"task {task_id}.{key}", required=False)
                model = _text(task.get("model"), f"task {task_id}.model")
                effort = _text(task.get("effort"), f"task {task_id}.effort")
                if model not in models:
                    raise ValueError(f"Task {task_id} uses unknown model {model}")
                if effort not in models[model]["supported_efforts"]:
                    raise ValueError(f"Task {task_id} uses unsupported effort {effort}")
                if type(task.get("escalation_eligible")) is not bool:
                    raise ValueError(f"Task {task_id} needs boolean escalation_eligible")
                tasks[task_id] = (plan_index, wave_index, task)

    for task_id, (plan_index, wave_index, task) in tasks.items():
        for dependency in task.get("dependencies", []):
            if dependency not in tasks:
                raise ValueError(f"Task {task_id} has unknown dependency {dependency}")
            dep_plan, dep_wave, _ = tasks[dependency]
            if dep_plan == plan_index and dep_wave > wave_index:
                raise ValueError(f"Task {task_id} depends on a later wave: {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"Dependency cycle includes {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in tasks[task_id][2].get("dependencies", []):
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)
    return tasks


def _bullets(items: list[str], empty: str = "None recorded.") -> str:
    return "\n".join(f"- {item}" for item in items) if items else empty


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build(
    source: Path, manifest_path: Path, output: Path,
    split_config_path: Path | None = None,
) -> Path:
    data = read_manifest(manifest_path)
    split_config = read_split_config(split_config_path)
    validate_split_config(split_config, data)
    if not source.is_file():
        raise ValueError(f"Source plan does not exist: {source}")
    source_text = source.read_text(encoding="utf-8-sig")
    if not source_text.strip():
        raise ValueError("Source plan is empty")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    source_dir = output / "source"
    config = output / "configuration"
    plan_root = output / "plans"
    for directory in (source_dir, config, plan_root):
        directory.mkdir()
    (source_dir / "ORIGINAL_PLAN.md").write_text(source_text, encoding="utf-8")
    (config / "manifest.yaml").write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
    _write_yaml(config / "splitting.yaml", split_config)
    _write_yaml(
        config / "project.yaml",
        {
            "version": 1,
            "id": data["project"]["id"],
            "title": data["project"]["title"],
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "source_name": source.name,
            "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "assumptions": data["project"].get("assumptions", []),
            "open_decisions": data["project"].get("open_decisions", []),
            "planning_provenance": {
                "source_plan_model": data["project"].get("source_plan_model", "unknown"),
                "first_decomposition_model": data["project"].get("first_decomposition_model", "unknown"),
            },
        },
    )
    _write_yaml(config / "model_catalog.yaml", {"version": 1, "models": data["models"]})

    register_rows: list[dict] = []
    routes: dict[str, dict] = {}
    index_lines = [f"# {data['project']['title']}", "", "Source: [preserved plan](source/ORIGINAL_PLAN.md).", "", "## Workstream plans", ""]
    for plan_number, plan in enumerate(data["plans"], 1):
        plan_dir = plan_root / f"{plan_number:02d}_{plan['id']}"
        waves_dir = plan_dir / "waves"
        waves_dir.mkdir(parents=True)
        index_lines.append(f"- [{plan['title']}](plans/{plan_dir.name}/PLAN.md)")
        wave_links: list[str] = []
        for wave in plan["waves"]:
            wave_dir = waves_dir / wave["id"]
            task_dir = wave_dir / "tasks"
            task_dir.mkdir(parents=True)
            wave_links.append(f"- [{wave['title']}](waves/{wave['id']}/WAVE.md)")
            task_links: list[str] = []
            for task in wave["tasks"]:
                task_id = task["id"]
                routes[task_id] = {
                    "model": task["model"],
                    "effort": task["effort"],
                    "escalation_eligible": task["escalation_eligible"],
                }
                register_rows.append(
                    {
                        "Task ID": task_id,
                        "Plan": plan["id"],
                        "Wave": wave["id"],
                        "Title": task["title"],
                        "Status": "PLANNED",
                        "Dependencies": ";".join(task.get("dependencies", [])),
                        "File Scope": ";".join(task["file_scope"]),
                        "Owner": "",
                        "Actual Model": "",
                        "Updated UTC": "",
                        "Evidence": "",
                    }
                )
                task_links.append(f"- [{task_id}: {task['title']}](tasks/{task_id}.md)")
                task_doc = f"""# {task_id}: {task['title']}

Plan: {plan['title']} · Wave: {wave['title']}

Starting model: `{task['model']}` · Effort: `{task['effort']}`. The authoritative route is in `configuration/model_policy.yaml` at the workspace root.

## Scope

{task['description']}

Source references: {', '.join(task['source_refs'])}

Dependencies: {', '.join(task.get('dependencies', [])) or 'None'}

Estimated file scope:
{_bullets(task['file_scope'])}

## Acceptance

{_bullets(task['acceptance'])}

## Validation

{_bullets(task['validation'])}

## Evidence to record

{_bullets(task['evidence'])}

## Assumptions and open decisions

Assumptions:
{_bullets(task.get('assumptions', []))}

Open decisions:
{_bullets(task.get('open_decisions', []))}
"""
                (task_dir / f"{task_id}.md").write_text(task_doc, encoding="utf-8")
            wave_doc = f"""# {wave['title']}

Workstream: [{plan['title']}](../../PLAN.md)

Tasks in this wave:

{chr(10).join(task_links)}

Start each task only when its own dependencies are complete. Check file-scope overlap and the ownership register before dispatch.
"""
            (wave_dir / "WAVE.md").write_text(wave_doc, encoding="utf-8")
        (plan_dir / "PLAN.md").write_text(
            f"# {plan['title']}\n\n{plan['goal']}\n\nSource references: {', '.join(plan['source_refs'])}\n\n"
            f"## Waves\n\n{chr(10).join(wave_links)}\n\n"
            f"## Assumptions\n\n{_bullets(plan.get('assumptions', []))}\n\n"
            f"## Open decisions\n\n{_bullets(plan.get('open_decisions', []))}\n\n"
            f"See [validation](VALIDATION.md) and [evidence](EVIDENCE.md).\n",
            encoding="utf-8",
        )
        (plan_dir / "VALIDATION.md").write_text(
            f"# Validation: {plan['title']}\n\n{_bullets(plan['validation'])}\n",
            encoding="utf-8",
        )
        (plan_dir / "EVIDENCE.md").write_text(
            f"# Evidence: {plan['title']}\n\nExpected evidence:\n\n{_bullets(plan['evidence'])}\n\n"
            "Record actual evidence paths and results in the task register when work is done.\n",
            encoding="utf-8",
        )

    _write_yaml(
        config / "model_policy.yaml",
        {
            "version": 1,
            "escalation": {
                "automatic": False,
                "requires": [
                    "recorded acceptance failure",
                    "diagnosed model-reasoning bottleneck rather than missing data or tools",
                    "unchanged task ownership, permissions, and validation gates",
                ],
                "default_max_consultations_per_task": 1,
            },
            "tasks": routes,
        },
    )
    _write_csv(config / "task_register.csv", REGISTER_FIELDS, register_rows)
    _write_csv(config / "ownership_signoff.csv", SIGNOFF_FIELDS, [])
    (config / "OWNERSHIP_PROTOCOL.md").write_text(
        """# Worker ownership and sign-off

`model_policy.yaml` gives planned model and effort for each task. `task_register.csv`
tracks execution state. `ownership_signoff.csv` is the spreadsheet-readable,
append-only record of actual work; it deliberately starts unsigned.

Before work, the coordinator verifies completed dependencies, checks file-scope
overlap, chooses the configured worker, and writes one `CLAIM` event with the
real worker ID, actual model/effort, timestamp, and file scope. Set the register
task to `IN_PROGRESS` with the same owner and actual model. Only one worker may
own a task at a time. Shared registers have one coordinator writer; workers
return evidence instead of concurrently editing the sheets.

On completion, record validation results, evidence paths, and commit ID in a
`COMPLETE` event, then set the task to `DONE` only if acceptance is met. Use a
`BLOCK` or `HANDOFF` event when appropriate, and update register status and
owner. Do not fabricate signatures or evidence. A model name is an attribution
of actual execution, not a cryptographic signature or a grant of authority.

Validation enforces these current-state rules:
- `PLANNED` may retain unfinished dependencies.
- `READY`, `IN_PROGRESS`, and `DONE` require every dependency to be `DONE`.
- `IN_PROGRESS` requires one active claim matching the register's owner and
  actual model. An active claim is incompatible with any other status.
- `DONE` requires a valid completion event and evidence in both the completion
  and register. Evidence contents and acceptance outcomes still need review.

Ledger rows are append-only. Events for a task have nondecreasing UTC
timestamps; equal times are allowed. `COMPLETE`, `BLOCK`, and `HANDOFF` must
come from the active claimant and release that claim. A receiving worker must
write a new `CLAIM` after a handoff before completing. Completion cannot be
duplicated, and no later event may reopen a completed task. `BLOCKED` and
`PAUSED` impose no additional dependency rule and cannot have an active claim.
The schema does not define a receiving-worker field or prescribe a register
status immediately after handoff; coordinate the new claim explicitly.

Evidence fields accept notes, HTTP(S) links, or workspace-relative file paths.
Separate multiple entries with semicolons. Recognizable file references
(paths with a separator, compact filenames with an extension, Markdown links
to local files, or explicit `file:` references) must resolve inside the
workspace to existing non-empty files. Use `text:` to disambiguate a note that
looks like a path. Empty and duplicate entries are rejected. External links
are not fetched. Legacy free-text notes remain valid; validation cannot prove
their contents or infer all extensionless filenames as file references.

The planning workspace never authorizes production publication or bypasses
project-specific permissions. Escalation to a stronger model requires a
recorded reason, failed acceptance evidence, and the same task ownership gate.
""",
        encoding="utf-8",
    )
    index_lines.extend(
        [
            "", "## Editable configuration", "",
            "- [Manifest](configuration/manifest.yaml)",
            "- [Splitting rules](configuration/splitting.yaml)",
            "- [Model catalog](configuration/model_catalog.yaml)",
            "- [Per-task model policy](configuration/model_policy.yaml)",
            "- [Task register](configuration/task_register.csv)",
            "- [Worker ownership sign-off sheet](configuration/ownership_signoff.csv)",
            "- [Ownership protocol](configuration/OWNERSHIP_PROTOCOL.md)", "",
            "The sign-off sheet is intentionally empty until actual workers claim tasks.",
        ]
    )
    (output / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="UTF-8 source plan")
    parser.add_argument("--manifest", type=Path, required=True, help="Authored YAML decomposition")
    parser.add_argument("--split-config", type=Path, help="Optional YAML splitting rules")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    output = build(
        args.source.resolve(), args.manifest.resolve(), args.out.resolve(),
        args.split_config.resolve() if args.split_config else None,
    )
    print(f"Created planning workspace: {output}")


if __name__ == "__main__":
    main()
