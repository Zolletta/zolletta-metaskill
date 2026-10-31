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
        self._write_settings(tmp_path, documentation={"api_doc_recursive": True})
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
        self._write_settings(tmp_path, documentation={"api_doc_include_private": True})
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
        self._write_settings(tmp_path, documentation={"api_doc_suggest_coverage": True})
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

    # --- validate_api_docs: exact issue payloads ---

    def test_phantom_doc_issue_full_fields_returns_exact_dict(self) -> None:
        sig = SourceSignature("real", "function", "mod.py", 3, [])
        source_sigs = {"mod.py": [sig]}
        documented = {"ghost": {"file": "api.md", "line": 42}}
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == [
            {
                "type": "documented_not_in_source",
                "severity": "high",
                "name": "ghost",
                "doc_file": "api.md",
                "doc_line": 42,
                "description": (
                    "'ghost' is documented but not found in source code (removed or renamed)"
                ),
            }
        ]

    def test_phantom_doc_issue_missing_fields_returns_defaults(self) -> None:
        sig = SourceSignature("real", "function", "mod.py", 3, [])
        source_sigs = {"mod.py": [sig]}
        documented: dict[str, dict[str, Any]] = {"ghost": {}}
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == [
            {
                "type": "documented_not_in_source",
                "severity": "high",
                "name": "ghost",
                "doc_file": "unknown",
                "doc_line": 0,
                "description": (
                    "'ghost' is documented but not found in source code (removed or renamed)"
                ),
            }
        ]

    def test_param_mismatch_full_fields_returns_exact_dicts(self) -> None:
        sig = SourceSignature("foo", "function", "src/mod.py", 7, [{"name": "a"}, {"name": "b"}])
        source_sigs = {"mod.py": [sig]}
        documented = {
            "foo": {
                "file": "api.md",
                "line": 9,
                "parameters": [{"name": "a"}, {"name": "z"}],
            }
        }
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == [
            {
                "type": "missing_param_in_docs",
                "severity": "medium",
                "name": "foo",
                "param": "b",
                "source_file": "src/mod.py",
                "source_line": 7,
                "doc_file": "api.md",
                "doc_line": 9,
                "description": "Parameter 'b' in source but not documented for 'foo'",
            },
            {
                "type": "extra_param_in_docs",
                "severity": "low",
                "name": "foo",
                "param": "z",
                "source_file": "src/mod.py",
                "source_line": 7,
                "doc_file": "api.md",
                "doc_line": 9,
                "description": "Parameter 'z' documented for 'foo' but not in source",
            },
        ]

    def test_param_mismatch_missing_fields_returns_defaults(self) -> None:
        sig = SourceSignature("foo", "function", "src/mod.py", 7, [{"name": "b"}])
        source_sigs = {"mod.py": [sig]}
        documented: dict[str, dict[str, Any]] = {"foo": {}}
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == [
            {
                "type": "missing_param_in_docs",
                "severity": "medium",
                "name": "foo",
                "param": "b",
                "source_file": "src/mod.py",
                "source_line": 7,
                "doc_file": "unknown",
                "doc_line": 0,
                "description": "Parameter 'b' in source but not documented for 'foo'",
            }
        ]

    def test_param_mismatch_extra_missing_fields_returns_defaults(self) -> None:
        sig = SourceSignature("foo", "function", "src/mod.py", 7, [])
        source_sigs = {"mod.py": [sig]}
        documented = {"foo": {"parameters": [{"name": "z"}]}}
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == [
            {
                "type": "extra_param_in_docs",
                "severity": "low",
                "name": "foo",
                "param": "z",
                "source_file": "src/mod.py",
                "source_line": 7,
                "doc_file": "unknown",
                "doc_line": 0,
                "description": "Parameter 'z' documented for 'foo' but not in source",
            }
        ]

    def test_deprecated_issue_full_fields_returns_exact_dict(self) -> None:
        sig = SourceSignature("old", "function", "src/mod.py", 12, [], decorators=["deprecated"])
        source_sigs = {"mod.py": [sig]}
        documented = {"old": {"file": "api.md", "line": 5, "parameters": []}}
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert issues == [
            {
                "type": "deprecated_still_documented",
                "severity": "low",
                "name": "old",
                "source_file": "src/mod.py",
                "source_line": 12,
                "description": (
                    "'old' has @deprecated decorator but may still be documented as current"
                ),
            }
        ]

    def test_deprecated_issue_not_deprecated_returns_empty(self) -> None:
        sig = SourceSignature("ok", "function", "src/mod.py", 12, [])
        source_sigs = {"mod.py": [sig]}
        documented = {"ok": {"file": "api.md", "line": 5, "parameters": []}}
        issues, _ = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert not any(i["type"] == "deprecated_still_documented" for i in issues)

    # --- _undocumented_suggestions ---

    def test_undocumented_suggestion_full_fields_returns_exact_dict(self) -> None:
        sig = SourceSignature("plain", "function", "mod.py", 11, [{"name": "x"}])
        source_sigs = {"mod.py": [sig]}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, {})
        assert suggestions == [
            {
                "type": "undocumented",
                "priority": "low",
                "name": "plain",
                "kind": "function",
                "source_file": "mod.py",
                "source_line": 11,
                "reason": "simple function — low documentation priority",
            }
        ]

    def test_undocumented_suggestions_dotted_names_return_both(self) -> None:
        """Qualified entries are suggested when their leaf name is absent from the keys."""
        sig = SourceSignature(
            "Cls.meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="Outer"
        )
        source_sigs = {"mod.py": [sig]}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, {})
        names = sorted(s["name"] for s in suggestions if s["type"] == "undocumented")
        assert names == ["Cls.meth", "Outer.Cls.meth"]

    def test_undocumented_suggestions_nested_qualified_returns_single(self) -> None:
        """A three-segment qualified name is still skipped when its leaf name is present."""
        sig = SourceSignature(
            "method", "method", "mod.py", 1, [{"name": "x"}], parent_class="Outer.Inner"
        )
        source_sigs = {"mod.py": [sig]}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, {})
        undoc = [s["name"] for s in suggestions if s["type"] == "undocumented"]
        assert undoc == ["method"]

    def test_undocumented_suggestions_qualified_skip_preserves_later(self) -> None:
        """Skipping a qualified name must not stop iteration over later signatures."""
        method = SourceSignature("meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="Cls")
        lone = SourceSignature("lone", "function", "mod.py", 2, [{"name": "y"}])
        source_sigs = {"mod.py": [method, lone]}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, {})
        names = [s["name"] for s in suggestions if s["type"] == "undocumented"]
        assert names == ["meth", "lone"]

    def test_undocumented_suggestions_skip_priority_preserves_later(self) -> None:
        """A 'skip' classification must not stop iteration over later signatures."""
        reexport = SourceSignature("reexport", "function", "__init__.py", 1, [])
        lone = SourceSignature("lone", "function", "mod.py", 2, [{"name": "y"}])
        source_sigs = {"mod.py": [reexport, lone]}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, {})
        names = [s["name"] for s in suggestions if s["type"] == "undocumented"]
        assert names == ["lone"]

    def test_undocumented_suggestions_private_sig_returns_empty(self) -> None:
        """Private signatures are never suggested, even when undocumented."""
        sig = SourceSignature("_priv", "function", "mod.py", 1, [], is_private=True)
        source_sigs = {"mod.py": [sig]}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, {})
        assert suggestions == []

    def test_undocumented_suggestions_documented_simple_name_returns_empty(self) -> None:
        """A method documented under its simple name is not suggested again."""
        sig = SourceSignature("meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="Cls")
        source_sigs = {"mod.py": [sig]}
        documented = {"meth": {"file": "api.md", "line": 1, "parameters": [{"name": "x"}]}}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        assert suggestions == []

    def test_undocumented_suggestions_documented_qualified_returns_empty(self) -> None:
        """A method documented under its qualified name is not suggested again."""
        sig = SourceSignature("meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="Cls")
        source_sigs = {"mod.py": [sig]}
        documented = {"Cls.meth": {"file": "api.md", "line": 1, "parameters": [{"name": "x"}]}}
        _, suggestions = APIDocValidator.validate_api_docs(source_sigs, documented)
        undoc = [s for s in suggestions if s["type"] == "undocumented"]
        assert undoc == []

    # --- _classify_undocumented reasons and boundaries ---

    def test_classify_undocumented_init_py_returns_skip_reason(self) -> None:
        sig = SourceSignature("foo", "function", "__init__.py", 1, [])
        assert APIDocValidator._classify_undocumented(sig) == (
            "skip",
            "re-export file — no standalone documentation needed",
        )

    def test_classify_undocumented_dataclass_returns_skip_reason(self) -> None:
        sig = SourceSignature("MyData", "class", "mod.py", 1, [], decorators=["dataclass"])
        assert APIDocValidator._classify_undocumented(sig) == (
            "skip",
            "dataclass — fields are self-documenting",
        )

    @pytest.mark.parametrize(
        "name",
        ["main", "run", "cli", "execute", "dispatch"],
        ids=[
            "main_function_high",
            "run_function_high",
            "cli_function_high",
            "execute_function_high",
            "dispatch_function_high",
        ],
    )
    def test_classify_undocumented_entry_function_returns_high(self, name: str) -> None:
        sig = SourceSignature(name, "function", "mod.py", 1, [])
        assert APIDocValidator._classify_undocumented(sig) == (
            "high",
            "entry-point function — users need to know this exists",
        )

    def test_classify_undocumented_entry_name_class_returns_medium(self) -> None:
        sig = SourceSignature("main", "class", "mod.py", 1, [])
        assert APIDocValidator._classify_undocumented(sig) == (
            "medium",
            "public class — part of the API surface",
        )

    def test_classify_undocumented_protocol_decorator_returns_high(self) -> None:
        sig = SourceSignature("MyProto", "class", "mod.py", 1, [], decorators=["Protocol"])
        assert APIDocValidator._classify_undocumented(sig) == (
            "high",
            "protocol definition — defines a public interface contract",
        )

    def test_classify_undocumented_runtime_checkable_returns_high_reason(self) -> None:
        sig = SourceSignature("MyProto", "class", "mod.py", 1, [], decorators=["runtime_checkable"])
        assert APIDocValidator._classify_undocumented(sig) == (
            "high",
            "protocol definition — defines a public interface contract",
        )

    def test_classify_undocumented_four_param_class_returns_high_reason(self) -> None:
        sig = SourceSignature("Big", "class", "mod.py", 1, [{"name": f"p{i}"} for i in range(4)])
        assert APIDocValidator._classify_undocumented(sig) == (
            "high",
            "class with 4 constructor params — complex initialization",
        )

    def test_classify_undocumented_three_param_class_returns_medium(self) -> None:
        sig = SourceSignature("Mid", "class", "mod.py", 1, [{"name": f"p{i}"} for i in range(3)])
        assert APIDocValidator._classify_undocumented(sig) == (
            "medium",
            "public class — part of the API surface",
        )

    def test_classify_undocumented_private_class_returns_low(self) -> None:
        sig = SourceSignature("_Hidden", "class", "mod.py", 1, [])
        assert APIDocValidator._classify_undocumented(sig) == (
            "low",
            "undocumented item",
        )

    def test_classify_undocumented_four_param_function_returns_medium_reason(self) -> None:
        sig = SourceSignature("fn", "function", "mod.py", 1, [{"name": f"p{i}"} for i in range(4)])
        assert APIDocValidator._classify_undocumented(sig) == (
            "medium",
            "function with 4 params — non-trivial signature",
        )

    def test_classify_undocumented_three_param_function_returns_low(self) -> None:
        sig = SourceSignature("fn", "function", "mod.py", 1, [{"name": f"p{i}"} for i in range(3)])
        assert APIDocValidator._classify_undocumented(sig) == (
            "low",
            "undocumented item",
        )

    def test_classify_undocumented_simple_function_returns_low_reason(self) -> None:
        sig = SourceSignature("fn", "function", "mod.py", 1, [{"name": "a"}, {"name": "b"}])
        assert APIDocValidator._classify_undocumented(sig) == (
            "low",
            "simple function — low documentation priority",
        )

    def test_classify_undocumented_method_returns_low_reason(self) -> None:
        sig = SourceSignature("meth", "method", "mod.py", 1, [{"name": "x"}], parent_class="C")
        assert APIDocValidator._classify_undocumented(sig) == (
            "low",
            "method — consider documenting if part of public API",
        )

    def test_classify_undocumented_other_kind_returns_low_reason(self) -> None:
        sig = SourceSignature("weird", "other", "mod.py", 1, [{"name": f"p{i}"} for i in range(5)])
        assert APIDocValidator._classify_undocumented(sig) == (
            "low",
            "undocumented item",
        )

    # --- run() ---

    def _settings(self, **doc: object) -> dict[str, Any]:
        """Return a minimal settings dict for a direct ``run()`` call."""
        documentation: dict[str, object] = {"dir": "docs"}
        documentation.update(doc)
        return {
            "language": "python",
            "python": {"paths": {"source": ["src"], "tests": ["tests"]}},
            "documentation": documentation,
        }

    def _make_tree(
        self,
        tmp_path: Path,
        source: str = "def foo(): pass\n",
        doc: str = "### `foo()`\n",
    ) -> Path:
        """Create src/ and docs/ under *tmp_path*; return the cache dir path."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(source)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text(doc)
        return tmp_path / "cache"

    def _cache(self, tmp_path: Path) -> dict[str, Any]:
        """Read the written cache file under ``tmp_path/cache``."""
        data: dict[str, Any] = json.loads(
            (tmp_path / "cache" / "api_doc_validator.json").read_text()
        )
        return data

    def test_run_missing_source_returns_error_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docs").mkdir()
        report, success = APIDocValidator.run(self._settings(), tmp_path / "cache")
        assert success is False
        assert report == "Error: no configured source directories exist on disk"
        assert self._cache(tmp_path) == {
            "error": report,
            "summary": {},
            "issues": [],
            "suggestions": [],
        }

    def test_run_missing_docs_returns_error_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        report, success = APIDocValidator.run(self._settings(), tmp_path / "cache")
        assert success is False
        assert report == "Error: documentation directory 'docs' does not exist"
        assert self._cache(tmp_path) == {
            "error": report,
            "summary": {},
            "issues": [],
            "suggestions": [],
        }

    def test_run_success_writes_summary_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path)
        report, success = APIDocValidator.run(self._settings(), cache_dir, as_json=True)
        assert success is True
        data = self._cache(tmp_path)
        assert data["summary"]["source_signatures"] == 1
        assert data["summary"]["documented_items"] == 1
        assert data["summary"]["total_issues"] == 0
        assert set(data) >= {"summary", "issues"}
        assert json.loads(report)["summary"]["source_signatures"] == 1

    def test_run_as_json_default_returns_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path)
        report, success = APIDocValidator.run(self._settings(), cache_dir)
        assert success is True
        assert "API Documentation Validation Report" in report

    def test_run_include_private_default_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path, source="def _p(): pass\ndef foo(): pass\n")
        _, success = APIDocValidator.run(self._settings(), cache_dir, as_json=True)
        assert success is True
        assert self._cache(tmp_path)["summary"]["source_signatures"] == 1

    def test_run_include_private_nonbool_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path, source="def _p(): pass\ndef foo(): pass\n")
        _, success = APIDocValidator.run(
            self._settings(api_doc_include_private="yes"), cache_dir, as_json=True
        )
        assert success is True
        assert self._cache(tmp_path)["summary"]["source_signatures"] == 1

    def test_run_recursive_default_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path, doc="Nothing.\n")
        sub = tmp_path / "docs" / "sub"
        sub.mkdir()
        (sub / "api.md").write_text("### `foo()`\n")
        _, success = APIDocValidator.run(self._settings(), cache_dir, as_json=True)
        assert success is True
        assert self._cache(tmp_path)["summary"]["documented_items"] == 0

    def test_run_recursive_nonbool_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path, doc="Nothing.\n")
        sub = tmp_path / "docs" / "sub"
        sub.mkdir()
        (sub / "api.md").write_text("### `foo()`\n")
        _, success = APIDocValidator.run(
            self._settings(api_doc_recursive="yes"), cache_dir, as_json=True
        )
        assert success is True
        assert self._cache(tmp_path)["summary"]["documented_items"] == 0

    def test_run_custom_source_root_returns_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        code = tmp_path / "code"
        code.mkdir()
        (code / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `foo()`\n")
        settings = self._settings()
        settings["python"]["paths"]["source"] = ["code"]
        _, success = APIDocValidator.run(settings, tmp_path / "cache", as_json=True)
        assert success is True
        assert self._cache(tmp_path)["summary"]["source_signatures"] == 1

    def test_run_suggest_coverage_default_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path, doc="Nothing.\n")
        report, success = APIDocValidator.run(self._settings(), cache_dir)
        assert success is True
        assert "DOCUMENTATION SUGGESTIONS" not in report

    def test_run_suggest_coverage_nonbool_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cache_dir = self._make_tree(tmp_path, doc="Nothing.\n")
        report, success = APIDocValidator.run(
            self._settings(api_doc_suggest_coverage="yes"), cache_dir
        )
        assert success is True
        assert "DOCUMENTATION SUGGESTIONS" not in report

    # --- _write_cache ---

    def test_write_cache_nested_dir_writes_pretty_json(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "deep" / "cache"
        data: dict[str, Any] = {"k": Path("x")}
        APIDocValidator._write_cache(cache_dir, data)
        cache_path = cache_dir / "api_doc_validator.json"
        assert [p.name for p in cache_dir.iterdir()] == ["api_doc_validator.json"]
        assert cache_path.read_text() == json.dumps(data, indent=2, default=str) + "\n"

    # --- APIDocValidator.main() cache wiring ---

    def test_main_writes_cache_under_runs_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        self._write_settings(tmp_path, runs_dir="runs")
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo(): pass\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("### `foo()`\n")
        rc = self._run(tmp_path, monkeypatch, ["prog"])
        assert rc == 0
        assert (tmp_path / "runs" / "cache" / "api_doc_validator.json").exists()
