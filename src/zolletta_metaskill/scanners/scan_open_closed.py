#!/usr/bin/env python3
"""Open/Closed Principle (OCP) validator.

Detects patterns where adding a new type requires modifying existing code
instead of extending it. The canonical OCP solution is polymorphism (strategy
pattern, plugin registry) — the validator flags code that uses type-based
branching instead.

Checks:
  - if/elif chains that compare type names (string comparison or isinstance
    ladders with 3+ branches)
  - getattr(obj, "method_name_" + type_name) dynamic dispatch by string
  - match/case statements on type (Python 3.10+)

These are signals that the code is "open for modification" instead of "open
for extension."

Usage:
    python3 scan_open_closed.py <directory> [--min-branches N]
        [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --min-branches N  Minimum branch count to flag a type ladder (default: 3)
    --skip            Skip this check entirely
    --strict          Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _is_type_check(node: ast.AST) -> bool:
    """Check if a condition is an isinstance() or type() comparison."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "isinstance":
            return True
        if node.func.id == "type":
            return True
    # type(obj) == SomeClass
    if isinstance(node, ast.Compare):
        if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name):
            if node.left.func.id == "type":
                return True
        # obj.__class__.__name__ == "SomeClass"
        if isinstance(node.left, ast.Attribute):
            if node.left.attr == "__name__":
                return True
    # String comparison: obj.type == "something" or obj.__class__.__name__
    if isinstance(node, ast.Compare):
        left = node.left
        if isinstance(left, ast.Attribute) and left.attr in ("type", "kind", "__class__"):
            return True
    return False


def _count_type_branches(node: ast.If) -> int:
    """Count how many branches in an if/elif chain do type checks."""
    count = 0
    current = node
    while isinstance(current, ast.If):
        if _is_type_check(current.test) or _contains_type_check(current.test):
            count += 1
        # Check elif chain
        if current.orelse and len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
        else:
            # Final else doesn't count as a type branch
            break
    return count


def _contains_type_check(node: ast.AST) -> bool:
    """Check if a boolean expression contains a type check."""
    if isinstance(node, ast.BoolOp):
        return any(_is_type_check(v) or _contains_type_check(v) for v in node.values)
    return _is_type_check(node)


def _is_string_type_dispatch(node: ast.Call) -> bool:
    """Detect getattr(obj, 'method_' + type_name) dynamic dispatch."""
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr != "getattr":
        # Direct attribute access with string concat: obj.__getattr__("method_" + x)
        return False
    if len(node.args) >= 2:
        second = node.args[1]
        # Check for string concatenation: "prefix_" + variable
        if isinstance(second, ast.BinOp) and isinstance(second.op, ast.Add):
            return True
        if isinstance(second, ast.JoinedStr):
            return True
    return False


def _find_match_on_type(node: ast.Match) -> bool:
    """Check if a match statement matches on type/class."""
    for case in node.cases:
        pattern = case.pattern
        if isinstance(pattern, ast.MatchClass):
            return True
    return False


def scan_file(path: Path) -> list[dict]:
    """Scan a file for OCP violations."""
    violations = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        # if/elif type ladders
        if isinstance(node, ast.If):
            branch_count = _count_type_branches(node)
            if branch_count >= 3:
                violations.append({
                    "type": "type_ladder",
                    "file": str(path),
                    "line": node.lineno,
                    "branches": branch_count,
                    "detail": f"if/elif chain with {branch_count} type-check branches",
                })

        # getattr dynamic dispatch
        if isinstance(node, ast.Call):
            if _is_string_type_dispatch(node):
                violations.append({
                    "type": "string_dispatch",
                    "file": str(path),
                    "line": node.lineno,
                    "branches": 0,
                    "detail": "getattr() with dynamic string — consider polymorphism",
                })

        # match/case on type (Python 3.10+)
        if isinstance(node, ast.Match):
            if _find_match_on_type(node):
                case_count = sum(1 for c in node.cases if isinstance(c.pattern, ast.MatchClass))
                if case_count >= 3:
                    violations.append({
                        "type": "match_on_type",
                        "file": str(path),
                        "line": node.lineno,
                        "branches": case_count,
                        "detail": f"match/case on type with {case_count} class patterns",
                    })

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open/Closed Principle (OCP) validator."
    )
    parser.add_argument("directory", nargs="?", default="src",
                        help="Root directory to scan (default: src)")
    parser.add_argument("--min-branches", type=int, default=3,
                        help="Min type-check branches to flag (default: 3)")
    parser.add_argument("--skip", action="store_true",
                        help="Skip this check entirely")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if violations are found")
    args = parser.parse_args()

    if args.skip:
        print("=" * 70)
        print("OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_violations: list[dict] = []
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        violations = scan_file(py)
        for v in violations:
            v["file"] = str(py.relative_to(root))
            all_violations.append(v)

    # Filter by min-branches for type ladders
    filtered = [v for v in all_violations
                if v["type"] != "type_ladder" or v["branches"] >= args.min_branches]

    print("=" * 70)
    print("OPEN/CLOSED PRINCIPLE (OCP) — VALIDATION REPORT")
    print("=" * 70)

    if filtered:
        print(f"\n## OCP violations ({len(filtered)} found)\n")
        for v in filtered:
            print(f"  [{v['type']}] {v['detail']}")
            print(f"    -> {v['file']}:{v['line']}")
            print(f"    Fix: replace type branching with polymorphism (strategy pattern,")
            print(f"         plugin registry, or protocol-based dispatch)")
    else:
        print("\n## OCP violations: none")

    print()
    if filtered and args.strict:
        print("Result: OCP VIOLATIONS FOUND (strict mode)")
        return 1
    elif filtered:
        print("Result: OCP violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
