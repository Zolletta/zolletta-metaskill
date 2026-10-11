# AGENTS.md

Conventions for the zolletta-metaskill repository. Follow them in all code under `src/` unless a file already deviates for a documented reason.

## General

- Every file should end with an empty row with a newline, following POSIX definition of file.

## Markdown

- No artificial line break
- Should pass markdownlint
- Mermeid graph should have no-fill in the boxes and no background
- **Relative links only.** Never hardcode `https://github.com/Zolletta/zolletta-metaskill/...` URLs in `docs/` or `skills/` — always use repo-root-relative links (`../../README.md`, `../../skills/zolletta-metaskill-help/SUBSKILL.md`). They resolve correctly on GitHub and in local clones. mkdocs cannot see outside `docs/`, so such links are downgraded to `info` via `validation.links.not_found` in `mkdocs.yml`; the real link audit is `link_checker.py`, which resolves them against the repo root.
- **ADR corpus layout.** Architecture ADRs live in `docs/explanation/adr/architecture/` — the only directory the distiller reads (`documentation.adrs` in `.zolletta-metaskill/settings.json`). Activity records (evaluations, feature-adds) never enter the corpus; pre-reform records stay decodable through git history. Accepted ADRs are immutable: replace them only by supersession (see `docs/explanation/adr/architecture/0000-adrs-record-architecture-not-activity.md`).


## Commits 

Use english and conventional commits

## Code

### Structure

- **One class per file.** Every file in `src/` defines exactly one class. The file is named after the class in snake_case (`one_class_per_file_scanner.py` → `OneClassPerFileScanner`). If a helper type is needed, give it its own file under `structs/` or a matching package — never a second class in the same file.
- **No module-level functions.** All functions live inside classes as `@staticmethod`s (or instance methods). Module-level `def` is not allowed in `src/` — helpers are private static methods on the owning class (e.g. `PHPEngine._have_tree_sitter_php`, not a bare `_have_tree_sitter_php()`). Constants are class attributes for the same reason.
- **No `if TYPE_CHECKING:` blocks.** Import everything needed for type annotations directly at the top of the module. `from __future__ import annotations` is already used everywhere so annotations are lazily evaluated — there is no need for `TYPE_CHECKING` guards. When a dependency must stay runtime-optional, import it lazily inside the method that uses it (see `PHPEngine._default_parser_factory`), not behind `TYPE_CHECKING`.

### Tests

- **Mirrored structure.** Every `src/zolletta_metaskill/<path>/<name>.py` has exactly one corresponding `tests/<path>/test_<name>.py` — the test file path mirrors the source file path exactly.
- **One test class per source class.** A test file contains exactly one `Test*` class named after the source class (`ProjectConfig` → `TestProjectConfig`), holding all its tests grouped under `# --- section ---` comments. Exceptionally a source class may gain additional test classes, but each lives in its own file (`test_<name>_<aspect>.py`) — never two classes in a single test file. Enforced on test roots by `one_class_per_file_scanner.py` (toggle: `check_one_class_per_test_file`).
- **Non-test files under `tests/` live in `tests/fixtures/<subpath>/`, mirroring the source subpath.** The 1:1 mirrored-structure rule above applies to `test_<name>.py` files only. Expected-output fixtures (scanner reports, markdown documents) are not test files and must not sit beside them — `src/zolletta_metaskill/documentor/report_aggregator.py` → `tests/fixtures/documentor/report_aggregator.md`. Committed rather than inline so that a change to user-facing output appears in review as a readable diff of the output itself. The scanners ignore these directories: both `test_structure_scanner.py` and `one_class_per_file_scanner.py` enumerate via `ProjectConfig.iter_files(root, {".py"})`.

### Scripts

- **Standard CLI.** Review scripts accept `[--json]` only; scan roots, toggles, and thresholds come from `.zolletta-metaskill/settings.json` via `ProjectConfig` — never positional directories or `--src`/`--tests` flags.
