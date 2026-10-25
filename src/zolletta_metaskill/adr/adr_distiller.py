"""Read, write, and update the adr-distilled.md file."""

from __future__ import annotations

import re
from pathlib import Path


class ADRDistiller:
    """Parse, write, and update the adr-distilled.md file.

    The distilled file lives in the ADR directory and contains one-line
    directives extracted from Accepted ADRs. Category headings (``## ...``)
    added by the agent are preserved across refreshes by updating
    individual directive lines in-place rather than rewriting the whole file.
    """

    _DISTILLED_FILENAME = "adr-distilled.md"
    _DIRECTIVE_RE = re.compile(r"^-\s+\[(ADR-\d+)\]\(")
    _LEAD_IN_RE = re.compile(r"^-\s+\[(ADR-\d+)\]\([^)]+\)\s+(.+?):$")

    @staticmethod
    def filename() -> str:
        """Return the distilled file filename."""
        return ADRDistiller._DISTILLED_FILENAME

    @staticmethod
    def parse_directives(content: str | None) -> dict[str, str]:
        """Parse existing distilled directives into a dict.

        Maps ADR number (e.g. ``"ADR-001"``) to the full directive line.
        This preserves agent-refined directives that are not stale.

        Only lines matching ``- [ADR-NNN](path) text`` are parsed.
        Category headings (``## ...``) are not tracked — they are preserved
        by keeping the existing file structure and only replacing/updating
        individual directive lines.

        """
        if content is None:
            return {}
        directives: dict[str, str] = {}
        for line in content.splitlines():
            match = ADRDistiller._DIRECTIVE_RE.match(line)
            if match:
                key = match.group(1)
                directives[key] = line
        return directives

    @staticmethod
    def is_lead_in(directive_line: str) -> bool:
        """Return True when a directive line ends in a colon lead-in."""
        return ADRDistiller._LEAD_IN_RE.match(directive_line.rstrip("\n")) is not None

    @staticmethod
    def find_lead_ins(directive_lines: list[str]) -> list[str]:
        """Return the ADR numbers whose directive text ends in a colon.

        A directive that ends in ``:`` is a lead-in, not a decision — the ADR
        opened its Decision section with "we adopt the following:" and put the
        rule in the list beneath it. ``docs/explanation/documentation/adr.md``
        tells authors to state the complete rule on the first line, and
        ADR-0006 records the dependency as a known risk whose mitigation is
        hand-refinement. This surfaces the case where that refinement did not
        happen, including a stub carried over from an earlier run: the mtime
        cache preserves whatever is on disk, so an unreffined directive is
        otherwise indistinguishable from a good one.

        Reported, never repaired. Rewriting the extraction would change the
        output of a published skill to tolerate a mistake the documentation
        tells authors not to make.

        Returns:
            ADR numbers in the order their directives appear, deduplicated.

        """
        keys: list[str] = []
        for line in directive_lines:
            match = ADRDistiller._LEAD_IN_RE.match(line.rstrip("\n"))
            if match and match.group(1) not in keys:
                keys.append(match.group(1))
        return keys

    @staticmethod
    def update_in_place(
        distilled_path: Path,
        existing_content: str,
        new_directives: dict[str, str],
        removed_keys: list[str],
    ) -> None:
        """Update individual directive lines in the existing file.

        Preserves category headings and other structure by only replacing
        directive lines that are stale/new and removing lines for removed ADRs.
        """
        removed_set = set(removed_keys)
        lines = existing_content.splitlines(keepends=True)
        result_lines: list[str] = []

        for line in lines:
            # pragma: no mutate start — rstrip arg irrelevant: prefix-anchored regex
            match = ADRDistiller._DIRECTIVE_RE.match(line.rstrip("\n"))
            # pragma: no mutate end
            if match:
                key = match.group(1)
                if key in removed_set:
                    continue  # Skip removed directive
                if key in new_directives:
                    # Replace with new directive (preserve trailing newline)
                    newline = "\n" if line.endswith("\n") else ""
                    result_lines.append(new_directives[key] + newline)
                else:
                    result_lines.append(line)
            else:
                result_lines.append(line)

        # pragma: no mutate start — file-writing side effect
        distilled_path.write_text("".join(result_lines), encoding="utf-8")
        # pragma: no mutate end

    @staticmethod
    def write(distilled_path: Path, directives: list[str]) -> None:
        """Write the distilled directives file with header."""
        distilled_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "---\n"
            "audience: ai\n"
            "status: generated\n"
            'description: "Auto-generated architectural directives distilled from Accepted ADRs."\n'
            "---\n\n"
            "# adr-distilled.md — Architectural Directives\n\n"
            "> Auto-generated from the project's ADRs by the adr-distiller.\n"
            "> Do not edit directly — edit the source ADRs and re-run "
            "`/zolletta-metaskill adr-distiller` or `/zolletta-metaskill review`.\n"
            "> Each directive links to its source ADR for full context. "
            "Only Accepted decisions are included.\n\n"
        )
        body = "\n".join(directives) + "\n"
        # pragma: no mutate start — file-writing side effect
        distilled_path.write_text(header + body, encoding="utf-8")
        # pragma: no mutate end

    @staticmethod
    def write_placeholder(distilled_path: Path) -> None:
        """Write the placeholder when no ADRs are found."""
        distilled_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            "audience: ai\n"
            "status: generated\n"
            'description: "Auto-generated placeholder written when no Accepted ADRs are found."\n'
            "---\n\n"
            "# adr-distilled.md — Architectural Directives\n\n"
            "No Architecture Decision Records (ADRs) were found in this "
            "project's documentation.\n\n"
            "ADRs capture the context, decision, and consequences of "
            "significant architectural choices.\n"
            "See https://adr.github.io/ for guidance on the ADR format.\n\n"
            "To start using ADRs:\n"
            "1. Create an `adr/` directory under your documentation folder\n"
            "2. Write your first ADR following the format described in the "
            "project's documentation standards\n"
            "3. Re-run `/zolletta-metaskill setup` to detect and distill them\n"
        )
        # pragma: no mutate start — file-writing side effect
        distilled_path.write_text(content, encoding="utf-8")
        # pragma: no mutate end
