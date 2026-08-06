---
audience: human, ai
status: stable
skills: [patterns]
---

# Detect God classes and structural design issues

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Identify God classes, missing tests, dependency-inversion violations, and other structural design problems in an object-oriented codebase using the Zolletta-metaskill patterns workflow. The approach is two-phase: automated triage with scanning scripts, then principle-based judgment to distinguish true God classes from long-but-cohesive classes.

## Prerequisites

- A codebase with `src/` and `tests/` directories (scripts use the `ast` module — no code execution required)
- The scanning scripts at `src/zolletta_metaskill/{patterns,code_style,testing_style}/` (or `scripts/python/` in the baseline layout)

## Phase 1 — Automated triage

Run the scanning scripts to get a structural overview. Each script produces a markdown report with candidates sorted by severity.

### Step 1 — Class metrics

```bash
python3 src/zolletta_metaskill/patterns/class_metrics_scanner.py src --top 30 --min-lines 50
```

This lists the largest classes by line count, with method count, public method count, and `self.*` attribute count. Classes with many attributes and methods are God class candidates.

### Step 2 — Test God classes

```bash
python3 src/zolletta_metaskill/patterns/test_god_classes_scanner.py tests --show-methods
```

This finds test classes that test multiple unrelated SUTs. Use `--show-methods` to see the method names and spot mixed SUTs.

### Step 3 — SOLID violations

```bash
# Dependency Inversion (DIP)
python3 src/zolletta_metaskill/patterns/dependency_inversion_scanner.py src

# Interface Segregation (ISP)
python3 src/zolletta_metaskill/patterns/interface_segregation_scanner.py src --min-methods 5

# Liskov Substitution (LSP)
python3 src/zolletta_metaskill/patterns/liskov_substitution_scanner.py src

# Open/Closed (OCP)
python3 src/zolletta_metaskill/patterns/open_closed_scanner.py src
```

### Step 4 — Structural conventions

```bash
# One class per file + filename matches class
python3 src/zolletta_metaskill/code_style/general/one_class_per_file_scanner.py src
python3 src/zolletta_metaskill/code_style/general/naming_conventions_scanner.py --src src --tests tests

# Test directory mirrors source directory
python3 src/zolletta_metaskill/testing_style/general/test_structure_scanner.py --src src --tests tests
```

### Step 5 — Dead code

```bash
python3 src/zolletta_metaskill/code_style/python/unused_all_exports_scanner.py src
```

### Phase 2 — Judgment

Apply the "reason to change" test from [general-principles.md](../../explanation/code/general-principles.md) → God Class Detection → Procedure.

Suppress false positives per [false-positive-prevention.md](../../explanation/code/false-positive-prevention.md) → Rule 1 (mandatory judgment step) and Rule 2 (coverage cross-check).

## See also

- [General principles](../../explanation/code/general-principles.md) — SOLID and other fundamental principles
- [False-positive prevention](../../explanation/code/false-positive-prevention.md) — three mechanisms to avoid false positives
- [Structural conventions](../../explanation/code/structural-conventions.md) — one class per file, test mirroring, naming
- [Scripts reference](../../reference/code/scripts.md) — full reference for all scanning scripts
- [Split a God test class](split-god-test-class.md) — how to split a test class that tests multiple SUTs
