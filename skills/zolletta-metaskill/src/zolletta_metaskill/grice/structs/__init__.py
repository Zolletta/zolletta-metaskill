"""Grice data models (structs)."""

from zolletta_metaskill.grice.structs.benchmark_entry import BenchmarkEntry
from zolletta_metaskill.grice.structs.defect_location import DefectLocation
from zolletta_metaskill.grice.structs.diagnosis import Diagnosis
from zolletta_metaskill.grice.structs.document_features import DocumentFeatures
from zolletta_metaskill.grice.structs.grice_report import GriceReport
from zolletta_metaskill.grice.structs.grice_settings import GriceSettings
from zolletta_metaskill.grice.structs.group_summary import GroupSummary
from zolletta_metaskill.grice.structs.group_triage import GroupTriage
from zolletta_metaskill.grice.structs.maxim_scores import MaximScores
from zolletta_metaskill.grice.structs.structural_defect import StructuralDefect
from zolletta_metaskill.grice.structs.triage_entry import TriageEntry

__all__ = [
    "BenchmarkEntry",
    "DefectLocation",
    "Diagnosis",
    "DocumentFeatures",
    "GriceReport",
    "GriceSettings",
    "GroupSummary",
    "GroupTriage",
    "MaximScores",
    "StructuralDefect",
    "TriageEntry",
]
