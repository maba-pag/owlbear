"""RED tests — Remove Mock from MCP server production code (#1197).

AC coverage:
- AC1 (td:1): No unittest.mock import in server.py
- AC2 (td:2): _agent_view_for removed; move_task, start_work, end_work use only
  _canonical_agent_view_for + direct engine fallback
- AC4 (td:1): Test patches referencing _agent_view_for updated in test files

FAIL paths summary:
- AC1 structural tests: server.py currently contains 'from unittest.mock import Mock'
  and 'isinstance(return_value, Mock)' — assertions that these are absent fail now.
- AC2 structural test: server.py defines 'def _agent_view_for' — assertion fails now.
- AC2 behavioral tests: tools call _agent_view_for first; since the real engine's
  AgentView resolves at the first tier, _canonical_agent_view_for spy is never called
  (call_count == 0). Assertions that spy.call_count == 1 fail now.
- AC4 structural tests: test_mcp_kanban.py, test_mcp_kanban_1126.py contain patches
  targeting '_agent_view_for'; test_server_1170.py imports and tests '_agent_view_for'.
  Assertions that '_agent_view_for' is absent from those sources fail now.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import owlbear_mcp_kanban.server as _server_mod
from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import (
    AppContext,
    end_work,
    move_task,
    start_work,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).parent
_SERVER_PY = (
    _TESTS_DIR.parent
    / "serve"
    / "mcp-kanban"
    / "src"
    / "owlbear_mcp_kanban"
    / "server.py"
)
_LIFECYCLE_TOOLS_PY = (
    _TESTS_DIR.parent
    / "serve"
    / "mcp-kanban"
    / "tests"
    / "test_mcp_lifecycle_tools.py"
)

# ---------------------------------------------------------------------------
# Board config — minimal flat schema accepted by KanbanEngine
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
- name: docs
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
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx_todo(tmp_path: Path) -> AppContext:
    """Real AppContext with one unclaimed task at 'todo'."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Test task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_claimed(tmp_path: Path) -> AppContext:
    """Real AppContext with one claimed task at 'in-progress'."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Claimed task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_NoMockImport — AC1 (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_NoMockImport:
    """AC1: server.py must not import or reference unittest.mock.Mock."""

    def test_server_has_no_unittest_mock_import(self) -> None:
        """AC1: 'from unittest.mock import Mock' must be absent from server.py.

        FAILS now: server.py contains 'from unittest.mock import Mock' at the top.
        After builder removes _agent_view_for and its Mock dependency, this import
        disappears.
        """
        source = _SERVER_PY.read_text(encoding="utf-8")
        assert "from unittest.mock import Mock" not in source

    def test_server_has_no_isinstance_mock_check(self) -> None:
        """AC1: isinstance(return_value, Mock) check must be absent from server.py.

        FAILS now: the _agent_view_for._score() inner function contains
        'not isinstance(return_value, Mock)' to distinguish test doubles.
        After builder removes _agent_view_for, this production-code Mock reference
        is gone.
        """
        source = _SERVER_PY.read_text(encoding="utf-8")
        assert "isinstance(return_value, Mock)" not in source


# ---------------------------------------------------------------------------
# TestFromAC_AgentViewForRemoved — AC2 (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewForRemoved:
    """AC2: _agent_view_for removed; tools use only _canonical_agent_view_for."""

    def test_agent_view_for_not_defined_in_server(self) -> None:
        """AC2: 'def _agent_view_for' must not appear in server.py.

        FAILS now: server.py defines _agent_view_for() starting around line 213.
        After builder removes the function, this definition is absent.
        """
        source = _SERVER_PY.read_text(encoding="utf-8")
        assert "def _agent_view_for" not in source

    @pytest.mark.asyncio
    async def test_move_task_resolves_via_canonical_agent_view_for(
        self, app_ctx_todo: AppContext
    ) -> None:
        """AC2: move_task calls _canonical_agent_view_for (not _agent_view_for) for resolution.

        FAILS now: move_task tries _agent_view_for first. With a real engine, the
        first-tier AgentView resolves and returns a result, so _canonical_agent_view_for
        is never invoked (spy.call_count == 0). Assertion spy.call_count == 1 fails.

        After builder removes the _agent_view_for first-tier block, _canonical_agent_view_for
        becomes the sole resolution path. Spy wraps the real function → call_count == 1.
        """
        ctx = _make_ctx(app_ctx_todo)
        with patch.object(
            _server_mod,
            "_canonical_agent_view_for",
            wraps=_server_mod._canonical_agent_view_for,  # noqa: SLF001
        ) as spy:
            await move_task(ctx, id="1", status="done")
        assert spy.call_count == 1  # FAILS now: 0 (first-tier handles it)

    @pytest.mark.asyncio
    async def test_start_work_resolves_via_canonical_agent_view_for(
        self, app_ctx_todo: AppContext
    ) -> None:
        """AC2: start_work calls _canonical_agent_view_for (not _agent_view_for) for resolution.

        FAILS now: start_work calls _agent_view_for first; the real AgentView resolves
        and claims the task, so _canonical_agent_view_for spy is never reached
        (spy.call_count == 0). Assertion spy.call_count == 1 fails.

        After builder removes the _agent_view_for block, _canonical_agent_view_for
        is called exactly once.
        """
        ctx = _make_ctx(app_ctx_todo)
        with patch.object(
            _server_mod,
            "_canonical_agent_view_for",
            wraps=_server_mod._canonical_agent_view_for,  # noqa: SLF001
        ) as spy:
            await start_work(ctx, id="1")
        assert spy.call_count == 1  # FAILS now: 0

    @pytest.mark.asyncio
    async def test_end_work_resolves_via_canonical_agent_view_for(
        self, app_ctx_claimed: AppContext
    ) -> None:
        """AC2: end_work calls _canonical_agent_view_for (not _agent_view_for) for resolution.

        FAILS now: end_work calls _invoke_view_end_work(_agent_view_for(engine), ...)
        first. With a real engine, the first-tier AgentView succeeds, so
        _canonical_agent_view_for spy is never called (spy.call_count == 0).
        Assertion spy.call_count == 1 fails.

        After builder removes the _agent_view_for first-tier block, _canonical_agent_view_for
        is called exactly once.
        """
        ctx = _make_ctx(app_ctx_claimed)
        with patch.object(
            _server_mod,
            "_canonical_agent_view_for",
            wraps=_server_mod._canonical_agent_view_for,  # noqa: SLF001
        ) as spy:
            await end_work(ctx, id="1", outcome="success", note="done")
        assert spy.call_count == 1  # FAILS now: 0


# ---------------------------------------------------------------------------
# TestFromAC_TestPatchesUpdated — AC4 (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_TestPatchesUpdated:
    """AC4: All test patches referencing _agent_view_for must be removed/updated."""

    def test_mcp_kanban_test_has_no_agent_view_for_references(self) -> None:
        """AC4: test_mcp_kanban.py must not reference _agent_view_for.

        FAILS now: test_mcp_kanban.py patches 'owlbear_mcp_kanban.server._agent_view_for'
        at lines 295, 319, 343. After builder updates these patches to
        _canonical_agent_view_for, '_agent_view_for' is absent from the file.
        """
        source = (_TESTS_DIR / "test_mcp_kanban.py").read_text(encoding="utf-8")
        assert "_agent_view_for" not in source

    def test_mcp_kanban_1126_test_has_no_agent_view_for_references(self) -> None:
        """AC4: test_mcp_kanban_1126.py must not reference _agent_view_for.

        FAILS now: test_mcp_kanban_1126.py uses patch(..._agent_view_for...) in
        TestFromAC_DeadTypeErrorFallback. After builder updates patches to
        _canonical_agent_view_for, '_agent_view_for' is absent.
        """
        source = (_TESTS_DIR / "test_mcp_kanban_1126.py").read_text(encoding="utf-8")
        assert "_agent_view_for" not in source

    def test_server_1170_has_no_agent_view_for_references(self) -> None:
        """AC4: _agent_view_for unit tests removed from test_server_1170.py.

        FAILS now: test_server_1170.py imports _agent_view_for and contains
        test_agent_view_for_none_attr_returns_none, test_agent_view_for_with_scored_
        candidates_returns_max, test_agent_view_for_returns_exact_highest_scored_
        candidate. After builder removes these tests, '_agent_view_for' is absent.
        """
        source = (_TESTS_DIR / "test_server_1170.py").read_text(encoding="utf-8")
        assert "_agent_view_for" not in source


# ---------------------------------------------------------------------------
# TestFromAC_CanonicalResolverClean — AC2 revised (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_CanonicalResolverClean:
    """AC2 (revised): _canonical_agent_view_for must contain no mock-aware logic.

    Banned patterns per Architecture Review:
    - _is_default_mock_object (inner function and call sites)
    - Class-name string checks: 'Mock', 'MagicMock', 'AsyncMock'
    - return_value identity comparisons: getattr(candidate, "return_value", ...)
    """

    def _resolver_source(self) -> str:
        """Return source of _canonical_agent_view_for()."""
        import owlbear_mcp_kanban.server as _mod

        return inspect.getsource(_mod._canonical_agent_view_for)  # noqa: SLF001

    def test_canonical_resolver_has_no_is_default_mock_object(self) -> None:
        """AC2 (revised): _is_default_mock_object must not appear in resolver body.

        FAILS now: server.py defines _is_default_mock_object() as an inner function
        of _canonical_agent_view_for() at line 224. This is mock-aware production
        code. After builder deletes lines 224-239, the inner function is absent.
        """
        source = self._resolver_source()
        assert "_is_default_mock_object" not in source

    def test_canonical_resolver_has_no_class_name_mock_check(self) -> None:
        """AC2 (revised): class-name string checks for mock types must not appear.

        FAILS now: line 225 of server.py checks
        `value.__class__.__name__ in {"Mock", "MagicMock", "AsyncMock"}`
        inside _canonical_agent_view_for. After builder removes lines 224-239,
        no class-name strings for mock detection remain.
        """
        source = self._resolver_source()
        # Banned: any literal mock class-name used for type detection
        assert '"MagicMock"' not in source
        assert '"AsyncMock"' not in source
        # 'Mock' substring check scoped to class-name detection context
        assert "__class__.__name__" not in source

    def test_canonical_resolver_has_no_return_value_string_lookup(self) -> None:
        """AC2 (revised): return_value identity comparison must not appear.

        FAILS now: line 228 of server.py uses
        `getattr(candidate, "return_value", object()) is resolved`
        to detect callable mock holders. After builder removes lines 224-239,
        no return_value string key lookup remains in the resolver.
        """
        source = self._resolver_source()
        assert '"return_value"' not in source


# ---------------------------------------------------------------------------
# TestFromAC_NonCallableMockFixtures — AC4 revised (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_NonCallableMockFixtures:
    """AC4 (revised): test fixtures must use NonCallableMagicMock for engine.agent_view.

    Callable MagicMock triggers the callable branch in _canonical_agent_view_for,
    causing the resolver to call the mock and inspect its return value. Using
    NonCallableMagicMock (callable() returns False) forces the direct-return path,
    so no mock-aware compatibility logic is needed in production code.
    """

    def test_server_1170_make_engine_mock_uses_noncallable_agent_view(self) -> None:
        """AC4 (revised): _make_engine_mock in test_server_1170.py must use NonCallableMagicMock.

        FAILS now: test_server_1170.py line 89 sets `av = MagicMock()`, making the
        mock callable. This forces _canonical_agent_view_for into the callable branch
        and requires mock-aware compatibility logic to avoid returning a bare default
        MagicMock. After builder changes to NonCallableMagicMock, callable() is False
        and the resolver returns the mock directly.
        """
        source = (_TESTS_DIR / "test_server_1170.py").read_text(encoding="utf-8")
        assert "NonCallableMagicMock" in source

    def test_lifecycle_tools_mock_av_fixture_uses_noncallable_agent_view(self) -> None:
        """AC4 (revised): mock_av fixture in test_mcp_lifecycle_tools.py must use NonCallableMagicMock.

        FAILS now: test_mcp_lifecycle_tools.py line 113 sets `av = MagicMock()`, making
        the lifecycle adapter's mock agent view callable. After builder changes to
        NonCallableMagicMock, callable() is False and production code requires no
        mock-class-name detection.
        """
        source = _LIFECYCLE_TOOLS_PY.read_text(encoding="utf-8")
        assert "NonCallableMagicMock" in source


# ---------------------------------------------------------------------------
# TestFromAC_CanonicalResolverBranches — AC2 revised callable-branch proof
# ---------------------------------------------------------------------------


class TestFromAC_CanonicalResolverBranches:
    """AC2 (revised): callable-branch proof for _canonical_agent_view_for.

    Covers server.py:219-222 — the 'if callable(candidate)' branch including
    exception suppression (server.py:219-220) and the None-result fallback
    (server.py:221-222).
    """

    def test_canonical_resolver_callable_returning_none(self) -> None:
        """AC2: callable agent_view returning None → resolver returns None.

        Covers server.py:221-222: 'if resolved is None: return None'.
        If that guard is removed, calling a None-returning agent_view would
        propagate None through and the resolver would incorrectly return None
        without the explicit guard — though the result is the same, removing
        the branch would break the three-branch contract described in AC2.

        Proof: candidate() returns None → _canonical_agent_view_for returns None.
        """
        engine = MagicMock()
        engine.agent_view = lambda: None
        result = _server_mod._canonical_agent_view_for(engine)  # noqa: SLF001
        assert result is None

    def test_canonical_resolver_callable_raising(self) -> None:
        """AC2: callable agent_view raising → exception suppressed → resolver returns None.

        Covers server.py:219-220: 'with contextlib.suppress(Exception): resolved = candidate()'.
        If exception suppression were removed, this would propagate the exception
        to the caller instead of returning None.

        Proof: candidate() raises RuntimeError → _canonical_agent_view_for returns None.
        """
        def _raising() -> None:
            msg = "test error — must be suppressed"
            raise RuntimeError(msg)

        engine = MagicMock()
        engine.agent_view = _raising
        result = _server_mod._canonical_agent_view_for(engine)  # noqa: SLF001
        assert result is None
