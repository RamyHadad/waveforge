# Contributing to WaveForge

Describe the problem and the behavior your change improves in an issue or pull request. Include a small reproducible source plan or manifest for generation and validation bugs.

Keep the skill domain-neutral. Project-specific rules belong in input plans or splitting configuration. Preserve the boundary between planning and execution, the original source, and actual ownership evidence.

For script changes, install `requirements.txt` and run:

```bash
python -m unittest discover -s scripts -p "test_*.py" -v
python scripts/build_plan_workspace.py --source examples/source-plan.md --manifest examples/decomposition.yaml --split-config examples/splitting.yaml --out .demo-workspace-contribution
python scripts/validate_plan_workspace.py .demo-workspace-contribution
```

Use a fresh output path each time. Add focused behavior tests when a script change warrants them. For documentation changes, check commands, relative links, and consistency with the existing skill and scripts.

This repository has not yet selected a license; resolve licensing with the maintainer before contributing code intended for redistribution.
