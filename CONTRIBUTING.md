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
uv sync --extra dev --extra php
```

This installs all development and runtime dependencies (including the optional PHP extras).

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

## Tests

- Test files live in `tests/`, mirroring the `src/zolletta_metaskill/` structure.
- Run the full suite: `uv run pytest`
- Run a single module: `uv run pytest tests/setup/`
- Coverage target: every file ≥92%. The setup package aims for 100%.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). Use the `.bump` script to bump the version across all files:

```bash
./.bump --to <version>
```

This updates `pyproject.toml`, `src/zolletta_metaskill/__init__.py`, all `SKILL.md` front-matter version fields, and `setup/assets/settings_template.json`. Review the diff, then commit.

## Documentation

Full documentation lives in `docs/` and is published to <https://zolletta.github.io/zolletta-metaskill/> via MkDocs Material. The build runs automatically on push to `main` when `docs/` changes (see `.github/workflows/docs-pages.yml`).

To preview documentation locally:

```bash
pip install mkdocs-material
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
