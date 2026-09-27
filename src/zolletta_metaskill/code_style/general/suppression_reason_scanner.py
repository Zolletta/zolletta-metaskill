#!/usr/bin/env python3
"""Flag type-checker suppressions that lack an error code or a reason.

Deterministic half of the "suppress-with-reason" convention from Martin
Fowler's *Maintainability sensors for coding agents* ("Guidance for
self-correction"): when a deliberately broad type (``Any``, ``mixed``)
produces a checker diagnostic, suppressing it is an acceptable judgment
call only when the suppression carries the specific error code **and** a
reason explaining why the type is deliberately broad. Checking that the
code and the reason exist is mechanical — no judgment needed — so this
scanner runs in Phase A.

What it checks per language:

- **Python** — ``# type: ignore`` comments (real comments only, via
  ``tokenize`` — matches inside string literals are not suppressions).
  ``missing error code`` when no ``[<code>…]`` list follows (the ruff
  ``PGH003`` equivalent); ``missing reason`` when no free text follows on
  the same line and the immediately preceding line is not a ``#`` comment
  (the "reason on the line above" convention).
- **PHP** — ``@phpstan-ignore``, ``@phpstan-ignore-line``,
  ``@phpstan-ignore-next-line``, and ``@psalm-suppress`` annotations inside
  ``//``, ``/* */``, and ``/** */`` comments. ``missing identifier`` when
  the syntax slot exists but is empty (``@phpstan-ignore`` without a
  dotted identifier, ``@psalm-suppress`` without an issue type);
  ``missing reason`` when no free text follows — docblock continuations
  on subsequent ``*`` lines count as reason text.

Which files are scanned is driven entirely by
``.zolletta-metaskill/settings.json``:

- The project's language(s) are read from settings.json and mapped to
  file extensions via the engine registry; only extensions this scanner
  has patterns for (``.py``, ``.php``) are scanned. With no usable
  language the run reports SKIPPED.
- Scan roots come from settings: ``python.paths.source`` for Python,
  ``php.autoload.psr-4`` directories for PHP (``src`` when unconfigured).
- Files ignored by git are skipped; outside a git repository every
  matching file is a candidate.

Usage:
    python3 suppression_reason_scanner.py [--json]

Options:
    --json          Output as JSON instead of text.

Exit code: 0 on success (violations are report-only); 1 when no
           configured source directory exists on disk.

"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tokenize
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.project_config import ProjectConfig


class SuppressionReasonScanner:
    """Flag suppressions missing a checker code or a reason."""

    PY_EXT = ".py"
    PHP_EXT = ".php"
    SUPPORTED_EXTENSIONS = {PY_EXT, PHP_EXT}

    _PY_IGNORE = re.compile(
        r"type:\s*ignore\b(?:\s*\[(?P<codes>[^\]]*)\])?(?P<rest>.*)"
    )
    _PHP_ANNOTATION = re.compile(
        r"@(?P<anno>phpstan-ignore-next-line|phpstan-ignore-line"
        r"|phpstan-ignore|psalm-suppress)\b(?P<rest>.*)"
    )
    # PHPStan error identifiers are dotted (e.g. ``argument.type``);
    # Psalm issue types are single CamelCase tokens (e.g.
    # ``MixedReturnStatement``).
    _PHPSTAN_IDENTIFIER = re.compile(r"^\s*(?P<ident>[A-Za-z][\w-]*(?:\.[\w-]+)+)")
    _PSALM_IDENTIFIER = re.compile(r"^\s*(?P<ident>[A-Za-z][\w]*)")
    _COMMENT_CLOSE = re.compile(r"\*/\s*$")

    # ------------------------------------------------------------------
    # Per-language suppression extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _has_python_reason(rest: str, lines: list[str], lineno: int) -> bool:
        """Return True when the ``type: ignore`` carries a reason.

        A reason is free text after the ignore (a trailing ``#`` comment
        counts) or a comment on the line immediately above.
        """
        if rest.strip().lstrip("#").strip():
            return True
        if lineno >= 2:
            return lines[lineno - 2].lstrip().startswith("#")
        return False

    @staticmethod
    def _scan_python(path: Path) -> list[dict[str, Any]]:
        """Return violation records for ``type: ignore`` comments."""
        try:
            text = path.read_text(encoding="utf-8")
            tokens = tokenize.generate_tokens(io.StringIO(text).readline)
            comments = [
                (tok.start[0], tok.string) for tok in tokens if tok.type == tokenize.COMMENT
            ]
        except (
            OSError,
            UnicodeDecodeError,
            SyntaxError,
            IndentationError,
            tokenize.TokenError,
        ):
            print(f"Warning: could not tokenize '{path}'", file=sys.stderr)
            return []

        lines = text.splitlines()
        violations: list[dict[str, Any]] = []
        for lineno, comment in comments:
            match = SuppressionReasonScanner._PY_IGNORE.search(comment)
            if not match:
                continue
            missing: list[str] = []
            codes = match.group("codes")
            if codes is None or not codes.strip():
                missing.append("error code")
            if not SuppressionReasonScanner._has_python_reason(
                match.group("rest"), lines, lineno
            ):
                missing.append("reason")
            if missing:
                violations.append(
                    {
                        "line": lineno,
                        "suppression": "# type: ignore",
                        "missing": missing,
                        "line_text": lines[lineno - 1].strip(),
                    }
                )
        return violations

    @staticmethod
    def _docblock_reason(lines: list[str], lineno: int) -> bool:
        """Return True when a docblock continues with text after *lineno*.

        For annotations inside a multi-line ``/** */`` block, subsequent
        ``*``-prefixed lines until the closing ``*/`` count as the reason.
        """
        for raw in lines[lineno:]:
            stripped = raw.strip()
            if not stripped.startswith("*"):
                return False
            content = stripped.lstrip("*").strip()
            if content.rstrip("/").strip():
                return True
            if stripped.endswith("*/"):
                return False
        return False

    @staticmethod
    def _php_has_reason(rest: str, lines: list[str], lineno: int) -> bool:
        """Return True when the annotation carries a reason.

        A reason is free text after the annotation (and identifier, where
        the slot exists) on the same line — a closing ``*/`` is ignored —
        or continuation text on following ``*`` docblock lines.
        """
        if SuppressionReasonScanner._COMMENT_CLOSE.sub("", rest).strip():
            return True
        return SuppressionReasonScanner._docblock_reason(lines, lineno)

    @staticmethod
    def _scan_php(path: Path) -> list[dict[str, Any]]:
        """Return violation records for PHPStan/Psalm suppressions."""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            print(f"Warning: could not read '{path}'", file=sys.stderr)
            return []

        lines = text.splitlines()
        violations: list[dict[str, Any]] = []
        for lineno, raw in enumerate(lines, 1):
            for match in SuppressionReasonScanner._PHP_ANNOTATION.finditer(raw):
                anno = match.group("anno")
                rest = match.group("rest")
                missing = []
                if anno == "phpstan-ignore":
                    ident = SuppressionReasonScanner._PHPSTAN_IDENTIFIER.match(rest)
                    if ident:
                        rest = rest[ident.end() :]
                    else:
                        missing.append("identifier")
                elif anno == "psalm-suppress":
                    ident = SuppressionReasonScanner._PSALM_IDENTIFIER.match(rest)
                    if ident:
                        rest = rest[ident.end() :]
                    else:
                        missing.append("identifier")
                if not SuppressionReasonScanner._php_has_reason(rest, lines, lineno):
                    missing.append("reason")
                if missing:
                    violations.append(
                        {
                            "line": lineno,
                            "suppression": f"@{anno}",
                            "missing": missing,
                            "line_text": raw.strip(),
                        }
                    )
        return violations

    @staticmethod
    def scan_file(path: Path) -> list[dict[str, Any]]:
        """Dispatch *path* to the matching per-language scanner."""
        if path.suffix == SuppressionReasonScanner.PY_EXT:
            return SuppressionReasonScanner._scan_python(path)
        return SuppressionReasonScanner._scan_php(path)

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------

    @staticmethod
    def main() -> int:
        """Entry point for the suppression-reason scanner CLI."""
        parser = argparse.ArgumentParser(
            description="Flag type-checker suppressions missing an error code "
            "or a reason (language-agnostic). Scan roots come from "
            ".zolletta-metaskill/settings.json."
        )
        parser.add_argument("--json", action="store_true", help="Output as JSON")
        args = parser.parse_args()

        settings = ProjectConfig.load_settings()
        languages = ProjectConfig.configured_languages(settings)
        if not languages:
            ProjectConfig.ensure_engines()
            languages = set(EngineRegistry.available_languages())
        extensions = (
            ProjectConfig.extensions_for(languages)
            & SuppressionReasonScanner.SUPPORTED_EXTENSIONS
        )
        if not extensions:
            ProjectConfig.emit_skipped(
                args.json, "no python/php language configured in settings.json"
            )
            return 0

        roots = ProjectConfig.existing_roots(
            ProjectConfig.source_roots(settings, languages)
        )
        if not roots:
            print(
                "Error: no configured source directories exist on disk "
                f"({', '.join(str(r) for r in ProjectConfig.source_roots(settings, languages))})",
                file=sys.stderr,
            )
            return 1

        files: list[Path] = []
        for root in roots:
            files.extend(ProjectConfig.iter_files(root, extensions))

        violations: list[dict[str, Any]] = []
        for path in files:
            for record in SuppressionReasonScanner.scan_file(path):
                record["file"] = str(path)
                violations.append(record)
        violations.sort(key=lambda v: (v["file"], v["line"]))

        if args.json:
            print(
                json.dumps(
                    {
                        "directories": [str(root) for root in roots],
                        "scanned": len(files),
                        "violation_count": len(violations),
                        "violations": violations,
                    },
                    indent=2,
                )
            )
        else:
            print("=" * 70)
            print("SUPPRESSION REASON — VALIDATION REPORT")
            print("=" * 70)
            roots_str = ", ".join(str(root) for root in roots)
            print(f"\nScanned {len(files)} files under {roots_str}")
            print(
                "Suppressions must carry the checker code/identifier "
                "and a reason."
            )

            if violations:
                print(
                    f"\n## Suppressions missing code/reason ({len(violations)})\n"
                )
                for violation in violations:
                    print(
                        f"  {violation['file']}:{violation['line']}  "
                        f"{violation['suppression']} missing "
                        f"{' and '.join(violation['missing'])}"
                    )
                print(
                    "\n  Fix: add the specific error code/identifier and a "
                    "reason explaining why the type is deliberately broad."
                )
            else:
                print("\n## Suppressions missing code/reason: none")

            print()
            if violations:
                print("Result: violations found (report-only mode)")
            else:
                print("Result: all clear")

        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(SuppressionReasonScanner.main())
