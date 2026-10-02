# Changelog

Notable changes to WaveForge are recorded here. Release versions follow
semantic version naming; workspace YAML schema versions are separate.

## [Unreleased]

### Added

- A redacted retrospective case study of the real v0.1.0 release request,
  including three workstreams, nine tasks, editable model routes, a generated
  workspace, and links to actual implementation/CI/release outcomes.
- CI build and validation of the case-study manifest and checked-in workspace.

## [0.1.0] - 2026-10-02

### Added

- Skill-guided semantic project decomposition into coherent workstreams,
  dependency waves, and bounded tasks with source references, acceptance,
  validation, and expected evidence.
- Version 1 YAML manifest and optional splitting rules for required
  workstreams and numeric decomposition limits.
- Manifest-driven workspace generation with predictable documents,
  editable configuration, and spreadsheet-readable task records.
- Preservation of one normalized source plan and verification of its SHA-256
  hash. Generation records a timestamp; outputs are not byte-identical runs.
- Per-task planned model and reasoning-effort routes, manually assigned,
  planner-selected, or mixed, with catalog and task-document validation.
- Actual worker claim, block, handoff, and completion ledger, initially empty.
- Dependency existence/cycle checks and completion requirements for `READY`,
  `IN_PROGRESS`, and `DONE` task states.
- Matching active worker claims, duplicate completion prevention, and
  nondecreasing per-task UTC event timestamps.
- Evidence-aware completion: recognizable local evidence references must
  stay inside the workspace and resolve to existing non-empty files; legacy
  notes and external links remain supported without content/network checks.
- A runnable two-workstream, three-task example with different model routes
  and reasoning efforts, usage prompts, and execution-boundary documentation.
- Unittest coverage and GitHub Actions checks on Python 3.10 and 3.14.
- MIT license and release instructions.

### Fixed

- Skill metadata and generated indexes distinguish planned model routing
  from actual worker ownership.

### Compatibility

- Manifest and workspace YAML schemas remain `version: 1`; CSV columns and
  status/event names are unchanged. Existing unexecuted example workspaces
  remain valid.
- Invalid executed states that previously escaped checks now fail validation.
  Local evidence references must point to real files; use `text:` for notes
  resembling paths. Completed tasks cannot be reclaimed; handoffs require a
  new receiving-worker claim.
- Planning and validation remain separate from implementation. No agent
  runtime, model invocation, database, or automatic task execution is added.

[0.1.0]: https://github.com/RamyHadad/waveforge/releases/tag/v0.1.0
