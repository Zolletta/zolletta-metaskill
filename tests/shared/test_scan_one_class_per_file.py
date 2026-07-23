"""Tests for scan_one_class_per_file.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.common.models import Finding
from zolletta_metaskill.common.registry import get_engine_for_file
from zolletta_metaskill.shared.scan_one_class_per_file import (
    _snake_to_pascal,
    main,
    scan_file,
    scan_module,
)


class TestSnakeToPascal:
    """Tests for _snake_to_pascal()."""

    def test_simple(self) -> None:
        assert _snake_to_pascal("my_class") == "MyClass"

    def test_single_word(self) -> None:
        assert _snake_to_pascal("cache") == "Cache"

    def test_empty(self) -> None:
        assert _snake_to_pascal("") == ""

    def test_multiple_words(self) -> None:
        assert _snake_to_pascal("my_awesome_class") == "MyAwesomeClass"

    def test_already_pascal(self) -> None:
        # No underscores, capitalize will title-case it
        assert _snake_to_pascal("myclass") == "Myclass"

    def test_leading_underscore(self) -> None:
        # split on "_" produces ["", "class"] -> "" + "Class"
        assert _snake_to_pascal("_class") == "Class"


class TestScanFile:
    """Tests for scan_file() — now returns list[Finding]."""

    def test_single_class_no_violation(self, tmp_path: Path) -> None:
        """A file with one class matching the filename produces no findings."""
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        findings = scan_file(f)
        assert findings == []

    def test_multiple_classes(self, tmp_path: Path) -> None:
        """A file with 2+ classes produces a multi_class finding."""
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "multi_class"
        assert findings[0].severity == "high"
        assert "Foo" in findings[0].description
        assert "Bar" in findings[0].description
        assert "2 classes" in findings[0].description

    def test_zero_classes(self, tmp_path: Path) -> None:
        """A file with no classes produces a zero_class finding."""
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 42\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "zero_class"
        assert findings[0].severity == "low"

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A syntax-error file produces no findings (skipped)."""
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        findings = scan_file(f)
        assert findings == []

    def test_nested_class_treated_as_single(self, tmp_path: Path) -> None:
        """Nested classes are not counted by the engine (only top-level).

        The file has one top-level class 'Outer' with a nested 'Inner'.
        Since only 'Outer' is counted, this is a name_mismatch (Outer != Nested).
        """
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "name_mismatch"
        assert "Outer" in findings[0].description

    def test_empty_file(self, tmp_path: Path) -> None:
        """An empty file produces a zero_class finding."""
        f = tmp_path / "empty.py"
        f.write_text("")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "zero_class"

    def test_file_path_in_finding(self, tmp_path: Path) -> None:
        """The finding's file field matches the path."""
        f = tmp_path / "thing.py"
        f.write_text("class WrongName:\n    pass\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].file == str(f)

    def test_name_mismatch(self, tmp_path: Path) -> None:
        """A class name that doesn't match the filename produces a finding."""
        f = tmp_path / "user.py"
        f.write_text("class WrongName:\n    pass\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].category == "name_mismatch"
        assert findings[0].severity == "medium"
        assert "WrongName" in findings[0].description
        assert "User" in findings[0].description  # expected name

    def test_class_name_matches_filename(self, tmp_path: Path) -> None:
        """A class name matching the PascalCase filename produces no findings."""
        f = tmp_path / "user_account.py"
        f.write_text("class UserAccount:\n    pass\n")
        findings = scan_file(f)
        assert findings == []

    def test_class_name_equals_stem(self, tmp_path: Path) -> None:
        """Class name == file stem (snake_case) is also accepted."""
        f = tmp_path / "user.py"
        f.write_text("class user:\n    pass\n")
        findings = scan_file(f)
        assert findings == []


class TestScanModule:
    """Tests for scan_module() with ModuleInfo directly."""

    def test_syntax_error_module(self, tmp_path: Path) -> None:
        """A module with has_syntax_error returns no findings."""
        engine = get_engine_for_file(tmp_path / "bad.py")
        assert engine is not None
        module = engine.parse_module(tmp_path / "bad.py")
        # parse_module on a non-existent file returns has_syntax_error=True
        assert module.has_syntax_error
        assert scan_module(module) == []

    def test_multi_class_finding(self, tmp_path: Path) -> None:
        """Two top-level classes produce a multi_class finding."""
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        engine = get_engine_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        findings = scan_module(module)
        assert len(findings) == 1
        assert findings[0].category == "multi_class"

    def test_returns_finding_objects(self, tmp_path: Path) -> None:
        """scan_module returns Finding dataclass instances."""
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 1\n")
        engine = get_engine_for_file(f)
        assert engine is not None
        module = engine.parse_module(f)
        findings = scan_module(module)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)


class TestMain:
    """Tests for main()."""

    def test_main_skip(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                       monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--skip"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_missing_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(missing)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_all_clear(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                            monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_multi_class_report_only(self, tmp_path: Path,
                                          capsys: pytest.CaptureFixture[str],
                                          monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "violations found" in out
        assert "2+ classes" in out

    def test_main_multi_class_strict(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "multi.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 1
        assert "VIOLATIONS FOUND" in out

    def test_main_name_mismatch(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class WrongName:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Class name != filename" in out
        assert "WrongName" in out

    def test_main_name_mismatch_strict(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                       monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class WrongName:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--strict"])
        rc = main()
        assert rc == 1

    def test_main_zero_class_reported(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                      monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "utils.py").write_text("def helper():\n    return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "0 classes" in out
        assert "utils.py" in out

    def test_main_ignore_zero(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "utils.py").write_text("def helper():\n    return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--ignore-zero"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        # With --ignore-zero, the "0 classes" section is not printed at all
        assert "0 classes" not in out
        assert "utils.py" not in out

    def test_main_ignore_zero_strict_no_violation(self, tmp_path: Path,
                                                  capsys: pytest.CaptureFixture[str],
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "utils.py").write_text("def helper():\n    return 1\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--ignore-zero", "--strict"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_syntax_error_skipped(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                       monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "bad.py").write_text("def broken(:\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        # Syntax error files are skipped (no error, no zero-class report)
        assert "bad.py" not in out or "0 classes" in out

    def test_main_empty_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                            monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_nested_dirs(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        sub = root / "models"
        sub.mkdir(parents=True)
        (root / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "item.py").write_text("class Item:\n    pass\n")
        (sub / "bad.py").write_text("class Wrong:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Wrong" in out
        assert "models/bad.py" in out

    def test_main_pycache_ignored(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                  monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        pycache = root / "__pycache__"
        pycache.mkdir()
        (pycache / "junk.py").write_text("class Junk:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Junk" not in out

    def test_main_class_name_matches_filename(self, tmp_path: Path,
                                              capsys: pytest.CaptureFixture[str],
                                              monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user_account.py").write_text("class UserAccount:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "none" in out

    def test_main_class_name_equals_stem(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                         monkeypatch: pytest.MonkeyPatch) -> None:
        """Class name == file stem (snake_case) is also accepted."""
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class user:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "none" in out

    def test_main_default_src(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch: pytest.MonkeyPatch) -> None:
        """main() with default 'src' directory."""
        monkeypatch.chdir(tmp_path)
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class User:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out
