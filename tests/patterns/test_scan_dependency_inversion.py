"""Tests for scan_dependency_inversion module."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.patterns.scan_dependency_inversion import (
    _extract_created_dependencies,
    _get_class_name_from_call,
    _get_constructor_params,
    _is_composition_root,
    _is_data_class,
    _is_entry_point,
    _is_factory,
    _is_real_dependency,
    main,
)


def _parse_class(source: str) -> ast.ClassDef:
    """Parse source and return the first ClassDef."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            return node
    raise AssertionError("No class found in source")  # pragma: no cover


def _parse_call(source: str) -> ast.Call:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            return node
    raise AssertionError("No Call found in source")  # pragma: no cover


class TestIsDataClass:
    def test_dataclass_decorator(self) -> None:
        node = _parse_class(
            "from dataclasses import dataclass\n@dataclass\nclass Foo:\n    x: int\n"
        )
        assert _is_data_class(node) is True

    def test_dataclass_call_decorator(self) -> None:
        node = _parse_class("@dataclass(frozen=True)\nclass Foo:\n    x: int\n")
        assert _is_data_class(node) is True

    def test_named_tuple_base(self) -> None:
        node = _parse_class("class Foo(NamedTuple):\n    x: int\n")
        assert _is_data_class(node) is True

    def test_typed_dict_base(self) -> None:
        node = _parse_class("class Foo(TypedDict):\n    x: int\n")
        assert _is_data_class(node) is True

    def test_enum_base(self) -> None:
        node = _parse_class("class Foo(Enum):\n    A = 1\n")
        assert _is_data_class(node) is True

    def test_int_enum_base(self) -> None:
        node = _parse_class("class Foo(IntEnum):\n    A = 1\n")
        assert _is_data_class(node) is True

    def test_flag_base(self) -> None:
        node = _parse_class("class Foo(Flag):\n    A = 1\n")
        assert _is_data_class(node) is True

    def test_int_flag_base(self) -> None:
        node = _parse_class("class Foo(IntFlag):\n    A = 1\n")
        assert _is_data_class(node) is True

    def test_not_data_class(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self):\n        pass\n")
        assert _is_data_class(node) is False

    def test_regular_decorator(self) -> None:
        node = _parse_class("@property\nclass Foo:\n    pass\n")
        assert _is_data_class(node) is False


class TestIsFactory:
    def test_factory_in_name(self) -> None:
        assert _is_factory("ServiceFactory") is True

    def test_builder_in_name(self) -> None:
        assert _is_factory("ServiceBuilder") is True

    def test_not_factory(self) -> None:
        assert _is_factory("Service") is False

    def test_empty_name(self) -> None:
        assert _is_factory("") is False


class TestIsEntryPoint:
    def test_main_file(self) -> None:
        assert _is_entry_point("main.py", {"main", "cli"}) is True

    def test_cli_file(self) -> None:
        assert _is_entry_point("cli.py", {"main", "cli"}) is True

    def test_app_file(self) -> None:
        assert _is_entry_point("app.py", {"app"}) is True

    def test_non_entry_point(self) -> None:
        assert _is_entry_point("service.py", {"main", "cli"}) is False

    def test_partial_match(self) -> None:
        assert _is_entry_point("my_main.py", {"main"}) is True

    def test_no_extension(self) -> None:
        assert _is_entry_point("main", {"main"}) is True

    def test_empty_patterns(self) -> None:
        assert _is_entry_point("main.py", set()) is False


class TestIsCompositionRoot:
    def test_make_container_call(self) -> None:
        node = _parse_class("class App:\n    def setup(self):\n        self.c = make_container()\n")
        assert _is_composition_root(node) is True

    def test_container_call(self) -> None:
        node = _parse_class("class App:\n    def setup(self):\n        self.c = Container()\n")
        assert _is_composition_root(node) is True

    def test_attribute_container_call(self) -> None:
        node = _parse_class(
            "class App:\n    def setup(self):\n        self.c = di.make_container()\n"
        )
        assert _is_composition_root(node) is True

    def test_not_composition_root(self) -> None:
        node = _parse_class("class Service:\n    def __init__(self):\n        self.x = 1\n")
        assert _is_composition_root(node) is False

    def test_create_container_call(self) -> None:
        node = _parse_class("class App:\n    def setup(self):\n        c = create_container()\n")
        assert _is_composition_root(node) is True


class TestExtractCreatedDependencies:
    def test_self_assignment_with_call(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["created"] == "GitLabClient"
        assert deps[0]["attribute"] == "client"
        assert deps[0]["method"] == "__init__"

    def test_multiple_deps(self) -> None:
        source = (
            "class Service:\n"
            "    def __init__(self):\n"
            "        self.client = GitLabClient()\n"
            "        self.repo = Repository()\n"
        )
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 2

    def test_stdlib_not_flagged(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.items = list()\n"
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 0

    def test_mock_not_flagged(self) -> None:
        source = "class TestService:\n    def setUp(self):\n        self.mock = Mock()\n"
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 0

    def test_non_self_assignment_ignored(self) -> None:
        source = (
            "class Service:\n    def __init__(self, client):\n"
            "        client = GitLabClient()\n"
        )
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 0

    def test_non_call_assignment_ignored(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.x = 42\n"
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 0

    def test_attribute_call_capitalized(self) -> None:
        source = (
            "class Service:\n    def __init__(self):\n"
            "        self.client = module.GitLabClient()\n"
        )
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["created"] == "GitLabClient"

    def test_attribute_call_lowercase_ignored(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.x = module.create()\n"
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 0

    def test_method_not_init(self) -> None:
        source = "class Service:\n    def setup(self):\n        self.client = GitLabClient()\n"
        node = _parse_class(source)
        deps = _extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["method"] == "setup"


class TestGetClassNameFromCall:
    def test_name_call(self) -> None:
        call = _parse_call("GitLabClient()")
        assert _get_class_name_from_call(call) == "GitLabClient"

    def test_attribute_call_capitalized(self) -> None:
        call = _parse_call("module.GitLabClient()")
        assert _get_class_name_from_call(call) == "GitLabClient"

    def test_attribute_call_lowercase(self) -> None:
        call = _parse_call("module.create()")
        assert _get_class_name_from_call(call) is None

    def test_other_node_type(self) -> None:
        """Call with a func that is neither Name nor Attribute (e.g. Subscript)."""
        call = _parse_call("d['key']()")
        assert _get_class_name_from_call(call) is None


class TestIsRealDependency:
    def test_real_dependency(self) -> None:
        assert _is_real_dependency("GitLabClient") is True

    def test_stdlib_type(self) -> None:
        assert _is_real_dependency("list") is False

    def test_dict_type(self) -> None:
        assert _is_real_dependency("dict") is False

    def test_path_type(self) -> None:
        assert _is_real_dependency("Path") is False

    def test_mock_type(self) -> None:
        assert _is_real_dependency("Mock") is False

    def test_magicmock_type(self) -> None:
        assert _is_real_dependency("MagicMock") is False

    def test_patch_type(self) -> None:
        assert _is_real_dependency("patch") is False

    def test_property_mock_type(self) -> None:
        assert _is_real_dependency("PropertyMock") is False

    def test_set_type(self) -> None:
        assert _is_real_dependency("set") is False

    def test_tuple_type(self) -> None:
        assert _is_real_dependency("tuple") is False


class TestGetConstructorParams:
    def test_with_init(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self, a, b):\n        pass\n")
        params = _get_constructor_params(node)
        assert params == {"a", "b"}

    def test_no_init(self) -> None:
        node = _parse_class("class Foo:\n    pass\n")
        params = _get_constructor_params(node)
        assert params == set()

    def test_init_with_defaults(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self, a, b=1):\n        pass\n")
        params = _get_constructor_params(node)
        assert params == {"a", "b"}

    def test_init_only_self(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self):\n        pass\n")
        params = _get_constructor_params(node)
        assert params == set()


class TestMain:
    def test_main_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Foo:\n    def __init__(self, client):\n"
            "        self.client = client\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "GitLabClient" in out
        assert "report-only" in out

    def test_main_strict_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out

    def test_main_skip(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "src", "--skip"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_skips_entry_points(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text(
            "class App:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "Skipped (entry points): 1" in out

    def test_main_skips_data_classes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "from dataclasses import dataclass\n@dataclass\nclass Config:\n    x: int = 0\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_skips_factory_classes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class ServiceFactory:\n    def create(self):\n        self.x = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_skips_composition_root(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class App:\n    def __init__(self):\n        self.c = make_container()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_custom_entry_points(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "custom_entry.py").write_text(
            "class App:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--entry-points", "custom_entry"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_skips_init_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_skips_pycache(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        pycache = src / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def (:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = main()
        assert rc == 0

    def test_main_dep_already_injected(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n"
            "    def __init__(self, GitLabClient):\n"
            "        self.client = GitLabClient()\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
