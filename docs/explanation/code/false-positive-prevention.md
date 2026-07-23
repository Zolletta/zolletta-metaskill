---
audience: human, ai
status: stable
skills: [patterns]
---

# False Positive Prevention

The patterns skill includes three mechanisms to prevent verdict oscillation between reviews. These mechanisms ensure that automated triage signals are never reported as findings without human judgment.

## 1. Mandatory judgment step for God class detection

`scan_class_metrics.py` reports class size as a triage signal, never a verdict. Before reporting any class as a God class, the reviewer must apply the "reason to change" test:

1. List every change that could require editing the class.
2. Group the changes by domain (HTTP/API, business logic, data access, configuration, presentation, I/O).
3. If the list has items from **different domains**, report it as a God class.
4. If all changes stem from the **same domain**, the class is cohesive. Explicitly state "cohesive — not a God class" in the report and do NOT report it as a finding.

**Classes that must be suppressed** (from [general-principles.md](general-principles.md) "What is NOT a God class"):

- A large class whose methods all serve one domain (e.g., a parser with 14 handler methods)
- A class with many static helpers that all operate on the same data structure
- An orchestrator that delegates to injected dependencies (high attribute count is delegation, not mixed concerns)
- A strategy class implementing a single protocol (all methods serve one strategy)

**You must NOT report a class as a God class or "large class" finding based on size alone.** Size (lines, methods, attributes) is a triage signal, never a verdict. A 400-line parser with 14 methods that all serve the parsing domain is NOT a God class. A 234-line orchestrator with 15 methods that delegates to injected dependencies is NOT a God class.

## 2. Coverage cross-check for missing tests

`scan_tests.py` reports structurally missing test files. Before reporting any as a finding, the reviewer must run `pytest --cov` and check the file's coverage:

1. Run `pytest --cov` (or `pytest --cov --cov-report=term-missing` if available).
2. Check the coverage percentage for each file in the "Missing tests" table.
3. If the file has **>50% coverage**, downgrade to informational — do NOT report it as a finding. Note it in an "Informational" section: "Structurally missing direct test file, but covered at X% via indirect tests."
4. Only report as a finding if the file has **<50% coverage** AND no direct test file AND no indirect class references.

This prevents the whack-a-mole cycle where every review re-reports the same structurally-missing-but-adequately-covered files.

## 3. Semantic composition-root detection

The `scan_dependency_inversion.py` scanner excludes entry points by filename pattern and detects DI container creation (`make_container()`, `Container()`, etc.) semantically. If the scanner still flags a class that is clearly a composition root (it wires the DI container, creates the container, or is the top-level entry point), suppress it and note "composition root — not a DIP violation" in the report.

Someone has to create the container — that is not a violation. The composition root (main, CLI entry point) is the only place where object creation belongs.

## Why these mechanisms exist

Without these checks, automated scanners produce false positives that oscillate between reviews:

- **Size-based God class detection** flags the same large-but-cohesive classes every review, wasting triage time.
- **Structural missing-test detection** re-reports files that are actually well-covered through indirect tests.
- **Pattern-based DIP detection** flags composition roots that are explicitly exempted by the DIP principle itself.

Each mechanism adds a mandatory human-judgment step between the automated signal and the reported finding, ensuring that only genuine issues reach the report.
