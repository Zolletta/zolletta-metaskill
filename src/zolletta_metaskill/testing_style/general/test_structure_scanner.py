#!/usr/bin/env python3
"""Check that the test directory structure mirrors the source directory structure.

Outputs a markdown report with five tables:

1. **Misnamed tests** — test files whose name doesn't match the source stem
   or class name of the source they test. These should be renamed.
2. **Misplaced tests** — test files with a name matching a source file but
   located in the wrong directory. These should be moved.
3. **Orphaned tests** — test files (or directories) that don't match any
   source file or directory. These may test deleted code.
4. **Missing tests** — source files with classes that have no direct test
   file and no indirect class reference in any test file. These are real gaps.
5. **Indirect references** — test files that reference classes from source
   files without a direct test. Informative only: shows which test files
   provide indirect coverage for otherwise untested source files.

The script checks directory-level mirroring and file-level coverage using
prefix matching. One source class can have many test files, so the convention
is:

    src/.../my_module.py  ->  tests/.../test_my_module*.py

This matches both single-file tests (test_my_module.py) and split tests
(test_my_module_operations.py, test_my_module_init.py, etc.).
It also checks class-name-based prefixes (snake_case):
    src/.../my_module.py (class MyClass)  ->  tests/.../test_my_class*.py

Source files with no mirrored test file are always checked for indirect
references: the script reads all test files once and checks if any class name
from the source file appears in the test code. Files with indirect references
are excluded from the "missing" table.

Source and test roots come from ``python.paths`` in ``settings.json``;
the mirror-base package comes from ``python.paths.package`` (auto-detected
when unset). The check runs when ``python.patterns.check_test_structure``
is not ``false``. File enumeration is git-ignore aware.

Usage:
    python3 test_structure_scanner.py [--json]

Options:
    --json           Output as JSON instead of markdown.

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


class TestStructureScanner:
    """Scan test directory structure for mirroring issues against source."""

    @staticmethod
    def _ensure_python_engine() -> None:
        """Ensure the PythonEngine is registered."""
        EngineRegistry.ensure(PythonEngine())

    @staticmethod
    def _pascal_to_snake(name: str) -> str:
        """Convert PascalCase to snake_case."""
        return "".join("_" + c.lower() if c.isupper() else c for c in name).lstrip("_")

    @staticmethod
    def _get_class_names(path: Path) -> list[str]:
        """Return top-level class names defined in a source file.

        Uses the registered language engine to parse the file, so no ``ast``
        import is needed here.
        """
        TestStructureScanner._ensure_python_engine()
        engine = EngineRegistry.get_for_file(path)
        if engine is None:  # pragma: no cover
            return []
        module = engine.parse_module(path)
        if module.has_syntax_error:
            return []
        return [cls.name for cls in module.classes]

    @staticmethod
    def _auto_detect_package(src_root: Path) -> str | None:
        """Auto-detect the package path under src/ (first child dir with __init__.py)."""
        for child in sorted(src_root.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child.name
        # Fallback: first child dir
        for child in sorted(src_root.iterdir()):
            if child.is_dir():
                return child.name
        return None

    @staticmethod
    def _collect_dirs(root: Path) -> set[Path]:
        """Return directory paths under *root*, relative to *root*.

        Includes ancestors of every non-ignored ``.py`` file plus truly
        empty directories (which carry no files for ``iter_files`` to find).
        Directories whose files are all git-ignored are excluded.
        """
        dirs: set[Path] = set()
        for f in ProjectConfig.iter_files(root, {".py"}):
            rel = f.relative_to(root).parent
            while str(rel) != ".":
                dirs.add(rel)
                rel = rel.parent
        for d in (p for p in root.rglob("*") if p.is_dir()):
            if not any(c.is_file() for c in d.rglob("*")):
                dirs.add(d.relative_to(root))
        return dirs

    @staticmethod
    def _build_source_index(src_pkg: Path) -> dict[str, dict[str, Any]]:
        """Index all source files with classes: rel_path -> {stem, classes, prefixes}."""
        index: dict[str, dict[str, Any]] = {}
        for py in ProjectConfig.iter_files(src_pkg, {".py"}):
            if py.name == "__init__.py":
                continue
            classes = TestStructureScanner._get_class_names(py)
            if not classes:
                continue
            rel = str(py.relative_to(src_pkg))
            stem = py.stem
            prefixes = {f"test_{stem}"}
            for cls_name in classes:
                prefixes.add(f"test_{TestStructureScanner._pascal_to_snake(cls_name)}")
            index[rel] = {
                "abs_path": py,
                "stem": stem,
                "classes": classes,
                "prefixes": prefixes,
                "dir": str(py.relative_to(src_pkg).parent),
            }
        return index

    @staticmethod
    def _match_test_to_source(
        test_name: str, src_index: dict[str, dict[str, Any]], test_dir: str = ""
    ) -> str | None:
        """Return the source rel_path whose prefix best matches this test file name.

        Uses longest-prefix matching to avoid false positives: test_scenario_writer.py
        matches scenario_writer.py (prefix test_scenario_writer) not scenario.py
        (prefix test_scenario), because the longer prefix is more specific.

        When two source files have equal-length prefixes (e.g. two cache.py files
        in different directories), prefers the one in the same directory as the test.
        """
        best_match: str | None = None
        best_prefix_len = 0
        best_same_dir = False
        for src_rel, info in src_index.items():
            for prefix in info["prefixes"]:
                if test_name == f"{prefix}.py" or test_name.startswith(f"{prefix}_"):
                    same_dir = info["dir"] == test_dir
                    # Prefer: longer prefix, then same directory
                    if len(prefix) > best_prefix_len or (
                        len(prefix) == best_prefix_len and same_dir and not best_same_dir
                    ):
                        best_prefix_len = len(prefix)
                        best_match = src_rel
                        best_same_dir = same_dir
        return best_match

    @staticmethod
    def main() -> int:
        """Entry point for the test structure mirror checker CLI."""
        parser = argparse.ArgumentParser(
            description="Check that test directory structure mirrors source structure. "
            "Roots and package come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        TestStructureScanner._ensure_python_engine()
        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.scan_languages(settings, "patterns.check_test_structure")
        py_langs = ProjectConfig.languages_for_extensions(languages, {".py"})
        if not py_langs:
            ProjectConfig.emit_skipped(args.json, "check_test_structure disabled in settings.json")
            return 0

        src_pkgs, test_pkgs = TestStructureScanner._resolve_packages(settings, py_langs)
        if src_pkgs is None or test_pkgs is None:
            return 1

        test_only_dirs, src_index, test_files = TestStructureScanner._collect_inputs(
            src_pkgs, test_pkgs
        )
        classified = TestStructureScanner._classify_test_files(test_files, src_index)
        indirect_refs, indirectly_covered = TestStructureScanner._find_indirect_refs(
            classified["test_refs"],
            classified["class_to_source"],
            classified["directly_covered"],
        )
        missing = TestStructureScanner._find_missing_tests(
            src_index, classified["directly_covered"], indirectly_covered
        )
        orphaned_dirs = [{"test_dir": str(d) + "/"} for d in test_only_dirs]

        if args.json:
            TestStructureScanner._emit_json(
                src_pkgs, test_pkgs, classified, orphaned_dirs, missing, indirect_refs
            )
            return 0
        TestStructureScanner._emit_text(
            src_pkgs, test_pkgs, classified, orphaned_dirs, missing, indirect_refs
        )
        return 0

    @staticmethod
    def _resolve_packages(
        settings: dict[str, Any], py_langs: set[str]
    ) -> tuple[list[Path] | None, list[Path] | None]:
        """Resolve the source/test package dirs, printing an error on failure."""
        src_roots = ProjectConfig.existing_roots(ProjectConfig.source_roots(settings, py_langs))
        test_roots = ProjectConfig.existing_roots(ProjectConfig.test_roots(settings, py_langs))
        if not src_roots:
            print(
                "Error: no configured source directories exist on disk",
                file=sys.stderr,
            )
            return None, None
        if not test_roots:
            print(
                "Error: no configured test directories exist on disk",
                file=sys.stderr,
            )
            return None, None

        pkg_name = ProjectConfig.package_name(
            settings, "python"
        ) or TestStructureScanner._auto_detect_package(src_roots[0])
        if not pkg_name:
            print("Error: could not auto-detect package under src/", file=sys.stderr)
            return None, None

        src_pkgs = [root / pkg_name for root in src_roots if (root / pkg_name).is_dir()]
        test_pkgs = [root / pkg_name for root in test_roots if (root / pkg_name).is_dir()]
        if not src_pkgs:
            print(
                f"Error: source package '{pkg_name}' does not exist under any "
                "configured source root",
                file=sys.stderr,
            )
            return None, None
        if not test_pkgs:
            print(
                f"Error: test package '{pkg_name}' does not exist under any configured test root",
                file=sys.stderr,
            )
            return None, None
        return src_pkgs, test_pkgs

    @staticmethod
    def _collect_inputs(
        src_pkgs: list[Path], test_pkgs: list[Path]
    ) -> tuple[list[Path], dict[str, dict[str, Any]], dict[str, tuple[Path, str]]]:
        """Collect test-only dirs, the source index, and test file contents."""
        src_dirs: set[Path] = set()
        for src_pkg in src_pkgs:
            src_dirs.update(TestStructureScanner._collect_dirs(src_pkg))
        test_dirs: set[Path] = set()
        for test_pkg in test_pkgs:
            test_dirs.update(TestStructureScanner._collect_dirs(test_pkg))
        test_only_dirs = sorted(test_dirs - src_dirs)

        # --- Build source index (merged across package roots) ---
        src_index: dict[str, dict[str, Any]] = {}
        for src_pkg in src_pkgs:
            src_index.update(TestStructureScanner._build_source_index(src_pkg))

        # --- Read all test files into memory for indirect reference checking ---
        # test_rel -> (test_pkg, content)
        test_files: dict[str, tuple[Path, str]] = {}
        for test_pkg in test_pkgs:
            for tp in ProjectConfig.iter_files(test_pkg, {".py"}):
                if tp.name == "__init__.py":
                    continue
                if not tp.name.startswith("test_"):
                    continue  # Skip conftest.py, fixtures.py, etc.
                rel = str(tp.relative_to(test_pkg))
                try:
                    test_files[rel] = (test_pkg, tp.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError):
                    test_files[rel] = (test_pkg, "")
        return test_only_dirs, src_index, test_files

    @staticmethod
    def _classify_test_files(
        test_files: dict[str, tuple[Path, str]],
        src_index: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Classify each test file as name-matched, misnamed, or orphaned."""
        misnamed: list[dict[str, Any]] = []
        misplaced: list[dict[str, Any]] = []
        orphaned: list[dict[str, Any]] = []

        # Track which source files have direct test coverage (name match or misnamed)
        directly_covered: set[str] = set()

        # Build a reverse index: class name -> source rel_path
        class_to_source: dict[str, str] = {}
        for src_rel, info in src_index.items():
            for cls_name in info["classes"]:
                class_to_source[cls_name] = src_rel

        # For each test file, store: test_rel -> (primary_source, content, referenced_classes)
        test_refs: list[dict[str, Any]] = []

        for test_rel, (test_pkg, content) in sorted(test_files.items()):
            c = TestStructureScanner._classify_one_test(
                test_rel, test_pkg, content, src_index, class_to_source
            )
            directly_covered.update(c["covered"])
            if c["misnamed"]:
                misnamed.append(c["misnamed"])
            if c["misplaced"]:
                misplaced.append(c["misplaced"])
            if c["orphaned"]:
                orphaned.append(c["orphaned"])
            if c["test_ref"]:
                test_refs.append(c["test_ref"])

        return {
            "misnamed": misnamed,
            "misplaced": misplaced,
            "orphaned": orphaned,
            "directly_covered": directly_covered,
            "test_refs": test_refs,
            "class_to_source": class_to_source,
        }

    @staticmethod
    def _classify_one_test(
        test_rel: str,
        test_pkg: Path,
        content: str,
        src_index: dict[str, dict[str, Any]],
        class_to_source: dict[str, str],
    ) -> dict[str, Any]:
        """Classify one test file — name-matched, misnamed, or orphaned."""
        result: dict[str, Any] = {
            "misnamed": None,
            "misplaced": None,
            "orphaned": None,
            "test_ref": None,
            "covered": set(),
        }
        test_path = test_pkg / test_rel
        test_dir_rel = str(test_path.relative_to(test_pkg).parent)

        # Find the best source file match by name prefix (longest prefix wins,
        # ties broken by preferring same directory)
        name_match = TestStructureScanner._match_test_to_source(
            test_path.name, src_index, test_dir_rel
        )
        # Find which source classes are referenced in the test content
        referenced_classes = TestStructureScanner._referenced_classes(content, src_index)

        if name_match:
            # Test file name matches a source file by prefix
            src_info = src_index[name_match]
            result["covered"] = {name_match}
            if src_info["dir"] != test_dir_rel:
                result["misplaced"] = {
                    "test_file": test_rel,
                    "source_file": name_match,
                    "test_dir": test_dir_rel,
                    "expected_dir": src_info["dir"],
                }
            result["test_ref"] = {
                "test_file": test_rel,
                "primary_source": name_match,
                "primary_classes": set(src_info["classes"]),
                "referenced_classes": referenced_classes,
            }
        elif referenced_classes:
            # Name doesn't match but it references source classes — misnamed
            ref_sources: dict[str, list[str]] = {}  # src_rel -> [classes]
            for cls_name in referenced_classes:
                src = class_to_source.get(cls_name)
                if src:
                    ref_sources.setdefault(src, []).append(cls_name)
            if ref_sources:
                # Primary source = the one with the most referenced classes
                primary = max(ref_sources, key=lambda s: len(ref_sources[s]))
                primary_info = src_index[primary]
                result["covered"] = set(ref_sources)
                result["misnamed"] = {
                    "test_file": test_rel,
                    "referenced_classes": ", ".join(sorted(referenced_classes)),
                    "expected_prefix": f"test_{primary_info['stem']}*.py",
                    "expected_dir": primary_info["dir"],
                }
                if primary_info["dir"] != test_dir_rel:
                    result["misplaced"] = {
                        "test_file": test_rel,
                        "source_file": primary,
                        "test_dir": test_dir_rel,
                        "expected_dir": primary_info["dir"],
                    }
                result["test_ref"] = {
                    "test_file": test_rel,
                    "primary_source": primary,
                    "primary_classes": set(ref_sources[primary]),
                    "referenced_classes": referenced_classes,
                }
        else:
            # Orphaned — doesn't match any source by name or class reference
            result["orphaned"] = {"test_file": test_rel}
        return result

    @staticmethod
    def _referenced_classes(
        content: str, src_index: dict[str, dict[str, Any]]
    ) -> list[str]:
        """List source class names that appear in the file content."""
        return [
            cls_name
            for info in src_index.values()
            for cls_name in info["classes"]
            if cls_name in content
        ]

    @staticmethod
    def _find_indirect_refs(
        test_refs: list[dict[str, Any]],
        class_to_source: dict[str, str],
        directly_covered: set[str],
    ) -> tuple[list[dict[str, Any]], set[str]]:
        """Find classes a test covers for sources with no direct test coverage."""
        indirect_refs: list[dict[str, Any]] = []
        indirectly_covered: set[str] = set()

        for ref in test_refs:
            # Find classes from source files without direct coverage
            other_classes: list[str] = []
            other_sources: set[str] = set()
            for cls_name in ref["referenced_classes"]:
                if cls_name in ref["primary_classes"]:
                    continue
                src = class_to_source.get(cls_name)
                if src and src != ref["primary_source"] and src not in directly_covered:
                    other_classes.append(cls_name)
                    other_sources.add(src)
                    indirectly_covered.add(src)

            if other_sources:
                indirect_refs.append(
                    {
                        "test_file": ref["test_file"],
                        "primary_source": ref["primary_source"],
                        "indirectly_tested_sources": ", ".join(sorted(other_sources)),
                        "indirectly_tested_classes": ", ".join(sorted(other_classes)),
                    }
                )
        return indirect_refs, indirectly_covered

    @staticmethod
    def _find_missing_tests(
        src_index: dict[str, dict[str, Any]],
        directly_covered: set[str],
        indirectly_covered: set[str],
    ) -> list[dict[str, Any]]:
        """Find source files covered neither directly nor indirectly."""
        missing: list[dict[str, Any]] = []
        for src_rel, info in sorted(src_index.items()):
            if src_rel in directly_covered or src_rel in indirectly_covered:
                continue
            missing.append(
                {
                    "source_file": src_rel,
                    "classes": ", ".join(info["classes"]),
                    "expected_prefix": f"test_{info['stem']}*.py",
                    "expected_dir": info["dir"],
                }
            )
        return missing

    @staticmethod
    def _emit_json(
        src_pkgs: list[Path],
        test_pkgs: list[Path],
        classified: dict[str, Any],
        orphaned_dirs: list[dict[str, Any]],
        missing: list[dict[str, Any]],
        indirect_refs: list[dict[str, Any]],
    ) -> None:
        """Emit the JSON report."""
        has_issues = bool(
            classified["misnamed"]
            or classified["misplaced"]
            or classified["orphaned"]
            or orphaned_dirs
            or missing
            or indirect_refs
        )
        print(
            json.dumps(
                {
                    "source_packages": [str(p) for p in src_pkgs],
                    "test_packages": [str(p) for p in test_pkgs],
                    "misnamed": classified["misnamed"],
                    "misplaced": classified["misplaced"],
                    "orphaned": classified["orphaned"],
                    "orphaned_dirs": orphaned_dirs,
                    "missing": missing,
                    "indirect_refs": indirect_refs,
                    "has_issues": has_issues,
                },
                indent=2,
            )
        )

    @staticmethod
    def _emit_text(
        src_pkgs: list[Path],
        test_pkgs: list[Path],
        classified: dict[str, Any],
        orphaned_dirs: list[dict[str, Any]],
        missing: list[dict[str, Any]],
        indirect_refs: list[dict[str, Any]],
    ) -> None:
        """Emit the markdown report."""
        misnamed = classified["misnamed"]
        misplaced = classified["misplaced"]
        orphaned = classified["orphaned"]
        has_issues = bool(
            misnamed or misplaced or orphaned or orphaned_dirs or missing or indirect_refs
        )

        print("# Test Structure — Validation Report\n")
        print(f"**Source packages:** {', '.join(f'`{p}`' for p in src_pkgs)}")
        print(f"**Test packages:** {', '.join(f'`{p}`' for p in test_pkgs)}\n")

        TestStructureScanner._emit_misnamed(misnamed)
        TestStructureScanner._emit_misplaced(misplaced)
        TestStructureScanner._emit_orphaned(orphaned, orphaned_dirs)
        TestStructureScanner._emit_missing(missing)
        TestStructureScanner._emit_indirect(indirect_refs)
        TestStructureScanner._emit_summary(
            misnamed, misplaced, orphaned, orphaned_dirs, missing, indirect_refs, has_issues
        )

    @staticmethod
    def _emit_misnamed(misnamed: list[dict[str, Any]]) -> None:
        """Emit the misnamed-tests section."""
        print(f"## 1. Misnamed tests ({len(misnamed)})\n")
        if misnamed:
            print("| Test file | Referenced classes | Expected prefix | Expected dir |")
            print("|---|---|---|---|")
            for item in misnamed:
                print(
                    f"| `{item['test_file']}` | {item['referenced_classes']} "
                    f"| `{item['expected_prefix']}` | `{item['expected_dir']}/ |"
                )
        else:
            print("*None — all test file names match their source stem or class name.*")
        print()

    @staticmethod
    def _emit_misplaced(misplaced: list[dict[str, Any]]) -> None:
        """Emit the misplaced-tests section."""
        print(f"## 2. Misplaced tests ({len(misplaced)})\n")
        if misplaced:
            print("| Test file | Source file | Current dir | Expected dir |")
            print("|---|---|---|---|")
            for item in misplaced:
                print(
                    f"| `{item['test_file']}` | `{item['source_file']}` "
                    f"| `{item['test_dir']}/ | `{item['expected_dir']}/ |"
                )
        else:
            print("*None — all test files are in the correct mirrored directory.*")
        print()

    @staticmethod
    def _emit_orphaned(
        orphaned: list[dict[str, Any]], orphaned_dirs: list[dict[str, Any]]
    ) -> None:
        """Emit the orphaned tests section (dirs first, then files)."""
        total_orphaned = len(orphaned) + len(orphaned_dirs)
        print(f"## 3. Orphaned tests ({total_orphaned})\n")
        if orphaned_dirs:
            print("### Orphaned test directories\n")
            print("| Test directory |")
            print("|---|")
            for item in orphaned_dirs:
                print(f"| `{item['test_dir']}` |")
            print()
        if orphaned:
            print("### Orphaned test files\n")
            print("| Test file |")
            print("|---|")
            for item in orphaned:
                print(f"| `{item['test_file']}` |")
        if not orphaned and not orphaned_dirs:
            print("*None — all test files and directories match a source counterpart.*")
        print()

    @staticmethod
    def _emit_missing(missing: list[dict[str, Any]]) -> None:
        """Emit the missing-tests section."""
        print(f"## 4. Missing tests ({len(missing)})\n")
        if missing:
            print("| Source file | Classes | Expected prefix | Expected dir |")
            print("|---|---|---|---|")
            for item in missing:
                print(
                    f"| `{item['source_file']}` | {item['classes']} "
                    f"| `{item['expected_prefix']}` | `{item['expected_dir']}/ |"
                )
        else:
            print("*None — all source files with classes have direct or indirect tests.*")
        print()

    @staticmethod
    def _emit_indirect(indirect_refs: list[dict[str, Any]]) -> None:
        """Emit the indirect-references section (informative only)."""
        print(f"## 5. Indirect references ({len(indirect_refs)}) — informative only\n")
        if indirect_refs:
            print(
                "| Test file | Primary source | Indirectly tested sources | "
                "Indirectly tested classes |"
            )
            print("|---|---|---|---|")
            for item in indirect_refs:
                print(
                    f"| `{item['test_file']}` | `{item['primary_source']}` "
                    f"| `{item['indirectly_tested_sources']}` | "
                    f"{item['indirectly_tested_classes']} |"
                )
        else:
            print("*None — no test file provides indirect coverage for uncovered source files.*")
        print()

    @staticmethod
    def _emit_summary(
        misnamed: list[dict[str, Any]],
        misplaced: list[dict[str, Any]],
        orphaned: list[dict[str, Any]],
        orphaned_dirs: list[dict[str, Any]],
        missing: list[dict[str, Any]],
        indirect_refs: list[dict[str, Any]],
        has_issues: bool,
    ) -> None:
        """Emit the summary table and result line."""
        total_orphaned = len(orphaned) + len(orphaned_dirs)
        print("---\n")
        print("## Summary\n")
        print("| Category | Count | Action |")
        print("|---|---|---|")
        print(f"| Misnamed tests | {len(misnamed)} | Rename |")
        print(f"| Misplaced tests | {len(misplaced)} | Move |")
        print(f"| Orphaned tests | {total_orphaned} | Delete or investigate |")
        print(f"| Missing tests | {len(missing)} | Write new tests |")
        print(f"| Indirect references | {len(indirect_refs)} | Informative only |")
        print()

        if has_issues:
            print("**Result:** STRUCTURAL MISMATCHES FOUND\n")
        else:
            print("**Result:** all clear\n")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(TestStructureScanner.main())
