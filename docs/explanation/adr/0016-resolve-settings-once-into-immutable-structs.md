# ADR-0016: Resolve settings once into immutable structs

## Status

Accepted

## Context

ADR-0002 established `settings.json` as the single configuration source, and ADR-0015 extended it to every review script and removed the bespoke CLI flags. Both settled *where* configuration comes from. Neither settled *how it reaches the code that consumes it*, and the answer in practice was: as a raw `dict[str, Any]`, re-inspected at every layer that needed something.

That had three costs, all observed in the documentor package.

**Re-derivation was duplicated and drifted.** `documentation.cache_dir` resolution lived apart from the four entry points that needed it, and every consumer could reach its own answer. The concrete result was two directories holding the same filenames: `resolve_cache_dir` returned a flat, run-agnostic `.zolletta-metaskill/cache` while the review orchestrator wrote into `<run>/cache/`. The two copies were not interchangeable — `link_checker.json` measured 1 631 B in the flat cache and 175 658 B in the run folder, one being the tool's own cache artifact and the other its captured `--broken-only` stdout, with nothing in either filename marking which was authoritative. Re-deriving the path at each entry point is what allowed the divergence in the first place.

**Settings-derived values were indistinguishable from everything else.** A resolved path, a threshold, a git rename list and a loop index all arrived as plain arguments, so nothing in the type system, and often nothing in review, could tell a value that came from configuration from one that did not. The cost showed up as arity: eleven methods exceeded the configured `max_arguments` of 5. For `DriftDetector` the excess was not incidental — six parameters where one was settings-derived, which is a signal that the signature was describing a bag of values rather than a dependency.

**The obvious fix was a no-op.** Pointing the flat cache at the newest run folder looked like a one-liner, and it was: `max(subdirs, key=name)` returns `cache` rather than a run folder, because `"cache"` sorts after any `"YYYY-..."` name. The naive version would have passed its own tests, kept writing to the flat path, and been indistinguishable from the code it replaced.

Bundling also has a failure mode of its own, which this ADR rules out rather than leaving to taste: a struct whose fields are all the same type is still transposable at a positional call site, and a struct that stores a value derivable from its own fields can be constructed in a contradictory state. Both are addressed below.

## Decision

Configuration is resolved once per run into immutable dataclasses, and those values are passed down unchanged rather than re-derived at each entry point or threaded as a raw dictionary.

The rules that make this more than a naming preference:

- **One resolution per run, at the entry point that owns the run.** A `from_settings` classmethod is the only place a `documentation.*` key is read. Below the entry point, a raw `settings` dict is never a function parameter.
- **Structs are `frozen=True`.** Resolution produces a value that a run shares; nothing downstream may edit it to suit a local case.
- **Derived values are properties, not fields.** `DocContext.file_parent_dir` is computed from `file_rel_path` rather than stored alongside it. A stored field would let a caller construct a document with a parent directory that contradicts its own path, and every reference would then resolve against the wrong base without raising.
- **Collections are tuples even when callers hold lists.** `SplitPlan` and `DistillDiff` accept what the caller has and store an immutable form, so freezing cannot be defeated by keeping a reference to the list that was passed in.
- **Bundle by role, not by count.** A single "context" object holding everything was rejected: it would fuse values with different lifetimes and different sources. The documentor settled on three tiers, each with its own struct — `GitRunContext` (run-invariant, from git, *not* from settings), `DocumentorSettings` (run-invariant, from `documentation.*`), and `DocContext` (rebuilt per document).
- **Merge only values that are meaningless apart.** `DistillDiff` bundles the four values that are the input and output of one merge; `APIDocReportOptions` bundles four values none of which is derivable from the others.

This is a constraint on future work, not a description of one refactor. A new settings-derived value is read once in `from_settings` and arrives as a field; a new per-item value is bundled with its siblings rather than added as a parameter.

## Consequences

**Positive:**

- One place reads each key, so a change to a key's meaning cannot leave half the call sites behind.
- A settings-derived argument is distinguishable at the call site by its type, which is what makes the arity limit enforceable rather than aspirational.
- Frozen structs cannot be mutated by one consumer in a way that changes another's result.
- Deriving values where they are needed makes a contradictory state unrepresentable instead of merely unlikely.

**Negative:**

- Resolution moves to the entry point, so adding a key means touching the struct, its resolver, and every consumer that must now pass it — more files per key than reading `settings` inline at the point of use.
- Callers that previously resolved a value on demand now depend on the struct having been built, so standalone helper invocations need a struct constructed by hand. The extra construction is the visible cost of the boundary.
- Three structs with different lifetimes cost one extra concept to learn, and the boundary between "settings" and "runtime facts" has to be drawn per value. `GitRunContext` is deliberately *not* settings-derived: `repo_root` is a runtime absolute path, because `settings.json` only ever holds the relative `documentation.dir`.

**Neutral:**

- `documentation.cache_dir` remains a supported explicit override, and still wins over the derived default. It was kept rather than removed because it is the only way to point output outside the repository, which some setups need.
- `adr-distiller` extracts the first non-empty line of the `## Decision` section, so a decision that must read correctly in `adr-distilled.md` has to be stated in full on that line. ADR-0014 and 0015 both had directives hand-refined for exactly this reason.
