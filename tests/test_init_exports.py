"""Public import inventory for the target delivery package."""

from __future__ import annotations


import owlbear_delivery


def test_target_and_snapshot_exports_exclude_retired_cutover_api() -> None:
    required = {
        "TargetAuthorityRegistry",
        "TargetRuntime",
        "WorkItemProjector",
        "create_legacy_snapshot",
    }
    retired = {"authorize_target_mutation", "cut_over_target_runtime"}

    assert required <= set(owlbear_delivery.__all__)
    assert all(callable(getattr(owlbear_delivery, name)) for name in required)
    assert retired.isdisjoint(owlbear_delivery.__all__)
    assert all(not hasattr(owlbear_delivery, name) for name in retired)
