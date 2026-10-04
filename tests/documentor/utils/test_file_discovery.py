"""Tests for file_discovery.py."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.documentor.utils.file_discovery import FileDiscovery


class TestFileDiscovery:
    # --- _load_gitignore_patterns ---

    def test_load_gitignore_patterns_no_gitignore_returns_empty(self, tmp_path: Path) -> None:
        assert FileDiscovery._load_gitignore_patterns(str(tmp_path)) == set()

    def test_load_gitignore_patterns_simple_entries(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(".venv/\nnode_modules/\n*.pyc\n")
        patterns = FileDiscovery._load_gitignore_patterns(str(tmp_path))
        assert ".venv" in patterns
        assert "node_modules" in patterns
        assert "*.pyc" not in patterns

    def test_load_gitignore_patterns_comments_and_negations(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("# comment\n!important\nbuild/\n")
        patterns = FileDiscovery._load_gitignore_patterns(str(tmp_path))
        assert "build" in patterns
        assert "important" not in patterns

    def test_load_gitignore_patterns_nested_path_basename(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("foo/bar/\n")
        patterns = FileDiscovery._load_gitignore_patterns(str(tmp_path))
        assert "bar" in patterns

    def test_load_gitignore_patterns_oserror_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").mkdir()
        assert FileDiscovery._load_gitignore_patterns(str(tmp_path)) == set()

    # --- find_doc_files ---

    def test_find_doc_files_finds_markdown_and_rst(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "guide.rst").write_text("Test")
        files = FileDiscovery.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert "guide.rst" in files

    def test_find_doc_files_skips_directories(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test")
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "lib.md").write_text("skip")
        files = FileDiscovery.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert not any("venv" in f for f in files)

    def test_find_doc_files_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        assert FileDiscovery.find_doc_files(str(tmp_path)) == []

    def test_find_doc_files_gitignore_skip_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("secrets/\n")
        (tmp_path / "README.md").write_text("# Test")
        secrets = tmp_path / "secrets"
        secrets.mkdir()
        (secrets / "secret.md").write_text("secret")
        files = FileDiscovery.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert not any("secrets" in f for f in files)

    def test_find_doc_files_gitignore_skip_file_name(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("ignored.md\n")
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "ignored.md").write_text("# Ignored")
        files = FileDiscovery.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert "ignored.md" not in files

    def test_find_doc_files_zolletta_metaskill_skipped(self, tmp_path: Path) -> None:
        zm = tmp_path / ".zolletta-metaskill"
        zm.mkdir()
        (zm / "report.md").write_text("# Report")
        (tmp_path / "README.md").write_text("# Test")
        files = FileDiscovery.find_doc_files(str(tmp_path))
        assert "README.md" in files
        assert all(".zolletta-metaskill" not in f for f in files)

    def test_find_doc_files_patterns_take_precedence(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "guide.rst").write_text("Test")
        files = FileDiscovery.find_doc_files(str(tmp_path), patterns=["*.rst"])
        assert files == ["guide.rst"]

    # --- find_code_files ---

    def test_find_code_files_finds_python(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text("x = 1")
        (tmp_path / "doc.md").write_text("# Doc")
        files = FileDiscovery.find_code_files(str(tmp_path))
        assert "mod.py" in files
        assert "doc.md" not in files

    def test_find_code_files_scoped_to_scope(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1")
        (tmp_path / "other.py").write_text("y = 2")
        files = FileDiscovery.find_code_files(str(tmp_path), scope="src")
        assert "src/mod.py" in files or "mod.py" in files
        assert not any("other.py" in f for f in files)

    def test_find_code_files_nonexistent_scope_returns_empty(self, tmp_path: Path) -> None:
        assert FileDiscovery.find_code_files(str(tmp_path), scope="nope") == []
