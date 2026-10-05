"""Protect Cockpit's package boundary and excluded HTTP surface."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import get_args

import pytest

from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceCriterion
from owlbear_delivery.evidence import DeliveryCriterionStatus, DeliveryFinalizationRules
from owlbear_delivery.finalization_reports import FinalizationFailureCode, ReportFinalizationFailure
from owlbear_delivery.merge_offer import MergeBlockReason
from owlbear_delivery.portfolio_operating import DeliveryHealthReason
from owlbear_delivery.runtime_models import DeliveryEvidenceVerdict
from owlbear_delivery.work_items import (
    ChangePauseUnavailableReason,
    DeliveryProgress,
    DeliveryReadinessReason,
    WorkItemDetailView,
)

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


def test_merge_block_reason_typescript_parity(project_root: Path) -> None:
    """Every Delivery merge-block reason has a Cockpit type and presentation label."""
    expected = {item.value for item in MergeBlockReason}
    api = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    union = re.search(r"export type MergeBlockReason\s*=\s*(.*?);", api, re.DOTALL)
    assert union is not None
    assert set(re.findall(r'"([^"]+)"', union.group(1))) == expected

    presentation = (project_root / "serve/cockpit/web/src/components/workItemPresentation.ts").read_text()
    labels = re.search(r"MERGE_BLOCK_LABELS[^=]*=\s*\{(.*?)\};", presentation, re.DOTALL)
    assert labels is not None
    keys = set(re.findall(r'^\s*"?([a-z-]+)"?:', labels.group(1), re.MULTILINE))
    assert keys == expected


@pytest.mark.parametrize(
    ("type_name", "labels", "values"),
    [
        ("DeliveryCriterionStatus", "EVIDENCE_STATUS_LABELS", get_args(DeliveryCriterionStatus.__value__)),
        ("DeliveryEvidenceVerdict", "EVIDENCE_VERDICT_LABELS", get_args(DeliveryEvidenceVerdict.__value__)),
        (
            "DeliveryAcceptanceIdentitySource",
            "IDENTITY_SOURCE_LABELS",
            get_args(DeliveryAcceptanceCriterion.model_fields["identity_source"].annotation),
        ),
        ("DeliveryFinalizationRules", "FINALIZATION_RULES_LABELS", get_args(DeliveryFinalizationRules.__value__)),
    ],
)
def test_evidence_projection_typescript_parity(
    project_root: Path, type_name: str, labels: str, values: tuple[str, ...]
) -> None:
    """Every evidence status, verdict, identity source and finalization rule has a Cockpit type and label."""
    api = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    union = re.search(rf"export type {type_name}\s*=\s*(.*?);", api, re.DOTALL)
    assert union is not None
    assert set(re.findall(r'"([^"]+)"', union.group(1))) == set(values)
    presentation = (project_root / "serve/cockpit/web/src/components/workItemPresentation.ts").read_text()
    mapping = re.search(rf"{labels}[^=]*=\s*\{{(.*?)\}};", presentation, re.DOTALL)
    assert mapping is not None
    assert set(re.findall(r'^\s*"?([a-z-]+)"?:', mapping.group(1), re.MULTILINE)) == set(values)


def test_delivery_readiness_reason_typescript_parity(project_root: Path) -> None:
    """Every core recovery/readiness reason is represented by the frontend contract."""
    source = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    union = re.search(r"export type DeliveryReadinessReasonCode\s*=\s*(.*?);", source, re.DOTALL)
    assert union is not None
    assert set(re.findall(r'"([^"]+)"', union.group(1))) == set(get_args(DeliveryReadinessReason))


def test_delivery_progress_typescript_parity(project_root: Path) -> None:
    """Every engine progress key, including reserved ones, has a Cockpit mirror and label."""
    api = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    union = re.search(r"export type DeliveryProgress\s*=\s*(.*?);", api, re.DOTALL)
    assert union is not None
    assert set(re.findall(r'"([^"]+)"', union.group(1))) == set(get_args(DeliveryProgress))
    presentation = (project_root / "serve/cockpit/web/src/components/workItemPresentation.ts").read_text()
    labels = re.search(r"DELIVERY_PROGRESS_LABELS[^=]*=\s*\{(.*?)\};", presentation, re.DOTALL)
    assert labels is not None
    assert set(re.findall(r'^\s*"?([a-z-]+)"?:', labels.group(1), re.MULTILINE)) == set(get_args(DeliveryProgress))


def test_change_pause_unavailable_reason_typescript_parity(project_root: Path) -> None:
    """Every Delivery Pause refusal reason has a Cockpit mirror and copy."""
    api = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    union = re.search(r"export type ChangePauseUnavailableReason\s*=\s*(.*?);", api, re.DOTALL)
    assert union is not None
    assert set(re.findall(r'"([^"]+)"', union.group(1))) == set(get_args(ChangePauseUnavailableReason))
    presentation = (project_root / "serve/cockpit/web/src/components/workItemPresentation.ts").read_text()
    copy = re.search(r"PAUSE_UNAVAILABLE_COPY[^=]*=\s*\{(.*?)\};", presentation, re.DOTALL)
    assert copy is not None
    keys = set(re.findall(r'^\s*"?([a-z-]+)"?:', copy.group(1), re.MULTILINE))
    assert keys == set(get_args(ChangePauseUnavailableReason))


def test_delivery_health_reason_typescript_parity(project_root: Path) -> None:
    """Every core health reason, including remote-state-version-unsupported, is mirrored in Cockpit."""
    source = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    union = re.search(r"export type DeliveryHealthReason\s*=\s*(.*?);", source, re.DOTALL)
    assert union is not None
    assert set(re.findall(r'"([^"]+)"', union.group(1))) == {reason.value for reason in DeliveryHealthReason}


def test_finalization_failure_typescript_parity(project_root: Path) -> None:
    """Every core finalization diagnostic code and category is represented in Cockpit."""
    source = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    code_union = re.search(r"export type FinalizationFailureCode\s*=\s*(.*?);", source, re.DOTALL)
    category_union = re.search(r"export type FinalizationFailureCategory\s*=\s*(.*?);", source, re.DOTALL)
    assert code_union is not None
    assert category_union is not None
    assert set(re.findall(r'"([^"]+)"', code_union.group(1))) == {code.value for code in FinalizationFailureCode}
    assert set(re.findall(r'"([^"]+)"', category_union.group(1))) == set(
        get_args(ReportFinalizationFailure.model_fields["category"].annotation)
    )


def test_work_item_detail_view_typescript_parity(project_root: Path) -> None:
    """Every engine Work Item detail field, including the revision prompt, has a Cockpit mirror."""
    api = (project_root / "serve/cockpit/web/src/api/workItems.ts").read_text()
    interface = re.search(r"^export interface WorkItemDetailView \{\n(.*?)^\}", api, re.DOTALL | re.MULTILINE)
    assert interface is not None
    assert set(re.findall(r"^  (\w+)\??:", interface.group(1), re.MULTILINE)) == set(WorkItemDetailView.model_fields)


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
                    violations.extend(
                        (
                            str(py_file.relative_to(src_root)),
                            alias.name,
                            node.lineno,
                        )
                        for alias in node.names
                        if alias.name in names
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
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.main import app  # noqa: PLC0415

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
        from owlbear_cockpit.main import app  # noqa: PLC0415

        paths = {route.path for route in app.routes if hasattr(route, "path")}
        assert not any("finaliz" in path.lower() for path in paths), paths
