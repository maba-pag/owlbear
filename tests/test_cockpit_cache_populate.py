"""Failing tests for #1402: Harden cache populate ordering in MtimeScanCache.

AC coverage:
  AC1 (td:2): MtimeScanCache signature state is not committed until cache.tasks is
              successfully populated.  If view.list_tasks() raises after a
              directory-signature change is detected, the signature must remain at its
              previous value so the next request retries the populate.
  AC2 (td:2): Warm-cache failure-recovery proof: (a) prime cache with successful
              populate, (b) simulate directory-signature change, (c) make
              view.list_tasks() raise on refresh attempt, (d) verify signature was NOT
              committed — a subsequent request with the same directory state must
              re-detect the change and retry population successfully.
  AC3 (td:0): Existing cockpit test suites pass without modification (skipped, td:0).

All tests FAIL until the builder fixes the signature-commit ordering in:
  serve/cockpit/src/owlbear_cockpit/cache.py  (possible API change: split check/commit)
  serve/cockpit/src/owlbear_cockpit/routes/read.py  (or try/except rollback)

Root cause: cache.has_changed_at(mtime) commits _last_signature BEFORE
view.list_tasks() is called. When list_tasks() raises, the new signature is already
committed, so the next request with the same directory state is a cache hit and serves
stale data indefinitely (until the next real file modification).

The warm-cache stale window ONLY opens after a prior successful population followed by
a failed refresh.  The cold-cache path is safe because `not has_cached_tasks` always
retries regardless of the committed signature.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.corruption import CorruptionError

# ---------------------------------------------------------------------------
# Minimal board config & setup helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with no tasks (clean slate)."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


# ===========================================================================
# AC1 (td:2): Signature state not committed when view.list_tasks() raises
# ===========================================================================


class TestFromAC_CachePopulateOrdering:
    """AC1: last-seen signature must not advance when view.list_tasks() raises.

    Current bug in routes/read.py:
        mtime = cache.scan()
        if cache.has_changed_at(mtime) or ...:   # commits mtime here (BUG)
            envelope = view.list_tasks()          # may raise after commit
            cache.tasks = envelope.tasks
    """

    def test_signature_not_committed_when_list_tasks_raises(self, engine: KanbanEngine) -> None:
        """Error path: cache.last_mtime must stay at prior value after failed refresh.

        Setup:
          - Manually prime cache so last_mtime == sig_a and has_cached_tasks == True.
          - Mock scan() to return sig_b (simulating a directory change).
          - Mock view.list_tasks() to raise CorruptionError.
          - GET /api/tasks → 500.

        Assertion: cache.last_mtime must remain sig_a (not advance to sig_b).

        Fails with current code because has_changed_at(sig_b) commits sig_b in the
        signature comparison before view.list_tasks() is invoked, so last_mtime
        becomes sig_b regardless of whether the populate succeeded or failed.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache, get_view  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        cache = MtimeScanCache(engine.tasks_dir)
        sig_a = 100
        sig_b = 200

        # Manually prime the cache: last_signature = sig_a, has_cached_tasks = True.
        cache.has_changed_at(sig_a)
        cache.tasks = []  # triggers has_cached_tasks = True

        assert cache.last_mtime == sig_a, "Precondition: cache primed with sig_a."

        mock_view = MagicMock(spec=CockpitView)
        mock_view.list_tasks.side_effect = CorruptionError("ERR_CORRUPT_DUPLICATE_ID", "duplicate task IDs")

        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_cache] = lambda: cache
        app.dependency_overrides[get_view] = lambda: mock_view

        try:
            client = TestClient(app, raise_server_exceptions=False)
            with patch.object(cache, "scan", return_value=sig_b):
                response = client.get("/api/tasks")

            assert response.status_code == 500, "A failed populate must propagate as 500 Internal Server Error."
            # Key assertion: signature must NOT have advanced to sig_b.
            assert cache.last_mtime != sig_b, (
                f"cache.last_mtime must not advance to sig_b={sig_b} when "
                f"view.list_tasks() raises.  Current bug: has_changed_at(sig_b) "
                f"commits sig_b before calling view.list_tasks(), so last_mtime "
                f"becomes {sig_b} regardless of populate success or failure."
            )
            assert cache.last_mtime == sig_a, (
                f"cache.last_mtime must remain at sig_a={sig_a} after a failed "
                f"populate so the next request can re-detect the directory change "
                f"and retry population."
            )
        finally:
            app.dependency_overrides.clear()

    def test_stale_cache_not_served_after_failed_populate(self, engine: KanbanEngine) -> None:
        """Boundary: repeated same-sig requests after failure must not serve stale data.

        Scenario (three requests):
          Request 1 (sig_a): prime — list_tasks succeeds → cache warmed.
          Request 2 (sig_b): refresh — list_tasks raises CorruptionError → 500.
          Request 3 (sig_b): same directory state, list_tasks still raises.
            With fix: rolled-back sig → has_changed_at re-detects change → retries → 500.
            With bug: committed sig → cache hit → 200 with stale tasks.

        Assertion: r3.status_code == 500.

        Fails with current code because the committed sig_b causes a cache hit on
        request 3, returning 200 with stale primed data instead of retrying.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache, get_view  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban.models import ListTasksResponse  # noqa: PLC0415

        cache = MtimeScanCache(engine.tasks_dir)
        sig_a = 300
        sig_b = 400

        prime_resp = ListTasksResponse(tasks=[], guidance=[], missing_ids=None)

        mock_view = MagicMock(spec=CockpitView)
        mock_view.list_tasks.side_effect = [
            prime_resp,  # Request 1 (prime): succeeds
            CorruptionError("ERR_CORRUPT_YAML_PARSE", "parse error"),  # Request 2 (sig_b): fails
            CorruptionError("ERR_CORRUPT_YAML_PARSE", "still broken"),  # Request 3 (sig_b): still fails
        ]

        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_cache] = lambda: cache
        app.dependency_overrides[get_view] = lambda: mock_view

        try:
            client = TestClient(app, raise_server_exceptions=False)

            # Request 1: prime cache (sig_a → has_cached_tasks = True).
            with patch.object(cache, "scan", return_value=sig_a):
                r1 = client.get("/api/tasks")
            assert r1.status_code == 200, "Prime request must succeed."

            # Request 2: directory changed, list_tasks raises.
            with patch.object(cache, "scan", return_value=sig_b):
                r2 = client.get("/api/tasks")
            assert r2.status_code == 500, "Failed refresh must return 500."

            # Request 3: same sig_b, list_tasks still raises.
            # With fix:  rolled-back sig → has_changed_at(sig_b) True → retries → 500.
            # With bug:  committed sig  → has_changed_at(sig_b) False → cache hit → 200.
            with patch.object(cache, "scan", return_value=sig_b):
                r3 = client.get("/api/tasks")

            assert r3.status_code == 500, (
                "A request with the same directory signature immediately after a "
                "failed populate must not serve stale data (200). "
                "With the current bug, has_changed_at() already committed sig_b "
                "during the failed refresh, so request 3 is a cache hit and returns "
                "200 with stale tasks.  With the fix, the rolled-back signature "
                "causes has_changed_at() to re-detect the change and retry, "
                "which raises CorruptionError again → 500."
            )
        finally:
            app.dependency_overrides.clear()

    def test_signature_committed_after_successful_populate(self, engine: KanbanEngine) -> None:
        """Happy path: cache.last_mtime must equal the scanned signature after success.

        Regression guard: proves that cache.commit_signature(mtime) IS called on the
        success path in routes/read.py.  Removing that call would leave last_mtime at
        its prior value (0 for a cold cache), causing every subsequent request to
        re-detect a change and re-invoke view.list_tasks(), defeating the cache.

        Setup:
          - Fresh cache (last_mtime == 0, has_cached_tasks == False).
          - Mock scan() to return sig_new.
          - Mock view.list_tasks() to succeed with an empty task list.
          - GET /api/tasks → 200.

        Assertion: cache.last_mtime == sig_new after the request.

        Fails if commit_signature(mtime) is absent or skipped on the success path,
        because last_mtime stays at 0 instead of advancing to sig_new.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache, get_view  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415
        from owlbear_kanban.models import ListTasksResponse  # noqa: PLC0415

        cache = MtimeScanCache(engine.tasks_dir)
        sig_new = 999

        assert cache.last_mtime == 0, "Precondition: fresh cache, last_mtime == 0."
        assert not cache.has_cached_tasks, "Precondition: fresh cache, no tasks cached."

        success_resp = ListTasksResponse(tasks=[], guidance=[], missing_ids=None)
        mock_view = MagicMock(spec=CockpitView)
        mock_view.list_tasks.return_value = success_resp

        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_cache] = lambda: cache
        app.dependency_overrides[get_view] = lambda: mock_view

        try:
            client = TestClient(app, raise_server_exceptions=False)
            with patch.object(cache, "scan", return_value=sig_new):
                response = client.get("/api/tasks")

            assert response.status_code == 200, "Successful populate must return 200."
            assert cache.last_mtime == sig_new, (
                f"cache.last_mtime must be committed to sig_new={sig_new} after a "
                f"successful populate.  "
                f"Current value: {cache.last_mtime}.  "
                f"If commit_signature(mtime) is absent or skipped on the success "
                f"path, last_mtime stays at 0 and every subsequent request "
                f"re-detects a change, bypassing the cache entirely."
            )
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# AC2 (td:2): Warm-cache failure-recovery: 4-step sequence
# ===========================================================================


class TestFromAC_WarmCacheFailureRecovery:
    """AC2: prime → sig-change → fail → retry succeeds with fresh data.

    Architect test-writer guidance: a single test exercising the 4-step sequence
    satisfies both AC1 (mechanism) and AC2 (proof).  A focused boundary test is
    added to verify the rollback value directly.
    """

    def test_4step_failure_recovery_warm_cache(self, tmp_path: Path) -> None:
        """AC2: full 4-step failure-recovery sequence as specified.

        (a) Prime:  GET /api/tasks succeeds → 1 task cached, sig_a committed.
        (b) Change: directory changes → scan() returns sig_b.
        (c) Fail:   view.list_tasks() raises CorruptionError → 500.
        (d) Retry:  same sig_b, view.list_tasks() now succeeds → 2 fresh tasks.

        Assertion: r3 returns 2 tasks (fresh data, not stale 1-task prime).

        Fails with current code because:
          - Step (c): has_changed_at(sig_b) commits sig_b before the exception.
          - Step (d): has_changed_at(sig_b) returns False (sig_b == sig_b) → cache hit
            → stale 1-task prime data served; list_tasks() never called for retry.

        Also verifies via mock call_count that list_tasks() is called 3 times
        (prime, fail, retry), not 2 (prime, fail — step (d) skips via cache hit).
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache, get_view  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        eng = KanbanEngine(kanban_dir)
        cache = MtimeScanCache(eng.tasks_dir)
        sig_a = 500
        sig_b = 600

        # Prepare genuine ListTasksResponse objects via the real view so that
        # FastAPI's response_model serialization succeeds.
        eng.create_task("Alpha", status="todo", priority="important")
        real_view = CockpitView(eng)
        prime_response = real_view.list_tasks()  # 1 task

        eng.create_task("Beta", status="todo", priority="needed")
        fresh_response = real_view.list_tasks()  # 2 tasks

        assert len(prime_response.tasks) == 1, "Precondition: prime has 1 task."
        assert len(fresh_response.tasks) == 2, "Precondition: fresh has 2 tasks."

        mock_view = MagicMock(spec=CockpitView)
        mock_view.list_tasks.side_effect = [
            prime_response,  # (a) prime: 1 task
            CorruptionError("ERR_CORRUPT_DUPLICATE_ID", "duplicate IDs"),  # (c) fail: raises
            fresh_response,  # (d) retry: 2 tasks
        ]

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: cache
        app.dependency_overrides[get_view] = lambda: mock_view

        try:
            client = TestClient(app, raise_server_exceptions=False)

            # (a) Prime: first request succeeds → 1 task.
            with patch.object(cache, "scan", return_value=sig_a):
                r1 = client.get("/api/tasks")
            assert r1.status_code == 200, "(a) Prime must succeed."
            assert len(r1.json()["tasks"]) == 1, "(a) Prime must return 1 task."
            assert cache.has_cached_tasks, "(a) Cache must be warm after prime."

            # (b)+(c) Sig change + failed refresh → 500.
            with patch.object(cache, "scan", return_value=sig_b):
                r2 = client.get("/api/tasks")
            assert r2.status_code == 500, "(b)+(c) Request with new sig and failing list_tasks() must be 500."

            # (d) Same sig_b — list_tasks now succeeds with fresh 2-task data.
            # Fix:  sig rolled back to sig_a → has_changed_at(sig_b) True → retries.
            # Bug:  sig stayed at sig_b → has_changed_at(sig_b) False → cache hit.
            with patch.object(cache, "scan", return_value=sig_b):
                r3 = client.get("/api/tasks")

            assert r3.status_code == 200, (
                "(d) Retry request must succeed.  "
                "With the current bug, the committed sig_b causes a cache hit and "
                "r3 returns stale 1-task prime data instead of retrying."
            )
            assert len(r3.json()["tasks"]) == 2, (
                "(d) Retry must return fresh 2-task data, not stale 1-task prime data. "
                "With the current bug, the cache hit skips list_tasks() and serves "
                "the 1-task list cached during step (a)."
            )
            # Verify list_tasks was invoked exactly 3 times: prime, fail, retry.
            # With the bug, call_count == 2 (step (d) skips via cache hit).
            assert mock_view.list_tasks.call_count == 3, (
                f"view.list_tasks() must be called 3 times (prime, fail, retry). "
                f"Actual call count: {mock_view.list_tasks.call_count}. "
                f"With the current bug, only 2 calls happen because step (d) "
                f"is a cache hit and does not invoke list_tasks()."
            )
        finally:
            app.dependency_overrides.clear()

    def test_signature_rolled_back_after_warm_cache_failure(self, engine: KanbanEngine) -> None:
        """Boundary: after warm-cache failure, cache.last_mtime must be prior value.

        Directly tests the rollback mechanism that enables the retry in the 4-step
        sequence: after a failed refresh (sig_a → sig_b with exception), last_mtime
        must equal sig_a so that the next has_changed_at(sig_b) call returns True.

        Fails with current code because has_changed_at(sig_b) commits sig_b before
        view.list_tasks() is called, leaving last_mtime == sig_b after the failure.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache, get_view  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        cache = MtimeScanCache(engine.tasks_dir)
        sig_a = 700
        sig_b = 800

        # Manually prime: simulate a prior successful populate at sig_a.
        cache.has_changed_at(sig_a)
        cache.tasks = []  # marks has_cached_tasks = True

        assert cache.last_mtime == sig_a, "Precondition: primed at sig_a."
        assert cache.has_cached_tasks, "Precondition: warm cache."

        mock_view = MagicMock(spec=CockpitView)
        mock_view.list_tasks.side_effect = CorruptionError("ERR_CORRUPT_YAML_PARSE", "engine error")

        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_cache] = lambda: cache
        app.dependency_overrides[get_view] = lambda: mock_view

        try:
            client = TestClient(app, raise_server_exceptions=False)
            with patch.object(cache, "scan", return_value=sig_b):
                response = client.get("/api/tasks")

            assert response.status_code == 500, "Failed refresh must be 500."

            assert cache.last_mtime == sig_a, (
                f"cache.last_mtime must be rolled back to sig_a={sig_a} after a "
                f"failed warm-cache populate.  "
                f"Current value: {cache.last_mtime}.  "
                f"The current bug commits sig_b={sig_b} inside has_changed_at() "
                f"before view.list_tasks() is called, so last_mtime stays at "
                f"sig_b={sig_b} even after the exception, preventing the next "
                f"request from re-detecting the directory change."
            )
        finally:
            app.dependency_overrides.clear()
