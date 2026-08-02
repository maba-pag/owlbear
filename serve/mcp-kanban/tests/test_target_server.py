"""Contract tests for the dormant target FastMCP assembly."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.target_authority import Outcome, PlanScopeKind, TargetAuthority, TaskPlanScope
from owlbear_kanban.target_runtime import (
    FinishTargetJobRequest,
    ReviewDisposition,
    StartTargetJobRequest,
    TargetJob,
    TargetRuntime,
)
from owlbear_mcp_kanban.target_server import TargetAppContext, TargetChangeBinding, assemble_target_server

TARGET_TOOLS = frozenset(
    {
        "arbitrate_attempt",
        "create_request",
        "finish_assembly",
        "finish_build",
        "finish_plan",
        "list_frontier",
        "list_semantic_updates",
        "list_work_item_activity",
        "list_work_items",
        "recover_interrupted_task",
        "resolve_request",
        "respond_to_review",
        "show_attempt",
        "show_completion_summary",
        "show_job",
        "show_receipt",
        "show_work_item",
        "start_job",
    }
)
REMOVED_TOOLS = frozenset(
    {
        "cancel_job",
        "finish_accept",
        "finish_audit",
        "prioritize_job",
        "reject_accept",
        "reject_audit",
        "release_job",
    }
)


def _binding(root: Path, change_id: str, outcome_id: str, job_id: int) -> TargetChangeBinding:
    authority = TargetAuthority(
        change_id=change_id,
        title=f"Change {change_id}",
        outcomes=(
            Outcome(
                outcome_id=outcome_id,
                title=f"Outcome {outcome_id}",
                promise=f"Deliver {outcome_id}",
                acceptance=("The result is observable",),
            ),
        ),
        task_plan_scopes=(
            TaskPlanScope(
                scope_id=f"PLAN-{job_id:03d}",
                kind=PlanScopeKind.OUTCOME,
                target_id=outcome_id,
            ),
        ),
    )
    runtime = TargetRuntime(authority, root / change_id)
    runtime.materialize(
        (
            TargetJob(
                job_id=job_id,
                kind="plan",
                change_id=change_id,
                authority_digest=runtime.authority_digest,
                work_item_id=outcome_id,
                plan_scope_id=f"PLAN-{job_id:03d}",
                created_at=f"2026-08-03T00:00:0{job_id}Z",
            ),
        )
    )
    return TargetChangeBinding(authority=authority, runtime=runtime)


def _context(tmp_path: Path) -> TargetAppContext:
    return TargetAppContext(
        changes={
            "change-a": _binding(tmp_path, "change-a", "OUT-001", 1),
            "change-b": _binding(tmp_path, "change-b", "OUT-002", 2),
        },
        process_is_alive=lambda _process_id: False,
        work_item_activity=lambda change_id, work_item_id: (
            {"change_id": change_id, "work_item_id": work_item_id, "kind": "planned"},
        ),
    )


def _tools(server) -> dict[str, object]:
    return dict(server._tool_manager._tools)  # noqa: SLF001


def test_target_registry_has_three_kind_lifecycle_without_removed_controls(tmp_path: Path) -> None:
    tools = _tools(assemble_target_server(_context(tmp_path)))

    assert tools.keys() == TARGET_TOOLS
    assert tools.keys().isdisjoint(REMOVED_TOOLS)
    for name, tool in tools.items():
        assert tool.annotations is not None
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.readOnlyHint is (name.startswith(("list_", "show_")))


@pytest.mark.asyncio
async def test_portfolio_query_pages_stably_across_loaded_changes(tmp_path: Path) -> None:
    tools = _tools(assemble_target_server(_context(tmp_path)))
    list_work_items = tools["list_work_items"].fn

    first = await list_work_items(limit=1)
    repeated = await list_work_items(limit=1)
    second = await list_work_items(cursor=first.next_cursor, limit=1)

    assert first == repeated
    assert [(item.change_id, item.work_item_id) for item in (*first.items, *second.items)] == [
        ("change-a", "OUT-001"),
        ("change-b", "OUT-002"),
    ]
    assert second.next_cursor is None
    activity = await tools["list_work_item_activity"].fn("OUT-001", "change-a")
    assert activity == [{"change_id": "change-a", "work_item_id": "OUT-001", "kind": "planned"}]

    with pytest.raises(ToolError) as exc_info:
        await list_work_items(change_id="change-a", cursor=first.next_cursor, limit=1)
    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_CURSOR_STALE"
    assert diagnostic["retry_safe"] is True


@pytest.mark.asyncio
async def test_target_diagnostic_preserves_authority_identity_and_retry_safety(tmp_path: Path) -> None:
    context = _context(tmp_path)
    tools = _tools(assemble_target_server(context))
    binding = context.changes["change-a"]
    request = StartTargetJobRequest(
        job_id=1,
        attempt_id="attempt-one",
        claim_id="claim-one",
        owner_id="builder-one",
        reviewer_id="reviewer-one",
        process_id="process-one",
        started_at="2026-08-03T00:01:00+00:00",
        lease_expires_at="2026-08-03T01:01:00+00:00",
    ).model_dump(mode="json")
    await tools["start_job"].fn("change-a", request)

    with pytest.raises(ToolError) as exc_info:
        await tools["start_job"].fn("change-a", request)

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic == {
        "code": "ERR_TARGET_RUNTIME_CONFLICT",
        "detail": "job is not ready",
        "current_authority_identity": binding.runtime.authority_digest,
        "retry_safe": True,
    }


@pytest.mark.asyncio
async def test_request_validation_and_kind_mismatch_use_target_diagnostics(tmp_path: Path) -> None:
    context = _context(tmp_path)
    tools = _tools(assemble_target_server(context))

    with pytest.raises(ToolError) as invalid_request:
        await tools["create_request"].fn(
            {
                "request_id": "INVALID_REQUEST",
                "change_id": "change-a",
                "authority_digest": context.changes["change-a"].runtime.authority_digest,
                "work_item_id": "OUT-001",
                "commitment_id": "COM-001",
                "created_at": "2026-08-03T00:01:00+00:00",
                "summary": "Need evidence",
            }
        )

    invalid_diagnostic = json.loads(str(invalid_request.value))
    assert invalid_diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert invalid_diagnostic["current_authority_identity"] == context.authority_identity
    assert invalid_diagnostic["retry_safe"] is False

    finish = FinishTargetJobRequest(
        job_id=1,
        attempt_id="attempt-one",
        claim_id="claim-one",
        owner_id="builder-one",
        reviewer_id="reviewer-one",
        review_id="review-one",
        receipt_id="receipt-one",
        candidate_commit="a" * 40,
        reviewed_at="2026-08-03T00:02:00+00:00",
        disposition=ReviewDisposition.ACCEPTABLE,
        claim="The build is correct",
        evidence=("focused proof",),
    ).model_dump(mode="json")
    with pytest.raises(ToolError) as wrong_kind:
        await tools["finish_build"].fn("change-a", finish)

    kind_diagnostic = json.loads(str(wrong_kind.value))
    assert kind_diagnostic["code"] == "ERR_TARGET_RUNTIME_REFERENCE"
    assert kind_diagnostic["current_authority_identity"] == context.changes["change-a"].runtime.authority_digest
    assert kind_diagnostic["retry_safe"] is False
