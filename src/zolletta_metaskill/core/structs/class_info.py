"""Information about a single class, interface, trait, or struct."""

from __future__ import annotations

from dataclasses import dataclass, field

from zolletta_metaskill.core.structs.method_info import MethodInfo


@dataclass(frozen=True)
class ClassInfo:
    """Information about a single class, interface, trait, or struct.

    Attributes:
        name: The class name.
        lineno: The 1-based line number where the definition starts.
        end_lineno: The 1-based line number where the definition ends.
        methods: Methods defined directly in the class body.
        bases: Base class or interface names.
        attributes: Instance attribute names (e.g. ``self.x`` → ``"x"``).
        is_abstract: Whether the class is abstract or an interface.
        is_test_class: Whether the class is a test class (name-based heuristic).

    """

    name: str
    lineno: int
    end_lineno: int
    methods: list[MethodInfo] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    is_abstract: bool = False
    is_test_class: bool = False
