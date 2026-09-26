#!/usr/bin/env python3
"""Report survived mutants from a completed ``mutmut run``.

Wraps two mutmut CLI calls — ``mutmut results`` (per-mutant status lines,
``    <module>.x_<func>__mutmut_<n>: <status>``) and ``mutmut show <name>``
(``# <name>: <status>`` followed by a unified diff) — and merges them into a
deterministic survived-mutant report for the ``python-testing-style`` skill.
Survivors are mutants the existing test suite did not kill; each one is a
candidate coverage/verification gap.

Everything is read from ``.zolletta-metaskill/settings.json`` (fixed location,
standard script contract):

- ``python.tools.mutmut.available`` — false/absent → ``Result: SKIPPED``
- ``python.testing.check_mutation_testing`` — false → ``Result: SKIPPED``
- ``python.testing.mutation_score_threshold`` — PASS/FAIL threshold (default 80)
- ``python.testing.mutation_max_mutants`` — cap on detailed survivors (default 50)
- ``python.paths.source`` — filters reported survivors to configured roots

The project root is the cwd where ``mutmut run`` was executed — mutmut's
``mutants/`` result cache resolves relative to it. ``mutmut`` itself is
invoked as a bare command; container/uv wrapping belongs to the skill level
(``docker compose exec <c> python3 ...``, ``uv run python3 ...``).

The mutation score is ``killed / evaluated`` where ``evaluated`` counts every
mutant with a definitive status (``not checked``, ``skipped``, and
``check was interrupted by user`` are excluded). Timeout mutants appear in
the counts table only; survived and ``no tests`` mutants are detailed.

Usage:
    python3 mutmut_survived_reporter.py [--json]

Options:
    --json             Output as JSON instead of text

Exit code: 0 always (report-only); 1 only when the mutmut invocation fails.

"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.project_config import ProjectConfig


class MutmutSurvivedReporter:
    """Extract survived-mutant findings from mutmut's CLI output."""

    SURVIVOR_STATUSES = {"survived", "no tests"}
    UNCHECKED_STATUSES = {"not checked", "skipped", "check was interrupted by user"}

    _CLASS_NAME_SEPARATOR = "ǁ"
    _RESULT_LINE = re.compile(r"^\s+(?P<name>\S+):\s+(?P<status>[a-z ]+?)\s*$")
    _DIFF_FILE = re.compile(r"^---\s+(?P<path>\S+)")
    _HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,\d+)? @@")

    # ------------------------------------------------------------------
    # mutmut invocation
    # ------------------------------------------------------------------

    @staticmethod
    def _run_mutmut(arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
        """Run ``mutmut <arguments>``; ``None`` when the process cannot run."""
        try:
            return subprocess.run(
                ["mutmut", *arguments],
                capture_output=True,
                text=True,
                timeout=600,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    @staticmethod
    def _results_stdout() -> str | None:
        """Return ``mutmut results`` stdout, or ``None`` when mutmut fails.

        ``--all`` is preferred so killed mutants are counted too (needed for
        the mutation score); its spelling drifted across 3.x releases, so the
        flag forms are tried in order before giving up.
        """
        for arguments in (
            ["results", "--all", "true"],
            ["results", "--all"],
            ["results"],
        ):
            proc = MutmutSurvivedReporter._run_mutmut(arguments)
            if proc is None:
                return None
            if proc.returncode == 0:
                return proc.stdout
        return None

    @staticmethod
    def _show_stdout(name: str) -> str | None:
        """Return ``mutmut show <name>`` stdout, or ``None`` when it fails."""
        proc = MutmutSurvivedReporter._run_mutmut(["show", name])
        if proc is None or proc.returncode != 0:
            return None
        return proc.stdout

    # ------------------------------------------------------------------
    # Output parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_results(stdout: str) -> dict[str, str]:
        """Map mutant name → status from ``mutmut results`` output."""
        statuses: dict[str, str] = {}
        for line in stdout.splitlines():
            match = MutmutSurvivedReporter._RESULT_LINE.match(line)
            if match:
                statuses[match.group("name")] = match.group("status")
        return statuses

    @staticmethod
    def _split_mutant_name(name: str) -> tuple[str, str | None]:
        """Return ``(dotted module, function/method name)`` from a mutant name.

        mutmut 3.x names function mutants ``<module>.x_<func>__mutmut_<n>``
        and method mutants ``<module>.xǁ<Class>ǁ<method>__mutmut_<n>``.
        """
        base, _, _ = name.partition("__mutmut_")
        module, _, leaf = base.rpartition(".")
        if leaf.startswith(f"x{MutmutSurvivedReporter._CLASS_NAME_SEPARATOR}"):
            # xǁClassǁmethod → the method name is the last segment
            return module, leaf.rsplit(MutmutSurvivedReporter._CLASS_NAME_SEPARATOR, 1)[-1]
        if leaf.startswith("x_"):
            return module, leaf[2:]
        return module, leaf or None

    @staticmethod
    def _resolve_file(module: str, source_dirs: list[str]) -> str | None:
        """Map a dotted module to a file path under the source roots.

        mutmut derives module names from the source path (``src/`` prefix
        stripped, ``/`` → ``.``). Returns the resolved path, or ``None`` when
        the file exists but is outside every configured source root.
        """
        rel = module.replace(".", "/") + ".py"
        for root in source_dirs:
            candidate = Path(root) / rel
            if candidate.is_file():
                return str(candidate)
        if Path(rel).is_file():
            return None
        return str(Path(source_dirs[0]) / rel) if source_dirs else rel

    @staticmethod
    def _under_source_root(path: str, source_dirs: list[str]) -> bool:
        """Return True when *path* sits under one of *source_dirs*."""
        if not source_dirs:
            return True
        target = Path(path)
        for root in source_dirs:
            try:
                target.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _parse_show(stdout: str) -> tuple[str | None, int | None, str | None, str]:
        """Extract ``(file, line, mutation, diff)`` from ``mutmut show`` output.

        The output is a ``# <name>: <status>`` header followed by a unified
        diff. *mutation* is the first removed/added line pair, e.g.
        ``if age >= 18: → if age > 18:``.
        """
        lines = stdout.splitlines()
        diff_lines = lines[1:] if lines and lines[0].startswith("# ") else lines
        file: str | None = None
        line: int | None = None
        removed: str | None = None
        added: str | None = None
        for raw in diff_lines:
            if file is None:
                match = MutmutSurvivedReporter._DIFF_FILE.match(raw)
                if match:
                    file = match.group("path")
                    continue
            if line is None:
                match = MutmutSurvivedReporter._HUNK_HEADER.match(raw)
                if match:
                    line = int(match.group("start"))
                    continue
            if removed is None and raw.startswith("-") and not raw.startswith("---"):
                removed = raw[1:].strip()
            elif (
                removed is not None
                and added is None
                and raw.startswith("+")
                and not raw.startswith("+++")
            ):
                added = raw[1:].strip()
                break
        mutation = f"{removed} → {added}" if removed is not None and added is not None else None
        return file, line, mutation, "\n".join(diff_lines)

    # ------------------------------------------------------------------
    # Report assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _survivor_entry(
        name: str, status: str, source_dirs: list[str]
    ) -> dict[str, Any] | None:
        """Build one survivor record; ``None`` when the mutant is out of scope."""
        module, function = MutmutSurvivedReporter._split_mutant_name(name)
        file = MutmutSurvivedReporter._resolve_file(module, source_dirs)
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "file": file,
            "line": None,
            "function": function,
            "mutation": None,
            "diff": None,
        }
        show_stdout = MutmutSurvivedReporter._show_stdout(name)
        if show_stdout is not None:
            diff_file, line, mutation, diff = MutmutSurvivedReporter._parse_show(show_stdout)
            if diff_file is not None:
                file = diff_file
            entry["line"] = line
            entry["mutation"] = mutation
            entry["diff"] = diff
        if (
            file is not None
            and Path(file).is_file()
            and not MutmutSurvivedReporter._under_source_root(file, source_dirs)
        ):
            return None
        entry["file"] = file
        return entry

    @staticmethod
    def _report(
        statuses: dict[str, str],
        threshold: int,
        max_mutants: int,
        source_dirs: list[str],
    ) -> dict[str, Any]:
        """Assemble the report dict from parsed ``mutmut results`` statuses."""
        counts: dict[str, int] = {}
        for status in statuses.values():
            counts[status] = counts.get(status, 0) + 1

        killed = counts.get("killed", 0)
        evaluated = sum(
            count
            for status, count in counts.items()
            if status not in MutmutSurvivedReporter.UNCHECKED_STATUSES
        )
        score = round(100.0 * killed / evaluated, 1) if evaluated else 100.0

        survivor_names = sorted(
            name for name, status in statuses.items()
            if status in MutmutSurvivedReporter.SURVIVOR_STATUSES
        )
        survivors: list[dict[str, Any]] = []
        for name in survivor_names[:max_mutants]:
            entry = MutmutSurvivedReporter._survivor_entry(name, statuses[name], source_dirs)
            if entry is not None:
                survivors.append(entry)

        return {
            "skipped": False,
            "counts": counts,
            "total": len(statuses),
            "mutation_score": score,
            "threshold": threshold,
            "status": "PASS" if score >= threshold else "FAIL",
            "survivor_count": len(survivor_names),
            "survivors_shown": len(survivors),
            "survivors_capped": len(survivor_names) > max_mutants,
            "survivors": survivors,
        }

    @staticmethod
    def _print_text(report: dict[str, Any]) -> None:
        """Print the report in the deterministic text format."""
        print("MUTMUT SURVIVED MUTANTS — REPORT")
        print("=" * 32)
        print()
        print("| Status   | Count |")
        print("|----------|-------|")
        for status in sorted(report["counts"]):
            print(f"| {status:<8} | {report['counts'][status]:>5} |")
        print()
        score = report["mutation_score"]
        print(
            f"Mutation score: {score:g}% (threshold: {report['threshold']}%)"
            f" — {report['status']}"
        )
        print()
        shown = report["survivors"]
        total = report["survivor_count"]
        if not shown:
            print("No survived mutants." if total == 0 else "No in-scope survived mutants.")
            return
        header = f"Survived mutants ({len(shown)} of {total} shown):"
        print(header)
        print()
        print("| File | Line | Mutant | Status | Mutation |")
        print("|------|------|--------|--------|----------|")
        for survivor in shown:
            file = survivor["file"] or "-"
            line = survivor["line"] if survivor["line"] is not None else "-"
            mutation = survivor["mutation"] or "-"
            print(
                f"| {file} | {line} | {survivor['name']} "
                f"| {survivor['status']} | {mutation} |"
            )
        diffs = [s for s in shown if s["diff"]]
        if diffs:
            print()
            print("Diffs:")
            print()
            for survivor in diffs:
                print(f"### {survivor['name']}")
                print()
                print("```diff")
                print(survivor["diff"])
                print("```")
                print()

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def main() -> int:
        """Entry point for the survived-mutants reporter CLI."""
        parser = argparse.ArgumentParser(
            description="Report survived mutants from a completed mutmut run. "
            "Reads python.tools.mutmut / python.testing.mutation_* from settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        if ProjectConfig.setting(settings, "python.tools.mutmut.available", False) is not True:
            ProjectConfig.emit_skipped(args.json, "python.tools.mutmut is not available")
            return 0
        if (
            ProjectConfig.setting(settings, "python.testing.check_mutation_testing", True)
            is False
        ):
            ProjectConfig.emit_skipped(
                args.json, "python.testing.check_mutation_testing is disabled in settings.json"
            )
            return 0

        threshold = ProjectConfig.setting(
            settings, "python.testing.mutation_score_threshold", 80
        )
        max_mutants = ProjectConfig.setting(
            settings, "python.testing.mutation_max_mutants", 50
        )
        source_dirs = ProjectConfig.source_dirs(settings, "python")

        stdout = MutmutSurvivedReporter._results_stdout()
        if stdout is None:
            print(
                "Error: 'mutmut results' failed — is mutmut installed and has "
                "'mutmut run' completed?",
                file=sys.stderr,
            )
            return 1

        report = MutmutSurvivedReporter._report(
            MutmutSurvivedReporter._parse_results(stdout),
            threshold,
            max_mutants,
            source_dirs,
        )
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            MutmutSurvivedReporter._print_text(report)
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(MutmutSurvivedReporter.main())
