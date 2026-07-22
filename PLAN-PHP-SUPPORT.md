# Plan: PHP Support & Language-Agnostic Scanners

## Goal

Make the triage scanners, skills, and documentation **language-agnostic by default**, with **language-specific extensions** where a construct has no neutral equivalent. Concretely:

- Introduce a `LanguageEngine` protocol that abstracts AST parsing. Scanners consume `ModuleInfo` (a language-neutral data model) instead of Python `ast` nodes directly.
- Add a `PythonEngine` (wrapping the existing `ast` module) and a `PHPEngine` (using tree-sitter).
- Refactor the language-neutral scanners in `shared/` and `patterns/` to consume `ModuleInfo`.
- Keep language-specific scanners in language packages (`python_code_style/`, `php_patterns/`) for constructs with no neutral model (docstrings, `__all__`, `instanceof`, PHP traits, etc.).
- Extend `setup` with PHP tooling detection (parallel to the existing Python step) and a `php` object in `settings.json`.
- Create `php-code-style` and `php-testing-patterns` skills.
- Implement PHP-specific SOLID scanners.
- Extend the existing Diátaxis `docs/` tree (which already has a PHP section) rather than creating new doc roots.

## Agnostic-first principle

This is the design rule that governs every phase below:

1. **Default is language-neutral.** Scanners in `shared/` and `patterns/` depend only on `LanguageEngine` + `ModuleInfo`. Documentation under `docs/explanation/code/general-principles.md` and `docs/explanation/code/structural-conventions.md` is language-neutral.
2. **Specificity is an exception, not the baseline.** When a construct has no neutral model (Python `__all__`/docstrings/`Protocol`, PHP `instanceof`/traits/`readonly`), the scanner lives in a language package (`python_code_style/`, `php_patterns/`) and may use the engine's native AST directly. Language-specific skills (`python-code-style`, `php-code-style`) and docs (`docs/explanation/code/python/`, `docs/explanation/code/php/`) **narrow** the agnostic baseline — they never restate it.
3. **The seam is the protocol.** Agnostic scanners never import `ast` or tree-sitter; they import `common.models` and call `engine.parse_module()`. Language-specific scanners may reach into the engine for native nodes.
4. **One scanner, many languages.** A neutral scanner (e.g. `scan_one_class_per_file.py`) must work for any registered engine without code changes — the engine is selected internally from the file extension.
5. **Settings mirror the same split.** `settings.json` has a top-level `language` field (neutral) plus optional per-language objects (`python`, `php`) that carry language-specific tooling and rule toggles.

## Testing policy

**Every new Python source file created by this plan must have a corresponding test file.** The test file mirrors the source path under `tests/` and is named `test_<source_stem>.py`.

However, **test creation is deferred** to [`PLAN-TEST-RECOVERY.md`](PLAN-TEST-RECOVERY.md). That plan owns the entire `tests/` tree (it is currently recovering 846 lost tests). Rather than scattering test tasks across two plans, every new test required by this plan is registered in a single dedicated section of `PLAN-TEST-RECOVERY.md` — "Tests required by PLAN-PHP-SUPPORT" — which lists each new test file, its destination, and what it must cover.

Concretely: when a phase of this plan creates `src/zolletta_metaskill/common/models.py`, it does **not** write `tests/common/test_models.py` itself. Instead, the phase adds an entry to the "Tests required by PLAN-PHP-SUPPORT" table in `PLAN-TEST-RECOVERY.md`, and that plan's execution picks it up. The inline "Tests" subsections in the phases below (1.5, 2.4, 3.5, 6.2) are the source of truth for what those deferred tests must cover — they are cross-referenced from the recovery plan.

This keeps a single execution owner for the whole `tests/` tree and avoids two plans writing into `tests/` concurrently.

## Current state

The repository is a meta-skill with a `src/` package, a set of top-level skill directories, and a Diátaxis `docs/` tree.

```
zolletta-metaskill/
├── SKILL.md                         # meta-skill registry + subcommand table
├── README.md                        # "specializations for Python (other languages in progress)"
├── pyproject.toml                   # v1.2.0, hatchling, py312, no tree-sitter deps
├── setup/                           # setup skill
│   ├── SKILL.md                     # detects language (composer.json → PHP already in Step 3)
│   └── assets/settings_template.json
├── review/                          # orchestrator skill (language-specific skills table)
├── external-review/                 # external-LLM review skill
├── patterns/                        # patterns skill (SKILL.md + assets/)
├── documentor/                      # documentor skill
├── python-code-style/               # Python style skill
├── python-testing-patterns/         # Python testing skill
├── docs/                            # Diátaxis docs tree
│   ├── explanation/code/general-principles.md          # language-agnostic SOLID/KISS
│   ├── explanation/code/structural-conventions.md      # language-agnostic
│   ├── explanation/code/false-positive-prevention.md   # language-agnostic
│   ├── explanation/code/python/python-review-patterns.md
│   └── explanation/code/php/php-review-patterns.md     # ALREADY EXISTS (strategy, ISP, traits, manual grep triage)
├── src/zolletta_metaskill/
│   ├── __init__.py                  # __version__ = "1.2.0"
│   ├── documentor/                  # 4 modules (drift_analyzer, link_checker, doc_staleness_scorer, api_doc_validator)
│   ├── patterns/                    # 6 SOLID + class metrics scanners + test_splitter (Python ast)
│   ├── python_code_style/           # 3 scanners (acronyms, unused exports, docstrings)
│   ├── python_testing_patterns/     # 1 scanner (test naming)
│   └── shared/                      # 3 scanners (naming, one-class-per-file, test mirroring)
└── (no tests/, no common/, no engines/, no cli.py, no __version__.py)
```

### Already in place toward PHP / agnosticism

These exist today and must not be recreated — later phases **extend** them:

| Artifact | Location | Status |
| --- | --- | --- |
| PHP language detection | `setup/SKILL.md` Step 3 table | `composer.json` → PHP already mapped |
| `language` field accepts `php` | `docs/reference/settings-schema.md`, `review/SKILL.md` | `php` already listed as a valid value |
| PHP review patterns doc | `docs/explanation/code/php/php-review-patterns.md` | Exists with strategy/ISP/trait patterns + manual grep triage |
| Language-agnostic note in scripts ref | `docs/reference/code/scripts.md` (top banner) | Already states the workflow is language-agnostic; scripts are a Python triage accelerator |
| Orchestrator extension hook | `review/SKILL.md` language-specific table | Already says "When support for other languages is added, extend this table" |
| Root skill languages line | `SKILL.md`, `README.md` | Already "Python / Others (Work in progress)" |

### What is missing

- `src/zolletta_metaskill/common/` (models, protocol, registry)
- `src/zolletta_metaskill/engines/` (PythonEngine, PHPEngine)
- `php` object in `setup/assets/settings_template.json` and its schema doc
- PHP tooling detection step in `setup/SKILL.md` (parallel to Step 6 for Python)
- `php-code-style/` and `php-testing-patterns/` skills
- `src/zolletta_metaskill/php_patterns/` (PHP-specific SOLID scanners)
- `tests/` directory (see `PLAN-TEST-RECOVERY.md`)
- `tree-sitter` / `tree-sitter-php` optional dependencies

### Scanner classification (src/ view)

| Script | Location | Language coupling | Can be language-agnostic? |
| --- | --- | --- | --- |
| scan_class_metrics.py | patterns/ | ast (classes, methods, attrs) | Yes — via engine |
| scan_dependency_inversion.py | patterns/ | ast (Call, Name, Attribute) | Yes — via engine |
| scan_interface_segregation.py | patterns/ | ast (Protocol, ABC) | Partial — Protocol is Python-specific |
| scan_liskov_substitution.py | patterns/ | ast (ClassDef, method sigs) | Yes — via engine |
| scan_open_closed.py | patterns/ | ast (If, isinstance, match) | Partial — isinstance is Python-specific |
| scan_test_god_classes.py | patterns/ | ast (ClassDef in test files) | Yes — via engine |
| test_splitter.py | patterns/ | ast (rewrites test files) | Python-only (code generation) |
| scan_acronym_casing.py | python_code_style/ | ast (comments, docstrings) | Python-only |
| scan_unused_all_exports.py | python_code_style/ | ast (**all**, imports) | Python-only |
| streamline_docstrings.py | python_code_style/ | ast (docstrings) | Python-only |
| scan_test_naming.py | python_testing_patterns/ | ast (test file naming) | Yes — via engine (file-level only) |
| scan_naming_conventions.py | shared/ | ast (class names vs filenames) | Yes — via engine |
| scan_one_class_per_file.py | shared/ | ast (ClassDef count) | Yes — via engine |
| scan_tests.py | shared/ | ast (test dir mirroring) | Yes — file-level only |

**7 scanners can be made fully language-agnostic** via an engine abstraction. **6 scanners are Python-specific** (docstrings, `__all__`, isinstance, Protocol, ABC, code rewriting) — they stay in language packages per the agnostic-first principle.

---

## Phase 1 — Common infrastructure (language-neutral models + engine protocol)

### 1.1 Create `src/zolletta_metaskill/common/`

```
src/zolletta_metaskill/common/
├── __init__.py
├── models.py                    # Language-neutral data models
├── registry.py                  # Engine registry (language -> engine instance)
└── language_engine.py           # Protocol definition
```

### 1.2 `common/models.py` — `ModuleInfo` and related dataclasses

```python
@dataclass(frozen=True)
class ClassInfo:
    name: str
    lineno: int
    end_lineno: int
    methods: list[MethodInfo]
    bases: list[str]              # base class names (e.g. ["Protocol"], ["BaseRepository"])
    attributes: list[str]         # instance attribute names (e.g. self.x -> "x")
    is_abstract: bool             # ABC / abstract class / interface
    is_test_class: bool           # name starts with "Test" (language-specific rule via engine)

@dataclass(frozen=True)
class MethodInfo:
    name: str
    lineno: int
    end_lineno: int
    params: list[str]             # parameter names (excluding self/this)
    is_public: bool               # language-specific visibility rule
    is_static: bool
    return_type: str | None       # type annotation string, if any
    raises: list[str]             # exception/throw types

@dataclass(frozen=True)
class ImportInfo:
    module: str                   # e.g. "os.path" or "Namespace\Sub\Class"
    names: list[str]              # imported names (from X import a, b)
    lineno: int
    is_relative: bool

@dataclass(frozen=True)
class ModuleInfo:
    path: Path
    language: str                 # "python", "php", etc.
    classes: list[ClassInfo]
    imports: list[ImportInfo]
    functions: list[MethodInfo]   # module-level functions
    all_exports: list[str] | None # __all__ for Python, None for others
    docstring: str | None
    has_syntax_error: bool
```

### 1.3 `common/language_engine.py` — Protocol

```python
class LanguageEngine(Protocol):
    @property
    def language(self) -> str: ...

    def parse_module(self, path: Path) -> ModuleInfo: ...
    def is_test_file(self, path: Path) -> bool: ...
    def is_source_file(self, path: Path) -> bool: ...
    def file_extensions(self) -> list[str]: ...   # [".py"], [".php"]
    def test_file_pattern(self) -> str: ...        # "test_*.py", "*Test.php"
```

### 1.4 `common/registry.py` — Engine registry

```python
_ENGINES: dict[str, type[LanguageEngine]] = {}

def register_engine(language: str, engine_class: type[LanguageEngine]) -> None: ...
def get_engine(language: str) -> LanguageEngine: ...
def get_engine_for_file(path: Path) -> LanguageEngine | None: ...
def available_languages() -> list[str]: ...
```

### 1.5 Tests for `common/`

- `tests/common/test_models.py` — dataclass construction, immutability
- `tests/common/test_registry.py` — register, get, unknown language, file extension matching

---

## Phase 2 — Engines

### 2.1 Create `src/zolletta_metaskill/engines/`

```
src/zolletta_metaskill/engines/
├── __init__.py
├── python_engine.py             # wraps ast module -> ModuleInfo
└── php_engine.py                # wraps tree-sitter -> ModuleInfo
```

### 2.2 `engines/python_engine.py`

- Implements `LanguageEngine`
- `parse_module()` reads the file, calls `ast.parse()`, walks the tree, and builds `ModuleInfo` with `ClassInfo`, `MethodInfo`, `ImportInfo`
- Maps Python-specific constructs:
  - `ast.ClassDef` → `ClassInfo` (bases from `node.bases`, attrs from `self.x` in method bodies)
  - `ast.FunctionDef` / `ast.AsyncFunctionDef` → `MethodInfo` (params from `args.args`, `self` excluded)
  - `ast.Import` / `ast.ImportFrom` → `ImportInfo`
  - `__all__` → `all_exports`
  - `ast.Raise` → `raises` (exception type name)
  - `ABC` in bases → `is_abstract=True`
  - `Protocol` in bases → `is_abstract=True`
  - `@staticmethod` → `is_static=True`
  - `_` prefix → `is_public=False`
- `is_test_file()`: filename starts with `test_` or class starts with `Test`
- `file_extensions()`: `[".py"]`

### 2.3 `engines/php_engine.py`

- Implements `LanguageEngine`
- Uses `tree-sitter-php` (add `tree-sitter` and `tree-sitter-php` to dependencies)
- `parse_module()` reads the file, parses with tree-sitter, queries for:
  - `class_declaration` → `ClassInfo` (name, methods, extends, implements)
  - `method_declaration` / `function_definition` → `MethodInfo` (params, visibility)
  - `use_declaration` → `ImportInfo` (namespace imports)
  - `interface_declaration` → `ClassInfo` with `is_abstract=True`
  - `trait_declaration` → `ClassInfo` (flagged as trait)
  - `abstract_modifier` → `is_abstract=True`
  - `static_modifier` → `is_static=True`
  - `public`/`private`/`protected` → `is_public`
  - `throw_statement` → `raises`
- `is_test_file()`: filename ends with `Test.php` or class ends with `Test`
- `file_extensions()`: `[".php"]`
- Composer autoload PSR-4 mapping for namespace → directory resolution

### 2.4 Tests for engines

- `tests/engines/test_python_engine.py` — parse various Python constructs, verify `ModuleInfo` fields
- `tests/engines/test_php_engine.py` — parse PHP fixtures, verify `ModuleInfo` fields
- Fixtures: `tests/fixtures/php/src/` with sample classes, interfaces, traits

---

## Phase 3 — Refactor language-agnostic scanners to consume `ModuleInfo`

### 3.1 Scanners to refactor (7)

These scanners currently use `ast` directly. Refactor them to accept `ModuleInfo` instead. They stay in their current packages (`shared/`, `patterns/`) because their concern is language-neutral — only their parsing dependency changes.

| Scanner                     | What it needs from ModuleInfo                             |
| --------------------------- | --------------------------------------------------------- |
| scan_class_metrics.py       | `classes` (name, lineno, end_lineno, methods, attributes) |
| scan_test_god_classes.py    | `classes` in test files (name, methods, lineno)           |
| scan_naming_conventions.py  | `classes` (name vs filename), `is_test_file()`            |
| scan_one_class_per_file.py  | `classes` (count per file)                                |
| scan_tests.py               | `is_test_file()`, `is_source_file()`, file extension      |
| scan_test_naming.py         | `is_test_file()`, filename vs source mirroring            |
| scan_liskov_substitution.py | `classes` (methods, params, bases, raises)                |

### 3.2 Refactoring pattern

Each scanner changes from:

```python
# Before
def scan_file(path: Path) -> list[dict]:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            ...
```

To:

```python
# After
def scan_module(module: ModuleInfo) -> list[Finding]:
    for cls in module.classes:
        ...
```

The `main()` function resolves the engine from the registry and calls `engine.parse_module()` before passing `ModuleInfo` to `scan_module()`. Engine selection is internal (by file extension) — the CLI interface stays `python3 src/.../scan_x.py <dir>`.

### 3.3 Scanners that stay language-specific (6)

Per the agnostic-first principle, these stay in their language packages and keep using the native AST directly. They can be ported later if a neutral model emerges.

| Scanner | Package | Why it stays language-specific |
| --- | --- | --- |
| scan_dependency_inversion.py | patterns/ (Python) | Detects `self._dep = Dep()` — Python attribute assignment |
| scan_interface_segregation.py | patterns/ (Python) | Detects `Protocol` and `ABC` — Python-specific abstractions |
| scan_open_closed.py | patterns/ (Python) | Detects `isinstance()`, `type()`, `match/case` — Python patterns |
| test_splitter.py | patterns/ (Python) | Rewrites Python test files (code generation) |
| scan_acronym_casing.py | python_code_style/ | Reads Python comments and docstrings |
| scan_unused_all_exports.py | python_code_style/ | Reads `__all__` and import tracking — Python-specific |
| streamline_docstrings.py | python_code_style/ | Rewrites Python docstrings |

> Note: `scan_dependency_inversion.py`, `scan_interface_segregation.py`, and `scan_open_closed.py` currently live in `patterns/` but are Python-specific. Consider moving them to `python_code_style/` (or a new `python_patterns/`) so `patterns/` becomes truly neutral. This is a naming refactor — decide during Phase 3.

### 3.4 New `Finding` dataclass

Add to `common/models.py`:

```python
@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    category: str          # "naming", "structure", "god_class", etc.
    severity: str          # "high", "medium", "low"
    description: str
    fix_type: str          # "auto", "manual", "skip"
```

Scanners return `list[Finding]` instead of `list[dict]`.

### 3.5 Tests

- Update existing tests (once recovered) to pass `ModuleInfo` fixtures instead of raw files
- Add `tests/fixtures/php/` with PHP equivalents of the Python fixtures

---

## Phase 4 — PHP setup (composer.json → settings.json)

`setup/SKILL.md` Step 3 already maps `composer.json` → PHP. This phase adds the **PHP tooling detection**, **configuration extraction**, and the **`php` settings object**, mirroring the existing Python path (Step 6 + Step 6.5 + Step 8 + Step 9 + Step 10 + setup guard + schema doc + tool messages).

### Python → PHP path mapping

The PHP configuration path is a structural mirror of the Python one. Each Python artifact has a PHP counterpart:

| Concern | Python | PHP |
| --- | --- | --- |
| Manifest file | `pyproject.toml` (TOML) | `composer.json` (JSON) |
| Manifest mtime field | `python.pyproject_mtime` | `php.composer_mtime` |
| Dependency section | `[project] dependencies` | `composer.json` `require` |
| Dev dependency section | `[project.optional-dependencies]` | `composer.json` `require-dev` |
| Autoload / package mapping | `[tool.hatch.build.targets.wheel] packages` | `composer.json` `autoload.psr-4` / `autoload-dev.psr-4` |
| Language version | `requires-python` in `pyproject.toml` | `composer.json` `require.php` (e.g. `">=8.2"`) |
| Tool config: linter | `[tool.ruff]` in `pyproject.toml` | `.php-cs-fixer.php` or `.php-cs-fixer.dist.php` (PHP code) / `.phpcs.xml` or `phpcs.xml.dist` (XML) |
| Tool config: test runner | `[tool.pytest.ini_options]` in `pyproject.toml` | `phpunit.xml` or `phpunit.dist.xml` (XML) |
| Tool config: static analysis | `[tool.mypy]` / `[tool.ty]` in `pyproject.toml` | `phpstan.neon` or `phpstan.dist.neon` (NEON) / `psalm.xml` or `psalm.dist.xml` (XML) |
| Tool config: dead code | `[tool.vulture]` in `pyproject.toml` | _(no direct equivalent — skip)_ |
| Tool binary location | global or `uv run` | `vendor/bin/<tool>` (Composer) |
| "not installed" messages | `docs/reference/tool-messages.md` | same file, new PHP sections |
| "unconfigured" warnings | `docs/reference/tool-messages.md` | same file, new PHP sections |
| Settings schema doc | `docs/reference/settings-schema.md` → `python` section | same file, new `php` section |
| Setup guard staleness | compare `pyproject.toml` mtime vs `python.pyproject_mtime` | compare `composer.json` mtime vs `php.composer_mtime` |

### 4.1 Add Step 7 — Detect PHP tooling (PHP projects only)

Add a new step to `setup/SKILL.md` parallel to Step 6, run only when the detected language from Step 3 is **PHP**. If the language is not PHP, skip this step entirely and set `php: null`.

For each tool, check in this order:

1. **Check `composer.json` `require-dev`** — if the tool's package is listed (e.g. `"phpunit/phpunit"`), mark it as available (the project uses it).
2. **Check for a config file** — if the tool's config file exists in the project root (e.g. `phpunit.xml`, `.php-cs-fixer.php`), mark it as available even if not in `require-dev` (the project intends to use it).
3. **If not found in `composer.json` or config file**, try calling the command — inside the container if `container_name` is set (`docker compose exec <container_name> vendor/bin/<tool> --version`), otherwise on the host (`vendor/bin/<tool> --version`). If the command succeeds, mark it as available.

The tools to detect:

| Tool | `composer.json` require-dev package | Config file(s) | Command |
| --- | --- | --- | --- |
| `phpunit` | `phpunit/phpunit` | `phpunit.xml`, `phpunit.dist.xml` | `vendor/bin/phpunit --version` |
| `phpstan` | `phpstan/phpstan` | `phpstan.neon`, `phpstan.dist.neon` | `vendor/bin/phpstan --version` |
| `psalm` | `vimeo/psalm` | `psalm.xml`, `psalm.dist.xml` | `vendor/bin/psalm --version` |
| `php_cs_fixer` | `friendsofphp/php-cs-fixer` | `.php-cs-fixer.php`, `.php-cs-fixer.dist.php` | `vendor/bin/php-cs-fixer --version` |
| `phpcs` | `squizlabs/php_codesniffer` | `.phpcs.xml`, `phpcs.xml.dist`, `.phpcs.xml.dist` | `vendor/bin/phpcs --version` |

Store each tool as an object in `php.tools` with an `available` boolean (see Step 8). The per-tool configuration fields are populated in Step 7.5.

> **Do NOT install any tool.** If a tool is not present, set `available: false` and print the corresponding "not installed" message in Step 9.

### 4.2 Add Step 7.5 — Extract PHP configuration from composer.json and tool config files

Parallel to Step 6.5 for Python. If the detected language is not PHP, skip this step entirely and leave `php: null`.

If the language is **PHP**, read `composer.json` and each tool's config file, and extract the effective configuration. Record `composer.json`'s modification time so the setup guard can detect staleness. All values are written into the `php.tools.<tool>` objects (alongside the `available` flag from Step 7) and the `php.autoload` / `php.php_version` fields.

1. **Record `composer_mtime`** — use `os.path.getmtime("composer.json")` (or equivalent). Store as a float in `php.composer_mtime`.

2. **Extract `php_version`** — read `composer.json` `require.php` (e.g. `">=8.2"`, `"^8.1"`, `"8.3"`). Parse the version constraint and store the minimum version as a string in `php.php_version` (e.g. `"8.2"`, `"8.1"`). If `require.php` is absent, store `null` and print a warning (the PHP version is unknown — review skills cannot assume a specific version).

3. **Extract autoload mapping** — read `composer.json` `autoload.psr-4` and `autoload-dev.psr-4`. Store in `php.autoload`:

   ```json
   "autoload": {
     "psr-4": { "App\\": "src/" },
     "psr-4-dev": { "Tests\\": "tests/" }
   }
   ```

   If `autoload` or `autoload-dev` is absent, store an empty object for the missing key. The `php-code-style` and `php-testing-patterns` skills use this to resolve namespaces to directories (equivalent to how Python skills use `[tool.hatch.build.targets.wheel] packages`).

4. **For each tool that is `available: true` in `php.tools`** (from Step 7), extract its configuration into the same `php.tools.<tool>` object:

   | Tool | If config file exists | If config file is absent |
   | --- | --- | --- |
   | `phpunit` | Parse `phpunit.xml` (XML): extract `bootstrap` → `bootstrap`, `<coverage>` config → `coverage_config`, `<testsuites>` dirs → `testpaths`. Store in `php.tools.phpunit`. | Store phpunit's built-in defaults: `bootstrap: null`, `testpaths: ["tests"]`, `coverage_config: null`. Print the phpunit "unconfigured" warning. |
   | `phpstan` | Parse `phpstan.neon` (NEON): extract `level` → `level` (0–9), `paths` → `paths`, `memory_limit` → `memory_limit`. Store in `php.tools.phpstan`. | Store phpstan's built-in defaults: `level: 0`, `paths: ["src"]`, `memory_limit: null`. Print the phpstan "unconfigured" warning. |
   | `psalm` | Parse `psalm.xml` (XML): extract `errorLevel` → `error_level` (1–8), `projectFiles` dirs → `paths`. Store in `php.tools.psalm`. | Store psalm's built-in defaults: `error_level: 1`, `paths: ["src"]`. Print the psalm "unconfigured" warning. |
   | `php_cs_fixer` | Check if `.php-cs-fixer.php` or `.php-cs-fixer.dist.php` exists. Store `config_file: true`. **Do not parse the PHP file** — it is executable PHP code, not a declarative format. The `php-code-style` skill reads it at review time if needed. | Store `config_file: false`. Print the php-cs-fixer "unconfigured" warning (states the built-in default ruleset: `@PSR-12`). |
   | `phpcs` | Parse `.phpcs.xml` or `phpcs.xml.dist` (XML): extract `standard` → `standard` (e.g. `"PSR12"`, `"Custom"`). Store in `php.tools.phpcs`. | Store phpcs's built-in defaults: `standard: "PSR12"`. Print the phpcs "unconfigured" warning. |

   > **NEON parsing**: `phpstan.neon` uses the NEON format (a YAML-like syntax). If a NEON parser is not available as a Python dependency, parse it as a simplified YAML subset (key: value, nested via indentation, arrays with `-`). PHPStan config files are typically simple enough for this. If parsing fails, store `level: null` and print a warning that the config could not be read.

5. **Static analysis resolution** — parallel to Python's type checker resolution. There is no `static_analyser` field in `settings.json`. Review skills run all available static analysers:
   - If `php.tools.phpstan.available` is `true` → run phpstan
   - If `php.tools.psalm.available` is `true` → run psalm
   - If neither is available → static analysis is skipped

   When both are available, both run. Findings from each are listed separately. This is documented in `php-code-style/SKILL.md` (to be created in Phase 5).

6. **Never modify `composer.json` or any tool config file.** Setup only reads them. The "unconfigured" warnings are informational — the user decides whether to add a config file.

7. **Write `php.code_style`** — copy the default rule toggles (see Step 8 for the shape). If `settings.json` already exists (re-run of setup), **preserve existing user-customized values** and only add keys that are new (merge, don't overwrite). Same merge behavior as `python.code_style`.

8. **Write `php.testing`** — copy the default rule toggles. Same merge behavior.

### 4.3 Update Step 8 — Write settings.json

Add `php` to the settings table and document its shape. The `php` subobject has this shape (PHP only; `null` otherwise):

```json
{
  "tools": {
    "phpunit": {
      "available": true,
      "bootstrap": "vendor/autoload.php",
      "testpaths": ["tests"],
      "coverage_config": true
    },
    "phpstan": { "available": true, "level": 6, "paths": ["src"], "memory_limit": "256M" },
    "psalm": { "available": false, "error_level": 1, "paths": ["src"] },
    "php_cs_fixer": { "available": true, "config_file": true },
    "phpcs": { "available": false, "standard": "PSR12" }
  },
  "code_style": {
    "check_naming_conventions": true,
    "check_one_class_per_file": true,
    "check_filename_matches_class": true
  },
  "testing": {
    "coverage_gap_threshold": 50,
    "coverage_well_covered_threshold": 80,
    "check_test_naming": true
  },
  "autoload": {
    "psr-4": { "App\\": "src/" },
    "psr-4-dev": { "Tests\\": "tests/" }
  },
  "php_version": "8.2",
  "composer_mtime": 1718700000.0
}
```

Add `php` to the Step 8 field table:

| Field | Source                                                             |
| ----- | ------------------------------------------------------------------ |
| `php` | Object from Steps 7 + 7.5 (PHP only; `null` otherwise) — see above |

### 4.4 Update Step 9 — Print "not installed" and "unconfigured" messages

Extend Step 9 to cover PHP tools, parallel to the Python coverage:

- For PHP projects, each tool in `php.tools` with `available: false` → corresponding "not installed" message
- For PHP projects, each tool in `php.tools` with `available: true` but unconfigured (no config file) → corresponding "unconfigured" warning

Add the following messages to `docs/reference/tool-messages.md`:

**"not installed" messages** (one per tool):

- `phpunit` — test runner, equivalent to pytest
- `phpstan` — static analysis, equivalent to mypy/ty
- `psalm` — static analysis, alternative to phpstan
- `php_cs_fixer` — code style fixer, equivalent to ruff --fix
- `phpcs` — code style sniffer, equivalent to ruff check

**"unconfigured" warnings** (one per tool with a config file):

- `phpunit` (unconfigured) — states defaults: `bootstrap: null`, `testpaths: ["tests"]`, no coverage config
- `phpstan` (unconfigured) — states defaults: `level: 0`, `paths: ["src"]`
- `psalm` (unconfigured) — states defaults: `error_level: 1`, `paths: ["src"]`
- `php_cs_fixer` (unconfigured) — states defaults: `@PSR-12` ruleset, `config_file: false`
- `phpcs` (unconfigured) — states defaults: `standard: "PSR12"`

Each message follows the same structure as the Python ones: explains why zolletta-metaskill benefits from the tool, states the effective defaults, and links to the tool's documentation.

### 4.5 Update Step 10 — Summary

Add PHP lines to the summary, parallel to the Python ones:

```text
  PHP tooling:                     (PHP only)
    phpunit:                       <yes/no>
    phpstan:                       <yes/no>
    psalm:                         <yes/no>
    php-cs-fixer:                  <yes/no>
    phpcs:                         <yes/no>
  PHP config:                      (PHP only)
    php version:                   <value>
    phpstan level:                 <value>
    phpcs standard:                <value>
```

### 4.6 Update `setup/assets/settings_template.json`

Add `"php": null` alongside the existing `"python": null`.

### 4.7 Update the setup guard (root `SKILL.md`)

The current staleness check is Python-only (Step 4 of the setup guard). Add a parallel PHP branch: if `settings.json` exists and `php` is not `null`, compare `composer.json`'s current modification time against `php.composer_mtime`. If they differ, re-run **only** Step 7.5 (composer.json + tool config extraction) and patch the `php.tools.*` configuration fields + `php.autoload` + `php.php_version` + `php.composer_mtime` in `settings.json`. Do not re-run full setup (language detection, Docker probe, tokensave probe). If `composer.json` does not exist or `php` is `null`, skip this check.

### 4.8 Create `setup/assets/settings.schema.json`

A machine-readable JSON Schema (draft 2020-12) that formally validates `settings.json`. It is the single source of truth for the shape of the file; the prose doc in `docs/reference/settings-schema.md` is the human-readable counterpart and must stay in sync.

The schema is **already created** at `setup/assets/settings.schema.json` alongside the existing `settings_template.json`. It covers:

- All 11 top-level fields (including `php`, added by this plan)
- `python` object: `tools` (uv, ruff, pytest, ty, vulture, mypy — each with its config fields), `code_style` (9 toggles), `testing` (3 fields), `pyproject_mtime`
- `php` object: `tools` (phpunit, phpstan, psalm, php_cs_fixer, phpcs — each with its config fields), `code_style` (**12 toggles — see fix below**), `testing` (3 fields), `autoload` (psr-4 + psr-4-dev), `php_version`, `composer_mtime`

> **`php.code_style` toggle fix (Phase 10.2 of PLAN-MASTER.md)**: The schema currently has 3 toggles (`check_naming_conventions`, `check_one_class_per_file`, `check_filename_matches_class`) that correspond to always-on rules from PLAN-PHP-CODE-STYLE — they should not be configurable. These must be **removed** and replaced with the 12 configurable toggles defined in PLAN-PHP-CODE-STYLE Phase 3.1:
>
> `check_union_types`, `check_intersection_types`, `check_enum_methods`, `check_first_class_callables`, `check_readonly_classes`, `check_typed_constants`, `check_override_attribute`, `check_property_hooks`, `check_asymmetric_visibility`, `check_pipe_operator`, `check_array_functions`, `check_string_functions`
>
> All 12 are `boolean` with `default: true`. This fix is executed in Phase 10.2 of PLAN-MASTER.md.

- `documentation` object: `language`, `dir`
- `additionalProperties: false` on every object (rejects unknown fields)
- `oneOf: [null, object]` for `python` and `php` (non-applicable languages get `null`)
- Enums for `language` (includes `""` for the template placeholder)

Validation passes for: the template (with `php: null`), a full Python `settings.json`, a full PHP `settings.json`. It correctly rejects missing required fields and unknown top-level fields.

**Usage**: `setup` should validate the `settings.json` it writes against this schema before finishing. Review subcommands can optionally validate on read. IDEs that support JSON Schema associations can map `.zolletta-metaskill/settings.json` → `setup/assets/settings.schema.json` for autocompletion and hover docs.

> **Sync rule**: when a field is added, removed, or renamed in `settings.json`, update **both** `settings.schema.json` and `docs/reference/settings-schema.md` in the same change. The schema is the source of truth for the shape; the prose doc is the source of truth for the semantics.

### 4.9 Update `docs/reference/settings-schema.md`

Add a `php` section parallel to the existing `python` section, documenting:

- **`php.tools`** — tool availability and configuration (table with one row per tool, same structure as `python.tools`)
- **`php.code_style`** — configurable rule toggles (table with key, type, default, area, rule — same structure as `python.code_style`)
- **`php.testing`** — configurable rule toggles (table — same structure as `python.testing`)
- **`php.autoload`** — PSR-4 namespace → directory mapping (source + dev)
- **`php.php_version`** — minimum PHP version extracted from `composer.json` `require.php`
- **`php.composer_mtime`** — staleness detection (same explanation as `python.pyproject_mtime`)
- **Static analysis resolution** note (parallel to the type checker resolution note: no `static_analyser` field, run all available, skip if none)
- **Setup guard staleness check** — PHP branch (parallel to the Python one)
- **JSON Schema** cross-reference: link to `setup/assets/settings.schema.json` at the top of the page, noting it as the machine-readable source of truth for the shape

---

## Phase 5 — PHP skills

### 5.1 Create `php-code-style/` skill

> **Superseded by [PLAN-PHP-CODE-STYLE.md](PLAN-PHP-CODE-STYLE.md)** — see that plan for the full 33-rule set (Type System, Modern PHP Features, PSR, Error Handling, Performance, Security), the report template, and version-gated configurable rules.

### 5.2 Create `php-testing-patterns/` skill

- PSR-12 compliance
- Naming conventions (PascalCase classes, camelCase methods, snake_case for test methods)
- One class per file (PSR-4)
- Docblock standards (PHPDoc)
- Type declarations (return types, param types, union types, nullable)
- `readonly` properties
- `enum` usage
- Avoid `else` (early returns)
- No `@author` tags

### 5.2 Create `php-testing-patterns/` skill

```
php-testing-patterns/
├── SKILL.md
└── assets/
    └── phpunit-coverage-template.xml
```

`SKILL.md` covers:

- PHPUnit test naming (`*Test.php`, methods start with `test_`)
- Test directory mirroring (`tests/` mirrors `src/` per PSR-4)
- One test class per SUT
- Coverage gap detection
- Mocking with Mockery or PHPUnit mocks
- Data providers
- Test doubles (stubs, mocks, spies)
- Avoid testing framework internals

---

## Phase 6 — SOLID scanners for PHP

### 6.1 PHP-specific SOLID scanners

Create `src/zolletta_metaskill/php_patterns/` (language-specific package, per the agnostic-first principle):

```
src/zolletta_metaskill/php_patterns/
├── __init__.py
├── scan_php_dependency_inversion.py   # detects `new Dep()` in constructors
├── scan_php_interface_segregation.py  # detects fat interfaces (many methods, partial implementers)
└── scan_php_open_closed.py            # detects if/elseif type ladders with instanceof
```

These use `PHPEngine` to parse PHP files and detect PHP-specific OCP/DIP/ISP violations:

- `instanceof` chains (OCP violation)
- `new` in constructors (DIP violation)
- Interface with many methods where implementers only use a subset (ISP violation)

### 6.2 Tests

- `tests/php_patterns/test_scan_php_dependency_inversion.py`
- `tests/php_patterns/test_scan_php_interface_segregation.py`
- `tests/php_patterns/test_scan_php_open_closed.py`
- Fixtures: `tests/fixtures/php/src/` with violation examples

---

## Phase 7 — Documentation updates (extend existing docs)

All targets in this phase already exist — extend, do not recreate.

### 7.1 Update `docs/reference/code/scripts.md`

The top banner already declares the workflow language-agnostic. Add:

- PHP scanners to the reference table
- A `LanguageEngine` protocol section (how engines are selected, how to add one)
- Usage examples for PHP scanning

### 7.2 Expand `docs/explanation/code/php/php-review-patterns.md`

This file already exists with strategy/ISP/trait patterns and manual grep triage. Expand it with:

- SOLID violation examples detected by the new PHP scanners (Phase 6)
- Tree-sitter-based scanner references (cross-link to `docs/reference/code/scripts.md`)

### 7.3 Update `README.md`

- Change "specializations for Python (other languages in progress)" to list PHP as supported
- Add `tree-sitter-php` to dependencies mention

### 7.4 Update root `SKILL.md`

- Add `php-code-style` and `php-testing-patterns` to the subcommand table
- Update the "Supported languages" line (currently "Python / Others (Work in progress)")

### 7.5 Update `review/SKILL.md`

Extend the language-specific skills table (which already has the "extend this table" note) with the PHP rows:

| Language | Skill | Scope |
| --- | --- | --- |
| PHP | `php-code-style` | PSR-12, naming, one class per file, PHPDoc, type declarations |
| PHP | `php-testing-patterns` | PHPUnit naming, mirroring, coverage gaps, mocking, data providers |

### 7.6 Update `CHANGELOG.md`

- `[1.3.0]` entry for PHP support

---

## Phase 8 — Dependencies and CI

### 8.1 `pyproject.toml`

Add optional dependencies (keeps the base package lightweight per the risk note):

```toml
[project.optional-dependencies]
php = ["tree-sitter>=0.21", "tree-sitter-php>=0.22"]
```

### 8.2 GitHub workflows

- Add a `php` job to `tests.yml` that installs `tree-sitter-php` and runs PHP scanner tests
- Add PHP fixtures to coverage

### 8.3 `codecov.yml`

- No changes needed (coverage already covers `src/`)

---

## Execution order

1. **Phase 1** — common infrastructure (models, protocol, registry) + tests
2. **Phase 2.2** — PythonEngine (refactor existing ast logic) + tests
3. **Phase 3** — Refactor 7 language-agnostic scanners + tests
4. **Phase 4** — PHP setup (Step 7 tooling detection, Step 7.5 config extraction, Step 8 `php` object, Step 9 messages, Step 10 summary, `settings.schema.json`, setup guard staleness, schema doc, tool-messages doc)
5. **Phase 5** — php-code-style and php-testing-patterns skills
6. **Phase 2.3** — PHPEngine (tree-sitter) + tests
7. **Phase 6** — PHP SOLID scanners + tests
8. **Phase 7** — Documentation updates (extend existing docs)
9. **Phase 8** — Dependencies, CI, version bump

## Risks

- **tree-sitter-php** adds a native dependency. It is optional (`pip install zolletta-metaskill[php]`) so the base package stays lightweight. `PHPEngine` must degrade gracefully (clear error) when the extra is not installed.
- **PHPEngine complexity**: tree-sitter queries for PHP are more verbose than Python ast walks. Budget extra time.
- **Scanner refactoring**: changing the signature of 7 scanners will break any existing tests. Tests must be recovered or rewritten first (see `PLAN-TEST-RECOVERY.md`).
- **Backward compatibility**: scanners currently called as `python3 src/.../scan_x.py <dir>`. The CLI interface must remain the same — the engine selection happens internally based on file extensions.
- **Naming of Python-specific scanners in `patterns/`**: `scan_dependency_inversion.py`, `scan_interface_segregation.py`, and `scan_open_closed.py` are Python-specific but live in a package meant to be neutral. Decide whether to relocate them before or after Phase 3 to avoid churn.
- **NEON parsing**: `phpstan.neon` uses the NEON format (not JSON, not YAML). A Python NEON parser may not be available. The plan proposes parsing it as a simplified YAML subset, which works for typical PHPStan configs but may fail on edge cases (anchors, includes). If parsing fails, store `level: null` and warn — the review skill will read the file directly at review time.
- **php-cs-fixer config is PHP code**: `.php-cs-fixer.php` is executable PHP, not a declarative format. Setup cannot parse it to extract the ruleset. It only records `config_file: true/false`. The `php-code-style` skill reads the file at review time if it needs to know which rules are enabled.
