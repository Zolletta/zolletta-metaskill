# CHANGELOG

<!-- version list -->

## v3.0.0 (2026-09-26)

### Bug Fixes

- **adr**: Nested ADR dirs, file-relative links, amended statuses
  ([#59](https://github.com/Zolletta/zolletta-metaskill/pull/59),
  [`a4117f6`](https://github.com/Zolletta/zolletta-metaskill/commit/a4117f69655d5cc4b70d53a1fb74eec3f7f11233))

### Features

- **install**: Manifest-driven install with git-tag clone
  ([#59](https://github.com/Zolletta/zolletta-metaskill/pull/59),
  [`a4117f6`](https://github.com/Zolletta/zolletta-metaskill/commit/a4117f69655d5cc4b70d53a1fb74eec3f7f11233))

### Refactoring

- **skills**: Rename sub-skill files to SUBSKILL.md
  ([#59](https://github.com/Zolletta/zolletta-metaskill/pull/59),
  [`a4117f6`](https://github.com/Zolletta/zolletta-metaskill/commit/a4117f69655d5cc4b70d53a1fb74eec3f7f11233))

### Breaking Changes

- **skills**: Subcommand instruction files are SUBSKILL.md, not SKILL.md; all
  skills/zolletta-metaskill-*/ paths changed accordingly.


## v2.0.0 (2026-09-22)

### Code Style

- Apply ruff format; cover settings-merge else branches in tests
  ([#54](https://github.com/Zolletta/zolletta-metaskill/pull/54),
  [`5135cba`](https://github.com/Zolletta/zolletta-metaskill/commit/5135cbaadef94fc631b59add685d6285b9a58e3a))

### Refactoring

- **scripts**: Standardize script CLI on settings.json-driven config
  ([#54](https://github.com/Zolletta/zolletta-metaskill/pull/54),
  [`5135cba`](https://github.com/Zolletta/zolletta-metaskill/commit/5135cbaadef94fc631b59add685d6285b9a58e3a))

- **scripts**: Standardize script CLI on settings.json-driven co…
  ([#54](https://github.com/Zolletta/zolletta-metaskill/pull/54),
  [`5135cba`](https://github.com/Zolletta/zolletta-metaskill/commit/5135cbaadef94fc631b59add685d6285b9a58e3a))


## v1.3.0 (2026-09-20)

### Bug Fixes

- **code-style**: Ignore null language sections in settings.json
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

### Features

- **code-style**: Add file length sensor
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

- **code-style**: Settings.json drives file-length sensor
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

### Refactoring

- **code-style**: Drop --exclude flag from file length scanner
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

- **code-style**: Drop --max-lines and --language flags
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

- **code-style**: Drop --settings and --skip flags
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

- **code-style**: Drop --strict flag from file length scanner
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

- **code-style**: Language-aware file length sensor
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))

### Testing

- **code-style**: Bring file length scanner to 100% coverage
  ([#53](https://github.com/Zolletta/zolletta-metaskill/pull/53),
  [`55394f3`](https://github.com/Zolletta/zolletta-metaskill/commit/55394f3c747e1bf459e2674fe3f648487c910465))


## v1.2.2 (2026-09-15)

### Bug Fixes

- **security**: Gitpython security fixes
  ([#52](https://github.com/Zolletta/zolletta-metaskill/pull/52),
  [`f8f81ed`](https://github.com/Zolletta/zolletta-metaskill/commit/f8f81ed239689a1a45f9073aa746769d87d24eea))


## v1.2.1 (2026-08-24)

### Bug Fixes

- Address review findings (broken links, DIP, dead code, scanner false positives)
  ([#31](https://github.com/Zolletta/zolletta-metaskill/pull/31),
  [`7958409`](https://github.com/Zolletta/zolletta-metaskill/commit/79584095d11d32a368b85347e1b5a9ddac3a0167))

- Replace type-unsafe assertions in test_acronym_casing_scanner
  ([#31](https://github.com/Zolletta/zolletta-metaskill/pull/31),
  [`7958409`](https://github.com/Zolletta/zolletta-metaskill/commit/79584095d11d32a368b85347e1b5a9ddac3a0167))

### Continuous Integration

- Avoid duplicate test runs on PR branches
  ([#31](https://github.com/Zolletta/zolletta-metaskill/pull/31),
  [`7958409`](https://github.com/Zolletta/zolletta-metaskill/commit/79584095d11d32a368b85347e1b5a9ddac3a0167))

- Bump actions/cache from v4 to v5 (Node.js 24)
  ([#31](https://github.com/Zolletta/zolletta-metaskill/pull/31),
  [`7958409`](https://github.com/Zolletta/zolletta-metaskill/commit/79584095d11d32a368b85347e1b5a9ddac3a0167))

### Refactoring

- Scripts-first protocol + new run directory structure
  ([#31](https://github.com/Zolletta/zolletta-metaskill/pull/31),
  [`7958409`](https://github.com/Zolletta/zolletta-metaskill/commit/79584095d11d32a368b85347e1b5a9ddac3a0167))

### Testing

- Close coverage gaps to reach 100% ([#31](https://github.com/Zolletta/zolletta-metaskill/pull/31),
  [`7958409`](https://github.com/Zolletta/zolletta-metaskill/commit/79584095d11d32a368b85347e1b5a9ddac3a0167))


## v1.2.0 (2026-08-24)


## v1.1.4 (2026-08-24)


## v1.1.3 (2026-08-24)


## v1.1.2 (2026-08-24)

### Bug Fixes

- **docs**: Fix broken links for mkdocs --strict build
  ([`14aa3a2`](https://github.com/Zolletta/zolletta-metaskill/commit/14aa3a2138407c776d3e2225bada5e068d7fe966))


## v1.1.1 (2026-08-24)

### Bug Fixes

- **docs-pages**: Install mkdocs as tool with material + plugin as deps
  ([`6adee5e`](https://github.com/Zolletta/zolletta-metaskill/commit/6adee5e0180a7d3df7536eb1d1b81f8f4a67af4b))


## v1.1.0 (2026-08-24)

### Features

- **docs**: Add git-revision-date-localized plugin for last-updated dates
  ([`8bf3cf8`](https://github.com/Zolletta/zolletta-metaskill/commit/8bf3cf8289d05b5cddeed6eeded63643900acae5))

### Refactoring

- **ci**: Restructure workflows + add setup composite action + docs
  ([`e1c52ff`](https://github.com/Zolletta/zolletta-metaskill/commit/e1c52ffb9b07e3180396a23b676b313a6b0fe75d))


## v1.0.1 (2026-08-24)

### Bug Fixes

- **ci**: Install uv in docs-pages workflow + add docs/release badges to README
  ([`fe6572e`](https://github.com/Zolletta/zolletta-metaskill/commit/fe6572e559f58be316fc3a65e7d41d5c68953a46))


## v1.0.0 (2026-08-24)

- Initial Release
