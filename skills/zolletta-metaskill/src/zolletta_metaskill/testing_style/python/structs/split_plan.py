"""SplitPlan dataclass for one test-class split."""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class SplitPlan:
    """The inputs for splitting one test class, bundled.

    ``_build_split_file`` and ``_emit_auto_mapping`` each took six parameters.
    Both consume the *same* bundle, so any change to the split inputs had to be
    threaded through two separate six-argument signatures — exactly the shape
    where one is updated and the other is not.

    Attributes:
        original_module: Parsed source module containing the class.
        class_node: The test class being split.
        test_methods: Methods that test one SUT and move to their own file.
        shared_methods: Methods every split file needs.
        original_class_name: Class name in the source file.

    """

    original_module: ast.Module
    class_node: ast.ClassDef
    test_methods: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = ()
    shared_methods: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = ()
    original_class_name: str = ""
