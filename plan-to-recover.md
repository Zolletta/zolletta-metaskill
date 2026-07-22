# Plan to Recover zolletta-metaskill

## Situation

The local working copy at `/Users/veronica.bolognesi/.agents/skills/zolletta-metaskill/` was wiped by another session and re-cloned from GitHub. The re-clone is at commit `a8edbe9` (Jul 17, 2026 — "feat: multi-language documentation support (1.1.0)"), which is the latest pushed commit.

**~17 uncommitted commits from two sessions of work were lost** (never pushed to remote). This plan reconstructs them.

## What was lost (summary of work across two sessions)

### Session 1 (prior thread, summary in `history_81c94bb82bc8491a.md`)

1. `ed1653b` — docs: organize quadrants into code/ and documentation/ subfolders (29 files)
2. `6858622` — docs: move operational-rules.md to reference/documentation/ (8 files)
3. `e2a9b27` — docs: move false-positive-prevention.md back to explanation/code/ (3 files)
4. `89ac3ee` — docs: move tool-messages.md up to reference/ root (9 files)
5. Graphify removal from code-exploration.md (12 mentions stripped, file rewritten tokensave-only)
6. Documentation-standards.md split into standards.md + readme.md + api.md + changelog.md + adr.md
7. Narrowing sentences updated (removed `~/.agents/rules/` subfolder references)
8. Frontmatter `skills: [all]` replaced with explicit full skill list in 3 files
9. `~/.agents/rules/code-exploration-rules.md` → symlink to `docs/reference/code/code-exploration.md`
10. `~/.agents/rules/documentation-rules.md` → symlink to `docs/explanation/documentation/standards.md`

### Session 2 (this thread, summary in `history_3ad7ec3127db41fc.md`)

11. `8780874` — docs: replace `skills: [all]` with explicit full skill list in 3 files
12. `12f4eb3` — docs: narrow `~/.agents/rules/` refs to `~/.agents/` and remove Pepita/CITE refs (10 files)
13. `7148c5a` — docs: make documentation directory configurable, remove `.backstage/` convention (11 files)
14. `9f13aca` — feat(setup): autodetect documentation directory during setup (`.backstage/` → `docs/` → default `docs/`)
15. Multiple commits for code/ subfolder restructuring (Python-specific files moved to `code/python/`, language-agnostic stayed at `code/` root)
16. `cdbbe10` — docs: add PHP review patterns (strategy autodiscovery, interface vs abstract)
17. `51035b5` — docs: extract structural-conventions.md from python-review-patterns.md
18. `42cd02b` — docs: extract general code-style and test-review how-tos, move split-god-test-class back to `code/` root
19. `6a1918d` — docs: fix table alignment in review-test-code.md
20. `0b2e36a` — docs: move scripts.md back to reference/code/ root (language-agnostic)
21. `33dad6d` / `20c1b56` — docs: generalize code docs, remove project-specific references (CITesterEngine, gitlab_manager, pytest --cov)
22. `151be0a` — docs: coalesce python-rules and python-code-style-rules into docs
23. `1a2b0fe` — docs: coalesce python.md into python-code-style.md
24. `600b8b0` — docs: coalesce tokensave-rules.md into docs/reference/code/tokensave.md

## Current state of the re-cloned repo

```
zolletta-metaskill/  (at a8edbe9, version 1.1.0)
├── .gitignore
├── CHANGELOG.md
├── README.md
├── SKILL.md
├── assets/
├── documentor/SKILL.md
├── external-review/SKILL.md
├── patterns/SKILL.md
├── python-code-style/SKILL.md
├── python-testing-patterns/SKILL.md
├── reference/                          ← flat, NOT under docs/
│   ├── code-exploration.md
│   ├── documentation_standards.md      ← not yet split
│   ├── general-principles.md
│   ├── python-review.md
│   ├── review-mode.md
│   ├── scripts.md
│   ├── settings-schema.md
│   └── tool-messages.md
├── review/SKILL.md
├── scripts/python/                     ← NOT under src/zolletta_metaskill/
│   ├── assets/
│   ├── scan_acronym_casing.py
│   ├── scan_class_metrics.py
│   ├── scan_dependency_inversion.py
│   ├── scan_interface_segregation.py
│   ├── scan_liskov_substitution.py
│   ├── scan_naming_conventions.py
│   ├── scan_one_class_per_file.py
│   ├── scan_open_closed.py
│   ├── scan_test_god_classes.py
│   ├── scan_test_naming.py
│   ├── scan_tests.py
│   ├── scan_unused_all_exports.py
│   ├── streamline_docstrings.py
│   └── test_splitter.py
└── setup/
    ├── SKILL.md
    └── assets/settings_template.json
```

### What the repo does NOT have (was added in lost commits)

- No `docs/` directory (Diátaxis docs structure)
- No `src/zolletta_metaskill/` package (scanners are in `scripts/python/`)
- No `tests/` directory (846 tests were added in lost commits)
- No `pyproject.toml` (was added to make it an installable package)
- No `documentation_directory` setting in `settings.json` schema
- No PHP review patterns
- No language-agnostic vs Python-specific code doc split
- No coalesced python-rules / tokensave-rules in docs

### Broken symlinks in `~/.agents/rules/`

All 5 symlinks are broken (point to `docs/` paths that don't exist yet):

- `code-exploration-rules.md` → `docs/reference/code/code-exploration.md` (BROKEN)
- `documentation-rules.md` → `docs/explanation/documentation/standards.md` (BROKEN)
- `python-code-style-rules.md` → `docs/reference/code/python/python-code-style.md` (BROKEN)
- `python-rules.md` → `docs/reference/code/python/python-code-style.md` (BROKEN)
- `tokensave-rules.md` → `docs/reference/code/tokensave.md` (BROKEN)

Standalone files (not affected):

- `commit-rules.md` (994 bytes, standalone)
- `communication-rules.md` (771 bytes, standalone)
- `environment-rules.md` (1105 bytes, standalone)

## Recovery plan

### Phase 0 — Secure the baseline

- [ ] 0.1. Verify the re-clone is clean: `git status` should show nothing to commit
- [ ] 0.2. Create a recovery branch: `git checkout -b recovery/docs-restructure`
- [ ] 0.3. Tag the baseline: `git tag baseline-a8edbe9`

### Phase 1 — Recreate the `docs/` Diátaxis structure

The biggest loss is the entire `docs/` directory. This was built incrementally across both sessions. Recreate it in this order:

- [ ] 1.1. Create the directory tree:

  ```
  docs/
  ├── tutorials/
  │   └── getting-started.md
  ├── how-to/
  │   ├── code/
  │   │   ├── python/
  │   │   │   ├── review-python-style.md
  │   │   │   └── review-python-tests.md
  │   │   ├── detect-god-classes.md
  │   │   ├── review-code-style.md
  │   │   ├── review-test-code.md
  │   │   ├── run-external-review.md
  │   │   └── split-god-test-class.md
  │   ├── documentation/
  │   │   └── review-documentation.md
  │   ├── install.md
  │   ├── run-full-review.md
  │   └── setup-project.md
  ├── explanation/
  │   ├── code/
  │   │   ├── php/
  │   │   │   └── php-review-patterns.md
  │   │   ├── python/
  │   │   │   └── python-review-patterns.md
  │   │   ├── false-positive-prevention.md
  │   │   ├── general-principles.md
  │   │   └── structural-conventions.md
  │   └── documentation/
  │       ├── adr.md
  │       ├── api.md
  │       ├── changelog.md
  │       ├── readme.md
  │       └── standards.md
  └── reference/
      ├── code/
      │   ├── python/
      │   │   └── python-code-style.md
      │   ├── code-exploration.md
      │   ├── review-mode.md
      │   ├── scripts.md
      │   └── tokensave.md
      ├── documentation/
      │   ├── drift-detection-tools.md
      │   ├── operational-rules.md
      │   └── scoring-and-categories.md
      ├── frontmatter.md
      ├── index.md
      ├── reports.md
      ├── settings-schema.md
      ├── subcommands.md
      └── tool-messages.md
  ```

- [ ] 1.2. Move existing `reference/*.md` files into `docs/reference/` (or their subfolder homes):
  - `reference/code-exploration.md` → `docs/reference/code/code-exploration.md` (rewrite: tokensave-only, no graphify)
  - `reference/documentation_standards.md` → split into `docs/explanation/documentation/standards.md` + `readme.md` + `api.md` + `changelog.md` + `adr.md`
  - `reference/general-principles.md` → `docs/explanation/code/general-principles.md`
  - `reference/python-review.md` → split into `docs/explanation/code/python/python-review-patterns.md` + `docs/how-to/code/python/review-python-style.md` + `docs/how-to/code/python/review-python-tests.md`
  - `reference/review-mode.md` → `docs/reference/code/review-mode.md`
  - `reference/scripts.md` → `docs/reference/code/scripts.md`
  - `reference/settings-schema.md` → `docs/reference/settings-schema.md`
  - `reference/tool-messages.md` → `docs/reference/tool-messages.md`

- [ ] 1.3. Create `docs/index.md` with the full tree and `skills: [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]` frontmatter

- [ ] 1.4. Update all SKILL.md files to point to new `docs/` paths

### Phase 2 — Apply the content changes from lost commits

These are the content transformations that were applied on top of the structure:

- [ ] 2.1. **Graphify removal**: rewrite `code-exploration.md` to be tokensave-only (remove comparison table, graphify decision branch, graphify links)
- [ ] 2.2. **Narrowing sentences**: update all "narrows down any eventual general rule" sentences to say `~/.agents/` instead of `~/.agents/rules/`
- [ ] 2.3. **Pepita/CITE removal**: replace `container_name: "cite"` → `"myproject"`, `testpaths: ["tests/pepita"]` → `["tests"]`, remove `cite` from `ENTRY_POINT_DEFAULTS` in scripts
- [ ] 2.4. **`.backstage/` → configurable `documentation_directory`**: add `documentation_directory` field to settings schema (default `docs/`), update setup autodetection (`.backstage/` if exists → `docs/` if exists → default `docs/`), update `settings_template.json` and `setup/SKILL.md`
- [ ] 2.5. **Code docs language split**: move Python-specific files to `code/python/`, keep language-agnostic at `code/` root. Create `code/php/php-review-patterns.md` (strategy autodiscovery, interface vs abstract, trait pattern)
- [ ] 2.6. **Extract structural-conventions.md** from python-review-patterns.md (one-class-per-file, test mirroring, naming, test God class splitting — language-agnostic)
- [ ] 2.7. **Extract general how-tos**: `review-code-style.md` (acronym casing, docstrings, always-on vs configurable) and `review-test-code.md` (coverage gap detection, scope boundary, configurable toggles) — language-agnostic
- [ ] 2.8. **Generalize code docs**: remove `CITesterEngine` references (→ `APIGateway` or generic), replace `pytest --cov` with "the test runner with coverage", remove "A Python codebase" from prerequisites, add language-agnostic admonitions to `split-god-test-class.md` and `review-mode.md`
- [ ] 2.9. **Frontmatter `skills: [all]` → explicit list** in `docs/index.md`, `docs/reference/subcommands.md`, `docs/reference/frontmatter.md`

### Phase 3 — Coalesce global rules into docs

- [ ] 3.1. Create `docs/reference/code/python/python-code-style.md` from `~/.agents/rules/python-rules.md` + `~/.agents/rules/python-code-style-rules.md` (merged into one file, generalized: container name from settings.json, no hardcoded mypy module list, no hardcoded line length)
- [ ] 3.2. Create `docs/reference/code/tokensave.md` from `~/.agents/rules/tokensave-rules.md` (available tools with params, seen_node_ids dedup, SQLite fallback, GitHub issue reporting, Explore agent prompt, per-project MCP config, maintenance)
- [ ] 3.3. Add link from `code-exploration.md` to `tokensave.md`
- [ ] 3.4. Update `docs/index.md` with the two new files

### Phase 4 — Recreate the `src/` package and `tests/`

The lost commits moved scanners from `scripts/python/` to `src/zolletta_metaskill/scanners/` and added 846 tests. This is the hardest part to recover because the test files are not in the GitHub baseline.

- [ ] 4.1. **Check if the other session preserved `src/` and `tests/`**: the other session may have a copy. Before recreating anything, ask the user to check.
- [ ] 4.2. **If `src/` and `tests/` are truly lost**: create `src/zolletta_metaskill/` package structure:

  ```
  src/zolletta_metaskill/
  ├── __init__.py
  ├── __version__.py
  └── scanners/
      ├── __init__.py
      ├── assets/
      │   └── acronyms.json
      ├── scan_acronym_casing.py
      ├── scan_class_metrics.py
      ├── scan_dependency_inversion.py
      ├── scan_interface_segregation.py
      ├── scan_liskov_substitution.py
      ├── scan_naming_conventions.py
      ├── scan_one_class_per_file.py
      ├── scan_open_closed.py
      ├── scan_test_god_classes.py
      ├── scan_test_naming.py
      ├── scan_tests.py
      ├── scan_unused_all_exports.py
      ├── streamline_docstrings.py
      └── test_splitter.py
  ```

  Move the scanner scripts from `scripts/python/` to `src/zolletta_metaskill/scanners/`, updating import paths.

- [ ] 4.3. **Recreate `pyproject.toml`**: the package needs a pyproject.toml with hatchling build, ruff config (line-length 100, target py312), mypy config, pytest config. This was added in lost commits.

- [ ] 4.4. **Recreate `tests/`**: the 846 tests are the hardest loss. The test files need to be rewritten from scratch or recovered from another source. Test categories:
  - `tests/scanners/test_*.py` — tests for each scanner script
  - `tests/documentor/test_*.py` — tests for documentor modules
  - Tests for settings schema, setup, etc.

- [ ] 4.5. **Recreate `scripts/.bump`**: the version bump script (updates version in pyproject.toml, `__version__.py`, all SKILL.md front-matter, setup_version doc row). This was committed as an untracked file that got included in a commit.

### Phase 5 — Recreate the installation scripts

- [ ] 5.1. Check what installation scripts existed (referenced in README and setup/SKILL.md)
- [ ] 5.2. Recreate `scripts/install.sh` or equivalent (symlinks skills into `~/.agents/skills/` or `~/.claude/skills/` and `~/.config/devin/skills/`)

### Phase 6 — Fix symlinks in `~/.agents/rules/`

- [ ] 6.1. Verify all 5 symlinks resolve after the docs are recreated:
  - `code-exploration-rules.md` → `docs/reference/code/code-exploration.md`
  - `documentation-rules.md` → `docs/explanation/documentation/standards.md`
  - `python-code-style-rules.md` → `docs/reference/code/python/python-code-style.md`
  - `python-rules.md` → `docs/reference/code/python/python-code-style.md`
  - `tokensave-rules.md` → `docs/reference/code/tokensave.md`
- [ ] 6.2. If any are still broken, recreate them with `ln -s`

### Phase 7 — Verify and commit

- [ ] 7.1. Run `uv run pytest tests/ -x -q` — should show 846 passed (once tests are recreated)
- [ ] 7.2. Run `uv run ruff check src tests` — should be clean
- [ ] 7.3. Run `uv run mypy src` — should be clean
- [ ] 7.4. Verify all cross-references in docs/ resolve (no broken links)
- [ ] 7.5. Verify all SKILL.md files point to correct docs/ paths
- [ ] 7.6. Commit in logical groups matching the original commit structure
- [ ] 7.7. **Push to remote** — `git push origin recovery/docs-restructure` or merge to main and push

## Priority order

1. **Phase 0** (secure baseline) — immediate
2. **Phase 1** (docs structure) — high, this is the bulk of the lost work and is fully reconstructable from the conversation history
3. **Phase 2** (content changes) — high, reconstructable from conversation history
4. **Phase 3** (coalesce rules) — high, the source files still exist in `~/.agents/rules/` as broken symlinks but the original content is in the conversation history
5. **Phase 4** (src/ and tests/) — medium, the scanner scripts exist in `scripts/python/` and can be moved; the tests are the real loss
6. **Phase 5** (install scripts) — low, check if they existed in the baseline
7. **Phase 6** (fix symlinks) — automatic once docs/ exists
8. **Phase 7** (verify and push) — final

## Recoverable sources found

### Rules files — copies in ci-tester-engine and ci-packages

Both `/Users/veronica.bolognesi/src/gitlab.pepita.io/pepita/automation/ci-tests/ci-tester-engine/rules/` and `/Users/veronica.bolognesi/src/gitlab.pepita.io/pepita/automation/ci-packages/rules/` have copies of the original rules files (before they were turned into symlinks):

- `commit-rules.md` ✅
- `communication-rules.md` ✅
- `documentation-rules.md` ✅ (original, before split into standards.md + readme.md + api.md + changelog.md + adr.md)
- `environment-rules.md` ✅
- `python-rules.md` ✅ (original, before coalescing into python-code-style.md)
- `tokensave-rules.md` ✅ (original, before coalescing into tokensave.md)

**NOT in either copy**: `python-code-style-rules.md` — this file was unique to `~/.agents/rules/` (a CI Tester Engine-specific code style workflow). The full content was read in this conversation's history (193 lines) and can be recovered from there.

## What is NOT recoverable without another source

- **The 846 test files** — these were written from scratch in the lost commits and are not in the GitHub baseline. They need to be either:
  - Recovered from the other session's working copy (if it still has them)
  - Rewritten from scratch (significant effort)
  - Recovered from a Time Machine backup
- **The exact content of every doc file** — the conversation history has summaries and snippets, but not the full final content of each file. The docs will need to be rewritten based on the descriptions in the conversation history. The content will be close but may not be byte-identical to what was lost.
- **`python-code-style-rules.md`** — recoverable from this conversation's history (the full 193-line file was read and is in the tool output), but not from any filesystem copy.

## Notes

- The `scripts/.bump` file was an untracked file that got accidentally committed in `20c1b56`. It's a version bump script that updates version across pyproject.toml, `__version__.py`, all SKILL.md files, and the setup_version doc row.
- The `src/zolletta_metaskill/` package structure was added to make the scanners importable as a Python package (for the 846 tests). In the baseline, scanners are standalone scripts in `scripts/python/`.
- The `documentation_directory` setting was added to make the docs directory configurable (default `docs/`, backward compat with `.backstage/`).
