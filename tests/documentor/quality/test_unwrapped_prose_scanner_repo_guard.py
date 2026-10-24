"""Repo-wide guard for the no-artificial-line-break convention.

The convention is deliberately unenforced by markdownlint — ``MD013: false``
in ``.markdownlint.yaml``, because a line-length rule would demand the exact
wrapping the convention forbids. These tests are what actually enforce it, and
they run inside the existing ``pytest + coverage`` CI job.
"""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.core.project_config import ProjectConfig
from zolletta_metaskill.documentor.quality.unwrapped_prose_scanner import UnwrappedProseScanner

REPO_ROOT = Path(__file__).resolve().parents[3]

#: CHANGELOG.md is written by python-semantic-release on every release and is
#: already excluded from the markdownlint gate in ``.markdownlint-cli2.jsonc``;
#: its wrapping is the generator's, not ours.
GENERATED = {"CHANGELOG.md"}

#: playground/ is intentionally defective input for scanner dogfooding — its
#: markdown carries wrapped prose on purpose, so findings there are expected,
#: not violations.
EXCLUDED_DIRS = {"playground"}


class TestUnwrappedProseScannerRepoGuard:
    # --- repo-wide guard ---

    def test_no_markdown_in_this_repo_has_a_wrapped_paragraph(self) -> None:
        findings = [
            f
            for f in UnwrappedProseScanner.scan_roots([REPO_ROOT])
            if Path(f.file).name not in GENERATED
            and not EXCLUDED_DIRS.intersection(Path(f.file).parts)
        ]
        assert findings == [], "\n".join(f"{f.file}:{f.line}  {f.description}" for f in findings)

    def test_repo_guard_actually_scans_a_meaningful_number_of_files(self) -> None:
        scanned = ProjectConfig.iter_files(REPO_ROOT, UnwrappedProseScanner.EXTENSIONS)
        assert len(scanned) > 50
