"""Tests for scan_one_class_per_file.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from zolletta_metaskill.shared.scan_one_class_per_file import (
    _snake_to_pascal,
    main,
    scan_file,
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
    """Tests for scan_file()."""

    def test_single_class(self, tmp_path: Path) -> None:
        f = tmp_path / "user.py"
        f.write_text("class User:\n    pass\n")
        info = scan_file(f)
        assert info["error"] is False
        assert len(info["classes"]) == 1
        assert info["classes"][0]["name"] == "User"
        assert info["classes"][0]["line"] == 1

    def test_multiple_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.py"
        f.write_text("class Foo:\n    pass\n\nclass Bar:\n    pass\n")
        info = scan_file(f)
        assert info["error"] is False
        names = [c["name"] for c in info["classes"]]
        assert names == ["Foo", "Bar"]

    def test_zero_classes(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("def helper():\n    return 42\n")
        info = scan_file(f)
        assert info["error"] is False
        assert info["classes"] == []

    def test_syntax_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        info = scan_file(f)
        assert info["error"] is True
        assert info["classes"] == []

    def test_nested_class(self, tmp_path: Path) -> None:
        f = tmp_path / "nested.py"
        f.write_text("class Outer:\n    class Inner:\n        pass\n")
        info = scan_file(f)
        assert info["error"] is False
        names = [c["name"] for c in info["classes"]]
        assert "Outer" in names
        assert "Inner" in names

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.py"
        f.write_text("")
        info = scan_file(f)
        assert info["error"] is False
        assert info["classes"] == []

    def test_file_path_in_result(self, tmp_path: Path) -> None:
        f = tmp_path / "thing.py"
        f.write_text("class Thing:\n    pass\n")
        info = scan_file(f)
        assert info["file"] == str(f)


class TestMain:
    """Tests for main()."""

    def test_main_skip(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                       monkeypatch) -> None:
        monkeypatch.setattr(sys, "argv", ["prog", "--skip"])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "SKIPPED" in out

    def test_main_missing_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch) -> None:
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr(sys, "argv", ["prog", str(missing)])
        rc = main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "does not exist" in err

    def test_main_all_clear(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                            monkeypatch) -> None:
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
                                          monkeypatch) -> None:
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
                                     monkeypatch) -> None:
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
                                monkeypatch) -> None:
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
                                       monkeypatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        (root / "__init__.py").write_text("")
        (root / "user.py").write_text("class WrongName:\n    pass\n")
        monkeypatch.setattr(sys, "argv", ["prog", str(root), "--strict"])
        rc = main()
        assert rc == 1

    def test_main_zero_class_reported(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                      monkeypatch) -> None:
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
                              monkeypatch) -> None:
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
                                                  monkeypatch) -> None:
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
                                       monkeypatch) -> None:
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
                            monkeypatch) -> None:
        root = tmp_path / "src"
        root.mkdir()
        monkeypatch.setattr(sys, "argv", ["prog", str(root)])
        rc = main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "all clear" in out

    def test_main_nested_dirs(self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                              monkeypatch) -> None:
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
                                  monkeypatch) -> None:
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
                                              monkeypatch) -> None:
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
                                         monkeypatch) -> None:
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
                              monkeypatch) -> None:
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
