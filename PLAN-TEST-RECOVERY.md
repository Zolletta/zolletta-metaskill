# Plan: Recover Lost Python Tests

## Situation

The repo was re-cloned from GitHub (commit `a8edbe9`, version 1.1.0). All work from two previous sessions was lost — including 846 tests at 100% coverage across 20+ test files. The tests were never pushed to remote. This plan identifies every possible recovery source and, where recovery is impossible, provides a reconstruction strategy.

## What was lost

### Test files (20 files, 846 tests total)

The test tree mirrors the current `src/zolletta_metaskill/` per-skill subfolder layout. The old flat `scanners/` directory no longer exists in source — tests must be placed in the matching subfolder.

```
tests/
├── conftest.py                                    # shared fixtures (python_fixtures, etc.)
├── test_cli.py                                    # CLI entry point tests
├── documentor/
│   ├── __init__.py
│   ├── test_api_doc_validator.py                  # ~975 lines, multiple test classes
│   ├── test_doc_staleness_scorer.py               # staleness scoring tests
│   ├── test_drift_analyzer.py                     # ~1250 lines, git-based drift detection
│   └── test_link_checker.py                       # ~1090 lines, link checking
├── patterns/
│   ├── __init__.py
│   ├── test_scan_class_metrics.py
│   ├── test_scan_dependency_inversion.py
│   ├── test_scan_interface_segregation.py
│   ├── test_scan_liskov_substitution.py
│   ├── test_scan_open_closed.py                   # ~350 lines
│   ├── test_scan_test_god_classes.py
│   └── test_test_splitter.py
├── python_code_style/
│   ├── __init__.py
│   ├── test_scan_acronym_casing.py
│   ├── test_scan_unused_all_exports.py
│   └── test_streamline_docstrings.py
├── python_testing_patterns/
│   ├── __init__.py
│   └── test_scan_test_naming.py
├── shared/
│   ├── __init__.py
│   ├── test_scan_naming_conventions.py
│   ├── test_scan_one_class_per_file.py
│   └── test_scan_tests.py
└── fixtures/
    ├── __init__.py
    └── python/
        ├── src/myproject/
        │   ├── large_service.py                   # God class fixture
        │   ├── mismatch_name.py                   # filename != class name
        │   ├── multi_class.py                     # 2+ classes in one file
        │   └── simple_class.py                    # clean fixture
        └── tests/myproject/
            ├── test_bad_names.py                  # misnamed test
            ├── test_helper_extra.py               # extra test
            ├── test_orphaned.py                   # orphaned test
            └── test_simple_class.py               # clean test fixture
```

### Supporting files also lost

- `src/zolletta_metaskill/__version__.py` — version file (content: `__version__ = "1.2.0"`)
- `src/zolletta_metaskill/cli.py` — CLI entry point
- `.github/workflows/quality.yml` — ruff, ty, mypy, vulture CI
- `.github/workflows/tests.yml` — pytest + coverage CI
- `codecov.yml` — coverage configuration
- `uv.lock` — lockfile (regenerable)
- `.vulture-whitelist.py` — vulture false-positive whitelist

---

## Recovery sources (in priority order)

### Source 1: Git object store — EXHAUSTED

Checked `git fsck --unreachable`, `git cat-file --batch-all-objects`, and all pack objects. The commit containing the tests (`4dce95a`) was created in a different clone and never pushed. **No test blobs or trees exist in the current object store.**

### Source 2: Devin conversation history — PARTIALLY AVAILABLE

Two history files contain the conversation that wrote the tests:

- **`/Users/veronica.bolognesi/.local/share/devin/cli/summaries/history_8ffa4d90e6ca4cec.md`** (334 KB, 307 `test_` mentions) — the main session that wrote all 846 tests, fixed linting, and reached 100% coverage. Contains:
  - Summaries of which test classes were added to which files
  - Line numbers and error messages from test failures (useful for understanding test content)
  - References to specific test function names and assertions
  - Descriptions of edge cases covered (e.g., "Added `TestMainEdgeCases` class with 7 new tests")
  - **NOT full test source code** — the history is a summary, not a transcript of every file write

- **`/Users/veronica.bolognesi/.local/share/devin/cli/summaries/history_04a55110948b4501.md`** (228 KB, 36 `test_` mentions) — a later session that may have additional context.

**What can be extracted**: test class names, test function names, edge cases covered, assertion patterns, fixture names. This is enough to reconstruct the test structure and know what each test should cover, but not the exact source code.

### Source 3: Other sessions' working copies — CHECK

Other Devin sessions or terminal sessions may have a copy of the tests. Check:

```bash
find /Users/veronica.bolognesi -path "*/zolletta-metaskill/tests/*" -name "test_*.py" 2>/dev/null
find /tmp -path "*/zolletta-metaskill/tests/*" 2>/dev/null
find /var/folders -path "*/zolletta-metaskill/tests/*" 2>/dev/null
```

### Source 4: Time Machine — UNAVAILABLE

`tmutil listbackups` reports no machine directory. Time Machine is not configured.

### Source 5: GitHub Actions cache — CHECK

If any CI run was triggered with the tests, the GitHub Actions cache or artifacts might contain them. Check:

```bash
gh run list --repo Zolletta/zolletta-metaskill --limit 20
gh run download <run-id> --repo Zolletta/zolletta-metaskill
```

However, the tests were likely never pushed (the commit was local-only), so CI probably never ran with them.

### Source 6: Source code itself — AVAILABLE

The scanner source files (`src/zolletta_metaskill/**/*.py`) are the best guide for rewriting tests. Each function's branches and edge cases define what the tests must cover. The conversation history tells us the target was 100% coverage, so every branch was tested.

---

## Reconstruction strategy

If no recovery source has the full test files, reconstruct them using this approach:

### Step 1: Extract test inventory from conversation history

Mine `history_8ffa4d90e6ca4cec.md` for:

- Every test class name and test method name mentioned
- Every edge case described (e.g., "test_detect_drift_referenced_file_no_changes")
- Every fixture name (e.g., `python_fixtures`, `tmp_path` usage)
- Every assertion pattern described
- Every `# pragma: no cover` annotation and its reason

**How**:

```bash
grep -E "class Test|def test_|Added.*test" history_8ffa4d90e6ca4cec.md | sort -u
```

### Step 2: Create `conftest.py` and fixtures

Recreate `tests/conftest.py` with:

- `python_fixtures` fixture — returns `Path` to `tests/fixtures/python/`
- Any other shared fixtures mentioned in the history

Recreate `tests/fixtures/python/` with the 8 fixture files:

- `src/myproject/simple_class.py` — one class, clean naming
- `src/myproject/large_service.py` — God class (many methods, many attrs)
- `src/myproject/mismatch_name.py` — filename != class name
- `src/myproject/multi_class.py` — 2+ classes in one file
- `tests/myproject/test_simple_class.py` — clean test
- `tests/myproject/test_bad_names.py` — misnamed test
- `tests/myproject/test_helper_extra.py` — extra test
- `tests/myproject/test_orphaned.py` — orphaned test

### Step 3: Write tests per scanner, using source as guide

For each scanner, read the source file and write tests that cover every branch. Use the conversation history to match the test class structure that was used. The conventions are known:

**Test conventions (from python-testing-patterns rules)**:

- NO `# Arrange`, `# Act`, `# Assert` comments
- Name tests `test_<unit>_<scenario>_<expected>`
- Use `tmp_path` fixture for temporary files
- Use `monkeypatch` for mocking
- Import from `zolletta_metaskill.<module_path>`
- Line length 100, ruff-compatible
- One `Test*` class per logical group

**Coverage conventions**:

- Use `# pragma: no cover` only for truly unreachable code (with comment explaining why)
- Use `# pragma: no branch` for loops that always exit via break
- Target: 100% statement + branch coverage

### Step 4: Test file reconstruction order (by difficulty)

| # | File | Difficulty | Notes |
| --- | --- | --- | --- |
| 1 | `test_cli.py` | Low | CLI is simple, few branches |
| 2 | `test_scan_class_metrics.py` | Low | Simple AST scanning, few edge cases |
| 3 | `test_scan_one_class_per_file.py` | Low | Simple counting logic |
| 4 | `test_scan_naming_conventions.py` | Medium | Multiple categories, auto-detection |
| 5 | `test_scan_tests.py` | Medium | Directory mirroring logic |
| 6 | `test_scan_test_naming.py` | Medium | Naming pattern matching |
| 7 | `test_scan_test_god_classes.py` | Medium | Class metrics in test files |
| 8 | `test_scan_acronym_casing.py` | Medium | Comment/docstring scanning |
| 9 | `test_scan_unused_all_exports.py` | Medium | `__all__` + import tracking |
| 10 | `test_scan_open_closed.py` | Medium | OCP detection, multiple patterns |
| 11 | `test_scan_interface_segregation.py` | Medium | Protocol/ABC analysis |
| 12 | `test_scan_liskov_substitution.py` | Medium | Method signature comparison |
| 13 | `test_scan_dependency_inversion.py` | Medium-Hard | DI detection, many branches |
| 14 | `test_test_splitter.py` | Medium | Code generation + file writing |
| 15 | `test_streamline_docstrings.py` | Hard | Complex docstring rewriting, many branches |
| 16 | `test_doc_staleness_scorer.py` | Hard | Scoring algorithm, many factors |
| 17 | `test_api_doc_validator.py` | Hard | API doc validation, ~975 lines |
| 18 | `test_link_checker.py` | Hard | Link checking, ~1090 lines |
| 19 | `test_drift_analyzer.py` | Hard | Git-based drift, ~1250 lines, needs git fixtures |

### Step 5: Git-based test fixtures

`test_drift_analyzer.py` requires git repos as fixtures. The conversation history reveals the pattern:

- `_init_git_repo(path)` — `git init` + `git config user.email/name`
- `_git_commit(path, msg)` — `git add -A` + `git commit -m msg`
- For drift detection tests: set `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` to an old date (e.g., `"2020-01-01T00:00:00"`) for the initial commit, then make changes and commit normally (today's date). This ensures `get_files_changed_since` detects the changes.

### Step 6: Verify

After reconstructing all tests:

```bash
cd /Users/veronica.bolognesi/.agents/skills/zolletta-metaskill
uv run pytest --cov -x -q          # should show 846+ passed, 100% coverage
uv run ruff check src tests         # should be clean
uv run ty check                     # should be clean
uv run mypy .                       # should be clean
uv run vulture                      # should be clean
```

---

## Known test details from conversation history

### `test_drift_analyzer.py` (~1250 lines, 98 tests at 100%)

Test classes mentioned:

- `TestDetectDriftForDoc` — `test_detect_drift_factual_many_code_changes`, `test_detect_drift_referenced_file_no_changes` (needs `GIT_AUTHOR_DATE`), `test_detect_drift_medium_severity_three_changed_refs`
- `TestMapDocsToCodeBranches` — `test_map_docs_to_code_oserror_reading_doc_skipped` (expects nonexistent doc NOT in mapping)
- `TestDetectDriftBranches` — `test_detect_drift_referenced_file_no_changes`
- `TestVersionHelpersBranches` — `test_version_is_older_v2_shorter_pads_zeros` (`_version_is_older("1.0", "1.0.1") is True`), `test_version_is_older_v2_shorter_not_older` (`_version_is_older("1.0.1", "1.0") is False`)
- `TestCheckReadmeStructureSubstringMatch` — `test_check_readme_structure_substring_match_no_word_skips_issue` (heading "Preinstallation" contains "installation" as substring)
- `TestExtractReferencesBranches` — `test_extract_references_non_code_extension_in_backticks_skipped`

Key helpers:

- `_init_git_repo(str(tmp_path))` — git init + config
- `_git_commit(str(tmp_path), "msg")` — git add -A + commit
- For date-sensitive tests: `env = {**os.environ, "GIT_AUTHOR_DATE": "2020-01-01T00:00:00", "GIT_COMMITTER_DATE": "2020-01-01T00:00:00"}`

### `test_scan_open_closed.py` (~350 lines, 36 tests at 100%)

Test classes:

- `TestIsTypeCheck` — isinstance, type(), type compare, class name attr, type attr, kind attr, non-type-check
- `TestContainsTypeCheck` — boolop OR, boolop no type
- `TestCountTypeBranches` — three isinstance, no type checks, final else
- `TestIsStringTypeDispatch` — concat, fstring, static string, non-getattr, one arg, static string second arg
- `TestFindMatchOnType` — class pattern, value pattern
- `TestScanFile` — if/elif ladder, no ladder, syntax error, getattr dispatch, match on type, multiple nodes, short match
- `TestMain` — python fixtures, skip flag, strict flag, if/elif strict, nonexistent dir, pycache skip, report-only mode

Branch-coverage classes:

- `TestIsTypeCheckBranches` — non-compare name falls through, compare attr not type/kind/class falls through
- `TestCountTypeBranchesFinalElse` — final else exits loop
- `TestIsStringTypeDispatchBranches` — one arg, non-binop non-joinedstr second arg
- `TestScanFileMultipleNodes` — walks multiple nodes, short match no violation
- `TestMainBranches` — pycache skip, report-only mode with violations

### `test_scan_dependency_inversion.py` (100% coverage)

Test classes mentioned:

- `TestIsDataClassBranches` — non-dataclass Call decorator, regular base class
- `TestExtractCreatedDependenciesBranches` — non-self assignment
- `TestGetClassNameFromCallBranches` — Subscript func
- `TestMainBranches` — `__pycache__` skip, `__init__.py` skip, data class skip, factory skip, composition root skip, created dep as constructor param, violations in report-only mode

### `test_streamline_docstrings.py` (100% coverage)

Test classes mentioned:

- `TestRebuildDocstringBranches` — leading/trailing blank stripping
- `TestIsTrivialArgDescBranches` — desc equals arg name
- `TestAnnotationStrBranches` — unparse exception via monkeypatch
- `TestDetectPrefixQuote` — non-matching regex input
- `TestProcessFileBranches` — empty Args section, self/cls in Args, redundant Returns, multiline arg desc, blank line between entries, line without colon before first entry
- `TestApplyEditsBranches` — empty body, non-docstring first stmt, non-string constant, docstring-only body with pass insertion, trailing blank removal, no trailing newline preservation
- `TestRel` — path outside root

### `test_api_doc_validator.py` (~975 lines, 100% coverage)

7 test classes covering 7 branches. Mentioned in subagent output.

### `test_link_checker.py` (~1090 lines, 100% coverage)

4 new test classes (8 tests). Mentioned in subagent output.

### `test_scan_liskov_substitution.py` (100% coverage)

4 new test classes (7 tests).

### `test_scan_acronym_casing.py` (100% coverage)

1 test class covering 1 branch.

### `test_test_splitter.py` (100% coverage)

2 test classes covering 2 branches.

### `test_scan_naming_conventions.py` (100% coverage)

3 new test classes with 14 new tests. Imports: `_auto_detect_package`, `_build_source_index`, `_get_class_names`.

### `test_scan_one_class_per_file.py` (100% coverage)

`TestMainEdgeCases` class with 7 new tests.

### `test_scan_test_naming.py` (100% coverage)

`TestFindTestFunctionsEdgeCases` and `TestMainEdgeCases` classes with 6 new tests.

### `test_scan_unused_all_exports.py` (100% coverage)

Fixed a 102-character line (E501) at line 226.

### `test_scan_test_god_classes.py` (100% coverage)

1 new test class (1 test).

### `test_doc_staleness_scorer.py` (100% coverage)

Achieved by subagent. No specific test class names recorded.

---

## `# pragma: no cover` annotations used

From the conversation history, these pragmas were added to source files:

| File | Line | Reason |
| --- | --- | --- |
| `drift_analyzer.py` | 553-554 | `except ValueError` in `_parse_version_part` — regex ensures cleaned is digits-only or empty |
| `drift_analyzer.py` | 496-502 | Temporal drift issue — requires a doc older than threshold (hard to test without mocking dates) |
| `scan_open_closed.py` | 94 | `if not isinstance(node, ast.Call)` — annotation is `ast.Call`, truly unreachable |
| `scan_open_closed.py` | 73 | `while isinstance(current, ast.If)` — `# pragma: no branch` — loop always exits via break |
| `streamline_docstrings.py` | 188 | `else: i += 1` in `parse_docstring` — dead code, inner while always consumes all non-header lines |

---

## Estimated effort

| Approach | Effort | Fidelity |
| --- | --- | --- |
| Find in another session's working copy | Minutes | 100% (exact files) |
| Find in GitHub Actions artifacts | Minutes | 100% (exact files) |
| Reconstruct from conversation history + source | 4-8 hours | 90-95% (same coverage, different implementation details) |
| Write from scratch using source only | 8-16 hours | 90% (same coverage, no history matching) |

## Recommended approach

1. **First**: search for surviving copies (Source 3 and Source 5) — takes 5 minutes
2. **If found**: copy them in, run `pytest --cov`, fix any import path issues (the source tree was restructured from `scanners/` flat to per-skill subfolders)
3. **If not found**: use the reconstruction strategy. Start with the easy files (Step 4 table, rows 1-6). Use subagents to parallelize — each subagent writes tests for 2-3 scanners. Use the conversation history to match test class names and edge cases. Use the source files to ensure 100% branch coverage.
4. **Import path migration**: the source tree changed from `src/zolletta_metaskill/scanners/` (flat) to `src/zolletta_metaskill/{patterns,python_code_style,python_testing_patterns,shared}/` (per-skill). All test imports must be updated:
   - `from zolletta_metaskill.scanners.scan_class_metrics import ...` → `from zolletta_metaskill.patterns.scan_class_metrics import ...`
   - `from zolletta_metaskill.scanners.scan_acronym_casing import ...` → `from zolletta_metaskill.python_code_style.scan_acronym_casing import ...`
   - `from zolletta_metaskill.scanners.scan_test_naming import ...` → `from zolletta_metaskill.python_testing_patterns.scan_test_naming import ...`
   - `from zolletta_metaskill.scanners.scan_naming_conventions import ...` → `from zolletta_metaskill.shared.scan_naming_conventions import ...`
   - `from zolletta_metaskill.scanners.scan_one_class_per_file import ...` → `from zolletta_metaskill.shared.scan_one_class_per_file import ...`
   - `from zolletta_metaskill.scanners.scan_tests import ...` → `from zolletta_metaskill.shared.scan_tests import ...`
   - `from zolletta_metaskill.scanners.scan_dependency_inversion import ...` → `from zolletta_metaskill.patterns.scan_dependency_inversion import ...`
   - `from zolletta_metaskill.scanners.scan_interface_segregation import ...` → `from zolletta_metaskill.patterns.scan_interface_segregation import ...`
   - `from zolletta_metaskill.scanners.scan_liskov_substitution import ...` → `from zolletta_metaskill.patterns.scan_liskov_substitution import ...`
   - `from zolletta_metaskill.scanners.scan_open_closed import ...` → `from zolletta_metaskill.patterns.scan_open_closed import ...`
   - `from zolletta_metaskill.scanners.scan_test_god_classes import ...` → `from zolletta_metaskill.patterns.scan_test_god_classes import ...`
   - `from zolletta_metaskill.scanners.test_splitter import ...` → `from zolletta_metaskill.patterns.test_splitter import ...`
   - `from zolletta_metaskill.scanners.streamline_docstrings import ...` → `from zolletta_metaskill.python_code_style.streamline_docstrings import ...`
   - `from zolletta_metaskill.scanners.scan_unused_all_exports import ...` → `from zolletta_metaskill.python_code_style.scan_unused_all_exports import ...`

---

## Tests required by PLAN-PHP-SUPPORT

PLAN-PHP-SUPPORT creates new Python source files but defers test creation to this plan (see PLAN-PHP-SUPPORT "Testing policy"). The table below lists every deferred test. Each must be created during Phase 6 of PLAN-MASTER.md, after the core test recovery is complete.

### `common/` (PLAN-PHP-SUPPORT Phase 1.5)

| Test file | Source file | What it must cover |
| --- | --- | --- |
| `tests/common/test_models.py` | `src/zolletta_metaskill/common/models.py` | Dataclass construction (`ModuleInfo`, `ClassInfo`, `MethodInfo`, `ImportInfo`), immutability (frozen=True), field defaults, optional fields (`all_exports=None`, `docstring=None`), `has_syntax_error` flag |
| `tests/common/test_registry.py` | `src/zolletta_metaskill/common/registry.py` | `register_engine()` + `get_engine()` round-trip, unknown language raises, `get_engine_for_file()` by extension, `available_languages()` list, duplicate registration |

### `engines/` (PLAN-PHP-SUPPORT Phase 2.4)

| Test file | Source file | What it must cover |
| --- | --- | --- |
| `tests/engines/test_python_engine.py` | `src/zolletta_metaskill/engines/python_engine.py` | `parse_module()` on various Python constructs (classes, methods, imports, `__all__`, `ast.Raise`, ABC/Protocol bases, `@staticmethod`, `_` prefix visibility), `is_test_file()` (filename + class name), `file_extensions()`, `is_source_file()`, syntax error handling |
| `tests/engines/test_php_engine.py` | `src/zolletta_metaskill/engines/php_engine.py` | `parse_module()` on PHP fixtures (class_declaration, method_declaration, use_declaration, interface_declaration, trait_declaration, abstract_modifier, static_modifier, visibility), `is_test_file()` (`*Test.php`), `file_extensions()`, PSR-4 autoload mapping. Fixtures: `tests/fixtures/php/src/` with sample classes, interfaces, traits |

### `php_patterns/` (PLAN-PHP-SUPPORT Phase 6.2)

| Test file | Source file | What it must cover |
| --- | --- | --- |
| `tests/php_patterns/test_scan_php_dependency_inversion.py` | `src/zolletta_metaskill/php_patterns/scan_php_dependency_inversion.py` | `new` in constructors (DIP violation), composition root exclusion, factory pattern exclusion, report-only mode, `__pycache__` skip. Fixtures: `tests/fixtures/php/src/` with violation examples |
| `tests/php_patterns/test_scan_php_interface_segregation.py` | `src/zolletta_metaskill/php_patterns/scan_php_interface_segregation.py` | Fat interfaces (many methods), partial implementers (subset of methods used), interface with few implementers (not a violation), report-only mode |
| `tests/php_patterns/test_scan_php_open_closed.py` | `src/zolletta_metaskill/php_patterns/scan_php_open_closed.py` | `instanceof` chains (OCP violation), if/elseif type ladders, match expression on type, no type-check (clean), report-only mode |
