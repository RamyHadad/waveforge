# Configuring the split

WaveForge accepts an optional UTF-8 YAML file through `--split-config`. Read
it **before** authoring the decomposition manifest. With no file, the default
is `mode: model_decides`: the model chooses coherent workstreams, waves, and
task sizes from the source plan. It does not follow a fixed chunk count.

Example user configuration:

```yaml
version: 1
mode: configured
required_workstreams: [runtime, application, validation]
min_workstreams: 3
max_workstreams: 5
max_waves_per_workstream: 4
max_tasks_per_wave: 6
rules:
  - Keep application UI and model-provider integration in separate workstreams.
  - Put release validation after the implementation waves it verifies.
```

All limits are optional positive integers. `required_workstreams` is a list of
plan IDs that must appear. `rules` are human-readable constraints; the model
must check them against the final plan. The builder and validator check the
numeric limits and required IDs, but cannot determine whether a semantic rule
was satisfied. Do not turn a broad goal into arbitrary equal-sized chunks just
to meet a number.

The generated workspace always contains `configuration/splitting.yaml`, even
when no file was supplied. The default records `mode: model_decides` with empty
constraints. Users can edit this file later, but edits to splitting rules do
not rewrite existing task plans. Re-run the skill into a **new** workspace and
review differences before migrating ownership or evidence records.
