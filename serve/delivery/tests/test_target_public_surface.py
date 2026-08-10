"""Public contract for the target-only Delivery package root."""

from __future__ import annotations

import owlbear_delivery


def test_package_root_exports_target_runtime() -> None:
    required = {
        "ChangeWorkspaceManager",
        "CompletedChangeRecord",
        "CompletedHistoryCatalog",
        "DeliveryPlanCandidate",
        "DeliveryTransition",
        "PortfolioApplication",
        "TargetAuthorityRegistry",
        "TargetAuthority",
        "TargetRuntime",
        "WorkItemProjector",
    }
    assert set(owlbear_delivery.__all__) >= required
