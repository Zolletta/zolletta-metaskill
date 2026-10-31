#!/usr/bin/env python3
"""Flag hard-wrapped prose paragraphs in markdown files.

The repository convention (see ``AGENTS.md`` §Markdown and
``docs/explanation/documentation/standards.md``) is that a paragraph lives on
one line and is never wrapped at a fixed column width, because markdown
renders a newline as a space and the wrap buys nothing but diff noise. The
convention is **unenforced**: ``.markdownlint.yaml`` sets ``MD013: false``
deliberately, since a line-length rule would demand the exact wrapping the
convention forbids. This scanner closes that gap.

The rule, taken from ``standards.md``: a paragraph is a run of consecutive
non-blank lines that are not headings, list items, blockquotes, code fences,
tables, or HTML, and every line in such a run belongs on one line. One reading
of that sentence would exempt a list item's continuation lines, but the corpus
house style settles it: ADR-0006 and ADR-0008 keep every bullet on a single
line. So a run is broken by a blank line, a heading, a table row, a fence, an
HTML comment, or **the start of another list item** — and everything else,
including an item's indented continuations, joins.

Frontmatter is excluded, and so are blockquotes: they are not paragraphs by
the definition above, and joining ``> a`` onto ``> b`` would alter the quote.

One finding is emitted per paragraph, anchored at its first line and naming
the full span, because "join lines 16-17" is actionable where "line 16 does
not end in punctuation" is not.

Which files are scanned is driven by ``.zolletta-metaskill/settings.json``
(created by the setup guard): the single root is ``documentation.dir``,
matching every other documentor tool — markdown outside it is out of scope.
The check is **opt-in** via ``documentation.check_unwrapped_prose`` (default
``false``) and reports SKIPPED with exit 0 when off, like every other toggle
in the schema. It is opt-in rather than on by default because a tree that
predates the convention can hold a long backlog, and formatting noise buries
real drift findings. Git ignored files are skipped.

Usage:
    python3 unwrapped_prose_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 on success (violations are report-only); 1 when no configured
documentation directory exists on disk.

"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.core.structs import Finding


class UnwrappedProseScanner:
    """Flag markdown paragraphs that are hard-wrapped across lines."""

    CATEGORY = "unwrapped_prose"
    SEVERITY = "low"
    EXTENSIONS = {".md", ".markdown"}
    DEFAULT_ENABLED = False
    DEFAULT_SETTINGS_PATH = ProjectConfig.DEFAULT_SETTINGS_PATH
    LIST_ITEM = re.compile(r"^([-*+]|\d+[.)])\s+")
    HEADING = re.compile(r"^#{1,6}(\s|$)")
    FENCE = re.compile(r"^(```|~~~)")
    TERMINATORS = frozenset(".!?:;)]}")

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _body_start(lines: list[str]) -> int:
        """Return the index of the first line after a leading frontmatter block.

        A file opening with ``---`` is treated as having frontmatter up to the
        next ``---``. Any other ``---`` is a thematic break and is left for
        :meth:`_run_ends_here`.
        """
        if not lines or lines[0].strip() != "---":
            return 0
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
        # pragma: no mutate start — equivalent: reaching here means lines[0] == "---", a block
        # boundary, so starting at 0 or 1 scans identically
        return 0
        # pragma: no mutate end

    @staticmethod
    def _is_block_boundary(stripped: str) -> bool:
        """Return whether *stripped* always ends a paragraph run.

        True for a blank line, a fence delimiter, a heading, a table row, an
        HTML comment, a thematic break, and a blockquote — the last because
        the rule does not define a blockquote as a paragraph, and joining
        ``> a`` onto ``> b`` would alter the quote.
        """
        if not stripped:
            return True
        if stripped in ("---", "***", "___"):
            return True
        if stripped.startswith(("|", ">", "<!--")):
            return True
        return bool(
            UnwrappedProseScanner.HEADING.match(stripped)
            or UnwrappedProseScanner.FENCE.match(stripped)
        )

    @staticmethod
    def _starts_new_list_item(stripped: str) -> bool:
        """Return whether *stripped* opens a new list item.

        This ends a run only in the middle of one, so two adjacent bullets are
        never merged. The same line is free to *open* a run, which is how a
        bullet with indented continuation lines is reported.
        """
        return bool(UnwrappedProseScanner.LIST_ITEM.match(stripped))

    @staticmethod
    def _ends_a_sentence(stripped: str) -> bool:
        """Return whether *stripped* ends a sentence cleanly.

        Markdown emphasis and code markers are stripped first, so a line
        ending ``**Positive:**`` or a backtick counts as terminated. This is
        what separates a genuine mid-sentence break from two complete
        sentences that merely happen to sit on separate lines — the latter is
        a layout preference, not the diff noise the convention exists to stop.
        """
        text = stripped.rstrip("*_`").rstrip()
        return bool(text) and text[-1] in UnwrappedProseScanner.TERMINATORS

    @staticmethod
    def _is_wrapped_run(run: list[str]) -> bool:
        """Return whether any line in *run* breaks mid-sentence.

        Every line but the last must terminate a sentence. If they all do, the
        run is a stack of complete sentences and is left alone.
        """
        return any(not UnwrappedProseScanner._ends_a_sentence(line) for line in run[:-1])

    @staticmethod
    def paragraph_runs(text: str) -> list[tuple[int, int]]:
        """Return ``(first_line, last_line)`` for every wrapped paragraph.

        Line numbers are 1-based and inclusive. A single-line paragraph is not
        a violation and is not returned, so an empty list means the text
        already obeys the convention.

        Fenced code is skipped by tracking the opening and closing delimiter
        rather than by inspecting each line, because code inside a fence is
        not prose and would otherwise be reported wholesale.

        Nested lists are skipped entirely. Inside one, a bullet and a
        same-indent trailing paragraph are indistinguishable by indentation
        alone, and joining them silently promotes a nested item to the top
        level and breaks the surrounding ordered list. That failure is real:
        it happened here in ``zolletta-metaskill-review`` Step 3.6. A
        conservative rule that stays correct beats a complete one that
        restructures a manifest.
        """
        lines = text.split("\n")
        runs: list[tuple[int, int]] = []
        i = UnwrappedProseScanner._body_start(lines)
        total = len(lines)
        # pragma: no mutate start — equivalent: None and False are both falsy, and `not in_fence`
        # toggles them identically
        in_fence = False
        # pragma: no mutate end
        while i < total:
            stripped = lines[i].strip()
            if UnwrappedProseScanner.FENCE.match(stripped):
                in_fence = not in_fence
                i += 1
                continue
            if in_fence or UnwrappedProseScanner._is_block_boundary(stripped):
                i += 1
                continue
            start = i
            run = [stripped]
            i += 1
            while i < total:
                nxt = lines[i].strip()
                if UnwrappedProseScanner.FENCE.match(nxt):
                    break
                if (
                    in_fence
                    or UnwrappedProseScanner._is_block_boundary(nxt)
                    or UnwrappedProseScanner._starts_new_list_item(nxt)
                ):
                    break
                run.append(nxt)
                i += 1
            indented = bool(lines[start][:1].isspace())
            # pragma: no mutate start — `> 1` vs `>= 1` is equivalent: a one-line run has an empty
            # run[:-1], so _is_wrapped_run already returns False for it
            if not indented and len(run) > 1 and UnwrappedProseScanner._is_wrapped_run(run):
                # pragma: no mutate end
                runs.append((start + 1, i))
        return runs

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    @staticmethod
    def scan_text(path: str | Path, text: str) -> list[Finding]:
        """Return one finding per wrapped paragraph in *text*.

        Args:
            path: Path recorded on each finding, for reporting only.
            text: Markdown source to inspect.

        Returns:
            A list of :class:`Finding` objects, empty when every paragraph in
            *text* already sits on a single line.

        """
        return [
            Finding(
                file=str(path),
                line=first,
                category=UnwrappedProseScanner.CATEGORY,
                severity=UnwrappedProseScanner.SEVERITY,
                description=(
                    f"paragraph wraps across lines {first}-{last}; "
                    "join it into one line (no artificial line breaks)"
                ),
            )
            for first, last in UnwrappedProseScanner.paragraph_runs(text)
        ]

    @staticmethod
    def scan_file(path: Path) -> list[Finding]:
        """Return findings for one markdown file, or none if unreadable."""
        try:
            # pragma: no mutate start — carried from inline pragma (was ineffective inside a
            # multi-line statement)
            text = path.read_text(encoding="utf-8")
            # pragma: no mutate end
        except (OSError, UnicodeDecodeError):
            return []
        return UnwrappedProseScanner.scan_text(path, text)

    @staticmethod
    def scan_roots(roots: list[Path]) -> list[Finding]:
        """Return findings for every markdown file under *roots*.

        Git-ignored files are skipped inside a repository, so a cache or a
        virtualenv never contributes findings.
        """
        findings: list[Finding] = []
        seen: set[Path] = set()
        for root in roots:
            if not root.is_dir():
                continue
            for path in ProjectConfig.iter_files(root, UnwrappedProseScanner.EXTENSIONS):
                if path in seen:
                    continue
                seen.add(path)
                findings.extend(UnwrappedProseScanner.scan_file(path))
        return sorted(findings, key=lambda f: (f.file, f.line))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @staticmethod
    def is_enabled(settings: dict[str, Any]) -> bool:
        """Return whether ``documentation.check_unwrapped_prose`` is on.

        Opt-in, defaulting to :attr:`DEFAULT_ENABLED`: a documentation tree
        that predates the convention can carry a long backlog, and turning the
        check on before clearing it buries real drift findings in formatting
        noise.
        """
        return bool(
            ProjectConfig.setting(
                settings,
                "documentation.check_unwrapped_prose",
                UnwrappedProseScanner.DEFAULT_ENABLED,
            )
        )

    @staticmethod
    def resolve_roots(settings: dict[str, Any]) -> list[Path]:
        """Return the directories to scan, from ``documentation.dir``.

        Only the documentation root, matching every other documentor tool.
        The skill's own scope rule is explicit that markdown outside
        ``documentation.dir`` is out of scope and a finding against it is a
        false positive by definition — ``skills/`` holds subagent contracts,
        root files hold contributor material, and ``CHANGELOG.md`` is
        generated. Widening the scan to "find more markdown" is exactly what
        that rule forbids.
        """
        return [ProjectConfig.docs_dir(settings)]

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_json(roots: list[Path], scanned: int, findings: list[Finding]) -> None:
        """Print the JSON report."""
        print(
            json.dumps(
                {
                    "directories": [str(root) for root in roots],
                    "scanned": scanned,
                    "violation_count": len(findings),
                    "violations": [
                        {
                            "file": f.file,
                            "line": f.line,
                            "category": f.category,
                            "severity": f.severity,
                            "description": f.description,
                        }
                        for f in findings
                    ],
                },
                indent=2,
            )
        )

    @staticmethod
    def _emit_text(roots: list[Path], scanned: int, findings: list[Finding]) -> None:
        """Print the text report."""
        print("=" * 70)
        print("UNWRAPPED PROSE — VALIDATION REPORT")
        print("=" * 70)
        print(f"\nScanned {scanned} files under {', '.join(str(r) for r in roots)}")
        if findings:
            print(f"\n## Wrapped paragraphs ({len(findings)})\n")
            for f in findings:
                print(f"  {f.file}:{f.line}  {f.description}")
            print(
                "\n  Fix: join each paragraph onto one line. This is a formatting "
                "rule, not a wording one — the text renders identically either way."
            )
        else:
            print("\n## Wrapped paragraphs: none")
        print()
        print("Result: violations found (report-only mode)" if findings else "Result: all clear")

    @staticmethod
    def main() -> int:
        """Entry point for the unwrapped prose scanner CLI."""
        # pragma: no mutate start — help text is not a tested contract
        parser = argparse.ArgumentParser(
            description="Flag markdown paragraphs hard-wrapped across lines. Roots "
            "come from .zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON instead of text")
        # pragma: no mutate end
        args = parser.parse_args()

        settings = ProjectConfig.load_settings(UnwrappedProseScanner.DEFAULT_SETTINGS_PATH)
        if not UnwrappedProseScanner.is_enabled(settings):
            ProjectConfig.emit_skipped(args.json, "check_unwrapped_prose disabled in settings.json")
            return 0

        roots = [root for root in UnwrappedProseScanner.resolve_roots(settings) if root.is_dir()]
        if not roots:
            print(
                "Error: no configured documentation directory exists on disk "
                f"({', '.join(str(r) for r in UnwrappedProseScanner.resolve_roots(settings))})",
                file=sys.stderr,
            )
            return 1

        scanned = sum(
            len(ProjectConfig.iter_files(root, UnwrappedProseScanner.EXTENSIONS)) for root in roots
        )
        findings = UnwrappedProseScanner.scan_roots(roots)
        if args.json:
            UnwrappedProseScanner._emit_json(roots, scanned, findings)
        else:
            UnwrappedProseScanner._emit_text(roots, scanned, findings)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(UnwrappedProseScanner.main())
