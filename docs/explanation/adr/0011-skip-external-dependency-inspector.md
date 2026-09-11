# ADR-0011: Do not add an external dependency inspector tool

## Status

Accepted

## Context

The article [Maintainability sensors for coding agents](https://martinfowler.com/articles/sensors-for-coding-agents.html) (Martin Fowler, 2026) describes using [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) as a sensor to enforce structural module dependency rules — "UI must not import from data layer", "domain must not import from infrastructure", "no circular imports between modules." We evaluated whether Zolletta-metaskill should integrate an equivalent external dependency inspector tool for any of its supported languages.

Equivalent external dependency inspector tools exist across ecosystems:

- **JavaScript/TypeScript**: [dependency-cruiser](https://github.com/sverweij/dependency-cruiser)
- **Python**: [import-cruiser](https://github.com/kevin91nl/import-cruiser), [Tach](https://github.com/tach-org/tach), [python-dependency-linter](https://pypi.org/project/python-dependency-linter/), [PyArchRules](https://pypi.org/project/pyarchrules/)
- **PHP**: [Deptrac](https://github.com/deptrac/deptrac), [Modulint](https://github.com/shipmonk-rnd/modulint), [php-dep](https://github.com/DeGraciaMathieu/php-dep)

## Decision

We do **not** integrate an external dependency inspector tool into Zolletta-metaskill.

The fundamental problem is that these tools are not zero-config. Unlike the sensors we do integrate (ruff, mypy, ty, vulture, PHPStan, Psalm), which produce findings on any project with sensible defaults, external dependency inspector tools require the project to **declare its architecture first** — defining modules, layers, and their allowed dependencies in a config file (`deptrac.yaml`, `tach.toml`, `import-cruiser.json`, `.dependency-cruiser.js`, etc.).

This creates two scenarios, both of which produce zero value:

1. **Config exists** — the project has already decided to enforce its architecture and is almost certainly running the tool in CI. Zolletta-metaskill re-running it duplicates CI output with no added signal.
2. **No config exists** — the tool cannot run. Zolletta-metaskill cannot invent architectural boundaries for a project; that is a design decision, not a review finding.

The narrow middle ground — "config exists but not in CI" — is rare enough to be a rounding error. Projects that invest in writing dependency-rule configs do so specifically to enforce them in CI.

This is structurally different from the sensors we do integrate. Ruff has `PLR0913` (too-many-arguments), `C901` (cyclomatic complexity), and `PLR0915` (too-many-statements) — rules that exist in a tool the project already uses but hasn't enabled. The sensor's job is to flip them on. That is a real value-add. External dependency inspector tools require the project to pre-declare its architecture, which is not something a review skill can or should do. This applies regardless of language.

The existing `dependency_inversion_scanner.py` already covers the *detectable* part of this axis — "this class creates its own dependencies instead of receiving them injected" — without requiring any configuration. That is the right level for a review skill: things it can find without the project pre-declaring its architecture.

## Consequences

**Positive:**

- No dead-weight sensor that either duplicates CI or cannot run.
- No false expectation that Zolletta-metaskill can enforce architectural boundaries the project hasn't defined.
- The decision is documented for future contributors who may re-suggest this integration after reading the Fowler article.

**Negative:**

- Projects that have defined module boundaries but are not enforcing them in CI get no coverage from Zolletta-metaskill. This is accepted as a vanishingly rare case.

**Neutral:**

- The existing DIP scanner continues to cover the configuration-free subset of dependency discipline (internal `new` creation in constructors).
- The ADR distiller (ADR-0010) provides architectural context to review subagents from the project's own ADRs, which is the configuration-free way to make reviewers architecture-aware.
- This decision covers external dependency inspector tools only — inferential modularity review (LLM-driven coupling analysis, as done by the existing `patterns` skill) is a separate concern and is not affected by this decision.
