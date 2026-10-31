# Playground — deliberately bad code for scanner dogfooding

Everything in this directory is **intentionally defective**. It is a self-contained fake project (Python + PHP sources, tests, docs, and its own `.zolletta-metaskill/settings.json`) that exists so every metaskill scanner can be pointed at it and report findings on demand. Do not fix anything in here — a "clean" playground is a broken one.

## Running the scanners

Scanners resolve `.zolletta-metaskill/settings.json` relative to the working directory, so run them **from inside `playground/`**:

```bash
cd playground
../.venv/bin/python ../src/zolletta_metaskill/code_style/general/file_length_scanner.py
```

Any scanner script under `../src/zolletta_metaskill/` works the same way. `expected-findings.md` maps each file to the scanners and rule ids it is meant to trigger — every file also carries a `# expected findings:` header comment.

## Convention

- `src/playground/` — bad Python (the `playground` package exists so `python.paths.package` auto-detection works for the mirror scanners)
- `tests/` — bad Python tests plus one clean mirror test
- `src-php/`, `tests-php/` — bad PHP, wired up by `composer.json` psr-4 mappings mirrored in settings.json
- `docs/` — wrapped prose, absolute GitHub links, a broken relative link, a misplaced ADR

## Known blind spots

- **Trailing newline** — the repo's `general.1` check requires every tracked file to end with a newline, so the playground cannot demonstrate a missing-newline defect without breaking a repo gate.
- **`tests.4` / `documentation.5`/`documentation.6`** — unenforced-by-design rules; `tests/helper.py` and `docs/explanation/adr/ADR-001.md` exist as illustrations, not as scanner findings. The misplaced ADR is simply invisible to ADR tooling, because `documentation.adrs` points at `explanation/adr/architecture`.
- **markdownlint** — `.markdownlint-cli2.jsonc` globs only cover `docs/**`, root `*.md`, and `skills/**`, so playground markdown is lint-exempt. The unwrapped-prose repo guard test excludes `playground/` explicitly.
- **`mypy` / `ty`** — both type-checker gates exclude `playground/` in `pyproject.toml`; the bad signatures would otherwise fail the build.
- **`functions.4`** (annotation coverage) is gated by `mypy`/`ty`, which never see this tree — the unannotated signatures here are illustrative only.
