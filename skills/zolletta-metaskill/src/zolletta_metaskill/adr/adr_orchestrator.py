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
from zolletta_metaskill.adr.structs.distill_diff import DistillDiff
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
        5. Removes directives for removed, demoted, or orphaned ADRs.
        6. Writes the updated ``adr-distilled.md`` and cache.

        Returns:
            A :class:`DistillReport` with lists of new, stale, removed, and
            dropped ADR numbers, the numbers of directives that look like a
            lead-in, and whether any ADRs exist.

        """
        records = ADRDiscovery.find_files(self.docs_dir, self.adrs_path)
        report = DistillReport()
        report.has_adrs = any(self._is_accepted(r.status) for r in records)

        # Load cache
        cache = ADRCache(self.cache_path)
        old_cache = cache.load()

        # Build new cache and classify changes
        current_keys, new_directives, new_cache = self._classify_records(records, old_cache, report)

        # Detect removed ADRs and drop them from the cache
        for key in old_cache:
            if key not in current_keys:
                report.removed.append(key)
        for key in report.removed:
            new_cache.pop(key, None)  # pragma: no mutate — new_cache holds only current records

        # Read existing distilled file (lives in the ADR directory, not docs root)
        distilled_path = self._distilled_path()
        existing_content = self._read_existing(distilled_path)

        # Build the final list of directive lines (sorted by ADR number)
        if existing_content is not None:
            existing_directives = ADRDistiller.parse_directives(existing_content)
        else:
            existing_directives = {}

        # Self-heal: regenerate any Accepted ADR whose directive is absent
        # from the file — covers a deleted/moved distilled file, manually
        # removed lines, and cache/directory migration divergence.
        for record in records:
            key = ADRCache.key(record)
            if (
                self._is_accepted(record.status)
                and key not in new_directives
                and key not in existing_directives
            ):
                directive = self.distill_adr(record)
                # distill_adr returns None only for non-Accepted records,
                # and this loop already filters for them
                if directive is not None:  # pragma: no branch
                    new_directives[key] = directive

        accepted_keys = {ADRCache.key(r) for r in records if self._is_accepted(r.status)}
        merged = self._merge_directives(existing_directives, new_directives, accepted_keys)
        report.dropped = [k for k in existing_directives if k not in merged]

        # Sort by ADR number for deterministic output
        sorted_keys = sorted(merged, key=lambda k: int(k.split("-")[1]))
        directive_lines = [merged[k] for k in sorted_keys]

        # Scanned over the merged set, not just this run's output, so a stub
        # preserved by the cache is still reported rather than passing as good.
        report.lead_ins = ADRDistiller.find_lead_ins(directive_lines)

        self._write_distilled(
            distilled_path,
            existing_content,
            DistillDiff(
                existing_directives=existing_directives,
                new_directives=new_directives,
                directive_lines=tuple(directive_lines),
                report=report,
            ),
        )

        # Save cache
        cache.save(new_cache)

        return report

    def _classify_records(
        self,
        records: list[ADRRecord],
        old_cache: dict[str, dict[str, object]],
        report: DistillReport,
    ) -> tuple[set[str], dict[str, str], dict[str, dict[str, object]]]:
        """Classify records as new/stale, distill them, and build the new cache."""
        current_keys: set[str] = set()
        new_directives: dict[str, str] = {}
        new_cache: dict[str, dict[str, object]] = {}

        for record in records:
            key = ADRCache.key(record)
            current_keys.add(key)
            cached = old_cache.get(key)
            # pragma: no mutate start — any non-"accepted" default gives the same result
            was_accepted = cached is not None and self._is_accepted(str(cached.get("status", "")))
            # pragma: no mutate end
            is_accepted = self._is_accepted(record.status)

            if cached is None:
                # New ADR
                report.new.append(key)
                directive = self.distill_adr(record)
                if directive is not None:
                    new_directives[key] = directive
                refined = directive is None or not ADRDistiller.is_lead_in(directive)
            elif (
                cached.get("mtime") != record.mtime
                or was_accepted != is_accepted
                or cached.get("refined") is False
            ):
                # Stale (mtime changed, status changed, or cached as unrefined)
                report.stale.append(key)
                directive = self.distill_adr(record)
                if directive is not None:
                    new_directives[key] = directive
                refined = directive is None or not ADRDistiller.is_lead_in(directive)
            else:
                # Up-to-date — preserve existing directive and its flag
                # pragma: no mutate start — this branch needs cached["refined"] is not False
                refined = bool(cached.get("refined", True))
                # pragma: no mutate end

            # Update cache entry
            new_cache[key] = {
                "path": str(record.file_path.relative_to(self.docs_dir).as_posix()),
                "mtime": record.mtime,
                "status": record.status,
                "refined": refined,
            }

        return current_keys, new_directives, new_cache

    def _distilled_path(self) -> Path:
        """Resolve the adr-distilled.md path inside the ADR directory."""
        adr_dir = self.docs_dir / self.adrs_path if self.adrs_path else self.docs_dir
        return adr_dir / ADRDistiller.filename()

    @staticmethod
    def _read_existing(distilled_path: Path) -> str | None:
        """Read the existing distilled file, or None if absent/unreadable."""
        existing_content: str | None = None
        if distilled_path.exists():
            with contextlib.suppress(OSError):
                existing_content = distilled_path.read_text(encoding="utf-8")  # pragma: no mutate
        return existing_content

    @staticmethod
    def _merge_directives(
        existing_directives: dict[str, str],
        new_directives: dict[str, str],
        accepted_keys: set[str],
    ) -> dict[str, str]:
        """Merge existing and freshly distilled directives.

        An existing directive is kept only while its ADR is an Accepted
        record — file removals, status demotions, and orphaned lines whose
        ADR is no longer in the corpus all drop out here.
        """
        merged: dict[str, str] = {}
        for key, directive in existing_directives.items():
            if key in accepted_keys:
                # pragma: no mutate start — the loop below overwrites this key with the same value
                merged[key] = new_directives.get(key, directive)
                # pragma: no mutate end
        for key, directive in new_directives.items():
            merged[key] = directive
        return merged

    @staticmethod
    def _write_distilled(
        distilled_path: Path,
        existing_content: str | None,
        diff: DistillDiff,
    ) -> None:
        """Write the distilled file — in-place when possible, else full rewrite."""
        report = diff.report
        existing_directives = diff.existing_directives
        new_directives = diff.new_directives
        directive_lines = list(diff.directive_lines)
        # pragma: no mutate start — has_adrs implies non-empty directive_lines
        if not (report.has_adrs and directive_lines):
            ADRDistiller.write_placeholder(distilled_path)
            return
        # pragma: no mutate end

        # Check if we can do an in-place update (preserve category headings).
        # This works when the existing file has directives (not a placeholder)
        # and every new directive replaces an existing line — the in-place
        # updater doesn't support inserting lines (brand-new ADRs, or stale
        # ADRs whose directive was previously absent from the file).
        # pragma: no mutate start — parse_directives(None) is {}, and a directive-less file also
        # leaves existing_directives empty, so the or-variant resolves identically downstream
        existing_has_directives = bool(
            existing_content is not None and ADRDistiller.parse_directives(existing_content)
        )
        # pragma: no mutate end
        can_update_in_place = existing_has_directives and all(
            key in existing_directives for key in new_directives
        )
        if can_update_in_place and existing_content is not None:
            ADRDistiller.update_in_place(
                distilled_path,
                existing_content,
                new_directives,
                report.dropped,
            )
        else:
            ADRDistiller.write(distilled_path, directive_lines)

    @staticmethod
    def _is_accepted(status: str) -> bool:
        """Check whether an ADR status counts as Accepted.

        A prefix match tolerates qualified statuses such as
        ``Accepted (amended 2026-09-26)`` that would otherwise be silently
        excluded by an exact comparison.
        """
        return status.strip().lower().startswith("accepted")

    def distill_adr(self, record: ADRRecord) -> str | None:
        """Mechanically distill an ADR into a directive line.

        Returns:
            A directive line like
            ``- [ADR-001](adr/0001-use-postgres.md) Use PostgreSQL.``
            or ``None`` if the ADR is not Accepted (excluded).

        """
        if not self._is_accepted(record.status):
            return None

        adr_dir = self.docs_dir / self.adrs_path if self.adrs_path else self.docs_dir
        link_path = record.file_path.relative_to(adr_dir).as_posix()
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
        if last_space > 0:  # pragma: no mutate — collapsed text never starts with " "
            return truncated[:last_space] + "..."
        return truncated + "..."

    # --- CLI helpers ---

    @staticmethod
    def run(argv: list[str] | None = None) -> int:
        """Parse args, run the distiller, and print the report.

        Returns the CLI exit code (0 on success, 1 on error).
        Delegates to ADRClient for argument parsing and output formatting.
        """
        from zolletta_metaskill.adr.adr_client import ADRClient

        return ADRClient.run(argv)

    @staticmethod
    def main() -> int:
        """Entry point for the ADR distiller CLI."""
        from zolletta_metaskill.adr.adr_client import ADRClient

        return ADRClient.run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(ADROrchestrator.main())
