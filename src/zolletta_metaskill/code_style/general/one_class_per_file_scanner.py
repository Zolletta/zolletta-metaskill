#!/usr/bin/env python3
"""Check the '1 class 1 file, 1 file 1 class' convention.

Reports three categories of violations:
  - Files with 2+ classes (should be split into separate files)
  - Files with 0 classes that are not __init__.py (utility/constant files —
    reported as low severity, not errors)
  - Class names that don't match the filename (snake_case -> PascalCase)

Configuration comes from ``.zolletta-metaskill/settings.json``:

- Scan roots: ``python.paths.source`` / ``php.autoload.psr-4`` (``src``
  when unconfigured), enumerated with git-ignore awareness.
- ``<language>.code_style.check_one_class_per_file`` — when false for
  every configured language the run reports SKIPPED.
- ``<language>.code_style.check_zero_class_files`` — when false for
  every scanned language, zero-class findings are filtered out
  (utility modules are allowed).

Usage:
    python3 one_class_per_file_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 always (report-only); 1 on usage errors such as no
           configured source directory existing on disk.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding, ModuleInfo


class OneClassPerFileScanner:
    """Check the '1 class 1 file, 1 file 1 class' convention."""

    @staticmethod
    def _snake_to_pascal(name: str) -> str:
        """Convert snake_case to PascalCase (e.g. my_class -> MyClass)."""
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def scan_module(module: ModuleInfo) -> list[Finding]:
        """Scan a parsed module and return findings for class-structure violations.

        Args:
            module: The :class:`ModuleInfo` produced by an engine.

        Returns:
            A list of :class:`Finding` objects.  Categories:
            ``"multi_class"`` (2+ classes), ``"zero_class"`` (no classes),
            ``"name_mismatch"`` (class name != filename).

        """
        if module.has_syntax_error:
            return []

        classes = module.classes
        file_path = str(module.path)

        if len(classes) > 1:
            names = ", ".join(c.name for c in classes)
            return [
                Finding(
                    file=file_path,
                    line=classes[0].lineno,
                    category="multi_class",
                    severity="high",
                    description=f"{len(classes)} classes: {names}",
                    fix_type="manual",
                )
            ]

        if len(classes) == 0:
            return [
                Finding(
                    file=file_path,
                    line=0,
                    category="zero_class",
                    severity="low",
                    description="No classes (utility/helper module)",
                    fix_type="skip",
                )
            ]

        # Exactly 1 class — check name match
        cls = classes[0]
        expected_pascal = OneClassPerFileScanner._snake_to_pascal(module.path.stem)
        if cls.name != expected_pascal and cls.name != module.path.stem:
            return [
                Finding(
                    file=file_path,
                    line=cls.lineno,
                    category="name_mismatch",
                    severity="medium",
                    description=(
                        f"Class '{cls.name}' doesn't match filename. "
                        f"Expected '{expected_pascal}' (or rename file to match class)"
                    ),
                    fix_type="manual",
                )
            ]

        return []

    @staticmethod
    def scan_file(path: Path) -> list[Finding]:
        """Backward-compatible wrapper that uses the registry to get an engine.

        Args:
            path: Path to a source file.

        Returns:
            A list of :class:`Finding` objects (empty if no engine matches or
            the file has a syntax error).

        """
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        return OneClassPerFileScanner.scan_module(module)

    @staticmethod
    def main() -> int:
        """Entry point for the one-class-per-file checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check '1 class 1 file, 1 file 1 class' convention. "
            "Scan roots and toggles come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_one_class_per_file"
        )
        if not languages:
            if args.json:
                print(
                    json.dumps(
                        {
                            "skipped": True,
                            "reason": "check_one_class_per_file disabled in settings.json",
                        }
                    )
                )
            else:
                print("=" * 70)
                print("1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT")
                print("=" * 70)
                print("\nResult: SKIPPED (check_one_class_per_file disabled in settings.json)\n")
            return 0

        roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, languages)
        )
        if not roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return 1

        ProjectConfig.ensure_engines()
        extensions = ProjectConfig.extensions_for(languages)
        report_zero = ProjectConfig.any_enabled(
            settings, languages, "code_style.check_zero_class_files"
        )

        files: list[Path] = []
        for root in roots:
            for path in ProjectConfig.iter_files(root, extensions):
                if path.name == "__init__.py":
                    continue
                files.append(path)
        all_findings: list[Finding] = []
        for path in files:
            all_findings.extend(OneClassPerFileScanner.scan_file(path))

        if not report_zero:
            all_findings = [f for f in all_findings if f.category != "zero_class"]

        multi_class = [f for f in all_findings if f.category == "multi_class"]
        zero_class = [f for f in all_findings if f.category == "zero_class"]
        name_mismatch = [f for f in all_findings if f.category == "name_mismatch"]

        has_violations = bool(all_findings)

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "scanned": len(files),
                        "violation_count": len(all_findings),
                        "violations": [
                            {
                                "file": f.file,
                                "line": f.line,
                                "category": f.category,
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
        print("1 CLASS 1 FILE, 1 FILE 1 CLASS — VALIDATION REPORT")
        print("=" * 70)

        if multi_class:
            print(f"\n## Files with 2+ classes ({len(multi_class)} files)\n")
            for f in multi_class:
                print(f"  {f.description}")
                print(f"    -> {f.file}")
                print("    Fix: split into one file per class")
        else:
            print("\n## Files with 2+ classes: none")

        if name_mismatch:
            print(f"\n## Class name != filename ({len(name_mismatch)} files)\n")
            for f in name_mismatch:
                print(f"  {f.description} (line {f.line})")
                print(f"    -> {f.file}")
        else:
            print("\n## Class name != filename: none")

        if report_zero:
            if zero_class:
                print(f"\n## Files with 0 classes ({len(zero_class)} files)\n")
                for f in zero_class:
                    print(f"  {f.file}")
                print(
                    "  (Low severity — utility/helper modules. "
                    "Set check_zero_class_files=false in settings.json to hide.)"
                )
            else:
                print("\n## Files with 0 classes: none")

        print()
        if has_violations:
            print("Result: violations found (report-only mode)")
        else:
            print("Result: all clear")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(OneClassPerFileScanner.main())
