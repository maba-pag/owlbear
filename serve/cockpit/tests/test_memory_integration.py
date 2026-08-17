"""Protect the Cockpit Memory API's real engine-to-route state-machine flow."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from owlbear_memory.engine import MemoryEngine
from owlbear_memory.models import MemoryCategory, MemoryState

# Mined from #1673: real-engine Cockpit Memory API state-machine integration.

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def real_engine(tmp_path: Path) -> MemoryEngine:
    """Real MemoryEngine backed by an isolated temporary directory."""
    return MemoryEngine(memory_dir=tmp_path)


@pytest.fixture
def client(real_engine: MemoryEngine):
    """FastAPI TestClient with the real MemoryEngine injected via DI override."""
    from owlbear_cockpit.deps import get_memory_engine  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_memory_engine] = lambda: real_engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 + AC2 + AC3: Full state-machine integration flow
# ---------------------------------------------------------------------------


class TestMemoryStateMachineDurable:
    """Integration tests for the complete memory state-machine chain via API."""

    def test_save_creates_pending_entry(self, real_engine: MemoryEngine) -> None:
        """AC1/AC2: engine.save() creates an entry in pending state."""
        entry = real_engine.save(
            title="Integration Entry",
            content="Content for integration verification.",
            categories=[MemoryCategory.DOMAIN_KNOWLEDGE],
            confidence=0.9,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        assert entry.state == MemoryState.PENDING

    def test_get_memories_after_save_returns_pending_and_zero_parse_errors(
        self, real_engine: MemoryEngine, client: TestClient
    ) -> None:
        """AC2: GET /api/memories after save returns entry with state=pending and parse_errors=0."""
        entry = real_engine.save(
            title="Check GET Entry",
            content="Verifying GET /api/memories response.",
            categories=[MemoryCategory.BEHAVIOUR],
            confidence=0.85,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        response = client.get("/api/memories")
        assert response.status_code == 200
        body = response.json()
        assert body["parse_errors"] == 0
        ids = [e["id"] for e in body["entries"]]
        assert entry.id in ids
        found = next(e for e in body["entries"] if e["id"] == entry.id)
        assert found["state"] == "pending"

    def test_edit_with_scope_agents_promotes_pending_to_curated(
        self, real_engine: MemoryEngine, client: TestClient
    ) -> None:
        """AC3: POST /api/memories/{id}/edit with scope_agents promotes pending→curated."""
        entry = real_engine.save(
            title="Promote Test",
            content="Will be promoted via scope_agents edit.",
            categories=[MemoryCategory.PROCESS],
            confidence=0.8,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        response = client.post(
            f"/api/memories/{entry.id}/edit",
            json={
                "expected_updated_at": entry.updated_at,
                "scope_agents": ["builder"],
            },
        )
        assert response.status_code == 200
        assert response.json()["entry"]["state"] == "curated"

    def test_approve_transitions_curated_to_approved(self, real_engine: MemoryEngine, client: TestClient) -> None:
        """AC3: POST /api/memories/{id}/approve transitions curated→approved."""
        entry = real_engine.save(
            title="Approve Test",
            content="Will be curated then approved.",
            categories=[MemoryCategory.DOMAIN_KNOWLEDGE],
            confidence=0.95,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        edit_resp = client.post(
            f"/api/memories/{entry.id}/edit",
            json={
                "expected_updated_at": entry.updated_at,
                "scope_agents": ["reviewer"],
            },
        )
        assert edit_resp.status_code == 200
        curated = edit_resp.json()["entry"]
        assert curated["state"] == "curated"

        approve_resp = client.post(
            f"/api/memories/{entry.id}/approve",
            json={"expected_updated_at": curated["updated_at"]},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["entry"]["state"] == "approved"

    def test_edit_approved_entry_downgrades_to_curated(self, real_engine: MemoryEngine, client: TestClient) -> None:
        """AC3: POST edit of an approved entry downgrades it to curated."""
        entry = real_engine.save(
            title="Downgrade Test",
            content="Will be downgraded: approved→curated.",
            categories=[MemoryCategory.PITFALL],
            confidence=0.9,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        # pending → curated
        edit_resp = client.post(
            f"/api/memories/{entry.id}/edit",
            json={"expected_updated_at": entry.updated_at, "scope_agents": ["scoped"]},
        )
        curated = edit_resp.json()["entry"]

        # curated → approved
        approve_resp = client.post(
            f"/api/memories/{entry.id}/approve",
            json={"expected_updated_at": curated["updated_at"]},
        )
        approved = approve_resp.json()["entry"]
        assert approved["state"] == "approved"

        # approved → curated (downgrade)
        downgrade_resp = client.post(
            f"/api/memories/{entry.id}/edit",
            json={"expected_updated_at": approved["updated_at"], "title": "Amended"},
        )
        assert downgrade_resp.status_code == 200
        assert downgrade_resp.json()["entry"]["state"] == "curated"

    def test_delete_curated_entry_soft_deletes(self, real_engine: MemoryEngine, client: TestClient) -> None:
        """AC3: POST delete of a curated entry returns {success:true}."""
        entry = real_engine.save(
            title="Delete Test",
            content="Will be promoted then soft-deleted.",
            categories=[MemoryCategory.GOAL],
            confidence=0.75,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        edit_resp = client.post(
            f"/api/memories/{entry.id}/edit",
            json={"expected_updated_at": entry.updated_at, "scope_agents": ["agent"]},
        )
        curated = edit_resp.json()["entry"]

        delete_resp = client.post(
            f"/api/memories/{entry.id}/delete",
            json={"expected_updated_at": curated["updated_at"]},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json() == {"success": True}

    def test_full_state_machine_sequence(self, real_engine: MemoryEngine, client: TestClient) -> None:
        """AC1+AC2+AC3: Complete flow: save→pending→curated→approved→curated→soft-deleted."""
        # Step 1: save → pending
        entry = real_engine.save(
            title="Full Flow Entry",
            content="End-to-end state machine verification.",
            categories=[MemoryCategory.BEHAVIOUR],
            confidence=0.88,
            source_agent="consolidation-agent",
            scope_agents=[],
        )
        assert entry.state == MemoryState.PENDING

        # Step 2: GET /api/memories → state=pending, parse_errors=0
        get_resp = client.get("/api/memories")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["parse_errors"] == 0
        found = next(e for e in body["entries"] if e["id"] == entry.id)
        assert found["state"] == "pending"

        # Step 3: edit with scope_agents → curated
        edit_resp = client.post(
            f"/api/memories/{entry.id}/edit",
            json={"expected_updated_at": entry.updated_at, "scope_agents": ["scoped-agent"]},
        )
        assert edit_resp.status_code == 200
        curated = edit_resp.json()["entry"]
        assert curated["state"] == "curated"

        # Step 4: approve → approved
        approve_resp = client.post(
            f"/api/memories/{entry.id}/approve",
            json={"expected_updated_at": curated["updated_at"]},
        )
        assert approve_resp.status_code == 200
        approved = approve_resp.json()["entry"]
        assert approved["state"] == "approved"

        # Step 5: edit → curated (downgrade)
        downgrade_resp = client.post(
            f"/api/memories/{entry.id}/edit",
            json={"expected_updated_at": approved["updated_at"], "title": "Amended"},
        )
        assert downgrade_resp.status_code == 200
        downgraded = downgrade_resp.json()["entry"]
        assert downgraded["state"] == "curated"

        # Step 6: delete → soft-deleted (curated → deleted)
        delete_resp = client.post(
            f"/api/memories/{entry.id}/delete",
            json={"expected_updated_at": downgraded["updated_at"]},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json() == {"success": True}


# ---------------------------------------------------------------------------
# AC4: Sibling suite regression guard
# ---------------------------------------------------------------------------
