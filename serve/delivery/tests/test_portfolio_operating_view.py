from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from serve.delivery.tests.test_portfolio_application import _awaiting_acceptance_fixture

from owlbear_delivery.delivery_runtime import DeliveryChangeStage


def test_portfolio_read_view_excludes_completed_statuses_but_retains_diagnostics(tmp_path: Path) -> None:
    application, runtime, _provider, state, _exact_head, state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "draft": False,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "e" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    application.observe_acceptance("change-a")
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    application.create_design_session("design-change", b"intent\n", b"design\n")

    view = application.portfolio_read_view()

    assert view.groups == ()
    assert tuple(status.change_id for status in view.operating.statuses) == ("design-change",)
    assert view.operating.unfinished_change_count == 0
    assert view.operating.completed_change_count == 1

    (state_root / "changes/change-a/contract.json").write_bytes(b"not-json\n")
    view = application.portfolio_read_view()

    assert tuple(status.change_id for status in view.operating.statuses) == ("change-a", "design-change")
    unavailable = view.operating.statuses[0]
    assert unavailable.stage is DeliveryChangeStage.COMPLETED
    assert unavailable.actionable_runtime is False
    assert unavailable.diagnostic_code == "runtime_unavailable"
    assert view.operating.completed_change_count == 1
