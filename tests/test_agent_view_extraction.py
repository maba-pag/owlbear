"""Tests for AgentView extraction from engine.py (task #1216).

AC (refined per architecture re-review 2026-05-04):
  1. engine.py does NOT contain `class AgentView`
  2. agent_view.py contains AgentView class exposing all 8 public methods:
     list_tasks, show_task, pick_tasks, create_task, edit_task, move_task, start_work, end_work
  3. agent_view.py imports KanbanEngine from engine (no circular import)
  4. Package __init__.py re-exports AgentView from agent_view (backward-compatible public API)
  5. Backward-compatible access: `from owlbear_kanban.engine import AgentView` resolves via __getattr__
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# AC#1 — engine.py does NOT contain `class AgentView`
# ---------------------------------------------------------------------------


class TestFromAC_EngineNoLongerContainsAgentView:
    """engine.py must not define AgentView after extraction."""

    def test_engine_module_does_not_define_agent_view(self) -> None:
        """AgentView should not be a class defined in the engine module itself."""
        import owlbear_kanban.engine as engine_mod

        # If AgentView is still defined in engine.py, it will have
        # __module__ == 'owlbear_kanban.engine'. After extraction it should
        # live in owlbear_kanban.agent_view and only be *re-exported* from engine.
        assert not hasattr(engine_mod, "AgentView") or (
            getattr(engine_mod.AgentView, "__module__", "") != "owlbear_kanban.engine"
        ), "class AgentView is still defined in owlbear_kanban.engine — it must be moved to owlbear_kanban.agent_view"

    def test_engine_source_does_not_contain_agent_view_class_definition(
        self,
    ) -> None:
        """Source of engine.py must not contain `class AgentView`."""
        engine_file = Path(__file__).parent.parent / "serve/kanban/src/owlbear_kanban/engine.py"
        source = engine_file.read_text()
        assert "class AgentView" not in source, (
            "engine.py still contains `class AgentView` — the class must be extracted to agent_view.py"
        )


# ---------------------------------------------------------------------------
# AC#2 — agent_view.py contains AgentView with identical public interface
# ---------------------------------------------------------------------------

_EXPECTED_PUBLIC_METHODS = {
    "list_tasks",
    "show_task",
    "pick_tasks",
    "create_task",
    "edit_task",
    "move_task",
    "start_work",
    "end_work",
}


class TestFromAC_AgentViewModuleExists:
    """owlbear_kanban.agent_view must exist and expose AgentView."""

    def test_agent_view_module_is_importable(self) -> None:
        """owlbear_kanban.agent_view must be a valid importable module."""
        import importlib as _importlib

        # Raises ModuleNotFoundError if file doesn't exist yet.
        mod = _importlib.import_module("owlbear_kanban.agent_view")
        assert mod is not None

    def test_agent_view_module_has_agent_view_class(self) -> None:
        """owlbear_kanban.agent_view must define the AgentView class."""
        from owlbear_kanban.agent_view import AgentView  # noqa: F401 (import is the assertion)

        assert inspect.isclass(AgentView)

    def test_agent_view_class_has_all_public_methods(self) -> None:
        """AgentView in agent_view.py must expose the same public interface."""
        from owlbear_kanban.agent_view import AgentView

        missing = _EXPECTED_PUBLIC_METHODS - {
            name for name, _ in inspect.getmembers(AgentView, predicate=inspect.isfunction)
        }
        assert not missing, f"AgentView in agent_view.py is missing public methods: {missing}"


# ---------------------------------------------------------------------------
# AC#3 — agent_view.py imports KanbanEngine from engine (no circular import)
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewImportsKanbanEngine:
    """agent_view.py must import KanbanEngine from owlbear_kanban.engine."""

    def test_agent_view_module_references_kanban_engine(self) -> None:
        """KanbanEngine must be accessible in the agent_view module namespace."""
        import owlbear_kanban.agent_view as av_mod

        assert hasattr(av_mod, "KanbanEngine"), "owlbear_kanban.agent_view does not import KanbanEngine from engine"

    def test_no_circular_import_between_agent_view_and_engine(self) -> None:
        """Importing agent_view must not trigger a circular import error."""
        # Drop cached modules to force a fresh import cycle.
        for key in list(sys.modules.keys()):
            if "owlbear_kanban" in key:
                sys.modules.pop(key, None)
        try:
            import owlbear_kanban.agent_view  # noqa: F401
            import owlbear_kanban.engine  # noqa: F401
        except ImportError as exc:
            pytest.fail(f"Circular import detected: {exc}")


# ---------------------------------------------------------------------------
# AC#4 — Package __init__.py re-exports AgentView from agent_view
# ---------------------------------------------------------------------------


class TestFromAC_PackageReexportsAgentView:
    """owlbear_kanban.__init__ must source AgentView from agent_view, not engine."""

    def test_package_agent_view_originates_from_agent_view_module(self) -> None:
        """AgentView exported from the package must be defined in agent_view."""
        from owlbear_kanban import AgentView

        assert AgentView.__module__ == "owlbear_kanban.agent_view", (
            f"AgentView.__module__ == {AgentView.__module__!r}; "
            "expected 'owlbear_kanban.agent_view' — "
            "__init__.py must re-export from agent_view, not engine"
        )

    def test_package_init_imports_agent_view_from_agent_view_module(self) -> None:
        """__init__.py must import AgentView from agent_view, not engine."""
        init_file = Path(__file__).parent.parent / "serve/kanban/src/owlbear_kanban/__init__.py"
        source = init_file.read_text()
        assert "from owlbear_kanban.agent_view import" in source or (
            "from owlbear_kanban import agent_view" in source
        ), (
            "__init__.py does not import AgentView from owlbear_kanban.agent_view — "
            "re-export from agent_view module is required"
        )


# ---------------------------------------------------------------------------
# AC#5 — Existing public API unchanged (regression guard)
# ---------------------------------------------------------------------------


class TestFromAC_ExistingAPIUnchanged:
    """AgentView accessed via the package must remain fully functional."""

    def test_agent_view_from_agent_view_module_is_instantiable(self, tmp_path: Path) -> None:
        """AgentView from agent_view.py can be instantiated with a KanbanEngine."""
        from owlbear_kanban.agent_view import AgentView
        from owlbear_kanban import KanbanEngine

        config = tmp_path / "config.yml"
        config.write_text("schema: grouped\nstatuses:\n  - todo\n  - done\nagents: []\n")
        (tmp_path / "tasks").mkdir()

        engine = KanbanEngine(tmp_path)
        av = AgentView(engine)
        assert av.engine is engine

    def test_package_import_of_agent_view_comes_from_agent_view_module(self) -> None:
        """Backward-compatible import still works AND originates from agent_view."""
        from owlbear_kanban import AgentView

        # Regression guard: the class is still importable from the package,
        # AND after extraction it must live in agent_view (not engine).
        assert inspect.isclass(AgentView)
        assert AgentView.__module__ == "owlbear_kanban.agent_view", (
            f"Backward-compat import of AgentView still resolves to "
            f"{AgentView.__module__!r} instead of 'owlbear_kanban.agent_view'"
        )

    def test_agent_view_init_stores_engine_reference(self, tmp_path: Path) -> None:
        """AgentView.__init__ must accept a KanbanEngine and store it as .engine."""
        from owlbear_kanban.agent_view import AgentView
        from owlbear_kanban import KanbanEngine

        config = tmp_path / "config.yml"
        config.write_text("schema: grouped\nstatuses:\n  - todo\n  - done\nagents: []\n")
        (tmp_path / "tasks").mkdir()

        engine = KanbanEngine(tmp_path)
        av = AgentView(engine)
        assert av.engine is engine, "AgentView.engine must be the KanbanEngine passed to __init__"


# ---------------------------------------------------------------------------
# AC#5 (refined) — `from owlbear_kanban.engine import AgentView` via __getattr__
# ---------------------------------------------------------------------------


class TestFromAC_BackwardCompatEngineImport:
    """`from owlbear_kanban.engine import AgentView` must resolve via __getattr__."""

    def test_engine_import_of_agent_view_does_not_raise(self) -> None:
        """`from owlbear_kanban.engine import AgentView` must not raise."""
        try:
            from owlbear_kanban.engine import AgentView  # noqa: F401
        except (ImportError, AttributeError) as exc:
            pytest.fail(f"from owlbear_kanban.engine import AgentView raised: {exc}")

    def test_engine_import_of_agent_view_originates_from_agent_view_module(
        self,
    ) -> None:
        """AgentView accessed via engine.__getattr__ must be defined in agent_view."""
        from owlbear_kanban.engine import AgentView  # noqa: PLC0415

        assert AgentView.__module__ == "owlbear_kanban.agent_view", (
            f"from owlbear_kanban.engine import AgentView resolved to "
            f"{AgentView.__module__!r} instead of 'owlbear_kanban.agent_view' — "
            "__getattr__ must proxy to agent_view.AgentView, not re-define it in engine"
        )

    def test_engine_import_of_agent_view_is_same_class_as_agent_view_module(
        self,
    ) -> None:
        """AgentView from engine import must be the identical object as agent_view.AgentView."""
        from owlbear_kanban.engine import AgentView as AgentViewFromEngine
        from owlbear_kanban.agent_view import AgentView as AgentViewFromModule

        assert AgentViewFromEngine is AgentViewFromModule, (
            "AgentView from `owlbear_kanban.engine` is not the same object as "
            "`owlbear_kanban.agent_view.AgentView` — __getattr__ must return "
            "the exact same class, not a copy or re-implementation"
        )
