#!/usr/bin/env python3
"""Flag functions and methods that exceed a configurable line count.

Language-agnostic sensor for the "function length" rule from Martin
Fowler's *Maintainability sensors for coding agents* ("Rules for typical
AI shortcomings") — long functions signal a unit doing too much or a
missing extraction. The scanner consumes ``MethodInfo.lineno`` /
``end_lineno`` from the language engines (``ModuleInfo.functions`` +
``ClassInfo.methods``), so it needs no per-language parsing of its own.

The metric is a line span — ``end_lineno - lineno + 1`` — covering the
signature and body (docstring included) but not decorators or docblocks,
which sit above the definition line. Lines are not statements: comments
and blank lines inflate the count compared to ruff ``PLR0915``
(``max-statements``); the exposed threshold is intentionally lenient for
triage. Only module-level functions and class methods are visible to
``ModuleInfo`` — nested functions, lambdas, and PHP closures are not
measured individually (their lines count toward the parent's span).

Which files are scanned and with what limit is driven entirely by
``.zolletta-metaskill/settings.json`` (created by the setup guard):

- The project's language(s) are read from settings.json — the top-level
  ``language`` field plus each populated ``<language>`` section — and
  mapped to file extensions via the engine registry (``python`` →
  ``.py``, ``php`` → ``.php``). Polyglot projects scan every configured
  language.
- Each language's ``code_style.check_function_length`` toggle is
  honoured: a language with the check disabled is not scanned, and when
  it is off for every configured language the run reports SKIPPED
  (exit 0).
- The limit is read from each enabled language's
  ``code_style.max_function_length`` (the smallest wins when several
  are configured); 100 is the default when none is configured.
- Scan roots come from settings: ``python.paths.source`` for Python,
  ``php.autoload.psr-4`` directories for PHP (``src`` when unconfigured).
- Files ignored by git (``.gitignore``, ``.git/info/exclude``,
  ``core.excludesFile``) are skipped. Outside a git repository every
  file matching the extensions is scanned.

Usage:
    python3 function_length_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 on success (violations are report-only); 1 on errors such
           as no configured source directory existing on disk.

"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding, ModuleInfo


class FunctionLengthScanner:
    """Flag functions and methods exceeding a line-count limit."""

    DEFAULT_MAX_FUNCTION_LINES = 100
    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH

    @staticmethod
    def resolve_extensions(settings_path: Path) -> set[str]:
        """Return the file extensions to scan for the project.

        Languages come from settings.json — the top-level ``language``
        field plus each populated ``<language>`` section — filtered to
        those whose ``code_style.check_function_length`` is not ``false``
        (so a polyglot project only scans the languages with the check
        on). Returns an empty set when every configured language has the
        check disabled. When nothing usable is configured, falls back to
        every registered engine's extensions.
        """
        ProjectConfig.ensure_engines()
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_function_length"
        )
        extensions = ProjectConfig.extensions_for(languages)
        if not extensions and languages:
            extensions = ProjectConfig.extensions_for(
                set(EngineRegistry.available_languages())
            )
        return extensions

    @staticmethod
    def resolve_max_lines(settings_path: Path) -> int:
        """Return the maximum allowed lines per function/method.

        The smallest ``<language>.code_style.max_function_length``
        across the enabled languages configured in settings.json; falls
        back to ``DEFAULT_MAX_FUNCTION_LINES`` when nothing is
        configured.
        """
        settings = ProjectConfig.load_settings(settings_path)
        langs = ProjectConfig.enabled_languages(
            settings, "code_style.check_function_length"
        )
        limits = []
        for lang in sorted(langs):
            value = ProjectConfig.setting(
                settings, f"{lang}.code_style.max_function_length", None
            )
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        return min(limits) if limits else FunctionLengthScanner.DEFAULT_MAX_FUNCTION_LINES

    @staticmethod
    def _records(module: ModuleInfo, max_lines: int) -> list[dict[str, Any]]:
        """Return one violation record per over-limit function/method.

        Each record has ``kind`` (``"Function"`` or ``"Method"``),
        ``function`` (bare name, or ``Class.method`` for methods),
        ``line``, ``end_line``, and ``lines`` keys. Modules with syntax
        errors produce no records.
        """
        if module.has_syntax_error:
            return []
        records: list[dict[str, Any]] = []
        for func in module.functions:
            lines = func.end_lineno - func.lineno + 1
            if lines > max_lines:
                records.append(
                    {
                        "kind": "Function",
                        "function": func.name,
                        "line": func.lineno,
                        "end_line": func.end_lineno,
                        "lines": lines,
                    }
                )
        for cls in module.classes:
            for method in cls.methods:
                lines = method.end_lineno - method.lineno + 1
                if lines > max_lines:
                    records.append(
                        {
                            "kind": "Method",
                            "function": f"{cls.name}.{method.name}",
                            "line": method.lineno,
                            "end_line": method.end_lineno,
                            "lines": lines,
                        }
                    )
        return records

    @staticmethod
    def scan_module(
        module: ModuleInfo, max_lines: int = DEFAULT_MAX_FUNCTION_LINES
    ) -> list[Finding]:
        """Return a ``function_length`` finding per over-limit function.

        Args:
            module: The parsed module to inspect.
            max_lines: Maximum allowed lines per function/method.

        Returns:
            A list of :class:`Finding` objects, one per function or
            method spanning more than *max_lines* lines.

        """
        return [
            Finding(
                file=str(module.path),
                line=record["line"],
                category="function_length",
                severity="medium",
                description=(
                    f"{record['kind']} '{record['function']}' has "
                    f"{record['lines']} lines (max {max_lines})"
                ),
                fix_type="manual",
            )
            for record in FunctionLengthScanner._records(module, max_lines)
        ]

    @staticmethod
    def _parse_file(path: Path) -> ModuleInfo | None:
        """Parse *path* via its engine, or ``None`` when unparsable.

        Files without a registered engine, unreadable files, and PHP
        files on hosts missing the optional ``tree-sitter-php``
        dependency all degrade to ``None`` (a stderr warning for the
        failure cases).
        """
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:
            return None
        try:
            return engine.parse_module(path)
        except (OSError, ImportError):
            print(f"Warning: could not parse '{path}'", file=sys.stderr)
            return None

    @staticmethod
    def scan_file(
        path: Path, max_lines: int = DEFAULT_MAX_FUNCTION_LINES
    ) -> list[Finding]:
        """Return ``function_length`` findings for *path*.

        Args:
            path: Path to a source file handled by a registered engine.
            max_lines: Maximum allowed lines per function/method.

        Returns:
            A list of :class:`Finding` objects; empty when the file
            cannot be parsed or every function is within the limit.

        """
        module = FunctionLengthScanner._parse_file(path)
        if module is None:
            return []
        return FunctionLengthScanner.scan_module(module, max_lines)

    @staticmethod
    def scan_directory(
        root: Path,
        max_lines: int | None = None,
        extensions: set[str] | None = None,
        settings_path: Path | None = None,
    ) -> list[Finding]:
        """Scan matching files under *root* for function-length violations.

        When *extensions* or *max_lines* is omitted it is resolved from
        *settings_path* (default ``.zolletta-metaskill/settings.json``).
        Files that cannot be parsed are skipped with a warning on stderr.
        """
        path = settings_path or FunctionLengthScanner.DEFAULT_SETTINGS_PATH
        if extensions is None:
            extensions = FunctionLengthScanner.resolve_extensions(path)
        if max_lines is None:
            max_lines = FunctionLengthScanner.resolve_max_lines(path)
        findings: list[Finding] = []
        for file_path in ProjectConfig.iter_files(root, extensions):
            findings.extend(FunctionLengthScanner.scan_file(file_path, max_lines))
        return findings

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def _scan_roots(
        roots: list[Path], extensions: set[str], max_lines: int
    ) -> tuple[int, list[dict[str, Any]]]:
        """Scan *roots* and return ``(file_count, violation_records)``."""
        files: list[Path] = []
        for root in roots:
            files.extend(ProjectConfig.iter_files(root, extensions))
        violations: list[dict[str, Any]] = []
        for path in files:
            module = FunctionLengthScanner._parse_file(path)
            if module is None:
                continue
            for record in FunctionLengthScanner._records(module, max_lines):
                violations.append(
                    {
                        "file": str(path),
                        "function": record["function"],
                        "kind": record["kind"],
                        "line": record["line"],
                        "end_line": record["end_line"],
                        "lines": record["lines"],
                        "over": record["lines"] - max_lines,
                    }
                )
        violations.sort(key=lambda v: v["lines"], reverse=True)
        return len(files), violations

    @staticmethod
    def _emit_json(
        roots: list[Path], scanned: int, max_lines: int, violations: list[dict[str, Any]]
    ) -> None:
        """Print the JSON report."""
        print(
            json.dumps(
                {
                    "directories": [str(root) for root in roots],
                    "scanned": scanned,
                    "max_function_length": max_lines,
                    "violation_count": len(violations),
                    "violations": [
                        {
                            "file": v["file"],
                            "function": v["function"],
                            "line": v["line"],
                            "end_line": v["end_line"],
                            "lines": v["lines"],
                            "over": v["over"],
                        }
                        for v in violations
                    ],
                },
                indent=2,
            )
        )

    @staticmethod
    def _emit_text(
        roots: list[Path], scanned: int, max_lines: int, violations: list[dict[str, Any]]
    ) -> None:
        """Print the text report."""
        print("=" * 70)
        print("FUNCTION LENGTH — VALIDATION REPORT")
        print("=" * 70)
        roots_str = ", ".join(str(root) for root in roots)
        print(f"\nScanned {scanned} files under {roots_str} (max {max_lines} lines)")

        if violations:
            print(f"\n## Functions exceeding the limit ({len(violations)})\n")
            for v in violations:
                print(
                    f"  {v['lines']:>6} lines  {v['file']}:{v['line']}-{v['end_line']}  "
                    f"{v['function']}  (over by {v['over']})"
                )
            print(
                "\n  Fix: split the function by responsibility, or raise "
                "max_function_length in settings.json if the length is "
                "justified (dispatch tables, generated code)."
            )
        else:
            print("\n## Functions exceeding the limit: none")

        print()
        if violations:
            print("Result: violations found (report-only mode)")
        else:
            print("Result: all clear")

    @staticmethod
    def main() -> int:
        """Entry point for the function length scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Flag functions and methods that exceed a maximum "
            "line count (language-agnostic; signature-to-end line span). "
            "Scan roots and the limit come from "
            ".zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON instead of text",
        )
        args = parser.parse_args()

        settings_path = FunctionLengthScanner.DEFAULT_SETTINGS_PATH
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_function_length"
        )
        if not languages:
            ProjectConfig.emit_skipped(
                args.json, "check_function_length disabled in settings.json"
            )
            return 0

        roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, languages)
        )
        if not roots:
            print(
                "Error: no configured source directories exist on disk "
                f"({', '.join(str(r) for r in ProjectConfig.source_roots(settings, languages))})",
                file=sys.stderr,
            )
            return 1

        extensions = ProjectConfig.extensions_for(languages)
        max_lines = FunctionLengthScanner.resolve_max_lines(settings_path)
        scanned, violations = FunctionLengthScanner._scan_roots(
            roots, extensions, max_lines
        )
        if args.json:
            FunctionLengthScanner._emit_json(roots, scanned, max_lines, violations)
        else:
            FunctionLengthScanner._emit_text(roots, scanned, max_lines, violations)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(FunctionLengthScanner.main())
