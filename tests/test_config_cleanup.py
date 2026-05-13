"""RED-phase failing tests for config validation cleanup (#1343).

Acceptance criteria coverage:
- AC1 (td:2): Remove agent_name from KanbanEngine.__init__ — 4 tests
- AC2 (td:1): Cockpit launch wiring no longer passes agent_name= — 1 test
- AC3 (td:1): CockpitView source="cockpit" labeling preserved — covered by
              existing mutation tests; no new failing tests available
- AC4 (td:2): Lazy agent_map preserved — test_engine_lazy_agent_map_1221
              TestFromAC_InitNoLongerRaises + TestFromAC_CockpitInitWithEmptyAgentMap
              must go GREEN after builder removes agent_name param
- AC5 (td:2): pick_tasks validates agent_map — test_engine_lazy_agent_map_1221
              TestFromAC_PickTasksValidatesAgentMap already green; preserved
- AC6 (td:2): Stale D24 eager-validation assertions replaced by lazy contract;
              builder rewrites TestFromAC_AgentMapCoverage in test_engine_init_1067.py;
              lazy contract (init succeeds, pick_tasks raises) verified in lazy_1221
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
next_id: 1
"""


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_RemoveAgentNameParam  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_RemoveAgentNameParam:
    """AC1: KanbanEngine.__init__ must not accept agent_name as a keyword argument.

    Internal _agent_name state and the agent_name property are preserved;
    only the constructor keyword parameter is removed.
    """

    def test_constructor_signature_excludes_agent_name(self) -> None:
        """agent_name must not appear in KanbanEngine.__init__ parameter list.

        RED: currently fails — agent_name IS in the signature with default None.
        """
        sig = inspect.signature(KanbanEngine.__init__)
        assert "agent_name" not in sig.parameters, (
            "KanbanEngine.__init__ still exposes 'agent_name' as a constructor "
            f"parameter; parameters found: {list(sig.parameters)}"
        )

    def test_passing_agent_name_string_raises_type_error(self, tmp_path: Path) -> None:
        """KanbanEngine(kanban_dir, agent_name='cockpit') must raise TypeError.

        RED: currently succeeds — agent_name='cockpit' is silently accepted and
        used to seed the internal _agent_name field.
        """
        kanban_dir = _make_board(tmp_path)
        with pytest.raises(TypeError):
            KanbanEngine(kanban_dir, agent_name="cockpit")

    def test_passing_agent_name_none_raises_type_error(self, tmp_path: Path) -> None:
        """KanbanEngine(kanban_dir, agent_name=None) must raise TypeError.

        None must not be treated as a silent no-op (use-random-name fallback).
        The parameter must not exist at all — passing agent_name=None must be
        as rejected as any other value.

        RED: currently succeeds — agent_name=None hits the ``if agent_name is not
        None`` branch and falls through to random name generation.
        """
        kanban_dir = _make_board(tmp_path)
        with pytest.raises(TypeError):
            KanbanEngine(kanban_dir, agent_name=None)

    def test_agent_name_property_preserved_after_param_removal(
        self, tmp_path: Path
    ) -> None:
        """After param removal, engine.agent_name property still returns a non-empty string.

        Guards against the builder accidentally removing internal random-name
        generation alongside the constructor parameter.  The property must still
        work and return the session-stable adjective-noun name.

        This test fails in RED on the sig assertion.  After the builder removes
        the param, both the sig check and the property assertion must pass.
        """
        sig = inspect.signature(KanbanEngine.__init__)
        assert "agent_name" not in sig.parameters  # RED: currently fails
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        name = engine.agent_name
        assert isinstance(name, str), f"engine.agent_name must be a str; got: {name!r}"
        assert name, f"engine.agent_name must be non-empty; got: {name!r}"


# ---------------------------------------------------------------------------
# TestFromAC_CallerCleanup  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_CallerCleanup:
    """AC2: All first-party callers must no longer pass agent_name= to KanbanEngine.

    The Cockpit launch path is the primary known caller.
    """

    def test_cockpit_run_does_not_pass_agent_name(self) -> None:
        """Cockpit main.run() source must not contain an agent_name= keyword argument.

        RED: currently fails — main.py line 74 reads:
            engine = KanbanEngine(kanban_dir)
        After the builder removes the constructor param and updates the caller,
        agent_name must not appear anywhere in run().
        """
        from owlbear_cockpit.main import run  # noqa: PLC0415

        source = inspect.getsource(run)
        assert "agent_name" not in source, (
            "cockpit main.run() still passes agent_name= to KanbanEngine.\n"
            "Remove the agent_name='cockpit' argument from the KanbanEngine(...) call.\n"
            f"Current source of run():\n{source}"
        )
