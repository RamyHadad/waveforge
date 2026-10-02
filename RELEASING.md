# Releasing WaveForge

WaveForge is published at `RamyHadad/waveforge`. Releases use annotated tags
such as `v0.1.0` and GitHub Releases. There is no Python package version to
synchronize: release versions and YAML schema `version: 1` are independent.

## Pre-release checks

Review the changes, confirm the workspace contracts and docs agree, and update
`CHANGELOG.md` with the version, release date, actual capabilities, fixes, and
compatibility notes. Preserve source hashes, actual claims, and evidence when
reviewing existing workspaces. Avoid committing private generated plans.

Run these checks from the repository root, using a fresh output directory:

```text
python -m pip install -r requirements.txt
python -m unittest discover -s scripts -p "test_*.py" -v
python scripts/build_plan_workspace.py --source examples/source-plan.md --manifest examples/decomposition.yaml --split-config examples/splitting.yaml --out .demo-workspace-release
python scripts/validate_plan_workspace.py .demo-workspace-release
git diff --check
git status --short
```

The complete suite builds its fixtures and checks the official example as
well. Check the Actions results for both Python 3.10 and 3.14. Locally run the
matrix versions you have installed and disclose versions you could not run.
Confirm there are no stale documentation links or misleading ownership terms.

If compatibility changes, explain which executed states or evidence formats
need correction. Keep established schema fields unless a versioned schema
change is necessary. Generation includes timestamp metadata; validation itself
is deterministic and does not contact models or external evidence services.

## Tag and publish

Commit the reviewed changes, push the branch, and tag that release commit.
Check `git tag --list` and remote tags first; never move an existing release tag.

```text
git push origin main
git tag -a v0.1.0 -m "WaveForge v0.1.0"
git push origin v0.1.0
```

After GitHub CI passes, create the release. With installed, authenticated GitHub
CLI, the initial release can use the changelog as its notes:

```text
gh release create v0.1.0 --repo RamyHadad/waveforge --verify-tag --title "WaveForge v0.1.0" --notes-file CHANGELOG.md
```

For future releases, extract the relevant changelog section into a temporary
Markdown file and use it with `--notes-file`. State supported Python versions,
workspace compatibility, validation changes, and installation/example usage.
GitHub supplies source archives; do not claim a package distribution exists.

If CLI authentication is unavailable, use GitHub's Releases interface after
the tag is pushed, select that tag, and paste the release notes. Report tag
publication and GitHub Release creation separately.

## Repository metadata

When authenticated CLI/API access is available, keep the description and
topics focused on planning and development coordination:

```text
gh repo edit RamyHadad/waveforge --description "Dependency-aware project decomposition and validated planning workspaces for multi-model AI development."
gh api --method PUT repos/RamyHadad/waveforge/topics -f "names[]=codex" -f "names[]=agent-skills" -f "names[]=ai-agents" -f "names[]=project-planning" -f "names[]=task-decomposition" -f "names[]=multi-agent" -f "names[]=python" -f "names[]=developer-tools"
```

These describe coordinated planning; WaveForge does not provide an agent
runtime. If access is unavailable, leave metadata changes for the maintainer
and report that they were not performed.
