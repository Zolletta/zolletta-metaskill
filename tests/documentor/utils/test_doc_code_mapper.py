"""Tests for DocCodeMapper."""

from __future__ import annotations

import subprocess
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
        """find_code_files skips what git ignores, so generated stubs are excluded."""
        (tmp_path / ".gitignore").write_text("generated/\n", encoding="utf-8")
        (tmp_path / "keep.py").write_text("", encoding="utf-8")
        generated = tmp_path / "generated"
        generated.mkdir()
        (generated / "stub.py").write_text("", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

        files = DocCodeMapper.find_code_files(str(tmp_path))
        assert "keep.py" in files
        assert not any("generated" in f for f in files)

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

    def test_map_docs_to_code_proximity_exact_dirs(self, tmp_path: Path) -> None:
        """Proximity mapping stores the matching directory, not a placeholder."""
        mapping = DocCodeMapper.map_docs_to_code(
            str(tmp_path), ["src/auth/README.md"], ["src/auth/login.py"]
        )
        assert mapping["src/auth/README.md"] == ["src/auth"]

    def test_map_docs_to_code_unreadable_doc_does_not_stop_others(self, tmp_path: Path) -> None:
        """A doc that fails to open must not abort content-ref mapping for the rest."""
        doc = tmp_path / "docs" / "b.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("See `x.py`.", encoding="utf-8")
        mapping = DocCodeMapper.map_docs_to_code(
            str(tmp_path), ["docs/missing.md", "docs/b.md"], ["pkg/x.py"]
        )
        assert "pkg" in mapping["docs/b.md"]

    def test_map_by_content_refs_root_level_code_not_mapped(self, tmp_path: Path) -> None:
        """A referenced code file at the repo root has no directory to map to."""
        doc = tmp_path / "docs" / "b.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("See `a.py`.", encoding="utf-8")
        mapping: dict[str, list[str]] = {"docs/b.md": []}
        DocCodeMapper._map_by_content_refs(str(tmp_path), ["docs/b.md"], ["a.py"], mapping)
        assert mapping["docs/b.md"] == []

    def test_map_docs_to_code_missing_doc_file_is_tolerated(self, tmp_path: Path) -> None:
        """map_docs_to_code skips content matching when the doc file cannot be read."""
        mapping = DocCodeMapper.map_docs_to_code(str(tmp_path), ["docs/absent.md"], [])
        assert mapping == {}

    def test_map_docs_to_code_readme_rst_and_txt(self, tmp_path: Path) -> None:
        for name in ("readme.rst", "readme.txt", "index.md"):
            doc = tmp_path / "guides" / name
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("# Docs", encoding="utf-8")
        mapping = DocCodeMapper.map_docs_to_code(
            str(tmp_path),
            ["guides/readme.rst", "guides/readme.txt", "guides/index.md"],
            [],
        )
        for doc_rel in ("guides/readme.rst", "guides/readme.txt", "guides/index.md"):
            assert "guides" in mapping[doc_rel]

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
        assert refs["links"] == {"https://example.com", "api.md"}

    def test_extract_references_external_and_anchor_links_not_files(self, tmp_path: Path) -> None:
        """http/https/mailto/anchor targets are links, never file references."""
        doc = tmp_path / "guide.md"
        doc.write_text(
            "[a](http://example.com/x) [b](https://example.com/y) "
            "[c](mailto:dev@example.com) [d](#section) [e](local.md)\n",
            encoding="utf-8",
        )
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "guide.md")
        assert refs["files"] == {"local.md"}
        for target in (
            "http://example.com/x",
            "https://example.com/y",
            "mailto:dev@example.com",
            "#section",
        ):
            assert target in refs["links"]

    def test_extract_references_anchor_suffix_stripped_from_file(self, tmp_path: Path) -> None:
        """``file.md#anchor`` records ``file.md`` — the fragment is dropped."""
        doc = tmp_path / "guide.md"
        doc.write_text("[x](docs/api.md#usage)\n", encoding="utf-8")
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "guide.md")
        assert "docs/api.md" in refs["files"]
        assert "docs/api.md#usage" not in refs["files"]

    def test_extract_references_from_doc_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """extract_references_from_doc returns empty reference sets for an unreadable doc."""
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "absent.md")
        assert refs == {"files": set(), "functions": set(), "versions": set(), "links": set()}

    def test_fenced_link_example_is_not_a_reference(self, tmp_path: Path) -> None:
        """A fenced block illustrating a link is documentation, not a reference.

        This is the false positive: the scorer reported ``link_health = 0``
        while ``link_checker`` correctly found 0 broken of 667, because only one
        of the two tracked fences.
        """
        doc = tmp_path / "guide.md"
        doc.write_text(
            "Real prose link: [api](api.md).\n"
            "\n"
            "```markdown\n"
            "Example syntax: [label](target.md)\n"
            "```\n",
            encoding="utf-8",
        )
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "guide.md")
        assert "api.md" in refs["files"]
        assert "target.md" not in refs["files"]
        assert "target.md" not in refs["links"]

    def test_fenced_code_reference_is_not_a_reference(self, tmp_path: Path) -> None:
        """A ```python block showing `import foo.py` is an example, not a reference."""
        doc = tmp_path / "guide.md"
        doc.write_text(
            "See `real.py`.\n\n```python\nimport `illustrative.py`\n```\n",
            encoding="utf-8",
        )
        refs = DocCodeMapper.extract_references_from_doc(str(tmp_path), "guide.md")
        assert "real.py" in refs["files"]
        assert "illustrative.py" not in refs["files"]
