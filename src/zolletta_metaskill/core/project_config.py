"""Shared project configuration helpers for review scripts.

Every review script consumes the same standard API::

    python3 <script>.py [--json]

Scan roots, rule toggles, and thresholds all come from
``.zolletta-metaskill/settings.json`` (written by the setup skill) — this
module is the single place that resolves them. Scripts never take a
positional directory or ``--src``/``--tests`` flags; the project layout IS
the configuration.

Conventions mirrored across every consumer:

- Languages are "configured" when the top-level ``language`` field names
  them or their ``<language>`` section is populated (non-null).
- A language is "enabled" for a check when its
  ``<language>.<section>.check_<name>`` toggle is not ``false``. When the
  check is disabled for every configured language the run reports
  SKIPPED.
- Source roots resolve per language: Python reads
  ``python.paths.source``, PHP reads ``php.autoload.psr-4`` values.
  Test roots read ``python.paths.tests`` / ``php.autoload.psr-4-dev``.
- Without settings (or without the relevant keys) roots fall back to
  ``src`` / ``tests`` — the same defaults the setup detector writes.
- File enumeration is git-ignore aware (``git ls-files`` with
  ``--exclude-standard``), so ``vendor/``, ``node_modules/``, build
  output, etc. stay out of reports. Outside a git repository every file
  under the root is a candidate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from zolletta_metaskill.core.engine.engine_registry import EngineRegistry
from zolletta_metaskill.core.engine.php_engine import PHPEngine
from zolletta_metaskill.core.engine.python_engine import PythonEngine


class ProjectConfig:
    """Resolve scan roots, toggles, and thresholds from settings.json.

    All helpers are ``@staticmethod`` methods on this class; constants are
    class-level attributes. There is no per-instance state — settings are
    passed explicitly to every method.
    """

    DEFAULT_SETTINGS_PATH = Path(".zolletta-metaskill/settings.json")

    DEFAULT_SOURCE_DIRS = ["src"]
    DEFAULT_TEST_DIRS = ["tests"]
    DEFAULT_DOCS_DIR = "docs"
    DEFAULT_RUNS_DIR = ".zolletta-metaskill"

    _MISSING = object()

    # ------------------------------------------------------------------
    # Settings loading and lookup
    # ------------------------------------------------------------------

    @staticmethod
    def ensure_engines() -> None:
        """Register the bundled engines so languages and extensions resolve."""
        EngineRegistry.ensure(PythonEngine())
        EngineRegistry.ensure(PHPEngine())

    @staticmethod
    def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> dict[str, Any]:
        """Return parsed settings.json, or an empty dict if unreadable.

        Args:
            path: Path to the settings file (default
                ``.zolletta-metaskill/settings.json`` relative to cwd).

        Returns:
            The parsed JSON object, or ``{}`` when the file is missing,
            unreadable, or does not contain a JSON object.

        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def setting(settings: dict[str, Any], dotted_path: str, default: Any) -> Any:
        """Return the value at *dotted_path* in *settings*, or *default*.

        The walk is type-aware: when *default* is not ``None`` the stored
        value is returned only if it matches the default's type (``bool`` is
        not accepted for ``int`` defaults, matching JSON semantics). When
        *default* is ``None`` the stored value is returned as-is (the caller
        is opting into a nullable setting).
        """
        node: Any = settings
        for part in dotted_path.split("."):
            if not isinstance(node, dict):
                return default
            node = node.get(part, ProjectConfig._MISSING)
            if node is ProjectConfig._MISSING:
                return default
        if default is None:
            return node
        if isinstance(default, bool):
            return node if isinstance(node, bool) else default
        if isinstance(default, int):
            return node if isinstance(node, int) and not isinstance(node, bool) else default
        if isinstance(default, str):
            return node if isinstance(node, str) else default
        if isinstance(default, list):
            return node if isinstance(node, list) else default
        if isinstance(default, dict):
            return node if isinstance(node, dict) else default
        return node

    # ------------------------------------------------------------------
    # Language resolution
    # ------------------------------------------------------------------

    @staticmethod
    def configured_languages(settings: dict[str, Any]) -> set[str]:
        """Return the languages configured in settings.json.

        The top-level ``language`` field plus each ``<language>`` section
        that is populated (non-null) and has a registered engine — unused
        languages stay ``null`` in settings.json, so key presence alone is
        not enough.
        """
        ProjectConfig.ensure_engines()
        registered = set(EngineRegistry.available_languages())
        languages: set[str] = set()
        language = settings.get("language")
        if isinstance(language, str) and language:
            languages.add(language)
        languages.update(lang for lang in registered if isinstance(settings.get(lang), dict))
        return languages

    @staticmethod
    def enabled_languages(settings: dict[str, Any], toggle_path: str) -> set[str]:
        """Return configured languages whose check toggle is not ``false``.

        Args:
            settings: Parsed settings.json.
            toggle_path: Dotted path within each ``<language>`` section naming
                the toggle, e.g. ``"code_style.check_file_length"`` or
                ``"patterns.check_ocp"``. A missing toggle means enabled.

        """
        enabled: set[str] = set()
        for lang in ProjectConfig.configured_languages(settings):
            section = settings.get(lang)
            if (
                isinstance(section, dict)
                and ProjectConfig.setting(section, toggle_path, True) is False
            ):
                continue
            enabled.add(lang)
        return enabled

    @staticmethod
    def any_enabled(
        settings: dict[str, Any],
        languages: set[str],
        toggle_path: str,
        default: bool = True,
    ) -> bool:
        """Return True when *toggle_path* is truthy for any of *languages*.

        Used for secondary toggles that apply scan-wide once the scan roots
        of several languages have been unioned (e.g. ``check_zero_class_files``
        filters a finding category). A language without a section, or without
        the key, contributes *default*.
        """
        for lang in languages:
            section = settings.get(lang)
            value = ProjectConfig.setting(
                section if isinstance(section, dict) else {}, toggle_path, default
            )
            if value:
                return True
        return False

    @staticmethod
    def scan_languages(settings: dict[str, Any], toggle_path: str) -> set[str]:
        """Return the languages a check should run over.

        The enabled languages when settings configure any; an empty set when
        every configured language has the toggle disabled (the caller reports
        SKIPPED); every registered language when settings configure none —
        the pre-setup fallback, so scripts still do something useful without
        a settings.json.
        """
        enabled = ProjectConfig.enabled_languages(settings, toggle_path)
        if enabled:
            return enabled
        if ProjectConfig.configured_languages(settings):
            return set()
        ProjectConfig.ensure_engines()
        return set(EngineRegistry.available_languages())

    @staticmethod
    def extensions_for(languages: set[str]) -> set[str]:
        """Map language names to file extensions via the engine registry.

        Languages without a registered engine produce a warning on stderr and
        contribute no extensions.
        """
        ProjectConfig.ensure_engines()
        registered = set(EngineRegistry.available_languages())
        extensions: set[str] = set()
        for lang in sorted(languages & registered):
            extensions.update(EngineRegistry.get(lang).file_extensions())
        for lang in sorted(languages - registered):
            print(f"Warning: no engine for language '{lang}'", file=sys.stderr)
        return extensions

    @staticmethod
    def languages_for_extensions(languages: set[str], extensions: set[str]) -> set[str]:
        """Return the subset of *languages* whose engine handles *extensions*.

        Used by language-specific scanners to restrict configured/enabled
        languages to the ones they can actually parse (e.g. the Python
        acronym scanner only wants languages with ``.py`` files).
        """
        ProjectConfig.ensure_engines()
        registered = set(EngineRegistry.available_languages())
        return {
            lang
            for lang in languages
            if lang in registered and extensions & set(EngineRegistry.get(lang).file_extensions())
        }

    # ------------------------------------------------------------------
    # Root resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _psr4_dirs(mapping: Any) -> list[str]:
        r"""Return directory strings from a composer autoload mapping.

        Values may be a single string (``"App\\": "src/"``) or a list of
        strings (``"App\\": ["src/", "lib/"]``); both are normalised.
        """
        dirs: list[str] = []
        if not isinstance(mapping, dict):
            return dirs
        for value in mapping.values():
            if isinstance(value, str):
                dirs.append(value)
            elif isinstance(value, list):
                dirs.extend(v for v in value if isinstance(v, str))
        return dirs

    @staticmethod
    def source_dirs(settings: dict[str, Any], lang: str) -> list[str]:
        """Return configured source roots for *lang* (defaults applied).

        Python reads ``python.paths.source``; PHP reads the directory values
        of ``php.autoload.psr-4``. Any other language — or a missing/empty
        configuration — falls back to ``["src"]``.
        """
        if lang == "php":
            psr4 = ProjectConfig._psr4_dirs(
                ProjectConfig.setting(settings, "php.autoload.psr-4", None)
            )
            return psr4 or list(ProjectConfig.DEFAULT_SOURCE_DIRS)
        if lang == "python":
            dirs: list[str] = ProjectConfig.setting(
                settings, "python.paths.source", list(ProjectConfig.DEFAULT_SOURCE_DIRS)
            )
            return dirs
        return list(ProjectConfig.DEFAULT_SOURCE_DIRS)

    @staticmethod
    def test_dirs(settings: dict[str, Any], lang: str) -> list[str]:
        """Return configured test roots for *lang* (defaults applied).

        Python reads ``python.paths.tests``; PHP reads the directory values
        of ``php.autoload.psr-4-dev``. Any other language — or a
        missing/empty configuration — falls back to ``["tests"]``.
        """
        if lang == "php":
            psr4 = ProjectConfig._psr4_dirs(
                ProjectConfig.setting(settings, "php.autoload.psr-4-dev", None)
            )
            return psr4 or list(ProjectConfig.DEFAULT_TEST_DIRS)
        if lang == "python":
            dirs: list[str] = ProjectConfig.setting(
                settings, "python.paths.tests", list(ProjectConfig.DEFAULT_TEST_DIRS)
            )
            return dirs
        return list(ProjectConfig.DEFAULT_TEST_DIRS)

    @staticmethod
    def package_name(settings: dict[str, Any], lang: str) -> str | None:
        """Return the package/namespace hint for mirror-structure checks.

        Python reads ``python.paths.package`` (``null`` when undetected).
        PHP uses the directory of the first ``autoload.psr-4`` mapping.
        """
        if lang == "python":
            pkg = ProjectConfig.setting(settings, "python.paths.package", None)
            return pkg if isinstance(pkg, str) and pkg else None
        if lang == "php":
            dirs = ProjectConfig._psr4_dirs(
                ProjectConfig.setting(settings, "php.autoload.psr-4", None)
            )
            return dirs[0] if dirs else None
        return None

    @staticmethod
    def _deduped_roots(
        settings: dict[str, Any],
        languages: set[str],
        dirs_fn: Callable[[dict[str, Any], str], list[str]],
    ) -> list[Path]:
        """Union of *dirs_fn* results across *languages*, deduplicated."""
        seen: dict[str, None] = {}
        for lang in sorted(languages):
            for d in dirs_fn(settings, lang):
                seen.setdefault(d)
        return [Path(d) for d in seen]

    @staticmethod
    def source_roots(settings: dict[str, Any], languages: set[str]) -> list[Path]:
        """Union of :meth:`source_dirs` across *languages* as Paths."""
        return ProjectConfig._deduped_roots(settings, languages, ProjectConfig.source_dirs)

    @staticmethod
    def test_roots(settings: dict[str, Any], languages: set[str]) -> list[Path]:
        """Union of :meth:`test_dirs` across *languages* as Paths."""
        return ProjectConfig._deduped_roots(settings, languages, ProjectConfig.test_dirs)

    @staticmethod
    def existing_roots(roots: list[Path]) -> list[Path]:
        """Filter *roots* to directories that exist on disk."""
        return [root for root in roots if root.is_dir()]

    # ------------------------------------------------------------------
    # Documentation and runs directories
    # ------------------------------------------------------------------

    @staticmethod
    def docs_dir(settings: dict[str, Any]) -> Path:
        """Return the documentation root (``documentation.dir``, default ``docs``)."""
        return Path(
            ProjectConfig.setting(settings, "documentation.dir", ProjectConfig.DEFAULT_DOCS_DIR)
        )

    @staticmethod
    def adrs_dir(settings: dict[str, Any]) -> Path | None:
        """Return the ADR directory, or ``None`` when no ADRs are configured.

        ``documentation.adrs`` is a path relative to ``documentation.dir``;
        an empty string means ADRs live scattered in the docs root.
        """
        adrs = ProjectConfig.setting(settings, "documentation.adrs", None)
        if adrs is None:
            return None
        if isinstance(adrs, str):
            return (
                ProjectConfig.docs_dir(settings) / adrs
                if adrs
                else ProjectConfig.docs_dir(settings)
            )
        return None

    @staticmethod
    def runs_dir(settings: dict[str, Any]) -> Path:
        """Return the review-runs root (``runs_dir``, default ``.zolletta-metaskill``)."""
        return Path(ProjectConfig.setting(settings, "runs_dir", ProjectConfig.DEFAULT_RUNS_DIR))

    # ------------------------------------------------------------------
    # File enumeration
    # ------------------------------------------------------------------

    @staticmethod
    def _git_files(root: Path) -> list[Path] | None:
        """Return non-ignored files under *root*, or ``None`` outside a git repo.

        Uses ``git ls-files`` so tracked files are always included and
        untracked files are filtered by every exclude source git honours
        (.gitignore, .git/info/exclude, core.excludesFile). Paths outside
        *root* (shown with ``../`` prefixes) are dropped.
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-c", "-o", "--exclude-standard", "-z"],
                capture_output=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0:
            return None
        files = []
        for rel in result.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
            if not rel or rel.startswith("../"):
                continue
            path = root / rel
            if path.is_file():
                files.append(path)
        return files

    @staticmethod
    def iter_files(root: Path, extensions: set[str]) -> list[Path]:
        """Return files under *root* matching *extensions*, sorted by path.

        Git-ignored files are skipped when *root* is inside a repository;
        outside a repo every matching file is returned.
        """
        candidates = ProjectConfig._git_files(root)
        if candidates is None:
            candidates = [p for p in root.rglob("*") if p.is_file()]
        return sorted(p for p in candidates if p.suffix.lower() in extensions)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @staticmethod
    def emit_skipped(as_json: bool, reason: str) -> None:
        """Print the standard SKIPPED report for a disabled check."""
        if as_json:
            print(json.dumps({"skipped": True, "reason": reason}))
        else:
            print(f"Result: SKIPPED ({reason})")
