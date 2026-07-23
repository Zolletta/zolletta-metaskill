"""Tests for ``scan_php_dependency_inversion`` — PHP DIP validator.

Covers ``scan_module``, ``scan_file``, ``main``, and edge cases:
empty files, syntax errors, no violations, factory exclusions, and
built-in type exclusions.

Tests that require ``tree-sitter-php`` are skipped when the optional
dependency is not installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.common.models import Finding
from zolletta_metaskill.engines.php_engine import _have_tree_sitter_php
from zolletta_metaskill.php_patterns.scan_php_dependency_inversion import (
    _is_factory,
    _is_real_dependency,
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


# ---------------------------------------------------------------------------
# Pure helper tests (no tree-sitter required)
# ---------------------------------------------------------------------------


class TestIsFactory:
    """``_is_factory`` detects Factory/Builder class names."""

    def test_factory_in_name(self) -> None:
        assert _is_factory("UserFactory") is True

    def test_builder_in_name(self) -> None:
        assert _is_factory("QueryBuilder") is True

    def test_no_match(self) -> None:
        assert _is_factory("UserService") is False

    def test_empty(self) -> None:
        assert _is_factory("") is False


class TestIsRealDependency:
    """``_is_real_dependency`` excludes PHP built-in types."""

    def test_real_class(self) -> None:
        assert _is_real_dependency("HttpClient") is True

    def test_built_in_stdClass(self) -> None:
        assert _is_real_dependency("stdClass") is False

    def test_built_in_DateTime(self) -> None:
        assert _is_real_dependency("DateTime") is False

    def test_built_in_Exception(self) -> None:
        assert _is_real_dependency("Exception") is False

    def test_scalar_array(self) -> None:
        assert _is_real_dependency("array") is False


# ---------------------------------------------------------------------------
# scan_file / scan_module tests (require tree-sitter-php)
# ---------------------------------------------------------------------------


@_skip_no_ts
class TestScanFile:
    """``scan_file`` parses a .php file and returns ``list[Finding]``."""

    def test_new_in_constructor(self, tmp_path: Path) -> None:
        """``new Dep()`` in __construct produces a DIP finding."""
        f = tmp_path / "Service.php"
        _write_php(
            f,
            "<?php\n"
            "class Service {\n"
            "    public function __construct() {\n"
            "        $this->client = new HttpClient();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].category == "dip"
        assert findings[0].severity == "medium"
        assert "HttpClient" in findings[0].description
        assert "Service" in findings[0].description
        assert "__construct" in findings[0].description

    def test_new_in_regular_method(self, tmp_path: Path) -> None:
        """``new Dep()`` in a non-constructor method is also flagged."""
        f = tmp_path / "Controller.php"
        _write_php(
            f,
            "<?php\n"
            "class Controller {\n"
            "    public function handle() {\n"
            "        $handler = new RequestHandler();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "dip"
        assert "RequestHandler" in findings[0].description
        assert "handle" in findings[0].description

    def test_multiple_new_calls(self, tmp_path: Path) -> None:
        """Multiple ``new`` calls produce multiple findings."""
        f = tmp_path / "Multi.php"
        _write_php(
            f,
            "<?php\n"
            "class Multi {\n"
            "    public function __construct() {\n"
            "        $this->a = new ServiceA();\n"
            "        $this->b = new ServiceB();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 2
        descriptions = " ".join(f.description for f in findings)
        assert "ServiceA" in descriptions
        assert "ServiceB" in descriptions

    def test_no_violation_injected_dependency(self, tmp_path: Path) -> None:
        """A class that receives deps via constructor params has no findings."""
        f = tmp_path / "GoodService.php"
        _write_php(
            f,
            "<?php\n"
            "class GoodService {\n"
            "    private HttpClient $client;\n"
            "    public function __construct(HttpClient $client) {\n"
            "        $this->client = $client;\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_factory_class_excluded(self, tmp_path: Path) -> None:
        """A class named *Factory is not flagged for ``new`` calls."""
        f = tmp_path / "UserFactory.php"
        _write_php(
            f,
            "<?php\n"
            "class UserFactory {\n"
            "    public function create() {\n"
            "        return new User();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_builder_class_excluded(self, tmp_path: Path) -> None:
        """A class named *Builder is not flagged for ``new`` calls."""
        f = tmp_path / "QueryBuilder.php"
        _write_php(
            f,
            "<?php\n"
            "class QueryBuilder {\n"
            "    public function build() {\n"
            "        return new Query();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_built_in_type_not_flagged(self, tmp_path: Path) -> None:
        """``new DateTime()`` and similar built-ins are not flagged."""
        f = tmp_path / "DateHelper.php"
        _write_php(
            f,
            "<?php\n"
            "class DateHelper {\n"
            "    public function now() {\n"
            "        return new DateTime();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert findings == []

    def test_exception_not_flagged(self, tmp_path: Path) -> None:
        """``new Exception()`` is not a DIP violation."""
        f = tmp_path / "Validator.php"
        _write_php(
            f,
            "<?php\n"
            "class Validator {\n"
            "    public function validate($data) {\n"
            "        throw new Exception('bad');\n"
            "    }\n"
            "}\n",
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
        _write_php(f, "<?php\nclass {\n    \n")
        findings = scan_file(f)
        assert findings == []

    def test_file_path_in_finding(self, tmp_path: Path) -> None:
        """The finding's file field matches the path."""
        f = tmp_path / "MyClass.php"
        _write_php(
            f,
            "<?php\n"
            "class MyClass {\n"
            "    public function __construct() {\n"
            "        $this->dep = new Dependency();\n"
            "    }\n"
            "}\n",
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

    def test_qualified_name_new(self, tmp_path: Path) -> None:
        r"""``new Namespace\Class()`` is detected."""
        f = tmp_path / "App.php"
        _write_php(
            f,
            "<?php\n"
            "class App {\n"
            "    public function __construct() {\n"
            "        $this->svc = new App\\Service();\n"
            "    }\n"
            "}\n",
        )
        findings = scan_file(f)
        assert len(findings) == 1
        assert "Service" in findings[0].description


@_skip_no_ts
class TestScanModule:
    """``scan_module`` consumes ``ModuleInfo`` and returns ``list[Finding]``."""

    def test_returns_finding_objects(self, tmp_path: Path) -> None:
        """Violations are returned as ``Finding`` dataclass instances."""
        f = tmp_path / "Service.php"
        _write_php(
            f,
            "<?php\n"
            "class Service {\n"
            "    public function __construct() {\n"
            "        $this->dep = new Dep();\n"
            "    }\n"
            "}\n",
        )
        from zolletta_metaskill.common.registry import get_engine_for_file
        from zolletta_metaskill.php_patterns.scan_php_dependency_inversion import (
            _ensure_php_engine,
        )

        _ensure_php_engine()
        engine = get_engine_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        findings = scan_module(module)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)

    def test_syntax_error_module(self, tmp_path: Path) -> None:
        """A module with ``has_syntax_error`` returns no findings."""
        f = tmp_path / "bad.php"
        _write_php(f, "<?php\nclass {\n")
        from zolletta_metaskill.common.registry import get_engine_for_file
        from zolletta_metaskill.php_patterns.scan_php_dependency_inversion import (
            _ensure_php_engine,
        )

        _ensure_php_engine()
        engine = get_engine_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        assert module.has_syntax_error
        assert scan_module(module) == []

    def test_non_php_language(self, tmp_path: Path) -> None:
        """A module with language != 'php' returns no findings."""
        from zolletta_metaskill.common.models import ModuleInfo

        module = ModuleInfo(
            path=tmp_path / "test.py",
            language="python",
            has_syntax_error=False,
        )
        assert scan_module(module) == []


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
            "<?php\nclass Good {\n"
            "    public function __construct(Dep $dep) {\n"
            "        $this->dep = $dep;\n"
            "    }\n}\n",
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
            root / "Bad.php",
            "<?php\nclass Bad {\n"
            "    public function __construct() {\n"
            "        $this->dep = new Dep();\n"
            "    }\n}\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "DIP violations" in out
        assert "Dep" in out

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
            root / "Bad.php",
            "<?php\nclass Bad {\n"
            "    public function __construct() {\n"
            "        $this->dep = new Dep();\n"
            "    }\n}\n",
        )
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "strict mode" in out
