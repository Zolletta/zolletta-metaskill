---
audience: human, ai
status: stable
skills: [patterns]
---

# Detect God classes and structural design issues

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Identify God classes, missing tests, dependency-inversion violations, and other structural design problems in an object-oriented codebase using the zolletta-metaskill patterns workflow. The approach is two-phase: automated triage with scanning scripts, then principle-based judgment to distinguish true God classes from long-but-cohesive classes.

## Prerequisites

- A codebase with `src/` and `tests/` directories (scripts use the `ast` module — no code execution required)
- The zolletta-metaskill skill installed and available to the agent
- The scanning scripts at `src/zolletta_metaskill/scanners/` (or `scripts/python/` in the baseline layout)

## Phase 1 — Automated triage

Run the scanning scripts to get a structural overview. Each script produces a markdown report with candidates sorted by severity.

### Step 1 — Class metrics

```bash
python3 src/zolletta_metaskill/scanners/scan_class_metrics.py src --top 30 --min-lines 50
```

This lists the largest classes by line count, with method count, public method count, and `self.*` attribute count. Classes with many attributes and methods are God class candidates.

### Step 2 — Test God classes

```bash
python3 src/zolletta_metaskill/scanners/scan_test_god_classes.py tests --show-methods
```

This finds test classes that test multiple unrelated SUTs. Use `--show-methods` to see the method names and spot mixed SUTs.

### Step 3 — SOLID violations

```bash
# Dependency Inversion (DIP)
python3 src/zolletta_metaskill/scanners/scan_dependency_inversion.py src

# Interface Segregation (ISP)
python3 src/zolletta_metaskill/scanners/scan_interface_segregation.py src --min-methods 5

# Liskov Substitution (LSP)
python3 src/zolletta_metaskill/scanners/scan_liskov_substitution.py src

# Open/Closed (OCP)
python3 src/zolletta_metaskill/scanners/scan_open_closed.py src
```

### Step 4 — Structural conventions

```bash
# One class per file + filename matches class
python3 src/zolletta_metaskill/scanners/scan_one_class_per_file.py src
python3 src/zolletta_metaskill/scanners/scan_naming_conventions.py --src src --tests tests

# Test directory mirrors source directory
python3 src/zolletta_metaskill/scanners/scan_tests.py --src src --tests tests
```

### Step 5 — Dead code

```bash
python3 src/zolletta_metaskill/scanners/scan_unused_all_exports.py src
```

## Phase 2 — Principle-based judgment

The scripts identify candidates, but not every large class is a God class. For each candidate from Phase 1, apply the "reason to change" test from [general-principles.md](../../explanation/code/general-principles.md):

1. **Read the class** — the script gives metrics, but we need to read the code to understand its responsibilities.
2. **Count reasons to change** — a God class has multiple unrelated reasons to change. If the class handles HTTP parsing, database access, and business logic, it has three responsibilities and should be split.
3. **Check cohesion** — a class with many methods that all operate on the same data is cohesive (not a God class). A class with methods that operate on disjoint subsets of data is not cohesive (God class).
4. **Check the false-positive prevention rules** from [false-positive-prevention.md](../../explanation/code/false-positive-prevention.md):
   - Mandatory judgment step — never report a God class based on metrics alone
   - Coverage cross-check — before reporting "missing tests", verify coverage is genuinely low
   - Semantic composition-root detection — entry points that create dependencies are not DIP violations

## Coverage cross-check (mandatory)

Before reporting any file from the "Missing tests" table as a finding, run `pytest --cov` and check the file's coverage. If the file has >50% coverage, it is adequately tested via indirect tests — downgrade to informational. Only report as a finding if coverage <50% AND no indirect references. This prevents the whack-a-mole cycle where every review re-reports the same structurally-missing-but-adequately-covered files.

## See also

- [General principles](../../explanation/code/general-principles.md) — SOLID and other fundamental principles
- [False-positive prevention](../../explanation/code/false-positive-prevention.md) — three mechanisms to avoid false positives
- [Structural conventions](../../explanation/code/structural-conventions.md) — one class per file, test mirroring, naming
- [Scripts reference](../../reference/code/scripts.md) — full reference for all scanning scripts
- [Split a God test class](split-god-test-class.md) — how to split a test class that tests multiple SUTs
