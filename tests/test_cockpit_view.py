from __future__ import annotations

# --- merged from tests/test_cockpit_view_1224.py ---
"""Failing tests for CockpitView relocation: kanban → cockpit package (#1224).

AC1 (td:2): CockpitView importable from owlbear_cockpit.view (new file)
AC2 (td:2): KanbanEngine.cockpit_view() + _cockpit_view removed; engine.py defines no CockpitView class;
            engine.py contains zero import/from references to owlbear_cockpit [cycle 2: import-boundary proof]
AC3 (td:2): Source consumers (deps.py, routes/read.py, routes/mutation.py) import from owlbear_cockpit.view
AC4 (td:2): Test files updated — no test file imports CockpitView from owlbear_kanban.engine
AC5a (td:2): Kanban-package CockpitView test classes removed from serve/kanban/tests/;
             includes TestFromAC_CockpitViewParentForwarding, _make_cockpit_view helper,
             and CockpitView import in test_engine_list_show_1071.py [cycle 2 expanded]
AC5b (td:2): CockpitView behavioral equivalence for list_tasks, show_task, board_config
             re-homed to this suite [cycle 2 new]
AC6 (td:1): CockpitView implementation does not access private engine attributes (no ._-prefixed fields)
AC7 (td:1): serve/kanban/README.md cockpit_view() row removed from engine accessor table
AC10 (td:1): Task-owned tests use KanbanEngine(kanban_dir) without agent_name parameter [cycle 2 new]
"""


import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Board fixture helper (minimal valid board)
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1: CockpitView importable from owlbear_cockpit.view (new module)
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewNewModule:
    """AC1: CockpitView must be importable from owlbear_cockpit.view."""

    def test_view_py_file_exists(self, project_root: Path) -> None:
        view_file = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "view.py"
        assert view_file.exists(), (
            "serve/cockpit/src/owlbear_cockpit/view.py must exist — "
            "CockpitView class should be defined here after relocation"
        )

    def test_cockpit_view_importable_from_new_path(self) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        assert CockpitView is not None, "CockpitView must be importable from owlbear_cockpit.view"

    def test_cockpit_view_instantiable_from_new_module(self, tmp_path: Path) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        assert view is not None, "CockpitView(engine) must construct successfully from new module"

    def test_cockpit_view_has_list_tasks(self, tmp_path: Path) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        assert callable(getattr(view, "list_tasks", None)), (
            "CockpitView from owlbear_cockpit.view must expose list_tasks"
        )

    def test_cockpit_view_has_show_task(self, tmp_path: Path) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        assert callable(getattr(view, "show_task", None)), "CockpitView from owlbear_cockpit.view must expose show_task"

    def test_cockpit_view_has_edit_task(self, tmp_path: Path) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        assert callable(getattr(view, "edit_task", None)), "CockpitView from owlbear_cockpit.view must expose edit_task"

    def test_cockpit_view_has_move_task(self, tmp_path: Path) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        assert callable(getattr(view, "move_task", None)), "CockpitView from owlbear_cockpit.view must expose move_task"

    def test_cockpit_view_has_release_task(self, tmp_path: Path) -> None:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        assert callable(getattr(view, "release_task", None)), (
            "CockpitView from owlbear_cockpit.view must expose release_task"
        )


# ---------------------------------------------------------------------------
# AC2: KanbanEngine cleanup — no cockpit_view() property, no _cockpit_view
# ---------------------------------------------------------------------------


class TestFromAC_EngineCleanup:
    """AC2: KanbanEngine must not expose cockpit_view() or _cockpit_view after relocation."""

    def test_engine_has_no_cockpit_view_property(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        assert not hasattr(engine, "cockpit_view"), (
            "KanbanEngine must NOT have a cockpit_view property after CockpitView relocation"
        )

    def test_engine_class_has_no_cockpit_view_attribute(self) -> None:
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        assert not hasattr(KanbanEngine, "cockpit_view"), (
            "KanbanEngine class must NOT have a cockpit_view descriptor after relocation"
        )

    def test_engine_instance_has_no_private_cockpit_view(self, tmp_path: Path) -> None:
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        assert not hasattr(engine, "_cockpit_view"), (
            "KanbanEngine must NOT initialize a _cockpit_view attribute after relocation"
        )

    def test_engine_py_does_not_define_cockpit_view_class(self, project_root: Path) -> None:
        engine_py = project_root / "serve" / "kanban" / "src" / "owlbear_kanban" / "engine.py"
        source = engine_py.read_text(encoding="utf-8")
        assert "class CockpitView" not in source, (
            "engine.py must not contain 'class CockpitView' after relocation to owlbear_cockpit.view"
        )

    def test_engine_py_has_no_cockpit_view_property_def(self, project_root: Path) -> None:
        engine_py = project_root / "serve" / "kanban" / "src" / "owlbear_kanban" / "engine.py"
        source = engine_py.read_text(encoding="utf-8")
        # Match "def cockpit_view" as a method/property definition
        assert not re.search(r"def cockpit_view\b", source), (
            "engine.py must not define a cockpit_view method/property after relocation"
        )

    def test_engine_py_has_no_owlbear_cockpit_import(self, project_root: Path) -> None:
        """AC2: engine.py must have zero import/from lines referencing owlbear_cockpit."""
        engine_py = project_root / "serve" / "kanban" / "src" / "owlbear_kanban" / "engine.py"
        source = engine_py.read_text(encoding="utf-8")
        hits = re.findall(r"^.*owlbear_cockpit.*$", source, re.MULTILINE)
        assert not hits, f"engine.py must contain zero references to owlbear_cockpit; found: {hits}"


# ---------------------------------------------------------------------------
# AC3: Source consumers import CockpitView from owlbear_cockpit.view
# ---------------------------------------------------------------------------


class TestFromAC_SourceConsumersImport:
    """AC3: deps.py, routes/read.py, routes/mutation.py must import from owlbear_cockpit.view."""

    def test_deps_py_imports_from_owlbear_cockpit_view(self, project_root: Path) -> None:
        deps_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "deps.py"
        source = deps_py.read_text(encoding="utf-8")
        assert "from owlbear_cockpit.view import CockpitView" in source, (
            "deps.py must import CockpitView from owlbear_cockpit.view, not from owlbear_kanban.engine"
        )

    def test_deps_py_does_not_import_from_kanban_engine(self, project_root: Path) -> None:
        deps_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "deps.py"
        source = deps_py.read_text(encoding="utf-8")
        assert "from owlbear_kanban.engine import CockpitView" not in source, (
            "deps.py must NOT import CockpitView from owlbear_kanban.engine after relocation"
        )

    def test_routes_read_imports_from_owlbear_cockpit_view(self, project_root: Path) -> None:
        read_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "routes" / "read.py"
        source = read_py.read_text(encoding="utf-8")
        assert "from owlbear_cockpit.view import CockpitView" in source, (
            "routes/read.py must import CockpitView from owlbear_cockpit.view"
        )

    def test_routes_read_does_not_import_from_kanban_engine(self, project_root: Path) -> None:
        read_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "routes" / "read.py"
        source = read_py.read_text(encoding="utf-8")
        assert "from owlbear_kanban.engine import CockpitView" not in source, (
            "routes/read.py must NOT import CockpitView from owlbear_kanban.engine after relocation"
        )

    def test_routes_mutation_imports_from_owlbear_cockpit_view(self, project_root: Path) -> None:
        mutation_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "routes" / "mutation.py"
        source = mutation_py.read_text(encoding="utf-8")
        assert "from owlbear_cockpit.view import CockpitView" in source, (
            "routes/mutation.py must import CockpitView from owlbear_cockpit.view"
        )

    def test_routes_mutation_does_not_import_from_kanban_engine(self, project_root: Path) -> None:
        mutation_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "routes" / "mutation.py"
        source = mutation_py.read_text(encoding="utf-8")
        assert "from owlbear_kanban.engine import CockpitView" not in source, (
            "routes/mutation.py must NOT import CockpitView from owlbear_kanban.engine after relocation"
        )


# ---------------------------------------------------------------------------
# AC4: Test files updated — no old import path remaining
# ---------------------------------------------------------------------------


class TestFromAC_TestFileImportUpdates:
    """AC4: Root test files must not import CockpitView from owlbear_kanban.engine."""

    def _assert_no_old_import(self, test_file: Path) -> None:
        source = test_file.read_text(encoding="utf-8")
        pattern = r"from owlbear_kanban\.engine import[^\n]*CockpitView"
        assert not re.search(pattern, source), (
            f"{test_file.name} must not import CockpitView from owlbear_kanban.engine; "
            "update to: from owlbear_cockpit.view import CockpitView"
        )

    def _assert_new_import_present(self, test_file: Path) -> None:
        """AC4 cycle 3: file must contain canonical new import path."""
        source = test_file.read_text(encoding="utf-8")
        pattern = r"from owlbear_cockpit\.view import CockpitView"
        assert re.search(pattern, source), (
            f"{test_file.name} must contain 'from owlbear_cockpit.view import CockpitView' after import path update"
        )

    def test_engine_cockpit_view_test_import_updated(self, project_root: Path) -> None:
        self._assert_no_old_import(project_root / "tests" / "test_engine_cockpit_view.py")

    def test_engine_release_task_occ_import_updated(self, project_root: Path) -> None:
        self._assert_no_old_import(project_root / "tests" / "test_engine_release_task_occ.py")

    def test_cockpit_kanban_routes_import_updated(self, project_root: Path) -> None:
        self._assert_no_old_import(project_root / "tests" / "test_cockpit_kanban_routes.py")

    def test_cockpit_mutation_api_1132_import_updated(self, project_root: Path) -> None:
        self._assert_no_old_import(project_root / "tests" / "test_cockpit_mutation_api_1132.py")

    def test_cockpit_read_api_import_updated(self, project_root: Path) -> None:
        self._assert_no_old_import(project_root / "tests" / "test_cockpit_read_api.py")

    def test_cockpit_read_api_import_updated_1223(self, project_root: Path) -> None:
        self._assert_no_old_import(project_root / "tests" / "test_cockpit_read_api.py")

    # AC4 cycle 3: positive import assertions (new-path string must be present)

    def test_engine_cockpit_view_test_has_new_import(self, project_root: Path) -> None:
        """AC4 cycle 3: test_engine_cockpit_view.py must positively import from owlbear_cockpit.view."""
        self._assert_new_import_present(project_root / "tests" / "test_engine_cockpit_view.py")

    def test_engine_release_task_occ_has_new_import(self, project_root: Path) -> None:
        """AC4 cycle 3: test_engine_release_task_occ.py must positively import from owlbear_cockpit.view."""
        self._assert_new_import_present(project_root / "tests" / "test_engine_release_task_occ.py")

    def test_cockpit_kanban_routes_has_new_import(self, project_root: Path) -> None:
        """AC4 cycle 3: test_cockpit_kanban_routes.py must positively import from owlbear_cockpit.view."""
        self._assert_new_import_present(project_root / "tests" / "test_cockpit_kanban_routes.py")

    def test_cockpit_mutation_api_1132_has_new_import(self, project_root: Path) -> None:
        """AC4 cycle 3: test_cockpit_mutation_api_1132.py must positively import from owlbear_cockpit.view."""
        self._assert_new_import_present(project_root / "tests" / "test_cockpit_mutation_api_1132.py")

    def test_cockpit_read_api_has_new_import(self, project_root: Path) -> None:
        """AC4 cycle 3: test_cockpit_read_api.py must positively import from owlbear_cockpit.view."""
        self._assert_new_import_present(project_root / "tests" / "test_cockpit_read_api.py")

    def test_cockpit_read_api_has_new_import_1223(self, project_root: Path) -> None:
        """AC4 cycle 3: test_cockpit_read_api.py must positively import from owlbear_cockpit.view."""
        self._assert_new_import_present(project_root / "tests" / "test_cockpit_read_api.py")


# ---------------------------------------------------------------------------
# AC5: Kanban-package test files — CockpitView test classes removed
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTestCleanup:
    """AC5: CockpitView test coverage must be removed from serve/kanban/tests/."""

    def test_engine_init_1067_no_cockpit_view_constructability_test(self, project_root: Path) -> None:
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_init_1067.py"
        source = test_file.read_text(encoding="utf-8")
        assert "CockpitView" not in source, (
            "test_engine_init_1067.py must not contain CockpitView after relocation; "
            "equivalent coverage lives in tests/test_engine_cockpit_view.py"
        )

    def test_engine_init_1068_no_cockpit_view_method_stubs_class(self, project_root: Path) -> None:
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_init_1068.py"
        source = test_file.read_text(encoding="utf-8")
        assert "TestFromAC_CockpitViewMethodStubs" not in source, (
            "test_engine_init_1068.py must not contain TestFromAC_CockpitViewMethodStubs; "
            "CockpitView tests belong in owlbear_cockpit package suite"
        )

    def test_engine_init_1068_no_views_constructed_at_init_cockpit_tests(self, project_root: Path) -> None:
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_init_1068.py"
        source = test_file.read_text(encoding="utf-8")
        # The cockpit_view() accessor test must be gone
        assert "engine.cockpit_view()" not in source, (
            "test_engine_init_1068.py must not test engine.cockpit_view() after relocation; "
            "the accessor is removed from KanbanEngine"
        )

    def test_engine_list_show_1071_no_cockpit_view_list_tasks_class(self, project_root: Path) -> None:
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_list_show_1071.py"
        source = test_file.read_text(encoding="utf-8")
        assert "TestFromAC_CockpitViewListTasks" not in source, (
            "test_engine_list_show_1071.py must not contain TestFromAC_CockpitViewListTasks; "
            "CockpitView tests belong in owlbear_cockpit package suite"
        )

    def test_engine_list_show_1071_no_cockpit_view_show_task_class(self, project_root: Path) -> None:
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_list_show_1071.py"
        source = test_file.read_text(encoding="utf-8")
        assert "TestFromAC_CockpitViewShowTask" not in source, (
            "test_engine_list_show_1071.py must not contain TestFromAC_CockpitViewShowTask; "
            "CockpitView tests belong in owlbear_cockpit package suite"
        )

    def test_engine_list_show_1071_no_cockpit_view_parent_forwarding_class(self, project_root: Path) -> None:
        """AC5a: TestFromAC_CockpitViewParentForwarding must be removed from kanban suite."""
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_list_show_1071.py"
        source = test_file.read_text(encoding="utf-8")
        assert "TestFromAC_CockpitViewParentForwarding" not in source, (
            "test_engine_list_show_1071.py must not contain TestFromAC_CockpitViewParentForwarding; "
            "equivalent parent-filter behavioral coverage belongs in tests/test_cockpit_view_1224.py"
        )

    def test_engine_list_show_1071_no_make_cockpit_view_helper(self, project_root: Path) -> None:
        """AC5a: _make_cockpit_view helper must be removed once all CockpitView references are gone."""
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_list_show_1071.py"
        source = test_file.read_text(encoding="utf-8")
        assert "_make_cockpit_view" not in source, (
            "test_engine_list_show_1071.py must not contain _make_cockpit_view helper; "
            "CockpitView is no longer tested in the kanban package suite"
        )

    def test_engine_list_show_1071_no_cockpit_view_import(self, project_root: Path) -> None:
        """AC5a: CockpitView import must be removed from test_engine_list_show_1071.py."""
        test_file = project_root / "serve" / "kanban" / "tests" / "test_engine_list_show_1071.py"
        source = test_file.read_text(encoding="utf-8")
        assert "CockpitView" not in source, (
            "test_engine_list_show_1071.py must not import or reference CockpitView; "
            "all CockpitView coverage belongs in the cockpit package suite"
        )


# ---------------------------------------------------------------------------
# AC6: CockpitView implementation does not access private engine attributes
# ---------------------------------------------------------------------------


class TestFromAC_ViewNoPrivateAccess:
    """AC6: view.py must not use any ._-prefixed engine attributes."""

    def test_view_py_has_no_private_engine_attribute_access(self, project_root: Path) -> None:
        view_py = project_root / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "view.py"
        source = view_py.read_text(encoding="utf-8")
        # Match self.engine._ or engine._ attribute access patterns
        private_access = re.findall(r"\bengine\._\w+", source)
        assert not private_access, f"view.py must not access private engine attributes; found: {private_access}"


# ---------------------------------------------------------------------------
# AC7: serve/kanban/README.md — cockpit_view() row removed
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeCleanup:
    """AC7: serve/kanban/README.md must not list cockpit_view() in the engine accessor table."""

    def test_readme_has_no_cockpit_view_row(self, project_root: Path) -> None:
        readme = project_root / "serve" / "kanban" / "README.md"
        source = readme.read_text(encoding="utf-8")
        assert "cockpit_view()" not in source, (
            "serve/kanban/README.md must not contain a cockpit_view() row; the accessor is removed from KanbanEngine"
        )


# ---------------------------------------------------------------------------
# AC5b: CockpitView behavioral equivalence — list_tasks, show_task, board_config
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewBehavior:
    """AC5b: Relocated CockpitView must delegate correctly for list_tasks, show_task, board_config."""

    def _make_view(self, tmp_path: Path) -> object:
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        return CockpitView(engine)

    def _make_view_with_task(self, tmp_path: Path) -> tuple[object, int]:
        """Return (view, task_id) with one task created on the board."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        task = engine.create_task("Test Task")
        view = CockpitView(engine)
        return view, task.id

    def test_list_tasks_empty_board_returns_empty_list(self, tmp_path: Path) -> None:
        """AC5b: CockpitView.list_tasks() on empty board returns a response with no tasks."""
        view = self._make_view(tmp_path)
        result = view.list_tasks()  # type: ignore[union-attr]
        assert result.tasks == [], "CockpitView.list_tasks() on empty board must return tasks=[]"

    def test_list_tasks_returns_created_tasks(self, tmp_path: Path) -> None:
        """AC5b: CockpitView.list_tasks() returns tasks that were created via the engine."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.create_task("Alpha")
        engine.create_task("Beta")
        view = CockpitView(engine)
        result = view.list_tasks()
        titles = [t.title for t in result.tasks]
        assert "Alpha" in titles, f"CockpitView.list_tasks() must include 'Alpha'; got titles: {titles}"
        assert "Beta" in titles, f"CockpitView.list_tasks() must include 'Beta'; got titles: {titles}"

    def test_list_tasks_parent_filter_returns_children_only(self, tmp_path: Path) -> None:
        """AC5b: CockpitView.list_tasks(parent=N) returns only direct children of N."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        parent_task = engine.create_task("Parent")
        child_task = engine.create_task("Child", parent=parent_task.id)
        _other = engine.create_task("Unrelated")
        view = CockpitView(engine)
        result = view.list_tasks(parent=parent_task.id)
        ids = [t.id for t in result.tasks]
        assert child_task.id in ids, (
            f"CockpitView.list_tasks(parent={parent_task.id}) must include child task {child_task.id}; got {ids}"
        )
        assert _other.id not in ids, (
            f"CockpitView.list_tasks(parent={parent_task.id}) must exclude unrelated task {_other.id}; got {ids}"
        )

    def test_list_tasks_parent_filter_returns_empty_when_no_match(self, tmp_path: Path) -> None:
        """AC5b: CockpitView.list_tasks(parent=N) returns empty list when no children exist."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        task = engine.create_task("Lonely Task")
        view = CockpitView(engine)
        result = view.list_tasks(parent=task.id)
        assert result.tasks == [], (
            f"CockpitView.list_tasks(parent={task.id}) must return [] when task has no children; got {result.tasks}"
        )

    def test_show_task_returns_correct_task(self, tmp_path: Path) -> None:
        """AC5b: CockpitView.show_task(id) returns the task matching the given ID."""
        view, task_id = self._make_view_with_task(tmp_path)
        result = view.show_task(task_id)  # type: ignore[union-attr]
        assert result.id == task_id, (
            f"CockpitView.show_task({task_id}) must return task with id={task_id}; got id={result.id}"
        )
        assert result.title == "Test Task", (
            f"CockpitView.show_task({task_id}) must return task titled 'Test Task'; got '{result.title}'"
        )

    def test_board_config_returns_board_name(self, tmp_path: Path) -> None:
        """AC5b: CockpitView.board_config() returns a BoardConfig with expected statuses."""
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        view = self._make_view(tmp_path)
        config = view.board_config()  # type: ignore[union-attr]
        assert isinstance(config, BoardConfig), (
            f"CockpitView.board_config() must return a BoardConfig instance; got {type(config)}"
        )
        assert "research" in config.statuses, (
            f"CockpitView.board_config() must return config with 'research' status; got {config.statuses}"
        )

    # AC5b cycle 3: parity assertions — exact output equality against engine

    def test_list_tasks_count_and_ids_match_engine(self, tmp_path: Path) -> None:
        """AC5b cycle 3: list_tasks() count and task IDs must match engine.agent_view().list_tasks()."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.create_task("Alpha")
        engine.create_task("Beta")
        view = CockpitView(engine)
        view_result = view.list_tasks()
        engine_result = engine.agent_view().list_tasks()
        assert len(view_result.tasks) == len(engine_result.tasks), (
            f"CockpitView.list_tasks() count {len(view_result.tasks)} must equal "
            f"engine.agent_view().list_tasks() count {len(engine_result.tasks)}"
        )
        assert {t.id for t in view_result.tasks} == {t.id for t in engine_result.tasks}, (
            "CockpitView.list_tasks() task IDs must exactly match engine.agent_view().list_tasks() IDs"
        )

    def test_show_task_returns_show_task_response_type(self, tmp_path: Path) -> None:
        """AC5b cycle 3: show_task() must return ShowTaskResponse with correct id, title, and status."""
        from owlbear_kanban.models import ShowTaskResponse  # noqa: PLC0415

        view, task_id = self._make_view_with_task(tmp_path)
        result = view.show_task(task_id)  # type: ignore[union-attr]
        assert isinstance(result, ShowTaskResponse), (
            f"CockpitView.show_task() must return ShowTaskResponse; got {type(result)}"
        )
        assert result.id == task_id, f"CockpitView.show_task({task_id}).id must equal {task_id}; got {result.id}"
        assert result.title == "Test Task", (
            f"CockpitView.show_task({task_id}).title must be 'Test Task'; got '{result.title}'"
        )
        assert result.status == "research", (
            f"CockpitView.show_task({task_id}).status must be 'research' (default); got '{result.status}'"
        )

    def test_board_config_statuses_match_engine(self, tmp_path: Path) -> None:
        """AC5b cycle 3: board_config().statuses must equal engine.board_config().statuses."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        view = CockpitView(engine)
        view_config = view.board_config()
        engine_config = engine.board_config()
        assert view_config.statuses == engine_config.statuses, (
            f"CockpitView.board_config().statuses {view_config.statuses!r} must equal "
            f"engine.board_config().statuses {engine_config.statuses!r}"
        )


# --- merged from tests/test_cockpit_view_1240.py ---
"""Failing tests for CockpitView archival validation block (#1240).

RED phase — all tests must fail until B3 implementation (CockpitView.move_task
validation block) is complete.

AC coverage:
  AC1:  status="archived" + archival_reason=None → ERR_ARCHIVAL_REASON_REQUIRED
  AC2:  reason="completed" + non-empty refs → ERR_ARCHIVAL_REFS_FORBIDDEN
  AC3:  reason="dropped" + non-empty refs → ERR_ARCHIVAL_REFS_FORBIDDEN
  AC4:  reason="wontfix" + non-empty refs → ERR_ARCHIVAL_REFS_FORBIDDEN
  AC5:  reason="deprecated" + empty refs → ERR_ARCHIVAL_REFS_REQUIRED
  AC6:  reason="duplicate" + empty refs → ERR_ARCHIVAL_REFS_REQUIRED
  AC7:  reason="completed" when task.status != "done" → ERR_COMPLETED_REQUIRES_DONE
  AC8:  archival_refs contains non-existent ID → ERR_ARCHIVAL_REF_MISSING (422)
  AC9:  archival_refs contains task's own ID (self-reference) → ERR_ARCHIVAL_REF_SELF (422)
  AC10: archival_refs creates a dependency cycle → ERR_ARCHIVAL_REF_CYCLE (422)
  AC11: Valid archival (completed, done, empty refs) succeeds and persists both
        fields — test added in retry cycle per reviewer AC11 gap.
"""


from pathlib import Path

import pytest

from owlbear_cockpit.view import CockpitView
from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ValidationError

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML_1240 = """\
statuses:
    - research
    - backlog
    - todo
    - in-progress
    - review
    - docs
    - done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
    research: researcher
    backlog: architect
    todo: test-writer
    in-progress: builder
    review: reviewer
    docs: doc-writer
    done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""


def _make_board_1240(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML_1240, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir_1240(tmp_path: Path) -> Path:
    """Board with two tasks: one at 'done', one at 'todo'."""
    kanban_dir = _make_board_1240(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Done task", status="done", priority="important")
    seed.create_task("Todo task", status="todo", priority="important")
    return kanban_dir


@pytest.fixture
def engine_1240(board_dir_1240: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir_1240)
    eng.list_tasks()
    return eng


@pytest.fixture
def view(engine_1240: KanbanEngine) -> CockpitView:
    """CockpitView bound to the test engine."""
    return CockpitView(engine_1240)


def _get_updated_1240(engine_1240: KanbanEngine, task_id: int) -> str:
    """Return the current 'updated' timestamp for the given task ID."""
    return str(engine_1240.show_task(str(task_id)).updated)


# ---------------------------------------------------------------------------
# AC1-AC10 -- CockpitView.move_task archival validation block
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewArchivalValidation:
    """Archival validation block in CockpitView.move_task (B3, task #1240)."""

    # -- AC1: reason required when status="archived" --

    def test_archive_without_reason_raises_archival_reason_required(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC1: move_task(id, "archived", archival_reason=None) must raise
        ERR_ARCHIVAL_REASON_REQUIRED.

        CockpitView currently passes through to engine unconditionally; no
        validation block exists. The call succeeds without raising.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived", expected_updated=updated, archival_reason=None)
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    # -- AC2-AC4: refs forbidden for completed / dropped / wontfix --

    def test_archive_completed_with_refs_raises_archival_refs_forbidden(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC2: move_task with reason='completed' and non-empty refs raises
        ERR_ARCHIVAL_REFS_FORBIDDEN.

        CockpitView has no validation block; the call passes through to the
        engine which stores the fields without error.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="completed",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_archive_dropped_with_refs_raises_archival_refs_forbidden(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC3: move_task with reason='dropped' and non-empty refs raises
        ERR_ARCHIVAL_REFS_FORBIDDEN.

        CockpitView has no validation block; refs are silently stored.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="dropped",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_archive_wontfix_with_refs_raises_archival_refs_forbidden(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC4: move_task with reason='wontfix' and non-empty refs raises
        ERR_ARCHIVAL_REFS_FORBIDDEN.

        CockpitView has no validation block; refs are silently stored.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="wontfix",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    # -- AC5-AC6: refs required for deprecated / duplicate --

    def test_archive_deprecated_without_refs_raises_archival_refs_required(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC5: move_task with reason='deprecated' and empty refs raises
        ERR_ARCHIVAL_REFS_REQUIRED.

        CockpitView has no validation block; the task is archived with
        archival_refs=[] and no error raised.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="deprecated",
                archival_refs=[],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_archive_duplicate_without_refs_raises_archival_refs_required(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC6: move_task with reason='duplicate' and empty refs raises
        ERR_ARCHIVAL_REFS_REQUIRED.

        CockpitView has no validation block; the task is archived with
        archival_refs=[] and no error raised.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="duplicate",
                archival_refs=[],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    # -- AC7: completed requires task.status == "done" --

    def test_archive_completed_from_non_done_status_raises_completed_requires_done(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC7: move_task with reason='completed' when task.status != 'done' raises
        ERR_COMPLETED_REQUIRES_DONE.

        Task 2 is at 'todo', not 'done'. CockpitView has no validation block;
        the engine stores archival_reason='completed' without checking prior status.
        """
        updated = _get_updated_1240(engine_1240, 2)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                2,
                "archived",
                expected_updated=updated,
                archival_reason="completed",
                archival_refs=[],
            )
        assert exc_info.value.code == "ERR_COMPLETED_REQUIRES_DONE"

    # -- AC8: ref ID does not exist on the board --

    def test_archive_with_nonexistent_ref_raises_archival_ref_missing(
        self, view: CockpitView, engine_1240: KanbanEngine
    ) -> None:
        """AC8: move_task with archival_refs containing a non-existent task ID raises
        a 422 ValidationError.

        Task 99999 does not exist. CockpitView has no validation block; the engine
        silently stores refs=[99999] without verifying existence.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="deprecated",
                archival_refs=[99999],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_MISSING"

    # -- AC9: self-reference in archival_refs --

    def test_archive_with_self_ref_raises_archival_ref_self(self, view: CockpitView, engine_1240: KanbanEngine) -> None:
        """AC9: move_task with archival_refs=[task_id] (self-reference) raises a
        422 ValidationError.

        Task 1 references its own ID in refs. CockpitView has no validation
        block; the engine silently stores refs=[1] with no self-reference check.
        """
        updated = _get_updated_1240(engine_1240, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="deprecated",
                archival_refs=[1],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF"

    # -- AC10: archival_refs creates a dependency cycle --

    def test_archive_with_cyclic_refs_raises_archival_ref_cycle(self, tmp_path: Path) -> None:
        """AC10: move_task with archival_refs that create a cycle raises a
        422 ValidationError.

        Setup:
          - Task A (id=1, done): to be archived via CockpitView with refs=[B.id]
          - Task B (id=2, todo): archived directly via engine with refs=[A.id]

        When the view validates A's archival, it follows B's refs which point
        back to A — a cycle. CockpitView has no validation block; the cycle
        is silently accepted and A is archived with refs=[B.id].
        """
        # Build a fresh board with tasks A (done) and B (todo).
        kanban_dir = _make_board(tmp_path)
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Task A", status="done", priority="important")
        seed.create_task("Task B", status="todo", priority="important")

        # Archive task B directly via engine (bypassing view validation):
        # B gets archival_refs=[1] — B references A.
        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        eng.move_task("2", "archived", archival_reason="deprecated", archival_refs=[1])

        # Now try to archive A via CockpitView with refs=[B.id=2].
        # A → B and B → A: cycle.
        view = CockpitView(eng)
        updated_a = _get_updated_1240(eng, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated_a,
                archival_reason="deprecated",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_CYCLE"

    # -- AC11: valid archival persists archival_reason and archival_refs --

    def test_valid_archival_persists_reason_and_refs(self, view: CockpitView, engine_1240: KanbanEngine) -> None:
        """AC11: move_task on a done task with status='archived',
        reason='completed', and archival_refs=[] succeeds and persists both
        fields on the returned response and on a fresh reload.

        Task 1 is seeded at 'done'. reason='completed' requires no refs and
        the task is already at terminal status, so all validation rules pass.
        """
        updated = _get_updated_1240(engine_1240, 1)
        response = view.move_task(
            1,
            "archived",
            expected_updated=updated,
            archival_reason="completed",
            archival_refs=[],
        )
        assert response.archival_reason == "completed"
        assert response.archival_refs == []

        # Verify persistence: reload from disk via engine.
        reloaded = engine.show_task("1")
        assert reloaded.archival_reason == "completed"
        assert reloaded.archival_refs == []


# --- merged from tests/test_cockpit_view_1244.py ---
"""Failing tests for CockpitView archival validation 422 surfacing via the route (#1244).

RED phase — all tests must fail until the route allows 'archived' moves to reach the
CockpitView.move_task validation block and surface the archival ValidationErrors as
HTTP 422 responses with validation-specific detail messages.

Root cause of failure: the route's valid_transitions() check returns only configured
pipeline statuses (research … done) — 'archived' is not among them, so the route
returns 422 "Cannot move from '...' to 'archived'" before view.move_task() is ever
reached.  The builder must allow 'archived' past the transition check so the view
layer's validation block can run and its error messages can surface.

AC coverage:
  AC1:  POST /move no reason → 422 detail contains archival_reason context
  AC2:  reason="completed" + refs → 422 detail reflects refs-forbidden
  AC3:  reason="dropped"   + refs → 422 detail reflects refs-forbidden
  AC4:  reason="wontfix"   + refs → 422 detail reflects refs-forbidden
  AC5:  reason="deprecated" + empty refs → 422 detail reflects refs-required
  AC6:  reason="duplicate"  + empty refs → 422 detail reflects refs-required
  AC7:  reason="completed", task not at done → 422 detail reflects done-required
  AC8:  archival_refs contains non-existent ID → 422 detail contains missing-ref context
  AC9:  archival_refs contains task's own ID → 422 detail reflects self-reference
  AC10: archival_refs creates a cycle → 422 detail reflects cycle detection
  AC11: valid archived from done (completed, no refs) → 200 with status='archived'
  (AC12: all 11 tests from #1240 pass — regression guard; see test_cockpit_view_1240.py)
"""


from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML_1244 = """\
statuses:
    - research
    - backlog
    - todo
    - in-progress
    - review
    - docs
    - done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
    research: researcher
    backlog: architect
    todo: test-writer
    in-progress: builder
    review: reviewer
    docs: doc-writer
    done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""


def _make_board_1244(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML_1244, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with two tasks: task 1 at 'done', task 2 at 'todo'."""
    kanban_dir = _make_board_1244(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Done task", status="done", priority="important")
    seed.create_task("Todo task", status="todo", priority="important")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with real engine injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _updated(engine: KanbanEngine, task_id: int) -> str:
    """Return the current 'updated' timestamp string for the given task."""
    return str(engine.show_task(str(task_id)).updated)


# ---------------------------------------------------------------------------
# TestFromAC_ArchivalValidation422Surfacing
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalValidation422Surfacing:
    """Route surfaces CockpitView.move_task archival ValidationErrors as HTTP 422.

    Each test POSTs to POST /api/tasks/{id}/move with status='archived' and
    invalid archival combinations, then asserts the 422 detail contains content
    from the archival validation block — not from the generic transition check
    ("Cannot move from '...' to 'archived'").

    All tests currently FAIL because valid_transitions() never includes 'archived',
    so the transition check fires first and the view validation block is unreachable
    via the route.
    """

    # -- AC1: archival_reason required when status='archived' --

    def test_route_archive_without_reason_returns_422_with_archival_detail(self, client, engine: KanbanEngine) -> None:
        """AC1: POST /move with status='archived' and no archival_reason returns
        a 422 whose detail message references archival_reason, not a generic
        transition rejection.

        Currently FAILS: route's valid_transitions() blocks 'archived', returning
        "Cannot move from 'done' to 'archived'" which does not mention archival_reason.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={"status": "archived", "updated": _updated(engine, 1)},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_reason is required when status='archived'"
        assert "archival_reason" in detail

    # -- AC2-AC4: archival_refs forbidden for completed / dropped / wontfix --

    def test_route_archive_completed_with_refs_returns_422_with_forbidden_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC2: reason='completed' + non-empty refs → 422 detail shows refs-forbidden.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "completed",
                "archival_refs": [2],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "forbidden" in detail.lower()

    def test_route_archive_dropped_with_refs_returns_422_with_forbidden_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC3: reason='dropped' + non-empty refs → 422 detail shows refs-forbidden.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "dropped",
                "archival_refs": [2],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "forbidden" in detail.lower()

    def test_route_archive_wontfix_with_refs_returns_422_with_forbidden_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC4: reason='wontfix' + non-empty refs → 422 detail shows refs-forbidden.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "wontfix",
                "archival_refs": [2],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "forbidden" in detail.lower()

    # -- AC5-AC6: archival_refs required for deprecated / duplicate --

    def test_route_archive_deprecated_without_refs_returns_422_with_required_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC5: reason='deprecated' + empty refs → 422 detail shows refs-required.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "deprecated",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "required" in detail.lower()

    def test_route_archive_duplicate_without_refs_returns_422_with_required_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC6: reason='duplicate' + empty refs → 422 detail shows refs-required.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "duplicate",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "required" in detail.lower()

    # -- AC7: completed requires task.status == 'done' --

    def test_route_archive_completed_from_non_done_returns_422_with_done_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC7: reason='completed' when task.status != 'done' → 422 detail shows
        done-required context.

        Task 2 is at 'todo'. Currently FAILS: route blocks 'archived' before the
        view can check the pre-move status; detail says "Cannot move from 'todo' to
        'archived'" which does not mention 'done' or 'terminal'.
        """
        resp = client.post(
            "/api/tasks/2/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 2),
                "archival_reason": "completed",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_reason='completed' requires terminal status"
        assert "terminal" in detail.lower() or "done" in detail.lower()

    # -- AC8: non-existent ref ID --

    def test_route_archive_with_nonexistent_ref_returns_422_with_ref_missing_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC8: archival_refs contains a non-existent task ID → 422 detail mentions
        the missing ref ID or 'not found'.

        Currently FAILS: route blocks 'archived'; detail is generic transition error.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "deprecated",
                "archival_refs": [99999],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival reference task '99999' not found"
        assert "99999" in detail or "not found" in detail.lower()

    # -- AC9: self-reference in archival_refs --

    def test_route_archive_with_self_ref_returns_422_with_self_ref_detail(self, client, engine: KanbanEngine) -> None:
        """AC9: archival_refs contains the task's own ID → 422 detail reflects
        self-reference rejection.

        Currently FAILS: route blocks 'archived'; detail is generic transition error.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "deprecated",
                "archival_refs": [1],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_refs cannot include the task itself"
        assert "itself" in detail.lower() or "self" in detail.lower()

    # -- AC10: cyclic archival_refs --

    def test_route_archive_with_cyclic_refs_returns_422_with_cycle_detail(self, tmp_path: Path) -> None:
        """AC10: archival_refs that create a cycle → 422 detail reflects cycle detection.

        Setup:
          - Task A (id=1, done): to be archived via route with refs=[B.id]
          - Task B (id=2, todo): archived directly via engine with refs=[A.id]

        B→A is already stored (archived directly). When archiving A→B via route, the
        cycle A→B→A is detected by CockpitView._has_archival_cycle.

        Currently FAILS: route blocks 'archived'; cycle check is never reached.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Task A", status="done", priority="important")
        seed.create_task("Task B", status="todo", priority="important")

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        # Archive B directly via engine (bypassing view validation): B refs A.
        eng.move_task("2", "archived", archival_reason="deprecated", archival_refs=[1])

        app.dependency_overrides[get_engine] = lambda: eng
        try:
            tc = TestClient(app)
            updated_a = str(eng.show_task("1").updated)
            resp = tc.post(
                "/api/tasks/1/move",
                json={
                    "status": "archived",
                    "updated": updated_a,
                    "archival_reason": "deprecated",
                    "archival_refs": [2],
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_refs would introduce a cycle"
        assert "cycle" in detail.lower()

    # -- AC11 (happy path): valid archival from done → 200 --

    def test_route_valid_archive_from_done_returns_200_with_archived_status(self, client, engine: KanbanEngine) -> None:
        """AC11: POST /move with status='archived', reason='completed', no refs,
        task at 'done' → HTTP 200 with status='archived' in the response.

        Currently FAILS: route blocks 'archived' via valid_transitions(), returning
        422 instead of 200.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "completed",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"
