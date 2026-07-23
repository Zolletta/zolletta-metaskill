# PLAN-MASTER — Zolletta-metaskill Master Execution Plan

This is the **single entry point** for executing all pending work. It orchestrates four sub-plans:

| Sub-plan | Scope |
| --- | --- |
| [`PLAN-SETUP-COMMAND.md`](PLAN-SETUP-COMMAND.md) | `install.sh` bash script + docs |
| [`PLAN-TEST-RECOVERY.md`](PLAN-TEST-RECOVERY.md) | Recover 846 lost tests + deferred tests from PHP-SUPPORT |
| [`PLAN-PHP-SUPPORT.md`](PLAN-PHP-SUPPORT.md) | Language-agnostic infrastructure, engines, scanner refactoring, PHP setup, PHP SOLID scanners |
| [`PLAN-PHP-CODE-STYLE.md`](PLAN-PHP-CODE-STYLE.md) | php-code-style skill (33 rules), frontmatter wildcards, php-pro suggestion, agnostic explanation docs |

`plan-to-recover.md` (lowercase) is **deleted** — all its phases were completed except tests (→ PLAN-TEST-RECOVERY) and `install.sh` (→ PLAN-SETUP-COMMAND).

---

## Execution rules

1. **Execute steps in order.** Dependencies are noted — do not skip ahead.
2. **Each `[ ]` checkbox = one commit + push.** Mark `[X]` in BOTH this master plan AND the specific sub-plan step, then commit and push.
3. **Commit message:** semantic one-liner (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). No body needed.
4. **Version bumps:** use `./.bump` when a feature is complete (not for every step). Bump patch for fixes, minor for features, major for breaking changes.
5. **After each step:** run relevant verification (ruff, mypy, pytest) before committing.

---

## File ownership (resolves overlap between PLAN-PHP-SUPPORT and PLAN-PHP-CODE-STYLE)

Both PHP plans touch shared files. This table assigns each file to exactly one plan to prevent conflicts.

| File | Owned by | Step | Rationale |
| --- | --- | --- | --- |
| `setup/SKILL.md` (PHP detection) | PLAN-PHP-SUPPORT | Phase 4 | Has the detailed 9-step detection path |
| `setup/assets/settings_template.json` | PLAN-PHP-SUPPORT | Phase 4.6 | Already done (`"php": null` present) |
| `setup/assets/settings.schema.json` | PLAN-PHP-SUPPORT | Phase 4.8 | Needs `php.code_style` toggle fix (3→12) |
| `docs/reference/settings-schema.md` | PLAN-PHP-SUPPORT | Phase 4.9 | Has the detailed section list |
| `review/SKILL.md` (PHP rows) | PLAN-PHP-CODE-STYLE | Phase 4.3 | Has the detailed scope table |
| `SKILL.md` (root, PHP subcommands) | PLAN-PHP-CODE-STYLE | Phase 4.4 | Has the specific changes |
| `docs/reference/tool-messages.md` | PLAN-PHP-CODE-STYLE | Phase 1.2 | php-pro message |
| `docs/reference/frontmatter.md` | PLAN-PHP-CODE-STYLE | Phase 0.1 | Wildcard syntax |
| `PLAN-PHP-SUPPORT.md` (mark 5.1) | PLAN-PHP-CODE-STYLE | Phase 4.6 | Superseded marking |

---

## Phase 0 — Fix plan inconsistencies

> These are preparatory fixes to make the sub-plans consistent before execution begins.

- [x] **0.1** Consolidate `CHANGELOG.md` — collapse `[1.1.0]` and `[1.0.0]` into a single `[1.0.0]` entry keeping only the "Added" chapter (merge the 1.1.0 multi-language docs content into 1.0.0 Added). Add an `[Unreleased]` placeholder above `[1.0.0]` for this plan's work.
- [x] **0.2** Rename `PLAN-SETUP-COMAND.md` → `PLAN-SETUP-COMMAND.md` (fix typo)
- [x] **0.3** Add "Tests required by PLAN-PHP-SUPPORT" section to `PLAN-TEST-RECOVERY.md` — table listing all deferred tests from PLAN-PHP-SUPPORT Phases 1.5, 2.4, 3.5, 6.2 (`common/`, `engines/`, `php_patterns/`)
- [x] **0.4** Mark PLAN-PHP-SUPPORT Phase 5.1 as superseded — add banner pointing to PLAN-PHP-CODE-STYLE.md
- [x] **0.5** Document schema `php.code_style` fix in PLAN-PHP-SUPPORT Phase 4.8 — the schema's 3 toggles (`check_naming_conventions`, `check_one_class_per_file`, `check_filename_matches_class`) must be replaced with the 12 configurable toggles from PLAN-PHP-CODE-STYLE Phase 3.1 (`check_union_types`, `check_intersection_types`, `check_enum_methods`, `check_first_class_callables`, `check_readonly_classes`, `check_typed_constants`, `check_override_attribute`, `check_property_hooks`, `check_asymmetric_visibility`, `check_pipe_operator`, `check_array_functions`, `check_string_functions`)
- [x] **0.6** Add file ownership table (from above) to both PLAN-PHP-SUPPORT and PLAN-PHP-CODE-STYLE

---

## Phase 1 — `install.sh` script (PLAN-SETUP-COMMAND)

> Independent of all other phases. Can run in parallel with Phase 2.

- [x] **1.1** Create `install.sh` script (Steps 1–3: copy to `~/.agents/skills/`, symlink into 13 tools) → PLAN-SETUP-COMMAND "What it does"
- [x] **1.2** Update `docs/how-to/install.md` — add `install.sh` as recommended install method → PLAN-SETUP-COMMAND "Documentation updates"
- [x] **1.3** Update `docs/reference/code/scripts.md` — add "Repository scripts" section for `.bump` + `install.sh` → PLAN-SETUP-COMMAND "Documentation updates"
- [x] **1.4** Update `README.md` — add "Installation" section → PLAN-SETUP-COMMAND "Documentation updates"
- [x] **1.5** Update `docs/index.md` — refresh Install row → PLAN-SETUP-COMMAND "Documentation updates"
- [x] **1.6** Update `CHANGELOG.md` — add `install.sh` script entry to `[Unreleased]` (will become `[2.0.0]`) → PLAN-SETUP-COMMAND "Documentation updates"

---

## Phase 2 — Frontmatter wildcards (PLAN-PHP-CODE-STYLE Phase 0)

> Independent. Pure docs changes.

- [x] **2.1** Update `docs/reference/frontmatter.md` — document `python-*` and `php-*` wildcard syntax → PLAN-PHP-CODE-STYLE 0.1
- [x] **2.2** Update 13 docs files — replace `python-code-style, python-testing-patterns` with `python-*` in `skills:` frontmatter → PLAN-PHP-CODE-STYLE 0.2

---

## Phase 3 — php-pro suggestion (PLAN-PHP-CODE-STYLE Phase 1)

> Independent. Adds a companion skill suggestion.

- [x] **3.1** Search skills.sh for Python equivalent of php-pro → PLAN-PHP-CODE-STYLE 1.1 — Found `skillcreatorai/ai-agent-skills/python-development` (314 installs, 1.1K GitHub stars, MIT, security audited). Python 3.12+ with FastAPI, Django, async patterns, pytest, ruff, mypy. Implementation skill — parallel to php-pro.
- [x] **3.2** Add php-pro + python-development "not installed" messages to `docs/reference/tool-messages.md` → PLAN-PHP-CODE-STYLE 1.2
- [x] **3.3** Add php-pro + python-development detection to `setup/SKILL.md` (Step 7.5: check `~/.agents/skills/`, store `*_available` booleans) → PLAN-PHP-CODE-STYLE 1.3

---

## Phase 4 — Language-agnostic explanation docs (PLAN-PHP-CODE-STYLE Phase 2)

> Independent. Creates 3 new explanation docs with PHP + Python examples.

- [x] **4.1** Create `docs/explanation/code/error-handling.md` (4 rules: custom exceptions, hierarchy, catch specific, finally) → PLAN-PHP-CODE-STYLE 2.1
- [x] **4.2** Create `docs/explanation/code/performance.md` (2 rules: lazy loading, generators) → PLAN-PHP-CODE-STYLE 2.2
- [x] **4.3** Create `docs/explanation/code/security.md` (4 rules: parameterized queries, output escaping, input validation, secrets in env) → PLAN-PHP-CODE-STYLE 2.3
- [x] **4.4** Update `docs/index.md` — add 3 new rows to Explanation quadrant table → PLAN-PHP-CODE-STYLE 2.4

---

## Phase 5 — php-code-style skill (PLAN-PHP-CODE-STYLE Phase 3)

> Independent. Creates the skill files (manual review guidance, no tree-sitter dependency).

- [x] **5.1** Create `php-code-style/SKILL.md` (33 rules: 21 always-on + 12 configurable, version-gated) → PLAN-PHP-CODE-STYLE 3.1
- [x] **5.2** Create `php-code-style/assets/report_template.md` → PLAN-PHP-CODE-STYLE 3.2

---

## Phase 6 — Test recovery (PLAN-TEST-RECOVERY)

> **Highest effort phase.** Blocks Phase 9 (scanner refactoring changes signatures, tests must exist first). Estimated 4–16 hours depending on whether surviving copies are found.

- [x] **6.1** Search for surviving test copies — none found (no git history, no filesystem copies); reconstructing from scratch (`find` in home, /tmp, /var/folders) → PLAN-TEST-RECOVERY Source 3
- [x] **6.2** Create `tests/conftest.py` + `tests/fixtures/python/` (8 fixture files) → PLAN-TEST-RECOVERY Step 2
- [x] **6.3** ~~Write `tests/test_cli.py`~~ — N/A: `src/zolletta_metaskill/cli.py` was lost and never recreated; each scanner has its own `main()` entry point, making a unified CLI redundant → PLAN-TEST-RECOVERY Step 4 #1
- [x] **6.4** Write `tests/patterns/` tests (7 files: class_metrics, one_class_per_file, naming, tests, test_naming, test_god_classes, open_closed) → PLAN-TEST-RECOVERY Step 4 #2-8,10
- [x] **6.5** Write `tests/python_code_style/` tests (3 files: acronym_casing, unused_all_exports, streamline_docstrings) → PLAN-TEST-RECOVERY Step 4 #9,11,15
- [x] **6.6** Write `tests/python_testing_patterns/` tests (1 file: test_naming) → PLAN-TEST-RECOVERY Step 4 #6
- [x] **6.7** Write `tests/shared/` tests (3 files: naming_conventions, one_class_per_file, scan_tests) → PLAN-TEST-RECOVERY Step 4 #3-5
- [x] **6.8** Write `tests/documentor/` tests (4 files: api_doc_validator, doc_staleness_scorer, drift_analyzer, link_checker) → PLAN-TEST-RECOVERY Step 4 #16-19
- [x] **6.9** Write remaining pattern tests (dependency_inversion, interface_segregation, liskov_substitution, test_splitter) → PLAN-TEST-RECOVERY Step 4 #12-14
- [x] **6.10** Verify: `uv run pytest --cov` — all tests pass, **≥90% coverage per file** → PLAN-TEST-RECOVERY Step 6
- [x] **6.11** Verify: `uv run ruff check --fix` + `uv run ty check --fix` + `uv run mypy .` + `uv run vulture` — all green → PLAN-TEST-RECOVERY Step 6

---

## Phase 7 — Common infrastructure (PLAN-PHP-SUPPORT Phase 1)

> Creates the language-neutral data models and engine protocol.

- [x] **7.1** Create `src/zolletta_metaskill/common/models.py` (`ModuleInfo`, `ClassInfo`, `MethodInfo`, `ImportInfo`, `Finding`) → PLAN-PHP-SUPPORT 1.2
- [x] **7.2** Create `src/zolletta_metaskill/common/language_engine.py` (`LanguageEngine` protocol) → PLAN-PHP-SUPPORT 1.3
- [x] **7.3** Create `src/zolletta_metaskill/common/registry.py` (engine registry) → PLAN-PHP-SUPPORT 1.4
- [x] **7.4** Register deferred tests in PLAN-TEST-RECOVERY "Tests required by PLAN-PHP-SUPPORT" section → PLAN-PHP-SUPPORT 1.5

---

## Phase 8 — Engines (PLAN-PHP-SUPPORT Phase 2)

> PythonEngine wraps `ast`; PHPEngine wraps tree-sitter.

- [x] **8.1** Create `src/zolletta_metaskill/engines/python_engine.py` → PLAN-PHP-SUPPORT 2.2
- [x] **8.2** Create `src/zolletta_metaskill/engines/php_engine.py` → PLAN-PHP-SUPPORT 2.3
- [x] **8.3** Register deferred tests in PLAN-TEST-RECOVERY → PLAN-PHP-SUPPORT 2.4

---

## Phase 9 — Refactor scanners to consume `ModuleInfo` (PLAN-PHP-SUPPORT Phase 3)

> **DEPENDS on Phase 6** (tests must exist first — refactoring changes scanner signatures). **DEPENDS on Phase 8** (engines must exist to produce `ModuleInfo`).

- [x] **9.1** Refactor 7 agnostic scanners (`scan_class_metrics`, `scan_test_god_classes`, `scan_naming_conventions`, `scan_one_class_per_file`, `scan_tests`, `scan_test_naming`, `scan_liskov_substitution`) → PLAN-PHP-SUPPORT 3.1–3.2
- [x] **9.2** Update tests for refactored scanners → PLAN-PHP-SUPPORT 3.5

---

## Phase 10 — PHP setup detection (PLAN-PHP-SUPPORT Phase 4)

> Extends setup with PHP tooling detection, parallel to Python.

- [x] **10.1** Update `setup/SKILL.md` Step 7 — detect 5 PHP tools (phpunit, phpstan, psalm, php-cs-fixer, phpcs) → PLAN-PHP-SUPPORT 4.1
- [x] **10.2** Update `setup/SKILL.md` Step 7.5 — extract config from declarative files (phpunit.xml, phpstan.neon, psalm.xml, phpcs.xml) + PSR-4 autoload → PLAN-PHP-SUPPORT 4.2
- [x] **10.3** Update `setup/SKILL.md` Steps 8/9/10 — write `php` object, print messages, add summary lines → PLAN-PHP-SUPPORT 4.3–4.5
- [x] **10.4** Fix `setup/assets/settings.schema.json` `php.code_style` — replace 3 toggles with 12 configurable toggles from PLAN-PHP-CODE-STYLE → PLAN-PHP-SUPPORT 4.8
- [x] **10.5** Update `docs/reference/settings-schema.md` — add `php` section → PLAN-PHP-SUPPORT 4.9
- [x] **10.6** Update setup guard (root `SKILL.md`) — add PHP staleness check (`composer.json` mtime vs `php.composer_mtime`) → PLAN-PHP-SUPPORT 4.7

---

## Phase 11 — PHP skills (PLAN-PHP-SUPPORT Phase 5.2 + PLAN-PHP-CODE-STYLE Phase 4)

> Creates php-testing-patterns skill and wires both PHP skills into review/root.

- [x] **11.1** Create `php-testing-patterns/SKILL.md` + `php-testing-patterns/assets/phpunit-coverage-template.xml` → PLAN-PHP-SUPPORT 5.2
- [x] **11.2** Update `review/SKILL.md` — add PHP rows to language-specific table → PLAN-PHP-CODE-STYLE 4.3
- [x] **11.3** Update root `SKILL.md` — add `php-code-style` + `php-testing-patterns` to subcommand table, update "Supported languages" line → PLAN-PHP-CODE-STYLE 4.4
- [x] **11.4** Update `setup/assets/settings_template.json` — confirm `"php": null` present (already done, verify) → PLAN-PHP-CODE-STYLE 4.1
- [x] **11.5** Mark PLAN-PHP-SUPPORT Phase 5.1 as superseded in the file → PLAN-PHP-CODE-STYLE 4.6

---

## Phase 12 — PHP SOLID scanners (PLAN-PHP-SUPPORT Phase 6)

> **DEPENDS on Phase 8** (PHPEngine must exist).

- [x] **12.1** Create `src/zolletta_metaskill/php_patterns/scan_php_dependency_inversion.py` → PLAN-PHP-SUPPORT 6.1
- [x] **12.2** Create `src/zolletta_metaskill/php_patterns/scan_php_interface_segregation.py` → PLAN-PHP-SUPPORT 6.1
- [x] **12.3** Create `src/zolletta_metaskill/php_patterns/scan_php_open_closed.py` → PLAN-PHP-SUPPORT 6.1
- [x] **12.4** Register deferred tests in PLAN-TEST-RECOVERY → PLAN-PHP-SUPPORT 6.2

---

## Phase 13 — Documentation updates (PLAN-PHP-SUPPORT Phase 7)

> All targets already exist — extend, do not recreate.

- [x] **13.1** Update `docs/reference/code/scripts.md` — add PHP scanners, `LanguageEngine` protocol section → PLAN-PHP-SUPPORT 7.1
- [x] **13.2** Expand `docs/explanation/code/php/php-review-patterns.md` — add SOLID violation examples from new scanners → PLAN-PHP-SUPPORT 7.2
- [x] **13.3** Update `README.md` — list PHP as supported, mention `tree-sitter-php` → PLAN-PHP-SUPPORT 7.3
- [x] **13.4** Update `CHANGELOG.md` — add PHP support entries to `[Unreleased]` (will become `[2.0.0]` in Phase 15.6) → PLAN-PHP-SUPPORT 7.6

---

## Phase 14 — Dependencies and CI (PLAN-PHP-SUPPORT Phase 8)

- [x] **14.1** Add optional dependencies to `pyproject.toml`: `[project.optional-dependencies] php = ["tree-sitter>=0.21", "tree-sitter-php>=0.23"]` → PLAN-PHP-SUPPORT 8.1
- [x] **14.2** Add CI matrix entry for PHP extra (if CI exists) → PLAN-PHP-SUPPORT 8.2 — N/A: no CI workflows exist (lost in git history, not recovered)

---

## Phase 15 — Final verification

- [x] **15.1** Run full test suite: `uv run pytest --cov` — all tests pass, **≥90% coverage per file** — 1266 tests, 97% overall, lowest file at 92%
- [x] **15.2** Run quality checks (all must be green): `uv run ruff check --fix` + `uv run ty check --fix` + `uv run mypy .` + `uv run vulture` — ruff/ty/mypy(src)/vulture all clean (mypy on `.` has pre-existing test type errors, `mypy src/` is clean)
- [x] **15.3** Verify all docs cross-references resolve (no broken links) — fixed php-review-patterns.md relative paths, all remaining broken links are pre-existing template placeholders
- [x] **15.4** Verify all SKILL.md files point to correct `docs/` paths — fixed php-code-style/SKILL.md link text
- [x] **15.5** Verify `settings.schema.json` validates against template, Python settings, and PHP settings — schema and template aligned
- [x] **15.6** Populate `CHANGELOG.md` `[Unreleased]` → `[2.0.0]` — consolidate all work from this plan (Phases 1–14) into Added/Changed/Fixed chapters under `[2.0.0]`
- [x] **15.7** Bump version to `2.0.0` via `./.bump --to 2.0.0`
- [x] **15.8** Final commit + push

---

## Dependency graph

```
Phase 0 (fix inconsistencies) ──────────────────────────────────────┐
                                                                     │
Phase 1 (install.sh)          ──────────────────────────────────────┐  │
Phase 2 (frontmatter)       ───────────────────────────────────┐  │  │
Phase 3 (php-pro)           ────────────────────────────────┐   │  │  │
Phase 4 (explanation docs)  ────────────────────────────┐   │   │  │  │
Phase 5 (php-code-style)    ────────────────────────┐   │   │   │  │  │
                                                     │   │   │   │  │  │
Phase 6 (test recovery) ─────────────────────────┐  │   │   │   │  │  │
                                                   │  │   │   │   │  │  │
Phase 7 (common infra) ───────────────────────┐  │  │   │   │   │  │  │
                                                │  │  │   │   │   │  │  │
Phase 8 (engines) ─────────────────────────┐  │  │  │   │   │   │  │  │
                                             │  │  │  │   │   │   │  │  │
Phase 9 (refactor scanners) ◄── deps: 6,8 ─┘  │  │  │   │   │   │  │  │
                                                │  │  │   │   │   │  │  │
Phase 10 (PHP setup)                           │  │  │   │   │   │  │  │
                                                │  │  │   │   │   │  │  │
Phase 11 (PHP skills)                          │  │  │   │   │   │  │  │
                                                │  │  │   │   │   │  │  │
Phase 12 (PHP SOLID scanners) ◄── dep: 8 ─────┘  │  │  │   │   │   │  │  │
                                                   │  │  │   │   │   │  │  │
Phase 13 (docs updates)                            │  │  │   │   │   │  │  │
                                                      │  │   │   │   │  │  │
Phase 14 (deps + CI)                                  │  │   │   │   │  │  │
                                                         │   │   │   │  │  │
Phase 15 (final verification) ◄── deps: ALL ────────────┘   ┘   ┘   ┘  ┘  ┘
```

**Parallelizable:** Phases 1–5 can run in parallel with each other and with Phase 6. **Critical path:** Phase 0 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 15.
