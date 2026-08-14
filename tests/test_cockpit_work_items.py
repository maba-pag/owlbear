"""Route-level contracts for the Delivery Cockpit application."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uuid

import pytest
from fastapi.testclient import TestClient

from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_cockpit.target_context import load_target_context
from owlbear_delivery_github import GitHubCliPublicationProvider
from owlbear_delivery.delivery_application_loader import DeliveryApplicationLoadError
from owlbear_delivery.delivery_application_loader import DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceWaitingError,
    DeliveryChangeDispositionConflictError,
)
from owlbear_delivery.portfolio_operating import (
    PortfolioGuidance,
    PortfolioGuidanceKind,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
)
from owlbear_delivery.work_items import (
    ChangeGroupView,
    WorkItemAction,
    WorkItemActivity,
    WorkItemActivityState,
    WorkItemCardView,
    WorkItemChangeLifecycle,
    WorkItemDetailView,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemProgress,
    WorkItemProgressKind,
    WorkItemPublicationPhase,
    WorkItemPublicationView,
    WorkItemScope,
    WorkItemStage,
)


def _card(change_id: str, outcome_id: str, needs: WorkItemNeed) -> WorkItemCardView:
    next_actor = WorkItemNextActor.YOU if needs == WorkItemNeed.YOU else WorkItemNextActor.AGENT
    next_step = "Your attention is required" if needs == WorkItemNeed.YOU else "Ready for Orchestration"
    return WorkItemCardView(
        item_key=f"outcome:{outcome_id}",
        work_item_id=outcome_id,
        change_id=change_id,
        scope=WorkItemScope.OUTCOME,
        title=f"Outcome {outcome_id}",
        stage=WorkItemStage.PLANNING,
        needs=needs,
        next_actor=next_actor,
        next_step=next_step,
        activity=WorkItemActivity(state=WorkItemActivityState.READY),
        progress=WorkItemProgress(kind=WorkItemProgressKind.PLAN, label="Task plan not published"),
        action=WorkItemAction(),
    )


class _DeliveryApplicationFake:
    def __init__(self, failures: dict[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.failures = failures or {}

    def list_work_item_groups(self) -> tuple[ChangeGroupView, ...]:
        self.calls.append(("list", ()))
        return self._work_item_groups()

    def portfolio_read_view(self) -> SimpleNamespace:
        self.calls.append(("portfolio", ()))
        return SimpleNamespace(
            groups=self._work_item_groups(),
            operating=self._portfolio_operating_view(),
        )

    @staticmethod
    def _work_item_groups() -> tuple[ChangeGroupView, ...]:
        return (
            ChangeGroupView(
                change_id="change-a",
                title="Change A",
                snapshot_version="a" * 64,
                lifecycle=WorkItemChangeLifecycle.IN_DELIVERY,
                outcome_total=1,
                outcome_completed=0,
                items=(_card("change-a", "OUT-001", WorkItemNeed.YOU),),
            ),
            ChangeGroupView(
                change_id="change-b",
                title="Change B",
                snapshot_version="b" * 64,
                lifecycle=WorkItemChangeLifecycle.FINALIZATION,
                outcome_total=1,
                outcome_completed=1,
                items=(
                    _card("change-b", "OUT-002", WorkItemNeed.NONE).model_copy(
                        update={
                            "stage": WorkItemStage.COMPLETED,
                            "next_actor": WorkItemNextActor.NONE,
                            "next_step": "Complete — no action needed",
                        }
                    ),
                    WorkItemCardView(
                        item_key="publication",
                        work_item_id="change-b",
                        change_id="change-b",
                        scope=WorkItemScope.CHANGE_PUBLICATION,
                        title="Change publication",
                        stage=None,
                        needs=WorkItemNeed.NONE,
                        next_actor=WorkItemNextActor.AGENT,
                        next_step="Finalize the reviewed Change",
                        activity=WorkItemActivity(state=WorkItemActivityState.READY),
                        progress=WorkItemProgress(
                            kind=WorkItemProgressKind.PUBLICATION,
                            label="Ready for finalization",
                        ),
                        action=WorkItemAction(),
                    ),
                ),
            ),
        )

    def portfolio_operating_view(self) -> PortfolioOperatingView:
        self.calls.append(("operating", ()))
        return self._portfolio_operating_view()

    @staticmethod
    def _portfolio_operating_view() -> PortfolioOperatingView:
        return PortfolioOperatingView(
            unfinished_change_count=2,
            completed_change_count=0,
            interventions=(
                PortfolioWorkReference(
                    change_id="change-a",
                    item_key="outcome:OUT-001",
                    scope=PortfolioWorkScope.OUTCOME,
                ),
            ),
            guidance=(
                PortfolioGuidance(
                    kind=PortfolioGuidanceKind.INTERVENE,
                    change_ids=("change-a",),
                    work_count=1,
                ),
            ),
        )

    def read_design_session(self, change_id: str) -> SimpleNamespace:
        self.calls.append(("show-design", (change_id,)))
        return SimpleNamespace(
            change_id=change_id,
            package_id="d" * 64,
            intent_bytes=b"# Design intent\n",
            design_bytes=b"# Design architecture\n",
        )

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView:
        self.calls.append(("show", (change_id, item_key)))
        if item_key == "publication":
            card = WorkItemCardView(
                item_key="publication",
                work_item_id=change_id,
                change_id=change_id,
                scope=WorkItemScope.CHANGE_PUBLICATION,
                title="Change publication",
                stage=None,
                needs=WorkItemNeed.NONE,
                next_actor=WorkItemNextActor.AGENT,
                next_step="Finalize the reviewed Change",
                activity=WorkItemActivity(state=WorkItemActivityState.READY),
                progress=WorkItemProgress(
                    kind=WorkItemProgressKind.PUBLICATION,
                    label="Ready for finalization",
                ),
                action=WorkItemAction(),
            )
            return WorkItemDetailView(
                snapshot_version="a" * 64,
                change_title=f"Change {change_id}",
                card=card,
                promise="Publish the reviewed Change.",
                publication=WorkItemPublicationView(
                    phase=WorkItemPublicationPhase.READY_FOR_FINALIZATION,
                ),
            )
        return WorkItemDetailView(
            snapshot_version="a" * 64,
            change_title=f"Change {change_id}",
            card=_card(change_id, item_key.removeprefix("outcome:"), WorkItemNeed.NONE),
            promise="Deliver the Outcome.",
        )

    def resolve_request(self, *args: object) -> dict[str, object]:
        self.calls.append(("answer", args))
        return {"request_id": args[1], "resolved": True}

    def clear_block(self, *args: object) -> dict[str, object]:
        self.calls.append(("clear", args))
        return {"block_id": args[2], "resolved": True}

    def recover_claim(self, *args: object) -> dict[str, object]:
        self.calls.append(("recover", args))
        return {"status": "recovered", "attempt_id": args[2], "claim_id": args[3]}

    def administrative_move(self, *args: object) -> dict[str, object]:
        self.calls.append(("move", args))
        return {"move": args[1]}

    def preview_administrative_move(self, *args: object) -> dict[str, object]:
        self.calls.append(("move-preview", args))
        return {
            "outcome_id": args[1],
            "target": args[2],
            "snapshot_version": "a" * 64,
            "invalidated_outcome_ids": [args[1]],
        }

    def reconcile_change_checkpoint(self, *args: object) -> dict[str, object]:
        self.calls.append(("publication-reconcile", args))
        return {"change_id": args[0], "reconciled": True}

    def mark_current_change_ready(self, *args: object) -> dict[str, object]:
        self.calls.append(("publication-ready", args))
        return {"change_id": args[0], "draft": False}

    def observe_acceptance(self, *args: object) -> dict[str, object]:
        self.calls.append(("acceptance-observe", args))
        failure = self.failures.get("observe_acceptance")
        if failure is not None:
            raise failure
        return {"change_id": args[0], "completion_id": "f" * 64}

    def resolve_change_disposition(self, *args: object) -> dict[str, object]:
        self.calls.append(("attention-resolve", args))
        failure = self.failures.get("resolve_change_disposition")
        if failure is not None:
            raise failure
        return {"change_id": args[0], "disposition_id": args[1]}

    def defer_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("defer", args))
        return {"change_id": args[0], "state": "deferred", "reason": args[1]}

    def resume_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("resume", args))
        return {"change_id": args[0], "state": "building"}

    def abandon_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("abandon", args))
        return {"change_id": args[0], "state": "abandoned", "reason": args[1]}

    def list_completed_changes(self, *args: object) -> dict[str, object]:
        self.calls.append(("completed-list", args))
        return {"records": [], "next_cursor": None}

    def search_completed_changes(self, *args: object) -> dict[str, object]:
        self.calls.append(("completed-search", args))
        return {"records": [], "next_cursor": None}

    def show_completed_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("completed-show", args))
        return {"change_id": args[0], "completion_id": args[1]}


def _client(failures: dict[str, Exception] | None = None) -> tuple[TestClient, _DeliveryApplicationFake]:
    application = _DeliveryApplicationFake(failures)
    return TestClient(assemble_target_app(application)), application  # type: ignore[arg-type]


def test_startup_loads_shared_delivery_configuration(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="dev",
        github_repository="example/project",
    )
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    application = object()

    with patch(
        "owlbear_cockpit.target_context.load_delivery_application",
        return_value=application,
    ) as load:
        result = load_target_context(workspace_root)

    assert result is application
    load.assert_called_once()
    call = load.call_args
    assert call.args == (config,)
    assert call.kwargs["workspace_root"] == workspace_root
    assert isinstance(call.kwargs["publication_provider"], GitHubCliPublicationProvider)


def test_startup_discovers_workspace_delivery_configuration(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="dev",
        github_repository="example/project",
    )
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    application = object()
    with patch(
        "owlbear_cockpit.target_context.load_delivery_application",
        return_value=application,
    ) as load:
        result = load_target_context(workspace_root)

    assert result is application
    load.assert_called_once()
    call = load.call_args
    assert call.args == (config,)
    assert call.kwargs["workspace_root"] == workspace_root
    assert isinstance(call.kwargs["publication_provider"], GitHubCliPublicationProvider)


def test_startup_reports_delivery_migration_blocker(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="dev",
        github_repository="example/project",
    )
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    load_error = DeliveryApplicationLoadError("runtime_root", "legacy runtime state requires migration")

    with (
        patch("owlbear_cockpit.target_context.load_delivery_application", side_effect=load_error),
        pytest.raises(
            RuntimeError,
            match="Cockpit Delivery startup failed for runtime_root: legacy runtime state requires migration",
        ),
    ):
        load_target_context(workspace_root)


def test_list_and_detail_expose_current_bounded_delivery_state() -> None:
    client, application = _client()

    portfolio = client.get("/api/work-items")
    detail = client.get("/api/changes/change-a/work-items/outcome:OUT-001")

    assert portfolio.status_code == 200
    assert portfolio.json()["totals"] == {
        "total": 3,
        "complete": 1,
        "needs": {"you": 1, "dependency": 0, "none": 2},
        "activity": {"idle": 0, "ready": 3, "working": 0},
    }
    assert portfolio.json()["operating"] == {
        "unfinished_change_count": 2,
        "completed_change_count": 0,
        "draft_design_change_ids": [],
        "design_required_change_ids": [],
        "claimed": [],
        "queued_for_orchestration": [],
        "interventions": [{"change_id": "change-a", "item_key": "outcome:OUT-001", "scope": "outcome"}],
        "dependency_waits": [],
        "guidance": [
            {"kind": "intervene", "change_ids": ["change-a"], "work_count": 1},
        ],
    }
    first = portfolio.json()["groups"][0]["items"][0]
    assert first["stage"] == "planning"
    assert first["needs"] == "you"
    assert detail.status_code == 200
    assert detail.json()["item"]["acceptance"] == []
    assert detail.json()["item"]["block"] is None
    assert detail.json()["item"]["requests"] == []
    assert "process_id" not in json.dumps((portfolio.json(), detail.json()))
    assert application.calls == [
        ("portfolio", ()),
        ("show", ("change-a", "outcome:OUT-001")),
    ]


def test_design_work_detail_exposes_verified_authored_sources() -> None:
    client, application = _client()

    detail = client.get("/api/design-work/design-draft")

    assert detail.status_code == 200
    assert detail.json() == {
        "change_id": "design-draft",
        "package_id": "d" * 64,
        "intent_markdown": "# Design intent\n",
        "design_markdown": "# Design architecture\n",
    }
    assert application.calls == [("show-design", ("design-draft",))]


def test_controls_require_exact_confirmation_and_delegate_once() -> None:
    client, application = _client()

    answer = client.post(
        "/api/changes/change-a/requests/request-one/answer",
        json={"selected_option_id": "option-a"},
    )
    clear = client.post(
        "/api/changes/change-a/outcomes/OUT-001/blocks/block-one/clear",
        json={"operator_note": "Verified externally", "locators": ["request:REQ-001"]},
    )
    rejected_recovery = client.post(
        "/api/changes/change-a/outcomes/OUT-001/claims/recover",
        json={"confirmed_lost": False, "attempt_id": "attempt-one", "claim_id": "claim-one"},
    )
    recovery = client.post(
        "/api/changes/change-a/outcomes/OUT-001/claims/recover",
        json={"confirmed_lost": True, "attempt_id": "attempt-one", "claim_id": "claim-one"},
    )
    preview = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward/preview",
        json={"target": "design"},
    )
    move = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward",
        json={"target": "design", "reason": "Authority changed", "snapshot_version": "a" * 64},
    )

    assert (answer.status_code, clear.status_code, recovery.status_code, preview.status_code, move.status_code) == (
        200,
        200,
        200,
        200,
        200,
    )
    assert rejected_recovery.status_code == 422
    assert [name for name, _args in application.calls] == ["answer", "clear", "recover", "move-preview", "move"]
    move_request = application.calls[-1][1][1]
    assert uuid.UUID(move_request.move_id).version == 4  # type: ignore[attr-defined]
    assert move_request.outcome_id == "OUT-001"  # type: ignore[attr-defined]
    assert move_request.expected_version == "a" * 64  # type: ignore[attr-defined]


def test_bulk_expired_claim_recovery_route_is_removed_without_delivery_call() -> None:
    client, application = _client()

    response = client.post("/api/work-items/claims/recover-expired")

    assert response.status_code in {404, 405}
    assert application.calls == []


def test_publication_and_completed_history_routes_delegate_exactly_once() -> None:
    client, application = _client()

    responses = (
        client.post("/api/changes/change-a/publication/reconcile"),
        client.post("/api/changes/change-a/publication/ready"),
        client.post("/api/changes/change-a/acceptance/observe"),
        client.post(
            "/api/changes/change-a/attention/resolve",
            json={"expected_disposition_id": "a" * 64},
        ),
        client.post(
            "/api/changes/change-a/defer",
            json={"reason": "Wait for user review"},
        ),
        client.post("/api/changes/change-a/resume"),
        client.post(
            "/api/changes/change-a/abandon",
            json={"reason": "User stopped the Change"},
        ),
        client.get("/api/work-items/completed", params={"limit": 25}),
        client.get("/api/work-items/completed/search", params={"query": "delivery", "limit": 5}),
        client.get("/api/work-items/completed/change-a", params={"completion_id": "a" * 64}),
    )

    assert [response.status_code for response in responses] == [200, 200, 200, 200, 200, 200, 200, 200, 200, 200]
    assert application.calls == [
        ("publication-reconcile", ("change-a",)),
        ("publication-ready", ("change-a",)),
        ("acceptance-observe", ("change-a",)),
        ("attention-resolve", ("change-a", "a" * 64)),
        ("defer", ("change-a", "Wait for user review")),
        ("resume", ("change-a",)),
        ("abandon", ("change-a", "User stopped the Change")),
        ("completed-list", (None, 25)),
        ("completed-search", ("delivery", None, 5)),
        ("completed-show", ("change-a", "a" * 64)),
    ]


def test_open_acceptance_waiting_route_is_retry_safe() -> None:
    client, application = _client(
        {"observe_acceptance": DeliveryAcceptanceWaitingError("pull request is still open and unmerged")}
    )

    response = client.post("/api/changes/change-a/acceptance/observe")

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_ACCEPTANCE_WAITING",
        "detail": "pull request is still open and unmerged",
        "authority": "delivery",
        "retry_safe": True,
    }
    assert application.calls == [("acceptance-observe", ("change-a",))]


def test_stale_attention_resolution_route_is_not_retry_safe() -> None:
    client, application = _client(
        {"resolve_change_disposition": DeliveryChangeDispositionConflictError("attention identity is stale")}
    )

    response = client.post(
        "/api/changes/change-a/attention/resolve",
        json={"expected_disposition_id": "a" * 64},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_RUNTIME_CONFLICT",
        "detail": "attention identity is stale",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("attention-resolve", ("change-a", "a" * 64))]


def test_malformed_body_fails_before_application_mutation() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward",
        json={"move_id": "caller-owned", "target": "design", "reason": "Authority changed"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "ERR_DELIVERY_HTTP_VALIDATION",
        "detail": "Delivery request input is malformed",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == []


def test_target_routes_are_mounted_on_live_app() -> None:
    from owlbear_cockpit.main import app  # noqa: PLC0415

    paths = app.openapi()["paths"]
    assert "/api/work-items" in paths
    assert "/api/changes/{change_id}/work-items/{item_key}" in paths
