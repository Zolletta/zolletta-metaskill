"""ADR Orchestrator — coordinate ADR distillation end-to-end.

Finds Architecture Decision Records in the project's documentation folder,
extracts the Decision section from each Accepted ADR, and produces a
one-line directive in ``adr-distilled.md`` with a markdown link to the
source ADR. An mtime cache tracks changes so only new/stale/removed ADRs
are re-distilled on subsequent runs.

Only ADRs with Status ``Accepted`` are included. Proposed, Deprecated,
and Superseded ADRs are excluded — the distilled file represents the
rules in force.

Implements the declarative architectural governance approach described in
https://www.infoq.com/articles/architectural-governance-ai-speed/ (InfoQ, 2026).

"""

from __future__ import annotations

import contextlib
import re
import sys
from pathlib import Path

from zolletta_metaskill.adr.adr_cache import ADRCache
from zolletta_metaskill.adr.adr_discovery import ADRDiscovery
from zolletta_metaskill.adr.adr_distiller import ADRDistiller
from zolletta_metaskill.adr.structs.adr_record import ADRRecord
from zolletta_metaskill.adr.structs.distill_report import DistillReport


class ADROrchestrator:
    """Orchestrate ADR distillation: discover, distill, cache, and write.

    This class ties together ADR discovery, single-ADR distillation,
    mtime caching, and distilled-file management into one refresh flow.
    It also provides static helpers for CLI argument parsing and output
    formatting so the CLI entry point stays a thin wrapper.
    """

    _MAX_DECISION_LEN = 200

    def __init__(self, docs_dir: Path, adrs_path: str | None, cache_path: Path) -> None:
        self.docs_dir = docs_dir
        self.adrs_path = adrs_path
        self.cache_path = cache_path

    def refresh(self) -> DistillReport:
        """Refresh ``adr-distilled.md`` based on current ADR files.

        This is the main entry point for the distiller. It:
        1. Finds all ADR files in the configured location.
        2. Compares against the mtime cache to classify as new/stale/removed.
        3. Re-distills new and stale ADRs mechanically (Accepted only).
        4. Preserves up-to-date directives (including agent refinements).
        5. Removes directives for removed ADRs.
        6. Writes the updated ``adr-distilled.md`` and cache.

        Returns:
            A :class:`DistillReport` with lists of new, stale, and removed
            ADR numbers, and whether any ADRs exist.

        """
        records = ADRDiscovery.find_files(self.docs_dir, self.adrs_path)
        report = DistillReport()
        report.has_adrs = any(r.status.lower() == "accepted" for r in records)

        # Load cache
        cache = ADRCache(self.cache_path)
        old_cache = cache.load()

        # Build new cache and classify changes
        current_keys: set[str] = set()
        new_directives: dict[str, str] = {}
        new_cache: dict[str, dict[str, object]] = {}

        for record in records:
            key = ADRCache.key(record)
            current_keys.add(key)
            cached = old_cache.get(key)
            was_accepted = cached is not None and cached.get("status", "").lower() == "accepted"
            is_accepted = record.status.lower() == "accepted"

            if cached is None:
                # New ADR
                report.new.append(key)
                directive = self.distill_adr(record)
                if directive is not None:
                    new_directives[key] = directive
            elif cached.get("mtime") != record.mtime or was_accepted != is_accepted:
                # Stale (mtime changed or status changed)
                report.stale.append(key)
                directive = self.distill_adr(record)
                if directive is not None:
                    new_directives[key] = directive
            # else: up-to-date — preserve existing directive

            # Update cache entry
            new_cache[key] = {
                "path": str(record.file_path.relative_to(self.docs_dir).as_posix()),
                "mtime": record.mtime,
                "status": record.status,
            }

        # Detect removed ADRs
        for key in old_cache:
            if key not in current_keys:
                report.removed.append(key)

        # Remove deleted entries from cache
        for key in report.removed:
            new_cache.pop(key, None)

        # Read existing distilled file (lives in the ADR directory, not docs root)
        adr_dir = self.docs_dir / self.adrs_path if self.adrs_path else self.docs_dir
        distilled_path = adr_dir / ADRDistiller.filename()
        existing_content: str | None = None
        if distilled_path.exists():
            with contextlib.suppress(OSError):
                existing_content = distilled_path.read_text(encoding="utf-8")

        # Build the final list of directive lines (sorted by ADR number)
        if existing_content is not None:
            existing_directives = ADRDistiller.parse_directives(existing_content)
        else:
            existing_directives = {}

        # Merge: start with existing, apply new/stale, remove removed
        merged: dict[str, str] = {}
        for key, directive in existing_directives.items():
            if key in report.removed:
                continue
            merged[key] = new_directives.get(key, directive)

        # Add brand-new directives (not in existing file)
        for key, directive in new_directives.items():
            if key not in merged:
                merged[key] = directive

        # Sort by ADR number for deterministic output
        sorted_keys = sorted(merged, key=lambda k: int(k.split("-")[1]))
        directive_lines = [merged[k] for k in sorted_keys]

        # Write distilled file
        if report.has_adrs and directive_lines:
            # Check if we can do an in-place update (preserve category headings).
            # This works when the existing file has directives (not a placeholder)
            # and no brand-new ADRs are being added (those need to be inserted, which
            # the in-place updater doesn't support — it only replaces and removes).
            existing_has_directives = bool(
                existing_content is not None and ADRDistiller.parse_directives(existing_content)
            )
            can_update_in_place = existing_has_directives and not report.new
            if can_update_in_place and existing_content is not None:
                ADRDistiller.update_in_place(
                    distilled_path, existing_content, new_directives, report.removed
                )
            else:
                ADRDistiller.write(distilled_path, directive_lines)
        else:
            ADRDistiller.write_placeholder(distilled_path)

        # Save cache
        cache.save(new_cache)

        return report

    def distill_adr(self, record: ADRRecord) -> str | None:
        """Mechanically distill an ADR into a directive line.

        Returns:
            A directive line like
            ``- [ADR-001](adr/0001-use-postgres.md) Use PostgreSQL.``
            or ``None`` if the ADR is not Accepted (excluded).

        """
        if record.status.lower() != "accepted":
            return None

        link_path = record.file_path.relative_to(self.docs_dir).as_posix()
        decision = self._truncate_decision(record.decision_text)
        return f"- [ADR-{record.number}]({link_path}) {decision}"

    @staticmethod
    def _truncate_decision(text: str) -> str:
        """Truncate decision text to the first sentence or ~200 chars.

        Strips markdown formatting and collapses whitespace.
        """
        # Strip markdown: bold, italic, code, links
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        cleaned = re.sub(r"\*(.+?)\*", r"\1", cleaned)
        cleaned = re.sub(r"`(.+?)`", r"\1", cleaned)
        cleaned = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", cleaned)
        # Collapse whitespace
        cleaned = " ".join(cleaned.split())

        if not cleaned:
            return ""

        # Truncate at first sentence boundary
        for i, char in enumerate(cleaned):
            if char in ".!?" and (i + 1 >= len(cleaned) or cleaned[i + 1].isspace()):
                return cleaned[: i + 1]

        # No sentence boundary — truncate at ~200 chars
        if len(cleaned) <= ADROrchestrator._MAX_DECISION_LEN:
            return cleaned
        # Try to break at a word boundary
        truncated = cleaned[: ADROrchestrator._MAX_DECISION_LEN]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space] + "..."
        return truncated + "..."

    # --- CLI helpers ---

    @staticmethod
    def run(argv: list[str] | None = None) -> int:
        """Parse args, run the distiller, and print the report.

        Returns the CLI exit code (0 on success, 1 on error).
        Delegates to ADRCLI for argument parsing and output formatting.
        """
        from zolletta_metaskill.adr.adr_cli import ADRCLI

        return ADRCLI.run(argv)


def main() -> int:
    """Entry point for the ADR distiller CLI."""
    from zolletta_metaskill.adr.adr_cli import ADRCLI

    return ADRCLI.run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
