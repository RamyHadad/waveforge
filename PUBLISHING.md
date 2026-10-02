# Publish WaveForge on GitHub

Target repository: **RamyHadad/waveforge**. These steps publish the repository and its README. A separate GitHub Pages website is optional and is not included here.

## 1. Create an empty repository

Sign in to GitHub as `RamyHadad`, then [create a new repository](https://github.com/new):

- Owner: `RamyHadad`
- Name: `waveforge`
- Description: `A Codex skill that turns project plans into workstreams, dependency waves, and model-routed tasks.`
- Visibility: choose public for a community-facing skill, or private for restricted access.
- Leave GitHub's README, .gitignore, and license initialization unchecked because the local files will be uploaded.

This project uses the MIT license in `LICENSE`; preserve it when publishing.

## 2. Upload from PowerShell

Run from this project's folder. If the folder already has a Git repository, skip `git init`; if `origin` already exists, inspect it with `git remote -v` before changing it.

```powershell
git init -b main
git add .
git diff --cached --stat
git commit -m "Prepare WaveForge skill for GitHub"
git remote add origin https://github.com/RamyHadad/waveforge.git
git push -u origin main
```

Git may ask you to sign in. If a commit reports a missing author identity, set your preferred name and GitHub email locally in this repository using `git config user.name` and `git config user.email`, then retry. Use your GitHub-provided private email if preferred.

GitHub's [guide for adding locally hosted code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github) covers authentication and first push.

## 3. Finish the repository page

The README appears automatically on the repository home page after upload. In the repository's About settings, add topics such as `codex`, `agent-skills`, `project-planning`, `task-decomposition`, and `python`.

Check the Actions tab for the `Validate WaveForge` workflow. Its test and example checks should pass before creating a release. The workflow is included locally; it runs on GitHub after a push or pull request.

## 4. Create a first release

Once validation passes, use GitHub's Releases interface to create a release such as `v0.1.0`. Describe the planning workflow, the supported Python versions, and the install and example commands. GitHub provides source archives for tagged releases.

Future updates can be published with `git add`, `git commit`, and `git push`. Avoid committing generated workspaces containing private project plans or live ownership records.
