"""Tests for liskov_substitution_scanner module."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.structs import ClassInfo, Finding, MethodInfo, ModuleInfo
from zolletta_metaskill.patterns.general.liskov_substitution_scanner import (
    LiskovSubstitutionScanner,
)


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
    """Chdir into tmp_path and run main() with *argv*."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    return LiskovSubstitutionScanner.main()


_LSP_VIOLATION_SRC = (
    "class Animal:\n"
    "    def speak(self):\n"
    "        return 'sound'\n"
    "class Dog(Animal):\n"
    "    def speak(self, extra):\n"
    "        return 'woof'\n"
)


def _lsp_violation(vtype: str) -> dict[str, Any]:
    """Return a minimal violation dict for ``_emit_text`` tests."""
    return {
        "type": vtype,
        "class": "Dog",
        "method": "speak",
        "line": 5,
        "detail": "some detail",
        "parent": "Animal",
        "file": "src/dog.py",
    }


class TestLiskovSubstitutionScanner:
    # --- BuildClassInfo ---

    def test_build_class_info_simple_class_returns_1(self) -> None:
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=5,
            methods=[MethodInfo(name="bar", lineno=2, end_lineno=3, params=["a"])],
        )
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["name"] == "Foo"
        assert info["bases"] == []
        assert "bar" in info["methods"]
        assert info["methods"]["bar"]["sig"]["pos_args"] == ["a"]
        assert info["methods"]["bar"]["sig"]["required_count"] == 1

    def test_class_with_name_base(self) -> None:
        cls = ClassInfo(name="Dog", lineno=1, end_lineno=2, bases=["Animal"])
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["bases"] == ["Animal"]

    def test_class_with_attribute_base(self) -> None:
        """ModuleInfo stores fully-qualified base names.

        _build_class_info normalises them to the last component.
        """
        cls = ClassInfo(name="Dog", lineno=1, end_lineno=2, bases=["animals.Animal"])
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["bases"] == ["Animal"]

    def test_build_class_info_multiple_bases_returns_multiple_items(self) -> None:
        cls = ClassInfo(name="Dog", lineno=1, end_lineno=2, bases=["Animal", "Creature"])
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["bases"] == ["Animal", "Creature"]

    def test_method_with_raises(self) -> None:
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=5,
            methods=[
                MethodInfo(name="bar", lineno=2, end_lineno=3, raises=["ValueError"]),
            ],
        )
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["methods"]["bar"]["raised"] == {"ValueError"}

    def test_method_with_return_type(self) -> None:
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=5,
            methods=[
                MethodInfo(name="bar", lineno=2, end_lineno=3, return_type="int"),
            ],
        )
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["methods"]["bar"]["sig"]["returns_annotation"] == "int"

    def test_is_stub_always_false(self) -> None:
        """ModuleInfo does not carry stub-body info, so is_stub is always False."""
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=3,
            methods=[MethodInfo(name="bar", lineno=2, end_lineno=2)],
        )
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["methods"]["bar"]["is_stub"] is False

    def test_has_vararg_always_false(self) -> None:
        """ModuleInfo does not carry vararg info, so has_vararg is always False."""
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=3,
            methods=[MethodInfo(name="bar", lineno=2, end_lineno=2)],
        )
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["methods"]["bar"]["sig"]["has_vararg"] is False

    def test_build_class_info_sig_dict_exact_match(self) -> None:
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=5,
            methods=[MethodInfo(name="bar", lineno=2, end_lineno=3, params=["a"])],
        )
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["methods"]["bar"]["sig"] == {
            "name": "bar",
            "line": 2,
            "pos_args": ["a"],
            "required_count": 1,
            "defaults_count": 0,
            "has_vararg": False,
            "has_kwarg": False,
            "returns_annotation": None,
        }

    def test_build_class_info_top_level_dict_exact_match(self) -> None:
        cls = ClassInfo(name="Foo", lineno=7, end_lineno=9, bases=["Animal"])
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info == {
            "name": "Foo",
            "line": 7,
            "bases": ["Animal"],
            "methods": {},
        }

    def test_build_class_info_multi_dot_base_returns_last(self) -> None:
        cls = ClassInfo(name="Dog", lineno=1, end_lineno=2, bases=["a.b.Animal"])
        info = LiskovSubstitutionScanner._build_class_info(cls)
        assert info["bases"] == ["Animal"]

    # --- CheckAllViolations ---

    def test_check_all_violations_external_base_skipped(self) -> None:
        all_classes = {
            "Child": {"bases": ["ExternalBase"], "file": "c.py", "methods": {}},
        }
        assert LiskovSubstitutionScanner._check_all_violations(all_classes) == []

    def test_check_all_violations_violation_adds_parent_and_file(self) -> None:
        method = {
            "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
            "raised": set(),
            "is_stub": False,
        }
        child_method = {
            "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False, "line": 5},
            "raised": set(),
            "is_stub": False,
        }
        all_classes = {
            "Animal": {
                "name": "Animal",
                "file": "src/animal.py",
                "bases": [],
                "methods": {"speak": method},
            },
            "Dog": {
                "name": "Dog",
                "file": "src/dog.py",
                "bases": ["Animal"],
                "methods": {"speak": child_method},
            },
        }
        violations = LiskovSubstitutionScanner._check_all_violations(all_classes)
        assert violations == [
            {
                "type": "extra_required_params",
                "class": "Dog",
                "method": "speak",
                "line": 5,
                "detail": "requires 1 params, parent requires 0",
                "parent": "Animal",
                "file": "src/dog.py",
            }
        ]

    # --- CollectAllClasses ---

    def test_collect_all_classes_syntax_error_file_skipped(self, tmp_path: Path) -> None:
        EngineRegistry.ensure_python()
        (tmp_path / "a_bad.py").write_text("class Foo:\n    def bar(:\n")
        (tmp_path / "b_good.py").write_text("class Good:\n    def ok(self):\n        return 1\n")
        all_classes = LiskovSubstitutionScanner._collect_all_classes([tmp_path])
        assert set(all_classes) == {"Good"}
        assert all_classes["Good"]["file"] == "b_good.py"

    def test_collect_all_classes_none_engine_continues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        EngineRegistry.ensure_python()
        (tmp_path / "a_first.py").write_text("class First:\n    pass\n")
        (tmp_path / "b_second.py").write_text("class Second:\n    pass\n")
        original = EngineRegistry.get_for_file

        def fake_get_for_file(path: Path) -> Any:
            if path.name == "a_first.py":
                return None
            return original(path)

        monkeypatch.setattr(EngineRegistry, "get_for_file", staticmethod(fake_get_for_file))
        all_classes = LiskovSubstitutionScanner._collect_all_classes([tmp_path])
        assert set(all_classes) == {"Second"}

    # --- CheckLspViolations ---

    def test_no_override_no_violation(self) -> None:
        parent: dict[str, Any] = {
            "name": "P",
            "methods": {"foo": {"sig": {"required_count": 0}, "raised": set(), "is_stub": False}},
        }
        child: dict[str, Any] = {"name": "C", "methods": {}}
        assert LiskovSubstitutionScanner._check_lsp_violations(parent, child) == []

    def test_extra_required_params(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {
                        "required_count": 2,
                        "pos_args": ["a", "b"],
                        "has_vararg": False,
                        "line": 5,
                    },
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "extra_required_params" in types

    def test_check_lsp_violations_fewer_params_contains_fewer_params(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {
                        "required_count": 2,
                        "pos_args": ["a", "b"],
                        "has_vararg": False,
                        "line": 1,
                    },
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False, "line": 5},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "fewer_params" in types

    def test_fewer_params_with_vararg_ok(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {
                        "required_count": 2,
                        "pos_args": ["a", "b"],
                        "has_vararg": False,
                        "line": 1,
                    },
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": True, "line": 5},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "fewer_params" not in types

    def test_check_lsp_violations_new_exceptions_contains_new_exceptions(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": {"ValueError"},
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": {"ValueError", "KeyError"},
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "new_exceptions" in types

    def test_broader_exceptions_allowed(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": {"ValueError", "RuntimeError"},
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "new_exceptions" not in types

    def test_check_lsp_violations_stub_override_contains_stub_override(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": set(),
                    "is_stub": True,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "stub_override" in types

    def test_stub_when_parent_also_stub_ok(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": True,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": set(),
                    "is_stub": True,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = [v["type"] for v in violations]
        assert "stub_override" not in types

    def test_check_lsp_violations_multiple_violations_returns_set(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {
                        "required_count": 2,
                        "pos_args": ["a", "b"],
                        "has_vararg": False,
                        "line": 5,
                    },
                    "raised": {"KeyError"},
                    "is_stub": True,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        types = {v["type"] for v in violations}
        assert types == {"extra_required_params", "new_exceptions", "stub_override"}

    def test_violation_has_correct_fields(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {
                        "required_count": 1,
                        "pos_args": ["a"],
                        "has_vararg": False,
                        "line": 10,
                    },
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        v = violations[0]
        assert v["class"] == "C"
        assert v["method"] == "foo"
        assert v["line"] == 10
        assert "detail" in v

    def test_check_lsp_violations_non_override_first_reports_later(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "other": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                },
                "foo": {
                    "sig": {"required_count": 1, "pos_args": ["a"], "has_vararg": False, "line": 2},
                    "raised": set(),
                    "is_stub": False,
                },
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {
                        "required_count": 2,
                        "pos_args": ["a", "b"],
                        "has_vararg": False,
                        "line": 5,
                    },
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        assert [v["type"] for v in violations] == ["extra_required_params"]

    def test_check_lsp_violations_broad_exception_members_all_allowed(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": {"Exception", "BaseException", "TypeError"},
                    "is_stub": False,
                }
            },
        }
        assert LiskovSubstitutionScanner._check_lsp_violations(parent, child) == []

    def test_check_lsp_violations_new_exceptions_exact_detail(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": {"KeyError"},
                    "is_stub": False,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        assert violations[0]["detail"] == "raises {'KeyError'}, parent raises nothing"

    def test_check_lsp_violations_stub_override_exact_violation(self) -> None:
        parent = {
            "name": "P",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 1},
                    "raised": set(),
                    "is_stub": False,
                }
            },
        }
        child = {
            "name": "C",
            "methods": {
                "foo": {
                    "sig": {"required_count": 0, "pos_args": [], "has_vararg": False, "line": 5},
                    "raised": set(),
                    "is_stub": True,
                }
            },
        }
        violations = LiskovSubstitutionScanner._check_lsp_violations(parent, child)
        assert violations == [
            {
                "type": "stub_override",
                "class": "C",
                "method": "foo",
                "line": 5,
                "detail": "overrides with empty body (pass/return None) — weakens postcondition",
            }
        ]

    # --- ScanModule ---

    def test_moduleinfo_no_violations_returns_empty_list(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Animal",
                    lineno=1,
                    end_lineno=3,
                    methods=[MethodInfo(name="speak", lineno=2, end_lineno=3)],
                ),
            ],
        )
        results = LiskovSubstitutionScanner.scan_module(module)
        assert results == []

    def test_extra_required_params_violation(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Animal",
                    lineno=1,
                    end_lineno=3,
                    methods=[MethodInfo(name="speak", lineno=2, end_lineno=3)],
                ),
                ClassInfo(
                    name="Dog",
                    lineno=4,
                    end_lineno=6,
                    bases=["Animal"],
                    methods=[
                        MethodInfo(name="speak", lineno=5, end_lineno=6, params=["extra"]),
                    ],
                ),
            ],
        )
        results = LiskovSubstitutionScanner.scan_module(module)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].category == "lsp_violation"
        assert "extra_required_params" in results[0].description
        assert "Dog.speak" in results[0].description

    def test_scan_module_violation_returns_exact_finding(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Animal",
                    lineno=1,
                    end_lineno=3,
                    methods=[MethodInfo(name="speak", lineno=2, end_lineno=3)],
                ),
                ClassInfo(
                    name="Dog",
                    lineno=4,
                    end_lineno=6,
                    bases=["Animal"],
                    methods=[
                        MethodInfo(name="speak", lineno=5, end_lineno=6, params=["extra"]),
                    ],
                ),
            ],
        )
        results = LiskovSubstitutionScanner.scan_module(module)
        assert results == [
            Finding(
                file=str(module.path),
                line=5,
                category="lsp_violation",
                severity="high",
                description=(
                    "[extra_required_params] Dog.speak() — "
                    "requires 1 params, parent requires 0 (parent: Animal)"
                ),
                fix_type="manual",
            )
        ]

    def test_new_exceptions_violation(self, tmp_path: Path) -> None:
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Animal",
                    lineno=1,
                    end_lineno=3,
                    methods=[MethodInfo(name="speak", lineno=2, end_lineno=3)],
                ),
                ClassInfo(
                    name="Dog",
                    lineno=4,
                    end_lineno=6,
                    bases=["Animal"],
                    methods=[
                        MethodInfo(
                            name="speak",
                            lineno=5,
                            end_lineno=6,
                            raises=["KeyError"],
                        ),
                    ],
                ),
            ],
        )
        results = LiskovSubstitutionScanner.scan_module(module)
        assert len(results) == 1
        assert "new_exceptions" in results[0].description

    def test_no_violation_when_parent_not_in_module(self, tmp_path: Path) -> None:
        """If the parent class is not in the same module, no violation is reported."""
        module = ModuleInfo(
            path=tmp_path / "mod.py",
            language="python",
            classes=[
                ClassInfo(
                    name="Dog",
                    lineno=1,
                    end_lineno=3,
                    bases=["Animal"],
                    methods=[
                        MethodInfo(name="speak", lineno=2, end_lineno=3, params=["extra"]),
                    ],
                ),
            ],
        )
        results = LiskovSubstitutionScanner.scan_module(module)
        assert results == []

    # --- ScanFile ---

    def test_file_with_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self, extra):\n"
            "        return 'woof'\n"
        )
        results = LiskovSubstitutionScanner.scan_file(f)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].category == "lsp_violation"
        assert "extra_required_params" in results[0].description

    def test_file_no_violations(self, tmp_path: Path) -> None:
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    def bar(self):\n        return 1\n")
        results = LiskovSubstitutionScanner.scan_file(f)
        assert results == []

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("class Foo:\n    def bar(:\n")
        results = LiskovSubstitutionScanner.scan_file(f)
        assert results == []

    def test_non_python_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.txt"
        f.write_text("not python")
        results = LiskovSubstitutionScanner.scan_file(f)
        assert results == []

    # --- Main ---

    def test_main_success_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_with_violations_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_LSP_VIOLATION_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "extra_required_params" in out
        assert "report-only mode" in out

    def test_main_check_disabled(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_lsp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert out == "Result: SKIPPED (check_lsp disabled in settings.json)\n"

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_lsp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report == {"skipped": True, "reason": "check_lsp disabled in settings.json"}

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert err == "Error: no configured source directories exist on disk\n"

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_json_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_LSP_VIOLATION_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] >= 1
        assert report["violations"][0]["type"] == "extra_required_params"
        assert report["directories"] == ["src"]

    def test_main_json_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    pass\n")
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["violation_count"] == 0

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def bar(:\n")
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_gitignored_dirs_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("src/ignored/\n")
        _write_settings(tmp_path)
        ignored = tmp_path / "src" / "ignored"
        ignored.mkdir(parents=True)
        (ignored / "mod.py").write_text(_LSP_VIOLATION_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_violation_output_contains_fix(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(_LSP_VIOLATION_SRC)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fix:" in out
        assert "extra_required_params" in out

    def test_main_new_exception_violation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self):\n"
            "        raise KeyError('x')\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "new_exceptions" in out

    def test_main_fewer_params_violation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self, volume):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self):\n"
            "        return 'woof'\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "fewer_params" in out

    def test_main_multiple_roots(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cross-root violations: parent in one root, child in another."""
        _write_settings(tmp_path, python={"paths": {"source": ["src", "lib"]}})
        src = tmp_path / "src"
        lib = tmp_path / "lib"
        src.mkdir()
        lib.mkdir()
        (src / "animal.py").write_text("class Animal:\n    def speak(self):\n        return 's'\n")
        (lib / "dog.py").write_text(
            "class Dog(Animal):\n    def speak(self, extra):\n        return 'w'\n"
        )
        rc = _run(tmp_path, monkeypatch, ["prog"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "extra_required_params" in out

    # --- EmitJson ---

    def test_emit_json_exact_serialization(self, capsys: pytest.CaptureFixture[str]) -> None:
        violations: list[dict[str, Any]] = [
            {"type": "new_exceptions", "extra": {"KeyError"}},
        ]
        LiskovSubstitutionScanner._emit_json([Path("src")], violations)
        out = capsys.readouterr().out
        expected = (
            json.dumps(
                {
                    "directories": ["src"],
                    "violation_count": 1,
                    "violations": violations,
                },
                indent=2,
                default=str,
            )
            + "\n"
        )
        assert out == expected

    # --- EmitText ---

    def test_emit_text_fewer_params_exact_fix_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        LiskovSubstitutionScanner._emit_text([_lsp_violation("fewer_params")])
        lines = capsys.readouterr().out.splitlines()
        assert "    Fix: accept *args/**kwargs to maintain substitutability" in lines

    def test_emit_text_new_exceptions_exact_fix_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        LiskovSubstitutionScanner._emit_text([_lsp_violation("new_exceptions")])
        lines = capsys.readouterr().out.splitlines()
        assert "    Fix: catch and wrap new exceptions, or declare them in the parent" in lines

    def test_emit_text_stub_override_exact_fix_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        LiskovSubstitutionScanner._emit_text([_lsp_violation("stub_override")])
        lines = capsys.readouterr().out.splitlines()
        assert (
            "    Fix: don't override if the method doesn't apply — reconsider the hierarchy"
            in lines
        )

    def test_emit_text_unknown_type_default_fix_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        LiskovSubstitutionScanner._emit_text([_lsp_violation("some_other_type")])
        lines = capsys.readouterr().out.splitlines()
        assert "    Fix: review the override" in lines

    def test_emit_text_no_violations_exact_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        LiskovSubstitutionScanner._emit_text([])
        out = capsys.readouterr().out
        assert out.splitlines() == [
            "=" * 70,
            "LISKOV SUBSTITUTION (LSP) — VALIDATION REPORT",
            "=" * 70,
            "",
            "## LSP violations: none",
            "",
            "Result: all clear",
        ]

    # --- Text contract ---

    def test_emit_text_matches_committed_contract(
        self,
        capsys: pytest.CaptureFixture[str],
        text_contract: Callable[[str, str], None],
    ) -> None:
        """The captured text report is a byte-for-byte contract.

        Do not loosen this assertion: it pins the exact text output. A
        legitimate change is ``pytest --update-fixtures`` plus a reviewed
        diff, never a hand-edit or a weaker matcher.
        """
        violations = [
            {
                "type": "extra_required_params",
                "class": "Dog",
                "method": "speak",
                "line": 5,
                "detail": "requires 2 params, parent requires 1",
                "parent": "Animal",
                "file": "src/animal.py",
            },
        ]
        LiskovSubstitutionScanner._emit_text(violations)
        text_contract("patterns/general/liskov_substitution_scanner.txt", capsys.readouterr().out)
