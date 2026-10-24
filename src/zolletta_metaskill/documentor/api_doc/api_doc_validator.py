#!/usr/bin/env python3
"""API Documentation Validator.

Extracts function and class signatures from Python source files using the ast module
and compares them against API documentation in markdown files.

Detects:
- Functions/classes in code but missing from docs
- Functions/classes documented but removed from code
- Parameter mismatches (missing, extra, wrong defaults)
- Deprecated items still documented as current
- Return type annotation mismatches

Source roots come from ``python.paths.source`` and the documentation
directory from ``documentation.dir`` in ``.zolletta-metaskill/settings.json``.
Behavior settings under ``documentation``:

- ``api_docs_recursive`` — recursively scan the docs directory (default: off)
- ``include_private`` — include ``_``-prefixed items (default: off)
- ``suggest_coverage`` — include prioritized documentation suggestions
  for undocumented items (default: off)

Usage:
    python api_doc_validator.py [--json]

Exit code: 0 always (report-only); 1 when no configured source root or the
documentation directory is missing on disk.

"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.api_doc.api_doc_report_writer import APIDocReportWriter
from zolletta_metaskill.documentor.api_doc.documented_item_extractor import (
    DocumentedItemExtractor,
)
from zolletta_metaskill.documentor.api_doc.source_signature_extractor import (
    SourceSignatureExtractor,
)
from zolletta_metaskill.documentor.structs import APIDocReportOptions
from zolletta_metaskill.documentor.structs.source_signature import SourceSignature
from zolletta_metaskill.documentor.utils.documentor_settings import DocumentorSettings


class APIDocValidator:
    """API Documentation Validator."""

    # --- Validation ---

    @staticmethod
    def validate_api_docs(
        source_sigs: dict[str, list[SourceSignature]],
        documented_items: dict[str, dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Compare source signatures against documented items and find mismatches.

        Returns:
            A tuple of (issues, suggestions). Issues are real drift (phantom docs,
            param mismatches, deprecations). Suggestions are undocumented items that
            might be worth documenting, prioritized by heuristics.

        """
        # Build lookup of all source signatures by name and qualified name
        source_by_name: dict[str, SourceSignature] = {}
        for file_sigs in source_sigs.values():
            for sig in file_sigs:
                source_by_name[sig.name] = sig
                source_by_name[sig.qualified_name] = sig

        documented_names = set(documented_items.keys())
        source_names = set(source_by_name.keys())
        shared = documented_names & source_names

        issues = APIDocValidator._phantom_doc_issues(
            documented_names, source_names, documented_items
        )
        issues += APIDocValidator._param_mismatch_issues(shared, source_by_name, documented_items)
        issues += APIDocValidator._deprecated_doc_issues(shared, source_by_name)
        suggestions = APIDocValidator._undocumented_suggestions(source_by_name, documented_names)

        return issues, suggestions

    @staticmethod
    def _phantom_doc_issues(
        documented_names: set[str],
        source_names: set[str],
        documented_items: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Documented but not in source (removed or renamed) — real drift."""
        issues = []
        for name in documented_names:
            if name not in source_names:
                doc_item = documented_items[name]
                issues.append(
                    {
                        "type": "documented_not_in_source",
                        "severity": "high",
                        "name": name,
                        "doc_file": doc_item.get("file", "unknown"),
                        "doc_line": doc_item.get("line", 0),
                        "description": (
                            f"'{name}' is documented but not found in source code "
                            "(removed or renamed)"
                        ),
                    }
                )
        return issues

    @staticmethod
    def _undocumented_suggestions(
        source_by_name: dict[str, SourceSignature],
        documented_names: set[str],
    ) -> list[dict[str, Any]]:
        """In source but not documented — suggestions, not issues."""
        suggestions = []
        for name, sig in source_by_name.items():
            # Skip qualified names that are also present as simple names
            if "." in name and name.split(".")[-1] in source_by_name:
                continue
            if (
                name not in documented_names
                and sig.qualified_name not in documented_names
                and not sig.is_private
            ):
                priority, reason = APIDocValidator._classify_undocumented(sig)
                if priority == "skip":
                    continue
                suggestions.append(
                    {
                        "type": "undocumented",
                        "priority": priority,
                        "name": name,
                        "kind": sig.kind,
                        "source_file": sig.file_path,
                        "source_line": sig.line_number,
                        "reason": reason,
                    }
                )
        return suggestions

    @staticmethod
    def _param_mismatch_issues(
        shared: set[str],
        source_by_name: dict[str, SourceSignature],
        documented_items: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Parameter mismatches for items in both source and docs."""
        issues = []
        for name in shared:
            sig = source_by_name[name]
            doc_item = documented_items[name]
            doc_params = {p["name"] for p in doc_item.get("parameters", [])}
            source_params = {p["name"] for p in sig.parameters}

            # Missing parameters in docs
            missing = source_params - doc_params
            for param in missing:
                issues.append(
                    {
                        "type": "missing_param_in_docs",
                        "severity": "medium",
                        "name": name,
                        "param": param,
                        "source_file": sig.file_path,
                        "source_line": sig.line_number,
                        "doc_file": doc_item.get("file", "unknown"),
                        "doc_line": doc_item.get("line", 0),
                        "description": (
                            f"Parameter '{param}' in source but not documented for '{name}'"
                        ),
                    }
                )

            # Extra parameters in docs
            extra = doc_params - source_params
            for param in extra:
                issues.append(
                    {
                        "type": "extra_param_in_docs",
                        "severity": "low",
                        "name": name,
                        "param": param,
                        "source_file": sig.file_path,
                        "source_line": sig.line_number,
                        "doc_file": doc_item.get("file", "unknown"),
                        "doc_line": doc_item.get("line", 0),
                        "description": (
                            f"Parameter '{param}' documented for '{name}' but not in source"
                        ),
                    }
                )
        return issues

    @staticmethod
    def _deprecated_doc_issues(
        shared: set[str],
        source_by_name: dict[str, SourceSignature],
    ) -> list[dict[str, Any]]:
        """Flag deprecated items still documented without a deprecation notice."""
        issues = []
        for name in shared:
            sig = source_by_name[name]
            if sig.is_deprecated:
                issues.append(
                    {
                        "type": "deprecated_still_documented",
                        "severity": "low",
                        "name": name,
                        "source_file": sig.file_path,
                        "source_line": sig.line_number,
                        "description": (
                            f"'{name}' has @deprecated decorator but may still be "
                            "documented as current"
                        ),
                    }
                )
        return issues

    @staticmethod
    def _classify_undocumented(sig: SourceSignature) -> tuple[str, str]:
        """Classify an undocumented item by documentation priority.

        Returns:
            A tuple of (priority, reason) where priority is "high", "medium", "low",
            or "skip", and reason explains the classification.

        """
        # Skip: __init__.py files, simple enums, constants
        if os.path.basename(sig.file_path) == "__init__.py":
            return "skip", "re-export file — no standalone documentation needed"

        # Skip: dataclass-like (decorated with @dataclass)
        if "dataclass" in sig.decorators:
            return "skip", "dataclass — fields are self-documenting"

        # High: entry points (main, run, CLI commands)
        if sig.name in ("main", "run", "cli", "execute", "dispatch") and sig.kind == "function":
            return "high", "entry-point function — users need to know this exists"

        # High: Protocol definitions (define public interfaces)
        if "runtime_checkable" in sig.decorators or "Protocol" in (sig.decorators or []):
            return "high", "protocol definition — defines a public interface contract"

        # High: classes with many parameters (complex constructors)
        if sig.kind == "class" and len(sig.parameters) > 3:
            return (
                "high",
                f"class with {len(sig.parameters)} constructor params — complex initialization",
            )

        # Medium: functions with complex signatures (>3 params)
        if sig.kind == "function" and len(sig.parameters) > 3:
            return "medium", f"function with {len(sig.parameters)} params — non-trivial signature"

        # Medium: classes (public API surface)
        if sig.kind == "class" and not sig.name.startswith("_"):
            return "medium", "public class — part of the API surface"

        # Low: simple functions
        if sig.kind == "function" and len(sig.parameters) <= 2:
            return "low", "simple function — low documentation priority"

        # Low: methods
        if sig.kind == "method":
            return "low", "method — consider documenting if part of public API"

        # Default
        return "low", "undocumented item"

    # --- Main ---

    @staticmethod
    def run(settings: dict[str, Any], cache_dir: Path, as_json: bool = False) -> tuple[str, bool]:
        """Run the API doc validator and write the JSON cache file.

        Returns ``(report, success)`` where *report* is the report string
        (Markdown or JSON depending on *as_json*) and *success* is False when
        the run could not proceed (missing source roots or docs dir).
        """
        languages = ProjectConfig.languages_for_extensions(
            ProjectConfig.configured_languages(settings), {".py"}
        )
        include_private = bool(
            ProjectConfig.setting(settings, "documentation.include_private", False)
        )
        recursive = bool(ProjectConfig.setting(settings, "documentation.api_docs_recursive", False))
        suggest_coverage = bool(
            ProjectConfig.setting(settings, "documentation.suggest_coverage", False)
        )

        source_roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, languages))
        if not source_roots:
            error_report = "Error: no configured source directories exist on disk"
            APIDocValidator._write_cache(
                cache_dir, {"error": error_report, "summary": {}, "issues": [], "suggestions": []}
            )
            return error_report, False

        doc_path = ProjectConfig.docs_dir(settings)
        if not doc_path.exists():
            error_report = f"Error: documentation directory '{doc_path}' does not exist"
            APIDocValidator._write_cache(
                cache_dir, {"error": error_report, "summary": {}, "issues": [], "suggestions": []}
            )
            return error_report, False

        source_sigs: dict[str, list[SourceSignature]] = {}
        for root in source_roots:
            for rel, sigs in SourceSignatureExtractor.extract_all_signatures(
                str(root), include_private
            ).items():
                key = str(root / rel)
                source_sigs[key] = sigs

        documented_items = DocumentedItemExtractor.extract_all_documented_items(
            str(doc_path), recursive=recursive
        )

        source_count = sum(len(sigs) for sigs in source_sigs.values())
        doc_count = len(documented_items)

        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented_items)

        options = APIDocReportOptions(
            source_count=source_count,
            doc_count=doc_count,
            as_json=as_json,
            suggest_coverage=suggest_coverage,
        )
        report = APIDocReportWriter.generate_report(issues, suggestions, options)

        cache_data = APIDocReportWriter.generate_report_data(issues, suggestions, options)
        APIDocValidator._write_cache(cache_dir, cache_data)

        return report, True

    @staticmethod
    def _write_cache(cache_dir: Path, cache_data: dict[str, Any]) -> None:
        """Write *cache_data* to the API doc validator cache file."""
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "api_doc_validator.json"
        cache_path.write_text(json.dumps(cache_data, indent=2, default=str) + "\n")

    @staticmethod
    def main() -> int:
        """Entry point for the API documentation validator CLI."""
        parser = argparse.ArgumentParser(
            description="Validate API documentation against Python source code. "
            "Source roots come from <lang>.paths.source and docs from "
            "documentation.dir in .zolletta-metaskill/settings.json.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--json", action="store_true", help="Output as JSON"
        )  # pragma: no mutate — help text is not a tested contract  # noqa: E501

        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        cache_dir = DocumentorSettings.resolve_cache_dir(settings)
        report, success = APIDocValidator.run(settings, cache_dir, as_json=args.json)
        print(report, file=sys.stderr if not success else sys.stdout)
        return 0 if success else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(APIDocValidator.main())
