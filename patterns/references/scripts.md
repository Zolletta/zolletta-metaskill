# Scripts Reference

All scripts live in `scripts/python/` and are designed for Python codebases. They use the `ast` module for static analysis — no code execution required.

Every script supports `--skip` (exit 0 with "SKIPPED" message) for projects that intentionally don't follow a given convention. Scripts that report violations also support `--strict` (exit code 1 if violations found).

## Triage Scripts

### scan_class_metrics.py

Scans all `.py` files and reports every class sorted by line count, with method count, public method count, and `self.*` attribute count.

```bash
python3 scripts/python/scan_class_metrics.py <directory> [--top N] [--min-lines N]
```

| Option          | Default | Description                       |
| --------------- | ------- | --------------------------------- |
| `<directory>`   | `src`   | Root directory to scan            |
| `--top N`       | 30      | Show only the top N classes       |
| `--min-lines N` | 50      | Skip classes shorter than N lines |

**Output**: a table with columns `LINES`, `ALL` (methods), `PUB` (public methods), `ATTRS` (`self.*` attributes), `CLASS`, and `file:start-end`.

Use the output to identify candidates, then read the code to apply the "reason to change" test.

### scan_test_classes.py

Scans test files and reports test classes sorted by size, with method count and method names. Detects test classes that test multiple unrelated SUTs.

```bash
python3 scripts/python/scan_test_classes.py <directory> [--top N] [--show-methods]
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
python3 scripts/python/scan_one_class_per_file.py <directory> [--strict] [--ignore-zero] [--skip]
```

| Option          | Default | Description                                         |
| --------------- | ------- | --------------------------------------------------- |
| `<directory>`   | `src`   | Root directory to scan                              |
| `--strict`      | off     | Exit with code 1 if violations are found            |
| `--ignore-zero` | off     | Don't report files with 0 classes (utility modules) |
| `--skip`        | off     | Skip this check entirely                            |

**Exceptions**: `__init__.py` is always skipped. Files with 0 classes are reported as low severity — use `--ignore-zero` to hide them.

### scan_test_structure_mirror.py

Checks that the test directory structure mirrors the source directory structure. Reports source dirs with no test dir, test dirs with no source dir, and source files containing classes with no corresponding test file.

```bash
python3 scripts/python/scan_test_structure_mirror.py \
    --src <src_root> --tests <test_root> \
    [--src-package <name>] [--tests-package <name>] \
    [--ignore-dirs <dir1,dir2,...>] [--skip]
```

| Option            | Default                 | Description                                                 |
| ----------------- | ----------------------- | ----------------------------------------------------------- |
| `--src`           | `src`                   | Source root directory                                       |
| `--tests`         | `tests`                 | Test root directory                                         |
| `--src-package`   | auto-detect             | Package path within `--src`                                 |
| `--tests-package` | same as `--src-package` | Package path within `--tests`                               |
| `--ignore-dirs`   | (none)                  | Comma-separated dir names to skip (e.g. `assets,templates`) |
| `--skip`          | off                     | Skip this check entirely                                    |

**File matching convention**: `src/.../my_module.py` -> `tests/.../test_my_module*.py`. One source class can have many test files (e.g. `test_cache_operations.py`, `test_cache_getters.py`), so matching is by prefix. Also checks class-name-based prefixes: `src/.../my_module.py` with class `MyClass` -> `tests/.../test_my_class*.py`.

### scan_naming_conventions.py

Checks two naming conventions in a single pass:

1. **Source file name == class name** — each source file with exactly one class should have a filename matching the class name (snake_case file → PascalCase class). Files with 0 or 2+ classes are skipped (handled by `scan_one_class_per_file.py`).
2. **Test file naming** — every `test_*.py` file must follow `test_<source_stem><eventual_suffix>.py`, where `<source_stem>` is the stem of a source file (or the snake_case form of a source class name) in the mirrored source directory. Test files that don't match any source file or class are reported as orphan/misnamed.

```bash
python3 scripts/python/scan_naming_conventions.py \
    --src <src_root> --tests <test_root> \
    [--src-package <name>] [--tests-package <name>] \
    [--ignore-dirs <dir1,dir2,...>] [--strict] [--skip]
```

| Option            | Default                 | Description                                                 |
| ----------------- | ----------------------- | ----------------------------------------------------------- |
| `--src`           | `src`                   | Source root directory                                       |
| `--tests`         | `tests`                 | Test root directory                                         |
| `--src-package`   | auto-detect             | Package path within `--src`                                 |
| `--tests-package` | same as `--src-package` | Package path within `--tests`                               |
| `--ignore-dirs`   | (none)                  | Comma-separated dir names to skip (e.g. `assets,templates`) |
| `--strict`        | off                     | Exit with code 1 if violations are found                    |
| `--skip`          | off                     | Skip this check entirely                                    |

**Matching logic**: for each test file `test_cache_operations.py`, the script strips `test_` to get `cache_operations`, then checks if any source file stem in the mirrored directory is a prefix (followed by nothing or by `_`). So `cache.py` matches `cache_operations` (suffix `_operations`), and `cache_operations.py` also matches (no suffix). The longest match wins. Class-name-based prefixes are also checked: source file `my_module.py` with class `MyClass` accepts `test_my_class*.py`.

**Use this instead of** `scan_one_class_per_file.py` + `scan_test_structure_mirror.py` when you want a single focused check on naming compliance (not coverage or directory mirroring).

## SOLID Validator Scripts

### scan_dependency_inversion.py (DIP)

Detects classes that instantiate their dependencies internally (`self.x = SomeClass(...)`) instead of receiving them as constructor parameters. Excludes entry points, dataclasses, factories, and stdlib types.

```bash
python3 scripts/python/scan_dependency_inversion.py <directory>
    [--entry-points <pattern1,pattern2,...>] [--skip] [--strict]
```

| Option           | Default                                                | Description                                  |
| ---------------- | ------------------------------------------------------ | -------------------------------------------- |
| `<directory>`    | `src`                                                  | Root directory to scan                       |
| `--entry-points` | `main,cli,app,__main__,cite,manage,wsgi,asgi,conftest` | Comma-separated filename patterns to exclude |
| `--skip`         | off                                                    | Skip this check entirely                     |
| `--strict`       | off                                                    | Exit with code 1 if violations are found     |

**Exclusions**: entry points (composition roots), dataclasses/NamedTuples/TypedDicts/Enums, factory classes, and stdlib types are automatically excluded.

### scan_interface_segregation.py (ISP)

Detects fat interfaces — Protocols/ABCs with many methods where implementers stub or raise NotImplementedError for methods they don't need.

```bash
python3 scripts/python/scan_interface_segregation.py <directory> [--min-methods N] [--skip] [--strict]
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
python3 scripts/python/scan_open_closed.py <directory> [--min-branches N] [--skip] [--strict]
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
python3 scripts/python/scan_liskov_substitution.py <directory> [--skip] [--strict]
```

| Option        | Default | Description                              |
| ------------- | ------- | ---------------------------------------- |
| `<directory>` | `src`   | Root directory to scan                   |
| `--skip`      | off     | Skip this check entirely                 |
| `--strict`    | off     | Exit with code 1 if violations are found |

**Checks**: overridden methods with extra required params, fewer params than parent, new exception types, stub overrides (pass/return None when parent has a real body).

## Refactoring Script

### test_splitter.py

Splits a God test class into per-SUT test files. Groups test methods by prefix, creates a new test file per SUT, and writes them to a temp folder. The original file is never modified.

```bash
# Step 1: auto-derive prefixes (no mapping needed)
python3 scripts/python/test_splitter.py <test_file>

# Step 2: review the proposed mapping, then split with --dry-run
python3 scripts/python/test_splitter.py <test_file> \
    --mapping '{"cache": "Cache", "extract_defaults": "DefaultsExtractor"}' \
    --dry-run

# Step 3: write the split files to .scratches/test_split/<filename>/
python3 scripts/python/test_splitter.py <test_file> \
    --mapping '{"cache": "Cache", "extract_defaults": "DefaultsExtractor"}'
```

| Option             | Default                             | Description                                               |
| ------------------ | ----------------------------------- | --------------------------------------------------------- |
| `<test_file>`      | (required)                          | Path to the test .py file to split                        |
| `--mapping <json>` | (none)                              | JSON file or inline JSON mapping prefix to SUT class name |
| `--out <dir>`      | `.scratches/test_split/<filename>/` | Output directory                                          |
| `--class <name>`   | first test class                    | Name of the test class to split                           |
| `--dry-run`        | off                                 | Show the proposed split without writing files             |

**Workflow**:

1. Run without `--mapping` to auto-derive prefixes and see a proposed mapping
2. Adjust the mapping (prefix -> SUT class name) based on your knowledge
3. Run with `--dry-run` to verify the grouping
4. Run without `--dry-run` to write files to the temp folder
5. Review the generated files, adjust imports if needed
6. Move the files to the test directory and delete the original

**What gets copied to each split file**:

- Module docstring (with "split from" note)
- All imports from the original file
- `pytestmark` assignment (if present)
- Shared methods (fixtures, helpers, setup/teardown) — copied to every split file
- Test methods matching the SUT's prefix

**Unmatched methods**: methods that don't match any prefix go to a `test__unmatched.py` file. Review these and add their prefixes to the mapping.

## Full Workflow

The scripts give you **triage data**, not verdicts. The recommended workflow:

1. `scan_class_metrics.py src/` → get the largest classes
2. Read the top 5-10 candidates
3. For each, list its responsibilities and group by domain
4. Apply the "reason to change" test
5. `scan_test_classes.py tests/ --show-methods` → find test classes testing multiple SUTs
6. For test God classes, check if each SUT has its own source file
7. `scan_one_class_per_file.py src/` → find files with multiple classes or name mismatches
8. `scan_test_structure_mirror.py` → find source files with no test file and structural gaps
9. `scan_naming_conventions.py` → find source files where class name ≠ filename and orphan/misnamed test files
10. If the human decides to split a test God class, use `test_splitter.py`
11. `scan_dependency_inversion.py src/` → find dependencies created internally
12. `scan_interface_segregation.py src/` → find fat protocols
13. `scan_open_closed.py src/` → find type-based branching that should be polymorphism
14. `scan_liskov_substitution.py src/` → find subclass overrides that break substitutability

For non-Python languages, see `general-principles.md` → God Class Detection for manual grep/find equivalents.
