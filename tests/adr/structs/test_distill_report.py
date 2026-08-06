"""Tests for DistillReport data model."""

from __future__ import annotations

from zolletta_metaskill.adr.structs.distill_report import DistillReport


class TestDistillReportDefaults:
    """Tests for DistillReport default field values."""

    def test_distill_report_defaults_returns_empty_lists(self) -> None:
        """DistillReport defaults to empty lists and has_adrs=False."""
        report = DistillReport()
        assert report.new == []
        assert report.stale == []
        assert report.removed == []
        assert report.has_adrs is False


class TestDistillReportToDict:
    """Tests for DistillReport.to_dict."""

    def test_to_dict_with_defaults_returns_empty_dict(self) -> None:
        """to_dict returns empty lists and False for a default report."""
        report = DistillReport()
        d = report.to_dict()
        assert d == {"new": [], "stale": [], "removed": [], "has_adrs": False}

    def test_to_dict_with_entries_returns_serializable_dict(self) -> None:
        """to_dict returns all fields correctly when populated."""
        report = DistillReport(
            new=["adr-001.md"],
            stale=["adr-002.md"],
            removed=["adr-003.md"],
            has_adrs=True,
        )
        d = report.to_dict()
        assert d["new"] == ["adr-001.md"]
        assert d["stale"] == ["adr-002.md"]
        assert d["removed"] == ["adr-003.md"]
        assert d["has_adrs"] is True

    def test_to_dict_returns_json_serializable_types(self) -> None:
        """to_dict returns only JSON-serializable types."""
        import json

        report = DistillReport(new=["a"], stale=["b"], removed=["c"], has_adrs=True)
        d = report.to_dict()
        json.dumps(d)  # should not raise
