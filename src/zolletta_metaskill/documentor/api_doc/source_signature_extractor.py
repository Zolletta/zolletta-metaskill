"""Source signature extractor.

Extracts function, method and class signatures from Python source files
using the ``ast`` module, for comparison against API documentation.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.structs.source_signature import SourceSignature


class SourceSignatureExtractor:
    """Extracts signatures from Python source via the AST."""

    @staticmethod
    def _annotation_to_str(node: ast.expr | None) -> str | None:
        """Convert an AST annotation node to a string representation."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except AttributeError:  # pragma: no cover — Python < 3.9 fallback
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Constant):
                return repr(node.value)
            elif isinstance(node, ast.Attribute):
                return f"{SourceSignatureExtractor._annotation_to_str(node.value)}.{node.attr}"
            elif isinstance(node, ast.Subscript):
                value = SourceSignatureExtractor._annotation_to_str(node.value)
                slice_ = SourceSignatureExtractor._annotation_to_str(node.slice)
                return f"{value}[{slice_}]"
            return str(type(node).__name__)

    @staticmethod
    def _extract_decorator_names(decorator_list: list[ast.expr]) -> list[str]:
        """Extract decorator names from AST decorator list."""
        names = []
        for dec in decorator_list:
            if isinstance(dec, ast.Name):
                names.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                names.append(f"{SourceSignatureExtractor._annotation_to_str(dec.value)}.{dec.attr}")
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    names.append(dec.func.id)
                elif isinstance(dec.func, ast.Attribute):
                    names.append(
                        f"{SourceSignatureExtractor._annotation_to_str(dec.func.value)}.{dec.func.attr}"
                    )
        return names

    @staticmethod
    def _extract_parameters(
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[dict[str, Any]]:
        """Extract parameter information from a function definition."""
        params: list[dict[str, Any]] = []
        args = func_node.args

        # Calculate defaults offset
        num_args = len(args.args)
        num_defaults = len(args.defaults)
        default_offset = num_args - num_defaults

        for i, arg in enumerate(args.args):
            if arg.arg == "self" or arg.arg == "cls":
                continue
            param: dict[str, Any] = {
                "name": arg.arg,
                "annotation": SourceSignatureExtractor._annotation_to_str(arg.annotation),
                "has_default": False,
                "default": None,
            }
            # Check if this arg has a default
            default_idx = i - default_offset
            if default_idx >= 0 and default_idx < len(args.defaults):
                param["has_default"] = True
                try:
                    param["default"] = ast.unparse(args.defaults[default_idx])
                except AttributeError:  # pragma: no cover
                    param["default"] = "..."
            params.append(param)

        # *args
        if args.vararg:
            params.append(
                {
                    "name": f"*{args.vararg.arg}",
                    "annotation": SourceSignatureExtractor._annotation_to_str(
                        args.vararg.annotation
                    ),
                    "has_default": False,
                    "default": None,
                }
            )

        # keyword-only args
        for i, arg in enumerate(args.kwonlyargs):
            param = {
                "name": arg.arg,
                "annotation": SourceSignatureExtractor._annotation_to_str(arg.annotation),
                "has_default": False,
                "default": None,
            }
            kw_default = args.kw_defaults[i] if i < len(args.kw_defaults) else None
            if kw_default is not None:
                param["has_default"] = True
                try:
                    param["default"] = ast.unparse(kw_default)
                except AttributeError:  # pragma: no cover
                    param["default"] = "..."
            params.append(param)

        # **kwargs
        if args.kwarg:
            params.append(
                {
                    "name": f"**{args.kwarg.arg}",
                    "annotation": SourceSignatureExtractor._annotation_to_str(
                        args.kwarg.annotation
                    ),
                    "has_default": False,
                    "default": None,
                }
            )

        return params

    @staticmethod
    def _extract_function_signature(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        tree: ast.AST,
        rel_path: str,
        include_private: bool,
    ) -> SourceSignature | None:
        """Extract a single function or method signature."""
        is_private = node.name.startswith("_")
        if is_private and not include_private:
            return None

        parent_class = None
        kind = "function"
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for item in parent.body:  # pragma: no branch — walk hits every class
                    if item is node:
                        parent_class = parent.name
                        kind = "method"
                        break

        return SourceSignature(
            name=node.name,
            kind=kind,
            file_path=rel_path,
            line_number=node.lineno,
            parameters=SourceSignatureExtractor._extract_parameters(node),
            return_annotation=SourceSignatureExtractor._annotation_to_str(node.returns),
            decorators=SourceSignatureExtractor._extract_decorator_names(node.decorator_list),
            docstring=ast.get_docstring(node),
            is_private=is_private,
            parent_class=parent_class,
        )

    @staticmethod
    def _extract_class_signature(
        node: ast.ClassDef, rel_path: str, include_private: bool
    ) -> SourceSignature | None:
        """Extract a single class signature."""
        is_private = node.name.startswith("_")
        if is_private and not include_private:
            return None

        init_params: list[dict[str, Any]] = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_params = SourceSignatureExtractor._extract_parameters(item)
                break

        return SourceSignature(
            name=node.name,
            kind="class",
            file_path=rel_path,
            line_number=node.lineno,
            parameters=init_params,
            decorators=SourceSignatureExtractor._extract_decorator_names(node.decorator_list),
            docstring=ast.get_docstring(node),
            is_private=is_private,
        )

    @staticmethod
    def extract_signatures(
        source_path: str, include_private: bool = False
    ) -> list[SourceSignature]:
        """Extract all function and class signatures from a Python file."""
        signatures: list[SourceSignature] = []
        try:
            with open(source_path, encoding="utf-8", errors="ignore") as f:
                source = f.read()
            tree = ast.parse(source, filename=source_path)
        except (SyntaxError, OSError):
            return signatures

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = SourceSignatureExtractor._extract_function_signature(
                    node, tree, source_path, include_private
                )
                if sig:
                    signatures.append(sig)
            elif isinstance(node, ast.ClassDef):
                cls_sig = SourceSignatureExtractor._extract_class_signature(
                    node, source_path, include_private
                )
                if cls_sig:
                    signatures.append(cls_sig)

        return signatures

    @staticmethod
    def extract_all_signatures(
        source_dir: str, include_private: bool = False
    ) -> dict[str, list[SourceSignature]]:
        """Extract signatures from all Python files in a directory."""
        all_sigs: dict[str, list[SourceSignature]] = {}

        for path in ProjectConfig.iter_files(Path(source_dir), {".py"}):
            rel_path = os.path.relpath(path, source_dir)
            sigs = SourceSignatureExtractor.extract_signatures(str(path), include_private)
            # Update file paths to be relative
            for s in sigs:
                s.file_path = rel_path
            if sigs:
                all_sigs[rel_path] = sigs

        return all_sigs
