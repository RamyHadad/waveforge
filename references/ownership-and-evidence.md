# Task states, ownership, and evidence

`model_policy.yaml` records a **planned route**: model ID, reasoning effort, and
escalation eligibility. It does not establish ownership. Ownership starts with
an actual worker's `CLAIM` in `ownership_signoff.csv`. Completion is supported
by a valid `COMPLETE` event and evidence, with acceptance reviewed by the
coordinator.

## Current task state

The live dependencies and statuses come from `task_register.csv`.

| Status | Validator requirement |
| --- | --- |
| `PLANNED` | Dependencies may be unfinished; no active claim |
| `READY` | All declared dependencies are `DONE`; no active claim |
| `IN_PROGRESS` | All dependencies are `DONE`; one active claim matches `Owner` and `Actual Model` |
| `DONE` | All dependencies are `DONE`; valid completion record and evidence in the ledger and register; no active claim |
| `BLOCKED`, `PAUSED` | No active claim; no additional dependency-completion requirement |

The validator checks the snapshot and append-only ledger, not an unrecorded
history of register edits. It retains checks for dependency existence, cycles,
initial manifest wave order, source hash, and agreement between task documents
and live configuration.

## Ownership ledger

Every event references an existing task and supplies non-empty `Worker`,
`Actual Model`, `Actual Effort`, and `Timestamp UTC`. Timestamps must be valid,
timezone-aware UTC values and nondecreasing **per task** in CSV order. Equal
timestamps are allowed; unrelated tasks need not have globally sorted events.

- `CLAIM`: starts ownership when there is no active claim and the task has not
  already completed. Multiple simultaneous claims are rejected.
- `COMPLETE`: requires the active claimant, ends the claim, and supplies valid
  evidence. Duplicate completion and later events on a completed task fail.
- `BLOCK` and `HANDOFF`: require the active claimant and release ownership. A
  receiving or resuming worker writes a new `CLAIM` before completion.

Existing schema ambiguity is preserved: there is no handoff receiver field,
and no mandated register status immediately after handoff. The coordinator
sets an appropriate status and records the next worker's claim. A historical
completion record need not force a register state by itself; conversely a
`DONE` register row must have a valid completion record. Historical actual
model records are not checked against today's editable model catalog.

The ledger does not track changes to past live dependencies, so the validator
checks dependency completion against the current register rather than
inferring historical dependency timing. Worker identities and results are
recorded attribution, not cryptographic proof.

## Evidence format

For `COMPLETE` events and `DONE` register rows, `Evidence` must contain a
non-empty reference. Multiple entries can be separated by semicolons.

| Example | Interpretation |
| --- | --- |
| `evidence/T-001.txt` | Workspace-relative local file |
| `tests.txt` | Local filename with an extension |
| `file:acceptance-report` | Explicit local file, including extensionless names |
| `[report](evidence/report.md)` | Markdown link to a local file |
| `https://example.com/report` | External reference; no network check |
| `Fixture passed` | Legacy free-text evidence note |
| `text:fixture.result` | Explicit note that might otherwise look like a file |

Local files must be regular files with non-zero byte size. Resolve paths from
the workspace root; absolute paths, drive-relative Windows paths, traversal
outside the root, and symlinks escaping the root are rejected. Both slash
styles are recognized. Empty entries and duplicate references within a field
are rejected, including paths that resolve to the same file. A single HTTP(S)
URL can include semicolons and is retained as one external reference.

Legacy evidence was free-form. To preserve compatibility, ordinary notes
remain accepted, and ambiguous extensionless names remain notes unless marked
`file:`. Compact filenames with extensions and references with path separators
are treated as local files; mark prose that looks like a path with `text:`.
The same evidence can appear in the completion row and register; each field is
checked independently. The validator does not demand identical fields or
derive required artifacts from human-readable acceptance/evidence prose.
It cannot verify whether notes are truthful, links are reachable, or local
reports demonstrate acceptance. Those judgments remain reviewer duties.
