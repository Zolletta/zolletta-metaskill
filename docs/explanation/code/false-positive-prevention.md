---
audience: human, ai
status: stable
skills: [patterns]
---

# False Positive Prevention

The patterns skill includes three mechanisms to prevent verdict oscillation between reviews. These mechanisms ensure that automated triage signals are never reported as findings without human judgment.

## 1. Mandatory judgment step for God class detection

`class_metrics_scanner.py` reports class size as a triage signal, never a verdict. Before reporting any class as a God class, the reviewer must apply the "reason to change" test:

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

**Why this matters**: size-based detection flags the same cohesive classes every review, wasting triage time. See [God Object — Wikipedia](https://en.wikipedia.org/wiki/God_object).

## 2. Coverage cross-check for missing tests

`test_structure_scanner.py` reports structurally missing test files. Before reporting any as a finding, the reviewer must run `pytest --cov` and check the file's coverage:

1. Run `pytest --cov` (or `pytest --cov --cov-report=term-missing` if available).
2. Check the coverage percentage for each file in the "Missing tests" table.
3. If the file has **>50% coverage**, downgrade to informational — do NOT report it as a finding. Note it in an "Informational" section: "Structurally missing direct test file, but covered at X% via indirect tests."
4. Only report as a finding if the file has **<50% coverage** AND no direct test file AND no indirect class references.

This prevents the whack-a-mole cycle where every review re-reports the same structurally-missing-but-adequately-covered files.

**Why this matters**: indirect coverage via integration tests is real coverage — re-reporting covered files is noise. See [coverage.py — reporting](https://coverage.readthedocs.io/en/latest/cmd.html#reporting).

## 3. Semantic composition-root detection

The `dependency_inversion_scanner.py` scanner excludes entry points by filename pattern and detects DI container creation (`make_container()`, `Container()`, etc.) semantically. If the scanner still flags a class that is clearly a composition root (it wires the DI container, creates the container, or is the top-level entry point), suppress it and note "composition root — not a DIP violation" in the report.

Someone has to create the container — that is not a violation. The composition root (main, CLI entry point) is the only place where object creation belongs.

**Why this matters**: flagging the composition root as a DIP violation re-litigates the one place where `new` is correct. See [Composition Root — Clean Code](https://wiki.c2.com/?CompositionRoot).

## 4. Coverage-ignore annotations require a documented criterion

`@codeCoverageIgnore` (PHP) and `# pragma: no cover` (Python) exclude code from coverage measurement. When the criterion for *which* classes or lines qualify is not documented, the annotations become an escape hatch — every review re-flags the same classes, and the author re-justifies them from memory.

Before reporting a coverage-ignore annotation as a finding:

1. **Is there a project-level policy?** Look in `AGENTS.md`, `CONTRIBUTING.md`, or the review settings.
2. **Does the annotated code match the policy?** If yes, do not flag — note "excluded per <policy>".
3. **If no policy exists**, report it as a *process* finding once: "Coverage-ignore annotation present but no documented criterion. Either document the criterion or remove the annotation."

**Why this matters**: judgement that lives only in the author's head is not reproducible — the next reviewer cannot reproduce the decision. See [coverage.py — excluding code](https://coverage.readthedocs.io/en/latest/excluding.html), [PHPUnit — @codeCoverageIgnore](https://docs.phpunit.de/en/main/annotations.html#codecoverageignore).

## 5. Generational drift is a sub-tree finding, not a per-file defect

When a codebase has sub-projects of different ages, older sub-projects lag the conventions established in newer ones. This is **discipline drift**, not **discipline absence**.

Before reporting drift items as per-file findings:

1. **Identify the sub-tree boundary** (e.g. `workflow-runner/` vs `ci-tester-engine/`).
2. **Group all drift items by sub-tree**, not by file. Report once per sub-tree.
3. **Do not report each `Optional[str]` as a separate finding** — dozens of identical findings bury the actionable signal.
4. **Frame as a migration decision**: "Standardise or accept the drift. If standardising, file a migration task."

**Common drift signals**: legacy typing (`Optional[X]`, `List[T]`), numbered test names (`test_unit_01_...`), reduced ruff ruleset (`E,F,I` only), banner-comment separators.

**Why this matters**: a single sub-tree-level finding is actionable; 47 individual `Optional[str]` findings are noise. See [Why these mechanisms exist](#why-these-mechanisms-exist).

## Why these mechanisms exist

Without these checks, automated scanners produce false positives that oscillate between reviews:

- **Size-based God class detection** flags the same large-but-cohesive classes every review.
- **Structural missing-test detection** re-reports files that are actually well-covered through indirect tests.
- **Pattern-based DIP detection** flags composition roots that are explicitly exempted by the DIP principle itself.
- **Unguided coverage-ignore detection** re-litigates the same annotations every review.
- **Per-file drift reporting** buries a single migration decision under dozens of identical findings.

Each mechanism adds a mandatory human-judgment step between the automated signal and the reported finding.
