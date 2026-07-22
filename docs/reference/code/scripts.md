---
audience: human, ai
status: stable
skills: [patterns]
---

# Scripts Reference

> **Language-agnostic**: the scanning workflow applies to any project. The scripts currently support Python via its `ast` module. For PHP and other languages, apply the principles manually by reading the code — the scripts are a triage accelerator, not a requirement.

All scripts live in per-skill subfolders under `src/zolletta_metaskill/` (`patterns/`, `python_code_style/`, `python_testing_patterns/`, `shared/`) and are designed for Python codebases. They use the `ast` module for static analysis — no code execution required.

Every script supports `--skip` (exit 0 with "SKIPPED" message) for projects that intentionally don't follow a given convention. Scripts that report violations also support `--strict` (exit code 1 if violations found).

## Triage Scripts

### scan_class_metrics.py

Scans all `.py` files and reports every class sorted by line count, with method count, public method count, and `self.*` attribute count.

```bash
python3 src/zolletta_metaskill/patterns/scan_class_metrics.py <directory> [--top N] [--min-lines N]
```

| Option          | Default | Description                       |
| --------------- | ------- | --------------------------------- |
| `<directory>`   | `src`   | Root directory to scan            |
| `--top N`       | 30      | Show only the top N classes       |
| `--min-lines N` | 50      | Skip classes shorter than N lines |

**Output**: a table with columns `LINES`, `ALL` (methods), `PUB` (public methods), `ATTRS` (`self.*` attributes), `CLASS`, and `file:start-end`.

Use the output to identify candidates, then read the code to apply the "reason to change" test.

### scan_test_god_classes.py

Scans test files and reports test classes sorted by size, with method count and method names. Detects test classes that test multiple unrelated SUTs.

```bash
python3 src/zolletta_metaskill/patterns/scan_test_god_classes.py <directory> [--top N] [--show-methods]
```

| Option           | Default | Description                                             |
| ---------------- | ------- | ------------------------------------------------------- |
| `<directory>`    | `tests` | Root directory to scan                                  |
| `--top N`        | 30      | Show only the top N classes                             |
| `--show-methods` | off     | List all method names per class (helps spot mixed SUTs) |

## Structural Convention Scripts

### scan_one_class_per_file.py

Checks the "1 class 1 file, 1 file 1 class" convention. Reports files with 2+ classes, files with 0 classes (non-`__init__.py`), and class names that don't match the filename.

```bash
python3 src/zolletta_metaskill/shared/scan_one_class_per_file.py <directory> [--strict] [--ignore-zero] [--skip]
```

| Option          | Default | Description                                         |
| --------------- | ------- | --------------------------------------------------- |
| `<directory>`   | `src`   | Root directory to scan                              |
| `--strict`      | off     | Exit with code 1 if violations are found            |
| `--ignore-zero` | off     | Don't report files with 0 classes (utility modules) |
| `--skip`        | off     | Skip this check entirely                            |

**Exceptions**: `__init__.py` is always skipped. Files with 0 classes are reported as low severity — use `--ignore-zero` to hide them.

### scan_tests.py

Checks that the test directory structure mirrors the source directory structure. Outputs a markdown report with five tables:

1. **Misnamed tests** — test files whose name doesn't match the source stem or class name of the source they test. Action: rename.
2. **Misplaced tests** — test files with a name matching a source file but located in the wrong directory. Action: move.
3. **Orphaned tests** — test files or directories that don't match any source file or directory. Action: delete or investigate.
4. **Missing tests** — source files with classes that have no direct test file and no indirect class reference in any test file. Action: write new tests.
5. **Indirect references** — test files that reference classes from source files without a direct test. Informative only: shows which test files provide indirect coverage for otherwise untested source files.

```bash
python3 src/zolletta_metaskill/shared/scan_tests.py \
    --src <src_root> --tests <test_root> \
    [--src-package <name>] [--tests-package <name>] \
    [--ignore-dirs <dir1,dir2,...>] [--skip]
```

| Option | Default | Description |
| --- | --- | --- |
| `--src` | `src` | Source root directory |
| `--tests` | `tests` | Test root directory |
| `--src-package` | auto-detect | Package path within `--src` |
| `--tests-package` | same as `--src-package` | Package path within `--tests` |
| `--ignore-dirs` | (none) | Comma-separated dir names to skip (e.g. `assets,templates`) |
| `--skip` | off | Skip this check entirely |

**File matching convention**: `src/.../my_module.py` -> `tests/.../test_my_module*.py`. One source class can have many test files (e.g. `test_cache_operations.py`, `test_cache_getters.py`), so matching is by prefix. Also checks class-name-based prefixes: `src/.../my_module.py` with class `MyClass` -> `tests/.../test_my_class*.py`. Uses longest-prefix matching to avoid false positives (e.g. `test_scenario_writer.py` matches `scenario_writer.py`, not `scenario.py`). When two source files have equal-length prefixes (e.g. two `cache.py` files in different directories), prefers the one in the same directory as the test.

**Indirect test detection**: source files with no mirrored test file are always checked for indirect references. The script reads all test files once and checks if any class name from the source file appears in the test code. Files with indirect references are excluded from the "missing" table — they have no mirrored test file but their classes ARE exercised through other test files.

**Coverage cross-check (mandatory)**: The "Missing tests" table is a structural signal only. Before reporting any file from this table as a finding in a review, you MUST run `pytest --cov` and check the file's coverage. If the file has >50% coverage, it is adequately tested via indirect tests — downgrade to informational. Only report as a finding if coverage <50% AND no indirect references. This prevents the whack-a-mole cycle where every review re-reports the same structurally-missing-but-adequately-covered files.

### scan_naming_conventions.py

Checks two naming conventions in a single pass:

1. **Source file name == class name** — each source file with exactly one class should have a filename matching the class name (snake_case file → PascalCase class). Files with 0 or 2+ classes are skipped (handled by `scan_one_class_per_file.py`).
2. **Test file naming** — every `test_*.py` file must follow `test_<source_stem><eventual_suffix>.py`, where `<source_stem>` is the stem of a source file (or the snake_case form of a source class name) in the mirrored source directory. Test files that don't match any source file or class are reported as orphan/misnamed.

```bash
python3 src/zolletta_metaskill/shared/scan_naming_conventions.py \
    --src <src_root> --tests <test_root> \
    [--src-package <name>] [--tests-package <name>] \
    [--ignore-dirs <dir1,dir2,...>] [--strict] [--skip]
```

| Option | Default | Description |
| --- | --- | --- |
| `--src` | `src` | Source root directory |
| `--tests` | `tests` | Test root directory |
| `--src-package` | auto-detect | Package path within `--src` |
| `--tests-package` | same as `--src-package` | Package path within `--tests` |
| `--ignore-dirs` | (none) | Comma-separated dir names to skip (e.g. `assets,templates`) |
| `--strict` | off | Exit with code 1 if violations are found |
| `--skip` | off | Skip this check entirely |

**Matching logic**: for each test file `test_cache_operations.py`, the script strips `test_` to get `cache_operations`, then checks if any source file stem in the mirrored directory is a prefix (followed by nothing or by `_`). So `cache.py` matches `cache_operations` (suffix `_operations`), and `cache_operations.py` also matches (no suffix). The longest match wins. Class-name-based prefixes are also checked: source file `my_module.py` with class `MyClass` accepts `test_my_class*.py`.

**Use this instead of** `scan_one_class_per_file.py` + `scan_tests.py` when you want a single focused check on naming compliance (not coverage or directory mirroring).

## SOLID Validator Scripts

### scan_dependency_inversion.py (DIP)

Detects classes that instantiate their dependencies internally (`self.x = SomeClass(...)`) instead of receiving them as constructor parameters. Excludes entry points, dataclasses, factories, and stdlib types.

```bash
python3 src/zolletta_metaskill/patterns/scan_dependency_inversion.py <directory>
    [--entry-points <pattern1,pattern2,...>] [--skip] [--strict]
```

| Option | Default | Description |
| --- | --- | --- |
| `<directory>` | `src` | Root directory to scan |
| `--entry-points` | `main,cli,app,__main__,myproject,manage,wsgi,asgi,conftest` | Comma-separated filename patterns to exclude |
| `--skip` | off | Skip this check entirely |
| `--strict` | off | Exit with code 1 if violations are found |

**Exclusions**: entry points (composition roots by filename pattern), classes that create DI containers (`make_container()`, `Container()`, etc. — detected semantically as composition roots), dataclasses/NamedTuples/TypedDicts/Enums, factory classes, and stdlib types are automatically excluded.

### scan_interface_segregation.py (ISP)

Detects fat interfaces — Protocols/ABCs with many methods where implementers stub or raise NotImplementedError for methods they don't need.

```bash
python3 src/zolletta_metaskill/patterns/scan_interface_segregation.py <directory> [--min-methods N] [--skip] [--strict]
```

| Option            | Default | Description                                  |
| ----------------- | ------- | -------------------------------------------- |
| `<directory>`     | `src`   | Root directory to scan                       |
| `--min-methods N` | 5       | Minimum abstract method count to flag as fat |
| `--skip`          | off     | Skip this check entirely                     |
| `--strict`        | off     | Exit with code 1 if violations are found     |

**Checks**: Protocol/ABC classes with N+ methods, implementers that raise NotImplementedError or have stub bodies (pass/return None) for interface methods.

### scan_open_closed.py (OCP)

Detects type-based branching (if/elif isinstance ladders, match/case on type, getattr string dispatch) that should be replaced with polymorphism.

```bash
python3 src/zolletta_metaskill/patterns/scan_open_closed.py <directory> [--min-branches N] [--skip] [--strict]
```

| Option             | Default | Description                              |
| ------------------ | ------- | ---------------------------------------- |
| `<directory>`      | `src`   | Root directory to scan                   |
| `--min-branches N` | 3       | Minimum type-check branches to flag      |
| `--skip`           | off     | Skip this check entirely                 |
| `--strict`         | off     | Exit with code 1 if violations are found |

### scan_liskov_substitution.py (LSP)

Detects subclass methods that break substitutability: incompatible signatures, new exception types, empty-body overrides.

```bash
python3 src/zolletta_metaskill/patterns/scan_liskov_substitution.py <directory> [--skip] [--strict]
```

| Option        | Default | Description                              |
| ------------- | ------- | ---------------------------------------- |
| `<directory>` | `src`   | Root directory to scan                   |
| `--skip`      | off     | Skip this check entirely                 |
| `--strict`    | off     | Exit with code 1 if violations are found |

**Checks**: overridden methods with extra required params, fewer params than parent, new exception types, stub overrides (pass/return None when parent has a real body).

## Dead Code Script

### scan_unused_all_exports.py

Finds names listed in `__all__` that are never imported by any other module in the source tree. Complements vulture, which treats `__all__` entries as "used" (public API exports) and therefore never flags them as dead code — even when no module ever imports them.

```bash
python3 src/zolletta_metaskill/python_code_style/scan_unused_all_exports.py <directory> [--strict] [--json] [--skip]
```

| Option        | Default | Description                                  |
| ------------- | ------- | -------------------------------------------- |
| `<directory>` | `src`   | Root source directory to scan                |
| `--strict`    | off     | Exit with code 1 if unused exports are found |
| `--json`      | off     | Output as JSON instead of markdown           |
| `--skip`      | off     | Skip this check entirely                     |

**How it works**: extracts all `__all__` entries from every `.py` file, builds an index of all imported names across the source tree, then cross-references. Names listed in `__all__` but never imported by any file other than the one defining `__all__` are reported as unused.

**Use alongside vulture**: run vulture first for general dead-code detection, then this scanner for the `__all__` gap. Do not double-report symbols that vulture already catches.

### scan_test_naming.py

Checks test function names against the `test_<unit>_<scenario>_<expected>` convention. Flags functions with fewer than `--min-segments` underscore-separated segments after the `test_` prefix. This is a deterministic replacement for manual review of test function names.

```bash
python3 src/zolletta_metaskill/python_testing_patterns/scan_test_naming.py <directory> [--min-segments N] [--strict] [--json] [--skip]
```

| Option             | Default | Description                              |
| ------------------ | ------- | ---------------------------------------- |
| `<directory>`      | `tests` | Root test directory to scan              |
| `--min-segments N` | 3       | Minimum segments after `test_` prefix    |
| `--strict`         | off     | Exit with code 1 if violations are found |
| `--json`           | off     | Output as JSON instead of markdown       |
| `--skip`           | off     | Skip this check entirely                 |

**How it works**: for each `test_*.py` or `*_test.py` file, extracts every `test_` function via AST, counts the underscore-separated segments after `test_`, and flags functions with fewer than `--min-segments`. The same input always produces the same output — no AI judgment involved.

**Why this exists**: manual review of test function names was non-deterministic and produced different violation counts on each run. The scanner replaces subjective judgment with a simple, objective segment count.

### scan_acronym_casing.py

Checks that acronyms in PascalCase class names stay fully uppercase (e.g. `HTTPClientFactory`, not `HttpClientFactory`). The scanner splits each PascalCase class name into words, checks each word against the configured acronym list, and flags any word that case-insensitively matches an acronym but isn't all-uppercase.

```bash
python3 src/zolletta_metaskill/python_code_style/scan_acronym_casing.py <directory> [--acronyms <list>] [--strict] [--json] [--skip]
```

| Option | Default | Description |
| --- | --- | --- |
| `<directory>` | `src` | Root source directory to scan |
| `--acronyms` | (from assets + settings) | Comma-separated acronym list (overrides built-in + settings) |
| `--strict` | off | Exit with code 1 if violations are found |
| `--json` | off | Output as JSON instead of markdown |
| `--skip` | off | Skip this check entirely |

The acronym list is built additively:

1. **Shipped base**: `python-code-style/assets/acronyms.json` (common SE acronyms: CI, CD, CICD, HTTP, HTTPS, JSON, SQL, URL, etc.) — always loaded
2. **Project-specific**: the top-level `acronyms` array in `settings.json` — merged with the shipped list (additive, not replacing)
3. **`--acronyms` CLI flag**: fully replaces both (for testing/debugging only)

## test_splitter.py

Automates splitting a test God class that tests multiple SUTs into per-SUT test files.

```bash
python3 src/zolletta_metaskill/patterns/test_splitter.py <test_file> [--dry-run] [--output-dir <dir>]
```

| Option         | Default  | Description                                    |
| -------------- | -------- | ---------------------------------------------- |
| `<test_file>`  | (req)    | Path to the test file to split                 |
| `--dry-run`    | off      | Show what would be split without writing files |
| `--output-dir` | same dir | Directory to write split files to              |

**What the splitter handles automatically**:

- Copies all imports to each split file
- Copies `pytestmark` to each split file
- Copies shared methods (fixtures, helpers) to each split file
- Generates proper class names (`Test<SutName>`)
- Indents methods correctly inside the class
- Reports unmatched methods for mapping review

**What the splitter does NOT do**:

- Remove unused imports from split files (review manually)
- Move the files to the final test directory (human reviews first)
- Delete the original file (human confirms the split is correct)
- Run the tests (human verifies the split files pass)

## Complete Workflow

The full scanning workflow runs all scripts in this order:

1. `scan_class_metrics.py` — triage: find the largest classes
2. `scan_test_god_classes.py --show-methods` — triage: find test God classes
3. `scan_one_class_per_file.py` — structural: one class per file
4. `scan_tests.py` — structural: test mirroring + missing tests
5. `scan_naming_conventions.py` — structural: naming compliance
6. `scan_dependency_inversion.py` — SOLID: DIP violations
7. `scan_interface_segregation.py` — SOLID: ISP violations
8. `scan_open_closed.py` — SOLID: OCP violations
9. `scan_liskov_substitution.py` — SOLID: LSP violations
10. `scan_unused_all_exports.py` — dead code: unused `__all__` exports
11. `scan_test_naming.py` — test naming convention
12. `scan_acronym_casing.py` — acronym casing convention
13. For each test God class: `test_splitter.py --dry-run` → review → split
14. Apply the "reason to change" test to each top candidate from step 1

## Repository Scripts

These are project-management scripts at the repository root, separate from the scanning scripts above.

### `.bump`

Bumps the zolletta-metaskill version across all files.

```bash
./.bump --to <version>
```

Updates: `pyproject.toml`, `src/zolletta_metaskill/__init__.py`, all `SKILL.md` front-matter version fields, and `setup/assets/settings_template.json` (`setup_version`).

### `.install`

Installs the skill into `~/.agents/skills/` and symlinks it into every detected AI agent tool's skills directory.

```bash
./.install           # install/refresh
./.install --force   # replace real dirs with symlinks
```

See [Install Zolletta-MetaSkill](../../how-to/install.md) for details.
