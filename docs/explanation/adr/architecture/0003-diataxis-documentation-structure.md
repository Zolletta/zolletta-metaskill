---
audience: ai, human
status: stable
skills: [review]
description: "Diátaxis documentation structure: tutorials, how-to, reference, explanation quadrants."
---

# ADR-0003: Diátaxis documentation structure

## Status

Accepted

## Context

Documentation without a framework accumulates into a flat folder with no clear purpose — a README grows into a catch-all, tutorials mix with reference, and readers cannot find what they need. The Diátaxis framework (diataxis.fr) organizes content into four quadrants by reader purpose: tutorials (learning), how-to guides (doing), reference (information), and explanation (understanding).

## Decision

Project documentation follows the Diátaxis framework with `tutorials/`, `how-to/`, `reference/`, `explanation/` quadrants.

The documentor skill checks compliance: each document sits in the correct quadrant directory, content matches the quadrant's purpose, and quadrant-specific completeness checks apply (e.g. tutorials need "What we will learn" + "Prerequisites"; how-to guides need "Prerequisites"). The staleness scorer detects quadrant directories and applies the appropriate required sections instead of README-style ones; non-English docs are handled via translated Diátaxis signpost headings (`documentation.diataxis_translations`).

## Consequences

**Positive:**

- Readers know where to look based on what they need; the documentor can apply quadrant-specific quality checks.
- The framework is established and externally documented — contributors can learn it independently.

**Negative:**

- Misplacement is a common documentor finding; some documents legitimately span quadrants and must pick a primary one.

**Neutral:**

- Diátaxis is a convention enforced only by the documentor's compliance checks — contributors can deviate with justification.
