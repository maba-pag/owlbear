"""Contract tests for the strict Delivery MCP adapter."""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict

from owlbear_delivery.change_workspace import CoordinationConflictError
from owlbear_delivery.completed_history import (
    CompletedHistoryDiagnostic,
    CompletedHistoryDiagnosticCode,
    CompletedHistoryMissingError,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryPlanCandidate,
    DeliveryResultCandidate,
    DeliveryRuntimeReferenceError,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
)
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.runtime_transaction import TransactionPathError
from owlbear_delivery_mcp.target_server import (
    DELIVERY_OPERATION_ANNOTATIONS,
    DELIVERY_OPERATION_NAMES,
    TargetMCPAdapter,
)

CHANGE = "change-a"
DIGEST = "a" * 64
COMMIT = "b" * 40


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    operation: str


class _RecordingApplication:
    def __init__(self, failures: dict[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.failures = failures or {}

    def __getattr__(self, name: str) -> Any:
        def operation(*args: object, **kwargs: object) -> object:
            self.calls.append((name, args, kwargs))
            failure = self.failures.get(name)
            if failure is not None:
                raise failure
            if name in {"list_work_items", "list_integration_ready_changes"}:
                return (_Result(operation=name),)
            if name == "publish_delivery_plan":
                request = args[1]
                assert hasattr(request, "tasks")
                tasks = request.tasks
                assert isinstance(tasks, tuple)
                assert all(isinstance(task, DeliveryTaskDefinition) for task in tasks)
                return DeliveryPlanCandidate(candidate_id="plan", claim_id="claim", digest=DIGEST, tasks=tasks)
            if name == "publish_delivery_result":
                request = args[1]
                assert hasattr(request, "result")
                result = request.result
                assert isinstance(result, DeliveryTaskResult)
                return DeliveryResultCandidate(
                    candidate_id="result",
                    claim_id="claim",
                    digest=DIGEST,
                    result=result,
                )
            return _Result(operation=name)

        return operation


def _task() -> dict[str, object]:
    return {
        "task_id": "TASK-001",
        "outcome_id": "OUT-001",
        "plan_scope_id": "SCOPE-001",
        "title": "Implement result",
        "result": "Observable result",
        "commitment_ids": ["COM-001"],
        "dependency_ids": [],
        "required_outputs": ["result"],
        "maintained_surfaces": ["surface"],
        "constraints": [],
        "exclusions": [],
        "acceptance_observations": ["result observed"],
        "proof_boundaries": ["public adapter"],
    }


def _result() -> dict[str, object]:
    return {
        "result_id": "result-one",
        "change_id": CHANGE,
        "authority_digest": DIGEST,
        "task_id": "TASK-001",
        "task_digest": DIGEST,
        "completed_commit": COMMIT,
    }


def _repair() -> dict[str, object]:
    return {
        "attention_id": DIGEST,
        "change_id": CHANGE,
        "integration_target": "main",
        "prior_change_head": COMMIT,
        "prior_target_head": COMMIT,
        "reviewed_repair_commit": COMMIT,
        "owner_id": "owner",
        "review": {"review_id": "review", "reviewer_id": "reviewer", "candidate_commit": COMMIT},
    }


def _repair_authority_attention() -> dict[str, object]:
    return {
        "attention_id": DIGEST,
        "change_id": CHANGE,
        "reason": "Reviewed and target behavior cannot both be preserved.",
        "locators": ["product.txt"],
    }


def _requests() -> dict[str, dict[str, object]]:
    change = {"change_id": CHANGE}
    claim = {**change, "outcome_id": "OUT-001", "attempt_id": "attempt", "claim_id": "claim"}
    repair_claim = {**change, "attempt_id": "repair-attempt", "claim_id": "repair-claim"}
    return {
        "create_design_session": {**change, "intent_bytes": "intent", "design_bytes": "design"},
        "read_design_session": change,
        "revise_design_session": {
            **change,
            "expected_package_id": DIGEST,
            "intent_bytes": "intent",
            "design_bytes": "design",
        },
        "publish_design_checkpoint": change,
        "derive_delivery_contract": change,
        "validate_delivery_contract": change,
        "admit_delivery_change": {"request": {"change_id": CHANGE, "active_claim_ids": []}},
        "list_work_items": {},
        "show_work_item": {**change, "work_item_id": "OUT-001"},
        "acquire_frontier_work": {},
        "show_plan_context": claim,
        "show_build_context": claim,
        "show_integration_repair_context": repair_claim,
        "publish_delivery_plan": {
            **change,
            "request": {"outcome_id": "OUT-001", "claim_id": "claim", "tasks": [_task()]},
        },
        "publish_delivery_result": {
            **change,
            "request": {"outcome_id": "OUT-001", "claim_id": "claim", "result": _result()},
        },
        "transition_delivery": {
            **change,
            "request": {
                "action": "block",
                "outcome_id": "OUT-001",
                "claim_id": "claim",
                "block_id": "block",
                "reason": "Need user action",
                "unblock_condition": "Action is complete",
                "expected_evidence": ["completion evidence"],
                "locators": ["request"],
                "request": {
                    "request_id": "request",
                    "kind": "action",
                    "outcome_id": "OUT-001",
                    "summary": "Complete the action",
                },
            },
        },
        "recover_claim": claim,
        "recover_integration_repair_claim": repair_claim,
        "list_integration_ready_changes": {},
        "show_integration_attention": change,
        "integrate_ready_change": change,
        "admit_reviewed_integration_repair": {**repair_claim, "repair": _repair()},
        "publish_integration_repair_authority_attention": {
            **repair_claim,
            "attention": _repair_authority_attention(),
        },
        "list_completed_changes": {"limit": 25},
        "search_completed_changes": {"query": "delivery", "limit": 25},
        "show_completed_change": {**change, "completion_id": DIGEST},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("operation_name", DELIVERY_OPERATION_NAMES)
async def test_each_delivery_operation_validates_delegates_once_and_serializes(operation_name: str) -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

    result = await getattr(adapter, operation_name)(_requests()[operation_name])

    assert [call[0] for call in application.calls] == [operation_name]
    tuple_results = {"list_work_items", "list_integration_ready_changes"}
    publication_results = {
        "publish_delivery_plan": {"candidate_id": "plan", "claim_id": "claim"},
        "publish_delivery_result": {"candidate_id": "result", "claim_id": "claim"},
    }
    if operation_name in publication_results:
        assert result.candidate_id == publication_results[operation_name]["candidate_id"]
        assert result.claim_id == publication_results[operation_name]["claim_id"]
        assert result.output.output_id == result.candidate_id
    else:
        assert result == (
            [{"operation": operation_name}] if operation_name in tuple_results else {"operation": operation_name}
        )
    serialized = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
    assert "intent_bytes" not in json.dumps(serialized)
    assert "design_bytes" not in json.dumps(serialized)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation_name", DELIVERY_OPERATION_NAMES)
async def test_invalid_parameters_fail_before_application_delegation(operation_name: str) -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

    with pytest.raises(ToolError) as exc_info:
        await getattr(adapter, operation_name)({"unexpected": True})

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert diagnostic["retry_safe"] is False
    assert application.calls == []


def test_delivery_operation_names_annotations_and_prohibited_methods_are_exact() -> None:
    reads = {
        "read_design_session",
        "derive_delivery_contract",
        "validate_delivery_contract",
        "list_work_items",
        "show_work_item",
        "show_plan_context",
        "show_build_context",
        "show_integration_repair_context",
        "list_integration_ready_changes",
        "show_integration_attention",
        "list_completed_changes",
        "search_completed_changes",
        "show_completed_change",
    }
    prohibited = {
        "resolve_request",
        "create_request",
        "unblock_delivery",
        "list_semantic_updates",
        "show_completion_summary",
        "respond_to_review",
        "arbitrate_attempt",
        "recover_interrupted_task",
        "start_job",
        "finish_plan",
        "finish_build",
        "finish_assembly",
        "return_delivery",
    }

    assert tuple(DELIVERY_OPERATION_ANNOTATIONS) == DELIVERY_OPERATION_NAMES
    for name, tool_annotations in DELIVERY_OPERATION_ANNOTATIONS.items():
        assert tool_annotations.destructive_hint is False
        assert tool_annotations.read_only_hint is (name in reads)
        assert tool_annotations.idempotent_hint is (name != "acquire_frontier_work")
    assert all(not hasattr(TargetMCPAdapter, name) for name in prohibited)


@pytest.mark.asyncio
async def test_revise_design_session_rejects_non_digest_identity_before_delegation() -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]
    request = {**_requests()["revise_design_session"], "expected_package_id": "not-a-digest"}

    with pytest.raises(ToolError) as exc_info:
        await adapter.revise_design_session(request)

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert application.calls == []


@pytest.mark.asyncio
async def test_named_runtime_catalog_and_integration_failures_preserve_diagnostics() -> None:
    catalog_error = CompletedHistoryMissingError(
        CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.MISSING,
            detail="completed change is absent",
            change_id=CHANGE,
        )
    )
    cases = (
        (
            "transition_delivery",
            DeliveryRuntimeReferenceError("outcome is absent"),
            "ERR_DELIVERY_RUNTIME_REFERENCE",
            False,
        ),
        ("list_completed_changes", catalog_error, "completed-history-missing", False),
        (
            "admit_reviewed_integration_repair",
            CoordinationConflictError("repair authority is stale"),
            "ERR_TARGET_COORDINATION_CONFLICT",
            True,
        ),
        (
            "revise_design_session",
            DesignPackageConflictError("package identity is stale"),
            "ERR_DESIGN_PACKAGE_CONFLICT",
            True,
        ),
        ("integrate_ready_change", TransactionPathError(), "ERR_TRANSACTION_PATH_UNSAFE", False),
    )
    for operation_name, failure, code, retry_safe in cases:
        application = _RecordingApplication({operation_name: failure})
        adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

        with pytest.raises(ToolError) as exc_info:
            await getattr(adapter, operation_name)(_requests()[operation_name])

        diagnostic = json.loads(str(exc_info.value))
        assert diagnostic["code"] == code
        assert diagnostic["detail"] == (str(failure) or code)
        assert diagnostic["current_authority_identity"] == CHANGE
        assert diagnostic["retry_safe"] is retry_safe
        assert [call[0] for call in application.calls] == [operation_name]
