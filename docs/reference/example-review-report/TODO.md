# TODO — Review 2026-08-06-19-41

- **Project:** zolletta-metaskill
- **Language:** python

## Detailed reports

For full findings (file paths, line numbers, impact, suggested fixes), see the specialist reports:

| Area            | Report file                                        |
|-----------------|----------------------------------------------------|
| Design patterns | [patterns.md](patterns.md)                         |
| Documentation   | [documentor.md](documentor.md)                     |
| Code style      | [python-code-style.md](python-code-style.md)       |
| Testing         | [python-testing-style.md](python-testing-style.md) |

## Dependency changes (under my control)

> No dependency changes required.

## Critical / blocking

> No critical or blocking issues found.

## High priority

- [ ] **3. [P1]** Fix 4 broken links in documentation
  - **Source**: documentor
  - **Files**: `docs/explanation/code/false-positive-prevention.md:77`, `docs/explanation/documentation/adr.md:81`, `docs/reference/reports.md:42`, `docs/reference/settings-schema.md:13`
  - **Problem**: 4 broken links found: empty anchor `[#]` in false-positive-prevention.md, missing file `adr/0003-adopt-microservices.md` in adr.md, wrong path `../../review/assets/summary_template.md` in reports.md, wrong path `../../setup/assets/settings.schema.json` in settings-schema.md.
  - **Fix**: Update each link to point to the correct file/anchor. See [documentor.md](documentor.md) for full details.

- [ ] **4. [P1]** Update 14 phantom API symbols in docs/reference/code/scripts.md
  - **Source**: documentor
  - **Files**: `docs/reference/code/scripts.md`, `docs/explanation/code/python/python-review-patterns.md`, `docs/adr/0007-language-neutral-engine-protocol.md`
  - **Problem**: 14 documented symbols no longer exist in source (renamed during refactoring): `test_file_pattern` → `test_glob_pattern_returns_glob`, `get_engine_for_file` → `get_for_file`, `get_engine` → `get`, `register_engine` → `register`, and 10 example/illustrative symbols. 3 missing parameter docs (`path`, `language`).
  - **Fix**: Update docs to use the new method names. Add missing parameter documentation. See [documentor.md](documentor.md) for full details.

## Medium priority

- [ ] **1. [P2]** Rename `ADRCli` to `ADRCLI` to satisfy the acronym-casing convention
  - **Source**: python-code-style
  - **Files**: `src/zolletta_metaskill/adr/adr_cli.py:21`
  - **Problem**: Class name `ADRCli` keeps the `CLI` acronym in mixed case (`Cli`). The configured acronym list includes `CLI`; the convention requires acronyms to stay fully uppercase in PascalCase class names (rule #3).
  - **Fix**: Rename the class to `ADRCLI`. The filename `adr_cli.py` already follows the "acronym lowercase in filename" convention and will then match the renamed class. Update the internal references in `adr_cli.py` (`ADRCli.build_parser`, `ADRCli.run`, `ADRCli.missing_docs_error`, `ADRCli.format_report`). See [python-code-style.md](python-code-style.md) for full details.

- [ ] **5. [P2]** Add missing README sections (Installation, License, Usage)
  - **Source**: documentor
  - **Files**: `README.md`
  - **Problem**: README.md is missing 3 recommended sections: Installation, License, and Usage. These are expected by the staleness scorer and are standard for open-source projects.
  - **Fix**: Add the missing sections to README.md. See [documentor.md](documentor.md) for full details.

- [ ] **6. [P2]** Fix 7 duplicate anchors in 5 documentation files
  - **Source**: documentor
  - **Files**: `docs/explanation/code/structural-conventions.md`, `docs/reference/code/scripts.md` (3), `docs/reference/documentation/workflows-and-tools.md`, `docs/reference/tool-messages.md`
  - **Problem**: 7 duplicate anchors found — headings generate the same anchor slug. 3 are from old script names in scripts.md.
  - **Fix**: Rename headings or use explicit anchor syntax. See [documentor.md](documentor.md) for full details.

## Low priority

- [ ] **2. [P3]** Rename confusing `test_glob_pattern_returns_glob` protocol method
  - **Source**: patterns
  - **Files**: `src/zolletta_metaskill/core/engine/language_engine.py:55`
  - **Problem**: The method name `test_glob_pattern_returns_glob` uses a `test_` prefix that implies a test method (not a production method), and `_returns_glob` leaks implementation detail into the name. Documentation refers to this as `test_file_pattern()`.
  - **Fix**: Rename to `test_file_pattern` or `test_glob_pattern` to remove the implementation leak and the confusing `test_` prefix connotation. See [patterns.md](patterns.md) for full details.

## Previous review status

All 10 items from the previous review (2026-08-06-18-29) are confirmed resolved:

| #  | Item                                                     | Status |
|----|----------------------------------------------------------|--------|
| 1  | Rename 577 test functions to naming convention           | ✅ Done |
| 2  | Rename 7 setup/ files to match class names               | ✅ Done |
| 3  | Extract ADROrchestrator CLI helpers into separate module | ✅ Done |
| 4  | Fix 10 manual E501 line-length violations                | ✅ Done |
| 5  | Replace 3 `time.sleep(0.01)` with deterministic mtime    | ✅ Done |
| 6  | Rename orphaned test file `test_distill_adrs.py`         | ✅ Done |
| 7  | Split multi-class test file `test_models.py`             | ✅ Done |
| 8  | Clean up 3 unused `__all__` exports in PHP scanners      | ✅ Done |
| 9  | Run `ruff format` and `ruff check --fix` for drift       | ✅ Done |
| 10 | Add `ADR` to the project's `acronyms` array              | ✅ Done |

No items carried forward — all previous findings were resolved.

---

_Generated by [zolletta-metaskill review](https://github.com/Zolletta/zolletta-metaskill/tree/main/skills/review/SKILL.md)_
