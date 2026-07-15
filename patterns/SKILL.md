---
name: zolletta-review
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

# Zolletta Design Patterns

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
- As part of a `/zolletta-python-review` run (design-patterns subagent)

## Reference Files

This skill is organized into a lean entry point (this file) plus five reference files. Read the relevant reference file when you need detailed guidance:

| File | Content |
| ---  | --- |
| [general-principles.md](../reference/general-principles.md) | Language-agnostic principles: SOLID (SRP, OCP, LSP, ISP, DIP), KISS, Separation of Concerns, Composition over Inheritance, Rule of Three, function size, dependency injection, God class detection procedure, common anti-patterns, and manual checks for non-Python languages — **shared** |
| [python-review.md](references/python-review.md) | Python-specific patterns: strategy pattern with autodiscovery, one-class-per-file convention, naming conventions, test structure mirroring, test God class splitting, Protocol vs ABC guidance |
| [scripts.md](references/scripts.md) | Full reference for all 10 scripts: usage, options, examples, and the complete 14-step workflow |
| [code-exploration.md](../reference/code-exploration.md) | Code graph tools (tokensave, GitNexus, graphify) decision tree, subagent guidance, and task templates — **shared** |
| [troubleshooting.md](references/troubleshooting.md) | Common questions and edge cases: God class false positives, DI parameter bloat, composition depth, rule of three exceptions, layering violations |

## Output

When this skill runs a review, it writes its findings to a markdown file with formatted tables:

- **Path**: `.scratches/zolletta-review/zolletta-review-YYYY-MM-DD-HH-MM.md` (timestamp = run start time)
- **Compound skills** (e.g. `zolletta-python-review`) may override the folder and filename — follow their instructions instead
- **`.scratches/` setup**: create the directory if it does not exist; add `.scratches/` to `.gitignore` (create `.gitignore` if not present, do not modify an existing one beyond appending the entry)
- **Format**: each finding is a row in a table with columns for severity, file, class/symbol, issue, and suggested fix

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

The design pattern principles and reference examples in this skill are adapted from [python-design-patterns](https://github.com/wshobson/agents) by wshobson (MIT License). The scanning scripts and the "reason to change" diagnostic workflow are original additions by Zolletta.
