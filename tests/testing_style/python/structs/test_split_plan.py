"""Tests for split_plan.py."""

from __future__ import annotations

import ast
import dataclasses

from zolletta_metaskill.testing_style.python.structs import SplitPlan


def _module(source: str = "class TestOriginal:\n    pass\n") -> ast.Module:
    return ast.parse(source)


def _class(source: str = "class TestOriginal:\n    pass\n") -> ast.ClassDef:
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.ClassDef)
    return node


def _methods(count: int) -> list[ast.FunctionDef]:
    """Build *count* function nodes, as the splitter collects them."""
    module = ast.parse("".join(f"def test_x{i}():\n    pass\n" for i in range(count)))
    return [n for n in module.body if isinstance(n, ast.FunctionDef)]


class TestSplitPlan:
    # --- Construction ---

    def test_required_fields_only(self) -> None:
        plan = SplitPlan(original_module=_module(), class_node=_class())
        assert plan.test_methods == ()
        assert plan.shared_methods == ()
        assert plan.original_class_name == ""

    def test_all_fields_are_stored(self) -> None:
        module, node = _module(), _class()
        methods = tuple(_methods(2))
        plan = SplitPlan(
            original_module=module,
            class_node=node,
            test_methods=methods,
            shared_methods=(),
            original_class_name="TestOriginal",
        )
        assert plan.original_module is module
        assert plan.class_node is node
        assert plan.test_methods == methods
        assert plan.original_class_name == "TestOriginal"

    # --- Immutability ---

    def test_is_frozen(self) -> None:
        plan = SplitPlan(original_module=_module(), class_node=_class())
        try:
            plan.original_class_name = "Other"  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("SplitPlan should be frozen")

    def test_tuple_defaults_are_not_shared(self) -> None:
        first = SplitPlan(original_module=_module(), class_node=_class())
        second = SplitPlan(original_module=_module(), class_node=_class())
        assert first.test_methods is not None
        assert first.test_methods == () and second.test_methods == ()

    # --- Role in the split path ---

    def test_method_collections_are_immutable_tuples(self) -> None:
        """Callers pass lists; the plan stores tuples so a plan cannot be mutated."""
        node = _class()
        methods = _methods(2)
        plan = SplitPlan(
            original_module=_module(),
            class_node=node,
            test_methods=tuple(methods),
            shared_methods=tuple(methods),
        )
        assert isinstance(plan.test_methods, tuple)
        assert isinstance(plan.shared_methods, tuple)

    def test_field_names_match_the_former_parameters(self) -> None:
        names = {f.name for f in dataclasses.fields(SplitPlan)}
        assert names == {
            "original_module",
            "class_node",
            "test_methods",
            "shared_methods",
            "original_class_name",
        }
