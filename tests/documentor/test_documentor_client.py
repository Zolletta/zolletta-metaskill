"""Tests for documentor_client.py."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.api_doc.api_doc_validator import APIDocValidator
from zolletta_metaskill.documentor.documentor_client import DocumentorClient
from zolletta_metaskill.documentor.links.link_checker import LinkChecker
from zolletta_metaskill.documentor.quality.quality_review import QualityReview


class TestDocumentorClient:
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
                "zolletta_metaskill.documentor.documentor_client.ProjectConfig.load_settings",
                return_value=settings if settings is not None else {},
            ),
            patch(
                "zolletta_metaskill.documentor.documentor_client.DocumentorSettings.resolve_cache_dir",
                return_value=cache_dir,
            ),
            patch.object(
                QualityReview,
                "run",
                side_effect=lambda _repo, _s, cd: fake_run(cd, quality_payload),
            ),
            patch.object(APIDocValidator, "run", return_value=None),
            patch.object(APIDocValidator, "_write_cache", return_value=None),
            patch.object(LinkChecker, "run", return_value=None),
            patch.object(
                DocumentorClient,
                "_python_configured",
                return_value=python_configured,
            ),
        )

    # --- _python_configured ---

    def _layout(self, tmp_path: Path, *, src: bool, docs: bool) -> Path:
        """Create the requested subset of ``src``/``docs`` and chdir into tmp_path."""
        if src:
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "mod.py").write_text("def foo(): pass\n")
        if docs:
            (tmp_path / "docs").mkdir()
        return tmp_path

    def test_python_configured_true_when_src_and_docs_exist(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Both an existing source root and an existing docs dir enable the Python run."""
        self._layout(tmp_path, src=True, docs=True)
        monkeypatch.chdir(tmp_path)
        settings = {"language": "python", "documentation": {"dir": "docs"}}
        assert DocumentorClient._python_configured(settings) is True

    def test_python_configured_false_when_source_root_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A configured source root that does not exist disables the Python run."""
        self._layout(tmp_path, src=False, docs=True)
        monkeypatch.chdir(tmp_path)
        settings = {"language": "python", "documentation": {"dir": "docs"}}
        assert DocumentorClient._python_configured(settings) is False

    def test_python_configured_false_when_docs_dir_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A missing docs dir disables the Python run even with a valid source root."""
        self._layout(tmp_path, src=True, docs=False)
        monkeypatch.chdir(tmp_path)
        settings = {"language": "python", "documentation": {"dir": "docs"}}
        assert DocumentorClient._python_configured(settings) is False

    def test_python_configured_false_for_non_python_language(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A language without Python source roots yields no roots for ``.py``."""
        self._layout(tmp_path, src=True, docs=True)
        monkeypatch.chdir(tmp_path)
        settings = {"language": "php", "documentation": {"dir": "docs"}}
        assert DocumentorClient._python_configured(settings) is False

    def test_python_configured_uses_custom_docs_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """``documentation.dir`` is honoured rather than the ``docs`` default."""
        self._layout(tmp_path, src=True, docs=True)
        (tmp_path / "guide").mkdir()
        monkeypatch.chdir(tmp_path)
        settings = {"language": "python", "documentation": {"dir": "guide"}}
        assert DocumentorClient._python_configured(settings) is True

    def test_python_configured_uses_custom_source_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """``python.paths.source`` is honoured rather than the ``src`` default."""
        (tmp_path / "lib").mkdir()
        (tmp_path / "docs").mkdir()
        monkeypatch.chdir(tmp_path)
        settings = {
            "language": "python",
            "python": {"paths": {"source": ["lib"]}},
            "documentation": {"dir": "docs"},
        }
        assert DocumentorClient._python_configured(settings) is True

    def test_python_configured_false_when_default_docs_exists_but_custom_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Only the configured docs dir counts, not the ``docs`` default."""
        self._layout(tmp_path, src=True, docs=True)
        monkeypatch.chdir(tmp_path)
        settings = {"language": "python", "documentation": {"dir": "guide"}}
        assert DocumentorClient._python_configured(settings) is False

    # --- main ---

    def test_main_runs_all_tools_and_prints_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patches = self._patch_main_inputs(tmp_path)
        cache_dir = tmp_path / "cache"
        with (
            patch("sys.argv", ["documentor_client.py"]),
            patches[0],
            patches[1] as mock_resolve,
            patches[2] as mock_q,
            patches[3] as mock_api,
            patches[4],
            patches[5] as mock_link,
            patches[6],
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 0
        mock_resolve.assert_called_once_with({})
        mock_q.assert_called_once_with(os.path.abspath("."), {}, cache_dir)
        mock_api.assert_called_once_with({}, cache_dir)
        mock_link.assert_called_once_with(os.path.abspath("."), {}, cache_dir)
        out = capsys.readouterr().out
        assert "Documentor Review Report" in out

    def test_main_creates_cache_dir_with_parents(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patches = self._patch_main_inputs(tmp_path)
        real_mkdir = Path.mkdir
        mkdir_kwargs: list[dict[str, Any]] = []

        def spy(self: Path, *args: Any, **kwargs: Any) -> None:
            mkdir_kwargs.append(kwargs)
            real_mkdir(self, *args, **kwargs)

        with (
            patch("sys.argv", ["documentor_client.py"]),
            patch.object(Path, "mkdir", autospec=True, side_effect=spy),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            DocumentorClient.main()
        assert mkdir_kwargs
        assert all(kwargs == {"parents": True, "exist_ok": True} for kwargs in mkdir_kwargs)

    def test_main_skips_api_doc_when_python_not_configured(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patches = self._patch_main_inputs(tmp_path, python_configured=False)
        with (
            patch("sys.argv", ["documentor_client.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3] as mock_api,
            patches[4] as mock_skip,
            patches[5],
            patches[6],
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 0
        mock_api.assert_not_called()
        mock_skip.assert_called_once_with(
            tmp_path / "cache",
            {
                "skipped_reason": "Python source roots or docs dir not configured/missing",
                "summary": {},
                "issues": [],
                "suggestions": [],
            },
        )

    def test_main_json_output(self, tmp_path: Path) -> None:
        patches = self._patch_main_inputs(tmp_path)
        printed: list[str] = []
        with (
            patch("sys.argv", ["documentor_client.py", "--json"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print", side_effect=printed.append),
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 0
        data = json.loads(printed[0])
        assert set(data["sections"]) == {"quality", "api_doc", "links"}
        assert data["summary"]["aggregate_score"] == 80.0

    def test_main_threshold_gate_exits_1(self, tmp_path: Path) -> None:
        settings = {"documentation": {"staleness_threshold": 90}}
        patches = self._patch_main_inputs(tmp_path, aggregate_score=50.0, settings=settings)
        with (
            patch("sys.argv", ["documentor_client.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 1

    def test_main_threshold_gate_json_mode_exits_1(self, tmp_path: Path) -> None:
        settings = {"documentation": {"staleness_threshold": 90}}
        patches = self._patch_main_inputs(tmp_path, aggregate_score=50.0, settings=settings)
        with (
            patch("sys.argv", ["documentor_client.py", "--json"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 1

    def test_main_score_equal_to_threshold_exits_0(self, tmp_path: Path) -> None:
        settings = {"documentation": {"staleness_threshold": 90}}
        patches = self._patch_main_inputs(tmp_path, aggregate_score=90.0, settings=settings)
        with (
            patch("sys.argv", ["documentor_client.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 0

    def test_main_quality_cache_without_summary_exits_0(self, tmp_path: Path) -> None:
        patches = self._patch_main_inputs(tmp_path)
        with (
            patch("sys.argv", ["documentor_client.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
            patch(
                "zolletta_metaskill.documentor.documentor_client.ReportAggregator.read_quality_cache",
                return_value={"issues": []},
            ),
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 0

    def test_main_no_score_exits_0(self, tmp_path: Path) -> None:
        patches = self._patch_main_inputs(tmp_path, aggregate_score=None)
        with (
            patch("sys.argv", ["documentor_client.py"]),
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch("builtins.print"),
        ):
            exit_code = DocumentorClient.main()
        assert exit_code == 0

    def test_below_threshold_returns_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            "zolletta_metaskill.core.project_config.ProjectConfig.load_settings",
            staticmethod(lambda *a, **k: {"documentation": {"staleness_threshold": 100}}),
        )
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = DocumentorClient.main()
        assert rc == 1
        assert "below threshold" in capsys.readouterr().err
