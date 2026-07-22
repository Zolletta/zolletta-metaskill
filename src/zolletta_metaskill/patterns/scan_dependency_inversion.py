#!/usr/bin/env python3
"""Dependency Inversion validator.

Detects classes that instantiate their dependencies internally instead of
receiving them as constructor parameters (dependency injection). This violates
the Dependency Inversion Principle: "depend on abstractions, not concretions."

When a class creates `self.client = GitLabClient(...)` in __init__ or a method,
it is tightly coupled to that concrete class. It should instead receive the
client as a parameter: `def __init__(self, client: GitLabClient)`.

Exclusions:
  - Files matching entry-point patterns (main, cli, app, __main__) — these are
    composition roots where object creation is expected.
  - Classes that create DI containers (make_container, Container, etc.) — these
    are semantic composition roots, detected by AST analysis regardless of
    filename.
  - Data classes / dataclasses / NamedTuples / TypedDicts / Enums.
  - Value objects and simple structs (classes with only __init__ and properties,
    no method calls to other classes).
  - Standard library types (list, dict, set, str, int, etc.).
  - Factory classes (classes with "Factory" in the name or that only create
    objects in their methods).

Usage:
    python3 scan_dependency_inversion.py <directory>
        [--entry-points <pattern1,pattern2,...>]
        [--skip] [--strict]

Arguments:
    directory       Root directory to scan (default: src)

Options:
    --entry-points <patterns>  Comma-separated filename patterns to exclude
                               from checking (default: main,cli,app,__main__,
                               myproject,manage,wsgi,asgi,conftest)
    --skip                     Skip this check entirely
    --strict                   Exit with code 1 if violations are found

Exit code: 0 if no violations (or --skip), 1 if violations found with --strict.

"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

STDLIB_TYPES = {
    "list", "dict", "set", "frozenset", "tuple", "str", "int", "float",
    "bool", "bytes", "bytearray", "complex", "None", "type", "object",
    "Path", "Decimal", "Fraction", "datetime", "date", "time", "timedelta",
    "OrderedDict", "defaultdict", "Counter", "deque", "ChainMap",
    "namedtuple",
}

# Patterns that indicate a value object / data holder, not a service
DATA_CLASS_MARKERS = {"dataclass", "NamedTuple", "TypedDict"}
ENTRY_POINT_DEFAULTS = {"main", "cli", "app", "__main__", "myproject", "manage",
                        "wsgi", "asgi", "conftest"}

# DI container creation function names that indicate a composition root.
# A class that calls any of these is responsible for wiring the DI container
# and is excluded from DIP violation reporting — someone has to create it.
DI_CONTAINER_FACTORIES = {
    "make_container",       # dishka
    "Container",            # generic
    "DIContainer",          # generic
    "create_container",     # generic
    "build_container",      # generic
    "AsyncContainer",       # dishka async
}


def _is_data_class(node: ast.ClassDef) -> bool:
    """Check if a class is a dataclass, NamedTuple, TypedDict, or Enum."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id in DATA_CLASS_MARKERS:
            return True
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
            if dec.func.id in DATA_CLASS_MARKERS:
                return True
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in ("Enum", "IntEnum", "Flag", "IntFlag"):
            return True
        if isinstance(base, ast.Name) and base.id in DATA_CLASS_MARKERS:
            return True
    return False


def _is_factory(name: str) -> bool:
    """Check if a class name suggests it's a factory."""
    return "Factory" in name or "Builder" in name


def _is_entry_point(filename: str, patterns: set[str]) -> bool:
    """Check if a file is an entry point / composition root."""
    stem = filename.replace(".py", "")
    for pattern in patterns:
        if pattern in stem:
            return True
    return False


def _is_composition_root(class_node: ast.ClassDef) -> bool:
    """Check if a class is a composition root by detecting DI container creation.

    A class that calls make_container(), Container(), or similar DI-framework
    functions is a composition root — it is the place where the DI container
    is assembled. Object creation is expected there and is not a DIP violation.
    """
    for node in ast.walk(class_node):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in DI_CONTAINER_FACTORIES:
                return True
            if isinstance(func, ast.Attribute) and func.attr in DI_CONTAINER_FACTORIES:
                return True
    return False


def _extract_created_dependencies(class_node: ast.ClassDef) -> list[dict]:
    """Find places where the class instantiates other classes and assigns to self."""
    violations = []

    for item in class_node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for node in ast.walk(item):
            # Pattern: self.xxx = SomeClass(...)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"):
                        continue
                    # Check if the assigned value is a constructor call
                    value = node.value
                    if isinstance(value, ast.Call):
                        created_class = _get_class_name_from_call(value)
                        if created_class and _is_real_dependency(created_class):
                            violations.append({
                                "class": class_node.name,
                                "created": created_class,
                                "attribute": target.attr,
                                "method": item.name,
                                "line": node.lineno,
                            })

            # Pattern: self.xxx = SomeClass  (assigning class, not instance — less common)
            # Skip this — it's usually a legitimate reference

    return violations


def _get_class_name_from_call(call: ast.Call) -> str | None:
    """Extract the class name being instantiated from a Call node."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        # e.g., module.SomeClass or self.factory.create()
        # Only flag if it looks like a class instantiation (capitalized name)
        if func.attr[0:1].isupper():
            return func.attr
        # factory.create() — not a direct instantiation
        return None
    return None


def _is_real_dependency(class_name: str) -> bool:
    """Check if a class name represents a real dependency (not a stdlib type)."""
    if class_name in STDLIB_TYPES:
        return False
    # Skip small utility types that are commonly instantiated inline
    if class_name in ("Mock", "MagicMock", "patch", "PropertyMock"):
        return False
    # Skip generic container constructors
    if class_name in ("list", "dict", "set", "tuple", "frozenset"):
        return False
    return True


def _get_constructor_params(class_node: ast.ClassDef) -> set[str]:
    """Get parameter names from __init__ (excluding self)."""
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            return {a.arg for a in item.args.args[1:]}  # skip self
    return set()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dependency Inversion validator — detect dependencies created instead of injected."
    )
    parser.add_argument("directory", nargs="?", default="src",
                        help="Root directory to scan (default: src)")
    parser.add_argument("--entry-points", default="",
                        help="Comma-separated filename patterns to exclude (default: main,cli,app,...)")
    parser.add_argument("--skip", action="store_true",
                        help="Skip this check entirely")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if violations are found")
    args = parser.parse_args()

    if args.skip:
        print("=" * 70)
        print("DEPENDENCY INVERSION — VALIDATION REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    entry_patterns = set(args.entry_points.split(",")) if args.entry_points else ENTRY_POINT_DEFAULTS

    all_violations: list[dict] = []
    scanned_files = 0
    skipped_files = 0

    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        if py.name == "__init__.py":
            continue

        rel_path = str(py.relative_to(root))

        if _is_entry_point(py.name, entry_patterns):
            skipped_files += 1
            continue

        scanned_files += 1

        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if _is_data_class(node):
                continue
            if _is_factory(node.name):
                continue
            if _is_composition_root(node):
                continue

            init_params = _get_constructor_params(node)
            created = _extract_created_dependencies(node)

            for v in created:
                # If the created class is already a constructor param, it's not a violation
                # (it might be re-wrapped or stored differently)
                if v["created"] in init_params:
                    continue
                v["file"] = rel_path
                all_violations.append(v)

    print("=" * 70)
    print("DEPENDENCY INVERSION — VALIDATION REPORT")
    print("=" * 70)
    print(f"\nFiles scanned: {scanned_files}  |  Skipped (entry points): {skipped_files}")

    if all_violations:
        print(f"\n## Dependencies created internally instead of injected ({len(all_violations)} found)\n")
        for v in all_violations:
            print(f"  {v['class']}.{v['method']}() creates {v['created']}()")
            print(f"    self.{v['attribute']} = {v['created']}(...)")
            print(f"    -> {v['file']}:{v['line']}")
            print(f"    Fix: pass {v['created']} as a constructor parameter:")
            print(f"         def __init__(self, {v['attribute']}: {v['created']})")
    else:
        print("\n## Dependencies created internally instead of injected: none")

    print()
    if all_violations and args.strict:
        print("Result: DI VIOLATIONS FOUND (strict mode)")
        return 1
    elif all_violations:
        print("Result: DI violations found (report-only mode)")
    else:
        print("Result: all clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
