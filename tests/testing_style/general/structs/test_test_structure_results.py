"""Tests for test_structure_results.py."""

from __future__ import annotations

import dataclasses
from typing import Any

# Aliased: the test class must be named Test<SutName> per tests.2, and the
# struct's own name starts with ``Test`` — importing it directly makes pytest
# try to collect it as a test class (PytestCollectionWarning).
from zolletta_metaskill.testing_style.general.structs import (
    TestStructureResults as Results,
)


def _item(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"test_file": "tests/x.py", "dir": "x"}
    base.update(overrides)
    return base


class TestTestStructureResults:
    # --- Defaults ---

    def test_all_buckets_default_to_empty(self) -> None:
        results = Results()
        assert results.misnamed == []
        assert results.misplaced == []
        assert results.orphaned == []
        assert results.orphaned_dirs == []
        assert results.missing == []
        assert results.indirect_refs == []

    def test_list_defaults_are_not_shared_between_instances(self) -> None:
        """A shared mutable default would leak one scan's findings into the next."""
        first = Results()
        second = Results()
        first.misnamed.append(_item())
        assert second.misnamed == []
        assert first.misnamed is not second.misnamed

    # --- Immutability ---

    def test_structure_results_assign_field_when_frozen_raises(self) -> None:
        results = Results()
        try:
            setattr(results, "missing", [_item()])
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("TestStructureResults should be frozen")

    def test_buckets_are_still_mutable_lists(self) -> None:
        """Frozen blocks rebinding, not in-place append — the scanner fills them in."""
        results = Results()
        results.missing.append(_item())
        assert len(results.missing) == 1

    # --- has_issues ---

    def test_has_issues_false_when_every_bucket_empty(self) -> None:
        assert Results().has_issues is False

    def test_has_issues_true_for_each_bucket(self) -> None:
        for name in (
            "misnamed",
            "misplaced",
            "orphaned",
            "orphaned_dirs",
            "missing",
            "indirect_refs",
        ):
            results = Results(**{name: [_item()]})
            assert results.has_issues is True, name

    def test_has_issues_is_computed_not_stored(self) -> None:
        """It was previously threaded through as a seventh parameter."""
        results = Results()
        assert "has_issues" not in {f.name for f in dataclasses.fields(results)}
        assert isinstance(Results.has_issues, property)

    def test_has_issues_tracks_in_place_mutation(self) -> None:
        results = Results()
        assert results.has_issues is False
        results.orphaned.append(_item())
        assert results.has_issues is True

    # --- Role in the emitters ---

    def test_six_buckets_match_the_reported_tables(self) -> None:
        """Five finding buckets plus orphaned_dirs, which is reported separately."""
        names = {f.name for f in dataclasses.fields(Results)}
        assert names == {
            "misnamed",
            "misplaced",
            "orphaned",
            "orphaned_dirs",
            "missing",
            "indirect_refs",
        }
