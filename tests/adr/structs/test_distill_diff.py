"""Tests for distill_diff.py."""

from __future__ import annotations

import dataclasses

from zolletta_metaskill.adr.structs.distill_diff import DistillDiff
from zolletta_metaskill.adr.structs.distill_report import DistillReport


class TestDistillDiff:
    # --- Construction ---

    def test_defaults_to_empty_pass(self) -> None:
        diff = DistillDiff()
        assert diff.existing_directives == {}
        assert diff.new_directives == {}
        assert diff.directive_lines == ()
        assert isinstance(diff.report, DistillReport)

    def test_all_fields_are_stored(self) -> None:
        report = DistillReport()
        report.has_adrs = True
        diff = DistillDiff(
            existing_directives={"ADR-0001": "one"},
            new_directives={"ADR-0002": "two"},
            directive_lines=("one", "two"),
            report=report,
        )
        assert diff.existing_directives == {"ADR-0001": "one"}
        assert diff.new_directives == {"ADR-0002": "two"}
        assert diff.directive_lines == ("one", "two")
        assert diff.report.has_adrs is True

    # --- Immutability ---

    def test_is_frozen(self) -> None:
        diff = DistillDiff()
        try:
            diff.directive_lines = ("x",)  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("DistillDiff should be frozen")

    def test_dict_defaults_are_not_shared(self) -> None:
        first = DistillDiff()
        second = DistillDiff()
        first.existing_directives["ADR-0001"] = "leaked"
        assert second.existing_directives == {}

    # --- Role in the write path ---

    def test_bundles_the_four_values_that_only_make_sense_together(self) -> None:
        """existing_content stays outside: it is the raw file, not the diff."""
        names = {f.name for f in dataclasses.fields(DistillDiff)}
        assert names == {
            "existing_directives",
            "new_directives",
            "directive_lines",
            "report",
        }
        assert "existing_content" not in names
