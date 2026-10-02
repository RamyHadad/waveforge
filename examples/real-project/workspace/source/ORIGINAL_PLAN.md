# Release preparation and validator hardening

This is the normalized, redacted source request for the real WaveForge v0.1.0
release. It preserves the requested outcomes and constraints while omitting
machine paths, attachment identifiers, and personal contact details.

## R01 — Architecture and compatibility

Read the repository and understand its manifest, model policy, task register,
ownership ledger, builder, validator, examples, and CI contracts. Preserve
existing schema fields and valid example workspaces. Keep the core purpose
planning, decomposition, routing, traceability, generation, and validation.
Do not add an agent runtime, database, LLM validation, or task execution.
Keep validation deterministic and preserve the normalized source plan/hash.

## R02 — Terminology and skill metadata

Replace wording that confuses planned model routes with actual task ownership
throughout metadata, documentation, examples, and generated output. Ownership
requires an actual worker claim; completion requires evidence. Use supported
metadata fields and provide a useful default prompt for validated planning.

## R03 — Task states and dependencies

Preserve the existing statuses. `PLANNED` may have unfinished dependencies.
`READY`, `IN_PROGRESS`, and `DONE` require every declared dependency to be
`DONE`. In-progress tasks also require a valid corresponding active claim.
Done tasks also require valid corresponding completion and evidence. Report
actionable errors identifying the task and unfinished dependency.

## R04 — Ownership lifecycle and chronology

Reject unknown or malformed task references, invalid mandatory worker
identity, duplicate active claims, completion without a matching claimant,
duplicate completion, and claims against completed tasks. Follow the existing
handoff protocol and document ambiguities rather than silently changing it.
When timestamps are required by the current schema, reject events that go
backwards for a task. Keep equal timestamps valid.

## R05 — Evidence validation

For identifiable local evidence references, check workspace containment,
file existence, non-empty content, and invalid or duplicate entries. Preserve
existing valid non-file evidence formats. Do not fetch external resources.
Acceptance judgments that cannot be verified deterministically remain reviewer
responsibilities.

## R06 — Behavioral regression tests

Keep existing tests and add meaningful cases for each invariant. Cover ready,
in-progress, and done tasks with unfinished/completed dependencies; missing
claims/completions/evidence; duplicate claims/completions; unknown tasks;
impossible chronology; a valid dependency chain; and the existing example.
Use the current unittest conventions and minimal dependencies.

## R07 — Documentation agreement

Update the README, skill, ownership instructions, references, and relevant
examples to match actual validation behavior. Clearly distinguish planned
routing, claimed work, and completed work with evidence. Search for stale
terminology and obsolete first-upload documentation references.

## R08 — Release preparation

Replace the first-upload guide with a release guide covering checks, changelog,
tag naming, notes, compatibility, and future release creation. Add an initial
changelog entry for `0.1.0` dated `2026-10-02`, describing actual capabilities.
Keep release metadata consistent without introducing package versioning.

## R09 — GitHub CI

Review official checkout and Python setup Actions against their latest stable
supported majors. Preserve the Python 3.10/3.14 matrix and run the complete
suite plus example builder/validator. Change runner pinning only if justified.

## R10 — Verification and publication gates

Run the complete tests, build and validate the official example, validate
existing fixtures, check documentation and stale references, and review the
diff. After validation passes, if authentication and permissions are available,
publish the annotated `v0.1.0` tag and GitHub Release and update relevant
description/topics. Otherwise provide exact maintainer commands. Report actual
results and operations; do not fabricate execution, signatures, or evidence.
