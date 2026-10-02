---
name: waveforge
description: Turn a broad project plan into configurable workstreams, dependency waves, task plans, and editable model-routing and ownership records. Use when preparing a plan for coordinated execution across models or repositories; do not use for ordinary single-task coding.
---

# WaveForge

Turn the user's source plan into a portable planning workspace. Preserve the
source, its requirements, and its unresolved choices. The generated workspace
is for planning and coordination; it does not start agents, approve work, or
publish changes.

## Build the plan

1. Read the complete source plan and any governing repository instructions.
   Inspect existing task or milestone documents before creating duplicates.
   For a non-text source, extract a UTF-8 Markdown working copy and retain a
   reference to the original file.
   Choose a new output directory outside existing project source unless the
   user specified a location. Do not overwrite an existing planning workspace.
2. Read any user-provided splitting rules before decomposing. If supplied,
   use the [splitting configuration](references/splitting-configuration.md)
   and honor its boundaries and limits. Otherwise, decide the workstreams,
   waves, and task sizes from the plan itself; do not impose a fixed number of
   plans or tasks. Split by coherent outcomes or workstreams, not merely by
   source headings.
   Give each workstream its own goal, scope, validation, evidence, and waves.
   Order waves by dependencies; make each task a bounded, reviewable change.
   Include acceptance criteria, validation steps, expected evidence, and
   source references for every task. Label inferred work and unresolved
   decisions explicitly. Preserve safety, permission, and publication gates.
3. Determine model routing mode from the user's input. If the user supplies a
   model and effort for a task, preserve that manual choice. If the user
   supplies only a model catalog or delegates routing, select a suitable model
   and effort separately for each unassigned task, preferring the lowest
   plausible route for its requirements. A project may mix manual and planned
   routes. Use models **actually available** in the target environment and put
   their exact IDs and supported efforts in the editable model catalog. Check
   every route against that catalog; flag an unavailable or unsupported manual
   choice rather than silently replacing it. If availability is unknown, ask
   for the catalog before completing executable routes. Never invent a callable
   model or claim a cost estimate without evidence. Reserve stronger routes
   for tasks that justify them or for evidenced escalation.
4. Author a YAML decomposition manifest following
   [the manifest and output contract](references/manifest-format.md). Run
   `scripts/build_plan_workspace.py` with the source plan, manifest, optional
   splitting configuration, and a new output path. The manifest is a plan
   authored from the source, not an automatically inferred substitute for
   engineering judgment.
5. Run `scripts/validate_plan_workspace.py` on the generated workspace. Review
   task ordering, traceability, acceptance coverage, model choices, and open
   decisions against the source. Correct the manifest and regenerate into a
   fresh directory if structural changes are needed; preserve any live
   ownership or evidence records from an existing workspace.

## Ownership and execution boundary

The generated `configuration/` folder holds the editable splitting rules,
manifest, model catalog, per-task model policy, task register, ownership protocol, and an
unsigned CSV sign-off sheet. CSV is a spreadsheet-readable sheet. A model may
record a claim or completion only for work it actually performed; never
pre-fill signatures, timestamps, test results, or commit IDs. One named worker
owns a task at a time. The coordinator checks dependencies and overlapping
file scopes, records the claim, and integrates results. An assigned model in
the policy is a **planned route**, not a claim or permission to mutate source.

Do not silently expand the source plan or turn a planning instruction into
implementation. Keep this skill domain-neutral: project-specific constraints
belong in the generated plan, not in this skill. Respect the user's existing
approval and tool boundaries when the workspace is later executed.

The scripts require Python 3.10+ and PyYAML. They only read the supplied
source/manifest and write the new output directory. They do not call models,
network services, or project tools.

## Model preference for initial planning

Prefer Astra for drafting the input plan and for WaveForge's **first**
decomposition and architecture review when it is available and the user has
not chosen another model. This is a quality preference, not a requirement or
an automatic model switch: the active chat model cannot be changed by this
skill. If Astra is unavailable, proceed with the strongest suitable available
model. Record the actual source-plan and first-decomposition models in the
manifest's `project` fields when known; generated configuration uses `unknown`
otherwise. Later task
implementation follows the generated per-task model policy; it does not
inherit the initial Astra preference.
