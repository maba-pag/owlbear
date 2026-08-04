"""Route-level contracts for the Delivery Cockpit application."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
import pytest

from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_cockpit.target_context import load_target_context
from owlbear_kanban.delivery_application_loader import (
    DeliveryRoleIdentityConfig,
    DeliveryRolePoliciesConfig,
    DeliveryStartupConfig,
)
from owlbear_kanban.delivery_runtime import DeliveryStage, DeliveryWorkerRole
from owlbear_kanban.portfolio_application import DeliveryOperatorClaim, DeliveryOperatorContext
from owlbear_kanban.work_items import WorkItemAttention, WorkItemProjection, WorkItemStage


def _projection(change_id: str, outcome_id: str, attention: WorkItemAttention) -> WorkItemProjection:
    return WorkItemProjection(
        work_item_id=outcome_id,
        change_id=change_id,
        scope="outcome",
        title=f"Outcome {outcome_id}",
        promise=f"Deliver {outcome_id}",
        stage=WorkItemStage.PLANNING,
        attention=attention,
        dependency_ready=True,
        next_action="Plan the outcome",
    )


class _DeliveryApplicationFake:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def list_work_items(self) -> tuple[WorkItemProjection, ...]:
        self.calls.append(("list", ()))
        return (
            _projection("change-a", "OUT-001", WorkItemAttention.USER),
            _projection("change-b", "OUT-002", WorkItemAttention.AGENT),
        )

    def show_operator_context(self, change_id: str, outcome_id: str) -> DeliveryOperatorContext:
        self.calls.append(("show", (change_id, outcome_id)))
        return DeliveryOperatorContext(
            change_id=change_id,
            outcome_id=outcome_id,
            stage=DeliveryStage.PLANNING,
            active_claim=DeliveryOperatorClaim(
                attempt_id="attempt-one",
                claim_id="claim-one",
                started_at="2026-08-04T00:02:00+00:00",
                worker_role=DeliveryWorkerRole.PLANNER,
            ),
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

    def show_integration_attention(self, *args: object) -> dict[str, object]:
        self.calls.append(("integration-attention", args))
        return {"code": "merge-conflict", "retry_condition": "Resolve conflict"}

    def integrate_ready_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("integration-retry", args))
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    role = DeliveryRoleIdentityConfig(
        worker_agent="worker",
        worker_model="model",
        reviewer_agent="reviewer",
        reviewer_model="model",
    )
    config = DeliveryStartupConfig(
        package_root=tmp_path / "packages",
        target_root=tmp_path / "workspace/.owlbear/target",
        repository_root=repository_root,
        worktree_root=tmp_path / "worktrees",
        execution_capacity=3,
        writer_capacity=1,
        integration_target="dev",
        role_policies=DeliveryRolePoliciesConfig(
            planner=role,
            builder=role,
            **{"assembly-reviewer": role},
        ),
    )
    config_path = tmp_path / "delivery.json"
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    monkeypatch.setenv("OWLBEAR_DELIVERY_CONFIG", str(config_path))
    workspace_root = tmp_path / "workspace"
    request_path = workspace_root / ".owlbear/target-cutover-request.json"
    request_path.parent.mkdir(parents=True)
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
    load.assert_called_once_with(config, authorized_target_root=config.target_root)


def test_list_and_detail_expose_current_bounded_delivery_state() -> None:
    client, application = _client()

    portfolio = client.get("/api/work-items")
    detail = client.get("/api/changes/change-a/outcomes/OUT-001")

    assert portfolio.status_code == 200
    assert portfolio.json()["attention_counts"] == {"user": 1, "agent": 1, "waiting": 0, "none": 0}
    first = portfolio.json()["items"][0]
    assert first["card"]["stage"] == "planning"
    assert first["links"]["self"] == "/api/changes/change-a/outcomes/OUT-001"
    assert detail.status_code == 200
    assert detail.json()["operator"]["active_claim"]["started_at"] == "2026-08-04T00:02:00+00:00"
    assert detail.json()["operator"]["block"] is None
    assert detail.json()["operator"]["requests"] == []
    assert "process_id" not in json.dumps((portfolio.json(), detail.json()))
    assert application.calls == [
        ("list", ()),
        ("show", ("change-a", "OUT-001")),
    ]


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
    move = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward",
        json={"target": "design", "reason": "Authority changed"},
    )

    assert (answer.status_code, clear.status_code, recovery.status_code, move.status_code) == (200, 200, 200, 200)
    assert rejected_recovery.status_code == 422
    assert [name for name, _args in application.calls] == ["answer", "clear", "recover", "move"]
    move_request = application.calls[-1][1][1]
    assert uuid.UUID(move_request.move_id).version == 4  # type: ignore[attr-defined]
    assert move_request.outcome_id == "OUT-001"  # type: ignore[attr-defined]


def test_integration_and_completed_history_routes_delegate_exactly_once() -> None:
    client, application = _client()

    responses = (
        client.get("/api/changes/change-a/integration-attention"),
        client.post("/api/changes/change-a/integration/retry"),
        client.get("/api/work-items/completed", params={"limit": 25}),
        client.get("/api/work-items/completed/search", params={"query": "delivery", "limit": 5}),
        client.get("/api/work-items/completed/change-a", params={"completion_id": "a" * 64}),
    )

    assert all(response.status_code == 200 for response in responses)
    assert application.calls == [
        ("integration-attention", ("change-a",)),
        ("integration-retry", ("change-a",)),
        ("completed-list", (None, 25)),
        ("completed-search", ("delivery", None, 5)),
        ("completed-show", ("change-a", "a" * 64)),
    ]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/work-items/OUT-001/updates"),
        ("get", "/api/work-items/OUT-001/completion"),
        ("post", "/api/work-items/OUT-001/requests"),
        ("post", "/api/work-items/OUT-001/recover"),
    ],
)
def test_schema_v1_routes_are_retired(method: str, path: str) -> None:
    client, application = _client()

    response = client.request(method, path, json={})

    assert response.status_code == 404
    assert application.calls == []


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
    assert "/api/changes/{change_id}/outcomes/{outcome_id}" in paths
