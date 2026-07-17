#!/usr/bin/env python3
"""Liskov Substitution Principle (LSP) validator.

Detects subclass methods that break substitutability — where a subtype cannot
replace its supertype without altering the correctness of the program.

Checks:
  - Overridden methods with incompatible signatures (narrower parameter types,
    fewer parameters, extra required parameters)
  - Overridden methods that raise new exception types not raised by the parent
  - Overridden methods that weaken postconditions (return None when parent
    always returns a value)
  - Subclasses that override a method with a completely empty body (pass/None)
    suggesting the method doesn't belong in the hierarchy

Usage:
    python3 scan_liskov_substitution.py <directory> [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --skip            Skip this check entirely
    --strict          Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _get_method_signature(func: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    """Extract method signature info."""
    args = func.args
    # Positional args (excluding self/cls)
    pos_args = [a.arg for a in args.args[1:]]  # skip self/cls
    defaults_count = len(args.defaults)
    required_count = len(pos_args) - defaults_count
    has_vararg = args.vararg is not None
    has_kwarg = args.kwarg is not None
    return {
        "name": func.name,
        "line": func.lineno,
        "pos_args": pos_args,
        "required_count": required_count,
        "defaults_count": defaults_count,
        "has_vararg": has_vararg,
        "has_kwarg": has_kwarg,
        "returns_annotation": _get_return_annotation(func),
    }


def _get_return_annotation(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Get return type annotation as string."""
    if func.returns is None:
        return None
    try:
        return ast.unparse(func.returns)
    except Exception:
        return None


def _get_raised_exceptions(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Find all exception types raised in a method."""
    raised = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Raise) and node.exc:
            exc = node.exc
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                raised.add(exc.func.id)
            elif isinstance(exc, ast.Name):
                raised.add(exc.id)
    return raised


def _is_stub_body(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if method body is just pass/return None/... (Ellipsis)."""
    body = func.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if len(body) == 1:
        stmt = body[0]
        if isinstance(stmt, ast.Pass):
            return True
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                return True
            if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            if stmt.value.value is ...:
                return True
    return False


def _get_classes(tree: ast.Module) -> dict[str, dict]:
    """Extract all classes with their methods and base classes."""
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = {}
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods[item.name] = {
                        "sig": _get_method_signature(item),
                        "raised": _get_raised_exceptions(item),
                        "is_stub": _is_stub_body(item),
                        "node": item,
                    }
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            classes[node.name] = {
                "name": node.name,
                "line": node.lineno,
                "bases": bases,
                "methods": methods,
            }
    return classes


def _check_lsp_violations(parent: dict, child: dict) -> list[dict]:
    """Check LSP violations between parent and child class."""
    violations = []
    parent_methods = parent["methods"]
    child_methods = child["methods"]

    for mname, parent_method in parent_methods.items():
        if mname not in child_methods:
            continue  # Not overridden — fine

        child_method = child_methods[mname]
        parent_sig = parent_method["sig"]
        child_sig = child_method["sig"]

        # Check 1: Extra required parameters
        if child_sig["required_count"] > parent_sig["required_count"]:
            violations.append({
                "type": "extra_required_params",
                "class": child["name"],
                "method": mname,
                "line": child_sig["line"],
                "detail": f"requires {child_sig['required_count']} params, parent requires {parent_sig['required_count']}",
            })

        # Check 2: Fewer parameters (can't accept what parent accepts)
        if len(child_sig["pos_args"]) < len(parent_sig["pos_args"]) and not child_sig["has_vararg"]:
            violations.append({
                "type": "fewer_params",
                "class": child["name"],
                "method": mname,
                "line": child_sig["line"],
                "detail": f"accepts {len(child_sig['pos_args'])} args, parent accepts {len(parent_sig['pos_args'])}",
            })

        # Check 3: New exception types
        parent_exc = parent_method["raised"]
        child_exc = child_method["raised"]
        new_exc = child_exc - parent_exc
        # Allow broader exceptions
        broader = {"Exception", "BaseException", "ValueError", "RuntimeError", "TypeError"}
        truly_new = new_exc - broader - parent_exc
        if truly_new:
            violations.append({
                "type": "new_exceptions",
                "class": child["name"],
                "method": mname,
                "line": child_sig["line"],
                "detail": f"raises {truly_new}, parent raises {parent_exc or 'nothing'}",
            })

        # Check 4: Stub override (pass/return None) when parent has real body
        if child_method["is_stub"] and not parent_method["is_stub"]:
            violations.append({
                "type": "stub_override",
                "class": child["name"],
                "method": mname,
                "line": child_sig["line"],
                "detail": "overrides with empty body (pass/return None) — weakens postcondition",
            })

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Liskov Substitution Principle (LSP) validator."
    )
    parser.add_argument("directory", nargs="?", default="src",
                        help="Root directory to scan (default: src)")
    parser.add_argument("--skip", action="store_true",
                        help="Skip this check entirely")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if violations are found")
    args = parser.parse_args()

    if args.skip:
        print("=" * 70)
        print("LISKOV SUBSTITUTION (LSP) — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    # Collect all classes across all files
    all_classes: dict[str, dict] = {}
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        classes = _get_classes(tree)
        for name, info in classes.items():
            info["file"] = str(py.relative_to(root))
            all_classes.setdefault(name, info)

    # Check each child against its parent
    violations: list[dict] = []
    for name, info in all_classes.items():
        for base_name in info["bases"]:
            if base_name in all_classes:
                parent = all_classes[base_name]
                lsp_violations = _check_lsp_violations(parent, info)
                for v in lsp_violations:
                    v["parent"] = base_name
                    v["file"] = info["file"]
                    violations.append(v)

    print("=" * 70)
    print("LISKOV SUBSTITUTION (LSP) — VALIDATION REPORT")
    print("=" * 70)

    if violations:
        print(f"\n## LSP violations ({len(violations)} found)\n")
        for v in violations:
            print(f"  [{v['type']}] {v['class']}.{v['method']}() — {v['detail']}")
            print(f"    Parent: {v['parent']}")
            print(f"    -> {v['file']}:{v['line']}")
            fixes = {
                "extra_required_params": "remove extra required params or make them optional",
                "fewer_params": "accept *args/**kwargs to maintain substitutability",
                "new_exceptions": "catch and wrap new exceptions, or declare them in the parent",
                "stub_override": "don't override if the method doesn't apply — reconsider the hierarchy",
            }
            fix = fixes.get(v["type"], "review the override")
            print(f"    Fix: {fix}")
    else:
        print("\n## LSP violations: none")

    print()
    if violations and args.strict:
        print("Result: LSP VIOLATIONS FOUND (strict mode)")
        return 1
    elif violations:
        print("Result: LSP violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
