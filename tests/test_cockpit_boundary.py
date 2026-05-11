"""Boundary and skeleton tests for the cockpit package (#924).

Covers:
- AC#1: pyproject.toml exists as workspace member with required deps
- AC#2: owlbear_cockpit package is importable
- AC#3: main.py exposes a FastAPI app with a /health endpoint
- AC#4: adapter.py is importable
- AC#5: AST boundary scan — cockpit src must not import forbidden engine names
- AC#6: root pyproject.toml [tool.ruff] src includes serve/cockpit/src
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {"claim_task", "start_work", "end_work", "pick_dispatchable"}
)
# Both top-level and submodule import paths are checked per research finding.
_FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {"owlbear_kanban", "owlbear_kanban.engine", "owlbear_kanban.dispatch"}
)


def _collect_forbidden_imports(src_root: Path) -> list[tuple[str, str, int]]:
    """Return (relative_file, name, lineno) for every forbidden import in *src_root*.

    Scans all ``.py`` files recursively.  Detects both::

        from owlbear_kanban import pick_dispatchable
        from owlbear_kanban.engine import start_work
    """
    violations: list[tuple[str, str, int]] = []
    for py_file in sorted(src_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in _FORBIDDEN_MODULES:
                    for alias in node.names:
                        if alias.name in _FORBIDDEN_NAMES:
                            violations.append(
                                (
                                    str(py_file.relative_to(src_root)),
                                    alias.name,
                                    node.lineno,
                                )
                            )
    return violations


# ---------------------------------------------------------------------------
# AC#1-4: Package skeleton
# ---------------------------------------------------------------------------


class TestFromAC_CockpitPackageSkeleton:
    """Package structure, importability, FastAPI app, and adapter placeholder.

    AC#1: pyproject.toml with required deps
    AC#2: owlbear_cockpit importable
    AC#3: main.py has FastAPI app + /health endpoint
    AC#4: adapter.py importable
    """

    # -- AC#1: pyproject.toml ------------------------------------------------

    def test_pyproject_toml_exists(self, project_root: Path) -> None:
        """AC#1: serve/cockpit/pyproject.toml exists."""
        pyproject = project_root / "serve" / "cockpit" / "pyproject.toml"
        assert pyproject.exists(), f"Missing workspace member config: {pyproject}"

    def test_pyproject_toml_declares_owlbear_kanban_dep(
        self, project_root: Path
    ) -> None:
        """AC#1: pyproject.toml lists owlbear-kanban as a dependency."""
        content = (project_root / "serve" / "cockpit" / "pyproject.toml").read_text()
        assert "owlbear-kanban" in content

    def test_pyproject_toml_declares_fastapi_dep(self, project_root: Path) -> None:
        """AC#1: pyproject.toml lists fastapi as a dependency."""
        content = (project_root / "serve" / "cockpit" / "pyproject.toml").read_text()
        assert "fastapi" in content

    def test_pyproject_toml_declares_uvicorn_dep(self, project_root: Path) -> None:
        """AC#1: pyproject.toml lists uvicorn as a dependency."""
        content = (project_root / "serve" / "cockpit" / "pyproject.toml").read_text()
        assert "uvicorn" in content

    def test_pyproject_toml_declares_pydantic_dep(self, project_root: Path) -> None:
        """AC#1: pyproject.toml lists pydantic as a dependency."""
        content = (project_root / "serve" / "cockpit" / "pyproject.toml").read_text()
        assert "pydantic" in content

    def test_pyproject_toml_has_workspace_source_for_kanban(
        self, project_root: Path
    ) -> None:
        """AC#1: pyproject.toml wires owlbear-kanban as a uv workspace source."""
        content = (project_root / "serve" / "cockpit" / "pyproject.toml").read_text()
        assert "workspace = true" in content, (
            "owlbear-kanban must be declared as workspace source "
            "([tool.uv.sources] owlbear-kanban = { workspace = true })"
        )

    # -- AC#2: package importable --------------------------------------------

    def test_package_importable(self) -> None:
        """AC#2: import owlbear_cockpit succeeds and resolves package name."""
        import owlbear_cockpit  # noqa: F401

        assert owlbear_cockpit.__name__ == "owlbear_cockpit"

    # -- AC#3: main.py + /health endpoint ------------------------------------

    def test_main_module_importable(self) -> None:
        """AC#3: owlbear_cockpit.main is importable."""
        import owlbear_cockpit.main  # noqa: F401

    def test_main_module_exposes_fastapi_app(self) -> None:
        """AC#3: main.py exposes a FastAPI application instance named ``app``."""
        from fastapi import FastAPI
        from owlbear_cockpit.main import app

        assert isinstance(app, FastAPI)

    def test_health_endpoint_exists_and_returns_200(self) -> None:
        """AC#3: GET /health returns HTTP 200."""
        from fastapi.testclient import TestClient
        from owlbear_cockpit.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_json_body(self) -> None:
        """AC#3: /health response body is a JSON object."""
        from fastapi.testclient import TestClient
        from owlbear_cockpit.main import app

        client = TestClient(app)
        response = client.get("/health")
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected JSON object, got {type(body).__name__}"
        )

    def test_health_endpoint_requires_no_auth(self) -> None:
        """AC#3: /health is reachable without any authentication headers."""
        from fastapi.testclient import TestClient
        from owlbear_cockpit.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        # Must not be 401 or 403 — unauthenticated access is expected.
        assert response.status_code not in (401, 403), (
            f"/health returned {response.status_code} — endpoint must not require auth"
        )


# ---------------------------------------------------------------------------
# AC#5: Boundary enforcement (AST scan)
# ---------------------------------------------------------------------------


class TestFromAC_BoundaryEnforcement:
    """AST boundary scan — cockpit src must not import D12-forbidden engine names.

    AC#5: scan all .py files under serve/cockpit/src/ for imports of
    claim_task, start_work, end_work, pick_dispatchable from owlbear_kanban*.
    """

    @pytest.fixture
    def cockpit_src_root(self, project_root: Path) -> Path:
        """Return path to cockpit src, asserting it exists."""
        src = project_root / "serve" / "cockpit" / "src"
        assert src.exists(), (
            f"serve/cockpit/src/ not found at {src}. "
            "Builder must create the package directory before boundary scan is meaningful."
        )
        return src

    def test_cockpit_src_directory_exists(self, project_root: Path) -> None:
        """AC#5 precondition: serve/cockpit/src/ directory exists."""
        src = project_root / "serve" / "cockpit" / "src"
        assert src.exists(), f"serve/cockpit/src/ missing at {src}"

    def test_scan_covers_at_least_one_python_file(self, cockpit_src_root: Path) -> None:
        """AC#5: scan must find .py files — a vacuous pass is not acceptable."""
        py_files = list(cockpit_src_root.rglob("*.py"))
        assert len(py_files) > 0, (
            f"No .py files found under {cockpit_src_root}. "
            "Builder must create package source files before boundary test is meaningful."
        )

    def test_no_forbidden_import_claim_task(self, cockpit_src_root: Path) -> None:
        """AC#5: cockpit src must not import 'claim_task' from owlbear_kanban*."""
        violations = [
            (f, n, ln)
            for f, n, ln in _collect_forbidden_imports(cockpit_src_root)
            if n == "claim_task"
        ]
        assert violations == [], (
            f"D12 violation — 'claim_task' imported at: {violations}"
        )

    def test_no_forbidden_import_start_work(self, cockpit_src_root: Path) -> None:
        """AC#5: cockpit src must not import 'start_work' from owlbear_kanban*."""
        violations = [
            (f, n, ln)
            for f, n, ln in _collect_forbidden_imports(cockpit_src_root)
            if n == "start_work"
        ]
        assert violations == [], (
            f"D12 violation — 'start_work' imported at: {violations}"
        )

    def test_no_forbidden_import_end_work(self, cockpit_src_root: Path) -> None:
        """AC#5: cockpit src must not import 'end_work' from owlbear_kanban*."""
        violations = [
            (f, n, ln)
            for f, n, ln in _collect_forbidden_imports(cockpit_src_root)
            if n == "end_work"
        ]
        assert violations == [], f"D12 violation — 'end_work' imported at: {violations}"

    def test_no_forbidden_import_pick_dispatchable(
        self, cockpit_src_root: Path
    ) -> None:
        """AC#5: cockpit src must not import 'pick_dispatchable' from owlbear_kanban*."""
        violations = [
            (f, n, ln)
            for f, n, ln in _collect_forbidden_imports(cockpit_src_root)
            if n == "pick_dispatchable"
        ]
        assert violations == [], (
            f"D12 violation — 'pick_dispatchable' imported at: {violations}"
        )


# ---------------------------------------------------------------------------
# AC#1390: Route exclusion guardrail (HTTP surface)
# ---------------------------------------------------------------------------


class TestFromAC_RouteExclusionGuardrail:
    """Excluded lifecycle endpoints must not be exposed by Cockpit HTTP routes."""

    @pytest.fixture
    def client(self):
        """Return a FastAPI test client for route-surface assertions."""
        from fastapi.testclient import TestClient
        from owlbear_cockpit.main import app

        return TestClient(app)

    @pytest.mark.parametrize(
        "path",
        [
            "/api/tasks/create",
            "/api/tasks/123/claim",
            "/api/tasks/123/start",
            "/api/tasks/123/end-work",
        ],
    )
    def test_excluded_lifecycle_post_routes_not_available(self, client, path: str) -> None:
        """POST lifecycle routes must return 404/405 to enforce product boundary."""
        response = client.post(path)
        assert response.status_code in (404, 405), (
            f"Expected 404 or 405 for excluded route {path}, got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# AC#6: Root ruff config
# ---------------------------------------------------------------------------


class TestFromAC_RuffConfig:
    """Root pyproject.toml [tool.ruff] src list must include serve/cockpit/src.

    AC#6: ensures ruff lint coverage for the new package.
    """

    def test_ruff_src_includes_cockpit(self, project_root: Path) -> None:
        """AC#6: root pyproject.toml [tool.ruff] src contains 'serve/cockpit/src'."""
        content = (project_root / "pyproject.toml").read_text()
        assert '"serve/cockpit/src"' in content or "'serve/cockpit/src'" in content, (
            "root pyproject.toml [tool.ruff] src does not include 'serve/cockpit/src'. "
            "Builder must add it for lint coverage."
        )
