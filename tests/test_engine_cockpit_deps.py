"""Failing tests for engine public properties + cockpit deps fix (#1222).

AC1: serve/cockpit/pyproject.toml lists ruamel.yaml in dependencies
AC2: KanbanEngine exposes tasks_dir and kanban_dir as public read-only properties
AC3: deps.py uses public properties instead of engine._tasks_dir / engine._kanban_dir
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Minimal board fixture helper
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1: pyproject.toml declares ruamel.yaml
# ---------------------------------------------------------------------------


class TestFromAC_CockpitDependencyDeclaration:
    """AC1: serve/cockpit/pyproject.toml must list ruamel.yaml as a dependency."""

    def test_ruamel_yaml_in_cockpit_pyproject(self, project_root: Path) -> None:
        pyproject = project_root / "serve" / "cockpit" / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert "ruamel.yaml" in content, "serve/cockpit/pyproject.toml must declare ruamel.yaml as a dependency"


# ---------------------------------------------------------------------------
# AC2: KanbanEngine exposes tasks_dir and kanban_dir as public read-only props
# ---------------------------------------------------------------------------


class TestFromAC_EnginePublicProperties:
    """AC2: KanbanEngine must expose tasks_dir and kanban_dir as public read-only properties."""

    def test_tasks_dir_property_accessible(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        assert hasattr(engine, "tasks_dir"), "KanbanEngine must expose a public 'tasks_dir' property"

    def test_tasks_dir_returns_expected_path(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        assert engine.tasks_dir == kanban_dir / "tasks"

    def test_tasks_dir_is_read_only(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        with pytest.raises(AttributeError):
            engine.tasks_dir = tmp_path / "other"  # type: ignore[misc]

    def test_kanban_dir_property_accessible(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        assert hasattr(engine, "kanban_dir"), "KanbanEngine must expose a public 'kanban_dir' property"

    def test_kanban_dir_returns_expected_path(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        assert engine.kanban_dir == kanban_dir

    def test_kanban_dir_is_read_only(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        with pytest.raises(AttributeError):
            engine.kanban_dir = tmp_path / "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC3: deps.py must not access private attributes
# ---------------------------------------------------------------------------


class TestFromAC_DepsUsesPublicProperties:
    """AC3: owlbear_cockpit.deps must use public properties, not private attrs."""

    def test_deps_does_not_access_private_tasks_dir(self, project_root: Path) -> None:
        deps_path = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "deps.py"
        content = deps_path.read_text(encoding="utf-8")
        assert "_tasks_dir" not in content, (
            "deps.py must not access engine._tasks_dir; use the public 'tasks_dir' property"
        )

    def test_deps_does_not_access_private_kanban_dir(self, project_root: Path) -> None:
        deps_path = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "deps.py"
        content = deps_path.read_text(encoding="utf-8")
        assert "_kanban_dir" not in content, (
            "deps.py must not access engine._kanban_dir; use the public 'kanban_dir' property"
        )
