"""Tests for DocstringStreamliner — split from TestDocstringStreamliner."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.code_style.python.docstring_report_writer import DocstringReportWriter
from zolletta_metaskill.code_style.python.docstring_streamliner import DocstringStreamliner


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {
            "code_style": {},
            "paths": {"source": ["src"], "tests": ["tests"], "package": "mypkg"},
        },
        "php": None,
    }
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


class TestDocstringStreamlinerIntegration:
    """Tests for DocstringStreamliner (integration), split from TestDocstringStreamliner."""

    def _parse(self, source: str) -> ast.FunctionDef:
        tree = ast.parse(source)
        DocstringStreamliner._annotate_parents(tree)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        return node

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return DocstringStreamliner.main()

    # --- Tests for DocstringStreamliner.is_trivial_arg_desc(). ---

    def test_no_annotation_keeps_section(self) -> None:
        assert DocstringStreamliner.is_trivial_arg_desc("x", "some desc", None) is False

    # --- Tests for DocstringStreamliner.get_arg_annotations(). ---

    def test_get_arg_annotations_simple_function_returns_dict(self) -> None:
        tree = ast.parse("def f(x: int, y: str) -> bool: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns == {"x": "int", "y": "str"}

    def test_get_arg_annotations_unannotated_arg_returns_dict(self) -> None:
        tree = ast.parse("def f(x, y: str) -> bool: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns == {"x": None, "y": "str"}

    def test_get_arg_annotations_kwonly_args_returns_dict(self) -> None:
        tree = ast.parse("def f(*, x: int, y: str) -> None: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        anns = DocstringStreamliner.get_arg_annotations(node)
        assert anns == {"x": "int", "y": "str"}

    # --- Tests for DocstringStreamliner.get_return_annotation(). ---

    def test_get_return_annotation_return_annotation_returns_bool(self) -> None:
        tree = ast.parse("def f(x: int) -> bool: ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        assert DocstringStreamliner.get_return_annotation(node) == "bool"

    def test_no_return_annotation(self) -> None:
        tree = ast.parse("def f(x: int): ...")
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)
        assert DocstringStreamliner.get_return_annotation(node) is None

    # --- Tests for DocstringStreamliner._detect_prefix_quote(). ---

    def test_no_match_returns_default(self) -> None:
        result = DocstringStreamliner._detect_prefix_quote("pass")
        assert result is not None
        prefix, quote = result
        assert prefix == ""
        assert quote == '"""'

    # --- Tests for DocstringStreamliner._init_is_obvious(). ---

    def test_init_is_obvious_all_annotated_returns_true(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"self": None, "x": "int", "y": "str"}) is True

    def test_init_is_obvious_self_only_returns_true(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"self": None}) is True

    def test_init_is_obvious_unannotated_param_returns_false(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"self": None, "x": None}) is False

    def test_init_is_obvious_cls_skipped_returns_true(self) -> None:
        assert DocstringStreamliner._init_is_obvious({"cls": None, "x": "int"}) is True

    # --- Tests for DocstringReportWriter.print_report(). ---

    def test_print_report_no_findings_contains_all_clear(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        total = DocstringReportWriter.print_report([], apply_mode=False)
        captured = capsys.readouterr()
        assert total == 0
        assert "all clear" in captured.out

    # --- Tests for DocstringStreamliner.main(). ---

    def test_check_disabled_reports_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"check_docstring_no_type_repeat": False}})
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"code_style": {"check_docstring_no_type_repeat": False}})
        (tmp_path / "src").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_no_findings_contains_all_clear(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary."""\n    pass\n', encoding="utf-8"
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_findings_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "dry-run" in out

    def test_findings_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Findings never produce a non-zero exit code."""
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0

    def test_main_json_flag_outputs_findings_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["total"] == 1
        assert report["apply_mode"] is False
        assert report["findings"][0]["kind"] == "redundant"
        assert "src" in report["directories"]

    def test_apply_flag_writes_changes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        mod = src / "mod.py"
        mod.write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog", "--apply"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "apply mode" in out
        new_content = mod.read_text(encoding="utf-8")
        assert "Args:" not in new_content

    def test_gitignored_files_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("ignored/\n")
        _write_settings(tmp_path)
        ignored = tmp_path / "src" / "ignored"
        ignored.mkdir(parents=True)
        (ignored / "mod.py").write_text(
            'def f(x: int) -> None:\n    """Summary.\n\nArgs:\n    x: int"""\n    pass\n',
            encoding="utf-8",
        )
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
