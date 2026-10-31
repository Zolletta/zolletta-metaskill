"""Language-neutral data models for scanner consumption.

These dataclasses are produced by
:class:`~zolletta_metaskill.core.engine.language_engine.LanguageEngine`
implementations and consumed by language-agnostic scanners.
"""

from zolletta_metaskill.core.structs.class_info import ClassInfo
from zolletta_metaskill.core.structs.finding import Finding
from zolletta_metaskill.core.structs.import_info import ImportInfo
from zolletta_metaskill.core.structs.method_info import MethodInfo
from zolletta_metaskill.core.structs.module_info import ModuleInfo

__all__ = ["ClassInfo", "Finding", "ImportInfo", "MethodInfo", "ModuleInfo"]
