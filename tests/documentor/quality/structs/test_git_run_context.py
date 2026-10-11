"""Tests for git_run_context.py."""

from __future__ import annotations

import dataclasses

from zolletta_metaskill.documentor.quality.structs.git_run_context import GitRunContext


class TestGitRunContext:
    # --- Construction ---

    def test_repo_root_only_gets_defaults(self) -> None:
        ctx = GitRunContext(repo_root="/repo")
        assert ctx.repo_root == "/repo"
        assert ctx.renames == ()
        assert ctx.current_version is None

    def test_all_fields_are_stored(self) -> None:
        ctx = GitRunContext(
            repo_root="/repo",
            renames=(("old.py", "new.py"),),
            current_version="3.5.0",
        )
        assert ctx.repo_root == "/repo"
        assert ctx.renames == (("old.py", "new.py"),)
        assert ctx.current_version == "3.5.0"

    # --- Immutability ---

    def test_is_frozen(self) -> None:
        ctx = GitRunContext(repo_root="/repo")
        try:
            ctx.repo_root = "/other"  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("GitRunContext should be frozen")

    def test_renames_default_is_not_shared_between_instances(self) -> None:
        first = GitRunContext(repo_root="/a")
        second = GitRunContext(repo_root="/b")
        assert first.renames is not second.renames or first.renames == second.renames
        assert first.renames == ()

    def test_equality_is_by_value(self) -> None:
        args = {"repo_root": "/repo", "renames": (("a", "b"),), "current_version": "1.0"}
        assert GitRunContext(**args) == GitRunContext(**args)  # type: ignore[arg-type]

    # --- Role in the review ---

    def test_carries_loop_invariant_git_facts(self) -> None:
        """Built once in QualityReview.run and shared across every document."""
        ctx = GitRunContext(
            repo_root="/repo",
            renames=(("tests.yml", "ci.yml"),),
            current_version="3.5.0",
        )
        # Same instance is handed to every per-doc check; nothing is recomputed.
        assert ctx.renames[0] == ("tests.yml", "ci.yml")
        assert ctx.current_version is not None
