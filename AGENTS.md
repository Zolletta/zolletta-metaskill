# AGENTS.md

Conventions for the zolletta-metaskill repository. Follow them in all files in the repo unless a file already deviates for a documented reason. Rules marked *unenforced* have no tool checking them — they are real, not optional.

## Before any commit

Every command below also runs in CI (`.github/workflows/tests.yml`, jobs `pytest + coverage`, `ruff + ty + mypy + vulture`, `markdownlint`). Run them locally first — a red CI run is a wasted round trip.

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run ty check .
uv run mypy .
uv run vulture . --min-confidence 80
uv run pytest -q
npx --yes markdownlint-cli2@0.23.3
```

`ruff format --check` is the only one CI does not run. When an ADR changes, refresh the distiller cache and confirm it goes quiet:

```bash
PYTHONPATH=src uv run python src/zolletta_metaskill/adr/adr_cli.py
```

## General

| Rule                                                    | Enforced by                                                                                                                                                                                                                    |
|---------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Every file ends with an empty row and a newline (POSIX) | *unenforced* for `.json`/`.yml`/`.toml`/`.txt` — no pre-commit hook exists. `.py` is covered by `ruff format --check`, which CI does not run; `.md` by `MD047` in `.markdownlint.yaml`, which the CI markdownlint job does run |

## Markdown

| Rule                                                                                                                                                                                                                                                                                                 | Enforced by                                                                                                                                                                                                          |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| No artificial line break — prose paragraphs stay on one line (spec: `docs/explanation/documentation/standards.md`)                                                                                                                                                                                   | `.markdownlint.yaml` — disables MD013 so no lint rule demands the wrapping this convention forbids                                                                                                                   |
| Should pass markdownlint                                                                                                                                                                                                                                                                             | `.markdownlint.yaml` holds the rule set and `.markdownlint-cli2.jsonc` the globs; the CI `markdownlint` job runs `npx --yes markdownlint-cli2@0.23.3` with `continue-on-error: true`, so it reports without blocking |
| Mermaid graphs have no fill and no background — default theme only (spec: `docs/explanation/documentation/standards.md#mermaid-diagrams`)                                                                                                                                                            | *unenforced* — no checker; zero diagrams in the repo today                                                                                                                                                           |
| Relative links only — never hardcode `https://github.com/Zolletta/zolletta-metaskill/...` URLs in `docs/` or `skills/`; repo-root-relative links resolve on GitHub and locally (mkdocs cannot see outside `docs/`, so they're downgraded to `info` via `validation.links.not_found` in `mkdocs.yml`) | `link_checker.py` — resolves links against the repo root                                                                                                                                                             |
| ADR corpus layout — architecture ADRs live in `docs/explanation/adr/architecture/`; activity records never enter the corpus; accepted ADRs are immutable — replace only by supersession (see `docs/explanation/adr/architecture/0000-adrs-record-architecture-not-activity.md`)                      | `adr-distiller` reads only `documentation.adrs` in `.zolletta-metaskill/settings.json`; pre-reform records decode via git history                                                                                    |

## Commits

| Rule                                                                                                    | Enforced by                                                                 |
|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [Conventional commits](https://www.conventionalcommits.org/) — human-facing detail in `CONTRIBUTING.md` | python-semantic-release — an unparseable commit produces no changelog entry |

## Code

### Structure

| Rule                                                                                                                                                                                                                                   | Enforced by                                                   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| One class per file — every file in `src/` defines exactly one class, named after it in snake_case (`one_class_per_file_scanner.py` → `OneClassPerFileScanner`); helper types get their own file under `structs/` or a matching package | `one_class_per_file_scanner.py` (`check_one_class_per_file`)  |
| No module-level functions — all functions are `@staticmethod`s or instance methods on the owning class (e.g. `PHPEngine._have_tree_sitter_php`); constants are class attributes                                                        | *unenforced* — nothing detects a module-level `def` in `src/` |
| No `if TYPE_CHECKING:` blocks — import directly; `from __future__ import annotations` is already used everywhere; runtime-optional deps import lazily inside the method that uses them (e.g. `PHPEngine._default_parser_factory`)      | *unenforced* — `src/` has zero occurrences today              |

### Tests

| Rule                                                                                                                                                                                                                                             | Enforced by                                                       |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| Mirrored structure — every `src/zolletta_metaskill/<path>/<name>.py` has exactly one `tests/<path>/test_<name>.py`, path-for-path                                                                                                                | `test_structure_scanner.py` (`check_test_structure`)              |
| One `Test*` class per test file named after the source class (`ProjectConfig` → `TestProjectConfig`), tests grouped under `# --- section ---` comments; extra test classes live in their own `test_<name>_<aspect>.py`                           | `one_class_per_file_scanner.py` (`check_one_class_per_test_file`) |
| Non-test files under `tests/` live in `tests/fixtures/<subpath>/` mirroring the source subpath — committed so output changes appear as readable diffs (scanners ignore these dirs: both enumerate via `ProjectConfig.iter_files(root, {".py"})`) | *unenforced* — nothing checks that a fixture lives there          |

### Scripts

| Rule                                                                                                                                                                                                                 | Enforced by                                                                                           |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| Standard CLI — review scripts accept `[--json]` only; scan roots, toggles, and thresholds come from `.zolletta-metaskill/settings.json` via `ProjectConfig`, never positional directories or `--src`/`--tests` flags | `ProjectConfig` — a script taking a positional root has nowhere to read settings from; plus `vulture` |
