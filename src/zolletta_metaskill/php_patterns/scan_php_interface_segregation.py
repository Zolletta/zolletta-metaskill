#!/usr/bin/env python3
"""PHP Interface Segregation Principle (ISP) validator.

Detects "fat interfaces" — PHP interfaces with many methods where
implementers are forced to depend on methods they do not use.  When an
interface has too many methods, it should be split into smaller, focused
interfaces so that implementers only depend on what they actually need.

This scanner uses :class:`~zolletta_metaskill.common.models.ModuleInfo`
directly (no raw tree-sitter AST needed):

- Interfaces are classes with ``is_abstract=True`` and no attributes.
- An interface with more than ``--min-methods`` methods (default: 7) is
  flagged as a "fat interface".

Usage:
    python3 scan_php_interface_segregation.py <directory>
        [--min-methods N] [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --min-methods N   Minimum method count to flag as fat (default: 7)
    --skip            Skip this check entirely
    --strict          Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from zolletta_metaskill.common.models import ClassInfo, Finding, ModuleInfo
from zolletta_metaskill.common.registry import (
    ensure_engine,
    get_engine_for_file,
)
from zolletta_metaskill.engines.php_engine import PHPEngine

__all__ = ["main", "scan_file", "scan_module"]

# Default threshold: interfaces with more than this many methods are "fat".
_DEFAULT_MIN_METHODS = 7


def _ensure_php_engine() -> None:
    """Ensure the PHPEngine is registered (idempotent)."""
    ensure_engine(PHPEngine())


def _is_interface(cls: ClassInfo) -> bool:
    """Return ``True`` if *cls* represents a PHP interface.

    In the :class:`ModuleInfo` model, PHP interfaces are mapped to
    :class:`ClassInfo` with ``is_abstract=True`` and no instance attributes.
    Abstract classes may also have ``is_abstract=True``, but they typically
    have attributes (or at least are not pure interfaces).  This heuristic
    follows the specification in PLAN-PHP-SUPPORT Phase 6.1.
    """
    return cls.is_abstract and not cls.attributes


def _find_implementers(
    interface_name: str, all_classes: list[ClassInfo]
) -> list[ClassInfo]:
    """Return all classes whose ``bases`` include *interface_name*."""
    return [cls for cls in all_classes if interface_name in cls.bases]


def scan_module(
    module: ModuleInfo, min_methods: int = _DEFAULT_MIN_METHODS
) -> list[Finding]:
    """Scan a parsed PHP module and return ISP findings.

    Detects interfaces (abstract classes with no attributes) that have
    more than *min_methods* methods.

    Args:
        module: The :class:`ModuleInfo` produced by :meth:`PHPEngine.parse_module`.
        min_methods: The minimum method count to flag as a fat interface.

    Returns:
        A list of :class:`Finding` objects with category ``"isp"``.

    """
    if module.has_syntax_error:
        return []
    if module.language != "php":
        return []

    findings: list[Finding] = []
    file_path = str(module.path)
    all_classes = module.classes

    for cls in all_classes:
        if not _is_interface(cls):
            continue
        method_count = len(cls.methods)
        if method_count > min_methods:
            method_names = ", ".join(m.name for m in cls.methods)
            implementers = _find_implementers(cls.name, all_classes)
            impl_text = (
                f" (implementers: {', '.join(c.name for c in implementers)})"
                if implementers
                else ""
            )
            findings.append(
                Finding(
                    file=file_path,
                    line=cls.lineno,
                    category="isp",
                    severity="low",
                    description=(
                        f"Fat interface '{cls.name}' has {method_count} methods "
                        f"(threshold: {min_methods}){impl_text}. "
                        f"Methods: {method_names}. "
                        f"Split into smaller, focused interfaces."
                    ),
                    fix_type="manual",
                )
            )

    return findings


def scan_file(
    path: Path, min_methods: int = _DEFAULT_MIN_METHODS
) -> list[Finding]:
    """Scan a single PHP file for ISP violations.

    Args:
        path: Path to a ``.php`` source file.
        min_methods: The minimum method count to flag as a fat interface.

    Returns:
        A list of :class:`Finding` objects (empty if no engine matches or
        the file has a syntax error).

    """
    _ensure_php_engine()
    engine = get_engine_for_file(path)
    if engine is None:  # pragma: no cover
        return []
    module = engine.parse_module(path)
    return scan_module(module, min_methods=min_methods)


def main() -> int:
    """Entry point for the PHP Interface Segregation validator CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "PHP Interface Segregation Principle (ISP) validator — "
            "detect fat interfaces with too many methods."
        )
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="src",
        help="Root directory to scan (default: src)",
    )
    parser.add_argument(
        "--min-methods",
        type=int,
        default=_DEFAULT_MIN_METHODS,
        help=f"Min method count to flag as fat (default: {_DEFAULT_MIN_METHODS})",
    )
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if violations are found",
    )
    args = parser.parse_args()

    _ensure_php_engine()
    if args.skip:
        print("=" * 70)
        print("PHP INTERFACE SEGREGATION (ISP) — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    all_findings: list[Finding] = []
    for php_file in root.rglob("*.php"):
        all_findings.extend(scan_file(php_file, min_methods=args.min_methods))

    print("=" * 70)
    print("PHP INTERFACE SEGREGATION (ISP) — VALIDATION REPORT")
    print("=" * 70)

    if all_findings:
        print(f"\n## Fat interfaces ({len(all_findings)} found)\n")
        for f in all_findings:
            try:
                rel = str(Path(f.file).relative_to(root))
            except ValueError:  # pragma: no cover
                rel = f.file  # pragma: no cover
            print(f"  {f.description}")
            print(f"    -> {rel}:{f.line}")
            print("    Fix: split into smaller, focused interfaces")
    else:
        print(f"\n## Fat interfaces: none (threshold: {args.min_methods} methods)")

    print()
    if all_findings and args.strict:
        print("Result: ISP VIOLATIONS FOUND (strict mode)")
        return 1
    elif all_findings:
        print("Result: ISP violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())  # pragma: no cover
