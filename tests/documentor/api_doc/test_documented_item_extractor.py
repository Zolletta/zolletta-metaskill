"""Tests for documented_item_extractor.py."""

from __future__ import annotations

from pathlib import Path

from zolletta_metaskill.documentor.api_doc.documented_item_extractor import (
    DocumentedItemExtractor,
)


class TestDocumentedItemExtractor:
    """DocumentedItemExtractor pulls item references out of markdown."""

    # --- extract_documented_items ---

    def test_extract_documented_items_heading_function_returns_function(
        self, tmp_path: Path
    ) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n\nSome description.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert "foo" in items
        assert items["foo"]["kind"] == "function"

    def test_heading_function_with_params(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo(a, b)`\n\nDescription.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert "foo" in items

    def test_extract_documented_items_inline_function_contains_y(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(x, y)` for details.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert "bar" in items
        param_names = [p["name"] for p in items["bar"]["parameters"]]
        assert "x" in param_names
        assert "y" in param_names

    def test_inline_function_skips_self_cls(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(self, x)` for details.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        param_names = [p["name"] for p in items["bar"]["parameters"]]
        assert "self" not in param_names
        assert "x" in param_names

    def test_inline_function_skips_cls(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(cls, x)` for details.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert [p["name"] for p in items["bar"]["parameters"]] == ["x"]

    def test_inline_function_item_dict_shape(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("Intro line.\n\nSee `bar(x)` for details.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert items["bar"] == {
            "name": "bar",
            "line": 3,
            "kind": "function",
            "file": str(p),
            "parameters": [{"name": "x"}],
        }

    def test_inline_function_annotated_param_keeps_name(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(a: int)` for details.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert [x["name"] for x in items["bar"]["parameters"]] == ["a"]

    def test_inline_function_starred_param_kept(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("See `bar(*args)` for details.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert [x["name"] for x in items["bar"]["parameters"]] == ["*args"]

    def test_extract_documented_items_param_list_contains_b(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n\n- `a` (int): first param\n- `b` (str): second param\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert "foo" in items
        assert items["foo"]["name"] == "foo"
        assert items["foo"]["line"] == 1
        assert items["foo"]["kind"] == "function"
        assert items["foo"]["file"] == str(p)
        assert items["foo"]["parameters"] == [
            {"name": "a", "annotation": "int"},
            {"name": "b", "annotation": "str"},
        ]

    def test_heading_item_dict_shape_exact(self, tmp_path: Path) -> None:
        """The heading branch must emit the full item shape, ``parameters`` included."""
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert items == {
            "foo": {
                "name": "foo",
                "line": 1,
                "kind": "function",
                "file": str(p),
                "parameters": [],
            }
        }

    def test_multiple_headings_carry_params(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text(
            "### `foo()`\n\n- `a` (int): first param\n\n### `bar()`\n\n- `x` (str): param\n"
        )
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert "foo" in items
        assert "bar" in items
        foo_params = [p["name"] for p in items["foo"]["parameters"]]
        assert "a" in foo_params

    def test_extract_documented_items_nonexistent_file_returns_empty_dict(
        self, tmp_path: Path
    ) -> None:
        items = DocumentedItemExtractor.extract_documented_items(str(tmp_path / "nope.md"))
        assert items == {}

    def test_extract_documented_items_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.md"
        p.write_text("")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert items == {}

    # --- extract_all_documented_items ---

    def test_extract_all_documented_items_single_file_contains_foo(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("### `foo()`\n")
        items = DocumentedItemExtractor.extract_all_documented_items(str(p))
        assert "foo" in items

    def test_directory_non_recursive(self, tmp_path: Path) -> None:
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.md").write_text("### `foo()`\n")
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("### `bar()`\n")
        items = DocumentedItemExtractor.extract_all_documented_items(str(d), recursive=False)
        assert "foo" in items
        assert "bar" not in items

    def test_extract_all_documented_items_directory_defaults_non_recursive(
        self, tmp_path: Path
    ) -> None:
        d = tmp_path / "docs"
        sub = d / "sub"
        sub.mkdir(parents=True)
        (d / "a.md").write_text("### `foo()`\n")
        (sub / "b.md").write_text("### `bar()`\n")
        items = DocumentedItemExtractor.extract_all_documented_items(str(d))
        assert "foo" in items
        assert "bar" not in items

    def test_extract_all_documented_items_rst_file_non_recursive(self, tmp_path: Path) -> None:
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.rst").write_text("### `foo()`\n")
        items = DocumentedItemExtractor.extract_all_documented_items(str(d), recursive=False)
        assert "foo" in items

    def test_extract_all_documented_items_rst_file_recursive(self, tmp_path: Path) -> None:
        d = tmp_path / "docs"
        sub = d / "sub"
        sub.mkdir(parents=True)
        (sub / "b.rst").write_text("### `bar()`\n")
        items = DocumentedItemExtractor.extract_all_documented_items(str(d), recursive=True)
        assert "bar" in items

    def test_extract_all_documented_items_directory_recursive_contains_bar(
        self, tmp_path: Path
    ) -> None:
        d = tmp_path / "docs"
        d.mkdir()
        (d / "a.md").write_text("### `foo()`\n")
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("### `bar()`\n")
        items = DocumentedItemExtractor.extract_all_documented_items(str(d), recursive=True)
        assert "foo" in items
        assert "bar" in items

    def test_extract_all_documented_items_nonexistent_path_returns_empty_dict(
        self, tmp_path: Path
    ) -> None:
        items = DocumentedItemExtractor.extract_all_documented_items(str(tmp_path / "nope"))
        assert items == {}

    # --- _parse_inline_param_list ---

    def test_parse_inline_param_list_empty_string_returns_empty(self) -> None:
        """An empty parameter string yields no parameters."""
        assert DocumentedItemExtractor._parse_inline_param_list("") == []

    def test_parse_inline_param_list_skips_non_identifier_entries(self) -> None:
        """Entries that are not valid identifiers after stripping ``*`` are dropped."""
        params = DocumentedItemExtractor._parse_inline_param_list("a, *, 2bad, b=1, ...")
        assert [p["name"] for p in params] == ["a", "b"]

    def test_extract_documented_items_inline_zero_arg_function(self, tmp_path: Path) -> None:
        """A zero-argument inline reference is recorded with an empty parameter list."""
        p = tmp_path / "api.md"
        p.write_text("Call `noop()` first.\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert items["noop"]["parameters"] == []

    def test_collect_inline_funcs_duplicate_name_keeps_first(self, tmp_path: Path) -> None:
        p = tmp_path / "api.md"
        p.write_text("`foo(a)` then `foo(b)`\n")
        items = DocumentedItemExtractor.extract_documented_items(str(p))
        assert [x["name"] for x in items["foo"]["parameters"]] == ["a"]
