"""Comprehensive tests for api_doc_validator.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.documentor.api_doc.api_doc_report_writer import APIDocReportWriter
from zolletta_metaskill.documentor.api_doc.api_doc_validator import APIDocValidator
from zolletta_metaskill.documentor.structs import APIDocReportOptions
from zolletta_metaskill.documentor.structs.source_signature import SourceSignature


class TestAPIDocValidator:
    # --- SourceSignature ---

    def test_sourcesignature_basic_construction_returns_false(self) -> None:
        sig = SourceSignature(
            name="foo",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
        )
        assert sig.name == "foo"
        assert sig.kind == "function"
        assert sig.decorators == []
        assert sig.is_private is False
        assert sig.parent_class is None
        assert sig.qualified_name == "foo"
        assert sig.is_deprecated is False

    def test_qualified_name_with_parent(self) -> None:
        sig = SourceSignature(
            name="method",
            kind="method",
            file_path="mod.py",
            line_number=5,
            parameters=[],
            parent_class="MyClass",
        )
        assert sig.qualified_name == "MyClass.method"

    def test_is_deprecated_decorator(self) -> None:
        sig = SourceSignature(
            name="old",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
            decorators=["deprecated"],
        )
        assert sig.is_deprecated is True

    def test_is_deprecated_case_insensitive(self) -> None:
        sig = SourceSignature(
            name="old",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
            decorators=["DeprecatED"],
        )
        assert sig.is_deprecated is True

    def test_is_deprecated_no_decorator(self) -> None:
        sig = SourceSignature(
            name="ok",
            kind="function",
            file_path="mod.py",
            line_number=1,
            parameters=[],
            decorators=["staticmethod"],
        )
        assert sig.is_deprecated is False

    def test_sourcesignature_to_dict_returns_false(self) -> None:
        sig = SourceSignature(
            name="foo",
            kind="function",
            file_path="mod.py",
            line_number=10,
            parameters=[{"name": "x"}],
            return_annotation="int",
            decorators=["staticmethod"],
            is_private=True,
            parent_class="Cls",
        )
        d = sig.to_dict()
        assert d["name"] == "foo"
        assert d["qualified_name"] == "Cls.foo"
        assert d["kind"] == "function"
        assert d["line"] == 10
        assert d["parameters"] == [{"name": "x"}]
        assert d["return_annotation"] == "int"
        assert d["is_private"] is True
        assert d["is_deprecated"] is False

    # --- validate_api_docs ---

    def test_documented_not_in_source(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "phantom": {"name": "phantom", "line": 1, "kind": "function", "file": "api.md"}
        }
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "documented_not_in_source" for i in issues)

    def test_sourcesignature_undocumented_suggestion_is_valid(self) -> None:
        sig = SourceSignature("undoc", "function", "mod.py", 1, [{"name": "a"}])
        source_sigs = {"mod.py": [sig]}
        documented: dict[str, dict[str, Any]] = {}
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert any(s["type"] == "undocumented" for s in suggestions)

    def test_missing_param_in_docs(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [{"name": "a"}, {"name": "b"}])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "foo": {
                "name": "foo",
                "line": 1,
                "kind": "function",
                "file": "api.md",
                "parameters": [{"name": "a"}],
            }
        }
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "missing_param_in_docs" and i["param"] == "b" for i in issues)

    def test_extra_param_in_docs(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [{"name": "a"}])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "foo": {
                "name": "foo",
                "line": 1,
                "kind": "function",
                "file": "api.md",
                "parameters": [{"name": "a"}, {"name": "ghost"}],
            }
        }
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "extra_param_in_docs" and i["param"] == "ghost" for i in issues)

    def test_deprecated_still_documented(self) -> None:
        sig = SourceSignature("old", "function", "mod.py", 1, [], decorators=["deprecated"])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "old": {
                "name": "old",
                "line": 1,
                "kind": "function",
                "file": "api.md",
                "parameters": [],
            }
        }
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert any(i["type"] == "deprecated_still_documented" for i in issues)

    def test_no_issues_when_matched(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [{"name": "a"}])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "foo": {
                "name": "foo",
                "line": 1,
                "kind": "function",
                "file": "api.md",
                "parameters": [{"name": "a"}],
            }
        }
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == []

    def test_both_empty_params(self) -> None:
        sig = SourceSignature("foo", "function", "mod.py", 1, [])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "foo": {
                "name": "foo",
                "line": 1,
                "kind": "function",
                "file": "api.md",
                "parameters": [],
            }
        }
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == []

    def test_qualified_name_skipped_when_simple_name_present(self) -> None:
        """Qualified name is skipped to avoid duplicate suggestions.

        When both 'method' and 'MyClass.method' are in source_by_name,
        the qualified name entry is skipped.
        """
        method_sig = SourceSignature(
            "method", "method", "mod.py", 1, [{"name": "x"}], parent_class="MyClass"
        )
        source_sigs = {"mod.py": [method_sig]}
        documented: dict[str, dict[str, Any]] = {}
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        # Only one suggestion for the method, not two
        undoc = [s for s in suggestions if s["type"] == "undocumented"]
        assert len(undoc) == 1
        assert undoc[0]["name"] == "method"

    def test_undocumented_init_py_is_skipped(self) -> None:
        """An undocumented function in __init__.py is classified as 'skip' and not suggested."""
        sig = SourceSignature("reexport", "function", "__init__.py", 1, [])
        source_sigs = {"__init__.py": [sig]}
        documented: dict[str, dict[str, Any]] = {}
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        undoc = [s for s in suggestions if s["type"] == "undocumented"]
        assert len(undoc) == 0

    def test_undocumented_dataclass_is_skipped(self) -> None:
        """An undocumented dataclass is classified as 'skip' and not suggested."""
        sig = SourceSignature("MyData", "class", "mod.py", 1, [], decorators=["dataclass"])
        source_sigs = {"mod.py": [sig]}
        documented: dict[str, dict[str, Any]] = {}
        issues, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        undoc = [s for s in suggestions if s["type"] == "undocumented"]
        assert len(undoc) == 0

    # --- _classify_undocumented ---

    def test_init_py_skip(self) -> None:
        sig = SourceSignature("foo", "function", "__init__.py", 1, [])
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "skip"

    def test_classify_undocumented_dataclass_skip_returns_skip(self) -> None:
        sig = SourceSignature("MyData", "class", "mod.py", 1, [], decorators=["dataclass"])
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "skip"

    def test_entry_point_high(self) -> None:
        sig = SourceSignature("main", "function", "mod.py", 1, [])
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "high"

    def test_classify_undocumented_protocol_high_returns_high(self) -> None:
        sig = SourceSignature("MyProto", "class", "mod.py", 1, [], decorators=["runtime_checkable"])
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "high"

    def test_complex_class_high(self) -> None:
        sig = SourceSignature(
            "BigClass", "class", "mod.py", 1, [{"name": f"p{i}"} for i in range(5)]
        )
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "high"

    def test_complex_function_medium(self) -> None:
        sig = SourceSignature(
            "complex", "function", "mod.py", 1, [{"name": f"p{i}"} for i in range(4)]
        )
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "medium"

    def test_simple_class_medium(self) -> None:
        sig = SourceSignature("Simple", "class", "mod.py", 1, [{"name": "a"}])
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "medium"

    def test_simple_function_low(self) -> None:
        sig = SourceSignature("simple", "function", "mod.py", 1, [{"name": "a"}])
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "low"

    def test_classify_undocumented_method_low_returns_low(self) -> None:
        sig = SourceSignature("meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="C")
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "low"

    def test_classify_undocumented_default_low_returns_low(self) -> None:
        sig = SourceSignature(
            "weird",
            "other",
            "mod.py",
            1,
            [{"name": "a"}, {"name": "b"}, {"name": "c"}],
        )
        priority, reason = APIDocValidator._classify_undocumented(sig)
        assert priority == "low"

    # --- generate_report ---

    def test_generate_report_json_output_returns_3(self) -> None:
        issues = [{"type": "documented_not_in_source", "severity": "high", "description": "test"}]
        report = APIDocReportWriter.generate_report(
            issues, [], APIDocReportOptions(5, 3, as_json=True)
        )
        data = json.loads(report)
        assert data["summary"]["total_issues"] == 1
        assert data["summary"]["source_signatures"] == 5
        assert data["summary"]["documented_items"] == 3

    def test_text_output_no_issues(self) -> None:
        report = APIDocReportWriter.generate_report(
            [], [], APIDocReportOptions(5, 3, as_json=False)
        )
        assert "No drift issues found" in report
        assert "Source signatures found: 5" in report

    def test_text_output_with_issues(self) -> None:
        issues = [
            {
                "type": "documented_not_in_source",
                "severity": "high",
                "description": "test",
                "source_file": "mod.py",
                "source_line": 10,
            }
        ]
        report = APIDocReportWriter.generate_report(
            issues, [], APIDocReportOptions(5, 3, as_json=False)
        )
        assert "HIGH" in report
        assert "test" in report

    def test_generate_report_suggest_coverage_contains_foo(self) -> None:
        suggestions = [
            {
                "type": "undocumented",
                "priority": "high",
                "name": "foo",
                "kind": "function",
                "reason": "entry point",
                "description": "desc",
            }
        ]
        report = APIDocReportWriter.generate_report(
            [], suggestions, APIDocReportOptions(5, 3, suggest_coverage=True)
        )
        assert "DOCUMENTATION SUGGESTIONS" in report
        assert "foo" in report

    def test_suggest_coverage_capped(self) -> None:
        suggestions = [
            {
                "type": "undocumented",
                "priority": "low",
                "name": f"f{i}",
                "kind": "function",
                "reason": "simple",
                "description": "desc",
            }
            for i in range(25)
        ]
        report = APIDocReportWriter.generate_report(
            [], suggestions, APIDocReportOptions(5, 3, suggest_coverage=True)
        )
        assert "more" in report

    def test_issues_by_type_section(self) -> None:
        issues = [{"type": "documented_not_in_source", "severity": "high", "description": "test"}]
        report = APIDocReportWriter.generate_report(
            issues, [], APIDocReportOptions(5, 3, as_json=False)
        )
        assert "ISSUES BY TYPE" in report

    # --- APIDocValidator.main() ---

    def _write_settings(self, tmp_path: Path, **overrides: object) -> Path:
        """Write a minimal settings.json under ``tmp_path/.zolletta-metaskill``."""
        settings: dict[str, object] = {
            "language": "python",
            "python": {"paths": {"source": ["src"], "tests": ["tests"]}},
            "documentation": {"dir": "docs"},
        }
        doc_overrides = overrides.pop("documentation", None)
        if isinstance(doc_overrides, dict):
            base_doc = settings["documentation"]
            assert isinstance(base_doc, dict)
            base_doc.update(doc_overrides)
        settings.update(overrides)
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "settings.json"
        path.write_text(json.dumps(settings))
        return path

    def _run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
        """Chdir into tmp_path and run main() with *argv*."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", argv)
        return APIDocValidator.main()

    def test_main_source_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        (tmp_path / "docs").mkdir()
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "source" in err

    def test_main_doc_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "documentation" in err

    def test_main_directory_source(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `foo()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "API Documentation Validation Report" in out

    def test_main_custom_docs_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path, documentation={"dir": "api.md"})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        (tmp_path / "api.md").write_text("### `foo()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0

    def test_main_json_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `foo()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "summary" in data

    def test_main_recursive_setting(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path, documentation={"api_docs_recursive": True})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        sub = docs / "sub"
        sub.mkdir(parents=True)
        (sub / "api.md").write_text("### `foo()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Documented items found:  1" in out

    def test_main_include_private_setting(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path, documentation={"include_private": True})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def _private(): pass\ndef foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `foo()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["summary"]["source_signatures"] == 2

    def test_main_suggest_coverage_setting(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path, documentation={"suggest_coverage": True})
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("Nothing here.\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "DOCUMENTATION SUGGESTIONS" in out

    def test_main_high_severity_report_only(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self._write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `phantom()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "phantom" in out
