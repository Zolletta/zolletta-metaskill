"""Tests for integration_graph_scanner.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.structs import ModuleInfo
from zolletta_metaskill.patterns.general.integration_graph_scanner import (
    IntegrationGraphScanner,
)

TS_PHP_AVAILABLE = PHPEngine._have_tree_sitter_php()


class TestIntegrationGraphScanner:
    # --- Helpers. ---

    @staticmethod
    def _write_settings(dirpath: Path, **overrides: object) -> Path:
        """Write a minimal settings.json under ``dirpath/.zolletta-metaskill``."""
        settings: dict[str, object] = {
            "language": "python",
            "python": {"code_style": {}},
            "php": None,
        }
        settings.update(overrides)
        meta = dirpath / ".zolletta-metaskill"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "settings.json"
        path.write_text(json.dumps(settings))
        return path

    @staticmethod
    def _git_init(root: Path) -> None:
        """Initialise a git repo at *root* so gitignore rules apply."""
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    @staticmethod
    def _write(path: Path, source: str) -> Path:
        """Write *source* to *path* (creating parents) and return it."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        return path

    # --- Tests for IntegrationGraphScanner.resolve_extensions(). ---

    def test_python_language_returns_py(self, tmp_path: Path) -> None:
        settings = self._write_settings(tmp_path, language="python")
        assert IntegrationGraphScanner.resolve_extensions(settings) == {".py"}

    def test_php_language_returns_php(self, tmp_path: Path) -> None:
        settings = self._write_settings(
            tmp_path, language="php", python=None, php={"code_style": {}}
        )
        assert IntegrationGraphScanner.resolve_extensions(settings) == {".php"}

    def test_polyglot_settings_scans_all_configured_languages(
        self, tmp_path: Path
    ) -> None:
        settings = self._write_settings(
            tmp_path, language="python", php={"code_style": {}}
        )
        assert IntegrationGraphScanner.resolve_extensions(settings) == {
            ".py",
            ".php",
        }

    def test_missing_settings_falls_back_to_all_engines(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / ".zolletta-metaskill" / "settings.json"
        assert IntegrationGraphScanner.resolve_extensions(missing) == {
            ".py",
            ".php",
        }

    def test_unknown_language_falls_back_to_all_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        settings = self._write_settings(tmp_path, language="go", python=None)
        result = IntegrationGraphScanner.resolve_extensions(settings)
        err = capsys.readouterr().err
        assert "no engine for language 'go'" in err
        assert result == {".py", ".php"}

    def test_invalid_json_falls_back(self, tmp_path: Path) -> None:
        meta = tmp_path / ".zolletta-metaskill"
        meta.mkdir()
        bad = meta / "settings.json"
        bad.write_text("{ not json")
        assert IntegrationGraphScanner.resolve_extensions(bad) == {
            ".py",
            ".php",
        }

    # --- Tests for Python edge resolution. ---

    def test_absolute_import_resolves_to_module_file(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "pkg" / "mod.py", "class Thing:\n    pass\n")
        self._write(
            root / "a.py",
            "from pkg.mod import Thing\n\nthing = Thing()\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1
        edge = result["edges"][0]
        assert edge["from"].endswith("a.py")
        assert edge["to"].endswith("mod.py")
        assert edge["line"] == 1
        assert edge["names"] == [{"name": "Thing", "usage": "call"}]

    def test_package_init_resolution(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "pkg" / "__init__.py", "X = 1\n")
        self._write(root / "a.py", "import pkg\n\nprint(pkg.X)\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1
        assert result["edges"][0]["to"].endswith("__init__.py")

    def test_from_import_resolves_submodule_per_name(self, tmp_path: Path) -> None:
        """``from pkg import a, b`` splits into per-submodule edges."""
        root = tmp_path / "src"
        self._write(root / "pkg" / "a.py", "A = 1\n")
        self._write(root / "pkg" / "b.py", "B = 2\n")
        self._write(root / "m.py", "from pkg import a, b\n\nprint(a.A, b.B)\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        targets = {Path(e["to"]).name for e in result["edges"]}
        assert targets == {"a.py", "b.py"}

    def test_relative_import_resolves_in_package(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "pkg" / "sibling.py", "S = 1\n")
        self._write(
            root / "pkg" / "a.py",
            "from .sibling import S\n\nprint(S)\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1
        assert result["edges"][0]["to"].endswith("sibling.py")

    def test_relative_bare_from_import_resolves_name(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "pkg" / "helper.py", "H = 1\n")
        self._write(root / "pkg" / "a.py", "from . import helper\n\nprint(helper.H)\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1
        assert result["edges"][0]["to"].endswith("helper.py")

    def test_relative_dotdot_climbs_ancestors(self, tmp_path: Path) -> None:
        """``from ..sib import x`` resolves by walking up to the root."""
        root = tmp_path / "src"
        self._write(root / "sib.py", "X = 1\n")
        self._write(
            root / "pkg" / "deep" / "a.py",
            "from ..sib import X\n\nprint(X)\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1
        assert result["edges"][0]["to"].endswith("sib.py")

    def test_relative_import_never_leaves_root(self, tmp_path: Path) -> None:
        """A relative import cannot resolve to a file above the scan root."""
        self._write(tmp_path / "leak.py", "L = 1\n")
        root = tmp_path / "src"
        self._write(root / "a.py", "from . import leak\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 0
        assert result["external_imports"] == 1

    def test_external_imports_counted_not_edged(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "a.py", "import os\nimport sys\n\nprint(os.getcwd())\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 0
        assert result["external_imports"] == 2

    def test_from_import_attribute_of_package_init(self, tmp_path: Path) -> None:
        """``from pkg import X`` where X lives in ``pkg/__init__.py``."""
        root = tmp_path / "src"
        self._write(root / "pkg" / "__init__.py", "X = 1\n")
        self._write(root / "a.py", "from pkg import X\n\nprint(X)\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1
        assert result["edges"][0]["to"].endswith("__init__.py")
        assert result["edges"][0]["names"] == [
            {"name": "X", "usage": "attribute"}
        ]

    # --- Tests for usage-hint classification (Python). ---

    def test_usage_call_attribute_root(self, tmp_path: Path) -> None:
        """``mod.func()`` marks the ``mod`` import as a call."""
        root = tmp_path / "src"
        self._write(root / "mod.py", "def go():\n    pass\n")
        self._write(root / "a.py", "import mod\n\nmod.go()\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "mod", "usage": "call"}
        ]

    def test_usage_type_annotation(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "t.py", "class T:\n    pass\n")
        self._write(
            root / "a.py",
            "from t import T\n\n\ndef f(x: T) -> T:\n    return x\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [{"name": "T", "usage": "type"}]

    def test_usage_type_annassign(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "t.py", "class T:\n    pass\n")
        self._write(root / "a.py", "from t import T\n\nx: T\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [{"name": "T", "usage": "type"}]

    def test_usage_extends_base_class(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "base.py", "class Base:\n    pass\n")
        self._write(
            root / "a.py", "from base import Base\n\n\nclass C(Base):\n    pass\n"
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "Base", "usage": "extends"}
        ]

    def test_usage_extends_keyword_metaclass(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "meta.py", "M = type\n")
        self._write(
            root / "a.py",
            "from meta import M\n\n\nclass C(metaclass=M):\n    pass\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [{"name": "M", "usage": "extends"}]

    def test_usage_attribute_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "c.py", "CONST = 1\n")
        self._write(root / "a.py", "from c import CONST\n\ny = CONST + 1\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "CONST", "usage": "attribute"}
        ]

    def test_usage_import_only(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "u.py", "X = 1\n")
        self._write(root / "a.py", "from u import X\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "X", "usage": "import-only"}
        ]

    def test_usage_priority_call_beats_type(self, tmp_path: Path) -> None:
        """A name used in a call AND an annotation reports ``call``."""
        root = tmp_path / "src"
        self._write(root / "t.py", "class T:\n    pass\n")
        self._write(
            root / "a.py",
            "from t import T\n\n\ndef f(x: T) -> None:\n    T()\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [{"name": "T", "usage": "call"}]

    def test_usage_type_dotted_annotation(self, tmp_path: Path) -> None:
        """``x: pkg.mod.T`` marks the ``pkg.mod`` import as ``type``."""
        root = tmp_path / "src"
        self._write(root / "pkg" / "mod.py", "class T:\n    pass\n")
        self._write(root / "a.py", "import pkg.mod\n\nx: pkg.mod.T\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "pkg.mod", "usage": "type"}
        ]

    def test_usage_extends_dotted_base(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "pkg" / "base.py", "class Base:\n    pass\n")
        self._write(
            root / "a.py",
            "import pkg.base\n\n\nclass C(pkg.base.Base):\n    pass\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "pkg.base", "usage": "extends"}
        ]

    def test_python_usages_syntax_error_returns_empty_kinds(
        self, tmp_path: Path
    ) -> None:
        f = self._write(tmp_path / "broken.py", "def foo(:\n")
        kinds = IntegrationGraphScanner._python_usages(f)
        assert kinds == {
            "call": set(),
            "extends": set(),
            "type": set(),
            "attribute": set(),
        }

    def test_usage_syntax_error_module_no_edges(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "broken.py", "def foo(:\n    from os import path\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 0

    def test_dotted_call_marks_module_call(self, tmp_path: Path) -> None:
        """``pkg.mod.Cls()`` marks a ``pkg.mod`` import as ``call``."""
        root = tmp_path / "src"
        self._write(root / "pkg" / "mod.py", "class Cls:\n    pass\n")
        self._write(root / "a.py", "import pkg.mod\n\nx = pkg.mod.Cls()\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"][0]["names"] == [
            {"name": "pkg.mod", "usage": "call"}
        ]

    # --- Tests for PHP edge resolution and usage hints. ---

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_use_resolves_psr4(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "App" / "Service.php", "<?php\nclass Service {}\n")
        self._write(
            root / "a.php",
            "<?php\nuse App\\Service;\n\n$s = new Service();\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".php"})
        assert result["edge_count"] == 1
        edge = result["edges"][0]
        assert edge["to"].endswith("Service.php")
        assert edge["names"] == [{"name": "Service", "usage": "new"}]

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_use_alias_usage(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "App" / "Service.php", "<?php\nclass Service {}\n")
        self._write(
            root / "a.php",
            "<?php\nuse App\\Service as Svc;\n\n$s = new Svc();\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".php"})
        assert result["edge_count"] == 1
        assert result["edges"][0]["names"] == [{"name": "Svc", "usage": "new"}]

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_type_and_extends_hints(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "App" / "Base.php", "<?php\nclass Base {}\n")
        self._write(root / "App" / "IFace.php", "<?php\ninterface IFace {}\n")
        self._write(root / "App" / "Dto.php", "<?php\nclass Dto {}\n")
        self._write(
            root / "a.php",
            "<?php\n"
            "use App\\Base;\n"
            "use App\\IFace;\n"
            "use App\\Dto;\n"
            "class C extends Base implements IFace {\n"
            "    public function f(Dto $d): void {}\n"
            "}\n",
        )
        result = IntegrationGraphScanner.scan_directory([root], {".php"})
        by_name = {
            n["name"]: n["usage"]
            for e in result["edges"]
            for n in e["names"]
        }
        assert by_name["Base"] == "extends"
        assert by_name["IFace"] == "extends"
        assert by_name["Dto"] == "type"

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_import_only(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "App" / "Unused.php", "<?php\nclass Unused {}\n")
        self._write(root / "a.php", "<?php\nuse App\\Unused;\n")
        result = IntegrationGraphScanner.scan_directory([root], {".php"})
        assert result["edges"][0]["names"] == [
            {"name": "Unused", "usage": "import-only"}
        ]

    @pytest.mark.skipif(not TS_PHP_AVAILABLE, reason="tree-sitter-php not installed")
    def test_php_external_use_counted(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "a.php", "<?php\nuse Vendor\\Lib\\Thing;\n")
        result = IntegrationGraphScanner.scan_directory([root], {".php"})
        assert result["edge_count"] == 0
        assert result["external_imports"] == 1

    def test_php_usages_without_engine_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``.php`` path with no PHP engine yields no usage hints."""
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        monkeypatch.setattr(EngineRegistry, "get_for_file", lambda _p: None)
        kinds = IntegrationGraphScanner._php_usages(tmp_path / "x.php")
        assert kinds == {"new": set(), "extends": set(), "type": set()}

    def test_php_usages_parse_failure_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> None:
            raise ImportError("tree-sitter-php is required")

        monkeypatch.setattr(PHPEngine, "parse_raw", _fail)
        f = self._write(tmp_path / "x.php", "<?php\nnew A();\n")
        kinds = IntegrationGraphScanner._php_usages(f)
        assert kinds == {"new": set(), "extends": set(), "type": set()}

    # --- Tests for scan_directory aggregation and plumbing. ---

    def test_fan_in_fan_out_aggregation(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        self._write(root / "hub.py", "X = 1\n")
        self._write(root / "a.py", "from hub import X\n\nprint(X)\n")
        self._write(root / "b.py", "from hub import X\n\nprint(X)\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        modules = {m["module"]: m for m in result["modules"]}
        hub_key = next(k for k in modules if k.endswith("hub.py"))
        assert modules[hub_key]["fan_in"] == 2
        assert modules[hub_key]["fan_out"] == 0
        a_key = next(k for k in modules if k.endswith("a.py"))
        assert modules[a_key]["fan_out"] == 1
        assert modules[a_key]["fan_in"] == 0

    def test_extensions_resolved_from_settings(self, tmp_path: Path) -> None:
        """Omitted extensions resolve from settings.json (python → .py)."""
        settings = self._write_settings(tmp_path, language="python")
        root = tmp_path / "src"
        self._write(root / "t.py", "T = 1\n")
        self._write(root / "a.py", "from t import T\n\nprint(T)\n")
        self._write(root / "x.php", "<?php\nuse App\\X;\n")
        result = IntegrationGraphScanner.scan_directory(
            [root], settings_path=settings
        )
        assert result["edge_count"] == 1
        assert result["edges"][0]["to"].endswith("t.py")

    def test_gitignored_file_skipped(self, tmp_path: Path) -> None:
        self._git_init(tmp_path)
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        root = tmp_path / "src"
        self._write(root / "t.py", "T = 1\n")
        self._write(root / "ignored.py", "from t import T\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 0

    def test_empty_graph_no_error(self, tmp_path: Path) -> None:
        root = tmp_path / "src"
        root.mkdir(parents=True)
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"] == []
        assert result["modules"] == []
        assert result["external_imports"] == 0

    def test_unparseable_file_warns_and_continues(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from zolletta_metaskill.core.engine.python_engine import PythonEngine

        def _fail(*_args: object, **_kwargs: object) -> ModuleInfo:
            raise OSError("unreadable")

        monkeypatch.setattr(PythonEngine, "parse_module", _fail)
        root = tmp_path / "src"
        self._write(root / "a.py", "import os\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"] == []
        assert result["scanned"] == 0
        assert "Warning: could not parse" in capsys.readouterr().err

    def test_file_without_engine_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from zolletta_metaskill.core.engine.engine_registry import EngineRegistry

        monkeypatch.setattr(EngineRegistry, "get_for_file", lambda _p: None)
        root = tmp_path / "src"
        self._write(root / "a.py", "import os\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edges"] == []

    def test_git_missing_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_git(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("git not installed")

        monkeypatch.setattr(subprocess, "run", _no_git)
        root = tmp_path / "src"
        self._write(root / "t.py", "T = 1\n")
        self._write(root / "a.py", "from t import T\n\nprint(T)\n")
        result = IntegrationGraphScanner.scan_directory([root], {".py"})
        assert result["edge_count"] == 1

    # --- Tests for IntegrationGraphScanner.main(). ---

    def test_main_missing_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No configured source directory on disk → usage error."""
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = IntegrationGraphScanner.main()
        err = capsys.readouterr().err
        assert rc == 1
        assert "no configured source directories" in err

    def test_main_text_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        self._write(root / "t.py", "T = 1\n")
        self._write(root / "a.py", "from t import T\n\nprint(T)\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = IntegrationGraphScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "INTEGRATION GRAPH" in out
        assert "internal edges" in out
        assert "a.py" in out
        assert "t.py" in out
        assert "triage artifact" in out

    def test_main_text_empty_graph(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        self._write(root / "a.py", "import os\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = IntegrationGraphScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "Edges: none" in out

    def test_main_json_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        self._write_settings(tmp_path)
        root = tmp_path / "src"
        self._write(root / "t.py", "T = 1\n")
        self._write(root / "a.py", "from t import T\n\nprint(T)\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        rc = IntegrationGraphScanner.main()
        report = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert report["scanned"] == 2
        assert report["edge_count"] == 1
        assert report["external_imports"] == 0
        edge = report["edges"][0]
        assert edge["line"] == 1
        assert edge["names"][0]["name"] == "T"
        modules = {m["module"]: m for m in report["modules"]}
        assert any(k.endswith("t.py") for k in modules)

    def test_main_no_settings_uses_registered_engines(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without settings.json, all registered engines' roots apply."""
        monkeypatch.chdir(tmp_path)
        root = tmp_path / "src"
        self._write(root / "t.py", "T = 1\n")
        self._write(root / "a.py", "from t import T\n\nprint(T)\n")
        monkeypatch.setattr(sys, "argv", ["prog"])
        rc = IntegrationGraphScanner.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert "internal edges" in out
