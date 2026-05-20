from __future__ import annotations

"""Durable integration tests: Cockpit Memory Tab end-to-end (#1673).

Consolidation backstop: verifies the full engine->API chain works together
after all 6 sibling tasks (#1667-#1672) have been implemented.

AC coverage:
  AC1: Real MemoryEngine via DI override + FastAPI TestClient; full state-machine
       flow: save→pending, edit-with-scope_agents→curated, approve→approved,
       edit→curated (downgrade), delete→soft-deleted
  AC2: Every API call returns HTTP 200 and entry.state matches expected transition;
       GET /api/memories after save returns entry with state=pending and parse_errors=0
  AC3: edit with scope_agents → pending→curated; approve → curated→approved;
       edit of approved → curated (downgrade); delete of curated → {success:true}
  AC4: All 6 sibling test files exist and Python modules are importable without errors;
       cross-package import chain (owlbear_memory ← cockpit) is intact
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_memory.engine import MemoryEngine
from owlbear_memory.models import MemoryCategory, MemoryState

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


class TestMemoryRegressionDurable:
    """AC4: Cross-package import verification and sibling test file existence."""

    def test_owlbear_memory_package_importable(self) -> None:
        """Cross-package import: owlbear_memory exposes engine, models, errors."""
        from owlbear_memory.engine import MemoryEngine  # noqa: PLC0415
        from owlbear_memory.errors import (  # noqa: PLC0415
            ConcurrencyError,
            NotFoundError,
            TransitionError,
        )
        from owlbear_memory.models import MemoryCategory, MemoryEntry, MemoryState  # noqa: PLC0415

        assert MemoryEngine is not None
        assert MemoryEntry is not None
        assert MemoryState is not None
        assert MemoryCategory is not None
        assert NotFoundError is not None
        assert ConcurrencyError is not None
        assert TransitionError is not None

    def test_cockpit_memory_router_importable(self) -> None:
        """Cross-package import: owlbear_cockpit.routes.memory exposes router."""
        from owlbear_cockpit.routes.memory import router  # noqa: PLC0415

        assert router is not None

    def test_cockpit_app_includes_memory_routes(self) -> None:
        """Cockpit app registers /api/memories routes (memory router included)."""
        from owlbear_cockpit.main import app  # noqa: PLC0415

        paths = [getattr(r, "path", "") for r in app.routes]
        memory_paths = [p for p in paths if "memories" in p]
        assert len(memory_paths) >= 1, f"No /api/memories routes found; routes={paths}"

    def test_sibling_python_test_files_exist(self) -> None:
        """AC4: All Python sibling test files exist in the workspace tests/ directory."""
        test_dir = _WORKSPACE_ROOT / "tests"
        expected = [
            "test_memory_primitives_1667.py",
            "test_memory_engine_1668.py",
            "test_mutation_tools.py",
            "test_cockpit_memory_routes_1670.py",
        ]
        for name in expected:
            assert (test_dir / name).exists(), f"Sibling test file missing: {name}"

    def test_sibling_frontend_test_files_exist(self) -> None:
        """AC4: Frontend sibling test files exist at the expected paths."""
        web_tests = _WORKSPACE_ROOT / "serve" / "cockpit" / "web" / "src" / "__tests__"
        assert (web_tests / "MemoryTab_1671.test.tsx").exists(), "Frontend test file MemoryTab_1671.test.tsx missing"
        assert (web_tests / "MemoryTab_1672.test.tsx").exists(), "Frontend test file MemoryTab_1672.test.tsx missing"

    def test_sibling_python_test_modules_importable(self) -> None:
        """AC4: Python sibling test modules can be imported without errors."""
        root = str(_WORKSPACE_ROOT)
        if root not in sys.path:
            sys.path.insert(0, root)
        module_specs = [
            ("test_memory_primitives_1667", _WORKSPACE_ROOT / "tests" / "test_memory_primitives_1667.py"),
            ("test_memory_engine_1668", _WORKSPACE_ROOT / "tests" / "test_memory_engine_1668.py"),
            ("test_mutation_tools", _WORKSPACE_ROOT / "tests" / "test_mutation_tools.py"),
            ("test_cockpit_memory_routes_1670", _WORKSPACE_ROOT / "tests" / "test_cockpit_memory_routes_1670.py"),
        ]
        import importlib.util  # noqa: PLC0415

        for mod_name, mod_path in module_specs:
            spec = importlib.util.spec_from_file_location(mod_name, mod_path)
            assert spec is not None, f"Could not create spec for {mod_path}"
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None, f"Spec has no loader for {mod_path}"
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            assert mod is not None, f"Module {mod_name} failed to load"
