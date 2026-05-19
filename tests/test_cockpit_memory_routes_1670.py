from __future__ import annotations

"""Failing tests for cockpit memory routes with OCC (#1670).

RED phase — all tests must fail until routes are implemented in GREEN.

AC coverage:
  - AC1: GET /api/memories → { entries: [...], parse_errors: int }, all 11 entry fields, all states
  - AC2: POST /api/memories/{id}/approve → 200 { entry }, 404/409/422 with MEM_ codes
  - AC3: POST /api/memories/{id}/edit → 200 { entry }, state transition, extra fields forbidden, errors
  - AC4: POST /api/memories/{id}/delete → 200 { success: true }, hard/soft delete, errors
  - AC5: Memory exception handlers in main.py use owlbear_memory.errors imports, MEM_ codes
"""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from owlbear_memory.errors import ConcurrencyError, NotFoundError, TransitionError
from owlbear_memory.models import MemoryCategory, MemoryEntry, MemoryState

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = "2026-05-19T10:00:00+00:00"
_ENTRY_ID = "11111111-1111-4111-a111-111111111111"
_ENTRY_ID_2 = "22222222-2222-4222-a222-222222222222"
_ENTRY_ID_3 = "33333333-3333-4333-a333-333333333333"
_ENTRY_ID_4 = "44444444-4444-4444-a444-444444444444"


def _make_entry(
    entry_id: str = _ENTRY_ID,
    state: MemoryState = MemoryState.PENDING,
    approved_at: str | None = None,
) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        title="Test Memory",
        content="Some memory content.",
        categories=[MemoryCategory.DOMAIN_KNOWLEDGE],
        confidence=0.9,
        state=state,
        scope_agents=[],
        source_agent="test-agent",
        created_at=_NOW,
        updated_at=_NOW,
        approved_at=approved_at,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_engine() -> MagicMock:
    """Mock MemoryEngine with default empty entries."""
    from owlbear_memory.engine import MemoryEngine  # noqa: PLC0415

    engine = MagicMock(spec=MemoryEngine)
    engine.get_entries.return_value = []
    engine.parse_errors = 0
    return engine


@pytest.fixture
def client(mock_engine: MagicMock):
    """FastAPI TestClient with memory engine injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.deps import get_memory_engine  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_memory_engine] = lambda: mock_engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: GET /api/memories
# ---------------------------------------------------------------------------


class TestFromAC_GetMemories:
    """AC1: GET /api/memories returns 200 with entries list and parse_errors integer."""

    def test_list_returns_200(self, client: TestClient) -> None:
        """Happy path: GET /api/memories returns HTTP 200."""
        response = client.get("/api/memories")
        assert response.status_code == 200

    def test_list_returns_entries_and_parse_errors_keys(self, client: TestClient) -> None:
        """Response body has top-level keys: entries (list) and parse_errors (int)."""
        response = client.get("/api/memories")
        assert response.status_code == 200
        body = response.json()
        assert "entries" in body
        assert "parse_errors" in body
        assert isinstance(body["entries"], list)
        assert isinstance(body["parse_errors"], int)

    def test_list_entry_has_all_required_fields(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Each entry in the response has all 11 required AC-enumerated fields."""
        entry = _make_entry()
        mock_engine.get_entries.return_value = [entry]
        response = client.get("/api/memories")
        assert response.status_code == 200
        items = response.json()["entries"]
        assert len(items) == 1
        item = items[0]
        required_fields = {
            "id",
            "title",
            "content",
            "categories",
            "confidence",
            "state",
            "scope_agents",
            "source_agent",
            "created_at",
            "updated_at",
            "approved_at",
        }
        missing = required_fields - item.keys()
        assert not missing, f"Entry is missing fields: {missing}"

    def test_list_entry_field_values_match_engine_output(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Field values in the response entry match the MemoryEntry from the engine."""
        entry = _make_entry(state=MemoryState.CURATED)
        mock_engine.get_entries.return_value = [entry]
        response = client.get("/api/memories")
        assert response.status_code == 200
        item = response.json()["entries"][0]
        assert item["id"] == entry.id
        assert item["title"] == entry.title
        assert item["content"] == entry.content
        assert item["confidence"] == entry.confidence
        assert item["state"] == "curated"
        assert item["source_agent"] == entry.source_agent
        assert item["created_at"] == _NOW
        assert item["updated_at"] == _NOW
        assert item["approved_at"] is None

    def test_list_includes_deleted_state_entries(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Response includes entries with state=deleted — not filtered out."""
        deleted_entry = _make_entry(entry_id=_ENTRY_ID_2, state=MemoryState.DELETED)
        mock_engine.get_entries.return_value = [deleted_entry]
        response = client.get("/api/memories")
        assert response.status_code == 200
        items = response.json()["entries"]
        states = [item["state"] for item in items]
        assert "deleted" in states

    def test_list_includes_all_four_lifecycle_states(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Response includes entries for pending, curated, approved, and deleted states."""
        entries = [
            _make_entry(_ENTRY_ID, MemoryState.PENDING),
            _make_entry(_ENTRY_ID_2, MemoryState.CURATED),
            _make_entry(_ENTRY_ID_3, MemoryState.APPROVED, approved_at=_NOW),
            _make_entry(_ENTRY_ID_4, MemoryState.DELETED),
        ]
        mock_engine.get_entries.return_value = entries
        response = client.get("/api/memories")
        assert response.status_code == 200
        items = response.json()["entries"]
        states = {item["state"] for item in items}
        assert states == {"pending", "curated", "approved", "deleted"}

    def test_list_parse_errors_reflects_engine_count(self, client: TestClient, mock_engine: MagicMock) -> None:
        """parse_errors in response matches engine.parse_errors attribute value."""
        mock_engine.parse_errors = 3
        response = client.get("/api/memories")
        assert response.status_code == 200
        assert response.json()["parse_errors"] == 3

    def test_list_empty_returns_empty_list_and_zero_errors(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Empty engine returns { entries: [], parse_errors: 0 }."""
        mock_engine.get_entries.return_value = []
        mock_engine.parse_errors = 0
        response = client.get("/api/memories")
        assert response.status_code == 200
        body = response.json()
        assert body["entries"] == []
        assert body["parse_errors"] == 0


# ---------------------------------------------------------------------------
# AC2: POST /api/memories/{id}/approve
# ---------------------------------------------------------------------------


class TestFromAC_ApproveMemory:
    """AC2: POST /api/memories/{id}/approve with OCC body and structured error envelope."""

    def test_approve_returns_200_with_entry_wrapper(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Happy path: approve returns 200 with { entry: MemoryEntryResponse } shape."""
        updated_entry = _make_entry(_ENTRY_ID, MemoryState.APPROVED, approved_at=_NOW)
        mock_engine.approve.return_value = updated_entry
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 200
        body = response.json()
        assert "entry" in body
        assert body["entry"]["id"] == _ENTRY_ID
        assert body["entry"]["state"] == "approved"

    def test_approve_calls_engine_with_entry_id_and_occ_token(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Engine.approve() is called with entry_id and expected_updated_at."""
        updated_entry = _make_entry(_ENTRY_ID, MemoryState.APPROVED, approved_at=_NOW)
        mock_engine.approve.return_value = updated_entry
        client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        mock_engine.approve.assert_called_once_with(_ENTRY_ID, _NOW)

    def test_approve_not_found_returns_404_with_mem_not_found_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """NotFoundError from engine returns 404 with code=MEM_NOT_FOUND."""
        mock_engine.approve.side_effect = NotFoundError("entry not found")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_NOT_FOUND"
        assert "message" in body

    def test_approve_concurrency_error_returns_409_with_mem_conflict_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """ConcurrencyError returns 409 with code=MEM_CONFLICT."""
        mock_engine.approve.side_effect = ConcurrencyError("occ mismatch")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": "2000-01-01T00:00:00+00:00"},
        )
        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_CONFLICT"
        assert "message" in body

    def test_approve_transition_error_returns_422_with_mem_invalid_transition_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """TransitionError (non-curated state) returns 422 with code=MEM_INVALID_TRANSITION."""
        mock_engine.approve.side_effect = TransitionError("approve() not allowed from state pending")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_INVALID_TRANSITION"
        assert "message" in body

    def test_approve_missing_body_returns_422(self, client: TestClient) -> None:
        """Missing request body returns 422 from Pydantic validation."""
        response = client.post(f"/api/memories/{_ENTRY_ID}/approve")
        assert response.status_code == 422

    def test_approve_missing_expected_updated_at_returns_422(self, client: TestClient) -> None:
        """Missing required expected_updated_at field returns 422."""
        response = client.post(f"/api/memories/{_ENTRY_ID}/approve", json={})
        assert response.status_code == 422

    def test_approve_error_envelope_uses_code_and_message_keys(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """Error responses use cockpit envelope { code, message }, not FastAPI { detail }."""
        mock_engine.approve.side_effect = NotFoundError("nope")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        body = response.json()
        assert "detail" not in body
        assert "code" in body
        assert "message" in body


# ---------------------------------------------------------------------------
# AC3: POST /api/memories/{id}/edit
# ---------------------------------------------------------------------------


class TestFromAC_EditMemory:
    """AC3: POST /api/memories/{id}/edit with OCC, optional fields, extra field rejection."""

    def test_edit_returns_200_with_entry_wrapper(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Happy path: edit returns 200 with { entry: MemoryEntryResponse } shape."""
        updated_entry = _make_entry(_ENTRY_ID, MemoryState.CURATED)
        mock_engine.edit.return_value = updated_entry
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "title": "Updated Title"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "entry" in body
        assert body["entry"]["id"] == _ENTRY_ID

    def test_edit_all_five_optional_fields_accepted(self, client: TestClient, mock_engine: MagicMock) -> None:
        """All 5 optional editable fields (title, content, categories, confidence, scope_agents) accepted."""
        updated_entry = _make_entry(_ENTRY_ID, MemoryState.CURATED)
        mock_engine.edit.return_value = updated_entry
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={
                "expected_updated_at": _NOW,
                "title": "New Title",
                "content": "New content text.",
                "categories": ["pitfall"],
                "confidence": 0.8,
                "scope_agents": ["agent-one"],
            },
        )
        assert response.status_code == 200

    def test_edit_approved_entry_response_shows_curated_state(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Editing an approved entry causes engine to return curated state (state transition)."""
        curated_entry = _make_entry(_ENTRY_ID, MemoryState.CURATED)
        mock_engine.edit.return_value = curated_entry
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "title": "Modified"},
        )
        assert response.status_code == 200
        assert response.json()["entry"]["state"] == "curated"

    def test_edit_extra_fields_forbidden_returns_422(self, client: TestClient) -> None:
        """Extra fields not in the allowlist are rejected with 422 (extra=forbid)."""
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "state": "approved"},
        )
        assert response.status_code == 422

    def test_edit_source_agent_field_rejected_as_extra(self, client: TestClient) -> None:
        """'source_agent' is not an editable field and must be rejected with 422."""
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "source_agent": "evil-agent"},
        )
        assert response.status_code == 422

    def test_edit_not_found_returns_404_with_mem_not_found_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """NotFoundError returns 404 with code=MEM_NOT_FOUND."""
        mock_engine.edit.side_effect = NotFoundError("entry not found")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "title": "New"},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_NOT_FOUND"

    def test_edit_concurrency_error_returns_409_with_mem_conflict_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """ConcurrencyError returns 409 with code=MEM_CONFLICT."""
        mock_engine.edit.side_effect = ConcurrencyError("stale token")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": "2000-01-01T00:00:00+00:00", "title": "New"},
        )
        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_CONFLICT"

    def test_edit_deleted_entry_returns_422_with_mem_invalid_transition_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """TransitionError from editing a deleted entry returns 422 with MEM_INVALID_TRANSITION."""
        mock_engine.edit.side_effect = TransitionError("edit() not allowed from state deleted")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "title": "Nope"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_INVALID_TRANSITION"

    def test_edit_missing_expected_updated_at_returns_422(self, client: TestClient) -> None:
        """Missing required expected_updated_at returns 422."""
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"title": "No OCC token"},
        )
        assert response.status_code == 422

    def test_edit_categories_must_be_valid_memory_category_values(self, client: TestClient) -> None:
        """Invalid category value in categories list is rejected by Pydantic with 422."""
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/edit",
            json={"expected_updated_at": _NOW, "categories": ["not-a-real-category"]},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC4: POST /api/memories/{id}/delete
# ---------------------------------------------------------------------------


class TestFromAC_DeleteMemory:
    """AC4: POST /api/memories/{id}/delete — hard/soft delete with { success: true } response."""

    def test_delete_returns_200_with_success_true(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Happy path: delete returns 200 with exactly { success: true }."""
        mock_engine.delete.return_value = _make_entry(_ENTRY_ID)
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/delete",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 200
        body = response.json()
        assert body == {"success": True}

    def test_delete_success_response_has_exactly_one_key(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Delete success response is exactly { success: true }, no additional fields."""
        mock_engine.delete.return_value = _make_entry(_ENTRY_ID)
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/delete",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"success"}
        assert body["success"] is True

    def test_delete_calls_engine_with_correct_args(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Engine.delete() is called with entry_id and expected_updated_at."""
        mock_engine.delete.return_value = _make_entry(_ENTRY_ID)
        client.post(
            f"/api/memories/{_ENTRY_ID}/delete",
            json={"expected_updated_at": _NOW},
        )
        mock_engine.delete.assert_called_once_with(_ENTRY_ID, _NOW)

    def test_delete_not_found_returns_404_with_mem_not_found_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """NotFoundError returns 404 with code=MEM_NOT_FOUND."""
        mock_engine.delete.side_effect = NotFoundError("entry not found")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/delete",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_NOT_FOUND"
        assert "message" in body

    def test_delete_concurrency_error_returns_409_with_mem_conflict_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """ConcurrencyError returns 409 with code=MEM_CONFLICT."""
        mock_engine.delete.side_effect = ConcurrencyError("stale token")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/delete",
            json={"expected_updated_at": "2000-01-01T00:00:00+00:00"},
        )
        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_CONFLICT"

    def test_delete_already_deleted_entry_returns_422_with_mem_invalid_transition_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """TransitionError from deleting already-deleted entry → 422 MEM_INVALID_TRANSITION."""
        mock_engine.delete.side_effect = TransitionError("delete() not allowed from state deleted")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/delete",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" not in body
        assert body["code"] == "MEM_INVALID_TRANSITION"

    def test_delete_missing_expected_updated_at_returns_422(self, client: TestClient) -> None:
        """Missing expected_updated_at field returns 422 from Pydantic validation."""
        response = client.post(f"/api/memories/{_ENTRY_ID}/delete", json={})
        assert response.status_code == 422

    def test_delete_missing_body_returns_422(self, client: TestClient) -> None:
        """Missing request body entirely returns 422."""
        response = client.post(f"/api/memories/{_ENTRY_ID}/delete")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC5: Memory exception handlers in main.py — qualified imports, MEM_ codes
# ---------------------------------------------------------------------------


class TestFromAC_MemoryExceptionHandlers:
    """AC5: Exception handlers for owlbear_memory.errors registered in main.py.

    Verified via AST scan (import source) and runtime behavior (code strings).
    """

    def test_main_registers_memory_exception_handlers(self) -> None:
        """main.py registers handlers for owlbear_memory.errors error types."""
        from pathlib import Path  # noqa: PLC0415

        main_path = Path(__file__).parent.parent / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "main.py"
        source = main_path.read_text(encoding="utf-8")
        assert "owlbear_memory" in source, (
            "main.py must import from owlbear_memory.errors and register memory exception handlers"
        )

    def test_main_memory_errors_imported_from_owlbear_memory_errors_module(self) -> None:
        """Memory error types are imported from 'owlbear_memory.errors' in main.py."""
        import ast  # noqa: PLC0415
        from pathlib import Path  # noqa: PLC0415

        main_path = Path(__file__).parent.parent / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "main.py"
        source = main_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        memory_imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "owlbear_memory.errors" in node.module:
                memory_imported_names.update(alias.name for alias in node.names)

        required_memory_error_types = {"NotFoundError", "ConcurrencyError", "TransitionError"}
        missing = required_memory_error_types - memory_imported_names
        assert not missing, (
            f"main.py must import {missing} from owlbear_memory.errors. "
            f"Currently importing from owlbear_memory.errors: {memory_imported_names}"
        )

    def test_not_found_error_returns_mem_not_found_code(self, client: TestClient, mock_engine: MagicMock) -> None:
        """NotFoundError from memory engine returns MEM_NOT_FOUND, not ERR_NOT_FOUND."""
        mock_engine.approve.side_effect = NotFoundError("entry not found")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 404
        assert response.json()["code"] == "MEM_NOT_FOUND"

    def test_concurrency_error_returns_mem_conflict_code(self, client: TestClient, mock_engine: MagicMock) -> None:
        """ConcurrencyError from memory engine returns MEM_CONFLICT, not ERR_STALE."""
        mock_engine.approve.side_effect = ConcurrencyError("occ mismatch")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "MEM_CONFLICT"

    def test_transition_error_returns_mem_invalid_transition_code(
        self, client: TestClient, mock_engine: MagicMock
    ) -> None:
        """TransitionError from memory engine returns MEM_INVALID_TRANSITION."""
        mock_engine.approve.side_effect = TransitionError("invalid state")
        response = client.post(
            f"/api/memories/{_ENTRY_ID}/approve",
            json={"expected_updated_at": _NOW},
        )
        assert response.status_code == 422
        assert response.json()["code"] == "MEM_INVALID_TRANSITION"

    def test_all_memory_error_codes_have_mem_prefix(self, client: TestClient, mock_engine: MagicMock) -> None:
        """All three memory error codes start with 'MEM_' — not 'ERR_' (kanban prefix)."""
        cases = [
            (NotFoundError("nf"), 404, "MEM_NOT_FOUND"),
            (ConcurrencyError("cc"), 409, "MEM_CONFLICT"),
            (TransitionError("te"), 422, "MEM_INVALID_TRANSITION"),
        ]
        for exc, expected_status, expected_code in cases:
            mock_engine.approve.side_effect = exc
            response = client.post(
                f"/api/memories/{_ENTRY_ID}/approve",
                json={"expected_updated_at": _NOW},
            )
            assert response.status_code == expected_status, (
                f"Expected status {expected_status} for {type(exc).__name__}, got {response.status_code}"
            )
            assert response.json()["code"] == expected_code, (
                f"Expected code {expected_code!r} for {type(exc).__name__}, got {response.json().get('code')!r}"
            )
