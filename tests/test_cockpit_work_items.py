"""Route-level contracts for the dormant target Cockpit application."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from owlbear_cockpit.routes.target_work import TargetCockpitBinding, TargetCockpitContext, assemble_target_app
from owlbear_cockpit.target_context import load_target_context
from owlbear_kanban.snapshot import LegacyDisposition, inventory_legacy_source
from owlbear_kanban.target_admission import (
    TargetAdmissionCandidate,
    TargetAdmissionRequest,
    TargetAuthorityRegistry,
    TargetChallengeEntry,
)
from owlbear_kanban.target_authority import (
    Commitment,
    CommitmentClass,
    CompletionSummary,
    DesignReentryBriefing,
    Outcome,
    PlanScopeKind,
    SemanticUpdate,
    TargetAuthority,
    TaskPlanScope,
)
from owlbear_kanban.target_cutover import (
    TargetAdapterRef,
    TargetCutoverClassification,
    TargetCutoverReadiness,
    TargetCutoverRequest,
    TargetCutoverSource,
    TargetCutoverSubjectKind,
    cut_over_target_runtime,
    target_authority_digest,
)
from owlbear_kanban.target_runtime import (
    StartTargetJobRequest,
    TargetJob,
    TargetRequest,
    TargetRuntime,
    TargetTask,
)


def _simple_authority(change_id: str, outcome_id: str, scope_id: str) -> TargetAuthority:
    return TargetAuthority(
        change_id=change_id,
        title=f"Change {change_id}",
        outcomes=(
            Outcome(
                outcome_id=outcome_id,
                title=f"Outcome {outcome_id}",
                promise=f"Deliver {outcome_id}",
                acceptance=(f"Observe {outcome_id}",),
            ),
        ),
        task_plan_scopes=(TaskPlanScope(scope_id=scope_id, kind=PlanScopeKind.OUTCOME, target_id=outcome_id),),
    )


def _binding(root: Path, change_id: str, outcome_id: str, *, design: bool) -> TargetCockpitBinding:
    commitment = Commitment(
        commitment_id="COM-001",
        commitment_class=CommitmentClass.PROTECTED_REQUEST,
        provenance="user request",
        statement=f"Preserve {outcome_id}",
    )
    briefing = DesignReentryBriefing(
        work_item_id=outcome_id,
        failed_claim="Current evidence does not prove isolation.",
        affected_commitment_ids=("COM-001",),
        evidence=("Two writers shared state.",),
        blocked_work_item_ids=(outcome_id,),
        resume_condition="Admit revised isolation authority.",
    )
    authority = TargetAuthority(
        change_id=change_id,
        title=f"Change {change_id}",
        commitments=(commitment,),
        outcomes=(
            Outcome(
                outcome_id=outcome_id,
                title=f"Outcome {outcome_id}",
                promise=f"Deliver {outcome_id}",
                acceptance=(f"Observe {outcome_id}",),
                commitment_ids=("COM-001",),
            ),
        ),
        task_plan_scopes=(TaskPlanScope(scope_id="PLAN-001", kind=PlanScopeKind.OUTCOME, target_id=outcome_id),),
        design_reentries=(briefing,) if design else (),
        semantic_updates=(
            SemanticUpdate(
                update_id="UPD-001",
                work_item_id=outcome_id,
                rationale="Keep the revised direction visible.",
                changed_commitment_ids=("COM-001",),
            ),
        ),
        completion_summaries=(
            CompletionSummary(
                work_item_id=outcome_id,
                satisfied_commitment_ids=("COM-001",),
                known_limits=("Assembly remains conditional.",),
            ),
        ),
    )
    runtime = TargetRuntime(authority, root / change_id)
    runtime.materialize(
        (
            TargetJob(
                job_id=1,
                kind="plan",
                change_id=change_id,
                authority_digest=runtime.authority_digest,
                work_item_id=outcome_id,
                plan_scope_id="PLAN-001",
                created_at="2026-08-04T00:00:00+00:00",
            ),
        ),
        (TargetTask(task_id="task-one", work_item_id=outcome_id, plan_scope_id="PLAN-001", title="Task"),),
    )
    if design:
        runtime.create_request(
            TargetRequest(
                request_id="request-one",
                change_id=change_id,
                authority_digest=runtime.authority_digest,
                work_item_id=outcome_id,
                commitment_id="COM-001",
                created_at="2026-08-04T00:01:00+00:00",
                summary="Clarify isolation",
            )
        )
    return TargetCockpitBinding(authority=authority, runtime=runtime)


def _client(tmp_path: Path, *, process_alive: bool = False) -> tuple[TestClient, TargetCockpitContext]:
    bindings = {
        "change-a": _binding(tmp_path, "change-a", "OUT-001", design=True),
        "change-b": _binding(tmp_path, "change-b", "OUT-002", design=False),
    }

    def requests(change_id: str, work_item_id: str) -> tuple[dict[str, object], ...]:
        if (change_id, work_item_id) != ("change-a", "OUT-001"):
            return ()
        return ({"request_id": "request-one", "summary": "Clarify isolation"},)

    context = TargetCockpitContext(
        changes=bindings,
        work_item_activity=lambda change_id, work_item_id: (
            {"kind": "returned", "change_id": change_id, "work_item_id": work_item_id},
        ),
        work_item_trace=lambda change_id, work_item_id: (
            {"kind": "receipt", "change_id": change_id, "work_item_id": work_item_id},
        ),
        work_item_requests=requests,
        process_is_alive=lambda _process_id: process_alive,
    )
    return TestClient(assemble_target_app(context)), context


def test_portfolio_returns_mixed_change_cards_and_attention_counts(tmp_path: Path) -> None:
    client, _context = _client(tmp_path)

    response = client.get("/api/work-items")

    assert response.status_code == 200
    payload = response.json()
    assert [(item["change_id"], item["work_item_id"]) for item in payload["items"]] == [
        ("change-a", "OUT-001"),
        ("change-b", "OUT-002"),
    ]
    assert payload["attention_counts"] == {"user": 1, "agent": 1, "waiting": 0, "none": 0}


def test_target_routes_are_mounted_on_live_app() -> None:
    from owlbear_cockpit.main import app  # noqa: PLC0415

    assert any(path.startswith("/api/work-items") for path in app.openapi()["paths"])


def test_live_context_requires_receipt_and_refreshes_post_cutover_admissions(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = workspace / ".owlbear/kanban"
    source.mkdir(parents=True)
    (source / "bootstrap.json").write_text('{"state":"current"}\n', encoding="utf-8")
    adapter = workspace / ".owlbear/adapters/delivery"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("bootstrap\n", encoding="utf-8")
    initial_authority = _simple_authority("change-a", "OUT-001", "PLAN-001")
    request = TargetCutoverRequest(
        sources=(
            TargetCutoverSource(
                source_path=".owlbear/kanban",
                snapshot_name="runtime",
                expected_source_digest=inventory_legacy_source(source, (), {}).source_digest,
            ),
        ),
        snapshot_path=".owlbear/legacy/target-cutover",
        target_path=".owlbear/target",
        receipt_path=".owlbear/target-cutover.json",
        adapter_refs=(TargetAdapterRef(relative_path=".owlbear/adapters/delivery", target="target"),),
        authorities=(initial_authority,),
        classifications=(
            TargetCutoverClassification(
                change_id="change-a",
                subject_kind=TargetCutoverSubjectKind.CHANGE,
                subject_id="change-a",
                disposition=LegacyDisposition.REINTRODUCE_NATIVE,
            ),
            TargetCutoverClassification(
                change_id="change-a",
                subject_kind=TargetCutoverSubjectKind.OUTCOME,
                subject_id="OUT-001",
                disposition=LegacyDisposition.REINTRODUCE_NATIVE,
            ),
        ),
        expected_authority_digest=target_authority_digest((initial_authority,)),
        actual_code_revision="a" * 64,
        expected_code_revision="a" * 64,
        readiness=TargetCutoverReadiness(),
        approval="ACTIVATE_TARGET_RUNTIME",
    )
    request_path = workspace / ".owlbear/target-cutover-request.json"
    request_path.write_text(request.model_dump_json(), encoding="utf-8")

    with pytest.raises(RuntimeError, match="valid target cutover request and receipt"):
        load_target_context(workspace, request_path)

    cut_over_target_runtime(workspace, request, smoke=lambda _root, _request: None)
    context = load_target_context(workspace, request_path)
    client = TestClient(assemble_target_app(context))
    assert [item["change_id"] for item in client.get("/api/work-items").json()["items"]] == ["change-a"]

    admitted_authority = _simple_authority("change-b", "OUT-002", "PLAN-002")
    candidate = TargetAdmissionCandidate(
        authority=admitted_authority,
        challenge=tuple(
            TargetChallengeEntry(subject_id=identity, disposition="pass", evidence=f"evidence for {identity}")
            for identity in ("change-b", "OUT-002", "PLAN-002")
        ),
        baseline=("uv run pytest -q",),
        known_limits=(),
        prepared_at="2026-08-05T00:00:00+00:00",
    )
    registry = TargetAuthorityRegistry(workspace / ".owlbear/target")
    assessment = registry.validate(candidate)
    registry.admit(
        TargetAdmissionRequest(
            candidate=candidate,
            approved_digest=assessment.authority_digest,
            approved_by="user",
            approved_at="2026-08-05T00:01:00+00:00",
        )
    )

    assert [item["change_id"] for item in client.get("/api/work-items").json()["items"]] == [
        "change-a",
        "change-b",
    ]


def test_detail_composes_semantics_progress_correction_and_trace_links(tmp_path: Path) -> None:
    client, context = _client(tmp_path)

    response = client.get("/api/work-items/OUT-001", params={"change_id": "change-a"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["commitments"][0]["commitment_id"] == "COM-001"
    assert payload["authority_identity"] == context.changes["change-a"].runtime.authority_digest
    assert payload["acceptance"] == ["Observe OUT-001"]
    assert payload["task_progress"] == [{"scope_id": "PLAN-001", "task_count": 1, "reviewed_task_count": 0}]
    assert payload["correction_history"][0]["kind"] == "returned"
    assert payload["semantic_updates"][0]["update_id"] == "UPD-001"
    assert payload["trace_links"]["activity"].endswith("change_id=change-a")
    assert "job_id" not in payload["card"]
    updates = client.get("/api/work-items/OUT-001/updates", params={"change_id": "change-a"})
    completion = client.get("/api/work-items/OUT-001/completion", params={"change_id": "change-a"})
    assert updates.json()["updates"][0]["update_id"] == "UPD-001"
    assert completion.json()["completion_summary"]["satisfied_commitment_ids"] == ["COM-001"]


def test_resume_design_returns_persisted_briefing_without_stage_mutation(tmp_path: Path) -> None:
    client, _context = _client(tmp_path)
    before = client.get("/api/work-items/OUT-001", params={"change_id": "change-a"}).json()["card"]["stage"]

    response = client.get("/api/work-items/OUT-001/resume-design", params={"change_id": "change-a"})
    after = client.get("/api/work-items/OUT-001", params={"change_id": "change-a"}).json()["card"]["stage"]

    assert response.status_code == 200
    assert response.json()["briefing"]["resume_condition"] == "Admit revised isolation authority."
    assert (before, response.json()["stage"], after) == ("design", "design", "design")


def test_scoped_request_reads_and_recovery_guard_cross_assembled_app(tmp_path: Path) -> None:
    client, context = _client(tmp_path, process_alive=True)
    binding = context.changes["change-b"]
    binding.runtime.start_job(
        StartTargetJobRequest(
            job_id=1,
            attempt_id="attempt-one",
            claim_id="claim-one",
            owner_id="builder-one",
            reviewer_id="reviewer-one",
            process_id="process-one",
            started_at="2026-08-04T00:02:00+00:00",
            lease_expires_at="2026-08-04T01:02:00+00:00",
        )
    )

    requests = client.get("/api/work-items/OUT-001/requests", params={"change_id": "change-a"})
    recovery = client.post(
        "/api/work-items/OUT-002/recover",
        params={"change_id": "change-b"},
        json={
            "job_id": 1,
            "attempt_id": "attempt-one",
            "claim_id": "claim-one",
            "process_id": "process-one",
            "recovered_at": "2026-08-04T00:03:00+00:00",
        },
    )

    assert requests.json()["requests"] == [{"request_id": "request-one", "summary": "Clarify isolation"}]
    assert recovery.status_code == 409
    assert recovery.json()["detail"]["code"] == "ERR_TARGET_RECOVERY_GUARD"
