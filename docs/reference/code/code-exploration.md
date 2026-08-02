---
audience: human, ai
status: stable
skills: [patterns, documentor, review, external-review]
---

# Tools to Leverage

Decision tree for choosing the right exploration tool. See [tokensave.md](tokensave.md) for tool reference.

## Patterns-specific workflow with code graph tools

The standard scanning workflow (see [`scripts.md`](scripts.md)) can be enhanced:

1. Run `scan_class_metrics.py` → get the largest classes (unchanged)
2. For each top candidate, use `tokensave_context` to understand its responsibilities **without reading the full file**
3. Use `tokensave_callees` to list what the class calls — group calls by domain (SQL, HTTP, formatting, etc.)
4. Apply the "reason to change" test based on the domain grouping
5. **Before splitting**: run `tokensave_impact` (or `tokensave_callers`) to assess blast radius — warn the user if risk is HIGH or CRITICAL
6. After splitting: run `tokensave_affected` to find which tests to run

## Subagents

When running as part of `/zolletta-metaskill review`, this skill is invoked by a subagent. When running standalone, you may spawn your own subagents for parallel work.

### When to use subagents

- **Parallel class analysis**: after `scan_class_metrics.py` identifies 5+ candidates, spawn one background subagent per candidate to read the class and apply the "reason to change" test. Each subagent returns a structured verdict (God class / long-but-cohesive, with domain grouping).
- **Parallel test file analysis**: after `scan_test_god_classes.py --show-methods` identifies test God classes, spawn one subagent per class to list which SUTs it tests and whether each SUT has its own source file.

### When NOT to use subagents

- Don't spawn subagents for code exploration if tokensave is available — use `tokensave_context` instead (per `tokensave-rules.md`).
- Don't spawn more than 3 background subagents at a time (batch if needed).
- Don't use subagents for running the scanning scripts — run them directly with `exec`.

### Subagent task template

```text
You are analyzing a class for God class detection.

Class: {class_name}
File: {file_path}
Lines: {line_count}
Methods: {method_count}

This project has tokensave initialised (.tokensave/ exists). Use
tokensave_context as your ONLY exploration tool. Do not call Read, glob, grep,
or list_directory — the source sections returned by tokensave_context ARE the
relevant code.

1. Use tokensave_context to understand what {class_name} does and what it calls.
2. List every reason this class could need to change.
3. Group the reasons by domain (HTTP, business logic, data access, formatting,
   configuration, I/O, etc.).
4. Apply the "reason to change" test: if 2+ domains, it's a God class.
5. If it's a God class, propose a split (which methods go to which new class).

Return a structured verdict:
- Verdict: God class | Long-but-cohesive
- Domains: [list of domains with method counts]
- Split proposal: [if God class, which methods go where]
- Confidence: High | Medium | Low
```
