# Contributing to Zolletta-metaskill

Thanks for your interest in contributing! This guide covers the practical steps to get a change merged.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Git

## Setup

```bash
git clone https://github.com/Zolletta/zolletta-metaskill.git
cd zolletta-metaskill
uv sync --all-extras
```

This installs all optional dependency groups: `dev` (pytest, ruff, mypy, ty, vulture) and `php` (tree-sitter, tree-sitter-php). Both are needed to run the full test suite and quality gate locally.

## Development workflow

1. **Branch from `main`**: `git checkout -b feat/your-feature` (or `fix/`, `docs/`, `chore/`).
2. **Make your changes**. Follow the existing code style — the project uses ruff, mypy, ty, and vulture (see `pyproject.toml` for configuration).
3. **Run the full quality gate locally** before pushing:

```bash
uv run pytest --cov=zolletta_metaskill --cov-report=term -q
uv run ruff check
uv run ty check .
uv run mypy .
uv run vulture .
```

These are the same checks CI runs (see `.github/workflows/ci.yml`). All four must pass.

4. **Commit and push** your branch, then open a pull request against `main`.

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/). Prefix every commit with one of:

| Type       | Use for                                             |
|------------|-----------------------------------------------------|
| `feat`     | New feature or capability                            |
| `fix`      | Bug fix                                             |
| `docs`     | Documentation changes                                |
| `refactor` | Code restructuring without behavior change          |
| `test`     | Adding or updating tests                            |
| `chore`    | Maintenance, deps, config                           |
| `style`    | Formatting, whitespace, naming                       |
| `ci`       | CI/CD changes                                        |
| `perf`     | Performance improvements                             |

Example: `feat(setup): detect PHP tools from composer.json`

Scope is optional but encouraged when the change targets a specific subcommand or module.

## Dogfooding

Zolletta-metaskill reviews its own code. Running the review skills on this repository before opening a PR is encouraged — it catches the same issues the maintainers would flag. Use:

```bash
/zolletta-metaskill review
```

Findings from a self-review don't need to be resolved if they're informational, but real findings (severity/impact) should be addressed or explained in the PR description.

## Tests

- Test files live in `tests/`, mirroring the `src/zolletta_metaskill/` structure.
- Run the full suite: `uv run pytest`
- Run a single module: `uv run pytest tests/setup/`
- Coverage target: every file ≥92%. The setup package aims for 100%.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). The version is a single number shared across all files — the meta-skill and every subskill always have the same version. Use the `.bump` script to update it atomically:

```bash
./.bump --to <version>
```

This updates `pyproject.toml`, `src/zolletta_metaskill/__init__.py`, all `SKILL.md` front-matter version fields, and `setup/assets/settings_template.json` in one pass. Review the diff, then commit.

### Version clashes

When multiple PRs are open at the same time, two contributors might bump to the same version. CI includes an automated **version clash check** that fails the PR if another open PR already targets the same version. If you get a clash error:

1. Check which version the other PR is targeting (the error message names the branch)
2. Re-bump to the next available version: `./.bump --to <next-version>`
3. Push — the check re-runs automatically

## Documentation

Full documentation lives in `docs/` and is published to <https://zolletta.github.io/zolletta-metaskill/> via MkDocs Material. The build runs automatically on push to `main` when `docs/` changes (see `.github/workflows/docs-pages.yml`).

To preview documentation locally:

```bash
uv pip install mkdocs-material
mkdocs serve
```

Then open <http://127.0.0.1:8000>.

## Project structure

```
src/zolletta_metaskill/   # Python package (scanning scripts, engines, setup)
skills/                   # SKILL.md files for each subcommand
docs/                     # Diátaxis-structured documentation
tests/                    # Test suite (mirrors src/ structure)
assets/                   # Logos and images
.bump                     # Version bump script
install.sh                # One-command installer
```

## License

By contributing, you agree that your contributions will be licensed under the MIT + Commons Clause license (see [LICENSE](LICENSE)).
