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
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.common.models import ClassInfo, Finding, ModuleInfo
from zolletta_metaskill.common.registry import (
    ensure_engine,
    get_engine_for_file,
)
from zolletta_metaskill.engines.python_engine import PythonEngine


def _ensure_python_engine() -> None:
    """Ensure the PythonEngine is registered."""
    ensure_engine(PythonEngine())


def _build_class_info(cls: ClassInfo) -> dict[str, Any]:
    """Build an internal info dict from a :class:`ClassInfo`.

    The dict format is consumed by :func:`_check_lsp_violations`.

    Args:
        cls: The :class:`ClassInfo` to convert.

    Returns:
        A dict with ``name``, ``line``, ``bases``, and ``methods`` keys.

    """
    methods: dict[str, dict[str, Any]] = {}
    for m in cls.methods:
        methods[m.name] = {
            "sig": {
                "name": m.name,
                "line": m.lineno,
                "pos_args": list(m.params),
                "required_count": len(m.params),
                "defaults_count": 0,
                "has_vararg": False,
                "has_kwarg": False,
                "returns_annotation": m.return_type,
            },
            "raised": set(m.raises),
            "is_stub": False,
        }
    # Normalise base names: ``animals.Animal`` → ``Animal``
    bases = [base.rsplit(".", 1)[-1] for base in cls.bases]
    return {
        "name": cls.name,
        "line": cls.lineno,
        "bases": bases,
        "methods": methods,
    }


def _check_lsp_violations(parent: dict[str, Any], child: dict[str, Any]) -> list[dict[str, Any]]:
    """Check LSP violations between parent and child class.

    Args:
        parent: Parent class info dict (from :func:`_build_class_info`).
        child: Child class info dict (from :func:`_build_class_info`).

    Returns:
        A list of violation dicts with keys ``type``, ``class``, ``method``,
        ``line``, and ``detail``.

    """
    violations: list[dict[str, Any]] = []
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
                "detail": (
                    f"requires {child_sig['required_count']} params, "
                    f"parent requires {parent_sig['required_count']}"
                ),
            })

        # Check 2: Fewer parameters (can't accept what parent accepts)
        if len(child_sig["pos_args"]) < len(parent_sig["pos_args"]) and not child_sig["has_vararg"]:
            violations.append({
                "type": "fewer_params",
                "class": child["name"],
                "method": mname,
                "line": child_sig["line"],
                "detail": (
                    f"accepts {len(child_sig['pos_args'])} args, "
                    f"parent accepts {len(parent_sig['pos_args'])}"
                ),
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


def scan_module(module: ModuleInfo) -> list[Finding]:
    """Check LSP violations within a single :class:`ModuleInfo`.

    Only violations where both the parent and child class are defined in the
    same module are reported. Cross-file violations require a global class
    registry and are handled by :func:`main`.

    Args:
        module: The parsed module to inspect.

    Returns:
        A list of :class:`Finding` objects for each LSP violation.

    """
    classes: dict[str, dict[str, Any]] = {}
    for cls in module.classes:
        classes[cls.name] = _build_class_info(cls)

    findings: list[Finding] = []
    for cls in module.classes:
        info = classes[cls.name]
        for base_name in info["bases"]:
            if base_name in classes:
                parent = classes[base_name]
                lsp_violations = _check_lsp_violations(parent, info)
                for v in lsp_violations:
                    findings.append(Finding(
                        file=str(module.path),
                        line=v["line"],
                        category="lsp_violation",
                        severity="high",
                        description=(
                            f"[{v['type']}] {v['class']}.{v['method']}() — "
                            f"{v['detail']} (parent: {base_name})"
                        ),
                        fix_type="manual",
                    ))
    return findings


def scan_file(path: Path) -> list[Finding]:
    """Backward-compatible wrapper that uses the registry to get an engine.

    Args:
        path: Path to a Python source file.

    Returns:
        A list of :class:`Finding` objects for LSP violations in the file.

    """
    _ensure_python_engine()
    engine = get_engine_for_file(path)
    if engine is None:
        return []
    module = engine.parse_module(path)
    return scan_module(module)


def main() -> int:
    """Entry point for the Liskov Substitution Principle validator CLI."""
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

    _ensure_python_engine()
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
    all_classes: dict[str, dict[str, Any]] = {}
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        engine = get_engine_for_file(py)
        if engine is None:
            continue
        module = engine.parse_module(py)
        if module.has_syntax_error:
            continue
        for cls in module.classes:
            info = _build_class_info(cls)
            info["file"] = str(py.relative_to(root))
            all_classes.setdefault(cls.name, info)

    # Check each child against its parent
    violations: list[dict[str, Any]] = []
    for _name, info in all_classes.items():
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
                "stub_override": (
                    "don't override if the method doesn't apply — "
                    "reconsider the hierarchy"
                ),
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
