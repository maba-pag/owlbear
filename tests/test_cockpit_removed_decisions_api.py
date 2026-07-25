"""Regression guards for removed Cockpit /api/decisions endpoints (#1863).

AC1: POST /api/decisions/{id}/resolve returns HTTP 404 after endpoint removal.
AC2: GET /api/decisions/pending returns HTTP 404 after endpoint removal.
AC3: Frontend decisions.test.ts removed; LegacyPendingDRResponse and dual-format
     normalization removed from usePendingDRs.ts.
AC4: Legacy decisions route module (decisions.py) is fully removed from disk.

These tests keep the removed route surface and old dual-format frontend hook
support from being reintroduced.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Minimal board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    board_dir = base_dir / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board_dir / "tasks").mkdir(exist_ok=True)
    (board_dir / "archive").mkdir(exist_ok=True)
    return board_dir


def _make_decisions_dir(base_dir: Path) -> Path:
    d = base_dir / "decisions"
    (d / "pending").mkdir(parents=True)
    (d / "resolved").mkdir(parents=True)
    return d


@pytest.fixture()
def engine(tmp_path: Path) -> KanbanEngine:
    board_dir = _make_board(tmp_path)
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture()
def decisions_dir(tmp_path: Path) -> Path:
    return _make_decisions_dir(tmp_path)


@pytest.fixture()
def client(engine: KanbanEngine, decisions_dir: Path):
    """FastAPI TestClient with engine and (if present) decisions_dir overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
    from owlbear_cockpit.deps import get_engine  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine

    get_decisions_dir_fn = getattr(cockpit_deps, "get_decisions_dir", None)
    if get_decisions_dir_fn is not None:
        app.dependency_overrides[get_decisions_dir_fn] = lambda: decisions_dir

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Absolute paths for frontend file assertions
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_HOOK_FILE = _PROJECT_ROOT / "serve" / "cockpit" / "web" / "src" / "hooks" / "usePendingDRs.ts"
_DECISIONS_TEST_FILE = _PROJECT_ROOT / "serve" / "cockpit" / "web" / "src" / "__tests__" / "decisions.test.ts"


# ---------------------------------------------------------------------------
# AC1 + AC2 + AC4: backend endpoint removal and module gone from disk
# ---------------------------------------------------------------------------


def _write_pending_dr(decisions_dir: Path, *, stem: str, task_id: int) -> Path:
    """Write a minimal pending DR file and return its path."""
    path = decisions_dir / "pending" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-05-01'\n"
        "response: pending\n"
        "---\n\n"
        f"# {stem}\n\nShould we expand the scope?\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


class TestRemovedDecisionsApi:
    """Verify old /api/decisions/* endpoints are removed and module is gone."""

    def test_post_resolve_existing_decision_approved_returns_404(
        self, client: TestClient, decisions_dir: Path, engine: KanbanEngine
    ) -> None:
        """AC1: POST to an existing decision ID must return 404."""
        task = engine.create_task("Scope gate")
        engine.edit_task(task.id, blocked=True, block_reason="DR pending")
        _write_pending_dr(decisions_dir, stem="1863-scope-dr", task_id=task.id)
        response = client.post(
            "/api/decisions/1863-scope-dr/resolve",
            json={"response": "approved"},
        )
        assert response.status_code == 404

    def test_post_resolve_existing_decision_needs_info_returns_404(
        self, client: TestClient, decisions_dir: Path, engine: KanbanEngine
    ) -> None:
        """AC1: POST with needs-info to a known decision ID must return 404."""
        task = engine.create_task("Needs-info gate")
        engine.edit_task(task.id, blocked=True, block_reason="DR pending")
        _write_pending_dr(decisions_dir, stem="1863-ni-dr", task_id=task.id)
        response = client.post(
            "/api/decisions/1863-ni-dr/resolve",
            json={"response": "needs-info", "notes": "Please clarify scope."},
        )
        assert response.status_code == 404

    def test_post_resolve_decision_invalid_payload_returns_404(self, client: TestClient) -> None:
        """AC1: POST to removed path returns 404 even when payload is invalid."""
        response = client.post(
            "/api/decisions/any-dr/resolve",
            json={"notes": "missing required response field"},
        )
        assert response.status_code == 404

    def test_get_decisions_pending_returns_404(self, client: TestClient) -> None:
        """AC2: GET /api/decisions/pending must return 404 after endpoint removal."""
        response = client.get("/api/decisions/pending")
        assert response.status_code == 404

    def test_old_decisions_route_module_file_does_not_exist(self) -> None:
        """AC4: decisions.py route module is physically removed from disk."""
        import owlbear_cockpit  # noqa: PLC0415

        cockpit_dir = Path(owlbear_cockpit.__file__).parent
        decisions_file = cockpit_dir / "routes" / "decisions.py"
        assert not decisions_file.exists(), f"Legacy decisions route module still present at {decisions_file}"


# ---------------------------------------------------------------------------
# AC3: frontend legacy type and normalization code removal
# ---------------------------------------------------------------------------


class TestRemovedFrontendDecisionsSupport:
    """Verify old frontend test file and legacy hook types/normalization are removed."""

    def test_frontend_decisions_test_file_removed(self) -> None:
        """AC3: decisions.test.ts (testing old POST /api/decisions endpoint) is deleted."""
        assert not _DECISIONS_TEST_FILE.exists(), f"Legacy frontend test file still exists: {_DECISIONS_TEST_FILE}"

    def test_legacy_pending_dr_response_interface_removed(self) -> None:
        """AC3: LegacyPendingDRResponse interface is removed from usePendingDRs.ts."""
        content = _HOOK_FILE.read_text(encoding="utf-8")
        assert "LegacyPendingDRResponse" not in content

    def test_is_pending_requests_payload_guard_removed(self) -> None:
        """AC3: isPendingRequestsPayload dual-format type guard is removed from hook."""
        content = _HOOK_FILE.read_text(encoding="utf-8")
        assert "isPendingRequestsPayload" not in content

    def test_dual_format_payload_items_access_removed(self) -> None:
        """AC3: Legacy payload.items branch in normalization is removed from hook.

        The old dual-format onSuccess handler reads payload.items to support
        LegacyPendingDRResponse.  After cleanup only the array (new) shape remains.
        """
        content = _HOOK_FILE.read_text(encoding="utf-8")
        assert "payload.items" not in content
