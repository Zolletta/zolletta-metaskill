"""DistillDiff dataclass for one ADR distillation pass."""

from __future__ import annotations

from dataclasses import dataclass, field

from zolletta_metaskill.adr.structs.distill_report import DistillReport


@dataclass(frozen=True)
class DistillDiff:
    """Everything one distillation pass produces, bundled.

    These four values were passed separately to ``_write_distilled`` but only
    make sense together: they are the input and the output of a single merge,
    and none is meaningful apart from the others. ``existing_content`` stays
    outside the bundle because it is the raw file rather than part of the diff.

    Attributes:
        existing_directives: Directives already present in the distilled file.
        new_directives: Directives extracted from newly-discovered ADRs.
        directive_lines: Final directive lines, sorted by ADR number.
        report: Classification report for this run.

    """

    existing_directives: dict[str, str] = field(default_factory=dict)
    new_directives: dict[str, str] = field(default_factory=dict)
    directive_lines: tuple[str, ...] = ()
    report: DistillReport = field(default_factory=DistillReport)
