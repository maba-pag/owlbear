"""Tests for task #529: Add set_approval_state MCP tool to memory-mcp.

Structural AC items specific to #529 NOT covered by test_set_approval_state_569.py
(the companion test task that covers the entire runtime behavioural contract).

The following AC items are already satisfied by the #569 builder and do not need
failing RED tests here:
  - SQL parameterized queries (no f-strings — current code passes)
  - tools.__all__ set_approval_state (already exported)
  - tools.__all__ _VALID_TRANSITIONS (already exported)

This file covers the single AC gap remaining after the #569 pipeline:
  - AC-LIT: new_state parameter must be Literal["approved","deleted","pending"]
             (current: bare `str` — tools.py:230)

AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| new_state Literal["approved","deleted","pending"] | test_new_state_annotation_is_not_bare_str, test_new_state_uses_literal_with_correct_values | error |

All 2 tests FAIL in RED phase — current annotation is `str`, not `Literal[...]`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_TOOLS_PY = _REPO_ROOT / "packages" / "mcp-memory" / "src" / "owlbear_mcp_memory" / "tools.py"


def _tools_source() -> str:
    assert _TOOLS_PY.is_file(), f"tools.py not found at {_TOOLS_PY}"
    return _TOOLS_PY.read_text(encoding="utf-8")


def _parse_tools() -> ast.Module:
    return ast.parse(_tools_source())


def _find_fn(tree: ast.Module, name: str) -> ast.AsyncFunctionDef | ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == name:
            return node
    return None


def _tools_all_values(tree: ast.Module) -> set[str]:
    """Return the set of string literals declared in tools.py __all__."""
    result: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
            and isinstance(node.value, ast.List)
        ):
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    result.add(elt.value)
    return result


# ---------------------------------------------------------------------------
# TestFromAC_LiteralAnnotation — AC-LIT
# ---------------------------------------------------------------------------


class TestFromAC_LiteralAnnotation:
    """Verify that new_state is annotated Literal["approved","deleted","pending"].

    Using Literal instead of bare str enables FastMCP schema-level enum validation
    so invalid new_state values are rejected before the function body runs.
    Per AC: Params: entry_id (str, required), new_state (Literal["approved","deleted","pending"])
    """

    def test_new_state_annotation_is_not_bare_str(self) -> None:
        """AC-LIT: new_state must NOT be annotated as bare 'str'.

        Current implementation passes this check at runtime but violates the AC
        type contract. The builder must change 'str' to
        'Literal["approved","deleted","pending"]'.
        """
        tree = _parse_tools()
        fn = _find_fn(tree, "set_approval_state")
        assert fn is not None, "set_approval_state not found in tools.py"

        for arg in fn.args.args:
            if arg.arg == "new_state":
                ann = arg.annotation
                if ann is not None and isinstance(ann, ast.Name) and ann.id == "str":
                    pytest.fail(
                        "set_approval_state new_state param is annotated as bare 'str'. "
                        "AC requires: Literal['approved', 'deleted', 'pending']. "
                        "Change the annotation in tools.py so FastMCP enforces valid states "
                        "at the schema layer (OWASP A03: input validation)."
                    )
                break

    def test_new_state_uses_literal_with_correct_values(self) -> None:
        """AC-LIT: new_state must be Literal["approved","deleted","pending"] exactly.

        Verifies three things:
        1. Annotation is a subscript (Literal[...] form)
        2. The outer name is 'Literal'
        3. The subscript contains exactly {"approved","deleted","pending"}
        """
        tree = _parse_tools()
        fn = _find_fn(tree, "set_approval_state")
        assert fn is not None, "set_approval_state not found in tools.py"

        new_state_annotation: ast.expr | None = None
        for arg in fn.args.args:
            if arg.arg == "new_state" and arg.annotation is not None:
                new_state_annotation = arg.annotation
                break

        assert new_state_annotation is not None, (
            "set_approval_state has no annotation for 'new_state'. "
            "AC requires: new_state: Literal['approved', 'deleted', 'pending']"
        )

        assert isinstance(new_state_annotation, ast.Subscript), (
            f"new_state annotation must be Literal[...], "
            f"got: {ast.dump(new_state_annotation)!r}. "
            "AC requires: new_state: Literal['approved', 'deleted', 'pending']"
        )

        subscript_name = (
            new_state_annotation.value.id  # type: ignore[attr-defined]
            if isinstance(new_state_annotation.value, ast.Name)
            else None
        )
        assert subscript_name == "Literal", (
            f"new_state annotation must use 'Literal', got {subscript_name!r}. "
            "AC requires: new_state: Literal['approved', 'deleted', 'pending']"
        )

        slice_node = new_state_annotation.slice
        if isinstance(slice_node, ast.Tuple):
            literal_values: set[str] = {
                elt.value  # type: ignore[union-attr]
                for elt in slice_node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
        elif isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            literal_values = {slice_node.value}
        else:
            literal_values = set()

        expected = {"approved", "deleted", "pending"}
        assert literal_values == expected, (
            f"Literal values mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {literal_values!r}\n"
            "AC requires: Literal['approved', 'deleted', 'pending']"
        )



