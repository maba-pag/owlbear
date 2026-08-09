"""Route-level contracts for the Delivery Cockpit application."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient

from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_cockpit.target_context import load_target_context
from owlbear_delivery.delivery_application_loader import DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryWorkerRole,
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
    WorkItemActionKind,
    WorkItemActivity,
    WorkItemActivityState,
    WorkItemCardView,
    WorkItemChangeLifecycle,
    WorkItemDetailView,
    WorkItemIntegrationView,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemProgress,
    WorkItemProgressKind,
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
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.integration_attention: DeliveryIntegrationAttention | None = None
        self.integration_superseded = False
        self.integration_repair_active = False
        self.integration_started: threading.Event | None = None
        self.integration_release: threading.Event | None = None

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
                lifecycle=WorkItemChangeLifecycle.INTEGRATION,
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
                        item_key="integration",
                        work_item_id="change-b",
                        change_id="change-b",
                        scope=WorkItemScope.CHANGE_INTEGRATION,
                        title="Integration",
                        stage=None,
                        needs=WorkItemNeed.NONE,
                        next_actor=WorkItemNextActor.AGENT,
                        next_step="Integrate the reviewed Change",
                        activity=WorkItemActivity(state=WorkItemActivityState.IDLE),
                        progress=WorkItemProgress(
                            kind=WorkItemProgressKind.INTEGRATION,
                            label="Ready to integrate",
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
        queued = PortfolioWorkReference(
            change_id="change-b",
            item_key="integration",
            scope=PortfolioWorkScope.INTEGRATION,
        )
        return PortfolioOperatingView(
            unfinished_change_count=2,
            completed_change_count=0,
            queued_for_orchestration=(queued,),
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
                PortfolioGuidance(
                    kind=PortfolioGuidanceKind.START_ORCHESTRATION,
                    change_ids=("change-b",),
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
        if item_key == "integration":
            card = WorkItemCardView(
                item_key="integration",
                work_item_id=change_id,
                change_id=change_id,
                scope=WorkItemScope.CHANGE_INTEGRATION,
                title="Integration",
                stage=None,
                needs=WorkItemNeed.NONE,
                next_actor=WorkItemNextActor.AGENT,
                next_step="Run a reviewed Integration repair"
                if self.integration_attention
                else "Integrate the reviewed Change",
                activity=WorkItemActivity(
                    state=WorkItemActivityState.READY,
                    worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER if self.integration_attention else None,
                ),
                progress=WorkItemProgress(
                    kind=WorkItemProgressKind.INTEGRATION,
                    label="Merge conflict" if self.integration_attention else "Not attempted",
                ),
                action=WorkItemAction(
                    kind=WorkItemActionKind.START_ORCHESTRATION,
                    label="Run Orchestration",
                    command="/orchestrate",
                )
                if self.integration_attention
                else WorkItemAction(),
            )
            return WorkItemDetailView(
                snapshot_version="a" * 64,
                change_title=f"Change {change_id}",
                card=card,
                promise="Publish the reviewed Change.",
                integration=WorkItemIntegrationView(
                    code=self.integration_attention.code if self.integration_attention else None,
                    disposition=DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED
                    if self.integration_attention
                    else None,
                    headline="Integration target moved" if self.integration_superseded else "Merge conflict",
                    explanation="Retry against the current target."
                    if self.integration_superseded
                    else "One conflict requires repair.",
                    superseded=self.integration_superseded,
                    repair_active=self.integration_repair_active,
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

    def recover_expired_claims(self) -> dict[str, object]:
        self.calls.append(("recover-expired", ()))
        return {
            "recoveries": [
                {
                    "status": "recovered",
                    "change_id": "change-a",
                    "outcome_id": "OUT-001",
                    "attempt_id": "attempt-one",
                    "claim_id": "claim-one",
                }
            ],
            "repair_recoveries": [],
        }

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

    def show_integration_attention(self, *args: object) -> DeliveryIntegrationAttention | None:
        self.calls.append(("integration-attention", args))
        return self.integration_attention

    def integrate_ready_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("integration-retry", args))
        if self.integration_started is not None and self.integration_release is not None:
            self.integration_started.set()
            self.integration_release.wait(timeout=2)
        return {"change_id": args[0], "replayed": False}

    def list_completed_changes(self, *args: object) -> dict[str, object]:
        self.calls.append(("completed-list", args))
        return {"records": [], "next_cursor": None}

    def search_completed_changes(self, *args: object) -> dict[str, object]:
        self.calls.append(("completed-search", args))
        return {"records": [], "next_cursor": None}

    def show_completed_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("completed-show", args))
        return {"change_id": args[0], "completion_id": args[1]}


def _client() -> tuple[TestClient, _DeliveryApplicationFake]:
    application = _DeliveryApplicationFake()
    return TestClient(assemble_target_app(application)), application  # type: ignore[arg-type]


def test_startup_authorizes_shared_delivery_configuration(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(schema_version=1, integration_target="dev")
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    request_path = workspace_root / ".owlbear/target-cutover-request.json"
    request_path.write_text("{}\n", encoding="utf-8")
    request = SimpleNamespace(target_path=".owlbear/target")
    application = object()

    with (
        patch(
            "owlbear_cockpit.target_context.TargetCutoverRequest.model_validate_json",
            return_value=request,
        ),
        patch("owlbear_cockpit.target_context.authorize_target_mutation") as authorize,
        patch("owlbear_cockpit.target_context.load_delivery_application", return_value=application) as load,
    ):
        result = load_target_context(workspace_root, request_path)

    assert result is application
    authorize.assert_called_once_with(workspace_root, request)
    load.assert_called_once_with(
        config,
        workspace_root=workspace_root,
        authorized_target_root=workspace_root / ".owlbear/target",
    )


def test_startup_discovers_workspace_delivery_configuration(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(schema_version=1, integration_target="dev")
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    request_path = workspace_root / ".owlbear/target-cutover-request.json"
    request_path.write_text("{}\n", encoding="utf-8")
    request = SimpleNamespace(target_path=".owlbear/target")
    application = object()
    with (
        patch(
            "owlbear_cockpit.target_context.TargetCutoverRequest.model_validate_json",
            return_value=request,
        ),
        patch("owlbear_cockpit.target_context.authorize_target_mutation"),
        patch("owlbear_cockpit.target_context.load_delivery_application", return_value=application) as load,
    ):
        result = load_target_context(workspace_root, request_path)

    assert result is application
    load.assert_called_once_with(
        config,
        workspace_root=workspace_root,
        authorized_target_root=workspace_root / ".owlbear/target",
    )


def test_list_and_detail_expose_current_bounded_delivery_state() -> None:
    client, application = _client()

    portfolio = client.get("/api/work-items")
    detail = client.get("/api/changes/change-a/work-items/outcome:OUT-001")

    assert portfolio.status_code == 200
    assert portfolio.json()["totals"] == {
        "total": 3,
        "complete": 1,
        "needs": {"you": 1, "dependency": 0, "none": 2},
        "activity": {"idle": 1, "ready": 2, "working": 0, "repairing": 0},
    }
    assert portfolio.json()["operating"] == {
        "unfinished_change_count": 2,
        "completed_change_count": 0,
        "draft_design_change_ids": [],
        "design_required_change_ids": [],
        "claimed": [],
        "queued_for_orchestration": [{"change_id": "change-b", "item_key": "integration", "scope": "integration"}],
        "interventions": [{"change_id": "change-a", "item_key": "outcome:OUT-001", "scope": "outcome"}],
        "dependency_waits": [],
        "guidance": [
            {"kind": "intervene", "change_ids": ["change-a"], "work_count": 1},
            {"kind": "start-orchestration", "change_ids": ["change-b"], "work_count": 1},
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


def test_expired_claim_recovery_delegates_to_delivery_once() -> None:
    client, application = _client()

    response = client.post("/api/work-items/claims/recover-expired")

    assert response.status_code == 200
    assert response.json()["recoveries"][0]["claim_id"] == "claim-one"
    assert application.calls == [("recover-expired", ())]


def test_integration_and_completed_history_routes_delegate_exactly_once() -> None:
    client, application = _client()

    responses = (
        client.get("/api/changes/change-a/integration-attention"),
        client.post("/api/changes/change-a/integration/retry"),
        client.get("/api/work-items/completed", params={"limit": 25}),
        client.get("/api/work-items/completed/search", params={"query": "delivery", "limit": 5}),
        client.get("/api/work-items/completed/change-a", params={"completion_id": "a" * 64}),
    )

    assert [response.status_code for response in responses] == [200, 202, 200, 200, 200]
    assert responses[1].json() == {"status": "started"}
    assert application.calls == [
        ("integration-attention", ("change-a",)),
        ("integration-attention", ("change-a",)),
        ("show", ("change-a", "integration")),
        ("integration-retry", ("change-a",)),
        ("completed-list", (None, 25)),
        ("completed-search", ("delivery", None, 5)),
        ("completed-show", ("change-a", "a" * 64)),
    ]


def test_merge_conflict_retry_is_rejected_without_integration_mutation() -> None:
    client, application = _client()
    application.integration_attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="change-a",
        change_head="b" * 40,
        target_head="c" * 40,
        integration_target="dev",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed Integration repair, then retry.",
    )

    response = client.post("/api/changes/change-a/integration/retry")

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_INTEGRATION_ACTION_REQUIRED",
        "detail": "Admit a reviewed Integration repair, then retry.",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [
        ("integration-attention", ("change-a",)),
        ("show", ("change-a", "integration")),
    ]


def test_superseded_integration_attention_can_retry() -> None:
    client, application = _client()
    application.integration_attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="change-a",
        change_head="b" * 40,
        target_head="c" * 40,
        integration_target="dev",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed Integration repair, then retry.",
    )
    application.integration_superseded = True

    response = client.post("/api/changes/change-a/integration/retry")

    assert response.status_code == 202
    assert response.json() == {"status": "started"}
    assert [name for name, _args in application.calls] == [
        "integration-attention",
        "show",
        "integration-retry",
    ]


def test_active_integration_repair_rejects_retry_after_target_moves() -> None:
    client, application = _client()
    application.integration_attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="change-a",
        change_head="b" * 40,
        target_head="c" * 40,
        integration_target="dev",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed Integration repair, then retry.",
    )
    application.integration_superseded = True
    application.integration_repair_active = True

    response = client.post("/api/changes/change-a/integration/retry")

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_INTEGRATION_ACTION_REQUIRED",
        "detail": "A reviewed Integration repair is already in progress.",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert [name for name, _args in application.calls] == ["integration-attention", "show"]


def test_integration_retry_is_single_flight_per_change() -> None:
    application = _DeliveryApplicationFake()
    application.integration_started = threading.Event()
    application.integration_release = threading.Event()
    app = assemble_target_app(application)  # type: ignore[arg-type]

    with TestClient(app) as first_client, TestClient(app) as second_client, ThreadPoolExecutor() as executor:
        first = executor.submit(first_client.post, "/api/changes/change-a/integration/retry")
        assert application.integration_started.wait(timeout=1)

        duplicate = second_client.post("/api/changes/change-a/integration/retry")
        application.integration_release.set()
        started = first.result(timeout=2)

    assert started.status_code == 202
    assert started.json() == {"status": "started"}
    assert duplicate.status_code == 202
    assert duplicate.json() == {"status": "running"}
    assert [name for name, _args in application.calls].count("integration-retry") == 1


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
