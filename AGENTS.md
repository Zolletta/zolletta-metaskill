---
audience: ai, human
status: stable
skills: [setup, review, patterns, documentor, grice, python-*, php-*]
---

# AGENTS.md

These are the conventions of this repository — one declaration per rule, so that new code is indistinguishable from the code around it.

## Context

Zolletta-metaskill is a review skill-set providing deterministic tools: the same project produces the same findings on every run, under any reviewer, with judgement reserved for what a machine cannot decide. The scanners under `skills/zolletta-metaskill/src/zolletta_metaskill/` are the product — and that gives this file one hard boundary:

- You **may** run the scanners in `src/` on your own work, as a reviewer would — that is dogfooding, and the tool already exists because the product needs it.
- You **may not** write a tool whose only purpose is enforcing a rule in this file — that belongs in your judgement, not in `src/`. The tell is a scanner no skill ever invokes. If you do end up writing such a check anyway, ask the human whether it is worth promoting into the skill's toolset as a reviewer tool before keeping it.

So a rule that "needs" enforcement is a signal to reconsider the rule, not to write the checker. The rules left unenforced on purpose are marked ❌ — take them more seriously, not less: a checked rule you break announces itself; an ❌ rule you break reaches the next reader with nothing having objected.

## Before any commit

Two groups, in this order. **Sensors** report findings and never fail — a finding is a rule you broke, so fix it. **Gates** fail the build, and run last to verify those fixes. All read roots, thresholds and toggles from `.zolletta-metaskill/settings.json`; none takes a positional path.

### Dogfooding

```bash
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/one_class_per_file_scanner.py    # classes.3, tests.2
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/naming_conventions_scanner.py   # classes.1
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/file_length_scanner.py          # classes.6
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/function_length_scanner.py      # functions.2
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/cyclomatic_complexity_scanner.py # functions.3
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/max_arguments_scanner.py        # functions.1
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/general/suppression_reason_scanner.py   # suppressions.1
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/python/acronym_casing_scanner.py        # classes.2
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/code_style/python/unused_all_exports_scanner.py    # imports.3
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/testing_style/general/test_structure_scanner.py    # tests.1
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/testing_style/python/test_naming_scanner.py        # tests.3
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py                   # documentation.4
uv run python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/unwrapped_prose_scanner.py      # documentation.1
```

### OS tools

`general.1` and `documentation.8` are absent here on purpose: they are syntactic, so `.githooks/pre-commit` fixes staged files instead of reporting — it appends the missing trailing newline and re-aligns staged markdown tables, then re-stages. What remains below is semantic: a finding means refactoring, which no hook can do for you.

```bash
# classes.4 — no module-level functions; expect no output
grep -rnE "^(async )?def " skills/zolletta-metaskill/src/ --include='*.py'
# classes.5 — no module-level constants; expect no output
grep -rnE "^[A-Z_][A-Z0-9_]* *(:[^=]+)?= " skills/zolletta-metaskill/src/ --include='*.py'
# imports.1 — no TYPE_CHECKING blocks; expect no output
grep -rn "TYPE_CHECKING" skills/zolletta-metaskill/src/ --include='*.py'
```

### Gates

Run these last — they verify that your sensor fixes were correct. A careless fix (a renamed test that now asserts nothing, a split class with a broken mirror) looks green to a sensor and red to `pytest`; that is the entire reason for the order.

```bash
uv run ruff check skills/zolletta-metaskill/src tests           # docstrings.1, imports.2, suppressions.1
uv run ruff format --check skills/zolletta-metaskill/src tests  # general.1 (.py)
uv run ty check .                     # functions.4
uv run mypy .                         # functions.4
uv run vulture . --min-confidence 80
uv run pytest -q                      # the guard test behind documentation.1
npx --yes markdownlint-cli2@0.23.3    # documentation.2
```

## Rules

Each rule has a stable id — `documentation.3`, `tests.2` — numbered within its area, so inserting a rule does not renumber the others. Quote the id when discussing one.

The glyph next to each rule id says what enforces it:

| Glyph | Meaning                                                                                                         |
|-------|-----------------------------------------------------------------------------------------------------------------|
| ✅     | a **scanner in `src/`** checks it — the skill verifying its own work                                            |
| 🔧    | something else does: an external tool, `.githooks/pre-commit`, a command in this file, or the shape of the code |
| ⚠️    | only partly                                                                                                     |
| ❌     | nothing does, and it is on you                                                                                  |

Nothing here runs by itself — ✅ and 🔧 are equally manual — and both answer without guessing.

The rules marked ❌ rest on this file alone.

### General

- `general.1` 🔧 — **Every file ends with an empty row and a newline.** The rule is POSIX, not stylistic: a file without a trailing newline breaks `git diff`, `cat`, and every POSIX tool that reads it. `ruff format` covers `.py` and `MD047` covers `.md`; for everything else `.githooks/pre-commit` is the check — it appends the newline to every staged text file rather than reporting, with `CHANGELOG.md` excluded since python-semantic-release regenerates it.

### Documentation

- `documentation.1` ✅ — **Prose paragraphs stay on a single line, never wrapped at a column width**, because markdown renders a newline as a space and the wrap buys nothing but diff noise. The rule binds accepted ADRs too — the one layout edit their immutability permits — and is unconditional here: a repo guard test in `pytest` fails on any wrapped paragraph whatever `documentation.check_unwrapped_prose` says. `MD013` is off on purpose, so no built-in rule demands the wrapping this forbids.
- `documentation.2` 🔧 — **Documentation must pass markdownlint.** The rule set lives in `.markdownlint.yaml` and the file globs in `.markdownlint-cli2.jsonc`.
- `documentation.3` ❌ — **Mermaid diagrams use the default theme only, with no fill and no background.** Nothing checks this, and no diagram exists in the repository today to check.
- `documentation.4` ✅ — **Links in `docs/` and `skills/` are repo-root-relative**, never a hardcoded `https://github.com/Zolletta/zolletta-metaskill/...` URL, because a relative link resolves both on GitHub and from a local checkout.
- `documentation.5` ❌ — **Architecture ADRs live in `docs/explanation/adr/architecture/`**, and activity records never enter the corpus.
- `documentation.6` ❌ — **An Accepted ADR is immutable and is replaced only by supersession.** Immutability governs content and status rather than layout: unwrapping the prose of an accepted ADR changes no decision, so it is done by editing in place.
- `documentation.7` ✅ — **When an ADR changes, the distiller cache is refreshed** — `PYTHONPATH=skills/zolletta-metaskill/src uv run python skills/zolletta-metaskill/src/zolletta_metaskill/adr/adr_client.py` — and reports no drift.
- `documentation.8` 🔧 — **Markdown tables carry the `markdown-table-prettify` layout** — every `|` in a column on the same character position — because the editor's format-on-save produces it and `.githooks/pre-commit` is the check — it re-aligns any staged table that drifts — so column alignment is a tool's output and never hand-counted padding.

### Commits

- `commits.1` 🔧 — **Commits follow Conventional Commits**, and the human-facing detail belongs in `CONTRIBUTING.md` rather than the commit message. An unparseable commit produces no changelog entry under `python-semantic-release`.

### Python

#### Classes

- `classes.1` ✅ — **A class mandates its filename** — `RawASTEngine` lives in `raw_ast_engine.py`, not the other way around; the match is case-insensitive because acronym casing is `classes.2`'s domain.
- `classes.2` ✅ — **An acronym in a class name stays fully uppercase.**
- `classes.3` ✅ — **Every file in `src/` defines exactly one class.**
- `classes.4` 🔧 — **No module-level functions.** Every function is a `@staticmethod` or an instance method on the class that owns it.
- `classes.5` 🔧 — **No module-level constants.** Constants are class attributes, so a name assigned at module scope means the class that should own it is missing.
- `classes.6` ✅ — **No file in `src/` exceeds 800 lines.**

#### Functions / Methods

- `functions.1` ✅ — **No function or method declares more than 5 parameters.** Positional-only, positional and keyword-only parameters count; `self`, `cls`, `*args`, `**kwargs` and PHP variadics do not.
- `functions.2` ✅ — **No function spans more than 125 lines**, measured from the signature through the end of the body, with the docstring included and decorators excluded.
- `functions.3` ✅ — **No branch is more complex than 12.** Counting follows ruff's `C901`: every `if`, `elif`, loop, `except` handler, non-catch-all `match` case and nested `def` adds one, while boolean operators, ternaries and comprehensions add none.
- `functions.4` 🔧 — **Every function and method signature is fully annotated** — parameters and return type. `mypy --strict` and `ty check` are the check.

#### Imports

- `imports.1` 🔧 — **No `if TYPE_CHECKING:` blocks.** If a name is needed only for annotation, `from __future__ import annotations` already makes every annotation lazy — import the name directly at module scope. A runtime-optional dependency is imported lazily inside the method that needs it.
- `imports.2` 🔧 — **Imports are absolute.** `from .conftest import x` is allowed in tests only; in `src/` a relative import breaks the ADR-0015 contract that `python3 <script>.py [--json]` runs from the project root. Ruff bans both forms with `ban-relative-imports = "all"`.
- `imports.3` ✅ — **Every name in `__all__` has a real importer.** `__all__` is a claim about the module's public surface, and the claim is checked rather than trusted — an export nothing imports is dead code that vulture cannot see.

#### Suppressions

- `suppressions.1` ✅ — **Every suppression carries its reason** — `type: ignore[code]`, `# noqa: RULE`, `# pragma: no cover` — so a reader can tell a deliberate exception from a leftover.
- `suppressions.2` ❌ — **A bare `# pragma: no mutate` suppresses only mutations on single-line statements.** Mutmut registers each mutant on its statement's first line and never sees comments nested inside a multi-line call, so a pragma on an `arg=` line inside `parser.add_argument(...)` does nothing. For multi-line statements wrap them in standalone `# pragma: no mutate start` / `# pragma: no mutate end` comment lines, and always verify with `mutmut show` that the mutant is actually gone.

#### CLI

- `cli.1` 🔧 — **The command line carries no configuration.** A tool exposes `[--json]` at most; everything else — roots, toggles, thresholds — comes from `.zolletta-metaskill/settings.json` through `ProjectConfig`, so the same checkout produces the same findings regardless of how the tool was invoked.
- `cli.2` 🔧 — **A scanner's entry point is `if __name__ == "__main__": sys.exit(Cls.main())`.**
- `cli.3` 🔧 — **A scanner is report-only**: it prints its findings to stdout (`T201` is ignored because stdout *is* the interface) and exits 0 even with findings, 1 only on usage errors.

#### Docstrings

- `docstrings.1` 🔧 — **Every module, class, function and method has a docstring**, in the repository's `Args:`/`Returns:` style. `__init__` methods and `__init__.py` files are exempt, as are all files under `tests/` — ruff's `D` rules are the check.

#### Structs

- `structs.1` ❌ — **A helper type is a `@dataclass(frozen=True)` in a `structs/` package**, one per file like every other class. Nothing checks this — the shape of the codebase is the convention.

### Tests

- `tests.1` ✅ — **Every source file has exactly one test file at the mirrored path** — `skills/zolletta-metaskill/src/zolletta_metaskill/<path>/<name>.py` pairs with `tests/<path>/test_<name>.py`, path for path.
- `tests.2` ✅ — **A test file holds one `Test*` class, named after the class it tests.** A second aspect gets its own file, named `test_<name>_<aspect>.py`.
- `tests.3` ✅ — **A test function is named `test_<unit>_<scenario>_<expected_outcome>`** and carries at least three segments after the prefix. A `parametrize` needs explicit `ids=` of the same shape, or the generated names become `test_naming` findings.
- `tests.4` ❌ — **A non-test file under `tests/` goes in `tests/fixtures/<subpath>/`, mirroring the source subpath, and is committed** — so that a change in output appears as a readable diff instead of a silent regeneration. The scanners ignore that directory: both enumerate through `ProjectConfig.iter_files(root, {".py"})`.
- `tests.5` ❌ — **Tests inside a `Test*` class are grouped under `# --- section ---` comments.**

#### Mutation testing

- `mutants.1` ❌ — **Case-variant literals are equivalent mutants on APFS.** Mutations like `"Makefile"` → `"MAKEFILE"` or `".zolletta-metaskill"` → `".ZOLLETTA-METASKILL"` cannot be killed on macOS because the filesystem is case-insensitive — silence them with `# pragma: no mutate` plus the reason, don't write a test that asserts platform-dependent behaviour.
- `mutants.2` ❌ — **Read the whole mutated expression before writing a test.** `x if cond or True` forces the same branch as the original, so it is an equivalent mutant; `and False` flips it. A test for an equivalent mutant passes on both versions and proves nothing — inspect first, then decide test vs pragma.
- `mutants.3` ❌ — **Substring asserts do not kill `XX…XX`/CAPS mutants.** The mutated text still contains the original substring. Assert on `splitlines()` membership, `startswith`/`endswith`, exact equality, or `count == N` for repeated lines.
- `mutants.4` ❌ — **When subagents fix mutants, the parent verifies once, at the end.** Per-mutant verification while children still work is an endless loop: they touch `mutants/` and each other's stats, so intermediate numbers lie anyway. Collect all child reports first, then run a single clean `mutmut run` to reconcile — that one result is the truth.
