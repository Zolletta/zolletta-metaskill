#!/usr/bin/env python3
"""Emit the project's internal import graph for coupling triage.

Triage tool for the Balanced Coupling assessment (Vlad Khononov's
model — see ``docs/explanation/code/balanced-coupling.md``). The scanner
parses every source file via its language engine, resolves each
``ImportInfo`` to a file inside the scanned tree, and emits the
internal integration edges plus per-module fan-in/fan-out. Imports that
do not resolve to a scanned file (stdlib, third-party, vendor) are
counted as external — the scanner never invents boundaries.

Each edge carries a per-name ``usage`` hint — the deterministic signal
the judgment pass uses to classify integration strength:

- **Python** (stdlib ``ast``): ``call`` when the name is invoked;
  ``extends`` when it appears as a class base; ``type`` when it appears
  in an annotation; ``attribute`` for any other reference; otherwise
  ``import-only``.
- **PHP** (tree-sitter via ``PHPEngine.parse_raw``): ``new`` for
  ``object_creation_expression``; ``extends`` for ``base_clause`` /
  ``class_interface_clause``; ``type`` for ``named_type`` positions;
  otherwise ``import-only``.

Resolution is approximate by design: Python dotted modules map to
``pkg/mod.py`` or ``pkg/mod/__init__.py`` under a scan root (relative
imports walk up the importer's package directories), PHP ``use``
statements map to ``Ns/Sub/Cls.php`` (PSR-4 approximation). What cannot
be resolved degrades to the external count, never to a false edge.

This is a triage artifact, not a ``Finding`` producer — the judgment
pass classifies strength/distance/volatility and applies the balance
rule.

Which languages are scanned and where is driven entirely by
``.zolletta-metaskill/settings.json`` (created by the setup guard):
the top-level ``language`` field plus each populated ``<language>``
section map to extensions via the engine registry; scan roots come from
``python.paths.source`` / ``php.autoload.psr-4`` (``src`` when
unconfigured); git-ignored files are skipped.

Usage:
    python3 integration_graph_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 on success; 1 on errors such as no configured source
           directory existing on disk.

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import ImportInfo, ModuleInfo


class IntegrationGraphScanner:
    """Emit internal import edges and fan-in/fan-out for a project."""

    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH

    # Usage-hint precedence: the strongest observed use wins.
    _USAGE_PRIORITY = ("new", "call", "extends", "type", "attribute")

    # ------------------------------------------------------------------
    # Settings / enumeration
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_extensions(settings_path: Path) -> set[str]:
        """Return the file extensions to scan for the project.

        Languages come from settings.json — the top-level ``language``
        field plus each populated ``<language>`` section — mapped to
        extensions via the engine registry. Patterns scanners run
        unconditionally (no ``check_*`` toggle); when nothing usable is
        configured, falls back to every registered engine's extensions.
        """
        ProjectConfig.ensure_engines()
        settings = ProjectConfig.load_settings(settings_path)
        languages = ProjectConfig.configured_languages(settings)
        extensions = ProjectConfig.extensions_for(languages)
        if not extensions:
            extensions = ProjectConfig.extensions_for(
                set(EngineRegistry.available_languages())
            )
        return extensions

    @staticmethod
    def _iter_project_files(
        roots: list[Path], extensions: set[str]
    ) -> list[Path]:
        """Return all matching files under *roots* (git-ignore aware)."""
        files: list[Path] = []
        for root in roots:
            files.extend(ProjectConfig.iter_files(root, extensions))
        return files

    # ------------------------------------------------------------------
    # Import → internal file resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _python_candidates(base: Path, dotted: str) -> list[Path]:
        """Return candidate files for a dotted module path under *base*."""
        parts = [p for p in dotted.split(".") if p]
        if not parts:
            return []
        stem = base.joinpath(*parts)
        return [
            stem.with_suffix(".py"),
            stem / "__init__.py",
        ]

    @staticmethod
    def _resolve_python(
        imp: ImportInfo, importer: Path, roots: list[Path]
    ) -> dict[Path, list[str]]:
        """Resolve a Python import to internal files.

        Returns a mapping ``{target_file: [names]}`` — one entry when the
        module itself resolves, several when ``from pkg import a, b``
        names resolve to different submodule files. Empty when nothing
        resolves (external/stdlib import).
        """
        if imp.is_relative:
            # ``node.level`` is not captured by the engine — try the
            # importer's package first, then each ancestor directory up
            # to (and including) the scan roots.
            search_dirs = [
                d
                for d in importer.parents
                if any(d == r or r in d.parents for r in roots)
            ]
        else:
            search_dirs = list(roots)
        for base in search_dirs:
            module_hits: dict[Path, list[str]] = defaultdict(list)
            candidates = IntegrationGraphScanner._python_candidates(
                base, imp.module
            )
            if not imp.module:
                candidates.append(base / "__init__.py")
            for candidate in candidates:
                if candidate.is_file():
                    for name in imp.names or [imp.module]:
                        module_hits[candidate].append(name)
            for name in imp.names:
                dotted = f"{imp.module}.{name}" if imp.module else name
                for candidate in IntegrationGraphScanner._python_candidates(
                    base, dotted
                ):
                    if candidate.is_file():
                        # The name is a submodule — attribute it to the
                        # submodule edge, not the package edge.
                        module_hits[candidate] = [
                            n for n in module_hits.get(candidate, []) if n != name
                        ]
                        module_hits[candidate].append(name)
            if module_hits:
                return dict(module_hits)
        return {}

    @staticmethod
    def _resolve_php(imp: ImportInfo, roots: list[Path]) -> dict[Path, list[str]]:
        r"""Resolve a PHP ``use`` clause to an internal file (PSR-4 approx).

        ``Ns\\Sub\\Cls`` maps to ``Ns/Sub/Cls.php`` under a scan root.
        Grouped ``use Ns\\{A, B}`` arrives as separate ImportInfos from
        the engine. Empty mapping when nothing resolves.
        """
        rel = Path(*imp.module.split("\\")).with_suffix(".php")
        symbol = imp.names[0] if imp.names else imp.module.split("\\")[-1]
        for root in roots:
            candidate = root / rel
            if candidate.is_file():
                return {candidate: [symbol]}
        return {}

    # ------------------------------------------------------------------
    # Usage-hint detection
    # ------------------------------------------------------------------

    @staticmethod
    def _annotation_names(node: ast.AST | None, out: set[str]) -> None:
        """Collect every identifier inside an annotation subtree."""
        if node is None:
            return
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                out.add(child.id)
            elif isinstance(child, ast.Attribute):
                out.add(child.attr)
                out.add(IntegrationGraphScanner._dotted(child))

    @staticmethod
    def _dotted(node: ast.AST) -> str:
        """Return the dotted text of a Name/Attribute chain (``a.b.c``)."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    @staticmethod
    def _python_usages(path: Path) -> dict[str, set[str]]:
        """Return ``{usage_kind: {name, ...}}`` observed in a ``.py`` file."""
        kinds: dict[str, set[str]] = {
            "call": set(),
            "extends": set(),
            "type": set(),
            "attribute": set(),
        }
        try:
            tree = ast.parse(path.read_bytes())
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            return kinds
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    kinds["call"].add(func.id)
                elif isinstance(func, ast.Attribute):
                    kinds["call"].add(func.attr)
                    kinds["call"].add(IntegrationGraphScanner._dotted(func))
                    root: ast.expr = func
                    while isinstance(root, ast.Attribute):
                        root = root.value
                    if isinstance(root, ast.Name):
                        kinds["attribute"].add(root.id)
            elif isinstance(node, ast.ClassDef):
                for base in list(node.bases) + [
                    kw.value for kw in node.keywords
                ]:
                    for sub in ast.walk(base):
                        if isinstance(sub, ast.Name):
                            kinds["extends"].add(sub.id)
                        elif isinstance(sub, ast.Attribute):
                            kinds["extends"].add(
                                IntegrationGraphScanner._dotted(sub)
                            )
                            kinds["extends"].add(sub.attr)
            elif isinstance(node, ast.Attribute):
                kinds["attribute"].add(node.attr)
                kinds["attribute"].add(IntegrationGraphScanner._dotted(node))
            elif isinstance(node, ast.Name):
                kinds["attribute"].add(node.id)
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                IntegrationGraphScanner._annotation_names(
                    node.annotation, kinds["type"]
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                IntegrationGraphScanner._annotation_names(
                    node.returns, kinds["type"]
                )
                for arg in (
                    node.args.posonlyargs
                    + node.args.args
                    + node.args.kwonlyargs
                ):
                    IntegrationGraphScanner._annotation_names(
                        arg.annotation, kinds["type"]
                    )
        return kinds

    @staticmethod
    def _php_usages(path: Path) -> dict[str, set[str]]:
        """Return ``{usage_kind: {name, ...}}`` observed in a ``.php`` file."""
        kinds: dict[str, set[str]] = {
            "new": set(),
            "extends": set(),
            "type": set(),
        }
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(path)
        if not isinstance(engine, PHPEngine):
            return kinds
        try:
            tree, source = engine.parse_raw(path)
        except (OSError, ImportError):
            return kinds

        def _text(node: Any) -> str:
            return source[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )

        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type == "object_creation_expression":
                for child in node.children:
                    if child.type in ("qualified_name", "name"):
                        kinds["new"].add(_text(child).split("\\")[-1])
            elif node.type == "named_type":
                kinds["type"].add(_text(node).split("\\")[-1])
            elif node.type in ("base_clause", "class_interface_clause"):
                for child in node.children:
                    if child.type in ("qualified_name", "name"):
                        kinds["extends"].add(_text(child).split("\\")[-1])
            stack.extend(node.children)
        return kinds

    @staticmethod
    def _usage_for(name: str, kinds: dict[str, set[str]]) -> str:
        """Return the strongest usage hint for *name*.

        A name matches a collected string when it is the whole string or
        a dotted segment boundary (``pkg.mod`` matches ``pkg.mod.Cls``).
        """
        def _matches(collected: set[str]) -> bool:
            return any(
                item == name
                or item.startswith(name + ".")
                or item.endswith("." + name)
                for item in collected
            )

        for kind in IntegrationGraphScanner._USAGE_PRIORITY:
            if _matches(kinds.get(kind, set())):
                return kind
        return "import-only"

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    @staticmethod
    def _edges_for_file(
        module: ModuleInfo, path: Path, roots: list[Path]
    ) -> tuple[list[dict[str, Any]], int]:
        """Return ``(edges, external_count)`` for one parsed module."""
        if module.has_syntax_error:
            return [], 0
        kinds = (
            IntegrationGraphScanner._php_usages(path)
            if path.suffix == ".php"
            else IntegrationGraphScanner._python_usages(path)
        )
        edges: list[dict[str, Any]] = []
        external = 0
        for imp in module.imports:
            if path.suffix == ".php":
                resolved = IntegrationGraphScanner._resolve_php(imp, roots)
            else:
                resolved = IntegrationGraphScanner._resolve_python(
                    imp, path, roots
                )
            if not resolved:
                external += 1
                continue
            for target, names in resolved.items():
                edges.append(
                    {
                        "from": str(path),
                        "to": str(target),
                        "line": imp.lineno,
                        "names": [
                            {
                                "name": name,
                                "usage": IntegrationGraphScanner._usage_for(
                                    name, kinds
                                ),
                            }
                            for name in names
                        ],
                    }
                )
        return edges, external

    @staticmethod
    def scan_directory(
        roots: list[Path],
        extensions: set[str] | None = None,
        settings_path: Path | None = None,
    ) -> dict[str, Any]:
        """Scan matching files under *roots* and build the import graph.

        When *extensions* is omitted it is resolved from *settings_path*
        (default ``.zolletta-metaskill/settings.json``). Returns a dict
        with ``edges``, ``external_imports``, and per-module
        ``fan_in``/``fan_out``.
        """
        path = settings_path or IntegrationGraphScanner.DEFAULT_SETTINGS_PATH
        if extensions is None:
            extensions = IntegrationGraphScanner.resolve_extensions(path)
        ProjectConfig.ensure_engines()
        edges: list[dict[str, Any]] = []
        external = 0
        scanned = 0
        for file_path in IntegrationGraphScanner._iter_project_files(
            roots, extensions
        ):
            engine = EngineRegistry.get_for_file(file_path)
            if engine is None:
                continue
            try:
                module = engine.parse_module(file_path)
            except (OSError, ImportError):
                print(
                    f"Warning: could not parse '{file_path}'", file=sys.stderr
                )
                continue
            scanned += 1
            file_edges, file_external = (
                IntegrationGraphScanner._edges_for_file(
                    module, file_path, roots
                )
            )
            edges.extend(file_edges)
            external += file_external
        return {
            "scanned": scanned,
            "edge_count": len(edges),
            "external_imports": external,
            "edges": edges,
            "modules": IntegrationGraphScanner._fan(edges),
        }

    @staticmethod
    def _fan(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return per-module ``fan_in``/``fan_out`` from the edge list."""
        fan_in: dict[str, set[str]] = defaultdict(set)
        fan_out: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            fan_out[edge["from"]].add(edge["to"])
            fan_in[edge["to"]].add(edge["from"])
        modules = sorted(set(fan_in) | set(fan_out))
        return [
            {
                "module": m,
                "fan_in": len(fan_in[m]),
                "fan_out": len(fan_out[m]),
            }
            for m in modules
        ]

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_json(result: dict[str, Any], roots: list[Path]) -> None:
        """Print the JSON report."""
        print(
            json.dumps(
                {
                    "directories": [str(root) for root in roots],
                    "scanned": result["scanned"],
                    "edge_count": len(result["edges"]),
                    "external_imports": result["external_imports"],
                    "edges": result["edges"],
                    "modules": result["modules"],
                },
                indent=2,
            )
        )

    @staticmethod
    def _emit_text(result: dict[str, Any], roots: list[Path]) -> None:
        """Print the text report."""
        edges = result["edges"]
        modules = sorted(
            result["modules"], key=lambda m: m["fan_out"], reverse=True
        )
        print("=" * 70)
        print("INTEGRATION GRAPH — INTERNAL DEPENDENCY EDGES")
        print("=" * 70)
        roots_str = ", ".join(str(root) for root in roots)
        print(
            f"\nScanned {result['scanned']} files under {roots_str}; "
            f"{len(edges)} internal edges, "
            f"{result['external_imports']} external imports."
        )

        print("\n## Modules by fan-out\n")
        print(f"  {'OUT':>4} {'IN':>4}  MODULE")
        for m in modules:
            print(f"  {m['fan_out']:>4} {m['fan_in']:>4}  {m['module']}")

        if edges:
            print("\n## Edges\n")
            for e in edges:
                names = ", ".join(
                    f"{n['name']}({n['usage']})" for n in e["names"]
                )
                print(f"  {e['from']}:{e['line']} -> {e['to']}  [{names}]")
        else:
            print("\n## Edges: none")
        print("\nResult: report generated (triage artifact)")

    @staticmethod
    def main() -> int:
        """Entry point for the integration graph scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Emit the internal import graph for coupling "
            "triage (Balanced Coupling model). Scan roots and languages "
            "come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON instead of text",
        )
        args = parser.parse_args()

        settings = ProjectConfig.load_settings(
            IntegrationGraphScanner.DEFAULT_SETTINGS_PATH
        )
        languages = ProjectConfig.configured_languages(settings)
        if not languages:
            languages = set(EngineRegistry.available_languages())

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
        result = IntegrationGraphScanner.scan_directory(
            roots, extensions=extensions
        )
        if args.json:
            IntegrationGraphScanner._emit_json(result, roots)
        else:
            IntegrationGraphScanner._emit_text(result, roots)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(IntegrationGraphScanner.main())
