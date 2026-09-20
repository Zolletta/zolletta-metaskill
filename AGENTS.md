# AGENTS.md

Conventions for the zolletta-metaskill repository. Follow them in all code under `src/` unless a file already deviates for a documented reason.

## General

- Every file should end with an empty row with a newline, following POSIX definition of file.

## Markdown

- No artificial line break
- Should pass markdownlint
- Mermeid graph should have no-fill in the boxes and no background
- **Relative links only.** Never hardcode `https://github.com/Zolletta/zolletta-metaskill/...` URLs in `docs/` or `skills/` — always use repo-root-relative links (`../../README.md`, `../../skills/help/SKILL.md`). They resolve correctly on GitHub and in local clones. mkdocs cannot see outside `docs/`, so such links are downgraded to `info` via `validation.links.not_found` in `mkdocs.yml`; the real link audit is `link_checker.py`, which resolves them against the repo root.


## Commits 

Use english and conventional commits

## Code

### Structure

- **One class per file.** Every file in `src/` defines exactly one class. The file is named after the class in snake_case (`one_class_per_file_scanner.py` → `OneClassPerFileScanner`). If a helper type is needed, give it its own file under `structs/` or a matching package — never a second class in the same file.
- **No module-level functions.** All functions live inside classes as `@staticmethod`s (or instance methods). Module-level `def` is not allowed in `src/` — helpers are private static methods on the owning class (e.g. `PHPEngine._have_tree_sitter_php`, not a bare `_have_tree_sitter_php()`). Constants are class attributes for the same reason.
- **No `if TYPE_CHECKING:` blocks.** Import everything needed for type annotations directly at the top of the module. `from __future__ import annotations` is already used everywhere so annotations are lazily evaluated — there is no need for `TYPE_CHECKING` guards. When a dependency must stay runtime-optional, import it lazily inside the method that uses it (see `PHPEngine._default_parser_factory`), not behind `TYPE_CHECKING`.

### Tests

- **Mirrored structure.** Every `src/zolletta_metaskill/<path>/<name>.py` has exactly one corresponding `tests/<path>/test_<name>.py` — the test file path mirrors the source file path exactly.
- **Test classes group coverage.** A test file contains multiple `Test*` classes, one per method or behavior area of the class under test (e.g. `TestMain`, `TestResolveExtensions`).

### Scripts

- **Standard CLI.** Review scripts accept `[--json]` only; scan roots, toggles, and thresholds come from `.zolletta-metaskill/settings.json` via `ProjectConfig` — never positional directories or `--src`/`--tests` flags.
