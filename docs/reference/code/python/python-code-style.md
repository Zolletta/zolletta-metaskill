---
audience: human, ai
status: stable
skills: [python-*, review, patterns]
---

# Python Code Style

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Python-specific coding conventions and code-style workflow. These rules are the single source of truth — the Zolletta-metaskill review skills enforce them and only narrow behavior for the review context.

## 1. Environment setup

1.1. **Always run inside the dev container.**

1.2. **Re-sync the virtual environment before any style or type check.** The `.venv` is mounted from the host and may be stale or linked to the wrong interpreter.

```bash
docker exec <container_name> bash -c "cd /workspace && rm -rf .venv && uv sync"
```

1.3. **Always run tools through `uv run`.** Do not run bare `ruff`, `mypy`, or `ty` binaries. If `uv` is not present in the container, run Python tools directly (e.g. `pytest`, `ruff check`).

1.4. **Persist the presence/absence of `uv`** with `tokensave_record_decision` (tag: `environment`) so it is recalled in future sessions. Decisions are stored in the per-project DB, so the tag is scoped to the current project automatically.

## 2. Lint and format

2.1. **Lint and auto-fix:**

```bash
uv run ruff check --fix src tests
```

2.2. **Format and auto-fix:**

```bash
uv run ruff format src tests
```

2.3. **Address only the remaining issues** that `--fix` could not resolve manually. Do not document them as recommendations without attempting the fix first.

2.4. **Line length and target version** are read from `settings.json` (populated by setup from `pyproject.toml`). Do not hardcode fallback values.

2.5. **Linting rules to enforce:**

- Avoid B007 ruff errors by renaming unused variables to `_` (underscore)
- Avoid writing one directly after another (concatenate them): `with` clauses, `if` statements

## 3. Type checking

3.1. **Run `ty` first:**

```bash
uv run ty check --fix
```

3.2. **Then run `mypy`:**

```bash
uv run mypy src
uv run mypy .
```

3.3. **Mypy overrides work per module list.** Override blocks apply only to listed modules; unlisted modules use the global default (`ignore_missing_imports = false`).

3.4. **Resolve true type errors.** After `import-untyped`/`import-not-found` issues are explained, fix any remaining errors such as `Missing return statement`, `Class cannot subclass Any`, `untyped-decorator`, etc.

3.5. **`type: ignore` discipline:**

- Never use `# type: ignore` unless explicitly asked by the human.
- Exception: in tests that deliberately exercise edge cases by passing invalid values (e.g. `None` where a non-nullable type is expected, reassigning dunder methods on a `Mock`, or `json.load` returning `Any`), `# type: ignore[...]` is allowed. In these cases:
  1. Do not change the implementation method signatures to accommodate the test — the type mismatch is intentional.
  2. Add a comment on the line above explaining _why_ the ignore is necessary (what edge case is being tested).

  3.6. **ty inherits all mypy rules.** Any rule above applies identically when using `ty` as the type checker.

  3.7. **Mypy error codes to avoid:** `[no-any-return]`, `[no-untyped-def]`, `[no-untyped-call]`.

## 4. Verification order

Run quality checks in this exact order:

1. `uv run ruff check --fix src tests`
2. `uv run ruff format src tests`
3. `uv run ruff check --fix src tests`
4. `uv run ty check --fix`
5. `uv run mypy src`
6. `uv run mypy .`

## 5. Documentation

5.1. Keep `CONTRIBUTING.md` aligned with `pyproject.toml` (line length, target version, exact commands).

5.2. Public classes and functions should have Google-style docstrings. If missing, add them when touching the file for other reasons.

## 6. General conventions

- 1 class 1 file, 1 file one class
- A class must have a single responsibility
- Prefer imports at the beginning of the file instead of local imports
- Do not use `TYPE_CHECKING` blocks — restructure module boundaries instead.

## 7. Comments

Avoid pleonastic comments that restate the obvious action of the next line of code without adding useful context. Prefer self-explanatory names and remove comments that only narrate the code.

Avoid:

- `# Mark as aggregated` before `item.is_aggregated = True`
- `# Initialize the parser` before `self.parser = Parser()`
- `# Set the timeout` before `self.timeout = timeout`
- `# Create a copy` before `cleaned = original.copy()`
- `# Validate before writing` before `validate(data)`
- `# Ensure output directory exists` before `output_dir.mkdir(...)`

Prefer:

- Comments that explain _why_ a non-obvious choice was made.
- Comments that document edge cases, workarounds, or assumptions.
- Comments that keep multi-step algorithms readable when the steps themselves are not obvious from the names.

Example of a useful comment:

```python
# OS limit is 255; leave room for the generated code prefix and extension
MAX_FILENAME_LENGTH = 200
```

If the code already says what it does, the comment can be removed.

## 8. Coalesce consecutive nested statements

8.1. **Never write two consecutive nested `if` statements when a single `and` (or `or`) condition expresses the same intent.** Consecutive nesting adds visual noise, increases indentation depth, and obscures the real guard logic. Ruff's `SIM102` rule flags this automatically — fix it, don't suppress it.

```python
# Bad: two nested ifs that both filter the same value
if user is not None:
    if user.is_active:
        process(user)

# Good: single guard with `and`
if user is not None and user.is_active:
    process(user)
```

8.2. **Merge multiple `isinstance` calls on the same value into a single tuple-form call** (also satisfies `SIM101`):

```python
# Bad
if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
    ...

# Good
if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
    ...
```

8.3. **The same rule applies to consecutive nested `with` statements** — use a single `with` with multiple context managers:

```python
# Bad
with open(input_path) as fin:
    with open(output_path, "w") as fout:
        fout.write(fin.read())

# Good
with open(input_path) as fin, open(output_path, "w") as fout:
    fout.write(fin.read())
```

8.4. **Exception — "save previous state" guards must stay nested.** When the inner `if` flushes or saves _previous_ state before the outer block sets up _new_ state, the nesting is intentional and must not be coalesced. Coalescing would skip the save step.

```python
# Correct — DO NOT coalesce: the inner if saves the previous item's
# parameters before the outer block starts a new item.
if match:
    if current_item and current_item in items:
        items[current_item]["parameters"] = current_params  # save previous
    current_item = match.group(1)                            # start new
```

8.5. **Ruff enforcement:** Ruff `SIM` rules enforce this automatically — see [flake8-simplify](https://github.com/astral-sh/ruff/issues?q=flake8-simplify).

## 9. Prefer early returns over nested if/elseif

9.1. **Guard clauses (early return / early continue / early raise) keep the happy path at the top indentation level.** Deeply nested `if`/`elseif` chains force the reader to hold a growing stack of conditions in their head to understand the main flow. Invert the conditions and return early instead.

```python
# Bad — happy path buried inside nested conditions
def process_order(order: Order) -> Receipt:
    if order is not None:
        if order.is_paid:
            if order.items:
                receipt = build_receipt(order)
                if receipt is not None:
                    return receipt
            else:
                raise ValueError("empty order")
        else:
            raise ValueError("unpaid order")
    else:
        raise ValueError("None order")

# Good — guard clauses first, happy path last and flat
def process_order(order: Order) -> Receipt:
    if order is None:
        raise ValueError("None order")
    if not order.is_paid:
        raise ValueError("unpaid order")
    if not order.items:
        raise ValueError("empty order")
    receipt = build_receipt(order)
    if receipt is None:
        raise ValueError("receipt build failed")
    return receipt
```

9.2. **Rules of thumb:**

- Invert the condition and return/raise/`continue` immediately.
- Each guard is a single `if` at the top level — no `else`.
- The happy path lives at base indentation, never inside an `if`.
- Prefer `if not cond: return` over `if cond: ... else: return`.
- Apply the same pattern to `for` loops with `continue`.

  9.3. **Ruff enforcement:** `RET501` (unnecessary `yield None`), `RET502` (implicit `return None` after `if`), `RET503` (missing explicit `return`), and `RET505` (unnecessary `else` after `return`) all flag code that should use early returns. Add `"RET"` (flake8-return) to the `select` list in `pyproject.toml` to enable them.

## 10. Tests

- In tests do not repeat yourself. Search mocks, fixtures and test mixins first. If not present, if repetition will derive from implementing tests, first create fixtures/mixin/mocks as needed then implement tests.
- Load data from fixtures rather than hardcoding test data.
- Privilege data-driven parametrization.

## 11. No AAA comments in tests

11.1. **Do not annotate test bodies with `# Arrange`, `# Act`, `# Assert` (or `# Act + Assert`) comments.** The structure of a test is self-evident — setup comes first, the call is the action, `assert` is the assertion. These comments are visual noise that restates what the code already says.

```python
# Bad — comments that restate the code
def test_get_user_returns_user_when_found(self) -> None:
    """Arrange a user, Act by fetching, Assert the user is returned."""
    user = User(id=1, name="Alice")                                          # Arrange
    result = repo.get_user(1)                                                # Act
    assert result == user                                                    # Assert

# Good — let the code speak for itself
def test_get_user_returns_user_when_found(self) -> None:
    """A found user is returned by get_user."""
    user = User(id=1, name="Alice")
    result = repo.get_user(1)
    assert result == user
```

11.2. **Rules of thumb:**

- The docstring already describes the scenario — `test_<unit>_<scenario>_<expected>` and the first line tell the reader what is being tested.
- `assert` statements are self-documenting; they don't need a `# Assert` label.
- If a test needs an inline comment, write a comment that explains _why_ — not _what step_ you're on. `# macOS default FS is case-insensitive` is useful; `# Arrange` is not.
- This applies to all AAA-style annotations: `# Arrange`, `# Act`, `# Assert`, `# Act + Assert`, `# Arrange — ...`, `# Act — ...`, `# Assert — ...`.

## 12. Coverage

- Add `# pragma: no cover` to `sys.exit()` calls in CLI scripts and signal handlers (they terminate the process and are not testable in unit tests)
- Add `# pragma: no cover` to signal handler functions and `signal.signal`/`signal.alarm` calls (they are system-level operations not testable in unit tests)
- Add `# pragma: no cover` to `if __name__ == "__main__":` blocks (entry points are not testable in unit tests)
