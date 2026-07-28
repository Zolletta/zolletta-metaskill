---
audience: human, ai
status: stable
skills: [patterns]
---

# Scripts Reference

> **Language-agnostic**: the scanning workflow applies to any project. The scripts support Python (via its `ast` module) and PHP (via tree-sitter-php). For other languages, apply the principles manually by reading the code — the scripts are a triage accelerator, not a requirement.

All scripts live in per-skill subfolders under `src/zolletta_metaskill/` (`patterns/`, `php_patterns/`, `python_code_style/`, `python_testing_patterns/`, `shared/`). Language-agnostic scanners consume a `ModuleInfo` data model produced by a `LanguageEngine` — no code execution required.

Every script supports `--skip` (exit 0 with "SKIPPED" message) for projects that intentionally don't follow a given convention. Scripts that report violations also support `--strict` (exit code 1 if violations found).

## Triage Scripts

### scan_class_metrics.py

Scans all `.py` files and reports every class sorted by line count, with method count, public method count, and `self.*` attribute count.

```bash
python3 src/zolletta_metaskill/patterns/scan_class_metrics.py <directory> [--top N] [--min-lines N]
```

| Option          | Default | Description                       |
|-----------------|---------|-----------------------------------|
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
|------------------|---------|---------------------------------------------------------|
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
|-----------------|---------|-----------------------------------------------------|
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

| Option            | Default                 | Description                                                 |
|-------------------|-------------------------|-------------------------------------------------------------|
| `--src`           | `src`                   | Source root directory                                       |
| `--tests`         | `tests`                 | Test root directory                                         |
| `--src-package`   | auto-detect             | Package path within `--src`                                 |
| `--tests-package` | same as `--src-package` | Package path within `--tests`                               |
| `--ignore-dirs`   | (none)                  | Comma-separated dir names to skip (e.g. `assets,templates`) |
| `--skip`          | off                     | Skip this check entirely                                    |

**File matching convention**: Test files match source files by stem prefix: `test_cache_*` matches `cache.py`.

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

| Option            | Default                 | Description                                                 |
|-------------------|-------------------------|-------------------------------------------------------------|
| `--src`           | `src`                   | Source root directory                                       |
| `--tests`         | `tests`                 | Test root directory                                         |
| `--src-package`   | auto-detect             | Package path within `--src`                                 |
| `--tests-package` | same as `--src-package` | Package path within `--tests`                               |
| `--ignore-dirs`   | (none)                  | Comma-separated dir names to skip (e.g. `assets,templates`) |
| `--strict`        | off                     | Exit with code 1 if violations are found                    |
| `--skip`          | off                     | Skip this check entirely                                    |

**Matching logic**: Longest stem-prefix match wins; class-name prefixes also checked.

## SOLID Validator Scripts

### scan_dependency_inversion.py (DIP)

Detects classes that instantiate their dependencies internally (`self.x = SomeClass(...)`) instead of receiving them as constructor parameters. Excludes entry points, dataclasses, factories, and stdlib types.

```bash
python3 src/zolletta_metaskill/patterns/scan_dependency_inversion.py <directory>
    [--entry-points <pattern1,pattern2,...>] [--skip] [--strict]
```

| Option           | Default                                                     | Description                                  |
|------------------|-------------------------------------------------------------|----------------------------------------------|
| `<directory>`    | `src`                                                       | Root directory to scan                       |
| `--entry-points` | `main,cli,app,__main__,myproject,manage,wsgi,asgi,conftest` | Comma-separated filename patterns to exclude |
| `--skip`         | off                                                         | Skip this check entirely                     |
| `--strict`       | off                                                         | Exit with code 1 if violations are found     |

**Exclusions**: Excludes entry points, DI containers, dataclasses, factories, and stdlib types.

### scan_interface_segregation.py (ISP)

Detects fat interfaces — Protocols/ABCs with many methods where implementers stub or raise NotImplementedError for methods they don't need.

```bash
python3 src/zolletta_metaskill/patterns/scan_interface_segregation.py <directory> [--min-methods N] [--skip] [--strict]
```

| Option            | Default | Description                                  |
|-------------------|---------|----------------------------------------------|
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
|--------------------|---------|------------------------------------------|
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
|---------------|---------|------------------------------------------|
| `<directory>` | `src`   | Root directory to scan                   |
| `--skip`      | off     | Skip this check entirely                 |
| `--strict`    | off     | Exit with code 1 if violations are found |

**Checks**: overridden methods with extra required params, fewer params than parent, new exception types, stub overrides (pass/return None when parent has a real body).

## PHP SOLID Validator Scripts

These scanners live in `src/zolletta_metaskill/php_patterns/` and target PHP codebases. They use the `PHPEngine` (tree-sitter-php) to parse `.php` files. Install the optional dependency with `pip install zolletta-metaskill[php]`.

### scan_php_dependency_inversion.py (DIP)

Detects classes that instantiate their dependencies internally (`new ConcreteClass()` in constructors or methods) instead of receiving them via dependency injection. Excludes factories, builders, and PHP built-in types.

```bash
python3 src/zolletta_metaskill/php_patterns/scan_php_dependency_inversion.py <directory> [--skip] [--strict]
```

| Option        | Default | Description                              |
|---------------|---------|------------------------------------------|
| `<directory>` | `src`   | Root directory to scan                   |
| `--skip`      | off     | Skip this check entirely                 |
| `--strict`    | off     | Exit with code 1 if violations are found |

**How it works**: since `ModuleInfo` does not capture `new` expressions, this scanner calls `PHPEngine.parse_raw()` to access the tree-sitter AST directly and walks it for `new_expression` nodes inside class methods.

**Exclusions**: classes whose name contains `Factory` or `Builder` are treated as composition roots where object creation is expected. PHP built-in types (`stdClass`, `DateTime`, `Exception`, etc.) are excluded from dependency detection.

### scan_php_interface_segregation.py (ISP)

Detects fat interfaces — PHP interfaces with many methods where implementers are forced to depend on methods they do not use.

```bash
python3 src/zolletta_metaskill/php_patterns/scan_php_interface_segregation.py <directory> [--min-methods N] [--skip] [--strict]
```

| Option            | Default | Description                              |
|-------------------|---------|------------------------------------------|
| `<directory>`     | `src`   | Root directory to scan                   |
| `--min-methods N` | 7       | Minimum method count to flag as fat      |
| `--skip`          | off     | Skip this check entirely                 |
| `--strict`        | off     | Exit with code 1 if violations are found |

**How it works**: uses `ModuleInfo` directly (no raw AST needed). PHP interfaces are mapped to `ClassInfo` with `is_abstract=True` and no attributes. Interfaces with more than `--min-methods` methods are flagged as fat.

### scan_php_open_closed.py (OCP)

Detects `if/elseif` chains that use `instanceof` to branch on subtypes — an OCP violation. Adding a new subtype requires modifying the ladder instead of simply adding a new implementation.

```bash
python3 src/zolletta_metaskill/php_patterns/scan_php_open_closed.py <directory> [--min-branches N] [--skip] [--strict]
```

| Option             | Default | Description                              |
|--------------------|---------|------------------------------------------|
| `<directory>`      | `src`   | Root directory to scan                   |
| `--min-branches N` | 3       | Minimum instanceof branches to flag      |
| `--skip`           | off     | Skip this check entirely                 |
| `--strict`         | off     | Exit with code 1 if violations are found |

**How it works**: since `ModuleInfo` does not capture `instanceof` expressions, this scanner calls `PHPEngine.parse_raw()` to access the tree-sitter AST directly and counts `instanceof` branches in `if_statement` nodes.

## LanguageEngine Protocol

The `LanguageEngine` protocol is the seam between language-agnostic scanners and language-specific parsers. Scanners depend only on this protocol and the `ModuleInfo` data model — they never import `ast` or tree-sitter directly.

### common/language_engine.py

Defines the `LanguageEngine` protocol (`@runtime_checkable`). Every engine must implement:

| Method / property      | Description                                                                |
|------------------------|----------------------------------------------------------------------------|
| `language`             | Language identifier (e.g. `"python"`, `"php"`)                             |
| `parse_module(path)`   | Parse a source file and return a `ModuleInfo`                              |
| `is_test_file(path)`   | Return `True` if the path is a test file for this language                 |
| `is_source_file(path)` | Return `True` if the path is a source file for this language               |
| `file_extensions()`    | Return the list of extensions handled (e.g. `[".py"]`, `[".php"]`)         |
| `test_file_pattern()`  | Return the glob pattern for test files (e.g. `"test_*.py"`, `"*Test.php"`) |

### common/registry.py

Provides the engine registry — maps language names and file extensions to engines:

| Function                    | Description                                                                                                        |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------|
| `register_engine(engine)`   | Register an engine under its `language` identifier (raises `ValueError` on duplicate)                              |
| `get_engine(language)`      | Return the registered engine for a language (raises `KeyError` if not found)                                       |
| `get_engine_for_file(path)` | Return the engine that handles a file path based on its extension, or `None`                                       |
| `ensure_engine(engine)`     | Register an engine if its language is not already registered (idempotent — safe to call from scanner entry points) |
| `available_languages()`     | Return a sorted list of registered language identifiers                                                            |

### engines/python_engine.py & engines/php_engine.py

Two implementations of the `LanguageEngine` protocol:

- **`PythonEngine`** — wraps Python's `ast` module to parse `.py` files into `ModuleInfo`.
- **`PHPEngine`** — wraps tree-sitter with the tree-sitter-php grammar to parse `.php` files into `ModuleInfo`. The `tree-sitter-php` package is an optional dependency (`pip install zolletta-metaskill[php]`); if not installed, the engine still instantiates but `parse_module()` raises a clear `ImportError`.

### PHPEngine.parse_raw()

```python
def parse_raw(self, path: Path) -> tuple[Tree, bytes]
```

Returns the raw tree-sitter `Tree` and source bytes for a `.php` file. Used by PHP-specific scanners (`scan_php_dependency_inversion.py`, `scan_php_open_closed.py`) that need direct AST access for constructs not captured in `ModuleInfo` (e.g. `new` expressions, `instanceof` chains). The source bytes are needed to extract text from individual nodes via `source[node.start_byte:node.end_byte]`.

## Dead Code Script

### scan_unused_all_exports.py

Finds names listed in `__all__` that are never imported by any other module in the source tree. Complements vulture, which treats `__all__` entries as "used" (public API exports) and therefore never flags them as dead code — even when no module ever imports them.

```bash
python3 src/zolletta_metaskill/python_code_style/scan_unused_all_exports.py <directory> [--strict] [--json] [--skip]
```

| Option        | Default | Description                                  |
|---------------|---------|----------------------------------------------|
| `<directory>` | `src`   | Root source directory to scan                |
| `--strict`    | off     | Exit with code 1 if unused exports are found |
| `--json`      | off     | Output as JSON instead of markdown           |
| `--skip`      | off     | Skip this check entirely                     |

### scan_test_naming.py

Checks test function names against the `test_<unit>_<scenario>_<expected>` convention. Flags functions with fewer than `--min-segments` underscore-separated segments after the `test_` prefix. This is a deterministic replacement for manual review of test function names.

```bash
python3 src/zolletta_metaskill/python_testing_patterns/scan_test_naming.py <directory> [--min-segments N] [--strict] [--json] [--skip]
```

| Option             | Default | Description                              |
|--------------------|---------|------------------------------------------|
| `<directory>`      | `tests` | Root test directory to scan              |
| `--min-segments N` | 3       | Minimum segments after `test_` prefix    |
| `--strict`         | off     | Exit with code 1 if violations are found |
| `--json`           | off     | Output as JSON instead of markdown       |
| `--skip`           | off     | Skip this check entirely                 |

### scan_acronym_casing.py

Checks that acronyms in PascalCase class names stay fully uppercase (e.g. `HTTPClientFactory`, not `HttpClientFactory`). The scanner splits each PascalCase class name into words, checks each word against the configured acronym list, and flags any word that case-insensitively matches an acronym but isn't all-uppercase.

```bash
python3 src/zolletta_metaskill/python_code_style/scan_acronym_casing.py <directory> [--acronyms <list>] [--strict] [--json] [--skip]
```

| Option        | Default                  | Description                                                  |
|---------------|--------------------------|--------------------------------------------------------------|
| `<directory>` | `src`                    | Root source directory to scan                                |
| `--acronyms`  | (from assets + settings) | Comma-separated acronym list (overrides built-in + settings) |
| `--strict`    | off                      | Exit with code 1 if violations are found                     |
| `--json`      | off                      | Output as JSON instead of markdown                           |
| `--skip`      | off                      | Skip this check entirely                                     |

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
|----------------|----------|------------------------------------------------|
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

Run scripts in order: triage (`scan_class_metrics`, `scan_test_god_classes`) → structural (`scan_one_class_per_file`, `scan_tests`, `scan_naming_conventions`) → SOLID (`scan_dependency_inversion`, `scan_interface_segregation`, `scan_open_closed`, `scan_liskov_substitution`) → PHP SOLID (PHP projects) → dead code (`scan_unused_all_exports`) → naming (`scan_test_naming`, `scan_acronym_casing`) → split (`test_splitter`). Apply the "reason to change" test to top candidates.

## Repository Scripts

These are project-management scripts at the repository root, separate from the scanning scripts above.

### `.bump`

Bumps the Zolletta-metaskill version across all files.

```bash
./.bump --to <version>
```

Updates: `pyproject.toml`, `src/zolletta_metaskill/__init__.py`, all `SKILL.md` front-matter version fields, and `setup/assets/settings_template.json` (`setup_version`).

### `install.sh`

Installs the skill into `~/.agents/skills/` and symlinks it into every detected AI agent tool's skills directory.

```bash
./install.sh           # install/refresh
./install.sh --force   # replace real dirs with symlinks
```

See [Install Zolletta-MetaSkill](../../how-to/install.md) for details.
