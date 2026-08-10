"""Public import inventory for the target delivery package."""

from __future__ import annotations


import owlbear_delivery


def test_target_and_snapshot_exports_remain_callable() -> None:
    required = {
        "TargetAuthorityRegistry",
        "TargetRuntime",
        "WorkItemProjector",
        "authorize_target_mutation",
        "cut_over_target_runtime",
        "create_legacy_snapshot",
    }

    assert required <= set(owlbear_delivery.__all__)
    assert all(callable(getattr(owlbear_delivery, name)) for name in required)
