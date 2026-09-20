#!/usr/bin/env python3
"""PHP Interface Segregation Principle (ISP) validator.

Detects "fat interfaces" — PHP interfaces with many methods where
implementers are forced to depend on methods they do not use.  When an
interface has too many methods, it should be split into smaller, focused
interfaces so that implementers only depend on what they actually need.

This scanner uses :class:`~zolletta_metaskill.core.structs.ModuleInfo`
directly (no raw tree-sitter AST needed):

- Interfaces are classes with ``is_abstract=True`` and no attributes.
- An interface with more than ``php.patterns.isp_min_methods`` methods
  (default: 7) is flagged as a "fat interface".

Scan roots come from ``php.autoload.psr-4`` in ``settings.json``. The check
runs when ``php.patterns.check_isp`` is not ``false``. File enumeration is
git-ignore aware.

Usage:
    python3 interface_segregation_scanner.py [--json]

Options:
    --json            Output as JSON instead of markdown.

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import ClassInfo, Finding, ModuleInfo


class InterfaceSegregationScanner:
    """PHP Interface Segregation Principle (ISP) validator.

    Detects "fat interfaces" — PHP interfaces with many methods where
    implementers are forced to depend on methods they do not use.
    All functions are exposed as ``@staticmethod`` methods on this class.
    """

    # Default threshold: interfaces with more than this many methods are "fat".
    _DEFAULT_MIN_METHODS = 7

    @staticmethod
    def _ensure_php_engine() -> None:
        """Ensure the PHPEngine is registered (idempotent)."""
        EngineRegistry.ensure(PHPEngine())

    @staticmethod
    def _is_interface(cls: ClassInfo) -> bool:
        """Return ``True`` if *cls* represents a PHP interface.

        In the :class:`ModuleInfo` model, PHP interfaces are mapped to
        :class:`ClassInfo` with ``is_abstract=True`` and no instance attributes.
        Abstract classes may also have ``is_abstract=True``, but they typically
        have attributes (or at least are not pure interfaces).  This heuristic
        follows the specification in PLAN-PHP-SUPPORT Phase 6.1.
        """
        return cls.is_abstract and not cls.attributes

    @staticmethod
    def _find_implementers(interface_name: str, all_classes: list[ClassInfo]) -> list[ClassInfo]:
        """Return all classes whose ``bases`` include *interface_name*."""
        return [cls for cls in all_classes if interface_name in cls.bases]

    @staticmethod
    def scan_module(module: ModuleInfo, min_methods: int | None = None) -> list[Finding]:
        """Scan a parsed PHP module and return ISP findings.

        Detects interfaces (abstract classes with no attributes) that have
        more than *min_methods* methods.

        Args:
            module: The :class:`ModuleInfo` produced by :meth:`PHPEngine.parse_module`.
            min_methods: The minimum method count to flag as a fat interface.

        Returns:
            A list of :class:`Finding` objects with category ``"isp"``.

        """
        if min_methods is None:
            min_methods = InterfaceSegregationScanner._DEFAULT_MIN_METHODS
        if module.has_syntax_error:
            return []
        if module.language != "php":
            return []

        findings: list[Finding] = []
        file_path = str(module.path)
        all_classes = module.classes

        for cls in all_classes:
            if not InterfaceSegregationScanner._is_interface(cls):
                continue
            method_count = len(cls.methods)
            if method_count > min_methods:
                method_names = ", ".join(m.name for m in cls.methods)
                implementers = InterfaceSegregationScanner._find_implementers(cls.name, all_classes)
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

    @staticmethod
    def scan_file(path: Path, min_methods: int | None = None) -> list[Finding]:
        """Scan a single PHP file for ISP violations.

        Args:
            path: Path to a ``.php`` source file.
            min_methods: The minimum method count to flag as a fat interface.

        Returns:
            A list of :class:`Finding` objects (empty if no engine matches or
            the file has a syntax error).

        """
        if min_methods is None:
            min_methods = InterfaceSegregationScanner._DEFAULT_MIN_METHODS
        InterfaceSegregationScanner._ensure_php_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        return InterfaceSegregationScanner.scan_module(module, min_methods=min_methods)

    @staticmethod
    def main() -> int:
        """Entry point for the PHP Interface Segregation validator CLI."""
        parser = argparse.ArgumentParser(
            description=(
                "PHP Interface Segregation Principle (ISP) validator — "
                "detect fat interfaces with too many methods."
            )
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        InterfaceSegregationScanner._ensure_php_engine()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_isp")
        php_langs = ProjectConfig.languages_for_extensions(languages, {".php"})
        if not php_langs:
            ProjectConfig.emit_skipped(args.json, "check_isp disabled in settings.json")
            return 0

        roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, php_langs)
        )
        if not roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1

        raw_min = ProjectConfig.setting(
            settings, "php.patterns.isp_min_methods", None
        )
        min_methods = (
            raw_min
            if isinstance(raw_min, int)
            else InterfaceSegregationScanner._DEFAULT_MIN_METHODS
        )

        all_findings: list[Finding] = []
        scanned_files = 0
        for root in roots:
            for php_file in ProjectConfig.iter_files(root, {".php"}):
                scanned_files += 1
                all_findings.extend(
                    InterfaceSegregationScanner.scan_file(php_file, min_methods=min_methods)
                )

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(r) for r in roots],
                        "scanned_files": scanned_files,
                        "min_methods": min_methods,
                        "violation_count": len(all_findings),
                        "violations": [
                            {
                                "file": f.file,
                                "line": f.line,
                                "severity": f.severity,
                                "description": f.description,
                            }
                            for f in all_findings
                        ],
                    },
                    indent=2,
                )
            )
            return 0

        print("=" * 70)
        print("PHP INTERFACE SEGREGATION (ISP) — VALIDATION REPORT")
        print("=" * 70)

        if all_findings:
            print(f"\n## Fat interfaces ({len(all_findings)} found)\n")
            for f in all_findings:
                print(f"  {f.description}")
                print(f"    -> {f.file}:{f.line}")
                print("    Fix: split into smaller, focused interfaces")
        else:
            print(f"\n## Fat interfaces: none (threshold: {min_methods} methods)")

        print()
        if all_findings:
            print("Result: ISP violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(InterfaceSegregationScanner.main())  # pragma: no cover
