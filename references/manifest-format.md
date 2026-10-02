# Decomposition manifest and output contract

The skill authors a UTF-8 YAML manifest after reading the input plan. The
builder requires `version: 1`, a project ID/title, a catalog of actual model
IDs, and at least one plan containing at least one wave and task. IDs use
letters, numbers, underscores, and hyphens; task IDs are unique globally.
Keep descriptions specific to the source project. The short example below is
only a shape guide.

```yaml
version: 1
project:
  id: sample-project
  title: Sample project
  # Optional factual provenance: source_plan_model and first_decomposition_model.
  assumptions: []
  open_decisions: []
models:
  gpt-6-sol:
    role: balanced coding
    supported_efforts: [medium, high]
plans:
  - id: foundation
    title: Foundation
    goal: Establish the shared contract
    source_refs: ["L4-L12"]
    validation: ["Contract checks pass"]
    evidence: ["Test output and reviewed contract diff"]
    waves:
      - id: wave-1
        title: Contract first
        tasks:
          - id: T-001
            title: Define the contract
            description: Define the data structures and failure states
            source_refs: ["L4-L8"]
            dependencies: []
            acceptance: ["Unknown versions fail closed"]
            validation: ["Run the contract fixture"]
            evidence: ["Fixture result and diff"]
            file_scope: ["src/contracts/**"]
            model: gpt-6-sol
            effort: medium
            escalation_eligible: false
```

For each plan, include the source references, validation outcomes, and evidence
needed to review its full scope. For each task, include source references,
dependencies, acceptance criteria, validation procedure, expected evidence,
and a file-scope estimate. A source reference can be a line range in the
preserved normalized source or a stable section/document identifier. Put
newly inferred requirements in `assumptions` and explain why; unresolved
choices go in `open_decisions`. Do not disguise them as source requirements.

Each task's `model` and `effort` form its planned route. Different tasks may use
different models and effort levels. Preserve user-specified routes; for tasks
without a route, the planning agent selects from the models and supported
efforts actually available in the target environment. The builder rejects
unknown models and unsupported efforts. After generation, the live route is in
`configuration/model_policy.yaml`, while this manifest retains the initial
choice.

The builder creates:

```text
<output>/
  README.md
  source/ORIGINAL_PLAN.md
  configuration/
    manifest.yaml
    splitting.yaml
    project.yaml
    model_catalog.yaml
    model_policy.yaml
    task_register.csv
    ownership_signoff.csv
    OWNERSHIP_PROTOCOL.md
  plans/<number>_<plan-id>/
    PLAN.md
    VALIDATION.md
    EVIDENCE.md
    waves/<wave-id>/
      WAVE.md
      tasks/<task-id>.md
```

Run it with paths to the normalized source and the authored manifest:

```text
python scripts/build_plan_workspace.py --source <plan.md> --manifest <decomposition.yaml> --out <new-workspace>
python scripts/build_plan_workspace.py --source <plan.md> --manifest <decomposition.yaml> --split-config <splitting.yaml> --out <new-workspace>
python scripts/validate_plan_workspace.py <new-workspace>
```

`splitting.yaml` records whether the model chose the decomposition or followed
user rules. See [splitting configuration](splitting-configuration.md) for the
editable format. `model_policy.yaml` is the live planned routing source. `task_register.csv` is
the live execution-status and dependency source. `manifest.yaml` preserves the
authored decomposition used to generate the initial workspace; its model and
dependency values are an initial snapshot, not a second live authority.
`ownership_signoff.csv` is an append-only record of
actual worker claims, handoffs, and completion evidence; it starts with only
headers. The generated `OWNERSHIP_PROTOCOL.md` explains how to use them.
These files are in `configuration/` so a user can inspect or edit them without
searching through task prose. Task files repeat the starting model/effort and
dependencies for convenience; after editing live configuration, update the
corresponding task file and validate. Never regenerate over active claims.

The validator checks structure, unique IDs, known dependencies, cycles,
initial same-plan wave order, model IDs and supported efforts, task file presence,
and consistency between live configuration and task files. It also enforces
dependency completion for ready/in-progress/done states, actual worker claims,
event chronology, and completion evidence as described in
[task states, ownership, and evidence](ownership-and-evidence.md). It cannot judge
whether the decomposition faithfully implements the source; the skill must
review that separately.
