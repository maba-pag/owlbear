"""Failing tests for cockpit move route OCC wire-up (#1135).

RED phase — all tests must fail until the move route is updated in GREEN.

AC coverage:
  - AC1: MoveRequest requires an 'updated' field (required, str)
  - AC2: Route performs precheck (req.updated != str(task.updated) -> 409) and
         passes expected_updated=req.updated to engine.move_task()
  - AC3: Route catches ConcurrencyError from owlbear_kanban.errors and returns
         HTTP 409 with detail "Task was modified since your last load (stale snapshot)"
  - AC4: Existing move tests need 'updated' in request body; tested indirectly via
         AC1 — missing 'updated' returns 422 (Pydantic validates before handler)
  - AC5: test_move_stale_updated_returns_409 — stale token proves end-to-end 409
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConcurrencyError


# ---------------------------------------------------------------------------
# Board fixture helpers (same pattern as test_cockpit_mutation_api.py)
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
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


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with 2 tasks.

    Task 1: status=todo,        priority=important  (unclaimed — move target)
    Task 2: status=in-progress, priority=needed     (unclaimed)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine for cockpit route tests."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with cockpit engine injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 — MoveRequest requires 'updated' field
# ---------------------------------------------------------------------------


class TestFromAC_MoveRequestUpdatedField:
    """AC1: MoveRequest must accept a required 'updated' field (str).

    Currently MoveRequest has only 'status'. Adding 'updated' as required means
    requests without it get 422 (Pydantic validates before the handler runs).
    """

    def test_move_without_updated_field_returns_422(self, client) -> None:
        """Move request missing 'updated' field → 422 validation error.

        Fails against current code because MoveRequest has no 'updated' field
        and the request succeeds with just {'status': 'in-progress'}.
        """
        response = client.post("/api/tasks/1/move", json={"status": "in-progress"})
        assert response.status_code == 422

    def test_move_with_valid_updated_and_status_returns_200(
        self, client, engine: KanbanEngine
    ) -> None:
        """Happy path: move with valid 'updated' token and reachable status → 200.

        Fails against current code because 'updated' is not accepted in MoveRequest.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200

    def test_move_nonexistent_task_with_updated_returns_404(self, client) -> None:
        """Non-existent task with 'updated' present → 404 (not 422 or 200).

        Pydantic accepts the request body; handler raises 404.
        Fails because 'updated' is not yet a field in MoveRequest.
        """
        response = client.post(
            "/api/tasks/999/move",
            json={"status": "in-progress", "updated": "2025-01-01T00:00:00"},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "999" in str(body.get("message", ""))

    def test_move_with_null_updated_returns_422(self, client) -> None:
        """Move request with null 'updated' value → 422 validation error.

        AC1 specifies 'updated' must be str (required). A null value is not a
        valid string and must be rejected by Pydantic type validation before
        the handler body runs. This is an AC1 non-string boundary case.
        """
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": None},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC2 — Precheck and expected_updated passthrough
# ---------------------------------------------------------------------------


class TestFromAC_MovePrecheck:
    """AC2: Route checks req.updated != str(task.updated) -> 409 and passes
    expected_updated=req.updated to engine.move_task().
    """

    def test_move_with_matching_updated_calls_engine_with_expected_updated(
        self, client, engine: KanbanEngine
    ) -> None:
        """Route must pass expected_updated=req.updated to engine.move_task().

        Wraps engine.move_task to inspect kwargs. Currently the route calls
        engine.move_task without expected_updated — this test proves the gap.
        """
        task = engine.show_task("1")
        with mock.patch.object(engine, "move_task", wraps=engine.move_task) as mocked:
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 200
        assert mocked.called, "engine.move_task must have been called"
        call_kwargs = mocked.call_args.kwargs
        assert "expected_updated" in call_kwargs, (
            "Route must pass expected_updated to engine.move_task"
        )
        assert call_kwargs["expected_updated"] == task.updated

    def test_move_precheck_stale_updated_returns_409(
        self, client, engine: KanbanEngine
    ) -> None:
        """Stale 'updated' token (precheck) → 409 before engine is called.

        The route must short-circuit with 409 when req.updated does not match
        the current task.updated. Currently no precheck exists — move succeeds.
        """
        task = engine.show_task("1")
        stale_timestamp = task.updated
        # Advance task.updated via engine before the HTTP move
        engine.edit_task("1", title="Concurrently modified — bumps updated")
        # HTTP move carries the old (stale) snapshot
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": stale_timestamp},
        )
        assert response.status_code == 409

    def test_move_precheck_stale_does_not_call_engine_move(
        self, client, engine: KanbanEngine
    ) -> None:
        """When precheck detects stale token, route returns 409 without calling engine.

        Ensures the route short-circuits before the write rather than relying
        solely on the engine CAS for protection.
        """
        task = engine.show_task("1")
        stale_timestamp = task.updated
        engine.edit_task("1", title="Bump updated for precheck test")
        with mock.patch.object(engine, "move_task", wraps=engine.move_task) as mocked:
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": stale_timestamp},
            )
        # Both assertions must hold: route returns 409 AND engine is never invoked
        assert response.status_code == 409, (
            "Stale precheck must return 409, not bypass to engine"
        )
        assert not mocked.called, (
            "engine.move_task must not be called when precheck detects stale token"
        )


# ---------------------------------------------------------------------------
# AC3 — ConcurrencyError → HTTP 409 with exact detail string
# ---------------------------------------------------------------------------


class TestFromAC_MoveConcurrencyError:
    """AC3: Route catches ConcurrencyError and returns 409 with the exact detail string.

    The precheck guards against detected staleness; engine.move_task with
    expected_updated is belt-and-suspenders for TOCTOU races. The route must
    catch ConcurrencyError and return 409.
    """

    def test_move_concurrency_error_from_engine_returns_409(
        self, client, engine: KanbanEngine
    ) -> None:
        """ConcurrencyError raised by engine.move_task → HTTP 409.

        Currently the route has no ConcurrencyError handler — the exception
        would propagate as a 500.
        """
        task = engine.show_task("1")

        def _raise_concurrency(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise ConcurrencyError(
                code="ERR_STALE",
                user_message="stale write detected",
            )

        with mock.patch.object(engine, "move_task", side_effect=_raise_concurrency):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 409

    def test_move_concurrency_error_has_exact_detail_string(
        self, client, engine: KanbanEngine
    ) -> None:
        """ConcurrencyError → 409 detail must be the canonical stale-snapshot message.

        Exact string: "Task was modified since your last load (stale snapshot)"
        """
        task = engine.show_task("1")

        def _raise_concurrency(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise ConcurrencyError(
                code="ERR_STALE",
                user_message="stale write detected",
            )

        with mock.patch.object(engine, "move_task", side_effect=_raise_concurrency):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert body.get("message") == "stale write detected"


# ---------------------------------------------------------------------------
# AC5 — test_move_stale_updated_returns_409 (named per AC)
# ---------------------------------------------------------------------------


class TestFromAC_MoveStaleUpdated:
    """AC5: End-to-end stale-token test using real engine state mutation.

    Pattern: obtain task snapshot → mutate task via engine (bumps updated) →
    HTTP move with stale token → 409.
    """

    def test_move_stale_updated_returns_409(self, client, engine: KanbanEngine) -> None:
        """Stale 'updated' token causes move route to return 409.

        Follows the pattern from test_edit_stale_updated_returns_409 in
        test_cockpit_mutation_api.py (same file, L286-300).
        """
        task = engine.show_task("1")
        stale_updated = task.updated
        # Mutate task via engine between the client's snapshot and the HTTP move
        engine.edit_task("1", title="Interleaved engine mutation")
        # HTTP move with stale snapshot
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": stale_updated},
        )
        assert response.status_code == 409

    def test_move_fresh_updated_after_mutation_returns_200(
        self, client, engine: KanbanEngine
    ) -> None:
        """After mutation, a fresh 'updated' token allows the move to succeed → 200.

        Boundary: confirms 409 is token-staleness specific, not a blanket block.
        """
        # Mutate task first
        engine.edit_task("1", title="Pre-move mutation")
        # Re-read the task to get the fresh updated token
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# AC4 — Shared suite contract: test_cockpit_mutation_api.py move tests updated
# ---------------------------------------------------------------------------


class TestFromAC_MoveSharedSuiteContract:
    """AC4: All /move POST calls in test_cockpit_mutation_api.py include 'updated' token.

    Source inspection guard. Fails until the builder updates the shared mutation
    suite to carry the required OCC token in every move request payload.
    """

    def test_shared_suite_move_posts_all_include_updated_token(self) -> None:
        """Source inspection: every /move POST in test_cockpit_mutation_api.py
        carries 'updated' in the json payload.

        Fails currently because test_cockpit_mutation_api.py sends status-only
        payloads for all 6 move POST calls (lines ~139, 144, 153, 164, 169, 400).
        Passes after builder applies AC4 and adds 'updated' to each call.
        """
        source = Path("tests/test_cockpit_mutation_api.py").read_text(encoding="utf-8")
        lines = source.splitlines()
        violations: list[str] = []

        for i, line in enumerate(lines):
            # Match lines that contain a /move URL fragment (part of a move POST)
            if "/move" not in line:
                continue
            # Collect a window covering the enclosing client.post(...) call
            start = max(0, i - 2)
            end = min(len(lines), i + 5)
            window = "\n".join(lines[start:end])
            # Skip lines that are not part of a client.post call
            if "client.post" not in window:
                continue
            # Flag if 'updated' is absent from the payload context
            if '"updated"' not in window and "'updated'" not in window:
                violations.append(f"  line {i + 1}: {line.strip()!r}")

        assert not violations, (
            "Move POST calls in test_cockpit_mutation_api.py missing 'updated' OCC token"
            " (AC4 — builder must update all move payloads):\n" + "\n".join(violations)
        )

    def test_shared_suite_move_posts_source_updated_from_engine_show_task(self) -> None:
        """Stronger AC4 guard: every /move POST in test_cockpit_mutation_api.py
        sources 'updated' dynamically from engine.show_task (not hardcoded).

        The weaker guard (test_shared_suite_move_posts_all_include_updated_token)
        only checks that the 'updated' key is present in the payload window.
        This test additionally verifies 'task.updated' appears nearby, proving
        the token is sourced dynamically — not from a hardcoded or stale value.

        Fails if any /move POST payload uses a hardcoded 'updated' value
        instead of one derived from engine.show_task().updated.
        """
        source = Path("tests/test_cockpit_mutation_api.py").read_text(encoding="utf-8")
        lines = source.splitlines()
        violations: list[str] = []

        for i, line in enumerate(lines):
            if "/move" not in line:
                continue
            start = max(0, i - 8)
            end = min(len(lines), i + 5)
            window = "\n".join(lines[start:end])
            if "client.post" not in window:
                continue
            # Skip if 'updated' key is absent (already caught by the weak guard)
            if '"updated"' not in window and "'updated'" not in window:
                continue
            # Stronger: verify 'updated' value is sourced from task.updated
            if "task.updated" not in window:
                violations.append(
                    f"  line {i + 1}: /move POST has 'updated' key but no "
                    f"'task.updated' source (may be hardcoded): {line.strip()!r}"
                )

        assert not violations, (
            "Move POST payloads in test_cockpit_mutation_api.py must source 'updated' from "
            "engine.show_task().updated (not hardcoded) per AC4:\n"
            + "\n".join(violations)
        )

    def test_shared_suite_config_is_engine_compatible(self, tmp_path: Path) -> None:
        """AC4: The _CONFIG_YAML in test_cockpit_mutation_api.py can initialize
        KanbanEngine without ConfigError.

        The shared move tests cannot execute when their board fixture raises
        ConfigError at KanbanEngine init. This test proves the shared suite's
        config format satisfies current engine validation requirements,
        including agent_map for every declared status.

        Fails when test_cockpit_mutation_api.py uses a stale config format
        that is missing agent_map — causing 37 setup errors that prevent AC4
        from being verified by executable regression of the named suite.
        """
        module_path = Path("tests/test_cockpit_mutation_api.py")
        spec = importlib.util.spec_from_file_location(
            "_shared_suite_probe", module_path
        )
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # defines _CONFIG_YAML and imports
        config_yaml: str = mod._CONFIG_YAML

        kanban_dir = tmp_path / "shared-board"
        kanban_dir.mkdir()
        (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()

        # Must not raise ConfigError — failure here proves the shared suite
        # is setup-blocked and AC4 cannot be confirmed by executable regression
        KanbanEngine(kanban_dir)
