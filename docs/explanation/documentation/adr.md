---
audience: human, ai
status: stable
skills: [documentor]
---

# Architecture Decision Records (ADRs)

## ADR Format

```markdown
# ADR-NNN: Title

## Status

Proposed | Accepted | Deprecated | Superseded by ADR-NNN

## Context

What is the issue that we are seeing that is motivating this decision?

## Decision

What is the change that we are proposing and/or doing?

## Consequences

What becomes easier or harder to do because of this change?
```

## ADR Best Practices

- Number sequentially, never reuse numbers
- Keep each ADR focused on a single decision
- Record the date of the decision
- Link to related ADRs
- Update status when superseded (do not delete old ADRs)
- Store in `docs/adr/` or `docs/decisions/`
- Include ADR index in project documentation
