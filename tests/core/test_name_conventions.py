"""Tests for name_conventions.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from zolletta_metaskill.core.name_conventions import NameConventions


class TestNameConventions:
    # --- Tests for NameConventions.snake_to_pascal(). ---

    def test_snake_to_pascal_simple_input_returns_myclass(self) -> None:
        assert NameConventions.snake_to_pascal("my_class") == "MyClass"

    def test_snake_to_pascal_single_word_returns_cache(self) -> None:
        assert NameConventions.snake_to_pascal("cache") == "Cache"

    def test_snake_to_pascal_empty_input_returns_empty(self) -> None:
        assert NameConventions.snake_to_pascal("") == ""

    def test_snake_to_pascal_multiple_words_returns_myawesomeclass(self) -> None:
        assert NameConventions.snake_to_pascal("my_awesome_class") == "MyAwesomeClass"

    def test_snake_to_pascal_already_pascal_returns_myclass(self) -> None:
        assert NameConventions.snake_to_pascal("myclass") == "Myclass"

    def test_snake_to_pascal_leading_underscore_returns_class(self) -> None:
        assert NameConventions.snake_to_pascal("_class") == "Class"

    def test_snake_to_pascal_multi_word_returns_defaultsextractor(self) -> None:
        assert NameConventions.snake_to_pascal("defaults_extractor") == "DefaultsExtractor"

    def test_snake_to_pascal_single_word_returns_foo(self) -> None:
        assert NameConventions.snake_to_pascal("foo") == "Foo"

    # --- Tests for NameConventions.pascal_to_snake(). ---

    def test_pascal_to_snake_simple_input_returns_my_class(self) -> None:
        assert NameConventions.pascal_to_snake("MyClass") == "my_class"

    def test_pascal_to_snake_single_word_returns_cache(self) -> None:
        assert NameConventions.pascal_to_snake("Cache") == "cache"

    def test_pascal_to_snake_empty_input_returns_empty(self) -> None:
        assert NameConventions.pascal_to_snake("") == ""

    def test_pascal_to_snake_multiple_words_returns_my_awesome_class(self) -> None:
        assert NameConventions.pascal_to_snake("MyAwesomeClass") == "my_awesome_class"

    def test_pascal_to_snake_all_lower_returns_myclass(self) -> None:
        assert NameConventions.pascal_to_snake("myclass") == "myclass"

    def test_pascal_to_snake_all_upper_returns_a_b_c(self) -> None:
        assert NameConventions.pascal_to_snake("ABC") == "a_b_c"

    def test_pascal_to_snake_single_char_returns_a(self) -> None:
        assert NameConventions.pascal_to_snake("A") == "a"

    def test_pascal_to_snake_multi_word_returns_defaults_extractor(self) -> None:
        assert NameConventions.pascal_to_snake("DefaultsExtractor") == "defaults_extractor"

    # --- Tests for NameConventions.test_prefixes(). ---

    def test_test_prefixes_stem_only_returns_test_stem(self) -> None:
        assert NameConventions.test_prefixes("cache", []) == {"test_cache"}

    def test_test_prefixes_with_class_adds_snake_prefix(self) -> None:
        prefixes = NameConventions.test_prefixes("mod", ["UserService"])
        assert prefixes == {"test_mod", "test_user_service"}

    def test_test_prefixes_multiple_classes_adds_each(self) -> None:
        prefixes = NameConventions.test_prefixes("multi", ["Foo", "Bar"])
        assert prefixes == {"test_multi", "test_foo", "test_bar"}

    def test_test_prefixes_class_matching_stem_deduplicates(self) -> None:
        assert NameConventions.test_prefixes("cache", ["Cache"]) == {"test_cache"}

    def test_test_prefixes_acronym_class_inserts_underscores(self) -> None:
        prefixes = NameConventions.test_prefixes("abc", ["ABC"])
        assert prefixes == {"test_abc", "test_a_b_c"}

    # --- Tests for NameConventions.get_class_names(). ---

    def test_get_class_names_single_class_returns_single_item(self, tmp_path: Path) -> None:
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        assert NameConventions.get_class_names(f) == ["User"]

    def test_get_class_names_multiple_classes_returns_multiple_items(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        assert NameConventions.get_class_names(f) == ["Foo", "Bar"]

    def test_get_class_names_no_classes_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 1\n")
        assert NameConventions.get_class_names(f) == []

    def test_get_class_names_syntax_error_returns_empty_list(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        assert NameConventions.get_class_names(f) == []

    def test_get_class_names_nested_class_excludes_value(self, tmp_path: Path) -> None:
        """Only top-level classes are returned (engine does not walk into nested)."""
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        names = NameConventions.get_class_names(f)
        assert "Outer" in names
        # Inner is nested inside Outer — the engine only extracts top-level classes
        assert "Inner" not in names

    # --- Tests for NameConventions.auto_detect_package(). ---

    def test_auto_detect_package_with_init_returns_mypkg(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        assert NameConventions.auto_detect_package(src) == "mypkg"

    def test_auto_detect_package_without_init_falls_back(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        assert NameConventions.auto_detect_package(src) == "mypkg"

    def test_auto_detect_package_picks_first_with_init(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        (src / "aaa").mkdir(parents=True)
        (src / "bbb").mkdir(parents=True)
        (src / "bbb" / "__init__.py").write_text("")
        assert NameConventions.auto_detect_package(src) == "bbb"

    def test_auto_detect_package_no_dirs_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        assert NameConventions.auto_detect_package(src) is None

    def test_auto_detect_package_files_only_returns_none(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.py").write_text("")
        assert NameConventions.auto_detect_package(src) is None

    def test_auto_detect_package_prefers_init_dir_over_first_dir(self, tmp_path: Path) -> None:
        """A dir with ``__init__.py`` wins over an alphabetically earlier plain dir."""
        src = tmp_path / "src"
        (src / "aaa").mkdir(parents=True)
        pkg = src / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        assert NameConventions.auto_detect_package(src) == "mypkg"

    def test_auto_detect_package_init_filename_is_exact(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The probe asks for ``__init__.py`` by that exact name.

        On a case-insensitive filesystem ``(pkg / "__INIT__.PY").exists()``
        returns ``True`` anyway, so the filename casing is pinned by
        monkeypatching ``Path.exists`` to be case-strict.
        """
        src = tmp_path / "src"
        (src / "aaa").mkdir(parents=True)
        pkg = src / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        real_exists = Path.exists

        def strict_exists(self: Path) -> bool:
            return self.name == "__init__.py" and real_exists(self)

        monkeypatch.setattr(Path, "exists", strict_exists)
        assert NameConventions.auto_detect_package(src) == "mypkg"
