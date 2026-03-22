"""RED-phase tests for #854 — public pydantic-ai typing imports.

Verifies the import-hygiene contract for #852:
- src/owlbear/core/agent.py, src/owlbear/tools/hooked.py, and
  src/owlbear/safety/gate.py must not import from pydantic_ai._* modules.
- hooked.py and gate.py must import RunContext from pydantic_ai (public API).
- agent.py TYPE_CHECKING block must define a local HistoryProcessor alias
  using public RunContext and ModelMessage names, covering sync and async
  callable variants both with and without context.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_AGENT_PY = _ROOT / "src/owlbear/core/agent.py"
_HOOKED_PY = _ROOT / "src/owlbear/tools/hooked.py"
_GATE_PY = _ROOT / "src/owlbear/safety/gate.py"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _private_pydantic_imports(tree: ast.Module) -> list[str]:
    """Return list of private pydantic_ai import module strings found in tree."""
    return [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("pydantic_ai._")
    ]


def _imported_names_from(tree: ast.Module, module: str) -> set[str]:
    """Return set of names imported from a specific module string."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _all_name_ids(node: ast.AST) -> set[str]:
    """Collect all ast.Name ids within a subtree."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _type_checking_body(tree: ast.Module) -> list[ast.stmt]:
    """Return the statement list inside the first 'if TYPE_CHECKING:' block."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "TYPE_CHECKING"
        ):
            return node.body
    return []


# ---------------------------------------------------------------------------
# AC1 — no private pydantic_ai imports in the three target files
# ---------------------------------------------------------------------------


class TestFromAC_NoPrivatePydanticAiImports:
    """agent.py, hooked.py, gate.py must contain zero private pydantic_ai imports."""

    def test_no_private_pydantic_ai_type_imports_in_target_files(self) -> None:
        """All three target files have zero ImportFrom.module starting with pydantic_ai._."""
        violations: list[str] = []
        for path in (_AGENT_PY, _HOOKED_PY, _GATE_PY):
            found = _private_pydantic_imports(_parse(path))
            if found:
                violations.append(f"{path.name}: {found}")
        assert not violations, (
            "Private pydantic_ai imports found (must be removed by #852):\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# AC2 — hooked.py must import RunContext from pydantic_ai (public)
# ---------------------------------------------------------------------------


class TestFromAC_HookedToolsetPublicRunContext:
    """hooked.py must import RunContext from pydantic_ai, not from pydantic_ai._run_context."""

    def test_hooked_toolset_uses_public_runcontext_import(self) -> None:
        """hooked.py imports RunContext from pydantic_ai and not from pydantic_ai._run_context."""
        tree = _parse(_HOOKED_PY)
        assert "RunContext" in _imported_names_from(tree, "pydantic_ai"), (
            "hooked.py does not import RunContext from pydantic_ai (public API)"
        )
        assert "RunContext" not in _imported_names_from(tree, "pydantic_ai._run_context"), (
            "hooked.py still imports RunContext from private pydantic_ai._run_context"
        )


# ---------------------------------------------------------------------------
# AC3 — gate.py must import RunContext from pydantic_ai (public)
# ---------------------------------------------------------------------------


class TestFromAC_ApprovalGatePublicRunContext:
    """gate.py must import RunContext from pydantic_ai, not from pydantic_ai._run_context."""

    def test_approval_gate_uses_public_runcontext_import(self) -> None:
        """gate.py imports RunContext from pydantic_ai and not from pydantic_ai._run_context."""
        tree = _parse(_GATE_PY)
        assert "RunContext" in _imported_names_from(tree, "pydantic_ai"), (
            "gate.py does not import RunContext from pydantic_ai (public API)"
        )
        assert "RunContext" not in _imported_names_from(tree, "pydantic_ai._run_context"), (
            "gate.py still imports RunContext from private pydantic_ai._run_context"
        )


# ---------------------------------------------------------------------------
# AC4 — agent.py TYPE_CHECKING block defines a public HistoryProcessor alias
# ---------------------------------------------------------------------------


class TestFromAC_AgentHistoryProcessorAlias:
    """agent.py TYPE_CHECKING block must define a public HistoryProcessor alias."""

    def test_agent_historyprocessor_alias_supports_public_sync_async_shapes(self) -> None:
        """agent.py TYPE_CHECKING block omits pydantic_ai._agent_graph import.

        Defines a local HistoryProcessor alias using RunContext and ModelMessage
        for both sync and async callable variants with and without context.
        """
        tree = _parse(_AGENT_PY)

        # --- Part 1: no import from pydantic_ai._agent_graph ---
        agent_graph_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "pydantic_ai._agent_graph"
        ]
        assert not agent_graph_imports, (
            "agent.py still imports from pydantic_ai._agent_graph; "
            "must be replaced by a local alias using public types"
        )

        # --- Part 2: local HistoryProcessor alias inside TYPE_CHECKING block ---
        tc_body = _type_checking_body(tree)
        assert tc_body, "No TYPE_CHECKING block found in agent.py"

        _type_alias_cls = getattr(ast, "TypeAlias", None)
        hp_assignment: ast.AST | None = None

        for stmt in tc_body:
            if isinstance(stmt, ast.Assign):
                if any(
                    isinstance(t, ast.Name) and t.id == "HistoryProcessor" for t in stmt.targets
                ):
                    hp_assignment = stmt
                    break
            elif isinstance(stmt, ast.AnnAssign):
                if isinstance(stmt.target, ast.Name) and stmt.target.id == "HistoryProcessor":
                    hp_assignment = stmt
                    break
            elif (  # Python 3.12+ `type X = ...` statement
                _type_alias_cls is not None
                and isinstance(stmt, _type_alias_cls)  # type: ignore[arg-type]
                and isinstance(getattr(stmt, "name", None), ast.Name)
                and stmt.name.id == "HistoryProcessor"  # type: ignore[union-attr]
            ):
                hp_assignment = stmt
                break

        assert hp_assignment is not None, (
            "No local HistoryProcessor alias assignment found "
            "in the TYPE_CHECKING block of agent.py"
        )

        # --- Part 3: alias references public RunContext and ModelMessage ---
        alias_names = _all_name_ids(hp_assignment)
        assert "RunContext" in alias_names, (
            f"HistoryProcessor alias must reference RunContext; found names: {sorted(alias_names)}"
        )
        assert "ModelMessage" in alias_names, (
            f"HistoryProcessor alias must reference ModelMessage; "
            f"found names: {sorted(alias_names)}"
        )

        # --- Part 4: async shape present (Awaitable or Coroutine) ---
        async_indicators = {"Awaitable", "Coroutine"}
        assert alias_names & async_indicators, (
            f"HistoryProcessor alias must cover async variants (Awaitable or Coroutine); "
            f"found names: {sorted(alias_names)}"
        )
