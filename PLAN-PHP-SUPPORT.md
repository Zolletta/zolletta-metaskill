# Plan: PHP Support & Language-Agnostic Scanners

## Goal

Make all triage scanners language-agnostic by introducing a `LanguageEngine` protocol that abstracts AST parsing. Each scanner consumes `ModuleInfo` (a language-neutral data model) instead of Python `ast` nodes directly. Add a `PythonEngine` (wrapping the existing `ast` module) and a `PhpEngine` (using tree-sitter). Extend `setup` to read `composer.json` and populate a `php` object in `settings.json`. Create `php-code-style` and `php-testing-patterns` skills. Implement SOLID scanners for PHP.

## Current state

```
src/zolletta_metaskill/
├── __init__.py                     # __version__ = "1.2.0"
├── documentor/                     # 4 modules (drift_analyzer, link_checker, etc.)
├── patterns/                       # 6 SOLID + class metrics scanners (Python ast)
├── python_code_style/              # 3 scanners (acronyms, unused exports, docstrings)
├── python_testing_patterns/        # 1 scanner (test naming)
└── shared/                         # 3 scanners (naming, one-class-per-file, test mirroring)
```

All 13 scanner scripts use Python's `ast` module directly. No `common/`, no `engines/`, no `cli.py`, no `__version__.py` (version is in `__init__.py`). No `tests/` directory exists.

### Scanner classification

| Script                        | Location                 | Language coupling              | Can be language-agnostic?               |
| ----------------------------- | ------------------------ | ------------------------------ | --------------------------------------- |
| scan_class_metrics.py         | patterns/                | ast (classes, methods, attrs)  | Yes — via engine                        |
| scan_dependency_inversion.py  | patterns/                | ast (Call, Name, Attribute)    | Yes — via engine                        |
| scan_interface_segregation.py | patterns/                | ast (Protocol, ABC)            | Partial — Protocol is Python-specific   |
| scan_liskov_substitution.py   | patterns/                | ast (ClassDef, method sigs)    | Yes — via engine                        |
| scan_open_closed.py           | patterns/                | ast (If, isinstance, match)    | Partial — isinstance is Python-specific |
| scan_test_god_classes.py      | patterns/                | ast (ClassDef in test files)   | Yes — via engine                        |
| test_splitter.py              | patterns/                | ast (rewrites test files)      | Python-only (code generation)           |
| scan_acronym_casing.py        | python_code_style/       | ast (comments, docstrings)     | Python-only                             |
| scan_unused_all_exports.py    | python_code_style/       | ast (**all**, imports)         | Python-only                             |
| streamline_docstrings.py      | python_code_style/       | ast (docstrings)               | Python-only                             |
| scan_test_naming.py           | python_testing_patterns/ | ast (test file naming)         | Yes — via engine (file-level only)      |
| scan_naming_conventions.py    | shared/                  | ast (class names vs filenames) | Yes — via engine                        |
| scan_one_class_per_file.py    | shared/                  | ast (ClassDef count)           | Yes — via engine                        |
| scan_tests.py                 | shared/                  | ast (test dir mirroring)       | Yes — file-level only                   |

**7 scanners can be made fully language-agnostic** via an engine abstraction. **6 scanners are Python-specific** (docstrings, `__all__`, isinstance, Protocol, ABC, code rewriting).

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

These scanners currently use `ast` directly. Refactor them to accept `ModuleInfo` instead:

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

The `main()` function resolves the engine from the registry and calls `engine.parse_module()` before passing `ModuleInfo` to `scan_module()`.

### 3.3 Scanners that stay Python-only (6)

| Scanner                       | Why it stays Python-only                                          |
| ----------------------------- | ----------------------------------------------------------------- |
| scan_dependency_inversion.py  | Detects `self._dep = Dep()` — Python attribute assignment pattern |
| scan_interface_segregation.py | Detects `Protocol` and `ABC` — Python-specific abstractions       |
| scan_open_closed.py           | Detects `isinstance()`, `type()`, `match/case` — Python patterns  |
| test_splitter.py              | Rewrites Python test files (code generation)                      |
| scan_acronym_casing.py        | Reads Python comments and docstrings                              |
| scan_unused_all_exports.py    | Reads `__all__` and import tracking — Python-specific             |
| streamline_docstrings.py      | Rewrites Python docstrings                                        |

These stay in `python_code_style/` and `patterns/` and keep using `ast` directly. They can be ported later if needed.

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

### 4.1 Extend `setup/SKILL.md`

Add a `php` section to the setup procedure:

- Detect `composer.json` in project root
- Read `require` and `require-dev` for dependencies
- Read `autoload.psr-4` for namespace → directory mapping
- Read `autoload-dev.psr-4` for test namespace → directory mapping
- Detect tools: `phpunit`, `phpstan`, `psalm`, `php-cs-fixer`, `phpcs`
- Populate `php` object in `settings.json`:

```json
{
  "php": {
    "tools": {
      "phpunit": true,
      "phpstan": false,
      "psalm": false,
      "php_cs_fixer": true,
      "phpcs": false
    },
    "code_style": {
      "check_naming_conventions": true,
      "check_one_class_per_file": true
    },
    "testing": {
      "check_test_naming": true
    },
    "autoload": {
      "psr-4": { "App\\": "src/" },
      "psr-4-dev": { "Tests\\": "tests/" }
    },
    "php_version": "8.2"
  }
}
```

### 4.2 Update `setup/assets/settings_template.json`

Add the `php` object template.

### 4.3 Update `docs/reference/settings-schema.md`

Document the `php` object schema.

---

## Phase 5 — PHP skills

### 5.1 Create `php-code-style/` skill

```
php-code-style/
├── SKILL.md
└── assets/
    └── php-cs-fixer-rules.php    # default ruleset template
```

`SKILL.md` covers:

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

Create `src/zolletta_metaskill/php_patterns/`:

```
src/zolletta_metaskill/php_patterns/
├── __init__.py
├── scan_php_dependency_inversion.py   # detects `new Dep()` in constructors
├── scan_php_interface_segregation.py  # detects fat interfaces (many methods, partial implementers)
└── scan_php_open_closed.py            # detects if/elseif type ladders with instanceof
```

These use `PhpEngine` to parse PHP files and detect PHP-specific OCP/DIP/ISP violations:

- `instanceof` chains (OCP violation)
- `new` in constructors (DIP violation)
- Interface with many methods where implementers only use a subset (ISP violation)

### 6.2 Tests

- `tests/php_patterns/test_scan_php_dependency_inversion.py`
- `tests/php_patterns/test_scan_php_interface_segregation.py`
- `tests/php_patterns/test_scan_php_open_closed.py`
- Fixtures: `tests/fixtures/php/src/` with violation examples

---

## Phase 7 — Documentation

### 7.1 Update `docs/reference/code/scripts.md`

- Add PHP scanners to the reference table
- Document the `LanguageEngine` protocol
- Add usage examples for PHP scanning

### 7.2 Update `docs/explanation/code/php/php-review-patterns.md`

- Expand with SOLID violation examples
- Add tree-sitter-based scanner references

### 7.3 Update `README.md`

- Add PHP to the supported languages list
- Add `tree-sitter-php` to dependencies

### 7.4 Update `SKILL.md` (root)

- Add `php-code-style` and `php-testing-patterns` to the skill list
- Update the "Supported languages" section

### 7.5 Update `CHANGELOG.md`

- `[1.3.0]` entry for PHP support

---

## Phase 8 — Dependencies and CI

### 8.1 `pyproject.toml`

Add optional dependencies:

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
2. **Phase 2** — PythonEngine (refactor existing ast logic) + tests
3. **Phase 3** — Refactor 7 language-agnostic scanners + tests
4. **Phase 4** — PHP setup (composer.json → settings.json)
5. **Phase 5** — php-code-style and php-testing-patterns skills
6. **Phase 2.3** — PhpEngine (tree-sitter) + tests
7. **Phase 6** — PHP SOLID scanners + tests
8. **Phase 7** — Documentation updates
9. **Phase 8** — Dependencies, CI, version bump

## Risks

- **tree-sitter-php** adds a native dependency. Consider making it optional (`pip install zolletta-metaskill[php]`) so the base package stays lightweight.
- **PhpEngine complexity**: tree-sitter queries for PHP are more verbose than Python ast walks. Budget extra time.
- **Scanner refactoring**: changing the signature of 7 scanners will break any existing tests. Tests must be recovered or rewritten first (see `PLAN-TEST-RECOVERY.md`).
- **Backward compatibility**: scanners currently called as `python3 src/.../scan_x.py <dir>`. The CLI interface must remain the same — the engine selection happens internally based on file extensions.
