#!/usr/bin/env python3
"""Check test function naming against the ``test_<unit>_<scenario>_<expected>`` convention.

Reports test functions whose name (after stripping the ``test_`` prefix) has
fewer than ``--min-segments`` underscore-separated segments. The convention
expects at least 3 segments: the unit under test, the scenario, and the
expected outcome.

Example::

    # Good — 3 segments: init, with_valid_dependencies, stores_attributes
    test_init_with_valid_dependencies_stores_attributes

    # Bad — 1 segment: init (no scenario, no expected outcome)
    test_init

    # Bad — 2 segments: to_dict, returns_expected (missing unit context)
    test_to_dict_returns_expected

The scanner is deterministic: the same input always produces the same output.
This replaces manual AI review of test function names, which was
non-deterministic and produced different violation counts on each run.

Test roots come from ``python.paths.tests`` in ``settings.json``; the
minimum segment count comes from ``python.testing.test_naming_min_segments``
(default 3). The check runs when ``python.testing.check_test_naming`` is
not ``false``. File enumeration is git-ignore aware.

Usage:
    python3 test_naming_scanner.py [--json]

Options:
    --json             Output as JSON instead of markdown

Exit code: 0 always (report-only).

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.python_engine import PythonEngine
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding, ModuleInfo


class TestNamingScanner:
    """Scan test function names for convention violations."""

    @staticmethod
    def _ensure_python_engine() -> None:
        """Ensure the PythonEngine is registered."""
        EngineRegistry.ensure(PythonEngine())

    @staticmethod
    def _count_segments(func_name: str) -> int:
        """Count underscore-separated segments after the ``test_`` prefix.

        Returns 0 if the name doesn't start with ``test_``.
        """
        if not func_name.startswith("test_"):
            return 0
        rest = func_name[len("test_") :]
        # Filter out empty segments (e.g. test__foo) and count non-empty parts
        segments = [s for s in rest.split("_") if s]
        return len(segments)

    @staticmethod
    def _find_test_functions(file_path: Path) -> list[tuple[str, int]]:
        """Return (function_name, line_number) for every test_ function in a file.

        Uses the registered language engine to parse the file.  Both top-level
        test functions and test methods inside classes are discovered.
        """
        TestNamingScanner._ensure_python_engine()
        engine = EngineRegistry.get_for_file(file_path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(file_path)
        if module.has_syntax_error:
            return []

        results: list[tuple[str, int]] = []
        for func in module.functions:
            if func.name.startswith("test_"):
                results.append((func.name, func.lineno))
        for cls in module.classes:
            # Only check methods on Test* classes — methods named test_* on
            # non-test classes (e.g. protocol implementations like
            # _StubEngine.test_file_glob) are not test functions.
            if not cls.name.startswith("Test"):
                continue
            for method in cls.methods:
                if method.name.startswith("test_"):
                    results.append((method.name, method.lineno))
        return results

    @staticmethod
    def scan_module(module: ModuleInfo, min_segments: int = 3) -> list[Finding]:
        """Scan a parsed module for test-naming convention violations.

        Args:
            module: The :class:`ModuleInfo` produced by an engine.
            min_segments: Minimum number of underscore-separated segments
                required after the ``test_`` prefix.

        Returns:
            A list of :class:`Finding` objects with category ``"test_naming"``.

        """
        if module.has_syntax_error:
            return []

        findings: list[Finding] = []
        file_path = str(module.path)

        for func in module.functions:
            if not func.name.startswith("test_"):
                continue
            segments = TestNamingScanner._count_segments(func.name)
            if segments < min_segments:
                findings.append(
                    Finding(
                        file=file_path,
                        line=func.lineno,
                        category="test_naming",
                        severity="medium",
                        description=(
                            f"Test function '{func.name}' has {segments} segments, "
                            f"expected >= {min_segments}"
                        ),
                        fix_type="manual",
                    )
                )

        for cls in module.classes:
            # Only check methods on Test* classes — methods named test_* on
            # non-test classes (e.g. protocol implementations like
            # _StubEngine.test_file_glob) are not test functions.
            if not cls.name.startswith("Test"):
                continue
            for method in cls.methods:
                if not method.name.startswith("test_"):
                    continue
                segments = TestNamingScanner._count_segments(method.name)
                if segments < min_segments:
                    findings.append(
                        Finding(
                            file=file_path,
                            line=method.lineno,
                            category="test_naming",
                            severity="medium",
                            description=(
                                f"Test method '{method.name}' has {segments} segments, "
                                f"expected >= {min_segments}"
                            ),
                            fix_type="manual",
                        )
                    )

        return findings

    @staticmethod
    def scan_file(path: Path, min_segments: int = 3) -> list[Finding]:
        """Backward-compatible wrapper that uses the registry to get an engine.

        Args:
            path: Path to a test file.
            min_segments: Minimum number of underscore-separated segments
                required after the ``test_`` prefix.

        Returns:
            A list of :class:`Finding` objects (empty if no engine matches or
            the file has a syntax error).

        """
        TestNamingScanner._ensure_python_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        return TestNamingScanner.scan_module(module, min_segments)

    @staticmethod
    def main() -> int:
        """Entry point for the test naming convention checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check test function naming: test_<unit>_<scenario>_<expected>. "
            "Flags functions with fewer than testing.test_naming_min_segments "
            "segments after test_."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        TestNamingScanner._ensure_python_engine()
        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "testing.check_test_naming")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(
                args.json, "check_test_naming disabled in settings.json"
            )
            return 0

        roots = ProjectConfig.existing_roots(ProjectConfig.test_roots(settings, py_langs))
        if not roots:
            print(
                "Error: no configured test directories exist on disk "
                f"({', '.join(str(r) for r in ProjectConfig.test_roots(settings, py_langs))})",
                file=sys.stderr,
            )
            return 1

        limits: list[int] = []
        for lang in sorted(py_langs):
            value = ProjectConfig.setting(
                settings, f"{lang}.testing.test_naming_min_segments", None
            )
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        min_segments = min(limits) if limits else 3

        violations: list[dict[str, Any]] = []
        total_test_functions = 0

        for test_root in roots:
            for py in ProjectConfig.iter_files(test_root, {".py"}):
                # Only scan test files (test_*.py or *_test.py)
                if not (py.name.startswith("test_") or py.name.endswith("_test.py")):
                    continue

                test_funcs = TestNamingScanner._find_test_functions(py)
                for func_name, line_no in test_funcs:
                    total_test_functions += 1
                    segments = TestNamingScanner._count_segments(func_name)
                    if segments < min_segments:
                        violations.append(
                            {
                                "file": str(py.relative_to(test_root)),
                                "line": line_no,
                                "function": func_name,
                                "segments": segments,
                                "min_required": min_segments,
                            }
                        )

        directories = [str(root) for root in roots]
        if args.json:
            print(
                json.dumps(
                    {
                        "directories": directories,
                        "total_test_functions": total_test_functions,
                        "violation_count": len(violations),
                        "min_segments": min_segments,
                        "violations": violations,
                    },
                    indent=2,
                )
            )
        else:
            print("=" * 70)
            print("TEST FUNCTION NAMING — VALIDATION REPORT")
            print("=" * 70)
            print(f"\nTest directories: {', '.join(directories)}")
            print(f"Minimum segments after test_: {min_segments}")
            print(f"Total test functions scanned: {total_test_functions}")
            print(f"Violations: {len(violations)}")
            if total_test_functions > 0:
                pct = (len(violations) / total_test_functions) * 100
                print(f"Violation rate: {pct:.1f}%")
            print()

            if violations:
                print(f"{'File':<55} {'Line':>5} {'Function':<45} {'Segs':>5}")
                print("-" * 115)
                for v in violations:
                    print(f"{v['file']:<55} {v['line']:>5} {v['function']:<45} {v['segments']:>5}")
                print()
                print(f"These test functions have fewer than {min_segments} segments")
                print("after the test_ prefix. The convention expects:")
                print("  test_<unit>_<scenario>_<expected_outcome>")
                print("Rename to include the scenario and expected outcome.")
            else:
                print("All test functions meet the naming convention.\n")

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(TestNamingScanner.main())
