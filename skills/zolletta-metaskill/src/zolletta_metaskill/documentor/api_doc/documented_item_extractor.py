"""Documented item extractor.

Extracts function and class references from markdown documentation —
headings and inline ``name(param, ...)`` mentions — for comparison
against source signatures.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class DocumentedItemExtractor:
    """Extracts documented items from markdown files."""

    @staticmethod
    def _parse_inline_param_list(param_str: str) -> list[dict[str, Any]]:
        """Parse parameter names from an inline function signature string."""
        params: list[dict[str, Any]] = []
        if not param_str:
            return params
        for p in param_str.split(","):
            p = p.strip()
            # pragma: no mutate start — a mutated "..." entry still fails isidentifier() below
            if p and p not in (
                "self",
                "cls",
                "...",
            ):
                # pragma: no mutate end
                parts = p.split(":")
                param_name = parts[0].strip().split("=")[0].strip()
                if param_name and param_name.replace("*", "").isidentifier():
                    params.append({"name": param_name})
        return params

    @staticmethod
    def _collect_inline_funcs(
        line: str, line_no: int, doc_path: str, items: dict[str, dict[str, Any]]
    ) -> None:
        """Find inline function references like `func(param1, param2)` in line."""
        inline_func = re.compile(r"`(\w+(?:\.\w+)*)\(([^)]*)\)`")
        for match in inline_func.finditer(line):
            func_name = match.group(1)
            if func_name not in items:
                params = DocumentedItemExtractor._parse_inline_param_list(match.group(2))
                items[func_name] = {
                    "name": func_name,
                    "line": line_no,
                    "kind": "function",
                    "file": doc_path,
                    "parameters": params,
                }

    @staticmethod
    def extract_documented_items(doc_path: str) -> dict[str, dict[str, Any]]:
        """Extract function/class references from markdown documentation."""
        items: dict[str, dict[str, Any]] = {}

        try:
            with open(doc_path, encoding="utf-8", errors="ignore") as f:  # pragma: no mutate
                content = f.read()
        except OSError:
            return items

        lines = content.splitlines()

        heading_func = re.compile(r"^#{1,6}\s+`?(\w+(?:\.\w+)*)\(`?.*\)?`?\s*$")
        param_pattern = re.compile(r"^\s*[-*]\s+`(\w+)`\s*(?:\(([^)]+)\))?\s*(?::|--)?\s*(.*)")

        current_item = None  # pragma: no mutate — falsy sentinel unobservable here
        # pragma: no mutate start — reassigned to [] as soon as a heading makes it reachable
        current_params: list[dict[str, Any]] = []
        # pragma: no mutate end

        for i, line in enumerate(lines):
            match = heading_func.match(line)
            if match:
                # pragma: no mutate start — current_item is always in items when set
                if current_item and current_item in items:
                    items[current_item]["parameters"] = current_params
                # pragma: no mutate end

                func_name = match.group(1)
                items[func_name] = {
                    "name": func_name,
                    "line": i + 1,
                    "kind": "function",
                    "file": doc_path,
                    "parameters": [],
                }
                current_item = func_name
                current_params = []
                continue

            DocumentedItemExtractor._collect_inline_funcs(line, i + 1, doc_path, items)

            param_match = param_pattern.match(line)
            if param_match and current_item:
                param_name = param_match.group(1)
                param_type = param_match.group(2)
                current_params.append(
                    {
                        "name": param_name,
                        "annotation": param_type,
                    }
                )

        # pragma: no mutate start — same invariant as the flush above
        if current_item and current_item in items:
            items[current_item]["parameters"] = current_params
        # pragma: no mutate end

        return items

    @staticmethod
    def extract_all_documented_items(
        doc_path: str, recursive: bool = False
    ) -> dict[str, dict[str, Any]]:
        """Extract documented items from one or more markdown files."""
        all_items: dict[str, dict[str, Any]] = {}

        if os.path.isfile(doc_path):
            return DocumentedItemExtractor.extract_documented_items(doc_path)

        if os.path.isdir(doc_path) and recursive:
            for path in ProjectConfig.iter_files(Path(doc_path), {".md", ".rst"}):
                items = DocumentedItemExtractor.extract_documented_items(str(path))
                all_items.update(items)
        elif os.path.isdir(doc_path):
            # Non-recursive: just top-level files
            for entry in Path(doc_path).iterdir():
                if entry.name.endswith((".md", ".rst")):
                    items = DocumentedItemExtractor.extract_documented_items(str(entry))
                    all_items.update(items)

        return all_items
