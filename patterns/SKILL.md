---
name: zolletta-metaskill-patterns
version: 1.1.0
license: MIT + Commons Clause
description: >
  Language-agnostic design pattern analysis with automated class metrics scanning. Detects God classes, SOLID violations, tight coupling, and composition-vs-inheritance issues in Python (via AST scripts) and other languages (via manual principle application). Use when refactoring a God class, evaluating structural quality, or planning a modular architecture. Succeeds and extends python-design-patterns (MIT, wshobson/agents).
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
  - write
  - run_subagent
  - read_subagent
  - mcp_call_tool
  - mcp_list_tools
---

# Zolletta-metaskill Design Patterns

Identify structural problems in object-oriented codebases using a two-phase approach:

1. **Automated triage** — run the scanning scripts to find large classes with many methods/attributes. This is a signal, not a verdict.
2. **Principle-based judgment** — apply the "reason to change" test to distinguish true God classes from long-but-cohesive classes.

The principles are language-agnostic (KISS, SOLID, Separation of Concerns, Composition over Inheritance, Rule of Three). The automated scripts currently support Python via its `ast` module. For PHP and other languages, apply the principles manually by reading the code — the scripts are a triage accelerator, not a requirement.

## When to Use This Skill

- Refactoring a God class or monolithic function that has grown too large
- Evaluating a pull request for structural issues (tight coupling, leaking types)
- Planning a modular architecture or choosing how to layer responsibilities
- Deciding whether to add a new abstraction or live with duplication
- Choosing between inheritance and composition for a new class hierarchy
- When a codebase is becoming hard to test because of entangled I/O and business logic
- As part of a `/zolletta-metaskill review` run (patterns subagent)

## Reference Files

This skill is organized into a lean entry point (this file) plus shared reference files in `../reference/`. Some are **mandatory reading** (marked with ★) — you must read them before starting any review. Others are optional and can be read on demand.

| File | Mandatory | Content |
| ---  | ---       | --- |
| [general-principles.md](../reference/general-principles.md) | ★ | Language-agnostic principles: SOLID (SRP, OCP, LSP, ISP, DIP), KISS, Separation of Concerns, Composition over Inheritance, Rule of Three, function size, dependency injection, God class detection procedure, "What is NOT a God class" criteria, common anti-patterns, and manual checks for non-Python languages — **shared** |
| [python-review.md](../reference/python-review.md) | ★ | Python-specific patterns: strategy pattern with autodiscovery, one-class-per-file convention, naming conventions, test structure mirroring, test God class splitting, Protocol vs ABC guidance — **shared** |
| [scripts.md](../reference/scripts.md) | ★ | Full reference for all 10 scripts: usage, options, examples, and the complete 14-step workflow — **shared** |
| [code-exploration.md](../reference/code-exploration.md) | on demand | Code graph tools (tokensave) decision tree, subagent guidance, and task templates — **shared** |
| [tool-messages.md](../reference/tool-messages.md) | on demand | "not installed" messages for the tool-failure handler — **shared** |

**Tool-failure handler**: if a tokensave MCP call fails with tool-not-found / server-not-found, follow the [tool-failure handler](../SKILL.md#tool-failure-handler) in the meta-skill — update `settings.json`, print the "not installed" message, and continue with grep/read fallback.

## Mandatory Procedure (Python)

Before evaluating any findings, you MUST read the three mandatory reference files (★) listed above. The principles in these files prevent false positives. Skipping them produces verdict oscillation between reviews.

### Mandatory judgment step for God class detection

For every class in the `scan_class_metrics.py` top-15 output, you MUST apply the "reason to change" test before reporting it as a finding:

1. List every change that could require editing the class.
2. Group the changes by domain (HTTP/API, business logic, data access, configuration, presentation, I/O).
3. If the list has items from **different domains**, report it as a God class.
4. If all changes stem from the **same domain**, the class is cohesive. Explicitly state "cohesive — not a God class" in the report and do NOT report it as a finding.

**Classes that must be suppressed** (from `general-principles.md` "What is NOT a God class"):

- A large class whose methods all serve one domain (e.g., a parser with 14 handler methods)
- A class with many static helpers that all operate on the same data structure
- An orchestrator that delegates to injected dependencies (high attribute count is delegation, not mixed concerns)
- A strategy class implementing a single protocol (all methods serve one strategy)

**You must NOT report a class as a God class or "large class" finding based on size alone.** Size (lines, methods, attributes) is a triage signal, never a verdict. A 400-line parser with 14 methods that all serve the parsing domain is NOT a God class. A 234-line orchestrator with 15 methods that delegates to injected dependencies is NOT a God class.

### Missing tests — coverage cross-check

The `scan_tests.py` "Missing tests" table is a **structural** signal. Before reporting any file from this table as a finding:

1. Run `pytest --cov` (or `pytest --cov --cov-report=term-missing` if available).
2. Check the coverage percentage for each file in the "Missing tests" table.
3. If the file has **>50% coverage**, downgrade to informational — do NOT report it as a finding. Note it in an "Informational" section: "Structurally missing direct test file, but covered at X% via indirect tests."
4. Only report as a finding if the file has **<50% coverage** AND no direct test file AND no indirect class references.

This prevents the whack-a-mole cycle where every review re-reports the same structurally-missing-but-adequately-covered files.

### Composition roots — DIP suppression

The `scan_dependency_inversion.py` scanner excludes entry points by filename pattern and detects DI container creation (`make_container()`, `Container()`, etc.) semantically. If the scanner still flags a class that is clearly a composition root (it wires the DI container, creates the container, or is the top-level entry point), suppress it and note "composition root — not a DIP violation" in the report. Someone has to create the container — that is not a violation.

## Output

When this skill runs a review, it writes its findings to a markdown file using the [report template](assets/report_template.md):

- **Path**: `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/patterns.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the folder and filename — follow their instructions instead
- **Directory setup**: the `.zolletta-metaskill/` directory and `.gitignore` entry are created by the [setup guard](../SKILL.md#setup-guard) — no manual setup needed
- **Format**: follow the [report template](assets/report_template.md) — grade at the top, scanning script results, findings grouped by severity with file/class/issue/principle/fix columns

## Best Practices Summary

1. **Keep it simple** — Choose the simplest solution that works
2. **Single responsibility** — Each unit has one reason to change
3. **Open for extension** — Add types via polymorphism, not if/elif modification
4. **Substitutable subtypes** — Subclasses must fulfill the parent contract
5. **Segregate interfaces** — Split fat protocols; implementers depend only on what they use
6. **Invert dependencies** — Pass dependencies in; only the composition root creates objects
7. **Separate concerns** — Distinct layers with clear purposes
8. **Compose, don't inherit** — Combine objects for flexibility
9. **Rule of three** — Wait before abstracting
10. **Keep functions small** — 20-50 lines (varies by complexity), one purpose
11. **Inject dependencies** — Constructor injection for testability
12. **Delete before abstracting** — Remove dead code, then consider patterns
13. **Test each layer** — Isolated tests for each concern
14. **Explicit over clever** — Readable code beats elegant code
15. **Size is not guilt** — A large class in one domain is not a God class
16. **Scan then judge** — Use scripts to triage, principles to verdict
17. **One class per file** — Each class gets its own file; filename matches class name
18. **Tests mirror source** — Test directory structure reflects source structure

## Attribution

The design pattern principles and reference examples in this skill are adapted from [python-design-patterns](https://github.com/wshobson/agents) by wshobson (MIT License). The scanning scripts and the "reason to change" diagnostic workflow are original additions by Zolletta-metaskill.
