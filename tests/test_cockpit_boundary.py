"""Protect Cockpit's package boundary and excluded HTTP surface."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Mined from #924: Cockpit source import boundary.
# Mined from #1390: Cockpit excludes Delivery lifecycle and finalization routes.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FORBIDDEN_NAMES: frozenset[str] = frozenset({"claim_task", "start_work", "end_work", "pick_dispatchable"})
# Both top-level and submodule import paths are checked per research finding.
_FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {"owlbear_delivery", "owlbear_delivery.engine", "owlbear_delivery.dispatch"}
)
_FINALIZATION_IMPORT_MODULES: frozenset[str] = frozenset(
    {
        "owlbear_delivery",
        "owlbear_delivery.delivery_runtime",
        "owlbear_delivery.portfolio_application",
    }
)
_FINALIZATION_IMPORT_NAMES: frozenset[str] = frozenset(
    {
        "DeliveryFinalization",
        "DeliveryFinalizationReceipt",
        "FinalizeDeliveryChange",
        "finalize_change",
    }
)


def _collect_forbidden_imports(
    src_root: Path,
    *,
    modules: frozenset[str] = _FORBIDDEN_MODULES,
    names: frozenset[str] = _FORBIDDEN_NAMES,
) -> list[tuple[str, str, int]]:
    """Return (relative_file, name, lineno) for every forbidden import in *src_root*.

    Scans all ``.py`` files recursively.  Detects both::

        from owlbear_delivery import pick_dispatchable
        from owlbear_delivery.engine import start_work
    """
    violations: list[tuple[str, str, int]] = []
    for py_file in sorted(src_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in modules:
                    for alias in node.names:
                        if alias.name in names:
                            violations.append(
                                (
                                    str(py_file.relative_to(src_root)),
                                    alias.name,
                                    node.lineno,
                                )
                            )
    return violations


# ---------------------------------------------------------------------------
# Cockpit import boundary
# ---------------------------------------------------------------------------


class TestCockpitImportBoundary:
    """Cockpit source must not import Delivery execution or finalization APIs."""

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
        """AC#5: cockpit src must not import 'claim_task' from owlbear_delivery*."""
        violations = [(f, n, ln) for f, n, ln in _collect_forbidden_imports(cockpit_src_root) if n == "claim_task"]
        assert violations == [], f"D12 violation — 'claim_task' imported at: {violations}"

    def test_no_forbidden_import_start_work(self, cockpit_src_root: Path) -> None:
        """AC#5: cockpit src must not import 'start_work' from owlbear_delivery*."""
        violations = [(f, n, ln) for f, n, ln in _collect_forbidden_imports(cockpit_src_root) if n == "start_work"]
        assert violations == [], f"D12 violation — 'start_work' imported at: {violations}"

    def test_no_forbidden_import_end_work(self, cockpit_src_root: Path) -> None:
        """AC#5: cockpit src must not import 'end_work' from owlbear_delivery*."""
        violations = [(f, n, ln) for f, n, ln in _collect_forbidden_imports(cockpit_src_root) if n == "end_work"]
        assert violations == [], f"D12 violation — 'end_work' imported at: {violations}"

    def test_no_forbidden_import_pick_dispatchable(self, cockpit_src_root: Path) -> None:
        """AC#5: cockpit src must not import 'pick_dispatchable' from owlbear_delivery*."""
        violations = [
            (f, n, ln) for f, n, ln in _collect_forbidden_imports(cockpit_src_root) if n == "pick_dispatchable"
        ]
        assert violations == [], f"D12 violation — 'pick_dispatchable' imported at: {violations}"

    def test_no_finalization_receipt_imports(self, cockpit_src_root: Path) -> None:
        """Cockpit presents finalization state but does not own finalization receipts or execution."""
        violations = _collect_forbidden_imports(
            cockpit_src_root,
            modules=_FINALIZATION_IMPORT_MODULES,
            names=_FINALIZATION_IMPORT_NAMES,
        )
        assert violations == [], f"Cockpit finalization boundary violation at: {violations}"


# ---------------------------------------------------------------------------
# Excluded HTTP surface
# ---------------------------------------------------------------------------


class TestCockpitRouteBoundary:
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

    def test_no_finalization_http_route_is_registered(self) -> None:
        """Finalization remains an agent-only Delivery operation, not a Cockpit HTTP route."""
        from owlbear_cockpit.main import app

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        assert not any("finaliz" in path.lower() for path in paths), paths
