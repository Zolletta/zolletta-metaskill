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
    python3 test_splitter.py <test_file> [--mapping <json>]
        [--class <TestClass>] [--dry-run] [--json]

Arguments:
    test_file       Path to the test .py file to split.

Options:
    --mapping <json>    JSON file or inline JSON string mapping prefix to SUT
                        class name. Example: {"cache": "Cache", "extract_defaults":
                        "DefaultsExtractor"}
    --class <name>      Name of the test class to split (default: first test class
                        in the file, i.e. first ClassDef with test methods)
    --dry-run           Show the proposed split without writing any files.
    --json              Output the proposed split as JSON.
    Output directory is ``<runs_dir>/test_split/<filename>/`` from
    ``settings.json`` (``runs_dir``, default ``.zolletta-metaskill``).

Exit code: 0 on success, 1 on error.

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, cast

from zolletta_metaskill.core.project_config import ProjectConfig


class TestSplitter:
    """Split a God test class into per-SUT test files."""

    @staticmethod
    def _pascal_to_snake(name: str) -> str:
        """Convert PascalCase to snake_case."""
        return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")

    @staticmethod
    def _snake_to_pascal(name: str) -> str:
        """Convert snake_case to PascalCase."""
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def _load_mapping(mapping_arg: str | None) -> dict[str, str]:
        """Load prefix->SUT mapping from a file path or inline JSON string."""
        if not mapping_arg:
            return {}
        p = Path(mapping_arg)
        if p.exists():
            return cast(dict[str, str], json.loads(p.read_text(encoding="utf-8")))
        return cast(dict[str, str], json.loads(mapping_arg))

    @staticmethod
    def _get_test_methods(class_node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Return test methods (name starts with test_) from a class."""
        return [
            n
            for n in class_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
        ]

    @staticmethod
    def _get_shared_methods(
        class_node: ast.ClassDef,
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Return non-test methods (fixtures, helpers, setup/teardown) from a class."""
        return [
            n
            for n in class_node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("test_")
        ]

    @staticmethod
    def _auto_derive_prefixes(
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
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

    @staticmethod
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

    @staticmethod
    def _unparse_node(node: ast.AST) -> str:
        """Convert an AST node back to source code."""
        return ast.unparse(node)

    @staticmethod
    def _indent_block(source: str, indent: str = "    ") -> str:
        """Indent every line of a source block by one level (4 spaces)."""
        return "\n".join(indent + line if line.strip() else line for line in source.splitlines())

    @staticmethod
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
                lines.append(TestSplitter._unparse_node(node))

        lines.append("")

        # pytestmark (if present in original)
        for node in original_module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        lines.append(TestSplitter._unparse_node(node))
                        lines.append("")

        # New class
        new_class_name = f"Test{sut_name}"
        lines.append(f"class {new_class_name}:")

        # Class docstring
        lines.append(f'    """Tests for {sut_name}, split from {original_class_name}."""')
        lines.append("")

        # Shared methods (fixtures, helpers) — copy to each split file
        for m in shared_methods:
            source = TestSplitter._unparse_node(m)
            lines.append(TestSplitter._indent_block(source))
            lines.append("")

        # Test methods for this SUT
        for m in test_methods:
            source = TestSplitter._unparse_node(m)
            lines.append(TestSplitter._indent_block(source))
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def main() -> int:
        """Entry point for the test splitter CLI."""
        args = TestSplitter._build_parser().parse_args()

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

        class_node = TestSplitter._find_target_class(tree, args.class_name)
        if not class_node:
            cls_desc = f" '{args.class_name}'" if args.class_name else ""
            print(f"Error: no test class{cls_desc} found in {test_file}", file=sys.stderr)
            return 1

        test_methods = TestSplitter._get_test_methods(class_node)
        shared_methods = TestSplitter._get_shared_methods(class_node)

        if not test_methods:
            print(f"Error: class {class_node.name} has no test methods", file=sys.stderr)
            return 1

        result: dict[str, Any] = {
            "test_file": str(test_file),
            "class": class_node.name,
            "test_methods": len(test_methods),
            "shared_methods": len(shared_methods),
        }

        # Load or auto-derive mapping
        mapping = TestSplitter._load_mapping(args.mapping)

        if not mapping:
            TestSplitter._emit_auto_mapping(
                args.json, test_file, class_node, test_methods, shared_methods, result
            )
            return 0

        # Group methods by SUT
        groups = TestSplitter._group_methods(test_methods, mapping)

        result["groups"] = {
            sut: [m.name for m in methods] for sut, methods in sorted(groups.items())
        }

        if args.json:
            if args.dry_run:
                result["dry_run"] = True
                print(json.dumps(result, indent=2))
                return 0
        else:
            TestSplitter._emit_proposed_split(
                test_file, class_node, test_methods, shared_methods, groups
            )
            if args.dry_run:
                print("\n--dry-run: no files written.")
                return 0

        # Output directory: <runs_dir>/test_split/<test_file stem>
        settings = ProjectConfig.load_settings()
        out_dir = ProjectConfig.runs_dir(settings) / "test_split" / test_file.stem

        out_dir.mkdir(parents=True, exist_ok=True)

        written = TestSplitter._write_split_files(
            tree, class_node, groups, shared_methods, out_dir
        )

        TestSplitter._emit_written(
            args.json, test_file, out_dir, written, result
        )
        return 0

    @staticmethod
    def _emit_written(
        json_mode: bool,
        test_file: Path,
        out_dir: Path,
        written: list[str],
        result: dict[str, Any],
    ) -> None:
        """Emit the final report after split files have been written."""
        if json_mode:
            result["out_dir"] = str(out_dir)
            result["written"] = written
            print(json.dumps(result, indent=2))
            return

        print(f"\nWriting split files to: {out_dir}/")
        for filename in written:
            print(f"  {filename}")
        print(f"\nDone. {len(written)} files written to {out_dir}/")
        print("Review the split files, then move them to replace the original.")
        print(f"Original file {test_file} was NOT modified.")

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        """Build the CLI argument parser."""
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
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        return parser

    @staticmethod
    def _find_target_class(tree: ast.Module, class_name: str | None) -> ast.ClassDef | None:
        """Find the target test class — the named one, or the first with tests."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if class_name and node.name == class_name:
                return node
            if not class_name and TestSplitter._get_test_methods(node):
                return node
        return None

    @staticmethod
    def _emit_auto_mapping(
        json_mode: bool,
        test_file: Path,
        class_node: ast.ClassDef,
        test_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
        shared_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
        result: dict[str, Any],
    ) -> None:
        """Emit the auto-derived prefix proposal when no --mapping was given."""
        auto = TestSplitter._auto_derive_prefixes(test_methods)
        proposed = {p: TestSplitter._snake_to_pascal(p) for p in auto}
        if json_mode:
            result["auto_prefixes"] = auto
            result["proposed_mapping"] = proposed
            print(json.dumps(result, indent=2))
            return
        print("=" * 70)
        print(f"TEST SPLITTER — {test_file.name}")
        print("=" * 70)
        print(f"\nClass: {class_node.name}")
        print(f"Test methods: {len(test_methods)}")
        print(f"Shared methods (fixtures/helpers): {len(shared_methods)}")
        print("\nNo --mapping provided. Auto-deriving prefixes from method names:")
        for prefix, names in sorted(auto.items()):
            print(
                f"  {prefix}: {len(names)} methods -> "
                f"{names[:3]}{'...' if len(names) > 3 else ''}"
            )
        print('\nUse --mapping \'{"prefix": "SutClass", ...}\' to specify SUT names.')
        print("Example:")
        print(f"  --mapping '{json.dumps(proposed)}'")
        print("\nRe-run with --mapping to split. Use --dry-run to preview first.")

    @staticmethod
    def _emit_proposed_split(
        test_file: Path,
        class_node: ast.ClassDef,
        test_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
        shared_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
        groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]],
    ) -> None:
        """Emit the text preview of the proposed per-SUT split."""
        print("=" * 70)
        print(f"TEST SPLITTER — {test_file.name}")
        print("=" * 70)
        print(f"\nClass: {class_node.name}")
        print(f"Test methods: {len(test_methods)}")
        print(f"Shared methods (fixtures/helpers): {len(shared_methods)}")
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

    @staticmethod
    def _write_split_files(
        tree: ast.Module,
        class_node: ast.ClassDef,
        groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]],
        shared_methods: list[ast.FunctionDef | ast.AsyncFunctionDef],
        out_dir: Path,
    ) -> list[str]:
        """Write one split test file per SUT group; return filenames written."""
        written: list[str] = []
        for sut, methods in sorted(groups.items()):
            if sut == "_unmatched" and not methods:  # pragma: no cover
                continue
            filename = f"test_{TestSplitter._pascal_to_snake(sut)}.py"
            filepath = out_dir / filename
            content = TestSplitter._build_split_file(
                tree, class_node, sut, methods, shared_methods, class_node.name
            )
            filepath.write_text(content, encoding="utf-8")
            written.append(filename)
        return written


if __name__ == "__main__":  # pragma: no cover
    sys.exit(TestSplitter.main())
