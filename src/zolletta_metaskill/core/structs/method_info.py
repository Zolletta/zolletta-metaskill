"""Information about a single method or module-level function."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MethodInfo:
    """Information about a single method or module-level function.

    Attributes:
        name: The method or function name.
        lineno: The 1-based line number where the definition starts.
        end_lineno: The 1-based line number where the definition ends.
        params: Parameter names excluding the receiver (``self`` / ``this``).
        is_public: Whether the member is publicly visible.
        is_static: Whether the member is static.
        return_type: Return type annotation as a string, if any.
        raises: Exception or throw type names that the method may raise.

    """

    name: str
    lineno: int
    end_lineno: int
    params: list[str] = field(default_factory=list)
    is_public: bool = True
    is_static: bool = False
    return_type: str | None = None
    raises: list[str] = field(default_factory=list)
