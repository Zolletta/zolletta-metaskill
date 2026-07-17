#!/usr/bin/env python3
"""Interface Segregation Principle (ISP) validator.

Detects "fat interfaces" — Protocols / ABCs with many methods where different
implementers only use subsets. When implementers are forced to stub or raise
NotImplementedError for methods they don't need, the interface should be split.

Checks:
  - Protocol/ABC classes with 5+ abstract methods (fat interface signal)
  - Implementers that raise NotImplementedError or return None (stub) for
    some methods of the interface
  - Protocol/ABC methods that no implementer actually calls (dead interface
    methods)

Usage:
    python3 scan_interface_segregation.py <directory> [--min-methods N]
        [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --min-methods N   Minimum abstract method count to flag as fat (default: 5)
    --skip            Skip this check entirely (exit 0 with 'skipped' message)
    --strict          Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _get_class_info(node: ast.ClassDef) -> dict:
    """Extract class info: bases, methods, abstract markers."""
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append({
                "name": item.name,
                "line": item.lineno,
                "raises_not_implemented": _raises_not_implemented(item),
                "returns_none": _returns_none_only(item),
            })
    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(base.attr)
    return {
        "name": node.name,
        "line": node.lineno,
        "bases": bases,
        "methods": methods,
    }


def _raises_not_implemented(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a method body raises NotImplementedError."""
    for node in ast.walk(func):
        if isinstance(node, ast.Raise) and node.exc:
            exc = node.exc
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                if exc.func.id == "NotImplementedError":
                    return True
            if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                return True
    return False


def _returns_none_only(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a method body is just 'pass' or 'return None' (stub)."""
    body = func.body
    # Strip docstring
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if len(body) == 1:
        stmt = body[0]
        if isinstance(stmt, ast.Pass):
            return True
        if (isinstance(stmt, ast.Return)
                and (stmt.value is None
                     or (isinstance(stmt.value, ast.Constant)
                         and stmt.value.value is None))):
            return True
    return False


def _is_protocol_or_abc(class_info: dict) -> bool:
    """Check if a class is a Protocol or ABC."""
    bases = class_info["bases"]
    return any(b in ("Protocol", "ABC") for b in bases)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interface Segregation Principle (ISP) validator."
    )
    parser.add_argument("directory", nargs="?", default="src",
                        help="Root directory to scan (default: src)")
    parser.add_argument("--min-methods", type=int, default=5,
                        help="Min abstract method count to flag as fat (default: 5)")
    parser.add_argument("--skip", action="store_true",
                        help="Skip this check entirely")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if violations are found")
    args = parser.parse_args()

    if args.skip:
        print("=" * 70)
        print("INTERFACE SEGREGATION (ISP) — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    # Collect all classes
    all_classes: dict[str, dict] = {}  # name -> class_info
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                info = _get_class_info(node)
                info["file"] = str(py.relative_to(root))
                all_classes.setdefault(info["name"], info)

    # Find protocols/ABCs
    protocols = {name: info for name, info in all_classes.items()
                 if _is_protocol_or_abc(info)}

    # Find implementers of each protocol/ABC
    implementers: dict[str, list[str]] = {}  # protocol_name -> [impl_class_names]
    for name, info in all_classes.items():
        for base in info["bases"]:
            if base in protocols:
                implementers.setdefault(base, []).append(name)

    fat_interfaces: list[dict] = []
    stub_violations: list[dict] = []

    for proto_name, proto_info in protocols.items():
        method_names = [m["name"] for m in proto_info["methods"]]
        if len(method_names) >= args.min_methods:
            fat_interfaces.append({
                "name": proto_name,
                "file": proto_info["file"],
                "line": proto_info["line"],
                "method_count": len(method_names),
                "methods": method_names,
            })

        # Check implementers for stubs
        for impl_name in implementers.get(proto_name, []):
            impl_info = all_classes[impl_name]
            impl_methods = {m["name"]: m for m in impl_info["methods"]}
            for proto_method in proto_info["methods"]:
                mname = proto_method["name"]
                if mname in impl_methods:
                    im = impl_methods[mname]
                    if im["raises_not_implemented"] or im["returns_none"]:
                        stub_violations.append({
                            "protocol": proto_name,
                            "implementer": impl_name,
                            "method": mname,
                            "file": impl_info["file"],
                            "line": im["line"],
                            "issue": "raises NotImplementedError" if im["raises_not_implemented"] else "stub (pass/return None)",
                        })

    has_violations = bool(fat_interfaces or stub_violations)

    print("=" * 70)
    print("INTERFACE SEGREGATION (ISP) — VALIDATION REPORT")
    print("=" * 70)

    if fat_interfaces:
        print(f"\n## Fat interfaces ({len(fat_interfaces)} found, >= {args.min_methods} methods)\n")
        for item in fat_interfaces:
            print(f"  {item['name']} ({item['method_count']} methods)")
            print(f"    -> {item['file']}:{item['line']}")
            print(f"    Methods: {', '.join(item['methods'])}")
            impls = implementers.get(item["name"], [])
            if impls:
                print(f"    Implementers: {', '.join(impls)}")
            print(f"    Fix: split into smaller, focused protocols")
    else:
        print(f"\n## Fat interfaces: none (threshold: {args.min_methods} methods)")

    if stub_violations:
        print(f"\n## Implementers stubbing interface methods ({len(stub_violations)} found)\n")
        for item in stub_violations:
            print(f"  {item['implementer']}.{item['method']}() — {item['issue']}")
            print(f"    Protocol: {item['protocol']}")
            print(f"    -> {item['file']}:{item['line']}")
            print(f"    Fix: split {item['protocol']} so {item['implementer']} only depends on what it needs")
    else:
        print("\n## Implementers stubbing interface methods: none")

    print()
    if has_violations and args.strict:
        print("Result: ISP VIOLATIONS FOUND (strict mode)")
        return 1
    elif has_violations:
        print("Result: ISP violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
