---
audience: human, ai
status: stable
skills: [patterns]
---

# Split a God test class

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**
> **Language-agnostic**: the procedure below applies to any language. The script referenced is Python-specific; for other languages, follow the same grouping logic manually.

Split a test class that tests multiple SUTs (System Under Test) into per-SUT test files. The `src/zolletta_metaskill/scanners/test_splitter.py` script automates this — it groups test methods by prefix, creates a new test file per SUT, and writes them to a temp folder. The original file is never modified.

## Prerequisites

- A test class that tests 2+ different source classes (SUTs)
- Each SUT has its own source file
- The test class has 20+ test methods
- The `src/zolletta_metaskill/scanners/test_splitter.py` script from `src/zolletta_metaskill/scanners/`

## When NOT to split

- All test methods target the same SUT (the class is just large, not a God class)
- The SUTs are tiny helper classes that don't warrant separate test files
- The test methods are integration tests that test the interaction of multiple classes together

## Steps

```bash
# Step 1: auto-derive prefixes (no mapping needed)
python3 src/zolletta_metaskill/scanners/test_splitter.py <test_file>

# Step 2: review the proposed mapping, then split with --dry-run
python3 src/zolletta_metaskill/scanners/test_splitter.py <test_file> \
    --mapping '{"cache": "Cache", "extract_defaults": "DefaultsExtractor"}' \
    --dry-run

# Step 3: write the split files to .zolletta-metaskill/test_split/<filename>/
python3 src/zolletta_metaskill/scanners/test_splitter.py <test_file> \
    --mapping '{"cache": "Cache", "extract_defaults": "DefaultsExtractor"}'
```

## Options

| Option             | Default                                      | Description                                          |
|---|---|---|
| `<test_file>`      | (required)                                   | Path to the test .py file to split                   |
| `--mapping <json>` | (none)                                       | JSON file or inline JSON mapping prefix to SUT class |
| `--out <dir>`      | `.zolletta-metaskill/test_split/<filename>/` | Output directory                                     |
| `--class <name>`   | first test class                             | Name of the test class to split                      |
| `--dry-run`        | off                                          | Show the proposed split without writing files        |

## Workflow

1. Run without `--mapping` to auto-derive prefixes and see a proposed mapping
2. Adjust the mapping (prefix -> SUT class name) based on your knowledge
3. Run with `--dry-run` to verify the grouping
4. Run without `--dry-run` to write files to the temp folder
5. Review the generated files, adjust imports if needed
6. Move the files to the test directory and delete the original

## What gets copied to each split file

- Module docstring (with "split from" note)
- All imports from the original file
- `pytestmark` assignment (if present)
- Shared methods (fixtures, helpers, setup/teardown) — copied to every split file
- Test methods matching the SUT's prefix

## What the splitter does NOT do

- Remove unused imports from split files (review manually)
- Move the files to the final test directory (human reviews first)
- Delete the original file (human confirms the split is correct)
- Run the tests (human verifies the split files pass)

## Unmatched methods

Methods that don't match any prefix go to a `test__unmatched.py` file. Review these and add their prefixes to the mapping.

## See also

- [Scripts reference](../../reference/code/scripts.md) — full reference for all scanning scripts
- [General principles](../../explanation/code/general-principles.md) — God class detection procedure
