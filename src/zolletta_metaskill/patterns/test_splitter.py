#!/usr/bin/env python3
"""Split a God test class into per-SUT test files.

Takes a test file containing a large test class that tests multiple SUTs
(Systems Under Test) and splits it into separate test files, one per SUT.
The new files are written to a temp folder — the original is never modified.

SUT detection uses method-name prefix grouping:
  - Methods are grouped by their prefix after ``test_`` (e.g. ``test_cache_*``
    -> prefix ``cache``).
  - A mapping from prefix to SUT class name can be provided via ``--mapping``
    (a JSON file or inline JSON string).
  - Without a mapping, the script auto-derives prefixes from the first token
    after ``test_`` and prints a proposed mapping for the human to review.

Usage:
    python3 test_splitter.py <test_file> [--mapping <json>] [--out <dir>]
        [--class <TestClass>] [--dry-run]

Arguments:
    test_file       Path to the test .py file to split.

Options:
    --mapping <json>    JSON file or inline JSON string mapping prefix to SUT
                        class name. Example: {"cache": "Cache", "extract_defaults":
                        "DefaultsExtractor"}
    --out <dir>         Output directory (default: .zolletta-metaskill/test_split/<filename>/)
    --class <name>      Name of the test class to split (default: first test class
                        in the file, i.e. first ClassDef with test methods)
    --dry-run           Show the proposed split without writing any files.

Exit code: 0 on success, 1 on error.

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import cast


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def _load_mapping(mapping_arg: str | None) -> dict[str, str]:
    """Load prefix->SUT mapping from a file path or inline JSON string."""
    if not mapping_arg:
        return {}
    p = Path(mapping_arg)
    if p.exists():
        return cast(dict[str, str], json.loads(p.read_text(encoding="utf-8")))
    return cast(dict[str, str], json.loads(mapping_arg))


def _get_test_methods(class_node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return test methods (name starts with test_) from a class."""
    return [
        n for n in class_node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_")
    ]


def _get_shared_methods(class_node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return non-test methods (fixtures, helpers, setup/teardown) from a class."""
    return [
        n for n in class_node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("test_")
    ]


def _auto_derive_prefixes(
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef]
) -> dict[str, list[str]]:
    """Auto-derive prefix groups from method names.

    Uses the first token after ``test_`` as the prefix. Returns a dict
    mapping prefix to list of method names.
    """
    groups: dict[str, list[str]] = {}
    for m in methods:
        # Remove "test_" prefix, take everything up to the next "_"
        remainder = m.name[len("test_") :]
        prefix = remainder.split("_")[0] if "_" in remainder else remainder
        groups.setdefault(prefix, []).append(m.name)
    return groups


def _group_methods(
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    mapping: dict[str, str],
) -> dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Group test methods by prefix using the provided mapping.

    Returns a dict mapping SUT class name to list of method nodes.
    Methods that don't match any prefix go to "_unmatched".
    """
    groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for m in methods:
        remainder = m.name[len("test_") :]
        matched = False
        # Try longest-prefix match first
        for prefix in sorted(mapping.keys(), key=len, reverse=True):
            if remainder == prefix or remainder.startswith(prefix + "_"):
                sut = mapping[prefix]
                groups.setdefault(sut, []).append(m)
                matched = True
                break
        if not matched:
            groups.setdefault("_unmatched", []).append(m)
    return groups


def _unparse_node(node: ast.AST) -> str:
    """Convert an AST node back to source code."""
    return ast.unparse(node)


def _indent_block(source: str, indent: str = "    ") -> str:
    """Indent every line of a source block by one level (4 spaces)."""
    return "\n".join(indent + line if line.strip() else line for line in source.splitlines())


def _build_split_file(
    original_module: ast.Module,
    class_node: ast.ClassDef,
    sut_name: str,
    test_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    shared_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
    original_class_name: str,
) -> str:
    """Build the source code for a single split test file."""
    lines: list[str] = []

    # Module docstring (if present)
    if (
        original_module.body
        and isinstance(original_module.body[0], ast.Expr)
        and isinstance(original_module.body[0].value, ast.Constant)
        and isinstance(original_module.body[0].value.value, str)
    ):
        doc = original_module.body[0].value.value
        lines.append(f'"""{doc} — split from {original_class_name}."""')
        lines.append("")
    else:
        lines.append(f'"""Tests for {sut_name} — split from {original_class_name}."""')
        lines.append("")

    # Imports (copy all from original module)
    for node in original_module.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.append(_unparse_node(node))

    lines.append("")

    # pytestmark (if present in original)
    for node in original_module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    lines.append(_unparse_node(node))
                    lines.append("")

    # New class
    new_class_name = f"Test{sut_name}"
    lines.append(f"class {new_class_name}:")

    # Class docstring
    lines.append(f'    """Tests for {sut_name}, split from {original_class_name}."""')
    lines.append("")

    # Shared methods (fixtures, helpers) — copy to each split file
    for m in shared_methods:
        source = _unparse_node(m)
        lines.append(_indent_block(source))
        lines.append("")

    # Test methods for this SUT
    for m in test_methods:
        source = _unparse_node(m)
        lines.append(_indent_block(source))
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Entry point for the test splitter CLI."""
    parser = argparse.ArgumentParser(
        description="Split a God test class into per-SUT test files."
    )
    parser.add_argument(
        "test_file",
        help="Path to the test .py file to split",
    )
    parser.add_argument(
        "--mapping",
        default=None,
        help="JSON file or inline JSON string mapping prefix to SUT class name",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory (default: .zolletta-metaskill/test_split/<filename>/)",
    )
    parser.add_argument(
        "--class",
        dest="class_name",
        default=None,
        help="Name of the test class to split (default: first test class)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the proposed split without writing any files",
    )
    args = parser.parse_args()

    test_file = Path(args.test_file)
    if not test_file.exists():
        print(f"Error: test file '{test_file}' does not exist", file=sys.stderr)
        return 1

    source = test_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"Error: failed to parse {test_file}: {e}", file=sys.stderr)
        return 1

    # Find the target test class
    class_node = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if args.class_name and node.name == args.class_name:
            class_node = node
            break
        if not args.class_name:
            test_methods = _get_test_methods(node)
            if test_methods:
                class_node = node
                break

    if not class_node:
        cls_desc = f" '{args.class_name}'" if args.class_name else ""
        print(f"Error: no test class{cls_desc} found in {test_file}", file=sys.stderr)
        return 1

    test_methods = _get_test_methods(class_node)
    shared_methods = _get_shared_methods(class_node)

    if not test_methods:
        print(f"Error: class {class_node.name} has no test methods", file=sys.stderr)
        return 1

    print("=" * 70)
    print(f"TEST SPLITTER — {test_file.name}")
    print("=" * 70)
    print(f"\nClass: {class_node.name}")
    print(f"Test methods: {len(test_methods)}")
    print(f"Shared methods (fixtures/helpers): {len(shared_methods)}")

    # Load or auto-derive mapping
    mapping = _load_mapping(args.mapping)

    if not mapping:
        print("\nNo --mapping provided. Auto-deriving prefixes from method names:")
        auto = _auto_derive_prefixes(test_methods)
        for prefix, names in sorted(auto.items()):
            print(
                f"  {prefix}: {len(names)} methods -> "
                f"{names[:3]}{'...' if len(names) > 3 else ''}"
            )
        print("\nUse --mapping '{\"prefix\": \"SutClass\", ...}' to specify SUT names.")
        print("Example:")
        proposed = {p: _snake_to_pascal(p) for p in auto}
        print(f'  --mapping \'{json.dumps(proposed)}\'')
        print("\nRe-run with --mapping to split. Use --dry-run to preview first.")
        return 0

    # Group methods by SUT
    groups = _group_methods(test_methods, mapping)

    print(f"\nProposed split ({len(groups)} groups):")
    for sut, methods in sorted(groups.items()):
        if sut == "_unmatched":
            print(f"\n  _unmatched ({len(methods)} methods):")
            for m in methods:
                print(f"    {m.name}")
            print("    (No prefix matched — review and add to mapping)")
        else:
            print(f"\n  {sut} -> Test{sut} ({len(methods)} methods):")
            for m in methods:
                print(f"    {m.name}")

    if "_unmatched" in groups:
        unmatched = groups["_unmatched"]
        print(f"\n⚠  {len(unmatched)} methods unmatched. Add their prefixes to --mapping")
        print("   or they will be placed in a separate _unmatched test file.")

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return 0

    # Determine output directory
    if args.out:
        out_dir = Path(args.out)
    else:
        out_dir = Path(".zolletta-metaskill/test_split") / test_file.stem

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting split files to: {out_dir}/")

    for sut, methods in sorted(groups.items()):
        if sut == "_unmatched" and not methods:  # pragma: no cover
            continue
        filename = f"test_{_pascal_to_snake(sut)}.py"
        filepath = out_dir / filename
        content = _build_split_file(
            tree, class_node, sut, methods, shared_methods, class_node.name
        )
        filepath.write_text(content, encoding="utf-8")
        print(f"  {filename} ({len(methods)} test methods)")

    print(f"\nDone. {len(groups)} files written to {out_dir}/")
    print("Review the split files, then move them to replace the original.")
    print(f"Original file {test_file} was NOT modified.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
