#!/usr/bin/env python3
"""Streamline Google-style docstrings per python-code-style Pattern 6.

Type annotations already convey argument and return types.  This script
removes docstring sections that merely repeat what the signature says, and
optionally strips docstrings from elements that do not need them.

Transformations (always safe — only act when the type annotation fully
describes the element):

  1. **Redundant ``Args:`` section** — removed when *every* entry's
     description is trivially derivable from the corresponding type
     annotation (empty, equal to the annotation, or "the <arg_name>").
     Entries for arguments that lack a type annotation are never
     considered trivial, so the section is kept.

  2. **Redundant ``Returns:`` section** — removed when the description is
     empty or equal to the return annotation.

  3. **Obsolete docstring** — removed entirely when, after stripping
     redundant sections, nothing meaningful remains (no summary text and
     no kept sections).

Opt-in transformations (require explicit flags):

  --strip-private   Remove docstrings from private functions/methods
                    (leading underscore, but not dunder methods).
  --strip-tests     Remove docstrings from ``test_*`` functions.
  --strip-nested    Remove docstrings from nested/local functions.
  --strip-obvious-init
                    Remove ``__init__`` docstrings when every parameter
                    has a type annotation (the signature is
                    self-explanatory).

Elements that are **never** touched:

  - Module-level docstrings
  - ``Raises:``, ``Example:``, ``Note:``, ``Yields:`` and other
    non-Args/Returns sections (they carry information annotations
    cannot express)
  - Class ``Attributes:`` sections
  - Summary lines (always preserved unless the whole docstring is
    obsolete)

Usage:
    python3 streamline_docstrings.py [directory] [options]

Arguments:
    directory             Root directory to scan (default: src).

Options:
    --apply               Write changes to disk.  Default: dry-run report.
    --strip-private       Also remove docstrings from private functions.
    --strip-tests         Also remove docstrings from test functions.
    --strip-nested        Also remove docstrings from nested/local functions.
    --strip-obvious-init  Also remove obvious __init__ docstrings.
    --strict              Exit with code 1 if any findings (even in dry-run).
    --skip                Skip this check entirely (exit 0 with 'skipped'
                          message).
    --ignore-dirs         Comma-separated directory names to skip.

Exit code: 0 if no findings (or --skip / non-strict), 1 if findings found
           with --strict.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_HEADERS: frozenset[str] = frozenset({
    "args",
    "arguments",
    "returns",
    "yields",
    "raises",
    "example",
    "examples",
    "note",
    "notes",
    "warning",
    "warnings",
    "see also",
    "references",
    "todo",
    "attributes",
    "parameters",
})

# Sections that may be removed when redundant.
REDUCIBLE_SECTIONS: frozenset[str] = frozenset({"args", "arguments", "parameters", "returns"})

# Sections that are never reduced — they carry info annotations cannot express.
PROTECTED_SECTIONS: frozenset[str] = frozenset({
    "yields", "raises", "example", "examples", "note", "notes",
    "warning", "warnings", "see also", "references", "todo", "attributes",
})

DUNDER_METHODS: frozenset[str] = frozenset({
    "__init__", "__new__", "__del__", "__repr__", "__str__", "__bytes__",
    "__format__", "__lt__", "__le__", "__eq__", "__ne__", "__gt__", "__ge__",
    "__hash__", "__bool__", "__getattr__", "__getattribute__", "__setattr__",
    "__delattr__", "__dir__", "__get__", "__set__", "__delete__", "__set_name__",
    "__class_getitem__", "__init_subclass__", "__call__", "__len__", "__len__",
    "__getitem__", "__setitem__", "__delitem__", "__iter__", "__next__",
    "__contains__", "__add__", "__sub__", "__mul__", "__matmul__", "__truediv__",
    "__enter__", "__exit__", "__aenter__", "__aexit__", "__await__",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single streamline finding for one docstring."""

    file: Path
    line: int
    kind: str  # "redundant_args", "redundant_returns", "obsolete",
    # "private", "test", "nested", "obvious_init"
    detail: str
    node: ast.AST
    # New docstring text after streamlining (None = remove entirely).
    new_text: str | None = None
    # Whether the docstring should be removed entirely.
    remove: bool = False


@dataclass
class FileReport:
    """Collected findings and edits for a single file."""

    path: Path
    findings: list[Finding] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Docstring parsing (Google-style)
# ---------------------------------------------------------------------------


def _is_section_header(line: str) -> bool:
    """Return True if *line* is a Google-style section header.

    After ``inspect.cleandoc`` section headers sit at column 0 and end with
    a colon, e.g. ``Args:``, ``Returns:``, ``Raises:``.
    """
    if line.startswith((" ", "\t")):
        return False
    stripped = line.strip()
    if not stripped.endswith(":"):
        return False
    name = stripped[:-1].strip().lower()
    return name in SECTION_HEADERS


def parse_docstring(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Split a cleaned docstring into (summary_lines, sections).

    Each section is a ``(header, body_lines)`` tuple where *body_lines*
    preserves the original relative indentation.
    """
    lines = text.split("\n")
    summary: list[str] = []
    sections: list[tuple[str, list[str]]] = []

    i = 0
    # Collect summary (everything before the first section header).
    while i < len(lines) and not _is_section_header(lines[i]):
        summary.append(lines[i])
        i += 1

    while i < len(lines):
        if _is_section_header(lines[i]):
            header = lines[i]
            body: list[str] = []
            i += 1
            while i < len(lines) and not _is_section_header(lines[i]):
                body.append(lines[i])
                i += 1
            # Strip trailing blank lines from the section body.
            while body and not body[-1].strip():
                body.pop()
            sections.append((header, body))
        else:
            i += 1

    return summary, sections


def rebuild_docstring(summary: list[str], sections: list[tuple[str, list[str]]]) -> str:
    """Reassemble a cleaned docstring from summary lines and kept sections.

    A trailing blank line is added after the last section to satisfy the
    Google-style D413 rule (blank line after last section).
    """
    parts = [line for line in summary]
    while parts and not parts[-1].strip():
        parts.pop()
    for header, body in sections:
        parts.append("")
        parts.append(header)
        parts.extend(body)
    while parts and not parts[0].strip():
        parts.pop(0)
    while parts and not parts[-1].strip():
        parts.pop()
    # Google style (D413): blank line after the last section.
    if sections:
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Triviality heuristics
# ---------------------------------------------------------------------------


def _arg_name_from_entry(name_part: str) -> str:
    """Extract the bare argument name from an Args entry left-hand side.

    Handles ``x``, ``x (int)``, ``*args``, ``**kwargs``.
    """
    bare = name_part.split("(")[0].strip()
    return bare.lstrip("*")


def is_trivial_arg_desc(
    entry_name: str, desc: str, annotation: str | None
) -> bool:
    """Return True if an Args entry merely repeats the type annotation.

    If *annotation* is ``None`` (the argument lacks a type annotation) the
    entry is never trivial — the docstring is the only source of type info.
    """
    if annotation is None:
        return False
    if not desc:
        return True
    arg_name = _arg_name_from_entry(entry_name)
    desc_clean = desc.strip().rstrip(".")
    ann_clean = annotation.strip()
    desc_lower = desc_clean.lower()
    arg_lower = arg_name.lower()

    if desc_clean == ann_clean:
        return True
    if desc_lower == arg_lower:
        return True
    if desc_lower in (f"the {arg_lower}", f"a {arg_lower}", f"an {arg_lower}"):
        return True
    # "str" / "int" etc. used as the whole description.
    if desc_clean == ann_clean:
        return True
    return False


def is_trivial_returns_desc(desc: str, return_annotation: str | None) -> bool:
    """Return True if a Returns description merely repeats the return type."""
    if return_annotation is None:
        return False
    desc_clean = desc.strip().rstrip(".")
    if not desc_clean:
        return True
    if desc_clean == return_annotation.strip():
        return True
    return False


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _annotation_str(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def get_arg_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str | None]:
    """Map every argument name to its annotation source (or ``None``)."""
    annotations: dict[str, str | None] = {}
    args = node.args
    all_args: list[ast.arg] = []
    all_args.extend(args.posonlyargs)
    all_args.extend(args.args)
    all_args.extend(args.kwonlyargs)
    for arg in all_args:
        annotations[arg.arg] = _annotation_str(arg.annotation)
    if args.vararg:
        annotations[args.vararg.arg] = _annotation_str(args.vararg.annotation)
    if args.kwarg:
        annotations[args.kwarg.arg] = _annotation_str(args.kwarg.annotation)
    return annotations


def get_return_annotation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    return _annotation_str(node.returns)


def _is_private(name: str) -> bool:
    return name.startswith("_") and name not in DUNDER_METHODS and not (
        name.startswith("__") and name.endswith("__")
    )


def _is_test_function(name: str) -> bool:
    return name.startswith("test_")


def _is_test_file(path: Path) -> bool:
    """Return True if *path* is a test file (test_*.py or under tests/)."""
    if path.name.startswith("test_"):
        return True
    return any(part == "tests" for part in path.parts)


def _is_nested(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if *node* is nested inside another function."""
    return isinstance(node.parent, (ast.FunctionDef, ast.AsyncFunctionDef))  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Source rendering
# ---------------------------------------------------------------------------


_DOCSTRING_RE = re.compile(r"^(\s*)([a-zA-Z]*)(""" + '"""' + r"|''')")


def _detect_prefix_quote(raw: str) -> tuple[str, str] | None:
    """Return (prefix, quote) from the raw source of a docstring literal."""
    match = _DOCSTRING_RE.match(raw)
    if not match:
        return "", '"""'
    return match.group(2), match.group(3)


def render_docstring(indent: str, prefix: str, quote: str, text: str) -> str:
    """Render a docstring literal source block from cleaned *text*."""
    lines = text.split("\n")
    opening = f"{indent}{prefix}{quote}"
    if len(lines) == 1 and lines[0]:
        return f"{opening}{lines[0]}{quote}"
    if not lines or (len(lines) == 1 and not lines[0]):
        return f"{opening}{quote}"
    result = [f"{opening}{lines[0]}"]
    for line in lines[1:]:
        result.append(f"{indent}{line}" if line else "")
    result.append(f"{indent}{quote}")
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _analyze_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
    strip_private: bool,
    strip_tests: bool,
    strip_nested: bool,
    strip_obvious_init: bool,
) -> Finding | None:
    """Analyse a single function/method docstring.  Return a Finding or None."""
    docstring = ast.get_docstring(node, clean=True)
    if docstring is None:
        return None

    name = node.name
    arg_annotations = get_arg_annotations(node)
    return_annotation = get_return_annotation(node)

    # --- Opt-in: strip private / test / nested / obvious-init -------------
    if strip_private and _is_private(name):
        return Finding(path, node.lineno, "private", f"{name}() — private", node, remove=True)
    if strip_tests and _is_test_function(name) and _is_test_file(path):
        return Finding(path, node.lineno, "test", f"{name}() — test function", node, remove=True)
    if strip_nested and _is_nested(node):
        return Finding(path, node.lineno, "nested", f"{name}() — nested function", node, remove=True)
    if (
        strip_obvious_init
        and name == "__init__"
        and _init_is_obvious(arg_annotations)
    ):
        return Finding(
            path, node.lineno, "obvious_init",
            "__init__ — all params have type annotations",
            node, remove=True,
        )

    # --- Default: reduce redundant Args / Returns -------------------------
    summary, sections = parse_docstring(docstring)
    kept_sections: list[tuple[str, list[str]]] = []
    removed_headers: list[str] = []

    for header, body in sections:
        header_lower = header.strip().rstrip(":").strip().lower()

        if header_lower in {"args", "arguments", "parameters"}:
            if _args_section_is_redundant(body, arg_annotations):
                removed_headers.append("Args")
                continue
        elif header_lower == "returns":
            if _returns_section_is_redundant(body, return_annotation):
                removed_headers.append("Returns")
                continue

        kept_sections.append((header, body))

    if not removed_headers:
        return None

    new_text = rebuild_docstring(summary, kept_sections)
    remove = not new_text.strip()
    detail = f"removed redundant section(s): {', '.join(removed_headers)}"
    return Finding(path, node.lineno, "redundant", detail, node,
                   new_text=new_text, remove=remove)


def _init_is_obvious(arg_annotations: dict[str, str | None]) -> bool:
    """Return True if every __init__ parameter (except self) has an annotation."""
    return all(
        ann is not None
        for name, ann in arg_annotations.items()
        if name not in ("self", "cls")
    )


def _args_section_is_redundant(
    body: list[str], arg_annotations: dict[str, str | None]
) -> bool:
    """Return True when every Args entry is trivially derivable from annotations."""
    entries = _parse_args_entries(body)
    if not entries:
        # An empty Args section is redundant.
        return True
    for name_part, desc in entries:
        arg_name = _arg_name_from_entry(name_part)
        if arg_name in ("self", "cls"):
            continue
        annotation = arg_annotations.get(arg_name)
        if not is_trivial_arg_desc(name_part, desc, annotation):
            return False
    return True


def _returns_section_is_redundant(body: list[str], return_annotation: str | None) -> bool:
    desc = "\n".join(body).strip()
    return is_trivial_returns_desc(desc, return_annotation)


def _parse_args_entries(body: list[str]) -> list[tuple[str, str]]:
    """Parse Args body lines into (name_part, description) tuples."""
    entries: list[tuple[str, str]] = []
    current_name: str | None = None
    current_desc: list[str] = []

    for line in body:
        stripped = line.strip()
        if not stripped:
            if current_name is not None:
                current_desc.append("")
            continue
        # A new entry starts at the base indentation level (4 spaces after
        # cleandoc).  Continuation lines are indented further.
        if not line.startswith("        ") and ":" in stripped:
            if current_name is not None:
                entries.append((current_name, " ".join(current_desc).strip()))
            name_part, _, desc = stripped.partition(":")
            current_name = name_part.strip()
            current_desc = [desc.strip()]
        else:
            if current_name is not None:
                current_desc.append(stripped)

    if current_name is not None:
        entries.append((current_name, " ".join(current_desc).strip()))
    return entries


# ---------------------------------------------------------------------------
# Parent tracking
# ---------------------------------------------------------------------------


def _annotate_parents(tree: ast.AST) -> None:
    """Attach ``parent`` attributes to every node for nested-function checks."""
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------


def process_file(
    path: Path,
    strip_private: bool,
    strip_tests: bool,
    strip_nested: bool,
    strip_obvious_init: bool,
) -> FileReport:
    """Analyse a single .py file and return its report."""
    report = FileReport(path=path)
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return report

    _annotate_parents(tree)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            finding = _analyze_function(
                node, path,
                strip_private, strip_tests, strip_nested, strip_obvious_init,
            )
            if finding is not None:
                report.findings.append(finding)
        # Class docstrings: only reduce redundant Args/Returns is not
        # applicable; classes are left untouched (Attributes is protected).

    return report


def apply_edits(path: Path, findings: list[Finding]) -> str:
    """Apply findings to *path* and return the new source text.

    Findings are applied bottom-to-top so earlier line numbers stay valid.
    """
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    # Sort by start line descending.
    ordered = sorted(findings, key=lambda f: f.node.lineno, reverse=True)

    for finding in ordered:
        node = finding.node
        # The docstring is the first statement of the function/class body.
        if not hasattr(node, "body") or not node.body:
            continue
        doc_expr = node.body[0]
        if not isinstance(doc_expr, ast.Expr) or not isinstance(doc_expr.value, ast.Constant):
            continue
        if not isinstance(doc_expr.value.value, str):
            continue

        start = doc_expr.lineno
        end = doc_expr.end_lineno
        raw_block = "".join(lines[start - 1 : end])
        indent = re.match(r"^(\s*)", raw_block).group(1)
        prefix, quote = _detect_prefix_quote(raw_block)

        if finding.remove or finding.new_text is None:
            # If the docstring is the only AST statement in the body,
            # replacing it with nothing would leave an empty body (syntax
            # error).  Insert a ``pass`` statement to keep the body valid.
            if len(node.body) == 1:
                pass_line = f"{indent}pass\n"
                lines[start - 1 : end] = [pass_line]
            else:
                # Remove the docstring lines entirely.
                del lines[start - 1 : end]
                # Remove a single trailing blank line if one is left behind.
                if start - 1 < len(lines) and lines[start - 1].strip() == "":
                    del lines[start - 1]
        else:
            rendered = render_docstring(indent, prefix, quote, finding.new_text)
            new_lines = [line + "\n" for line in rendered.split("\n")]
            # The last line may already end with a newline from the original;
            # preserve the original line ending of the final docstring line.
            if lines[end - 1].endswith("\n"):
                new_lines[-1] = new_lines[-1].rstrip("\n") + "\n"
            else:
                new_lines[-1] = new_lines[-1].rstrip("\n")
            lines[start - 1 : end] = new_lines

    return "".join(lines)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def print_report(reports: list[FileReport], root: Path, apply_mode: bool) -> int:
    """Print a human-readable report.  Return the total finding count."""
    all_findings: list[Finding] = []
    for report in reports:
        all_findings.extend(report.findings)

    print("=" * 70)
    print("DOCSTRING STREAMLINE — REPORT")
    print("=" * 70)

    if not all_findings:
        print("\nResult: all clear\n")
        return 0

    # Group by kind.
    by_kind: dict[str, list[Finding]] = {}
    for f in all_findings:
        by_kind.setdefault(f.kind, []).append(f)

    kind_labels: dict[str, str] = {
        "redundant": "Redundant Args/Returns sections",
        "private": "Private function docstrings (use --strip-private to remove)",
        "test": "Test function docstrings (use --strip-tests to remove)",
        "nested": "Nested function docstrings (use --strip-nested to remove)",
        "obvious_init": "Obvious __init__ docstrings (use --strip-obvious-init to remove)",
    }

    for kind, label in kind_labels.items():
        items = by_kind.get(kind, [])
        if not items:
            continue
        print(f"\n## {label} ({len(items)} finding{'s' if len(items) != 1 else ''})\n")
        for f in items:
            print(f"  {_rel(f.file, root)}:{f.line}")
            print(f"    {f.detail}")

    total = len(all_findings)
    print()
    if apply_mode:
        print(f"Result: {total} docstring(s) streamlined (apply mode)")
    else:
        print(f"Result: {total} finding(s) (dry-run mode). Use --apply to fix.")
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Streamline Google-style docstrings per python-code-style Pattern 6.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="src",
        help="Root directory to scan (default: src)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk (default: dry-run report only).",
    )
    parser.add_argument(
        "--strip-private",
        action="store_true",
        help="Also remove docstrings from private functions (_name).",
    )
    parser.add_argument(
        "--strip-tests",
        action="store_true",
        help="Also remove docstrings from test_* functions.",
    )
    parser.add_argument(
        "--strip-nested",
        action="store_true",
        help="Also remove docstrings from nested/local functions.",
    )
    parser.add_argument(
        "--strip-obvious-init",
        action="store_true",
        help="Also remove __init__ docstrings when all params have annotations.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any findings are reported.",
    )
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip this check entirely (exit 0 with 'skipped' message).",
    )
    parser.add_argument(
        "--ignore-dirs",
        default="",
        help="Comma-separated directory names to skip (e.g. __pycache__,assets).",
    )
    args = parser.parse_args()

    if args.skip:
        print("=" * 70)
        print("DOCSTRING STREAMLINE — REPORT")
        print("=" * 70)
        print("\nResult: SKIPPED (--skip flag)\n")
        return 0

    root = Path(args.directory)
    if not root.exists():
        print(f"Error: directory '{root}' does not exist", file=sys.stderr)
        return 1

    ignore = {d.strip() for d in args.ignore_dirs.split(",") if d.strip()}
    ignore.add("__pycache__")

    reports: list[FileReport] = []
    for py in root.rglob("*.py"):
        if any(part in ignore for part in py.parts):
            continue
        report = process_file(
            py,
            strip_private=args.strip_private,
            strip_tests=args.strip_tests,
            strip_nested=args.strip_nested,
            strip_obvious_init=args.strip_obvious_init,
        )
        if report.findings:
            reports.append(report)

    total = print_report(reports, root, apply_mode=args.apply)

    if args.apply:
        for report in reports:
            new_source = apply_edits(report.path, report.findings)
            report.path.write_text(new_source, encoding="utf-8")

    if args.strict and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
