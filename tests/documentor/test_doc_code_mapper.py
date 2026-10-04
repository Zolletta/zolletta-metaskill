"""Tests for DocCodeMapper."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.documentor.doc_code_mapper import DocCodeMapper


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
