"""Tests for liskov_substitution_scanner module."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from zolletta_metaskill.core.structs import ClassInfo, Finding, MethodInfo, ModuleInfo
from zolletta_metaskill.patterns.general.liskov_substitution_scanner import (
    LiskovSubstitutionScanner,
)


class TestBuildClassInfo:
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


class TestCheckLspViolations:
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


class TestScanModule:
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


class TestScanFile:
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


class TestMain:
    def test_main_success_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_with_violations_report_only(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self, extra):\n"
            "        return 'woof'\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "extra_required_params" in out
        assert "report-only mode" in out

    def test_main_with_violations_strict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self, extra):\n"
            "        return 'woof'\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src), "--strict"])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out

    def test_readouterr_main_skip_contains_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path), "--skip"])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_nonexistent_dir(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "/nonexistent/path/xyz"])
        rc = LiskovSubstitutionScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_empty_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text("class Foo:\n    def bar(:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_pycache_ignored(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        pycache = src / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "mod.py").write_text("class Foo:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_default_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("class Foo:\n    def bar(self):\n        return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = LiskovSubstitutionScanner.main()
        assert rc == 0

    def test_main_violation_output_contains_fix(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text(
            "class Animal:\n"
            "    def speak(self):\n"
            "        return 'sound'\n"
            "class Dog(Animal):\n"
            "    def speak(self, extra):\n"
            "        return 'woof'\n"
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Fix:" in out
        assert "extra_required_params" in out

    def test_main_new_exception_violation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "new_exceptions" in out

    def test_main_fewer_params_violation(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        monkeypatch.setattr(sys, "argv", ["prog", str(src)])
        rc = LiskovSubstitutionScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "fewer_params" in out
