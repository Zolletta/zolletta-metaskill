# AGENTS.md

Conventions for the zolletta-metaskill repository. Follow them in all code under `src/` unless a file already deviates for a documented reason.

## Two rules about rules

**1. If a tool can enforce it, the tool is the rule.** Every rule below names the tool that checks it. Run the tool; do not reason about what it would say, and never satisfy a rule by hand when a scanner, linter or CI step already exists for it. A rule enforced by `ruff` is not yours to interpret — if the code disagrees with the gate, the gate wins and the fix is in the code. If the gate itself is wrong, that is a change to the gate, in its own commit, with the reason written down.

**2. A rule with no enforcement is not a rule.** Every rule below carries a gate: a sensor, a linter rule, a type checker, or a CI step. A new rule lands **together with** the gate that checks it, in the same change — a rule written down and never checked is a comment, and it decays the day nobody is watching. Every rule below is marked with the tool that enforces it; where a tool is named, use it. If you find a rule here with no tool, that is a defect in this file: fix the rule or add the gate.

Rules marked **unenforced** are known exceptions. They are listed because they are real, not because they are optional — each one is a standing argument for the gate that should exist.

Rules that survived the 2026-10-11 pass but that I do not believe are earning their place are **not** deleted here: they are parked in [Rules to be deleted](#rules-to-be-deleted) for a human to decide. Nothing in that list is gone until someone says so.

## General

- Every file should end with an empty row with a newline, following POSIX definition of file. — *unenforced* (a hook, not a gate: it can be bypassed with `--no-verify`)

## Markdown

- No artificial line break — *unenforced, and it must stay that way*: the rule and MD013 cannot both hold, so the config disables MD013 rather than rewrapping prose.
- Should pass markdownlint — **unenforced**: no `.markdownlint.yaml` exists and no workflow runs it. This is the rule the markdownlint gate exists to enforce.
- Mermeid graph should have no-fill in the boxes and no background — *unenforced*
- **Relative links only.** Never hardcode `https://github.com/Zolletta/zolletta-metaskill/...` URLs in `docs/` or `skills/` — always use repo-root-relative links (`../../README.md`, `../../skills/zolletta-metaskill-help/SUBSKILL.md`). They resolve correctly on GitHub and in local clones. mkdocs cannot see outside `docs/`, so such links are downgraded to `info` via `validation.links.not_found` in `mkdocs.yml`; the real link audit is `link_checker.py`, which resolves them against the repo root.
- **ADR corpus layout.** Architecture ADRs live in `docs/explanation/adr/architecture/` — the only directory the distiller reads (`documentation.adrs` in `.zolletta-metaskill/settings.json`). Activity records (evaluations, feature-adds) never enter the corpus; pre-reform records stay decodable through git history. Accepted ADRs are immutable: replace them only by supersession (see `docs/explanation/adr/architecture/0000-adrs-record-architecture-not-activity.md`).

## Commits

Use english and conventional commits

## Code

### Structure

- **One class per file.** Every file in `src/` defines exactly one class. The file is named after the class in snake_case (`one_class_per_file_scanner.py` → `OneClassPerFileScanner`). If a helper type is needed, give it its own file under `structs/` or a matching package — never a second class in the same file. — enforced by `one_class_per_file_scanner.py` (`check_one_class_per_file`)
- **No module-level functions.** All functions live inside classes as `@staticmethod`s (or instance methods). Module-level `def` is not allowed in `src/` — helpers are private static methods on the owning class (e.g. `PHPEngine._have_tree_sitter_php`, not a bare `_have_tree_sitter_php()`). Constants are class attributes for the same reason. — **unenforced**: nothing detects a module-level `def` in `src/`. This rule has no gate.
- **No `if TYPE_CHECKING:` blocks.** Import everything needed for type annotations directly at the top of the module. `from __future__ import annotations` is already used everywhere so annotations are lazily evaluated — there is no need for `TYPE_CHECKING` guards. When a dependency must stay runtime-optional, import it lazily inside the method that uses it (see `PHPEngine._default_parser_factory`), not behind `TYPE_CHECKING`. — **unenforced**: `src/` has zero occurrences today, so the rule holds by discipline rather than by gate.

### Tests

- **Mirrored structure.** Every `src/zolletta_metaskill/<path>/<name>.py` has exactly one corresponding `tests/<path>/test_<name>.py` — the test file path mirrors the source file path exactly. — enforced by `test_structure_scanner.py` (`check_test_structure`)
- **One test class per source class.** A test file contains exactly one `Test*` class named after the source class (`ProjectConfig` → `TestProjectConfig`), holding all its tests grouped under `# --- section ---` comments. Exceptionally a source class may gain additional test classes, but each lives in its own file (`test_<name>_<aspect>.py`) — never two classes in a single test file. Enforced on test roots by `one_class_per_file_scanner.py` (toggle: `check_one_class_per_test_file`).
- **Non-test files under `tests/` live in `tests/fixtures/<subpath>/`, mirroring the source subpath.** The 1:1 mirrored-structure rule above applies to `test_<name>.py` files only. Expected-output fixtures (scanner reports, markdown documents) are not test files and must not sit beside them — `src/zolletta_metaskill/documentor/report_aggregator.py` → `tests/fixtures/documentor/report_aggregator.md`. Committed rather than inline so that a change to user-facing output appears in review as a readable diff of the output itself. The scanners ignore these directories: both `test_structure_scanner.py` and `one_class_per_file_scanner.py` enumerate via `ProjectConfig.iter_files(root, {".py"})`. — *unenforced*: the scanners ignore `tests/fixtures/` but nothing checks that a fixture lives there.

### Scripts

- **Standard CLI.** Review scripts accept `[--json]` only; scan roots, toggles, and thresholds come from `.zolletta-metaskill/settings.json` via `ProjectConfig` — never positional directories or `--src`/`--tests` flags. — enforced by the absence of alternatives plus `vulture`; the `--json`-only surface is what `ProjectConfig` assumes, so a script that takes a positional root has nowhere to read its settings from.

## Rules to be deleted

Nothing here has been deleted. These rules survived the 2026-10-11 enforcement pass, and each one is a candidate for removal because it is either unenforceable or in direct conflict with another rule. **Review them and decide: delete it, keep it and accept that it stays unenforced, or replace it with wording a tool can check.** They stay in force until that decision is made — parking a rule here is not permission to ignore it.

| Rule                                                             | Why it is a candidate                                                                                                                                                                                                             | Recommendation                                                                                                                                                                                                               |
|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| No artificial line break                                         | In direct conflict with MD013, which wants 2 020 of them rewrapped. The markdownlint gate has to keep MD013 **disabled** because of this rule — a rule that forces a lint rule to be switched off is costing more than it returns | **Keep as prose, stop treating it as enforceable.** The gate disables MD013 and the config comment says why; that comment is the enforcement. Otherwise the rule and the rule set contradict each other inside a config file |
| Mermeid graph should have no-fill in the boxes and no background | Not machine-checkable, and it governs a handful of diagrams                                                                                                                                                                       | **Delete.** Presentation belongs with the diagram it presents                                                                                                                                                                |
| Use english and conventional commits                             | Conventional commits **are** enforced — by python-semantic-release, which produces no changelog entry for a commit that does not parse. English is not machine-checkable                                                          | **Narrow rather than delete.** Keep "conventional commits" (enforced); drop "english" as a rule, or keep it as prose in `CONTRIBUTING.md` where nobody expects a gate                                                        |

Deleting a rule is not a quiet edit: say in the commit message which gate stops existing because of it, and whether anything that depended on it needs replacing.

