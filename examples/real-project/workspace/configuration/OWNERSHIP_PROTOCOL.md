# Worker ownership and sign-off

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
