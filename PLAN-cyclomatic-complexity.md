# Plan — Add cyclomatic complexity sensor (issue #45)

Add a deterministic cyclomatic-complexity sensor for Python and PHP — a language-aware scanner mirroring `file_length_scanner.py` — plus settings keys, a ruff config mirror, skill docs, and reference docs.

Issue: https://github.com/Zolletta/zolletta-metaskill/issues/45

## Context

Issue #45 asks for a cyclomatic-complexity sensor, one of the "low-hanging-fruit" maintainability rules from Martin Fowler's *Maintainability sensors for coding agents*. Default branch is `main` (no `master`).

The in-flight `feat/file-length-sensor` branch is the sibling sensor and defines the exact touch-points for a new configurable sensor. This work should branch off `origin/main` as `feat/cyclomatic-complexity-sensor` (or off the file-length branch if preferred — see risks).

## Confirmed design decisions

- **Mechanism**: language-aware stdlib/tree-sitter scanner + ruff config mirror. Python counted via stdlib `ast`; PHP via `PHPEngine.parse_raw` (tree-sitter-php, optional dep — degrades to a stderr warning, matching existing PHP scanners). The issue's claim that PHPStan has a `CyclomaticComplexity` rule is inaccurate — PHPStan core has none; only third-party extensions / PHPMD do, and PHPMD isn't among detected tools.
- **Report style**: findings at threshold — functions above `max_cyclomatic_complexity` become `medium` findings (`fix_type="manual"`), like `file_length`. Legit cases (parsers, state machines) → raise threshold or use `--exclude`.
- **Rule numbers**: Python **#23**, PHP **#35** — avoids colliding with #21/#34 taken by the file-length branch, so both can merge cleanly.
- **This repo's own `pyproject.toml`**: do NOT add `C901` to its `select` — `ruff check --select C901 src/ tests/` currently reports **34 violations** (mostly `main()` argparse blocks). Dogfooding is a separate cleanup decision.
- `settings_template.json` and report templates need no changes (generic).

## Implementation steps

1. **New branch** `feat/cyclomatic-complexity-sensor` off `origin/main`.

2. **New scanner** `src/zolletta_metaskill/code_style/general/cyclomatic_complexity_scanner.py` (~350 lines, mirroring `file_length_scanner.py`):
   - `DEFAULT_MAX_COMPLEXITY = 10`; self-contained copies of `_load_settings`/`resolve_extensions`/`_git_files`/`_iter_files` helpers (file-length branch is unmerged — can't import from it; dedupe in a later refactor).
   - Python path: `ast.parse`, compute complexity per `FunctionDef`/`AsyncFunctionDef` (top-level, methods, nested) = 1 + decision points matching ruff C901/mccabe semantics (`If` incl. elif, `For`/`AsyncFor`, `While`, `ExceptHandler`, `BoolOp` arms, `IfExp`, `match_case`, comprehension clauses). Nested defs counted independently — their bodies excluded from the enclosing function's count.
   - PHP path: `EngineRegistry` + `PHPEngine.parse_raw`; walk each `function_definition`/`method_declaration`/closure counting `if_statement`, `elseif`, `for`, `foreach`, `while`, `do`, `case_statement`, `match` arms, `catch_clause`, `conditional_expression` (ternary), `&&`/`||`/`??`. `except (OSError, ImportError)` → skip with warning when tree-sitter-php missing.
   - `scan_file` → `Finding`s: `category="cyclomatic_complexity"`, `severity="medium"`, `line` = def lineno, `fix_type="manual"`, description `Function '<name>' has cyclomatic complexity N (max M)`.
   - CLI identical in shape to file_length: `directory`, `--max-complexity N`, `--settings`, `--exclude`, `--strict`, `--json`, `--skip`.

3. **Tests** `tests/code_style/general/test_cyclomatic_complexity_scanner.py` — mirror `test_file_length_scanner.py` structure; PHP tests guarded by `pytest.mark.skipif(not _have_tree_sitter_php())` (same pattern as `tests/patterns/php/`).

4. **Schema** `skills/setup/assets/settings.schema.json`:
   - `python_code_style` + `php_code_style`: add required keys `check_cyclomatic_complexity` (bool, default `true`) and `max_cyclomatic_complexity` (int, min 1, default `10`).
   - `python_tools_ruff`: add required `max_complexity` (`["integer","null"]`, min 1, default `null`) — mirrors `[tool.ruff.lint.mccabe] max-complexity`.

5. **Settings docs** `docs/reference/settings-schema.md`: example JSON blocks, `python.tools.ruff` object row (line ~208), python code_style table (~line 229), php code_style table (~line 289). Note: setup seeds `python.code_style.max_cyclomatic_complexity` from `[tool.ruff.lint.mccabe]` when present, else 10. (`skills/setup/SKILL.md` step 6.5 defers the field list to this doc — likely no change needed; verify.)

6. **`skills/python-code-style/SKILL.md`**: add `cyclomatic_complexity_scanner` to execution-protocol script list; Table 2 row `#23 Structure | Cyclomatic complexity limit | check_cyclomatic_complexity, max_cyclomatic_complexity | true, 10`; detailed rule `#23` section under Structure with enforcement command, interplay with project-side `C901`/`[tool.ruff.lint.mccabe]`, exceptions guidance, and the "scanner is the single source of truth" note.

7. **`skills/php-code-style/SKILL.md`**: Table row `#35 Structure | Cyclomatic complexity limit`; `### Structure (#35)` section noting PHPStan/Psalm lack a built-in McCabe rule so the scanner (tree-sitter) is the deterministic check; same enforcement command.

8. **`docs/reference/code/scripts.md`**: new `cyclomatic_complexity_scanner.py` section (options table, exceptions note).

9. **`docs/reference/code/scripts-first-protocol.md`**: add `cyclomatic_complexity_scanner.py` rows to the `python-code-style` and `php-code-style` script tables — `cache/cyclomatic_complexity.txt`, condition `check_cyclomatic_complexity`.

10. **How-tos**: `docs/how-to/code/review-code-style.md` (new subsection + configurable list), `docs/how-to/code/python/review-python-style.md` (section + settings example). No PHP how-to exists.

11. **`docs/explanation/code/general-principles.md`**: in "Function Size Guidelines" (~line 413), add the deterministic-enforcement blurb with the scanner command, same style as the file-length addition.

## Files to modify

- `src/zolletta_metaskill/code_style/general/cyclomatic_complexity_scanner.py` — **new**
- `tests/code_style/general/test_cyclomatic_complexity_scanner.py` — **new**
- `skills/setup/assets/settings.schema.json` — new code_style keys + `python_tools_ruff.max_complexity`
- `docs/reference/settings-schema.md` — schema doc mirror
- `skills/python-code-style/SKILL.md` — rule #23
- `skills/php-code-style/SKILL.md` — rule #35
- `docs/reference/code/scripts.md` — scanner reference
- `docs/reference/code/scripts-first-protocol.md` — script tables
- `docs/how-to/code/review-code-style.md`, `docs/how-to/code/python/review-python-style.md` — how-tos
- `docs/explanation/code/general-principles.md` — Function Size blurb

## Verification

- `uv run pytest tests/code_style/general/test_cyclomatic_complexity_scanner.py -v`
- Cross-validate vs ruff: `python3 src/zolletta_metaskill/code_style/general/cyclomatic_complexity_scanner.py src --max-complexity 10 --json` should flag the same ~34 functions as `uv run ruff check --select C901 src/ tests/` — compare per-function numbers.
- `uv run pytest` (full suite), `uv run ruff check src/ tests/`, `uv run mypy src/`, `uv run ty check`.
- Validate settings schema JSON parses: `python3 -m json.tool skills/setup/assets/settings.schema.json`.

## Risks / considerations

- **McCabe parity**: counting rules must match ruff C901 (boolop arms, comprehensions, match cases, nested-def isolation) — the ruff cross-check in verification catches drift.
- **Settings compat**: new required keys make old `settings.json` files schema-stale until re-setup — same trade-off the file-length branch accepted; setup guard handles refresh.
- **Parallel-branch conflicts**: scanner is self-contained (no import from file-length branch); doc tables are the only likely trivial merge conflicts, mitigated by non-colliding rule numbers.
- **PHP without tree-sitter**: sensor produces no findings — mitigated by a stderr warning; documented in SKILL.md.
