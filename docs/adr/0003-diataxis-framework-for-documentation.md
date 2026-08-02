# ADR-0003: Diátaxis framework for documentation

## Status

Accepted

## Context

Documentation needs structure to be useful. Without a framework, docs accumulate in a flat folder with no clear purpose — a README grows into a catch-all, tutorials mix with reference, and readers cannot find what they need.

Several documentation frameworks exist. The Diátaxis framework (https://diataxis.fr/) organizes content into four quadrants based on the reader's purpose: tutorials (learning), how-to guides (doing), reference (information), and explanation (understanding). Each quadrant has distinct conventions and serves a different audience.

## Decision

We adopt the Diátaxis framework for the project's documentation. Docs are organized into four quadrant directories: `tutorials/`, `how-to/`, `reference/`, and `explanation/`.

The documentor skill checks Diátaxis compliance:
- Each document is placed in the correct quadrant directory.
- Content matches the quadrant's purpose (no explanation in reference, no tutorial in how-to).
- Quadrant-specific completeness checks apply (e.g., tutorials need "What we will learn" and "Prerequisites"; how-to guides need "Prerequisites" or "Before Starting").
- The staleness scorer detects Diátaxis quadrant directories and applies the appropriate required sections, preventing docs from scoring 0 when they follow Diátaxis conventions instead of README-style sections.

For non-English documentation, the documentor translates Diátaxis signpost headings before running the staleness scorer, so the quadrant detection works across languages.

## Consequences

**Positive:**
- Documentation has a clear structure — readers know where to look based on what they need.
- The documentor can apply quadrant-specific quality checks, producing more relevant findings.
- The framework is well-established and documented at diataxis.fr, so contributors can learn it independently.
- Non-English docs are supported via translated signposts.

**Negative:**
- Contributors must understand the four quadrants to place docs correctly. Misplacement is a common finding in documentor reviews.
- Some documents span quadrants (e.g., a getting-started guide that is both tutorial and how-to). The framework requires choosing one primary quadrant.

**Neutral:**
- The Diátaxis structure is a convention, not enforced by tooling beyond the documentor's compliance checks. Contributors can deviate if they justify it.
