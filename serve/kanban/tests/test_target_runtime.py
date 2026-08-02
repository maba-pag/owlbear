from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from owlbear_kanban.target_authority import (
    Commitment,
    CommitmentClass,
    DesignReentryBriefing,
    Outcome,
    PlanScopeKind,
    TargetAuthority,
    TaskPlanScope,
)
from owlbear_kanban.target_runtime import (
    TARGET_MUTATION_ADAPTER,
    ArbitrateTargetAttemptRequest,
    FinishTargetJobRequest,
    RecoverInterruptedTaskRequest,
    RespondToReviewRequest,
    ReturnLevel,
    ReviewDisposition,
    StartTargetJobRequest,
    TargetAttemptState,
    TargetJob,
    TargetJobState,
    TargetRequest,
    TargetRuntime,
    TargetRuntimeConflictError,
    TargetRecoveryError,
    TargetRuntimeReferenceError,
    TargetTask,
)
from owlbear_kanban.work_items import WorkItemAttention, WorkItemProjector, WorkItemStage


def _job() -> dict[str, object]:
    return {
        "job_id": 1,
        "kind": "build",
        "change_id": "target-runtime",
        "authority_digest": "a" * 64,
        "work_item_id": "OUT-001",
        "plan_scope_id": "PLAN-001",
        "task_id": "TASK-001",
        "created_at": "2026-08-02T00:00:00Z",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", "accept"),
        ("kind", "audit"),
        ("priority", 1),
        ("state", "cancelled"),
    ],
)
def test_target_job_rejects_obsolete_kinds_and_controls(field: str, value: object) -> None:
    payload = _job()
    payload[field] = value

    with pytest.raises(PydanticValidationError):
        TargetJob.model_validate(payload)


def test_target_mutation_rejects_release_payload() -> None:
    with pytest.raises(PydanticValidationError):
        TARGET_MUTATION_ADAPTER.validate_python(
            {
                "action": "release",
                "job_id": 1,
                "attempt_id": "attempt-001",
                "claim_id": "claim-001",
                "released_at": "2026-08-02T00:01:00Z",
            }
        )


def _authority() -> TargetAuthority:
    return TargetAuthority(
        change_id="target-runtime",
        title="Target runtime",
        commitments=(
            Commitment(
                commitment_id="COM-001",
                commitment_class=CommitmentClass.PROTECTED_REQUEST,
                provenance="user request",
                statement="Keep requests scoped.",
            ),
        ),
        outcomes=(
            Outcome(
                outcome_id="OUT-001",
                title="Outcome A",
                promise="Deliver A",
                acceptance=("A is observable",),
                commitment_ids=("COM-001",),
            ),
            Outcome(
                outcome_id="OUT-002",
                title="Outcome B",
                promise="Deliver B",
                acceptance=("B is observable",),
                commitment_ids=("COM-001",),
            ),
            Outcome(
                outcome_id="OUT-003",
                title="Outcome C",
                promise="Deliver C",
                acceptance=("C is observable",),
                commitment_ids=("COM-001",),
                dependency_ids=("OUT-001",),
            ),
        ),
        task_plan_scopes=tuple(
            TaskPlanScope(
                scope_id=f"PLAN-00{index}",
                kind=PlanScopeKind.OUTCOME,
                target_id=f"OUT-00{index}",
            )
            for index in range(1, 4)
        ),
    )


def _runtime(tmp_path) -> TargetRuntime:
    return TargetRuntime(_authority(), tmp_path)


def _target_job(
    runtime: TargetRuntime,
    job_id: int,
    work_item_id: str,
    *,
    kind: str = "build",
    task_id: str | None = None,
) -> TargetJob:
    index = int(work_item_id[-1])
    return TargetJob.model_validate(
        {
            "job_id": job_id,
            "kind": kind,
            "change_id": "target-runtime",
            "authority_digest": runtime.authority_digest,
            "work_item_id": work_item_id,
            "plan_scope_id": f"PLAN-00{index}",
            "task_id": task_id,
            "created_at": f"2026-08-02T00:00:0{job_id}Z",
        }
    )


def _task(identity: str, work_item_id: str) -> TargetTask:
    return TargetTask(
        task_id=identity,
        work_item_id=work_item_id,
        plan_scope_id=f"PLAN-00{int(work_item_id[-1])}",
        title=f"Build {work_item_id}",
    )


def _start(
    runtime: TargetRuntime,
    job_id: int,
    attempt: str,
    reviewer: str,
    **changes: object,
):
    return runtime.start_job(
        StartTargetJobRequest.model_validate(
            {
                "job_id": job_id,
                "attempt_id": attempt,
                "claim_id": f"claim-{attempt}",
                "owner_id": "builder",
                "reviewer_id": reviewer,
                "process_id": "process-001",
                "started_at": "2026-08-02T00:10:00Z",
                "lease_expires_at": "2026-08-02T01:00:00Z",
                **changes,
            }
        )
    )


def _finish(
    runtime: TargetRuntime,
    job_id: int,
    attempt: str,
    reviewer: str,
    **changes: object,
):
    return runtime.finish_job(
        FinishTargetJobRequest.model_validate(
            {
                "job_id": job_id,
                "attempt_id": attempt,
                "claim_id": f"claim-{attempt}",
                "owner_id": "builder",
                "reviewer_id": reviewer,
                "candidate_commit": "b" * 40,
                "reviewed_at": "2026-08-02T00:20:00Z",
                "claim": "The task satisfies its accepted plan.",
                "evidence": ("focused proof passed",),
                **changes,
            }
        )
    )


def test_acceptable_build_publishes_receipt_and_marks_task_reviewed(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    job = _target_job(runtime, 1, "OUT-001", task_id="TASK-001")
    runtime.materialize((job,), (_task("TASK-001", "OUT-001"),))
    _start(runtime, 1, "attempt-001", "reviewer-one")

    result = _finish(
        runtime,
        1,
        "attempt-001",
        "reviewer-one",
        disposition=ReviewDisposition.ACCEPTABLE,
        review_id="review-001",
        receipt_id="build-receipt-001",
    )

    assert result.job.state == TargetJobState.COMPLETED
    assert result.receipt is not None
    assert result.receipt.candidate_commit == "b" * 40
    assert runtime.show_receipt("build-receipt-001") == result.receipt
    assert runtime.list_attempts("OUT-001") == (result.attempt,)
    assert runtime.list_receipts("OUT-001") == (result.receipt,)
    assert runtime.list_attempts("OUT-002") == ()
    assert runtime.list_receipts("OUT-002") == ()
    assert (tmp_path / "target-runtime/receipts/build-receipt-001.json").is_file()
    assert runtime.work_item_evidence().task_progress[0].reviewed_task_count == 1


def test_repair_retains_reviewer_and_restart_requires_a_fresh_reviewer(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    jobs = (
        _target_job(runtime, 1, "OUT-001", task_id="TASK-001"),
        _target_job(runtime, 2, "OUT-002", task_id="TASK-002"),
    )
    runtime.materialize(jobs, (_task("TASK-001", "OUT-001"), _task("TASK-002", "OUT-002")))
    _start(runtime, 1, "attempt-001", "reviewer-one")

    repair = _finish(
        runtime,
        1,
        "attempt-001",
        "reviewer-one",
        disposition=ReviewDisposition.REPAIR,
        review_id="review-repair",
    )
    completed = _finish(
        runtime,
        1,
        "attempt-001",
        "reviewer-one",
        disposition=ReviewDisposition.ACCEPTABLE,
        review_id="review-after-repair",
        receipt_id="build-receipt-001",
    )

    assert repair.attempt.state == TargetAttemptState.REPAIR
    assert completed.attempt.reviewer_id == "reviewer-one"
    assert len(completed.attempt.reviews) == 2

    _start(runtime, 2, "attempt-002", "reviewer-two")
    restarted = _finish(
        runtime,
        2,
        "attempt-002",
        "reviewer-two",
        disposition=ReviewDisposition.RESTART,
        review_id="review-restart",
    )
    assert restarted.job.state == TargetJobState.PENDING
    with pytest.raises(TargetRuntimeConflictError):
        _start(runtime, 2, "attempt-003", "reviewer-two")
    assert _start(runtime, 2, "attempt-004", "reviewer-three").attempt.reviewer_id == "reviewer-three"


def test_one_evidence_response_routes_to_one_final_arbiter(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    runtime.materialize(
        (_target_job(runtime, 1, "OUT-001", task_id="TASK-001"),),
        (_task("TASK-001", "OUT-001"),),
    )
    _start(runtime, 1, "attempt-001", "reviewer-one")
    _finish(
        runtime,
        1,
        "attempt-001",
        "reviewer-one",
        disposition=ReviewDisposition.REPAIR,
        review_id="review-disputed",
    )
    runtime.respond_to_review(
        RespondToReviewRequest(
            job_id=1,
            attempt_id="attempt-001",
            claim_id="claim-attempt-001",
            owner_id="builder",
            response_id="response-001",
            responded_at="2026-08-02T00:21:00Z",
            evidence=("owner counter-evidence",),
        )
    )

    result = runtime.arbitrate(
        ArbitrateTargetAttemptRequest(
            job_id=1,
            attempt_id="attempt-001",
            claim_id="claim-attempt-001",
            arbiter_id="arbiter-one",
            decision_id="decision-001",
            receipt_id="build-receipt-001",
            decided_at="2026-08-02T00:30:00Z",
            disposition="acceptable",
            rationale="The focused proof resolves the concrete disagreement.",
        )
    )

    assert result.receipt is not None
    assert result.receipt.arbiter_id == "arbiter-one"
    with pytest.raises(TargetRuntimeConflictError):
        _finish(
            runtime,
            1,
            "attempt-001",
            "reviewer-one",
            disposition=ReviewDisposition.REPAIR,
            review_id="review-forbidden",
        )


def test_request_blocks_only_target_and_semantic_dependents(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    runtime.materialize(tuple(_target_job(runtime, index, f"OUT-00{index}", kind="plan") for index in range(1, 4)))
    request = runtime.create_request(
        TargetRequest(
            request_id="request-001",
            change_id="target-runtime",
            authority_digest=runtime.authority_digest,
            work_item_id="OUT-001",
            commitment_id="COM-001",
            created_at="2026-08-02T00:00:00Z",
            summary="Protected meaning needs a user decision.",
        )
    )

    assert runtime.list_requests("OUT-001") == (request,)
    assert runtime.list_requests("OUT-002") == ()
    assert tuple(job.work_item_id for job in runtime.list_frontier()) == ("OUT-002",)


def test_expiry_and_known_dead_recovery_are_guarded(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    jobs = (
        _target_job(runtime, 1, "OUT-001", task_id="TASK-001"),
        _target_job(runtime, 2, "OUT-002", task_id="TASK-002"),
    )
    runtime.materialize(jobs, (_task("TASK-001", "OUT-001"), _task("TASK-002", "OUT-002")))
    _start(
        runtime,
        1,
        "attempt-expired",
        "reviewer-one",
        lease_expires_at="2026-08-02T00:11:00Z",
    )
    _start(runtime, 2, "attempt-live", "reviewer-two", process_id="process-live")

    assert runtime.recover_expired_claims("2026-08-02T00:12:00Z")[0].job_id == 1
    recovery = RecoverInterruptedTaskRequest(
        job_id=2,
        attempt_id="attempt-live",
        claim_id="claim-attempt-live",
        process_id="process-live",
        recovered_at="2026-08-02T00:13:00Z",
    )
    with pytest.raises(TargetRecoveryError):
        runtime.recover_interrupted_task(recovery, process_is_alive=lambda _process: True)
    assert (
        runtime.recover_interrupted_task(recovery, process_is_alive=lambda _process: False).state
        == TargetJobState.PENDING
    )


def _briefing(**changes: object) -> DesignReentryBriefing:
    return DesignReentryBriefing.model_validate(
        {
            "work_item_id": "OUT-001",
            "failed_claim": "Outcome A cannot be delivered under its accepted commitments.",
            "affected_commitment_ids": ("COM-001",),
            "evidence": ("focused proof contradicts the accepted acceptance",),
            "blocked_work_item_ids": ("OUT-003",),
            "resume_condition": "The user re-scopes COM-001.",
            **changes,
        }
    )


def test_plan_return_republishes_the_scope_and_drops_superseded_tasks(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    jobs = (
        _target_job(runtime, 1, "OUT-001", task_id="TASK-001"),
        _target_job(runtime, 2, "OUT-001", task_id="TASK-002"),
    )
    tasks = (
        _task("TASK-001", "OUT-001").model_copy(update={"reviewed": True, "build_receipt_id": "receipt-old"}),
        _task("TASK-002", "OUT-001"),
    )
    runtime.materialize(jobs, tasks)
    _start(runtime, 2, "attempt-001", "reviewer-one")

    result = _finish(
        runtime,
        2,
        "attempt-001",
        "reviewer-one",
        disposition=ReviewDisposition.TASK_PLAN,
        review_id="review-001",
    )

    assert result.job.state == TargetJobState.RETURNED
    assert result.job.return_level == ReturnLevel.TASK_PLAN
    frontier = runtime.list_frontier()
    assert tuple((job.job_id, job.kind) for job in frontier) == ((3, "plan"),)
    assert runtime.show_job(1).state == TargetJobState.RETURNED
    progress = runtime.work_item_evidence().task_progress
    assert tuple((item.scope_id, item.task_count, item.reviewed_task_count) for item in progress) == (
        ("PLAN-001", 1, 1),
    )


def test_design_return_blocks_the_semantic_slice_and_surfaces_the_briefing(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    runtime.materialize(tuple(_target_job(runtime, index, f"OUT-00{index}", kind="plan") for index in range(1, 4)))
    _start(runtime, 1, "attempt-001", "reviewer-one")

    _finish(
        runtime,
        1,
        "attempt-001",
        "reviewer-one",
        disposition=ReviewDisposition.DESIGN,
        review_id="review-001",
        design_reentry=_briefing(),
    )

    assert tuple(job.work_item_id for job in runtime.list_frontier()) == ("OUT-002",)
    projector = WorkItemProjector(_authority(), runtime.work_item_evidence())
    projection = projector.show("OUT-001").projection
    assert (projection.stage, projection.attention) == (WorkItemStage.DESIGN, WorkItemAttention.USER)
    assert projector.show("OUT-001").briefing == _briefing()


def test_design_return_requires_a_briefing_that_matches_its_authority(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    runtime.materialize((_target_job(runtime, 1, "OUT-001", kind="plan"),))
    _start(runtime, 1, "attempt-001", "reviewer-one")

    with pytest.raises(PydanticValidationError):
        _finish(
            runtime,
            1,
            "attempt-001",
            "reviewer-one",
            disposition=ReviewDisposition.DESIGN,
            review_id="review-001",
        )
    with pytest.raises(TargetRuntimeReferenceError):
        _finish(
            runtime,
            1,
            "attempt-001",
            "reviewer-one",
            disposition=ReviewDisposition.DESIGN,
            review_id="review-001",
            design_reentry=_briefing(work_item_id="OUT-002"),
        )
