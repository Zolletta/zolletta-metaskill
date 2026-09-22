"""Tests for liskov_substitution_scanner module."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

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
        assert "SKIPPED" in out

    def test_main_check_disabled_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path, python={"patterns": {"check_lsp": False}})
        (tmp_path / "src").mkdir()
        rc = _run(tmp_path, monkeypatch, ["prog", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["skipped"] is True

    def test_main_missing_src(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_settings(tmp_path)
        rc = _run(tmp_path, monkeypatch, ["prog"])
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

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
