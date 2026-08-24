---
audience: human, ai
status: stable
skills: []
---

# CI/CD Workflows

GitHub Actions workflows that automate testing, releasing, and documentation deployment for Zolletta-metaskill.

## Workflow overview

| Workflow         | File                                     | Trigger                            | Scope                                                                                |
|------------------|------------------------------------------|------------------------------------|--------------------------------------------------------------------------------------|
| Tests            | `.github/workflows/tests.yml`            | Push (all branches), pull request  | pytest + coverage, ruff, ty, mypy, vulture                                           |
| Semantic Release | `.github/workflows/semantic-release.yml` | Push to `main`                     | Calls Tests, then creates a version tag + GitHub Release via python-semantic-release |
| Docs (Pages)     | `.github/workflows/docs-pages.yml`       | Push to `main` (docs changes only) | Builds MkDocs Material site and deploys to GitHub Pages                              |

## Tests

Runs on every push and pull request. Executes the full test suite with coverage reporting, followed by static analysis (ruff, ty, mypy, vulture). Also callable as a reusable workflow by Semantic Release.

- **Triggers**: `push` (all branches), `pull_request`, `workflow_call`
- **Jobs**: `pytest` → `quality` (quality depends on pytest passing)
- **Coverage**: Uploaded to Codecov

## Semantic Release

Runs only on pushes to `main`. It calls the Tests workflow as a dependency, then — if all checks pass — determines the next version from commit history, stamps it into `pyproject.toml`, creates a git tag, and publishes a GitHub Release.

- **Trigger**: `push` to `main`
- **Depends on**: Tests workflow (via `workflow_call`)
- **Versioning**: [python-semantic-release](https://github.com/python-semantic-release/python-semantic-release) with conventional commits
- **Release types**: `feat` → minor, `fix`/`perf`/`refactor` → patch, breaking changes → major
- **Ignored types**: `chore`, `docs`, `deps`, `ci` (no version bump)
- **Authentication**: Uses the built-in `GITHUB_TOKEN`

## Docs (Pages)

Runs only when documentation files change on `main`. Builds the MkDocs Material site and deploys it to GitHub Pages at [zolletta.github.io/zolletta-metaskill](https://zolletta.github.io/zolletta-metaskill/).

- **Trigger**: `push` to `main` with changes in `docs/**`, `mkdocs.yml`, or the workflow file itself
- **Concurrency**: Only one deployment at a time; in-progress runs are cancelled
- **Path filters**: Does not run on code-only changes

## Shared setup

All workflows use a composite action (`.github/actions/setup-env/action.yml`) that installs `uv`, sets up Python, caches the `.venv` directory, and runs `uv sync`. This avoids duplicating setup steps across jobs and speeds up runs via cache reuse.
