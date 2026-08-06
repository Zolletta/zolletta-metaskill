"""Tests for ADRRecord data model."""

from __future__ import annotations

import time
from pathlib import Path

from zolletta_metaskill.adr.structs.adr_record import ADRRecord


class TestADRRecordCreation:
    """Tests for ADRRecord dataclass creation and field access."""

    def test_adr_record_creation_with_all_fields_returns_record(self) -> None:
        """ADRRecord stores all fields correctly."""
        path = Path("/tmp/adr-001.md")
        mtime = time.time()
        record = ADRRecord(
            number="001",
            title="Use PostgreSQL",
            status="Accepted",
            decision_text="We will use PostgreSQL.",
            file_path=path,
            mtime=mtime,
        )
        assert record.number == "001"
        assert record.title == "Use PostgreSQL"
        assert record.status == "Accepted"
        assert record.decision_text == "We will use PostgreSQL."
        assert record.file_path == path
        assert record.mtime == mtime

    def test_adr_record_with_non_padded_number_returns_number(self) -> None:
        """ADRRecord accepts non-zero-padded numbers."""
        record = ADRRecord(
            number="5",
            title="Use Redis",
            status="Proposed",
            decision_text="",
            file_path=Path("/tmp/adr-5.md"),
            mtime=0.0,
        )
        assert record.number == "5"

    def test_adr_record_empty_decision_text_returns_empty_string(self) -> None:
        """ADRRecord accepts empty decision text."""
        record = ADRRecord(
            number="002",
            title="Use Kafka",
            status="Accepted",
            decision_text="",
            file_path=Path("/tmp/adr-002.md"),
            mtime=0.0,
        )
        assert record.decision_text == ""
