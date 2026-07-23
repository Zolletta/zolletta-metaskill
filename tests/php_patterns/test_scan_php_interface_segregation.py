"""Tests for ``scan_php_interface_segregation`` — PHP ISP validator.

Covers ``scan_module``, ``scan_file``, ``main``, helper functions, and
edge cases: empty files, syntax errors, no violations, implementers
detection, and custom thresholds.

Tests that require ``tree-sitter-php`` are skipped when the optional
dependency is not installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.common.models import (
    ClassInfo,
    Finding,
    MethodInfo,
    ModuleInfo,
)
from zolletta_metaskill.engines.php_engine import _have_tree_sitter_php
from zolletta_metaskill.php_patterns.scan_php_interface_segregation import (
    _find_implementers,
    _is_interface,
    main,
    scan_file,
    scan_module,
)

TS_PHP_AVAILABLE = _have_tree_sitter_php()
_skip_no_ts = pytest.mark.skipif(
    not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed"
)


def _write_php(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_method(name: str, lineno: int = 1) -> MethodInfo:
    """Create a minimal :class:`MethodInfo` for testing."""
    return MethodInfo(name=name, lineno=lineno, end_lineno=lineno)


# ---------------------------------------------------------------------------
# Pure helper tests (no tree-sitter required)
# ---------------------------------------------------------------------------


class TestIsInterface:
    """``_is_interface`` detects PHP interfaces from :class:`ClassInfo`."""

    def test_abstract_no_attributes_is_interface(self) -> None:
        cls = ClassInfo(name="Foo", lineno=1, end_lineno=10, is_abstract=True)
        assert _is_interface(cls) is True

    def test_abstract_with_attributes_is_not_interface(self) -> None:
        cls = ClassInfo(
            name="AbstractFoo",
            lineno=1,
            end_lineno=10,
            is_abstract=True,
            attributes=["x"],
        )
        assert _is_interface(cls) is False

    def test_concrete_class_is_not_interface(self) -> None:
        cls = ClassInfo(name="Foo", lineno=1, end_lineno=10, is_abstract=False)
        assert _is_interface(cls) is False

    def test_concrete_with_attributes_is_not_interface(self) -> None:
        cls = ClassInfo(
            name="Foo",
            lineno=1,
            end_lineno=10,
            is_abstract=False,
            attributes=["x"],
        )
        assert _is_interface(cls) is False


class TestFindImplementers:
    """``_find_implementers`` returns classes whose bases include the name."""

    def test_finds_implementer(self) -> None:
        interface = ClassInfo(name="IRepo", lineno=1, end_lineno=5)
        impl = ClassInfo(
            name="UserRepo",
            lineno=6,
            end_lineno=10,
            bases=["IRepo"],
        )
        result = _find_implementers("IRepo", [interface, impl])
        assert result == [impl]

    def test_no_implementers(self) -> None:
        interface = ClassInfo(name="IRepo", lineno=1, end_lineno=5)
        other = ClassInfo(name="Foo", lineno=6, end_lineno=10)
        result = _find_implementers("IRepo", [interface, other])
        assert result == []

    def test_multiple_implementers(self) -> None:
        interface = ClassInfo(name="IRepo", lineno=1, end_lineno=5)
        impl_a = ClassInfo(
            name="UserRepo", lineno=6, end_lineno=10, bases=["IRepo"]
        )
        impl_b = ClassInfo(
            name="OrderRepo", lineno=11, end_lineno=15, bases=["IRepo"]
        )
        unrelated = ClassInfo(name="Foo", lineno=16, end_lineno=20)
        result = _find_implementers("IRepo", [interface, impl_a, impl_b, unrelated])
        assert result == [impl_a, impl_b]

    def test_empty_class_list(self) -> None:
        assert _find_implementers("IRepo", []) == []


# ---------------------------------------------------------------------------
# scan_module tests (use ModuleInfo directly — no tree-sitter required)
# ---------------------------------------------------------------------------


class TestScanModule:
    """``scan_module`` consumes ``ModuleInfo`` and returns ``list[Finding]``."""

    def test_fat_interface_flagged(self, tmp_path: Path) -> None:
        """An interface with more than ``min_methods`` methods is flagged."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(8)
        ]
        cls = ClassInfo(
            name="FatInterface",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=True,
        )
        module = ModuleInfo(
            path=tmp_path / "Fat.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "isp"
        assert findings[0].severity == "low"
        assert findings[0].fix_type == "manual"
        assert "FatInterface" in findings[0].description
        assert "8 methods" in findings[0].description
        assert "threshold: 7" in findings[0].description

    def test_interface_at_threshold_not_flagged(self, tmp_path: Path) -> None:
        """An interface with exactly ``min_methods`` methods is not flagged."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(7)
        ]
        cls = ClassInfo(
            name="BorderlineInterface",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=True,
        )
        module = ModuleInfo(
            path=tmp_path / "Border.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert findings == []

    def test_interface_below_threshold_not_flagged(self, tmp_path: Path) -> None:
        """An interface with fewer than ``min_methods`` methods is not flagged."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(3)
        ]
        cls = ClassInfo(
            name="SmallInterface",
            lineno=1,
            end_lineno=10,
            methods=methods,
            is_abstract=True,
        )
        module = ModuleInfo(
            path=tmp_path / "Small.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert findings == []

    def test_concrete_class_not_flagged(self, tmp_path: Path) -> None:
        """A concrete class with many methods is not flagged."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(10)
        ]
        cls = ClassInfo(
            name="BigClass",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=False,
        )
        module = ModuleInfo(
            path=tmp_path / "Big.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert findings == []

    def test_abstract_class_with_attributes_not_flagged(self, tmp_path: Path) -> None:
        """An abstract class with attributes is not treated as an interface."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(10)
        ]
        cls = ClassInfo(
            name="AbstractBase",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=True,
            attributes=["foo"],
        )
        module = ModuleInfo(
            path=tmp_path / "Base.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert findings == []

    def test_implementers_in_description(self, tmp_path: Path) -> None:
        """The finding description includes implementer class names."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(8)
        ]
        interface = ClassInfo(
            name="FatInterface",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=True,
        )
        impl = ClassInfo(
            name="Impl",
            lineno=21,
            end_lineno=30,
            bases=["FatInterface"],
        )
        module = ModuleInfo(
            path=tmp_path / "Fat.php",
            language="php",
            classes=[interface, impl],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 1
        assert "Impl" in findings[0].description
        assert "implementers" in findings[0].description

    def test_no_implementers_no_impl_text(self, tmp_path: Path) -> None:
        """No implementers → description has no 'implementers' substring."""
        methods = [
            _make_method(f"method_{i}", lineno=i + 1) for i in range(8)
        ]
        cls = ClassInfo(
            name="FatInterface",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=True,
        )
        module = ModuleInfo(
            path=tmp_path / "Fat.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 1
        assert "implementers" not in findings[0].description

    def test_method_names_in_description(self, tmp_path: Path) -> None:
        """The finding description lists method names."""
        methods = [
            _make_method("save", lineno=2),
            _make_method("delete", lineno=3),
            _make_method("find", lineno=4),
            _make_method("all", lineno=5),
            _make_method("first", lineno=6),
            _make_method("update", lineno=7),
            _make_method("count", lineno=8),
            _make_method("exists", lineno=9),
        ]
        cls = ClassInfo(
            name="RepoInterface",
            lineno=1,
            end_lineno=20,
            methods=methods,
            is_abstract=True,
        )
        module = ModuleInfo(
            path=tmp_path / "Repo.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 1
        assert "save" in findings[0].description
        assert "delete" in findings[0].description
        assert "exists" in findings[0].description

    def test_custom_min_methods(self, tmp_path: Path) -> None:
        """A custom ``min_methods`` threshold changes which interfaces are flagged."""
        methods = [
            _make_method(f"m_{i}", lineno=i + 1) for i in range(4)
        ]
        cls = ClassInfo(
            name="Smallish",
            lineno=1,
            end_lineno=10,
            methods=methods,
            is_abstract=True,
        )
        module = ModuleInfo(
            path=tmp_path / "Smallish.php",
            language="php",
            classes=[cls],
        )
        # With min_methods=3, 4 methods > 3 → flagged
        assert len(scan_module(module, min_methods=3)) == 1
        # With min_methods=4, 4 methods is not > 4 → not flagged
        assert scan_module(module, min_methods=4) == []

    def test_multiple_fat_interfaces(self, tmp_path: Path) -> None:
        """Multiple fat interfaces produce multiple findings."""
        methods_a = [
            _make_method(f"a_{i}", lineno=i + 1) for i in range(8)
        ]
        methods_b = [
            _make_method(f"b_{i}", lineno=i + 1) for i in range(9)
        ]
        cls_a = ClassInfo(
            name="FatA", lineno=1, end_lineno=20, methods=methods_a, is_abstract=True
        )
        cls_b = ClassInfo(
            name="FatB", lineno=21, end_lineno=40, methods=methods_b, is_abstract=True
        )
        module = ModuleInfo(
            path=tmp_path / "Multi.php",
            language="php",
            classes=[cls_a, cls_b],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 2
        names = {f.description.split("'")[1] for f in findings}
        assert names == {"FatA", "FatB"}

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A module with ``has_syntax_error`` returns no findings."""
        module = ModuleInfo(
            path=tmp_path / "bad.php",
            language="php",
            has_syntax_error=True,
        )
        assert scan_module(module) == []

    def test_non_php_language_returns_empty(self, tmp_path: Path) -> None:
        """A module with language != 'php' returns no findings."""
        module = ModuleInfo(
            path=tmp_path / "test.py",
            language="python",
        )
        assert scan_module(module) == []

    def test_empty_classes(self, tmp_path: Path) -> None:
        """A module with no classes returns no findings."""
        module = ModuleInfo(
            path=tmp_path / "empty.php",
            language="php",
            classes=[],
        )
        assert scan_module(module) == []

    def test_finding_file_path(self, tmp_path: Path) -> None:
        """The finding's file field matches the module path."""
        methods = [
            _make_method(f"m_{i}", lineno=i + 1) for i in range(8)
        ]
        cls = ClassInfo(
            name="Fat", lineno=1, end_lineno=20, methods=methods, is_abstract=True
        )
        module = ModuleInfo(
            path=tmp_path / "Fat.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 1
        assert findings[0].file == str(tmp_path / "Fat.php")

    def test_finding_line_number(self, tmp_path: Path) -> None:
        """The finding's line field matches the class lineno."""
        methods = [
            _make_method(f"m_{i}", lineno=i + 5) for i in range(8)
        ]
        cls = ClassInfo(
            name="Fat", lineno=5, end_lineno=30, methods=methods, is_abstract=True
        )
        module = ModuleInfo(
            path=tmp_path / "Fat.php",
            language="php",
            classes=[cls],
        )
        findings = scan_module(module, min_methods=7)
        assert len(findings) == 1
        assert findings[0].line == 5


# ---------------------------------------------------------------------------
# scan_file tests (require tree-sitter-php)
# ---------------------------------------------------------------------------


@_skip_no_ts
class TestScanFile:
    """``scan_file`` parses a .php file and returns ``list[Finding]``."""

    def test_fat_interface_detected(self, tmp_path: Path) -> None:
        """A PHP interface with 8 methods is flagged."""
        f = tmp_path / "FatInterface.php"
        _write_php(
            f,
            "<?php\n"
            "interface FatInterface {\n"
            + "".join(
                f"    public function method_{i}();\n" for i in range(8)
            )
            + "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "isp"
        assert findings[0].severity == "low"
        assert "FatInterface" in findings[0].description
        assert "8 methods" in findings[0].description

    def test_small_interface_not_flagged(self, tmp_path: Path) -> None:
        """A PHP interface with 3 methods is not flagged."""
        f = tmp_path / "SmallInterface.php"
        _write_php(
            f,
            "<?php\n"
            "interface SmallInterface {\n"
            "    public function save();\n"
            "    public function delete();\n"
            "    public function find();\n"
            "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_custom_threshold(self, tmp_path: Path) -> None:
        """``min_methods=2`` flags an interface with 3 methods."""
        f = tmp_path / "ThreeMethods.php"
        _write_php(
            f,
            "<?php\n"
            "interface ThreeMethods {\n"
            "    public function a();\n"
            "    public function b();\n"
            "    public function c();\n"
            "}\n",
        )
        findings = scan_file(f, min_methods=2)
        assert len(findings) == 1
        assert "3 methods" in findings[0].description

    def test_implementer_detected(self, tmp_path: Path) -> None:
        """The finding description includes implementer names."""
        f = tmp_path / "WithImpl.php"
        _write_php(
            f,
            "<?php\n"
            "interface BigRepo {\n"
            + "".join(
                f"    public function m{i}();\n" for i in range(8)
            )
            + "}\n"
            "class UserRepo implements BigRepo {\n"
            + "".join(
                f"    public function m{i}() {{}}\n" for i in range(8)
            )
            + "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert "UserRepo" in findings[0].description

    def test_concrete_class_not_flagged(self, tmp_path: Path) -> None:
        """A concrete class with many methods is not flagged."""
        f = tmp_path / "BigClass.php"
        _write_php(
            f,
            "<?php\n"
            "class BigClass {\n"
            + "".join(
                f"    public function method_{i}() {{}}\n" for i in range(10)
            )
            + "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_empty_file(self, tmp_path: Path) -> None:
        """An empty .php file produces no findings."""
        f = tmp_path / "empty.php"
        _write_php(f, "<?php\n")
        findings = scan_file(f)
        assert findings == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A file with a syntax error produces no findings."""
        f = tmp_path / "broken.php"
        _write_php(f, "<?php\ninterface {\n    \n")
        findings = scan_file(f)
        assert findings == []

    def test_file_path_in_finding(self, tmp_path: Path) -> None:
        """The finding's file field matches the path."""
        f = tmp_path / "FatInterface.php"
        _write_php(
            f,
            "<?php\n"
            "interface FatInterface {\n"
            + "".join(
                f"    public function m{i}();\n" for i in range(8)
            )
            + "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].file == str(f)

    def test_no_classes(self, tmp_path: Path) -> None:
        """A file with only free functions produces no findings."""
        f = tmp_path / "functions.php"
        _write_php(
            f,
            "<?php\n"
            "function greet($name) {\n"
            "    return 'Hello, ' . $name;\n"
            "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_non_php_file_returns_empty(self, tmp_path: Path) -> None:
        """A non-.php file returns no findings (no matching engine)."""
        f = tmp_path / "script.py"
        _write_php(f, "class Foo:\n    pass\n")
        findings = scan_file(f)
        assert findings == []

    def test_multiple_fat_interfaces(self, tmp_path: Path) -> None:
        """Multiple fat interfaces in one file produce multiple findings."""
        f = tmp_path / "Multi.php"
        _write_php(
            f,
            "<?php\n"
            "interface FatA {\n"
            + "".join(
                f"    public function a{i}();\n" for i in range(8)
            )
            + "}\n"
            "interface FatB {\n"
            + "".join(
                f"    public function b{i}();\n" for i in range(9)
            )
            + "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 2


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for ``main()`` CLI entry point."""

    def test_main_skip(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--skip"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_missing_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(missing)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    @_skip_no_ts
    def test_main_all_clear(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_php(
            root / "Good.php",
            "<?php\n"
            "interface Good {\n"
            "    public function save();\n"
            "    public function find();\n"
            "}\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    @_skip_no_ts
    def test_main_violation_report_only(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_php(
            root / "Fat.php",
            "<?php\n"
            "interface Fat {\n"
            + "".join(
                f"    public function m{i}();\n" for i in range(8)
            )
            + "}\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "ISP violations" in out
        assert "Fat" in out

    @_skip_no_ts
    def test_main_strict_mode(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_php(
            root / "Fat.php",
            "<?php\n"
            "interface Fat {\n"
            + "".join(
                f"    public function m{i}();\n" for i in range(8)
            )
            + "}\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out

    @_skip_no_ts
    def test_main_custom_min_methods(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_php(
            root / "Small.php",
            "<?php\n"
            "interface Small {\n"
            "    public function a();\n"
            "    public function b();\n"
            "    public function c();\n"
            "}\n",
        )
        monkeypatch.setattr(
            sys, "argv", ["prog", str(root), "--min-methods", "2"]
        )
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "ISP violations" in out
        assert "Small" in out

    @_skip_no_ts
    def test_main_report_shows_threshold(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "src"
        root.mkdir()
        _write_php(
            root / "Good.php",
            "<?php\n"
            "interface Good {\n"
            "    public function save();\n"
            "}\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "threshold: 7" in out
