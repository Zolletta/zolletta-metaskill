#!/usr/bin/env python3
"""Flag functions and methods with high cyclomatic complexity.

Language-agnostic sensor for the cyclomatic-complexity rule from
Martin Fowler's *Maintainability sensors for coding agents*
("Rules for typical AI shortcomings") — deeply branched functions are
hard to review, test, and modify, and are a classic AI-generation
failure mode.

Python files are parsed with stdlib ``ast``; PHP files via
``PHPEngine.parse_raw`` (tree-sitter-php, an optional dependency — its
absence degrades to a stderr warning and skipped files). Complexity is
computed per ``FunctionDef``/``AsyncFunctionDef``/closure, including
nested ones, which are reported independently.

Python counting matches ruff ``C901`` (mccabe): a function starts at 1;
each ``if``/``elif``, ``for``/``async for``, ``while``, ``except``
handler, non-catch-all ``match`` case, ``try`` ``else`` clause, and
nested ``def`` adds 1. Boolean operators, ternaries, comprehensions,
``assert``, ``with``, and ``else``/``finally`` blocks add nothing.

PHP counting adds 1 per ``if``, ``elseif``, ``for``, ``foreach``,
``while``, ``do``, ``case``, ``match`` arm, ``catch`` clause, ternary,
``&&``/``||``/``??`` operator, and nested function/closure.

Which files are scanned and with what limit is driven entirely by
``.zolletta-metaskill/settings.json`` (created by the setup guard):

- The project's language(s) are read from settings.json — the top-level
  ``language`` field plus each populated ``<language>`` section — and
  mapped to file extensions via the engine registry (``python`` →
  ``.py``, ``php`` → ``.php``). Polyglot projects scan every configured
  language.
- Each language's ``code_style.check_cyclomatic_complexity`` toggle is
  honoured: a language with the check disabled is not scanned, and when
  it is off for every configured language the run reports SKIPPED
  (exit 0).
- The limit is read from each enabled language's
  ``code_style.max_cyclomatic_complexity`` (the smallest wins when
  several are configured); 10 is the default when none is configured.
- Scan roots come from settings: ``python.paths.source`` for Python,
  ``php.autoload.psr-4`` directories for PHP (``src`` when
  unconfigured).
- Files ignored by git (``.gitignore``, ``.git/info/exclude``,
  ``core.excludesFile``) are skipped. Outside a git repository every
  file matching the extensions is scanned.

Usage:
    python3 cyclomatic_complexity_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 on success (violations are report-only); 1 on errors such
           as no configured source directory existing on disk.

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding


class CyclomaticComplexityScanner:
    """Flag functions and methods exceeding a complexity limit."""

    DEFAULT_MAX_COMPLEXITY = 10
    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH

    # tree-sitter-php node types that add a decision point.
    _PHP_DECISION_TYPES = frozenset(
        {
            "if_statement",
            "else_if_clause",
            "for_statement",
            "foreach_statement",
            "while_statement",
            "do_statement",
            "case_statement",
            "match_conditional_expression",
            "catch_clause",
            "conditional_expression",
        }
    )
    # tree-sitter-php node types that introduce a new function scope.
    _PHP_FUNCTION_TYPES = frozenset(
        {
            "function_definition",
            "method_declaration",
            "anonymous_function",
            "arrow_function",
        }
    )
    # tree-sitter-php type wrappers that qualify member names.
    _PHP_TYPE_TYPES = frozenset(
        {
            "class_declaration",
            "interface_declaration",
            "trait_declaration",
            "enum_declaration",
        }
    )
    _PHP_BINARY_OPERATORS = frozenset({"&&", "||", "??"})

    @staticmethod
    def resolve_extensions(settings_path: Path) -> set[str]:
        """Return the file extensions to scan for the project.

        Languages come from settings.json — the top-level ``language``
        field plus each populated ``<language>`` section — filtered to
        those whose ``code_style.check_cyclomatic_complexity`` is not
        ``false`` (so a polyglot project only scans the languages with
        the check on). Returns an empty set when every configured
        language has the check disabled. When nothing usable is
        configured, falls back to every registered engine's extensions.
        """
        ProjectConfig.ensure_engines()
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_cyclomatic_complexity"
        )
        extensions = ProjectConfig.extensions_for(languages)
        if not extensions and languages:
            extensions = ProjectConfig.extensions_for(
                set(EngineRegistry.available_languages())
            )
        return extensions

    @staticmethod
    def resolve_max_complexity(settings_path: Path) -> int:
        """Return the maximum allowed cyclomatic complexity.

        The smallest ``<language>.code_style.max_cyclomatic_complexity``
        across the enabled languages configured in settings.json; falls
        back to ``DEFAULT_MAX_COMPLEXITY`` when nothing is configured.
        """
        settings = ProjectConfig.load_settings(settings_path)
        langs = ProjectConfig.enabled_languages(
            settings, "code_style.check_cyclomatic_complexity"
        )
        limits = []
        for lang in sorted(langs):
            value = ProjectConfig.setting(
                settings, f"{lang}.code_style.max_cyclomatic_complexity", None
            )
            if isinstance(value, int) and not isinstance(value, bool):
                limits.append(value)
        return (
            min(limits) if limits
            else CyclomaticComplexityScanner.DEFAULT_MAX_COMPLEXITY
        )

    # ------------------------------------------------------------------
    # Python (stdlib ast, ruff C901 semantics)
    # ------------------------------------------------------------------

    @staticmethod
    def _python_decision(node: ast.AST) -> int:
        """Return the complexity contribution of one ``ast`` node."""
        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.ExceptHandler,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            return 1
        if isinstance(node, ast.match_case):
            pattern = node.pattern
            is_catch_all = (
                isinstance(pattern, ast.MatchAs)
                and pattern.pattern is None
                and node.guard is None
            )
            return 0 if is_catch_all else 1
        if isinstance(node, (ast.Try, ast.TryStar)):
            return 1 if node.orelse else 0
        return 0

    @staticmethod
    def _python_complexity(func: ast.AST) -> int:
        """Return the cyclomatic complexity of one function node.

        The function starts at 1; decision points inside its body are
        added. Nested ``def`` statements each count 1 for the enclosing
        function and are walked as well — matching ruff ``C901``, which
        reports each nested function's complexity independently while
        folding its decisions into the enclosing count.
        """
        body = getattr(func, "body", [])
        complexity = 1
        for stmt in body:
            for node in ast.walk(stmt):
                complexity += CyclomaticComplexityScanner._python_decision(node)
        return complexity

    @staticmethod
    def _python_functions(tree: ast.AST) -> list[tuple[str, ast.AST]]:
        """Return ``(qualified_name, node)`` for every function in *tree*.

        Functions nested inside other functions or classes are found
        wherever they appear (``if`` blocks, ``try`` bodies, …) and are
        qualified as ``Outer.inner``/``Class.method``.
        """
        found: list[tuple[str, ast.AST]] = []

        def _visit(node: ast.AST, prefix: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = f"{prefix}.{child.name}" if prefix else child.name
                    found.append((name, child))
                    _visit(child, name)
                elif isinstance(child, ast.ClassDef):
                    name = f"{prefix}.{child.name}" if prefix else child.name
                    _visit(child, name)
                else:
                    _visit(child, prefix)

        _visit(tree, "")
        return found

    @staticmethod
    def _python_records(path: Path) -> list[dict[str, Any]]:
        """Return complexity records for every function in a ``.py`` file."""
        try:
            tree = ast.parse(path.read_bytes())
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            return []
        records = []
        for name, node in CyclomaticComplexityScanner._python_functions(tree):
            records.append(
                {
                    "kind": "Function",
                    "function": name,
                    "line": getattr(node, "lineno", 1),
                    "complexity": CyclomaticComplexityScanner._python_complexity(node),
                }
            )
        return records

    # ------------------------------------------------------------------
    # PHP (tree-sitter-php via PHPEngine.parse_raw)
    # ------------------------------------------------------------------

    @staticmethod
    def _php_name(node: Any, source: bytes) -> str:
        """Return the declared name of a PHP function node."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return "closure" if node.type == "anonymous_function" else "arrow"
        return source[name_node.start_byte : name_node.end_byte].decode(
            "utf-8", errors="replace"
        )

    @staticmethod
    def _php_complexity(root: Any) -> int:
        """Return the cyclomatic complexity of one PHP function node.

        The function starts at 1; each decision-point node inside adds 1.
        Nested function roots (closures, arrow functions) add 1 and are
        walked as well — they are also reported independently.
        """
        complexity = 1
        stack = list(root.children)
        while stack:
            node = stack.pop()
            if (
                node.type in CyclomaticComplexityScanner._PHP_FUNCTION_TYPES
                or node.type in CyclomaticComplexityScanner._PHP_DECISION_TYPES
            ):
                complexity += 1
            elif node.type == "binary_expression":
                complexity += sum(
                    1
                    for child in node.children
                    if child.type
                    in CyclomaticComplexityScanner._PHP_BINARY_OPERATORS
                )
            stack.extend(node.children)
        return complexity

    @staticmethod
    def _php_functions(root: Any, source: bytes) -> list[tuple[str, Any]]:
        """Return ``(qualified_name, node)`` for every PHP function root."""
        found: list[tuple[str, Any]] = []

        def _visit(node: Any, prefix: str) -> None:
            for child in node.children:
                if child.type in CyclomaticComplexityScanner._PHP_FUNCTION_TYPES:
                    name = CyclomaticComplexityScanner._php_name(child, source)
                    qualified = f"{prefix}.{name}" if prefix else name
                    found.append((qualified, child))
                    _visit(child, qualified)
                elif child.type in CyclomaticComplexityScanner._PHP_TYPE_TYPES:
                    name = CyclomaticComplexityScanner._php_name(child, source)
                    qualified = f"{prefix}.{name}" if prefix else name
                    _visit(child, qualified)
                else:
                    _visit(child, prefix)

        _visit(root, "")
        return found

    @staticmethod
    def _php_records(engine: PHPEngine, path: Path) -> list[dict[str, Any]]:
        """Return complexity records for every function in a ``.php`` file."""
        try:
            tree, source = engine.parse_raw(path)
        except (OSError, ImportError):
            print(f"Warning: could not parse '{path}'", file=sys.stderr)
            return []
        if tree.root_node.has_error:
            return []
        kinds = {
            "method_declaration": "Method",
            "function_definition": "Function",
        }
        records = []
        for name, node in CyclomaticComplexityScanner._php_functions(
            tree.root_node, source
        ):
            records.append(
                {
                    "kind": kinds.get(node.type, "Closure"),
                    "function": name,
                    "line": node.start_point[0] + 1,
                    "complexity": CyclomaticComplexityScanner._php_complexity(node),
                }
            )
        return records

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def _records_for_file(path: Path) -> list[dict[str, Any]] | None:
        """Return per-function records for *path*, or ``None`` if unhandled."""
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:
            return None
        if isinstance(engine, PHPEngine):
            return CyclomaticComplexityScanner._php_records(engine, path)
        return CyclomaticComplexityScanner._python_records(path)

    @staticmethod
    def _findings(
        records: list[dict[str, Any]], path: Path, max_complexity: int
    ) -> list[Finding]:
        """Return a ``cyclomatic_complexity`` finding per over-limit function."""
        return [
            Finding(
                file=str(path),
                line=record["line"],
                category="cyclomatic_complexity",
                severity="medium",
                description=(
                    f"{record['kind']} '{record['function']}' has cyclomatic "
                    f"complexity {record['complexity']} (max {max_complexity})"
                ),
                fix_type="manual",
            )
            for record in records
            if record["complexity"] > max_complexity
        ]

    @staticmethod
    def scan_file(
        path: Path, max_complexity: int = DEFAULT_MAX_COMPLEXITY
    ) -> list[Finding]:
        """Return ``cyclomatic_complexity`` findings for *path*.

        Args:
            path: Path to a source file handled by a registered engine.
            max_complexity: Maximum allowed cyclomatic complexity.

        Returns:
            A list of :class:`Finding` objects; empty when the file cannot
            be parsed or every function is within the limit.

        """
        records = CyclomaticComplexityScanner._records_for_file(path)
        if records is None:
            return []
        return CyclomaticComplexityScanner._findings(records, path, max_complexity)

    @staticmethod
    def scan_directory(
        root: Path,
        max_complexity: int | None = None,
        extensions: set[str] | None = None,
        settings_path: Path | None = None,
    ) -> list[Finding]:
        """Scan matching files under *root* for complexity violations.

        When *extensions* or *max_complexity* is omitted it is resolved
        from *settings_path* (default
        ``.zolletta-metaskill/settings.json``). Files that cannot be
        parsed are skipped with a warning on stderr.
        """
        path = settings_path or CyclomaticComplexityScanner.DEFAULT_SETTINGS_PATH
        if extensions is None:
            extensions = CyclomaticComplexityScanner.resolve_extensions(path)
        if max_complexity is None:
            max_complexity = CyclomaticComplexityScanner.resolve_max_complexity(path)
        findings: list[Finding] = []
        for file_path in ProjectConfig.iter_files(root, extensions):
            findings.extend(
                CyclomaticComplexityScanner.scan_file(file_path, max_complexity)
            )
        return findings

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def _scan_roots(
        roots: list[Path], extensions: set[str], max_complexity: int
    ) -> tuple[int, list[dict[str, Any]]]:
        """Scan *roots* and return ``(file_count, violation_records)``."""
        files: list[Path] = []
        for root in roots:
            files.extend(ProjectConfig.iter_files(root, extensions))
        violations: list[dict[str, Any]] = []
        for path in files:
            records = CyclomaticComplexityScanner._records_for_file(path)
            if records is None:
                continue
            for record in records:
                if record["complexity"] > max_complexity:
                    violations.append(
                        {
                            "file": str(path),
                            "function": record["function"],
                            "kind": record["kind"],
                            "line": record["line"],
                            "complexity": record["complexity"],
                            "over": record["complexity"] - max_complexity,
                        }
                    )
        violations.sort(key=lambda v: v["complexity"], reverse=True)
        return len(files), violations

    @staticmethod
    def _emit_json(
        roots: list[Path],
        scanned: int,
        max_complexity: int,
        violations: list[dict[str, Any]],
    ) -> None:
        """Print the JSON report."""
        print(
            json.dumps(
                {
                    "directories": [str(root) for root in roots],
                    "scanned": scanned,
                    "max_complexity": max_complexity,
                    "violation_count": len(violations),
                    "violations": [
                        {
                            "file": v["file"],
                            "function": v["function"],
                            "line": v["line"],
                            "complexity": v["complexity"],
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
        roots: list[Path],
        scanned: int,
        max_complexity: int,
        violations: list[dict[str, Any]],
    ) -> None:
        """Print the text report."""
        print("=" * 70)
        print("CYCLOMATIC COMPLEXITY — VALIDATION REPORT")
        print("=" * 70)
        roots_str = ", ".join(str(root) for root in roots)
        print(
            f"\nScanned {scanned} files under {roots_str} "
            f"(max complexity {max_complexity})"
        )

        if violations:
            print(f"\n## Functions exceeding the limit ({len(violations)})\n")
            for v in violations:
                print(
                    f"  {v['complexity']:>6}  {v['file']}:{v['line']}  "
                    f"{v['function']}  (over by {v['over']})"
                )
            print(
                "\n  Fix: extract a collaborator or decompose the function, "
                "or raise max_cyclomatic_complexity in settings.json if the "
                "complexity is justified (parsers, state machines, generated "
                "code)."
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
        """Entry point for the cyclomatic complexity scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Flag functions and methods with high cyclomatic "
            "complexity (language-agnostic; ruff C901-style counting). Scan "
            "roots and the limit come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON instead of text",
        )
        args = parser.parse_args()

        settings_path = CyclomaticComplexityScanner.DEFAULT_SETTINGS_PATH
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.scan_languages(
            settings, "code_style.check_cyclomatic_complexity"
        )
        if not languages:
            ProjectConfig.emit_skipped(
                args.json, "check_cyclomatic_complexity disabled in settings.json"
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
        max_complexity = CyclomaticComplexityScanner.resolve_max_complexity(
            settings_path
        )
        scanned, violations = CyclomaticComplexityScanner._scan_roots(
            roots, extensions, max_complexity
        )
        if args.json:
            CyclomaticComplexityScanner._emit_json(
                roots, scanned, max_complexity, violations
            )
        else:
            CyclomaticComplexityScanner._emit_text(
                roots, scanned, max_complexity, violations
            )
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(CyclomaticComplexityScanner.main())
