"""Public contract for the target-only Delivery package root."""

from __future__ import annotations

import owlbear_delivery


def test_package_root_exports_target_runtime_without_retired_execution() -> None:
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
        "TargetCutoverResult",
        "WorkItemProjector",
        "authorize_target_mutation",
        "cut_over_target_runtime",
    }
    retired = {
        "CancelJobRequest",
        "DispatchRuntime",
        "FinishAcceptRequest",
        "NativeRuntime",
        "NativeWorkspace",
        "RejectAuditRequest",
        "ReleaseJobRequest",
        "SetJobPriorityRequest",
        "PortfolioDispatcher",
        "WriterGrant",
    }

    assert set(owlbear_delivery.__all__) >= required
    assert set(owlbear_delivery.__all__).isdisjoint(retired)
    assert not {name for name in retired if hasattr(owlbear_delivery, name)}
