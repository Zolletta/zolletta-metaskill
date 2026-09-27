---
audience: human, ai
status: stable
skills: [patterns]
---

# Balanced Coupling

Vlad Khononov's Balanced Coupling model (published openly at [coupling.dev](https://coupling.dev) and in *Balancing Coupling in Software Design*) — the framework the `patterns` review uses to decide whether an integration between two parts of the codebase is a finding. Coupling is not inherently bad; the question is whether it is **balanced** given how far apart the components sit and how often they change.

## The three dimensions

- **Integration Strength** — how much knowledge crosses the boundary. Knowledge is the key unit: implementation details, invariants, and semantics — not just signatures.
- **Distance** — the socio-technical cost of a cascading change. Components in the same module are close; components in different modules, services, or team-owned codebases are progressively farther.
- **Volatility** — the probability that the integrated components will change. Evaluated via the domain role (DDD subdomains), never via commit history.

The balance rule:

```text
BALANCE = (STRENGTH xor DISTANCE) or (not VOLATILITY)
```

Coupling is balanced when strength and distance are inversely related (high strength is fine at low distance, and vice versa) **or** when the integration is unlikely to change. An integration that is **unbalanced and volatile** — strong knowledge sharing across a distant boundary that changes often — produces cascading, expensive, unpredictable changes. That is complexity.

## Integration strength

Ordered from weakest to strongest:

| Level        | Knowledge shared                                          | Scanner signal                                                                     |
|--------------|-----------------------------------------------------------|------------------------------------------------------------------------------------|
| **Contract** | A stable, narrow public interface                         | `type` usage (type hints against a public API), `import-only`                      |
| **Model**    | A shared data model — both sides know the same structures | `attribute` access to a shared record/DTO                                          |
| **Functional** | Business-logic semantics — *how* the other side works   | `call`/`new` — behavior is invoked, not just referenced                            |
| **Intrusive**  | Implementation details — privates, internals            | Reaching into internals; `extends` of a concrete class; monkey-patching            |

Strength is a judgment call informed by the `integration_graph_scanner.py` usage hints, not derived from them — read the flagged edge's code when the hint alone is ambiguous (e.g. `call` on a stable public factory is contract-ish; `call` on a method exposing internals is functional or intrusive).

## Distance

Distance is measured relative to the project's abstraction level:

- **Same module** — the lowest distance; strong coupling here is expected cohesion.
- **Cross-module, same codebase** — moderate; the scanner's edges are exactly these boundaries.
- **Cross-service / cross-repo** — highest; outside what a `src/` review can see, but calls through adapters/clients still carry it.

Distance is partially inferable from code structure (module paths, package boundaries). Organizational distance — different teams owning the components — is not visible in code; treat it as unknown unless the project's docs or ADRs say otherwise.

## Volatility

Volatility is estimated from the **subdomain** a module plays, not from git history:

- **Core** (the business differentiator — `auth/`, `billing/`, domain logic) — high volatility; changes are frequent and matter.
- **Supporting** (helpers that exist because of the core) — medium.
- **Generic** (solved problems — `utils/`, adapters over stable libraries, vendor shims) — low; they mostly change when the core forces them to.

The reviewer infers the subdomain from naming, location, and what the module actually does — always noted as an assumption. When `adr-distilled.md` / `cache/_context.md` carries architectural directives identifying core or generic areas, those refine the classification.

## Applying the balance rule

The four extreme combinations and their verdicts:

| Strength | Distance | Volatility | Verdict |
|----------|----------|------------|---------|
| high     | high     | high       | **Unbalanced + volatile — finding.** Strong knowledge flow across a distant boundary that keeps changing: the worst form of complexity. |
| high     | high     | low        | Tolerable tech debt — **note**, not a finding. |
| low      | low      | any        | Over-engineering / cohesion-drift risk — **note**; unrelated logic may be forced into the same module. |
| balanced | balanced | —          | No action. |

**Severity discipline**: only *unbalanced AND volatile* integrations are reported as findings. Everything else is a note — high-strength + high-distance + low-volatility is stable enough to tolerate, and low-strength + low-distance risks cohesion rot rather than cascade. This mirrors the God-class discipline in `general-principles.md`: the scanner provides triage, the judgment pass decides.

## The model is fractal

The rule applies identically at every level: class, module, service, system. For a `src/` review the default levels are **class** (imports between files) and **module/package** (imports between packages) — the scanner emits file-level edges; group by package when assessing module-level balance.

## Non-interactive inference

This review runs without asking the user questions:

- **Distance** is inferred from code structure — same module = low, cross-module = higher.
- **Volatility** is inferred from the subdomain heuristic above.
- Every inferred classification is **noted as an assumption** in the report so a human can override it with domain knowledge the code doesn't carry.

## Relation to existing principles

- **God class** — intrusive-strength knowledge concentrated *inside* one boundary; the same model applied within a single unit.
- **Dependency Inversion** — depending on an abstraction is contract-strength integration by construction.
- **"Reason to change"** — the volatility axis stated differently: an integration aligned with one source of change stays balanced.
- **Interface Segregation** — narrowing a contract reduces strength at the same distance, rebalancing the integration.

## Enforcement

`integration_graph_scanner.py` emits the internal edges and usage hints that seed the assessment — it is a triage artifact, not a verdict. The judgment pass (see the patterns skill's mandatory coupling-assessment step) classifies strength, distance, and volatility per cross-module edge and applies the balance rule.

```bash
python3 src/zolletta_metaskill/patterns/general/integration_graph_scanner.py --json
```

## Attribution

The Balanced Coupling model is by Vlad Khononov ([coupling.dev](https://coupling.dev), *Balancing Coupling in Software Design*). This page restates the openly published model in original wording. The reference implementation's skill files (`vladikk/modularity`) are licensed CC BY-NC-SA 4.0 and were not copied. The sensor-based framing follows Martin Fowler's [Maintainability sensors for coding agents](https://martinfowler.com/articles/sensors-for-coding-agents.html).
