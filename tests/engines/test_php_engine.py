"""Tests for :class:`zolletta_metaskill.engines.php_engine.PHPEngine`."""

from __future__ import annotations

from pathlib import Path

import pytest

from zolletta_metaskill.common.language_engine import LanguageEngine
from zolletta_metaskill.engines.php_engine import PHPEngine, _have_tree_sitter_php

TS_PHP_AVAILABLE = _have_tree_sitter_php()


# --- Protocol / metadata tests -------------------------------------------


def test_engine_satisfies_protocol() -> None:
    """PHPEngine instances should be recognised as LanguageEngine."""
    engine = PHPEngine()
    assert isinstance(engine, LanguageEngine)


def test_language_property() -> None:
    assert PHPEngine().language == "php"


def test_file_extensions() -> None:
    assert PHPEngine().file_extensions() == [".php"]


def test_test_file_pattern() -> None:
    assert PHPEngine().test_file_pattern() == "*Test.php"


def test_is_source_file() -> None:
    engine = PHPEngine()
    assert engine.is_source_file(Path("src/Foo.php")) is True
    assert engine.is_source_file(Path("src/Foo.PHP")) is False
    assert engine.is_source_file(Path("src/Foo.phtml")) is False
    assert engine.is_source_file(Path("README.md")) is False


def test_is_test_file_by_name() -> None:
    engine = PHPEngine()
    assert engine.is_test_file(Path("tests/UserTest.php")) is True
    assert engine.is_test_file(Path("src/CalculatorTest.php")) is True
    assert engine.is_test_file(Path("src/User.php")) is False


def test_is_test_file_by_directory() -> None:
    engine = PHPEngine()
    assert engine.is_test_file(Path("tests/Helper.php")) is True
    assert engine.is_test_file(Path("app/Service.php")) is False


# --- parse_module tests (require tree-sitter-php) ------------------------


pytestmark_ts = pytest.mark.skipif(
    not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed"
)


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_simple_class(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
class User {
    public function getName(): string {
        return $this->name;
    }
    private function secret(): void {}
}
"""
    path = tmp_path / "User.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    assert info.language == "php"
    assert info.path == path
    assert info.has_syntax_error is False
    assert len(info.classes) == 1
    cls = info.classes[0]
    assert cls.name == "User"
    assert cls.is_abstract is False
    assert cls.is_test_class is False
    assert cls.bases == []
    method_names = [m.name for m in cls.methods]
    assert "getName" in method_names
    assert "secret" in method_names


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_class_methods_visibility_and_static(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
class Service {
    public function pub() {}
    protected function prot() {}
    private function priv() {}
    public static function stat() {}
    function defaultVis() {}
}
"""
    path = tmp_path / "Service.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    by_name = {m.name: m for m in cls.methods}

    assert by_name["pub"].is_public is True
    assert by_name["prot"].is_public is False
    assert by_name["priv"].is_public is False
    assert by_name["stat"].is_public is True
    assert by_name["stat"].is_static is True
    assert by_name["pub"].is_static is False
    # PHP defaults to public when no modifier is present.
    assert by_name["defaultVis"].is_public is True


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_method_params_and_return_type(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
class Calculator {
    public function add(int $a, int $b): int {
        return $a + $b;
    }
    public function maybe(): ?string {
        return null;
    }
}
"""
    path = tmp_path / "Calculator.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    add = next(m for m in cls.methods if m.name == "add")
    assert add.params == ["a", "b"]
    assert add.return_type == "int"
    maybe = next(m for m in cls.methods if m.name == "maybe")
    assert maybe.return_type is not None
    assert "string" in maybe.return_type


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_abstract_class(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
abstract class Base {
    abstract public function required(): void;
    public function concrete() {}
}
"""
    path = tmp_path / "Base.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    assert cls.name == "Base"
    assert cls.is_abstract is True


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_interface(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
interface RepositoryInterface {
    public function find(int $id): ?array;
    public function save(array $data): bool;
}
"""
    path = tmp_path / "RepositoryInterface.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    assert len(info.classes) == 1
    cls = info.classes[0]
    assert cls.name == "RepositoryInterface"
    assert cls.is_abstract is True
    assert len(cls.methods) == 2


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_trait(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
trait Loggable {
    public function log(string $message): void {
        echo $message;
    }
}
"""
    path = tmp_path / "Loggable.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    assert len(info.classes) == 1
    cls = info.classes[0]
    assert cls.name == "Loggable"
    assert cls.is_abstract is False
    assert len(cls.methods) == 1


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_class_bases(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
class Admin extends User implements AdminInterface, Serializable {
    public function data() {}
}
"""
    path = tmp_path / "Admin.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    assert "User" in cls.bases
    assert "AdminInterface" in cls.bases
    assert "Serializable" in cls.bases


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_test_class_heuristic(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
class UserTest extends TestCase {
    public function testItWorks() {}
}
"""
    path = tmp_path / "UserTest.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    assert cls.name == "UserTest"
    assert cls.is_test_class is True


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_free_functions(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
function greet(string $name): string {
    return "Hello, " . $name;
}
function add(int $a, int $b): int {
    return $a + $b;
}
"""
    path = tmp_path / "functions.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    assert info.classes == []
    names = [f.name for f in info.functions]
    assert "greet" in names
    assert "add" in names
    greet = next(f for f in info.functions if f.name == "greet")
    assert greet.params == ["name"]
    assert greet.return_type == "string"


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_use_imports(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
namespace App\\Service;

use Some\\Namespace\\Cls;
use Other\\Ns\\{ClsA, ClsB};
use Third\\Lib\\Thing as Alias;
"""
    path = tmp_path / "imports.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    modules = [imp.module for imp in info.imports]
    assert "Some\\Namespace\\Cls" in modules
    assert "Other\\Ns\\ClsA" in modules
    assert "Other\\Ns\\ClsB" in modules
    assert "Third\\Lib\\Thing" in modules
    aliased = next(imp for imp in info.imports if imp.module == "Third\\Lib\\Thing")
    assert "Alias" in aliased.names


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_throws(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php
class Worker {
    public function risky(): void {
        throw new \\RuntimeException("boom");
    }
    public function safe(): void {}
}
"""
    path = tmp_path / "Worker.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    risky = next(m for m in cls.methods if m.name == "risky")
    assert "RuntimeException" in risky.raises
    safe = next(m for m in cls.methods if m.name == "safe")
    assert safe.raises == []


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_syntax_error(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = "<?php class { "
    path = tmp_path / "broken.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    assert info.has_syntax_error is True


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_unreadable_file(tmp_path: Path) -> None:
    engine = PHPEngine()
    path = tmp_path / "missing.php"
    info = engine.parse_module(path)
    assert info.has_syntax_error is True
    assert info.classes == []
    assert info.functions == []


@pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
def test_parse_lineno(tmp_path: Path) -> None:
    engine = PHPEngine()
    src = """<?php

class First {
    public function method() {}
}
"""
    path = tmp_path / "First.php"
    path.write_text(src, encoding="utf-8")

    info = engine.parse_module(path)
    cls = info.classes[0]
    assert cls.lineno == 3
    method = cls.methods[0]
    assert method.lineno == 4


# --- Graceful degradation -------------------------------------------------


def test_engine_instantiable_without_optional_dep() -> None:
    """The engine should construct regardless of tree-sitter-php presence."""
    engine = PHPEngine()
    # Metadata methods must work without the optional dependency.
    assert engine.language == "php"
    assert engine.file_extensions() == [".php"]
    assert engine.test_file_pattern() == "*Test.php"


def test_parse_module_missing_dependency(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When tree-sitter-php is absent, parse_module raises a clear ImportError."""
    engine = PHPEngine()
    # Force the "not installed" state.
    monkeypatch.setattr(
        "zolletta_metaskill.engines.php_engine._have_tree_sitter_php", lambda: False
    )
    engine._ready = False  # type: ignore[attr-defined]
    engine._parser = None  # type: ignore[attr-defined]

    path = tmp_path / "Foo.php"
    path.write_text("<?php class Foo {}", encoding="utf-8")

    with pytest.raises(ImportError, match="tree-sitter-php"):
        engine.parse_module(path)
