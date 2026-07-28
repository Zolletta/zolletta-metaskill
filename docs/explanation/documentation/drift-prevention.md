---
audience: human, ai
status: stable
skills: [documentor]
---

# Drift Prevention Guide

Strategies and patterns for preventing documentation from falling out of sync with code.

---

## Documentation-Code Coupling Strategies

### 1. Proximity Coupling

Keep documentation physically close to the code it describes. The closer the docs are to the code, the more likely they are to be updated together.

- Module-level README files in each package directory
- Inline docstrings updated as part of function changes
- Architecture docs in the same directory as the system they describe

### 2. Reference Coupling

Documentation references specific code artifacts (function names, file paths, line numbers). When those artifacts change, tools can detect the broken references.

- Use exact function names in docs rather than paraphrasing
- Reference file paths relative to the repo root
- Include code snippets via file inclusion rather than copy-paste

### 3. Generation Coupling

Some documentation is generated directly from code, making drift impossible for the generated portions.

- API reference from docstrings (Sphinx, TypeDoc)
- CLI help text from argparse/click definitions
- Configuration docs from schema definitions
- Database schema docs from migration files

### 4. Process Coupling

Team processes that ensure docs are updated alongside code changes.

- PR templates with a "Documentation" checkbox
- Required doc review for any PR touching public API
- Documentation ownership assigned per module

---

## Automated Documentation Generation

### What to Generate

| Source            | Generated Doc     | Tool                              |
|-------------------|-------------------|-----------------------------------|
| Python docstrings | API reference     | Sphinx, pdoc, mkdocstrings        |
| TypeScript types  | API reference     | TypeDoc                           |
| OpenAPI spec      | REST API docs     | Swagger UI, Redoc                 |
| CLI argparse      | Command reference | argparse --help, click            |
| Database schema   | ERD / schema docs | SchemaSpy, dbdocs                 |
| Git log           | Changelog draft   | git-cliff, conventional-changelog |

### What NOT to Generate

- Tutorials (require narrative flow)
- Architecture overviews (require judgment)
- Getting started guides (require empathy for beginners)
- Migration guides (require understanding of breaking changes)
- Security advisories (require careful wording)

---

## CI/CD Documentation Gates

### Gate 1: Link Validation (Every PR)

```yaml
- name: Check documentation links
  run: python link_checker.py . --broken-only
  # Fails PR if any internal links are broken
```

### Gate 2: Staleness Check (Every PR touching code)

```yaml
- name: Check doc freshness
  run: python doc_staleness_scorer.py . --threshold 50
  # Fails if documentation score drops below 50
```

### Gate 3: API Validation (PRs touching src/)

```yaml
- name: Validate API docs
  run: python api_doc_validator.py src/ docs/api.md
  # Fails if documented API diverges from source
```

### Gate 4: Full Drift Report (Release branches)

```yaml
- name: Full drift analysis
  run: python drift_analyzer.py . --json > drift-report.json
  # Generates report as release artifact
```

### Recommended Pipeline

- **PR checks:** Gates 1 + 2 (fast, blocks merge)
- **Nightly:** Gates 1 + 2 + 3 (thorough, alerts team)
- **Release:** All gates + full report (comprehensive, blocks release)

---

## Review Checklist for Documentation Updates

### For Every Code PR

- [ ] Do any doc files reference changed functions, classes, or files?
- [ ] Are there new public functions/classes that need documentation?
- [ ] Were any documented functions removed or renamed?
- [ ] Are version strings still accurate?

### For Documentation PRs

- [ ] All links resolve (local files, anchors, cross-document)
- [ ] Code examples are syntactically correct
- [ ] Table of contents matches actual headings
- [ ] No placeholder or TODO text remains

### For Release PRs

- [ ] CHANGELOG updated with all user-facing changes
- [ ] README version strings match release version
- [ ] Migration guide written for breaking changes
- [ ] API docs regenerated from latest source

---

## Common Drift Patterns and Prevention

| Pattern           | Drift                          | Prevention                                         |
|-------------------|--------------------------------|----------------------------------------------------|
| Renamed function  | API docs reference old name    | Run `api_doc_validator.py` after refactors         |
| Moved file        | Links point to old path        | Run `link_checker.py` after file moves             |
| Removed parameter | Docs list removed params       | Run `api_doc_validator.py` after signature changes |
| New module        | No docs for new code           | Add docs in same PR as new code                    |
| Version bump      | Docs reference old version     | Run `doc_staleness_scorer.py` before release       |
| Refactored class  | Docs describe old structure    | Update architecture docs after refactors           |
| Deleted feature   | Docs reference removed feature | Delete docs when removing features                 |

---
