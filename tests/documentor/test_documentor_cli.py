"""Tests for documentor_cli.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.api_doc.api_doc_validator import APIDocValidator
from zolletta_metaskill.documentor.documentor_cli import DocumentorCLI
from zolletta_metaskill.documentor.links.link_checker import LinkChecker
from zolletta_metaskill.documentor.quality.quality_review import QualityReview


class TestDocumentorCLI:
    def _patch_main_inputs(
        self,
        tmp_path: Path,
        *,
        python_configured: bool = True,
        aggregate_score: float | None = 80.0,
        settings: dict[str, Any] | None = None,
    ) -> tuple[Any, ...]:
        cache_dir = tmp_path / "cache"
        quality_payload = {
            "summary": {"aggregate_score": aggregate_score, "total_docs": 1},
            "documents": [],
            "issues": [],
        }

        def fake_run(cache_dir_arg: Path, payload: dict[str, Any]) -> Path:
            cache_dir_arg.mkdir(parents=True, exist_ok=True)
            path = cache_dir_arg / "quality.json"
            path.write_text(json.dumps(payload))
            return path

        return (
            patch(
                "zolletta_metaskill.documentor.documentor_cli.ProjectConfig.load_settings",
                return_value=settings if settings is not None else {},
            ),
            patch(
                "zolletta_metaskill.documentor.documentor_cli.DocumentorSettings.resolve_cache_dir",
                return_value=cache_dir,
            ),
            patch.object(
                QualityReview,
                "run",
                side_effect=lambda repo, s, cd: fake_run(cd, quality_payload),
            ),
            patch.object(APIDocValidator, "run", return_value=None),
            patch.object(APIDocValidator, "_write_cache", return_value=None),
            patch.object(LinkChecker, "run", return_value=None),
            patch.object(
                DocumentorCLI,
                "_python_configured",
                return_value=python_configured,
            ),
        )

    # --- main ---

    def test_main_runs_all_tools_and_prints_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patches = self._patch_main_inputs(tmp_path)
        with (
            patch("sys.argv", ["documentor_cli.py"]),
            patches[0],
            patches[1],
            patches[2] as mock_q,
            patches[3] as mock_api,
            patches[4],
            patches[5] as mock_link,
            patches[6],
        ):
            exit_code = DocumentorCLI.main()
        assert exit_code == 0
        mock_q.assert_called_once()
        mock_api.assert_called_once()
        mock_link.assert_called_once()
        out = capsys.readouterr().out
        assert "Documentor Review Report" in out

    def test_main_skips_api_doc_when_python_not_configured(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patches = self._patch_main_inputs(tmp_path, python_configured=False)
        with (
            patch("sys.argv", ["documentor_cli.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3] as mock_api,
            patches[4] as mock_skip,
            patches[5],
            patches[6],
        ):
            exit_code = DocumentorCLI.main()
        assert exit_code == 0
        mock_api.assert_not_called()
        mock_skip.assert_called_once()

    def test_main_json_output(self, tmp_path: Path) -> None:
        patches = self._patch_main_inputs(tmp_path)
        printed: list[str] = []
        with (
            patch("sys.argv", ["documentor_cli.py", "--json"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print", side_effect=printed.append),
        ):
            exit_code = DocumentorCLI.main()
        assert exit_code == 0
        data = json.loads(printed[0])
        assert set(data["sections"]) == {"quality", "api_doc", "links"}
        assert data["summary"]["aggregate_score"] == 80.0

    def test_main_threshold_gate_exits_1(self, tmp_path: Path) -> None:
        settings = {"documentation": {"staleness_threshold": 90}}
        patches = self._patch_main_inputs(tmp_path, aggregate_score=50.0, settings=settings)
        with (
            patch("sys.argv", ["documentor_cli.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            exit_code = DocumentorCLI.main()
        assert exit_code == 1

    def test_main_no_score_exits_0(self, tmp_path: Path) -> None:
        patches = self._patch_main_inputs(tmp_path, aggregate_score=None)
        with (
            patch("sys.argv", ["documentor_cli.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            exit_code = DocumentorCLI.main()
        assert exit_code == 0
