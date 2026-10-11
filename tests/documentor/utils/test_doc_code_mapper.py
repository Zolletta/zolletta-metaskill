"""Tests for DocCodeMapper."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.documentor.utils.doc_code_mapper import DocCodeMapper


class TestDocCodeMapper:
    """Tests for code discovery and doc-to-code mapping."""

    # --- Code Discovery ---

    def test_find_code_files_discovers_extensions(self, tmp_path: Path) -> None:
        """find_code_files finds supported code files and ignores non-code files."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("# py", encoding="utf-8")
        (src / "util.ts").write_text("// ts", encoding="utf-8")
        (src / "notes.txt").write_text("text", encoding="utf-8")

        files = DocCodeMapper.find_code_files(str(tmp_path))
        assert "src/app.py" in files
        assert "src/util.ts" in files
        assert "src/notes.txt" not in files

    def test_find_code_files_with_scope(self, tmp_path: Path) -> None:
        """find_code_files respects directory scope parameter."""
        (tmp_path / "a.py").write_text("", encoding="utf-8")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("", encoding="utf-8")

        files = DocCodeMapper.find_code_files(str(tmp_path), scope="sub")
        assert "sub/b.py" in files
        assert "a.py" not in files

    def test_find_code_files_missing_path_returns_empty(self, tmp_path: Path) -> None:
        """find_code_files returns an empty list when the scope is not a directory."""
        assert DocCodeMapper.find_code_files(str(tmp_path), scope="does-not-exist") == []

    def test_find_code_files_respects_gitignore_entries(self, tmp_path: Path) -> None:
        """find_code_files skips directories and files listed in .gitignore."""
        (tmp_path / ".gitignore").write_text("generated/\n", encoding="utf-8")
        (tmp_path / "keep.py").write_text("", encoding="utf-8")
        generated = tmp_path / "generated"
        generated.mkdir()
        (generated / "stub.py").write_text("", encoding="utf-8")

        files = DocCodeMapper.find_code_files(str(tmp_path))
        assert "keep.py" in files
        assert not any("generated" in f for f in files)

    # --- Gitignore Parsing ---

    def test_load_gitignore_patterns_filters_and_normalizes(self, tmp_path: Path) -> None:
        """_load_gitignore_patterns keeps literal entries and normalizes paths."""
        (tmp_path / ".gitignore").write_text(
            "# a comment\n\n!important\n*.log\nbuild?\n/dist\nsrc/generated\n",
            encoding="utf-8",
        )
        patterns = DocCodeMapper._load_gitignore_patterns(str(tmp_path))
        assert patterns == {"dist", "generated"}

    def test_load_gitignore_patterns_unreadable_returns_empty(self, tmp_path: Path) -> None:
        """_load_gitignore_patterns returns an empty set when opening .gitignore fails."""
        (tmp_path / ".gitignore").mkdir()
        assert DocCodeMapper._load_gitignore_patterns(str(tmp_path)) == set()

    def test_load_gitignore_patterns_absent_returns_empty(self, tmp_path: Path) -> None:
        """_load_gitignore_patterns returns an empty set when no .gitignore exists."""
        assert DocCodeMapper._load_gitignore_patterns(str(tmp_path)) == set()

    # --- Mapping Strategies ---

    def test_map_docs_to_code_proximity(self, tmp_path: Path) -> None:
        """map_docs_to_code matches docs to code in same directory."""
        mapping = DocCodeMapper.map_docs_to_code(
            str(tmp_path), ["src/auth/README.md"], ["src/auth/login.py"]
        )
        assert "src/auth" in mapping["src/auth/README.md"]

    def test_map_docs_to_code_content_reference(self, tmp_path: Path) -> None:
        """map_docs_to_code matches docs mentioning code file names."""
        doc = tmp_path / "docs" / "setup.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("See `config.py` for settings.", encoding="utf-8")

        mapping = DocCodeMapper.map_docs_to_code(
            str(tmp_path), ["docs/setup.md"], ["src/core/config.py"]
        )
        assert "src/core" in mapping["docs/setup.md"]

    def test_map_docs_to_code_parent_directory(self, tmp_path: Path) -> None:
        """map_docs_to_code also maps a doc to the parent directory of its own dir."""
        mapping = DocCodeMapper.map_docs_to_code(
            str(tmp_path),
            ["docs/auth/README.md"],
            ["docs/auth/login.py", "docs/core/config.py", "docs/index.py"],
        )
        dirs = mapping["docs/auth/README.md"]
        assert "docs/auth" in dirs
        assert "docs" in dirs

    def test_map_docs_to_code_naming_convention(self, tmp_path: Path) -> None:
        """map_docs_to_code maps a README to its own directory by name convention."""
        readme = tmp_path / "docs" / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text("# Docs", encoding="utf-8")

        mapping = DocCodeMapper.map_docs_to_code(str(tmp_path), ["docs/README.md"], ["src/app.py"])
        assert "docs" in mapping["docs/README.md"]

    def test_map_docs_to_code_missing_doc_file_is_tolerated(self, tmp_path: Path) -> None:
        """map_docs_to_code skips content matching when the doc file cannot be read."""
        mapping = DocCodeMapper.map_docs_to_code(str(tmp_path), ["docs/absent.md"], [])
        assert mapping == {}

    # --- Reference Extraction ---

    def test_extract_references_from_doc(self, tmp_path: Path) -> None:
        """extract_references_from_doc extracts file, function, and version refs."""
        doc = tmp_path / "guide.md"
        doc.write_text(
            "Version 1.2.0.\n"
            "Call `authenticate(` before using `client.py`.\n"
            "See [docs](https://example.com) and [api](api.md).\n",
            encoding="utf-8",
        )
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "guide.md")
        assert "1.2.0" in refs["versions"]
        assert "authenticate" in refs["functions"]
        assert "client.py" in refs["files"]
        assert "api.md" in refs["files"]
        assert "https://example.com" in refs["links"]

    def test_extract_references_from_doc_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """extract_references_from_doc returns empty reference sets for an unreadable doc."""
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "absent.md")
        assert refs == {"files": set(), "functions": set(), "versions": set(), "links": set()}
