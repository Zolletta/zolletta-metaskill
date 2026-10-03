# PLAN-62 — Dogfooding (issue #62)

Issue: https://github.com/Zolletta/zolletta-metaskill/issues/62
Branch: `62-dogfooding`

Two deliverables per the amended issue: **(A)** fake projects as scanner regression
inputs (this branch), **(B)** a real-skill dogfooding run in a fresh session
(install script → review skill → burn down findings, 100% coverage maintained).

## Part A — `fake-projects/` regression fixtures

### Location decision

`fake-projects/` at the **repo root** — not `tests/fixtures/`. Rationale:

- pytest `testpaths = ["tests"]` would collect fixture `test_*.py` files and fail
  the suite on their intentionally-broken imports.
- `tests/` is a scanned test root: `test_structure_scanner.py` examines any
  `test_*` file inside it, so fixture test files would show up as
  orphaned/misnamed/multi-class findings in **our own** dogfooding report —
  polluting the burn-down with phantom findings (no per-file suppression exists).
- `src/` is the only scanned source root, so a root-level `fake-projects/` is
  invisible to both pytest and every self-scan.

### Layout

Each fake project is a standalone mini-project — deliberately non-coherent, one
file per sin-cluster:

```
fake-projects/
  README.md                       # purpose, "intentionally broken", links issue #62
  python/
    pyproject.toml                # minimal fake package (never installed)
    .zolletta-metaskill/settings.json
    src/fakeproj/                 # one file per deterministic finding
    tests/                        # broken test structure on purpose
    expected_findings.json        # scanner → file → symbol/kind manifest
    expected_judgment.md          # AI-flaggable checklist (documented, not CI-asserted)
  php/
    composer.json                 # PSR-4 autoload map
    .zolletta-metaskill/settings.json
    src/ , tests/
    expected_findings.json
    expected_judgment.md
```

### Fixture settings

Each `settings.json` configures its own language with **deliberately low
thresholds** so fixture files stay small and readable (e.g. `max_arguments: 2`,
`max_function_length: 5`, `max_cyclomatic_complexity: 3`, `max_file_length: 40`),
all `check_*` toggles `true`. Source root `src`, test root `tests`, PSR-4 map for
PHP.

### Scanner coverage matrix (deterministic findings)

| Scanner | Python trigger | PHP trigger |
|---|---|---|
| `file_length_scanner` | module > `max_file_length` | same |
| `max_arguments_scanner` | `def` with >2 params | method with >2 params |
| `function_length_scanner` | `def` >5 lines | method >5 lines |
| `cyclomatic_complexity_scanner` | `if/elif/for` chain | same |
| `suppression_reason_scanner` | bare `# type: ignore` | bare `@phpstan-ignore*`/`@psalm-suppress` |
| `one_class_per_file_scanner` | two classes in one file; multi-class test file | two classes in one file |
| `naming_conventions_scanner` (`check_filename_matches_class`) | file name ≠ class name | file name ≠ class name |
| `acronym_casing_scanner` | `ApiClient`-style mis-cased acronym | same |
| `unused_all_exports_scanner` (py only) | `__all__` entry never imported | — |
| `class_metrics_scanner` | god-class-candidate metrics row | same |
| `integration_graph_scanner` | package with internal edges incl. intrusive usage (`call` into `_private`) | `use` edges + `new`/`extends` usage hints |
| `liskov_substitution_scanner` | subclass violating parent contract | PHP engine scan if applicable |
| `dependency_inversion_scanner` | `Concrete()` inside method | `new Concrete()` inside method |
| `interface_segregation_scanner` | fat Protocol + stubbed implementer | fat interface + stubbed impl |
| `open_closed_scanner` | `isinstance` type dispatch | `instanceof` dispatch |
| `test_god_classes_scanner` | test class over method threshold | same |
| `test_structure_scanner` | misnamed, misplaced, orphaned test files + missing-test row | same categories |
| `test_naming_scanner` (py) | test methods violating naming convention | — |

(`mutmut_survived_reporter`, `link_checker`, `adr_*`, `test_splitter` and the
setup detectors are out of scope — not code-review scanners.)

### Judgment-pass layer (AI-flaggable)

A handful of files exercise categories no scanner can decide: SRP smell,
premature abstraction (single-implementation interface), KISS violation,
intrusive coupling across a package boundary (feeds the coupling assessment).
Each carries an `# EXPECTED:`/`// EXPECTED:` comment naming the principle; the
same list lives in `expected_judgment.md` so a review run can be checked for
coverage. These are **not** asserted by CI — they're the checklist for Part B.

### Regression test wiring

No new top-level test file (a non-mirrored `test_*.py` would itself be flagged
misnamed/orphaned by `test_structure_scanner` in the self-scan). Instead each
scanner's **existing mirrored test class** gains fixture-regression tests:
load `fake-projects/<lang>/.zolletta-metaskill/settings.json`, run the scanner
(in-process where the class accepts settings/roots; subprocess with
`cwd=fake-projects/<lang>` where the CLI path matters), and compare against the
scanner's slice of `expected_findings.json`. PHP tests reuse the
`TS_PHP_AVAILABLE` skip guard. Paths in the manifest are relative to the fixture
root; findings match on `file` + `symbol`/`kind`, not line numbers (brittle).

### Verification (Part A)

- `uv run pytest` — all green, 100% coverage maintained.
- Each scanner `--json` run manually against both fixtures during development;
  manifest written from verified real output (then re-asserted by tests).
- `uv run python src/zolletta_metaskill/testing_style/general/test_structure_scanner.py`
  on the repo — must show **zero** new findings from `fake-projects/`.
- `pytest` at repo root must not collect `fake-projects/`.
- ruff/mypy/ty/vulture on `src/` + `tests/` unchanged — fixture files are NOT
  linted or typed (they're intentionally bad); verify CI doesn't pick them up
  (all our quality commands take explicit paths: `src/`, `tests/`).
- `git status` — fixtures committed normally (git-aware `iter_files` lists them
  for the fixture run because they're committed).

### Conventional commit + PR

`test(fixtures): add fake-projects regression inputs (#62)` — dedicated PR, then
wait for feedback per workflow.

## Part B — real-skill dogfooding (separate session, after Part A merges)

1. `./install.sh` the released version.
2. Fresh session: run `setup` (re-verify `settings.json`), then the full
   `review` skill against this repo.
3. Triage every finding: fix, suppress with documented justification
   (`# suppress:`-style reasons where applicable), or configure — never silently
   ignore. `expected_judgment.md` lists what the AI pass *should* flag on the
   fixtures as a sanity reference.
4. Known existing debt entering the burn-down: ~38 C901 complexity violations,
   ~16 function-length, ~5 max-arguments, acronym-casing remnants.
5. 100% coverage maintained throughout; conventional commits; PR(s) for the
   burn-down.
