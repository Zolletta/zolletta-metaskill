"""Tests for drift_analyzer.py."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from zolletta_metaskill.documentor.drift_analyzer import (
    _load_gitignore_patterns,
    _parse_version_part,
    _version_is_older,
    check_readme_structure,
    detect_drift_for_doc,
    extract_references_from_doc,
    find_code_files,
    find_doc_files,
    generate_report,
    get_current_version_from_git,
    get_file_last_modified,
    get_files_changed_since,
    get_renamed_files,
    main,
    map_docs_to_code,
    run_git,
)

# ---------------------------------------------------------------------------
# _load_gitignore_patterns
# ---------------------------------------------------------------------------


class TestLoadGitignorePatterns:
    def test_no_gitignore(self, tmp_path: Path) -> None:
        assert _load_gitignore_patterns(str(tmp_path)) == set()

    def test_simple_entries(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(".venv/\nnode_modules/\nbuild/\n", encoding="utf-8")
        patterns = _load_gitignore_patterns(str(tmp_path))
        assert ".venv" in patterns
        assert "node_modules" in patterns
        assert "build" in patterns

    def test_comments_and_negations_skipped(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(
            "# comment\n!important\n*.pyc\ncache/\n", encoding="utf-8"
        )
        patterns = _load_gitignore_patterns(str(tmp_path))
        assert "cache" in patterns
        assert "important" not in patterns
        assert "*.pyc" not in patterns

    def test_nested_path_takes_basename(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("foo/bar/\n", encoding="utf-8")
        patterns = _load_gitignore_patterns(str(tmp_path))
        assert "bar" in patterns

    def test_os_error_handled(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("cache/\n", encoding="utf-8")
        with patch("builtins.open", side_effect=OSError("boom")):
            assert _load_gitignore_patterns(str(tmp_path)) == set()


# ---------------------------------------------------------------------------
# run_git
# ---------------------------------------------------------------------------


class TestRunGit:
    def test_success(self, tmp_path: Path) -> None:
        result = run_git(str(tmp_path), ["status"], default="FAIL")
        # Not a git repo, so returns default
        assert result == "FAIL"

    def test_file_not_found(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            assert run_git(str(tmp_path), ["log"], default="DEF") == "DEF"

    def test_timeout(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=1)):
            assert run_git(str(tmp_path), ["log"], default="DEF") == "DEF"

    def test_nonzero_returncode(self, tmp_path: Path) -> None:
        mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err")
        with patch("subprocess.run", return_value=mock_result):
            assert run_git(str(tmp_path), ["log"], default="DEF") == "DEF"

    def test_success_with_output(self, tmp_path: Path) -> None:
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="output\n", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            assert run_git(str(tmp_path), ["log"]) == "output"


# ---------------------------------------------------------------------------
# get_file_last_modified
# ---------------------------------------------------------------------------


class TestGetFileLastModified:
    def test_valid_date(self, tmp_path: Path) -> None:
        with patch(
            "zolletta_metaskill.documentor.drift_analyzer.run_git",
            return_value="2024-01-15T10:00:00+00:00",
        ):
            result = get_file_last_modified(str(tmp_path), "README.md")
            assert result is not None
            assert result.year == 2024

    def test_empty_output(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=""):
            assert get_file_last_modified(str(tmp_path), "README.md") is None

    def test_invalid_date(self, tmp_path: Path) -> None:
        with patch(
            "zolletta_metaskill.documentor.drift_analyzer.run_git", return_value="not-a-date"
        ):
            assert get_file_last_modified(str(tmp_path), "README.md") is None


# ---------------------------------------------------------------------------
# get_files_changed_since
# ---------------------------------------------------------------------------


class TestGetFilesChangedSince:
    def test_parse_changes(self, tmp_path: Path) -> None:
        output = "M\tsrc/foo.py\nA\tsrc/bar.py\nR100\told.py\tnew.py\n"
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=output):
            changes = get_files_changed_since(str(tmp_path), "2024-01-01")
        assert len(changes) == 3
        assert changes[0] == {"status": "M", "file": "src/foo.py"}
        assert changes[1] == {"status": "A", "file": "src/bar.py"}
        assert changes[2] == {"status": "R", "file": "new.py"}

    def test_with_scope(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git") as mock_git:
            mock_git.return_value = ""
            get_files_changed_since(str(tmp_path), "2024-01-01", scope="src/")
            args = mock_git.call_args[0][1]
            assert "--" in args
            assert "src/" in args

    def test_empty_output(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=""):
            assert get_files_changed_since(str(tmp_path), "2024-01-01") == []

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value="\n\n  \n"):
            assert get_files_changed_since(str(tmp_path), "2024-01-01") == []


# ---------------------------------------------------------------------------
# get_renamed_files
# ---------------------------------------------------------------------------


class TestGetRenamedFiles:
    def test_parse_renames(self, tmp_path: Path) -> None:
        output = "R100\told.py\tnew.py\nR90\ta.py\tb.py\n"
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=output):
            renames = get_renamed_files(str(tmp_path), "90 days ago")
        assert renames == [("old.py", "new.py"), ("a.py", "b.py")]

    def test_empty(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=""):
            assert get_renamed_files(str(tmp_path), "90 days ago") == []

    def test_non_rename_skipped(self, tmp_path: Path) -> None:
        output = "M\tsrc/foo.py\n"
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=output):
            assert get_renamed_files(str(tmp_path), "90 days ago") == []

    def test_empty_lines_skipped(self, tmp_path: Path) -> None:
        output = "\nR100\told.py\tnew.py\n\nR90\ta.py\tb.py\n\n"
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=output):
            renames = get_renamed_files(str(tmp_path), "90 days ago")
        assert renames == [("old.py", "new.py"), ("a.py", "b.py")]


# ---------------------------------------------------------------------------
# get_current_version_from_git
# ---------------------------------------------------------------------------


class TestGetCurrentVersion:
    def test_with_v_prefix(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value="v1.2.3"):
            assert get_current_version_from_git(str(tmp_path)) == "1.2.3"

    def test_without_v_prefix(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value="2.0.0"):
            assert get_current_version_from_git(str(tmp_path)) == "2.0.0"

    def test_no_tags(self, tmp_path: Path) -> None:
        with patch("zolletta_metaskill.documentor.drift_analyzer.run_git", return_value=""):
            assert get_current_version_from_git(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# find_doc_files
# ---------------------------------------------------------------------------


class TestFindDocFiles:
    def test_finds_markdown(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.rst").write_text("Guide", encoding="utf-8")
        result = find_doc_files(str(tmp_path))
        assert "README.md" in result
        assert os.path.join("docs", "guide.rst") in result

    def test_skips_hidden_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "README.md").write_text("git", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        result = find_doc_files(str(tmp_path))
        assert ".git" not in str(result)
        assert "README.md" in result

    def test_custom_patterns(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        (tmp_path / "data.txt").write_text("data", encoding="utf-8")
        result = find_doc_files(str(tmp_path), patterns=["*.md"])
        assert "README.md" in result
        assert "data.txt" not in result

    def test_custom_patterns_with_dot(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        result = find_doc_files(str(tmp_path), patterns=[".md"])
        assert "README.md" in result

    def test_custom_patterns_bare_ext(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        result = find_doc_files(str(tmp_path), patterns=["md"])
        assert "README.md" in result

    def test_gitignore_skips(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("docs/\n", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "README.md").write_text("# Test", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        result = find_doc_files(str(tmp_path))
        assert "README.md" in result
        assert all("docs" not in f for f in result)

    def test_sorted_output(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("b", encoding="utf-8")
        (tmp_path / "a.md").write_text("a", encoding="utf-8")
        result = find_doc_files(str(tmp_path))
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# find_code_files
# ---------------------------------------------------------------------------


class TestFindCodeFiles:
    def test_finds_python(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")
        result = find_code_files(str(tmp_path))
        assert "main.py" in result

    def test_scope_subdir(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "other.py").write_text("x = 2", encoding="utf-8")
        result = find_code_files(str(tmp_path), scope="src")
        assert any("mod.py" in f for f in result)
        assert all("other.py" not in f for f in result)

    def test_nonexistent_scope(self, tmp_path: Path) -> None:
        assert find_code_files(str(tmp_path), scope="nonexistent/") == []

    def test_skips_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "mod.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "mod.py").write_text("x = 1", encoding="utf-8")
        result = find_code_files(str(tmp_path))
        assert "mod.py" in result
        assert all("__pycache__" not in f for f in result)


# ---------------------------------------------------------------------------
# map_docs_to_code
# ---------------------------------------------------------------------------


class TestMapDocsToCode:
    def test_directory_proximity(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "auth.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "src" / "auth.md").write_text("auth docs", encoding="utf-8")
        doc_files = [os.path.join("src", "auth.md")]
        code_files = [os.path.join("src", "auth.py")]
        mapping = map_docs_to_code(str(tmp_path), doc_files, code_files)
        assert os.path.join("src", "auth.md") in mapping

    def test_content_reference(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "auth.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See auth.py for details", encoding="utf-8")
        doc_files = ["README.md"]
        code_files = [os.path.join("src", "auth.py")]
        mapping = map_docs_to_code(str(tmp_path), doc_files, code_files)
        assert "README.md" in mapping
        assert os.path.join("src", "") in mapping["README.md"] or "src" in mapping["README.md"]

    def test_parent_directory_proximity(self, tmp_path: Path) -> None:
        """Doc in a subdirectory whose parent directory contains code files."""
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "mod.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "pkg" / "docs").mkdir()
        (tmp_path / "pkg" / "docs" / "guide.md").write_text("guide", encoding="utf-8")
        doc_files = [os.path.join("pkg", "docs", "guide.md")]
        code_files = [os.path.join("pkg", "mod.py")]
        mapping = map_docs_to_code(str(tmp_path), doc_files, code_files)
        assert os.path.join("pkg", "docs", "guide.md") in mapping
        assert "pkg" in mapping[os.path.join("pkg", "docs", "guide.md")]

    def test_readme_naming_convention(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "README.md").write_text("# Auth", encoding="utf-8")
        doc_files = [os.path.join("src", "README.md")]
        code_files = []
        mapping = map_docs_to_code(str(tmp_path), doc_files, code_files)
        assert os.path.join("src", "README.md") in mapping

    def test_unreadable_doc_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        doc_files = ["README.md"]
        code_files = ["src/main.py"]
        with patch("builtins.open", side_effect=OSError("boom")):
            mapping = map_docs_to_code(str(tmp_path), doc_files, code_files)
        # Should not crash; mapping may be empty or have default
        assert isinstance(mapping, dict)


# ---------------------------------------------------------------------------
# extract_references_from_doc
# ---------------------------------------------------------------------------


class TestExtractReferences:
    def test_markdown_links(self, tmp_path: Path) -> None:
        doc = tmp_path / "README.md"
        doc.write_text("See [guide](guide.md) for more.", encoding="utf-8")
        refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert "guide.md" in refs["files"]
        assert "guide.md" in refs["links"]

    def test_external_links(self, tmp_path: Path) -> None:
        doc = tmp_path / "README.md"
        doc.write_text("Visit [site](https://example.com).", encoding="utf-8")
        refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert "https://example.com" in refs["links"]
        assert "https://example.com" not in refs["files"]

    def test_function_references(self, tmp_path: Path) -> None:
        doc = tmp_path / "README.md"
        doc.write_text("Call `my_func(` function.", encoding="utf-8")
        refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert "my_func" in refs["functions"]

    def test_version_strings(self, tmp_path: Path) -> None:
        doc = tmp_path / "README.md"
        doc.write_text("Requires v1.2.3 or later.", encoding="utf-8")
        refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert "1.2.3" in refs["versions"]

    def test_code_block_file_refs(self, tmp_path: Path) -> None:
        doc = tmp_path / "README.md"
        doc.write_text("Edit `config.yaml` file.", encoding="utf-8")
        refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert "config.yaml" in refs["files"]

    def test_unreadable_file(self, tmp_path: Path) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert refs == {"files": set(), "functions": set(), "versions": set(), "links": set()}

    def test_anchor_links(self, tmp_path: Path) -> None:
        doc = tmp_path / "README.md"
        doc.write_text("See [section](#section).", encoding="utf-8")
        refs = extract_references_from_doc(str(tmp_path), "README.md")
        assert "#section" in refs["links"]
        assert "#section" not in refs["files"]


# ---------------------------------------------------------------------------
# detect_drift_for_doc
# ---------------------------------------------------------------------------


class TestDetectDriftForDoc:
    def test_no_git_history(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        with patch(
            "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified", return_value=None
        ):
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        assert len(issues) == 1
        assert issues[0]["category"] == "temporal"
        assert issues[0]["severity"] == "info"

    def test_factual_drift_referenced_files(self, tmp_path: Path) -> None:
        (tmp_path / "auth.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `auth.py` for auth.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since"
            ) as mock_changed,
        ):
            mock_changed.return_value = [{"status": "M", "file": "auth.py"}]
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "low"

    def test_factual_drift_high_severity(self, tmp_path: Path) -> None:
        for i in range(7):
            (tmp_path / f"mod{i}.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text(
            "See " + " ".join(f"`mod{i}.py`" for i in range(7)), encoding="utf-8"
        )
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since"
            ) as mock_changed,
        ):
            mock_changed.return_value = [{"status": "M", "file": "mod0.py"}]
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "high"

    def test_factual_drift_medium_severity(self, tmp_path: Path) -> None:
        for i in range(4):
            (tmp_path / f"mod{i}.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text(
            "See " + " ".join(f"`mod{i}.py`" for i in range(4)), encoding="utf-8"
        )
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since"
            ) as mock_changed,
        ):
            mock_changed.return_value = [{"status": "M", "file": "mod0.py"}]
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "medium"

    def test_non_code_ref_skipped(self, tmp_path: Path) -> None:
        """Non-code file references (e.g. .md) are skipped in factual drift."""
        (tmp_path / "guide.md").write_text("guide", encoding="utf-8")
        (tmp_path / "README.md").write_text("See [guide](guide.md) for details.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 0

    def test_ref_resolved_from_repo_root(self, tmp_path: Path) -> None:
        """Code file ref that exists at repo root but not in doc's directory."""
        sub = tmp_path / "docs"
        sub.mkdir()
        (sub / "guide.md").write_text("See `mod.py` for details.", encoding="utf-8")
        (tmp_path / "mod.py").write_text("x = 1", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since"
            ) as mock_changed,
        ):
            mock_changed.return_value = [{"status": "M", "file": "mod.py"}]
            issues = detect_drift_for_doc(str(tmp_path), "docs/guide.md", [], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1
        assert factual[0]["severity"] == "low"

    def test_temporal_staleness(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        old_date = datetime.now(UTC) - timedelta(days=200)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=old_date,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        temporal = [
            i for i in issues if i["category"] == "temporal" and "not updated" in i["description"]
        ]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "medium"

    def test_version_drift(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("Requires v1.0.0", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], "2.0.0")
        version_issues = [i for i in issues if "version" in i["description"].lower()]
        assert len(version_issues) == 1

    def test_referential_rename_edge_case(self, tmp_path: Path) -> None:
        (tmp_path / "old.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("See `old.py`", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(
                str(tmp_path), "README.md", [], [("old.py", "new.py")], None
            )
        ref_issues = [i for i in issues if i["category"] == "referential"]
        assert len(ref_issues) == 1
        assert ref_issues[0]["severity"] == "high"

    def test_referential_rename_broad(self, tmp_path: Path) -> None:
        # old.py does NOT exist — broad rename detection fires (medium severity)
        (tmp_path / "README.md").write_text("See `old.py`", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(
                str(tmp_path),
                "README.md",
                [],
                [("old.py", "new.py")],
                None,
                include_referential=True,
            )
        ref_issues = [i for i in issues if i["category"] == "referential"]
        # Broad rename (medium) and possibly broken file reference (medium)
        rename_issues = [i for i in ref_issues if "renamed" in i["description"]]
        assert len(rename_issues) == 1
        assert rename_issues[0]["severity"] == "medium"

    def test_broken_file_reference(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("See `nonexistent.py`", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(
                str(tmp_path), "README.md", [], [], None, include_referential=True
            )
        ref_issues = [
            i
            for i in issues
            if i["category"] == "referential" and "non-existent" in i["description"]
        ]
        assert len(ref_issues) == 1

    def test_readme_structure_check(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n\nSome content.", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        structural = [i for i in issues if i["category"] == "structural"]
        assert len(structural) > 0

    def test_fallback_associated_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        doc_modified = datetime.now(UTC) - timedelta(days=10)
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=doc_modified,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since"
            ) as mock_changed,
        ):
            # Return many changes to trigger the >20 threshold
            mock_changed.return_value = [
                {"status": "M", "file": f"src/mod{i}.py"} for i in range(25)
            ]
            issues = detect_drift_for_doc(str(tmp_path), "README.md", ["src"], [], None)
        factual = [i for i in issues if i["category"] == "factual"]
        assert len(factual) == 1

    def test_naive_datetime_handled(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        old_date = datetime(2020, 1, 1)  # naive
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=old_date,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_files_changed_since",
                return_value=[],
            ),
        ):
            issues = detect_drift_for_doc(str(tmp_path), "README.md", [], [], None)
        temporal = [
            i for i in issues if i["category"] == "temporal" and "not updated" in i["description"]
        ]
        assert len(temporal) == 1


# ---------------------------------------------------------------------------
# check_readme_structure
# ---------------------------------------------------------------------------


class TestCheckReadmeStructure:
    def test_missing_sections(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n\nSome text.", encoding="utf-8")
        issues = check_readme_structure(str(tmp_path), "README.md")
        sections = {i["description"].split(": ")[-1] for i in issues}
        assert "Installation" in sections
        assert "Usage" in sections
        assert "License" in sections

    def test_all_sections_present(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation\n## Usage\n## License\n", encoding="utf-8"
        )
        issues = check_readme_structure(str(tmp_path), "README.md")
        assert len(issues) == 0

    def test_partial_match(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Project\n## Installation Guide\n## Usage Guide\n## License Info\n", encoding="utf-8"
        )
        issues = check_readme_structure(str(tmp_path), "README.md")
        assert len(issues) == 0

    def test_unreadable_file(self, tmp_path: Path) -> None:
        with patch("builtins.open", side_effect=OSError("boom")):
            issues = check_readme_structure(str(tmp_path), "README.md")
        assert issues == []


# ---------------------------------------------------------------------------
# _parse_version_part / _version_is_older
# ---------------------------------------------------------------------------


class TestVersionComparison:
    def test_parse_numeric(self) -> None:
        assert _parse_version_part("10") == 10

    def test_parse_with_suffix(self) -> None:
        assert _parse_version_part("2alpha") == 2

    def test_parse_empty(self) -> None:
        assert _parse_version_part("") == 0

    def test_parse_non_numeric(self) -> None:
        assert _parse_version_part("abc") == 0

    def test_older_version(self) -> None:
        assert _version_is_older("1.0.0", "2.0.0") is True

    def test_newer_version(self) -> None:
        assert _version_is_older("2.0.0", "1.0.0") is False

    def test_equal_version(self) -> None:
        assert _version_is_older("1.0.0", "1.0.0") is False

    def test_different_lengths(self) -> None:
        assert _version_is_older("1.0", "1.0.1") is True

    def test_v2_shorter_than_v1(self) -> None:
        assert _version_is_older("1.0.1", "1.0") is False

    def test_with_prerelease(self) -> None:
        assert _version_is_older("1.0.0-alpha", "1.0.0") is False

    def test_empty_string_is_older(self) -> None:
        # Empty string parses to [0] which is older than [1, 0, 0]
        assert _version_is_older("", "1.0.0") is True


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_empty_issues_json(self, tmp_path: Path) -> None:
        import json

        report = generate_report(str(tmp_path), [], [], as_json=True)
        data = json.loads(report)
        assert data["summary"]["total_docs"] == 0
        assert data["summary"]["total_issues"] == 0

    def test_with_issues_json(self, tmp_path: Path) -> None:
        import json

        issues = [
            {
                "file": "README.md",
                "severity": "high",
                "category": "factual",
                "description": "test",
                "fix_type": "auto",
            },
            {
                "file": "guide.md",
                "severity": "low",
                "category": "temporal",
                "description": "old",
                "fix_type": "manual",
            },
        ]
        report = generate_report(str(tmp_path), issues, ["README.md", "guide.md"], as_json=True)
        data = json.loads(report)
        assert data["summary"]["total_issues"] == 2
        assert data["summary"]["by_severity"]["high"] == 1
        assert data["summary"]["by_severity"]["low"] == 1

    def test_human_readable(self, tmp_path: Path) -> None:
        issues = [
            {
                "file": "README.md",
                "severity": "high",
                "category": "factual",
                "description": "test",
                "fix_type": "auto",
            },
        ]
        report = generate_report(str(tmp_path), issues, ["README.md"], as_json=False)
        assert "Documentation Drift Report" in report
        assert "HIGH SEVERITY" in report
        assert "[AUTO]" in report

    def test_no_issues_human_readable(self, tmp_path: Path) -> None:
        report = generate_report(str(tmp_path), [], ["README.md"], as_json=False)
        assert "No documentation drift detected" in report

    def test_severity_sorting(self, tmp_path: Path) -> None:
        issues = [
            {
                "file": "a.md",
                "severity": "low",
                "category": "temporal",
                "description": "a",
                "fix_type": "manual",
            },
            {
                "file": "b.md",
                "severity": "critical",
                "category": "factual",
                "description": "b",
                "fix_type": "auto",
            },
        ]
        report = generate_report(str(tmp_path), issues, ["a.md", "b.md"], as_json=False)
        # Critical should appear before low
        assert report.index("CRITICAL") < report.index("LOW")

    def test_fix_type_summary(self, tmp_path: Path) -> None:
        issues = [
            {
                "file": "a.md",
                "severity": "low",
                "category": "temporal",
                "description": "a",
                "fix_type": "auto",
            },
            {
                "file": "b.md",
                "severity": "low",
                "category": "temporal",
                "description": "b",
                "fix_type": "manual",
            },
        ]
        report = generate_report(str(tmp_path), issues, ["a.md", "b.md"], as_json=False)
        assert "FIX TYPE SUMMARY" in report
        assert "Auto-fixable" in report


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_not_a_directory(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(nonexistent)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_not_a_git_repo(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_no_doc_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / ".git").mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "No documentation files found" in captured.out

    def test_no_doc_files_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / ".git").mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--json"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_full_run_with_docs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "README.md").write_text(
            "# Test\n## Usage\n## Installation\n## License\n", encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=None,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_renamed_files", return_value=[]
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_current_version_from_git",
                return_value=None,
            ),pytest.raises(SystemExit) as exc_info
        ):
            main()
        # No high/critical issues -> exit 0
        assert exc_info.value.code == 0

    def test_full_run_json(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "README.md").write_text(
            "# Test\n## Usage\n## Installation\n## License\n", encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--json"])
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=None,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_renamed_files", return_value=[]
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_current_version_from_git",
                return_value=None,
            ),pytest.raises(SystemExit) as exc_info
        ):
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert "summary" in data

    def test_doc_patterns_arg(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
        (tmp_path / "data.txt").write_text("data", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--doc-patterns", "*.md"])
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=None,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_renamed_files", return_value=[]
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_current_version_from_git",
                return_value=None,
            ),pytest.raises(SystemExit) as exc_info
        ):
            main()
        assert exc_info.value.code == 0

    def test_min_severity_filter(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "README.md").write_text(
            "# Test\n## Usage\n## Installation\n## License\n", encoding="utf-8"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--min-severity", "critical"])
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=None,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_renamed_files", return_value=[]
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_current_version_from_git",
                return_value=None,
            ),pytest.raises(SystemExit) as exc_info
        ):
            main()
        assert exc_info.value.code == 0

    def test_non_readme_doc_no_associated_dirs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A non-README doc with no code files gets default associated_dirs=['']."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "guide.md").write_text("# Guide\n\nSome content.\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path)])
        with (
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_file_last_modified",
                return_value=None,
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_renamed_files", return_value=[]
            ),
            patch(
                "zolletta_metaskill.documentor.drift_analyzer.get_current_version_from_git",
                return_value=None,
            ),pytest.raises(SystemExit) as exc_info
        ):
            main()
        assert exc_info.value.code == 0
