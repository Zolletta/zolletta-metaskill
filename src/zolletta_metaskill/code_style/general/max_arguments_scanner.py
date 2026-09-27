#!/usr/bin/env python3
"""Flag functions and methods that declare too many parameters.

Language-agnostic sensor for the "max arguments" rule from Martin Fowler's
*Maintainability sensors for coding agents* ("Rules for typical AI
shortcomings") — long parameter lists signal a function doing too much or
a missing parameter object. The scanner consumes ``MethodInfo.params``
from the language engines (``ModuleInfo.functions`` +
``ClassInfo.methods``), so it needs no per-language parsing of its own.

Parameter counting follows ruff ``PLR0913`` semantics: positional-only,
positional, and keyword-only parameters count; the receiver
(``self``/``cls``) and variadics (``*args``/``**kwargs``/``...$args``)
do not. Only module-level functions and class methods are visible to
``ModuleInfo`` — nested functions, lambdas, and PHP closures are not
counted.

Which files are scanned and with what limit is driven entirely by
``.zolletta-metaskill/settings.json`` (created by the setup guard):

- The project's language(s) are read from settings.json — the top-level
  ``language`` field plus each populated ``<language>`` section — and
  mapped to file extensions via the engine registry (``python`` →
  ``.py``, ``php`` → ``.php``). Polyglot projects scan every configured
  language.
- Each language's ``code_style.check_max_arguments`` toggle is honoured:
  a language with the check disabled is not scanned, and when it is off
  for every configured language the run reports SKIPPED (exit 0).
- The limit is read from each enabled language's
  ``code_style.max_arguments`` (the smallest wins when several are
  configured); 5 is the default when none is configured.
- Scan roots come from settings: ``python.paths.source`` for Python,
  ``php.autoload.psr-4`` directories for PHP (``src`` when unconfigured).
- Files ignored by git (``.gitignore``, ``.git/info/exclude``,
  ``core.excludesFile``) are skipped. Outside a git repository every
  file matching the extensions is scanned.

Usage:
    python3 max_arguments_scanner.py [--json]

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


class MaxArgumentsScanner:
    """Flag functions and methods exceeding a parameter-count limit."""

    DEFAULT_MAX_ARGS = 5
    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH

    @staticmethod
    def resolve_extensions(settings_path: Path) -> set[str]:
        """Return the file extensions to scan for the project.

        Languages come from settings.json — the top-level ``language``
        field plus each populated ``<language>`` section — filtered to
        those whose ``code_style.check_max_arguments`` is not ``false``
        (so a polyglot project only scans the languages with the check
        on). Returns an empty set when every configured language has the
        check disabled. When nothing usable is configured, falls back to
        every registered engine's extensions.
        """
        ProjectConfig.ensure_engines()
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_max_arguments"
        )
        extensions = ProjectConfig.extensions_for(languages)
        if not extensions and languages:
            extensions = ProjectConfig.extensions_for(
                set(EngineRegistry.available_languages())
            )
        return extensions

    @staticmethod
    def resolve_max_args(settings_path: Path) -> int:
        """Return the maximum allowed parameters per function/method.

        The smallest ``<language>.code_style.max_arguments`` across the
        enabled languages configured in settings.json; falls back to
        ``DEFAULT_MAX_ARGS`` when nothing is configured.
        """
        settings = ProjectConfig.load_settings(settings_path)
        langs = ProjectConfig.enabled_languages(
            settings, "code_style.check_max_arguments"
        )
        limits = []
        for lang in sorted(langs):
            value = ProjectConfig.setting(
                settings, f"{lang}.code_style.max_arguments", None
            )
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        return min(limits) if limits else MaxArgumentsScanner.DEFAULT_MAX_ARGS

    @staticmethod
    def _records(module: ModuleInfo, max_args: int) -> list[dict[str, Any]]:
        """Return one violation record per over-limit function/method.

        Each record has ``kind`` (``"Function"`` or ``"Method"``),
        ``function`` (bare name, or ``Class.method`` for methods),
        ``line``, and ``params`` keys. Modules with syntax errors produce
        no records.
        """
        if module.has_syntax_error:
            return []
        records: list[dict[str, Any]] = []
        for func in module.functions:
            if len(func.params) > max_args:
                records.append(
                    {
                        "kind": "Function",
                        "function": func.name,
                        "line": func.lineno,
                        "params": len(func.params),
                    }
                )
        for cls in module.classes:
            for method in cls.methods:
                if len(method.params) > max_args:
                    records.append(
                        {
                            "kind": "Method",
                            "function": f"{cls.name}.{method.name}",
                            "line": method.lineno,
                            "params": len(method.params),
                        }
                    )
        return records

    @staticmethod
    def scan_module(module: ModuleInfo, max_args: int = DEFAULT_MAX_ARGS) -> list[Finding]:
        """Return a ``max_arguments`` finding per over-limit function.

        Args:
            module: The parsed module to inspect.
            max_args: Maximum allowed declared parameters.

        Returns:
            A list of :class:`Finding` objects, one per function or method
            declaring more than *max_args* parameters.

        """
        return [
            Finding(
                file=str(module.path),
                line=record["line"],
                category="max_arguments",
                severity="medium",
                description=(
                    f"{record['kind']} '{record['function']}' has "
                    f"{record['params']} parameters (max {max_args})"
                ),
                fix_type="manual",
            )
            for record in MaxArgumentsScanner._records(module, max_args)
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
    def scan_file(path: Path, max_args: int = DEFAULT_MAX_ARGS) -> list[Finding]:
        """Return ``max_arguments`` findings for *path*.

        Args:
            path: Path to a source file handled by a registered engine.
            max_args: Maximum allowed declared parameters.

        Returns:
            A list of :class:`Finding` objects; empty when the file cannot
            be parsed or every function is within the limit.

        """
        module = MaxArgumentsScanner._parse_file(path)
        if module is None:
            return []
        return MaxArgumentsScanner.scan_module(module, max_args)

    @staticmethod
    def scan_directory(
        root: Path,
        max_args: int | None = None,
        extensions: set[str] | None = None,
        settings_path: Path | None = None,
    ) -> list[Finding]:
        """Scan matching files under *root* for max-arguments violations.

        When *extensions* or *max_args* is omitted it is resolved from
        *settings_path* (default ``.zolletta-metaskill/settings.json``).
        Files that cannot be parsed are skipped with a warning on stderr.
        """
        path = settings_path or MaxArgumentsScanner.DEFAULT_SETTINGS_PATH
        if extensions is None:
            extensions = MaxArgumentsScanner.resolve_extensions(path)
        if max_args is None:
            max_args = MaxArgumentsScanner.resolve_max_args(path)
        findings: list[Finding] = []
        for file_path in ProjectConfig.iter_files(root, extensions):
            findings.extend(MaxArgumentsScanner.scan_file(file_path, max_args))
        return findings

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def _scan_roots(
        roots: list[Path], extensions: set[str], max_args: int
    ) -> tuple[int, list[dict[str, Any]]]:
        """Scan *roots* and return ``(file_count, violation_records)``."""
        files: list[Path] = []
        for root in roots:
            files.extend(ProjectConfig.iter_files(root, extensions))
        violations: list[dict[str, Any]] = []
        for path in files:
            module = MaxArgumentsScanner._parse_file(path)
            if module is None:
                continue
            for record in MaxArgumentsScanner._records(module, max_args):
                violations.append(
                    {
                        "file": str(path),
                        "function": record["function"],
                        "kind": record["kind"],
                        "line": record["line"],
                        "params": record["params"],
                        "over": record["params"] - max_args,
                    }
                )
        violations.sort(key=lambda v: v["params"], reverse=True)
        return len(files), violations

    @staticmethod
    def _emit_json(
        roots: list[Path], scanned: int, max_args: int, violations: list[dict[str, Any]]
    ) -> None:
        """Print the JSON report."""
        print(
            json.dumps(
                {
                    "directories": [str(root) for root in roots],
                    "scanned": scanned,
                    "max_arguments": max_args,
                    "violation_count": len(violations),
                    "violations": [
                        {
                            "file": v["file"],
                            "function": v["function"],
                            "line": v["line"],
                            "params": v["params"],
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
        roots: list[Path], scanned: int, max_args: int, violations: list[dict[str, Any]]
    ) -> None:
        """Print the text report."""
        print("=" * 70)
        print("MAX ARGUMENTS — VALIDATION REPORT")
        print("=" * 70)
        roots_str = ", ".join(str(root) for root in roots)
        print(f"\nScanned {scanned} files under {roots_str} (max {max_args} parameters)")

        if violations:
            print(f"\n## Functions exceeding the limit ({len(violations)})\n")
            for v in violations:
                print(
                    f"  {v['params']:>6} params  {v['file']}:{v['line']}  "
                    f"{v['function']}  (over by {v['over']})"
                )
            print(
                "\n  Fix: introduce a parameter object or split the function, "
                "or raise max_arguments in settings.json if the arity is "
                "justified (DTOs, value objects, DI-heavy constructors)."
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
        """Entry point for the max arguments scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Flag functions and methods declaring too many "
            "parameters (language-agnostic; PLR0913-style counting). Scan "
            "roots and the limit come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON instead of text",
        )
        args = parser.parse_args()

        settings_path = MaxArgumentsScanner.DEFAULT_SETTINGS_PATH
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_max_arguments"
        )
        if not languages:
            ProjectConfig.emit_skipped(
                args.json, "check_max_arguments disabled in settings.json"
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
        max_args = MaxArgumentsScanner.resolve_max_args(settings_path)
        scanned, violations = MaxArgumentsScanner._scan_roots(
            roots, extensions, max_args
        )
        if args.json:
            MaxArgumentsScanner._emit_json(roots, scanned, max_args, violations)
        else:
            MaxArgumentsScanner._emit_text(roots, scanned, max_args, violations)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(MaxArgumentsScanner.main())
