"""Tests for documentation_files_finder.py."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.documentor.utils.documentation_files_finder import (
    DocumentationFilesFinder,
)


class TestDocumentationFilesFinder:
    # --- documentation.dir ---

    def test_finder_finds_markdown_under_the_default_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "how-to").mkdir(parents=True)
        (tmp_path / "docs" / "index.md").write_text("# Index")
        (tmp_path / "docs" / "how-to" / "guide.md").write_text("# Guide")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.documentation == ("docs/how-to/guide.md", "docs/index.md")

    def test_finder_honours_a_configured_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "manual").mkdir()
        (tmp_path / "manual" / "index.md").write_text("# Index")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "ignored.md").write_text("# Ignored")
        settings = {"language": "en", "documentation": {"dir": "manual"}}
        inventory = DocumentationFilesFinder.find(settings, str(tmp_path))
        assert inventory.documentation == ("manual/index.md",)

    def test_finder_keeps_only_markdown_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# Index")
        (tmp_path / "docs" / "notes.txt").write_text("notes")
        (tmp_path / "docs" / "api.rst").write_text("API")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.documentation == ("docs/index.md",)

    def test_finder_finds_every_markdown_variant_extension(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        for name in ("a.markdown", "b.mdown", "c.mkd", "d.md"):
            (tmp_path / "docs" / name).write_text("# Doc")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.documentation == (
            "docs/a.markdown",
            "docs/b.mdown",
            "docs/c.mkd",
            "docs/d.md",
        )

    def test_finder_returns_nothing_for_a_missing_docs_dir(self, tmp_path: Path) -> None:
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.documentation == ()

    # --- root documents ---

    def test_finder_finds_every_root_document_kind(self, tmp_path: Path) -> None:
        for name in ("README.md", "CONTRIBUTING.md", "AGENTS.md"):
            (tmp_path / name).write_text("# Doc")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.root_documents == {
            "agents": "AGENTS.md",
            "contributing": "CONTRIBUTING.md",
            "readme": "README.md",
        }

    def test_finder_omits_an_absent_root_document(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Readme")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.root_documents == {"readme": "README.md"}

    def test_finder_matches_a_root_document_case_insensitively(self, tmp_path: Path) -> None:
        (tmp_path / "readme.MD").write_text("# Readme")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.all_paths == ("readme.MD",)

    def test_finder_keeps_a_root_document_beside_an_empty_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Readme")
        (tmp_path / "docs").mkdir()
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.all_paths == ("README.md",)

    # --- out of scope by construction ---

    def test_finder_never_returns_skills_or_changelog_markdown(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# Index")
        (tmp_path / "skills" / "one").mkdir(parents=True)
        (tmp_path / "skills" / "one" / "SKILL.md").write_text("# Skill")
        (tmp_path / "SKILL.md").write_text("# Skill")
        (tmp_path / "CHANGELOG.md").write_text("# Changelog")
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.all_paths == ("docs/index.md",)

    # --- skipped_reason ---

    def test_finder_flags_a_configured_docs_dir_that_is_missing(self, tmp_path: Path) -> None:
        settings = {"language": "en", "documentation": {"dir": "manual"}}
        inventory = DocumentationFilesFinder.find(settings, str(tmp_path))
        assert inventory.documentation == ()
        assert inventory.skipped_reason == "documentation.dir 'manual' is not a directory"

    def test_finder_does_not_flag_a_missing_default_docs_dir(self, tmp_path: Path) -> None:
        inventory = DocumentationFilesFinder.find({"language": "en"}, str(tmp_path))
        assert inventory.skipped_reason is None

    def test_finder_does_not_flag_an_empty_configured_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        settings = {"language": "en", "documentation": {"dir": "docs"}}
        inventory = DocumentationFilesFinder.find(settings, str(tmp_path))
        assert inventory.skipped_reason is None
