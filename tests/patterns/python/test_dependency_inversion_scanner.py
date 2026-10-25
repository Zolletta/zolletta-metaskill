"""Tests for dependency_inversion_scanner module."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from zolletta_metaskill.patterns.python.dependency_inversion_scanner import (
    DependencyInversionScanner,
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


def _write_settings(dirpath: Path, **overrides: object) -> Path:
    """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
    settings: dict[str, object] = {
        "language": "python",
        "python": {
            "patterns": {},
            "paths": {"source": ["src"], "tests": ["tests"], "package": "mypkg"},
        },
        "php": None,
    }
    python_overrides = overrides.pop("python", None)
    if isinstance(python_overrides, dict):
        base_python = settings["python"]
        assert isinstance(base_python, dict)
        for key, value in python_overrides.items():
            if isinstance(value, dict) and isinstance(base_python.get(key), dict):
                base_python[key].update(value)
            else:
                base_python[key] = value
    settings.update(overrides)
    meta = dirpath / ".zolletta-metaskill"
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / "settings.json"
    path.write_text(json.dumps(settings))
    return path


def test_write_settings_replaces_non_dict_python_value(tmp_path: Path) -> None:
    """A non-dict ``python`` override value replaces the base value."""
    path = _write_settings(tmp_path, python={"tools": "none"})
    written = json.loads(path.read_text())
    python = written["python"]
    assert isinstance(python, dict)
    assert python["tools"] == "none"


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    return DependencyInversionScanner.main()


class TestDependencyInversionScanner:
    # --- IsDataClass ---

    def test_parse_class_dataclass_decorator_returns_true(self) -> None:
        node = _parse_class(
            "from dataclasses import dataclass\n@dataclass\nclass Foo:\n    x: int\n"
        )
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_dataclass_call_decorator(self) -> None:
        node = _parse_class("@dataclass(frozen=True)\nclass Foo:\n    x: int\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_named_tuple_base(self) -> None:
        node = _parse_class("class Foo(NamedTuple):\n    x: int\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_typed_dict_base(self) -> None:
        node = _parse_class("class Foo(TypedDict):\n    x: int\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_parse_class_enum_base_returns_true(self) -> None:
        node = _parse_class("class Foo(Enum):\n    A = 1\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_int_enum_base(self) -> None:
        node = _parse_class("class Foo(IntEnum):\n    A = 1\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_parse_class_flag_base_returns_true(self) -> None:
        node = _parse_class("class Foo(Flag):\n    A = 1\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_int_flag_base(self) -> None:
        node = _parse_class("class Foo(IntFlag):\n    A = 1\n")
        assert DependencyInversionScanner._is_data_class(node) is True

    def test_not_data_class(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self):\n        pass\n")
        assert DependencyInversionScanner._is_data_class(node) is False

    def test_attribute_base_not_data_class(self) -> None:
        node = _parse_class("class Foo(mod.Base):\n    pass\n")
        assert DependencyInversionScanner._is_data_class(node) is False

    def test_regular_name_base_not_data_class(self) -> None:
        node = _parse_class("class Foo(SomeBase):\n    pass\n")
        assert DependencyInversionScanner._is_data_class(node) is False

    def test_parse_class_regular_decorator_returns_false(self) -> None:
        node = _parse_class("@property\nclass Foo:\n    pass\n")
        assert DependencyInversionScanner._is_data_class(node) is False

    # --- IsFactory ---

    def test_factory_in_name(self) -> None:
        assert DependencyInversionScanner._is_factory("ServiceFactory") is True

    def test_builder_in_name(self) -> None:
        assert DependencyInversionScanner._is_factory("ServiceBuilder") is True

    def test_is_factory_not_factory_returns_false(self) -> None:
        assert DependencyInversionScanner._is_factory("Service") is False

    def test_is_factory_empty_name_returns_false(self) -> None:
        assert DependencyInversionScanner._is_factory("") is False

    # --- IsEntryPoint ---

    def test_is_entry_point_main_file_returns_true(self) -> None:
        assert DependencyInversionScanner._is_entry_point("main.py", {"main", "cli"}) is True

    def test_is_entry_point_cli_file_returns_true(self) -> None:
        assert DependencyInversionScanner._is_entry_point("cli.py", {"main", "cli"}) is True

    def test_is_entry_point_app_file_returns_true(self) -> None:
        assert DependencyInversionScanner._is_entry_point("app.py", {"app"}) is True

    def test_non_entry_point(self) -> None:
        assert DependencyInversionScanner._is_entry_point("service.py", {"main", "cli"}) is False

    def test_is_entry_point_partial_match_returns_true(self) -> None:
        assert DependencyInversionScanner._is_entry_point("my_main.py", {"main"}) is True

    def test_is_entry_point_no_extension_returns_true(self) -> None:
        assert DependencyInversionScanner._is_entry_point("main", {"main"}) is True

    def test_is_entry_point_empty_patterns_returns_false(self) -> None:
        assert DependencyInversionScanner._is_entry_point("main.py", set()) is False

    def test_is_entry_point_pattern_spanning_suffix_returns_false(self) -> None:
        """A ``.py``-suffixed pattern never matches (the suffix is stripped first)."""
        assert DependencyInversionScanner._is_entry_point("main.py", {"main.py"}) is False

    def test_is_entry_point_suffix_replaced_with_text_returns_false(self) -> None:
        """Stripping ``.py`` must not leave replacement text a pattern could match."""
        assert DependencyInversionScanner._is_entry_point("main.py", {"XXXX"}) is False

    # --- IsCompositionRoot ---

    def test_make_container_call(self) -> None:
        node = _parse_class("class App:\n    def setup(self):\n        self.c = make_container()\n")
        assert DependencyInversionScanner._is_composition_root(node) is True

    def test_parse_class_container_call_returns_true(self) -> None:
        node = _parse_class("class App:\n    def setup(self):\n        self.c = Container()\n")
        assert DependencyInversionScanner._is_composition_root(node) is True

    def test_attribute_container_call(self) -> None:
        node = _parse_class(
            "class App:\n    def setup(self):\n        self.c = di.make_container()\n"
        )
        assert DependencyInversionScanner._is_composition_root(node) is True

    def test_not_composition_root(self) -> None:
        node = _parse_class("class Service:\n    def __init__(self):\n        self.x = 1\n")
        assert DependencyInversionScanner._is_composition_root(node) is False

    def test_create_container_call(self) -> None:
        node = _parse_class("class App:\n    def setup(self):\n        c = create_container()\n")
        assert DependencyInversionScanner._is_composition_root(node) is True

    # --- ExtractCreatedDependencies ---

    def test_self_assignment_with_call(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["created"] == "GitLabClient"
        assert deps[0]["attribute"] == "client"
        assert deps[0]["method"] == "__init__"

    def test_extract_created_dependencies_self_only_seam_not_flagged(self) -> None:
        """A local bound to a ``self.<attr>`` expression alone is an injection seam."""
        source = (
            "class Engine:\n"
            "    def _get_parser(self):\n"
            "        factory = self._parser_factory\n"
            "        self._parser = factory()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert deps == []

    def test_extract_created_dependencies_multi_target_assign_flags_self(self) -> None:
        """A non-self target in a multi-target assign must not hide the self target."""
        source = (
            "class Service:\n"
            "    def __init__(self):\n"
            "        other = self.client = GitLabClient()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["attribute"] == "client"

    def test_extract_created_dependencies_seam_local_not_flagged(self) -> None:
        source = (
            "class Engine:\n"
            "    def _get_parser(self):\n"
            "        factory = self._parser_factory or Engine._default_factory\n"
            "        self._parser = factory()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 0

    def test_extract_created_dependencies_plain_local_still_flagged(self) -> None:
        source = (
            "class Service:\n"
            "    def run(self):\n"
            "        factory = make_factory()\n"
            "        self.client = factory()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["created"] == "factory"

    def test_parse_class_multiple_deps_returns_2(self) -> None:
        source = (
            "class Service:\n"
            "    def __init__(self):\n"
            "        self.client = GitLabClient()\n"
            "        self.repo = Repository()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 2

    def test_stdlib_not_flagged(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.items = list()\n"
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 0

    def test_non_function_body_items_skipped(self) -> None:
        source = (
            "class Service:\n"
            "    registry = GitLabClient()\n"
            "    def __init__(self):\n"
            "        self.client = GitLabClient()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["method"] == "__init__"

    def test_mock_not_flagged(self) -> None:
        source = "class TestService:\n    def setUp(self):\n        self.mock = Mock()\n"
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 0

    def test_non_self_assignment_ignored(self) -> None:
        source = (
            "class Service:\n    def __init__(self, client):\n        client = GitLabClient()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 0

    def test_non_call_assignment_ignored(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.x = 42\n"
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 0

    def test_extract_created_dependencies_attribute_call_capitalized(self) -> None:
        source = (
            "class Service:\n    def __init__(self):\n        self.client = module.GitLabClient()\n"
        )
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["created"] == "GitLabClient"

    def test_attribute_call_lowercase_ignored(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.x = module.create()\n"
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 0

    def test_method_not_init(self) -> None:
        source = "class Service:\n    def setup(self):\n        self.client = GitLabClient()\n"
        node = _parse_class(source)
        deps = DependencyInversionScanner._extract_created_dependencies(node)
        assert len(deps) == 1
        assert deps[0]["method"] == "setup"

    # --- GetClassNameFromCall ---

    def test_parse_call_name_call_returns_gitlabclient(self) -> None:
        call = _parse_call("GitLabClient()")
        assert DependencyInversionScanner._get_class_name_from_call(call) == "GitLabClient"

    def test_get_class_name_from_call_attribute_call_capitalized(self) -> None:
        call = _parse_call("module.GitLabClient()")
        assert DependencyInversionScanner._get_class_name_from_call(call) == "GitLabClient"

    def test_attribute_call_lowercase(self) -> None:
        call = _parse_call("module.create()")
        assert DependencyInversionScanner._get_class_name_from_call(call) is None

    def test_other_node_type(self) -> None:
        """Call with a func that is neither Name nor Attribute (e.g. Subscript)."""
        call = _parse_call("d['key']()")
        assert DependencyInversionScanner._get_class_name_from_call(call) is None

    # --- IsRealDependency ---

    def test_is_real_dependency_real_dependency_returns_true(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("GitLabClient") is True

    def test_is_real_dependency_stdlib_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("list") is False

    def test_is_real_dependency_dict_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("dict") is False

    def test_is_real_dependency_path_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("Path") is False

    def test_is_real_dependency_mock_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("Mock") is False

    def test_is_real_dependency_magicmock_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("MagicMock") is False

    def test_is_real_dependency_patch_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("patch") is False

    def test_property_mock_type(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("PropertyMock") is False

    def test_is_real_dependency_set_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("set") is False

    def test_is_real_dependency_tuple_type_returns_false(self) -> None:
        assert DependencyInversionScanner._is_real_dependency("tuple") is False

    # --- GetConstructorParams ---

    def test_parse_class_with_init_returns_set(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self, a, b):\n        pass\n")
        params = DependencyInversionScanner._get_constructor_params(node)
        assert params == {"a", "b"}

    def test_parse_class_no_init_returns_params(self) -> None:
        node = _parse_class("class Foo:\n    pass\n")
        params = DependencyInversionScanner._get_constructor_params(node)
        assert params == set()

    def test_init_with_defaults(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self, a, b=1):\n        pass\n")
        params = DependencyInversionScanner._get_constructor_params(node)
        assert params == {"a", "b"}

    def test_init_only_self(self) -> None:
        node = _parse_class("class Foo:\n    def __init__(self):\n        pass\n")
        params = DependencyInversionScanner._get_constructor_params(node)
        assert params == set()

    # --- ScanClass ---

    def test_scan_class_partial_init_match_keeps_later_violations(self) -> None:
        """An injected param must skip only its own violation, not the rest."""
        source = (
            "class Service:\n"
            "    def __init__(self, GitLabClient):\n"
            "        self.client = GitLabClient()\n"
            "        self.repo = Repository()\n"
        )
        node = _parse_class(source)
        violations = DependencyInversionScanner._scan_class(node, "pkg/service.py")
        assert [v["created"] for v in violations] == ["Repository"]

    def test_scan_class_attaches_rel_path_as_file(self) -> None:
        source = "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        node = _parse_class(source)
        violations = DependencyInversionScanner._scan_class(node, "pkg/service.py")
        assert violations[0]["file"] == "pkg/service.py"

    # --- Main ---

    def test_main_no_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Foo:\n    def __init__(self, client):\n        self.client = client\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_with_violations(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "GitLabClient" in out
        assert "report-only" in out
        assert "Files scanned: 1  |  Skipped (entry points): 0" in out.splitlines()

    def test_main_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        payload = json.loads(out)
        assert payload == {
            "directories": ["src"],
            "scanned_files": 1,
            "skipped_files": 0,
            "violation_count": 1,
            "violations": [
                {
                    "class": "Service",
                    "created": "GitLabClient",
                    "attribute": "client",
                    "method": "__init__",
                    "line": 3,
                    "file": "mod.py",
                }
            ],
        }
        assert out == json.dumps(payload, indent=2) + "\n"

    def test_main_skipped_when_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_dip": False}})
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert out == "Result: SKIPPED (check_dip disabled in settings.json)\n"

    def test_main_skipped_json_when_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_dip": False}})
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        assert json.loads(out)["skipped"] is True

    def test_main_no_source_dirs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert err == "Error: no configured source directories exist on disk\n"

    def test_main_skips_entry_points(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text(
            "class App:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
        assert "Skipped (entry points): 1" in out

    def test_main_skips_data_classes(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "from dataclasses import dataclass\n@dataclass\nclass Config:\n    x: int = 0\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_skips_factory_classes(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class ServiceFactory:\n    def create(self):\n        self.x = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_skips_composition_root(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class App:\n    def __init__(self):\n        self.c = make_container()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_custom_entry_points(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"dip_entry_points": ["custom_entry"]}})
        src = tmp_path / "src"
        src.mkdir()
        (src / "custom_entry.py").write_text(
            "class App:\n    def __init__(self):\n            self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Skipped (entry points): 1" in out

    def test_main_skips_init_files(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def (:\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_dep_already_injected(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n"
            "    def __init__(self, GitLabClient):\n"
            "        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_gitignore_aware(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        ignored = src / "ignored.py"
        ignored.write_text(
            "class Other:\n    def __init__(self):\n        self.dep = OtherClient()\n"
        )
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["violation_count"] == 1

    def test_main_custom_source_root(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"paths": {"source": ["lib"]}})
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["violation_count"] == 1
        assert payload["violations"][0]["file"] == "mod.py"

    def test_main_skips_multiple_entry_points(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "cli.py").write_text("class CliApp:\n    pass\n")
        (src / "main.py").write_text("class MainApp:\n    pass\n")
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["skipped_files"] == 2
        assert payload["violation_count"] == 1

    def test_main_counts_multiple_scanned_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("class A:\n    pass\n")
        (src / "b.py").write_text("class B:\n    pass\n")
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["scanned_files"] == 2

    def test_main_scans_files_after_init(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text("class Init:\n    pass\n")
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["violation_count"] == 1

    def test_main_scans_files_after_syntax_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def (:\n")
        (src / "mod.py").write_text(
            "class Service:\n    def __init__(self):\n        self.client = GitLabClient()\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["violation_count"] == 1

    # --- Text Output Contract ---

    def test_emit_text_matches_committed_contract(
        self,
        capsys: pytest.CaptureFixture[str],
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The captured text report is a byte-for-byte contract.

        The comparison is exact on purpose and must not be loosened to a
        substring or regex check: a legitimate change to the rendered report is
        ``pytest --update-fixtures`` followed by a reviewed diff.

        """
        violations = [
            {
                "class": "Service",
                "created": "GitLabClient",
                "attribute": "client",
                "method": "__init__",
                "line": 4,
                "file": "pkg/service.py",
            }
        ]
        DependencyInversionScanner._emit_text(violations, 3, 1)
        text_contract(
            "patterns/python/dependency_inversion_scanner.txt",
            capsys.readouterr().out,
        )

    def test_emit_text_no_violations_exact_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        DependencyInversionScanner._emit_text([], 2, 1)
        assert capsys.readouterr().out.splitlines() == [
            "=" * 70,
            "DEPENDENCY INVERSION — VALIDATION REPORT",
            "=" * 70,
            "",
            "Files scanned: 2  |  Skipped (entry points): 1",
            "",
            "## Dependencies created internally instead of injected: none",
            "",
            "Result: all clear",
        ]
