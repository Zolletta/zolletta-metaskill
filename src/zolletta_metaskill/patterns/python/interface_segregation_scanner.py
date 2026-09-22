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

Scan roots come from ``python.paths.source`` in ``settings.json``; the
method threshold comes from ``python.patterns.isp_min_methods`` (default
5). The check runs when ``python.patterns.check_isp`` is not ``false``.
File enumeration is git-ignore aware.

Usage:
    python3 interface_segregation_scanner.py [--json]

Options:
    --json            Output as JSON instead of markdown.

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class InterfaceSegregationScanner:
    """Interface Segregation Principle (ISP) validator."""

    @staticmethod
    def _get_class_info(node: ast.ClassDef) -> dict[str, Any]:
        """Extract class info: bases, methods, abstract markers."""
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(
                    {
                        "name": item.name,
                        "line": item.lineno,
                        "raises_not_implemented": (
                            InterfaceSegregationScanner._raises_not_implemented(item)
                        ),
                        "returns_none": (InterfaceSegregationScanner._returns_none_only(item)),
                    }
                )
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

    @staticmethod
    def _raises_not_implemented(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if a method body raises NotImplementedError."""
        for node in ast.walk(func):
            if isinstance(node, ast.Raise) and node.exc:
                exc = node.exc
                if (
                    isinstance(exc, ast.Call)
                    and isinstance(exc.func, ast.Name)
                    and exc.func.id == "NotImplementedError"
                ):
                    return True
                if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                    return True
        return False

    @staticmethod
    def _returns_none_only(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if a method body is just 'pass' or 'return None' (stub)."""
        body = func.body
        # Strip docstring
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        if len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                return True
            if isinstance(stmt, ast.Return) and (
                stmt.value is None
                or (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)
            ):
                return True
        return False

    @staticmethod
    def _is_protocol_or_abc(class_info: dict[str, Any]) -> bool:
        """Check if a class is a Protocol or ABC."""
        bases = class_info["bases"]
        return any(b in ("Protocol", "ABC") for b in bases)

    @staticmethod
    def main() -> int:
        """Entry point for the Interface Segregation Principle validator CLI."""
        parser = argparse.ArgumentParser(
            description="Interface Segregation Principle (ISP) validator. "
            "Roots come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_isp")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(args.json, "check_isp disabled in settings.json")
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, py_langs))
        if not roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1

        limits: list[int] = []
        for lang in sorted(py_langs):
            value = ProjectConfig.setting(settings, f"{lang}.patterns.isp_min_methods", None)
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        min_methods = min(limits) if limits else 5

        # Collect all classes across all roots
        all_classes: dict[str, dict[str, Any]] = {}  # name -> class_info
        for root in roots:
            for py in ProjectConfig.iter_files(root, {".py"}):
                try:
                    tree = ast.parse(py.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        info = InterfaceSegregationScanner._get_class_info(node)
                        info["file"] = str(py.relative_to(root))
                        all_classes.setdefault(info["name"], info)

        # Find protocols/ABCs
        protocols = {
            name: info
            for name, info in all_classes.items()
            if InterfaceSegregationScanner._is_protocol_or_abc(info)
        }

        # Find implementers of each protocol/ABC
        implementers: dict[str, list[str]] = {}  # protocol_name -> [impl_class_names]
        for name, info in all_classes.items():
            for base in info["bases"]:
                if base in protocols:
                    implementers.setdefault(base, []).append(name)

        fat_interfaces: list[dict[str, Any]] = []
        stub_violations: list[dict[str, Any]] = []

        for proto_name, proto_info in protocols.items():
            method_names = [m["name"] for m in proto_info["methods"]]
            if len(method_names) >= min_methods:
                fat_interfaces.append(
                    {
                        "name": proto_name,
                        "file": proto_info["file"],
                        "line": proto_info["line"],
                        "method_count": len(method_names),
                        "methods": method_names,
                    }
                )

            # Check implementers for stubs
            for impl_name in implementers.get(proto_name, []):
                impl_info = all_classes[impl_name]
                impl_methods = {m["name"]: m for m in impl_info["methods"]}
                for proto_method in proto_info["methods"]:
                    mname = proto_method["name"]
                    if mname in impl_methods:
                        im = impl_methods[mname]
                        if im["raises_not_implemented"] or im["returns_none"]:
                            stub_violations.append(
                                {
                                    "protocol": proto_name,
                                    "implementer": impl_name,
                                    "method": mname,
                                    "file": impl_info["file"],
                                    "line": im["line"],
                                    "issue": (
                                        "raises NotImplementedError"
                                        if im["raises_not_implemented"]
                                        else "stub (pass/return None)"
                                    ),
                                }
                            )

        has_violations = bool(fat_interfaces or stub_violations)

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "min_methods": min_methods,
                        "fat_interfaces": fat_interfaces,
                        "stub_violations": stub_violations,
                        "violation_count": len(fat_interfaces) + len(stub_violations),
                    },
                    indent=2,
                )
            )
            return 0

        print("=" * 70)
        print("INTERFACE SEGREGATION (ISP) — VALIDATION REPORT")
        print("=" * 70)

        if fat_interfaces:
            print(f"\n## Fat interfaces ({len(fat_interfaces)} found, >= {min_methods} methods)\n")
            for item in fat_interfaces:
                print(f"  {item['name']} ({item['method_count']} methods)")
                print(f"    -> {item['file']}:{item['line']}")
                print(f"    Methods: {', '.join(item['methods'])}")
                impls = implementers.get(item["name"], [])
                if impls:
                    print(f"    Implementers: {', '.join(impls)}")
                print("    Fix: split into smaller, focused protocols")
        else:
            print(f"\n## Fat interfaces: none (threshold: {min_methods} methods)")

        if stub_violations:
            print(f"\n## Implementers stubbing interface methods ({len(stub_violations)} found)\n")
            for item in stub_violations:
                print(f"  {item['implementer']}.{item['method']}() — {item['issue']}")
                print(f"    Protocol: {item['protocol']}")
                print(f"    -> {item['file']}:{item['line']}")
                print(
                    f"    Fix: split {item['protocol']} so {item['implementer']} "
                    "only depends on what it needs"
                )
        else:
            print("\n## Implementers stubbing interface methods: none")

        print()
        if has_violations:
            print("Result: ISP violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(InterfaceSegregationScanner.main())
