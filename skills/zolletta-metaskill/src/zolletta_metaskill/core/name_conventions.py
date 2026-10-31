"""Shared naming-convention helpers: case conversion and test-file prefixes.

The file↔class and test-file naming rules are a single domain convention —
the scanners that enforce it (naming conventions, test structure, test
splitter, one class per file) consume this module rather than each carrying
a private copy that can silently diverge.
"""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig


class NameConventions:
    """Case conversion, class extraction, and test-prefix rules for scanners."""

    @staticmethod
    def snake_to_pascal(name: str) -> str:
        """Convert snake_case to PascalCase (e.g. my_class -> MyClass)."""
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def pascal_to_snake(name: str) -> str:
        """Convert PascalCase to snake_case (e.g. MyClass -> my_class)."""
        # pragma: no mutate start — mutated strip-sets are equivalent on PascalCase input
        return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")
        # pragma: no mutate end

    @staticmethod
    def test_prefixes(stem: str, classes: list[str]) -> set[str]:
        """Return the valid test-file prefixes for one source file.

        ``test_<stem>`` from the filename plus ``test_<snake(cls)>`` for each
        class the file defines — the two prefix families the test-naming
        convention accepts.
        """
        prefixes = {f"test_{stem}"}
        for cls_name in classes:
            prefixes.add(f"test_{NameConventions.pascal_to_snake(cls_name)}")
        return prefixes

    @staticmethod
    def get_class_names(path: Path) -> list[str]:
        """Return top-level class names defined in a source file.

        Uses the registered language engine to parse the file, so no ``ast``
        import is needed here.
        """
        ProjectConfig.ensure_engines()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        if module.has_syntax_error:
            return []
        return [cls.name for cls in module.classes]

    @staticmethod
    def auto_detect_package(src_root: Path) -> str | None:
        """Auto-detect the package path under src/ (first child dir with __init__.py)."""
        for child in sorted(src_root.iterdir()):
            # pragma: no mutate start — case variants of __init__.py are not real files
            if child.is_dir() and (child / "__init__.py").exists():
                # pragma: no mutate end
                return child.name
        # Fallback: first child dir
        for child in sorted(src_root.iterdir()):
            if child.is_dir():
                return child.name
        return None
