---
audience: human, ai
status: stable
skills: [documentor]
---

# Changelog Conventions

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-03-18

### Added

- New drift detection algorithm for renamed files

### Changed

- Improved staleness scoring weights

### Deprecated

- Old `--verbose` flag (use `--log-level` instead)

### Removed

- Python 3.7 support

### Fixed

- False positives in anchor validation

### Security

- Updated dependency to patch CVE-2026-XXXX
```

## Changelog Rules

- Every user-facing change gets an entry
- Group by type (Added, Changed, Deprecated, Removed, Fixed, Security)
- Most recent version first
- Include dates in ISO 8601 format
- Link version headers to git comparison URLs
- Keep an `[Unreleased]` section for in-progress changes
- Write for the user, not the developer ("Added search feature" not "Implemented ElasticSearch integration in SearchService")
