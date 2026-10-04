"""N03-A runtime scenarios: admissible evidence, finalization coverage and the stored-byte contract."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from serve.delivery.tests.evidence_support import finalization_proof
from serve.delivery.tests.test_delivery_runtime import (
    _activate,
    _active_second_task,
    _canonical,
    _runtime,
    _task_result,
)

from owlbear_delivery.acceptance_criteria import (
    DeliveryAcceptanceCriterion,
    DeliveryAcceptanceRef,
    acceptance_criteria,
    acceptance_version,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceEvidenceError,
    DeliveryCommandResult,
    DeliveryConfirmationScope,
    DeliveryFrontier,
    DeliveryMissingResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWaivedResult,
    FinalizeDeliveryChange,
    PublishDeliveryResult,
)
from owlbear_delivery.evidence import (
    FINALIZATION_SEMANTICS_MAX_BYTES,
    DeliveryContextRefusal,
    DeliveryFinalizationSemantics,
    build_finalization_semantics,
    evaluate_acceptance_evidence,
    finalization_basis_digest,
    measure_semantics,
    result_digest,
)

_AT = datetime(2026, 8, 11, 13, tzinfo=UTC)
_HEAD = "3" * 40
_COMPLETED = (DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED)


@pytest.fixture(autouse=True)
def _publication_base(monkeypatch: pytest.MonkeyPatch) -> None:
    derive = DeliveryRuntime.finalization_diff_base

    def diff_base(runtime: DeliveryRuntime, frontier: DeliveryFrontier | None = None) -> str | None:
        return derive(runtime, frontier) or "0" * 40

    monkeypatch.setattr(DeliveryRuntime, "finalization_diff_base", diff_base)


def _observation(commit: str, task_id: str, **changes: object) -> DeliveryObservationReceipt:
    values: dict[str, object] = {
        "change_id": "delivery-runtime",
        "task_or_finalization_id": task_id,
        "exact_commit": commit,
        "observation_kind": "pytest",
        "procedure": "uv run pytest focused.py",
        "result": DeliveryCommandResult(exit_status=0),
        "observer_or_runner_identity": "pytest",
        "observed_at": _AT,
    }
    return DeliveryObservationReceipt.create(DeliveryObservation(**(values | changes)))


def _semantics(runtime: DeliveryRuntime, head: str = _HEAD) -> DeliveryFinalizationSemantics:
    semantics = runtime.finalization_semantics(head)
    assert isinstance(semantics, DeliveryFinalizationSemantics)
    return semantics


def _review(
    semantics: DeliveryFinalizationSemantics | None,
    observations: tuple[DeliveryObservationReceipt, ...],
    *,
    head: str = _HEAD,
) -> DeliveryReviewReceipt:
    values: dict[str, object] = {
        "exact_commit": head,
        "author_id": "finalizer",
        "reviewer_id": "build-reviewer",
        "evidence": ("Reviewed the exact head.",),
        "reviewed_at": _AT,
    }
    if semantics is None:
        values["review_mode"] = "task"
    else:
        values |= {
            "review_mode": "finalization",
            "basis_digest": semantics.basis_digest,
            "observation_ids": tuple(item.observation_id for item in observations),
        }
    return DeliveryReviewReceipt.create(DeliveryReview(**values))


def _cover_all_task_results(runtime: DeliveryRuntime, state_root: Path) -> None:
    """Rewrite each completed result so its own exact-commit evidence covers its outcome's criteria."""
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    criteria = acceptance_criteria(runtime.contract)
    bindings = []
    for binding in frontier.bindings:
        refs = tuple(item.ref for item in criteria if item.outcome_id == binding.outcome_id)
        results = tuple(
            result.model_copy(
                update={
                    "observations": (_observation(result.completed_commit, result.task_id, covers=refs),),
                }
            )
            for result in binding.results
        )
        bindings.append(binding.model_copy(update={"results": results}))
    path = state_root / "changes/delivery-runtime/frontier.json"
    path.write_bytes(_canonical(frontier.model_copy(update={"bindings": tuple(bindings)})))


def _gaps(error: pytest.ExceptionInfo[DeliveryAcceptanceEvidenceError]) -> list[str]:
    return [gap.reason for gap in error.value.gaps]


# --- Builder results ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("variant", "reason"),
    [
        ("failed", "failed"),
        ("unknown", "unknown-acceptance"),
        ("stale", "stale-acceptance-version"),
        ("unresolved", "request-unresolved"),
    ],
)
def test_result_with_inadmissible_evidence_is_refused_without_a_write(
    tmp_path: Path, variant: str, reason: str
) -> None:
    runtime, _coordinator, _coordination, _initial, attempt_commit, _first, tasks = _active_second_task(tmp_path)
    (criterion,) = (item for item in acceptance_criteria(runtime.contract) if item.outcome_id == "OUT-001")
    changes: dict[str, object] = {
        "failed": {"result": DeliveryCommandResult(exit_status=1)},
        "unknown": {"covers": (DeliveryAcceptanceRef(acceptance_id="AC-999", acceptance_version="a" * 64),)},
        "stale": {
            "covers": (
                DeliveryAcceptanceRef(
                    acceptance_id=criterion.acceptance_id, acceptance_version=acceptance_version("x")
                ),
            )
        },
        "unresolved": {
            "procedure": "manual check",
            "result": {"kind": "manual-procedure", "assessment": "passed"},
            "provenance": "human-confirmed",
            "request_id": "REQ-absent",
            "covers": (criterion.ref,),
        },
    }[variant]
    result = _task_result("RESULT-002", "delivery-runtime", runtime.authority_digest, tasks[1], attempt_commit)
    result = result.model_copy(update={"observations": (_observation(attempt_commit, "TASK-002", **changes),)})
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryAcceptanceEvidenceError) as raised:
        runtime.publish_result(PublishDeliveryResult(outcome_id="OUT-001", claim_id="claim-002", result=result))

    assert reason in _gaps(raised)
    assert raised.value.code == "ERR_DELIVERY_ACCEPTANCE_EVIDENCE"
    assert runtime.frontier_bytes() == before


def test_result_with_a_pending_missing_record_promotes_and_shows_missing(tmp_path: Path) -> None:
    runtime, _coordinator, _coordination, _initial, attempt_commit, _first, tasks = _active_second_task(tmp_path)
    (criterion,) = (item for item in acceptance_criteria(runtime.contract) if item.outcome_id == "OUT-001")
    result = _task_result("RESULT-002", "delivery-runtime", runtime.authority_digest, tasks[1], attempt_commit)
    observations = (
        _observation(attempt_commit, "TASK-002"),
        _observation(
            attempt_commit,
            "TASK-002",
            procedure="browser check",
            result=DeliveryMissingResult(owner="assisted-check", reason="Needs a browser."),
            covers=(criterion.ref,),
        ),
    )
    result = result.model_copy(update={"observations": observations})

    candidate = runtime.publish_result(PublishDeliveryResult(outcome_id="OUT-001", claim_id="claim-002", result=result))

    assert candidate.result == result
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    promoted = frontier.model_copy(
        update={
            "bindings": tuple(
                binding.model_copy(update={"results": (*binding.results, result)})
                if binding.outcome_id == "OUT-001"
                else binding
                for binding in frontier.bindings
            )
        }
    )
    coverage = {
        item.acceptance_id: item.status for item in evaluate_acceptance_evidence(runtime.contract, promoted).criteria
    }
    assert coverage[criterion.acceptance_id] == "missing"


def test_task_result_may_not_carry_a_finalization_review(tmp_path: Path) -> None:
    runtime, _coordinator, _coordination, _initial, attempt_commit, _first, tasks = _active_second_task(tmp_path)
    result = _task_result("RESULT-002", "delivery-runtime", runtime.authority_digest, tasks[1], attempt_commit)
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="finalization",
            basis_digest="e" * 64,
            observation_ids=tuple(item.observation_id for item in result.observations),
            exact_commit=attempt_commit,
            author_id="builder",
            reviewer_id="build-reviewer",
            evidence=("Reviewed.",),
            reviewed_at=_AT,
        )
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(
            PublishDeliveryResult(
                outcome_id="OUT-001", claim_id="claim-002", result=result.model_copy(update={"review": review})
            )
        )

    assert runtime.frontier_bytes() == before


# --- Finalization ---------------------------------------------------------------------------------


def test_uncovered_criterion_refuses_finalization_even_when_every_task_check_passed(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    semantics = _semantics(runtime)
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryAcceptanceEvidenceError) as raised:
        runtime.finalize_change(
            FinalizeDeliveryChange(operation_id="finalize", exact_head=_HEAD, review=_review(semantics, ())),
            _AT,
        )

    assert _gaps(raised).count("uncovered") == 3
    assert runtime.frontier_bytes() == before
    assert runtime.finalization() is None


def test_carried_and_exact_head_evidence_together_finalize_and_replay(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    proof = finalization_proof(
        _semantics(runtime),
        change_id="delivery-runtime",
        exact_head=_HEAD,
        operation_id="finalize",
        observed_at=_AT,
        procedure="uv run pytest",
        author_id="finalizer",
        reviewer_id="build-reviewer",
        evidence="Reviewed.",
    )

    receipt = runtime.finalize_change(proof, _AT)

    assert receipt.schema_version == 3
    assert json.loads(runtime.frontier_bytes())["schema_version"] == 19
    assert runtime.finalize_change(proof, _AT) == receipt


def test_full_carried_coverage_finalizes_with_zero_new_observations(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    _cover_all_task_results(runtime, tmp_path)
    semantics = _semantics(runtime)
    assert {item.status for item in semantics.coverage} == {"covered"}

    receipt = runtime.finalize_change(
        FinalizeDeliveryChange(operation_id="finalize", exact_head=_HEAD, review=_review(semantics, ())),
        _AT,
    )

    assert receipt.observations == ()
    assert receipt.review.observation_ids == ()


def _answered_waiver_request(
    criterion: DeliveryAcceptanceCriterion,
    request_id: str,
    decision: str,
    scope: DeliveryAcceptanceRef | None = None,
) -> DeliveryRequest:
    """Return a waiver request of the criterion's outcome as the user answered it in Cockpit."""
    return DeliveryRequest(
        request_id=request_id,
        kind=DeliveryRequestKind.DECISION,
        outcome_id=criterion.outcome_id,
        summary="Waive the criterion",
        options=tuple(DeliveryRequestOption(option_id=item, label=item) for item in ("waive", "keep-required")),
        applies_to=DeliveryConfirmationScope(
            kind="waive", acceptance=(scope or criterion.ref,), procedure="manual check"
        ),
        resolution=DeliveryRequestResolution(selected_option_id=decision),
    )


def _store_requests(runtime: DeliveryRuntime, state_root: Path, *requests: DeliveryRequest) -> None:
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    bindings = tuple(
        binding.model_copy(
            update={"requests": tuple(item for item in requests if item.outcome_id == binding.outcome_id)}
        )
        for binding in frontier.bindings
    )
    (state_root / "changes/delivery-runtime/frontier.json").write_bytes(
        _canonical(frontier.model_copy(update={"schema_version": 19, "bindings": bindings}))
    )


def _finalize_with_waiver(
    runtime: DeliveryRuntime, waived: DeliveryAcceptanceCriterion, listed_request_id: str
) -> FinalizeDeliveryChange:
    """Build the Finalizer's proof from the shared semantics, as w-change-finalization Step 2 directs."""
    semantics = _semantics(runtime)
    listed = next(item for item in semantics.confirmations if item.request_id == listed_request_id)
    waiver = _observation(
        _HEAD,
        "finalize",
        procedure=listed.scope.procedure,
        result=DeliveryWaivedResult(reason="The user waived it."),
        provenance="human-confirmed",
        request_id=listed.request_id,
        covers=(waived.ref,),
    )
    rest = tuple(
        DeliveryAcceptanceRef(acceptance_id=item.acceptance_id, acceptance_version=item.acceptance_version)
        for item in semantics.coverage
        if item.status not in {"covered", "waived"} and item.acceptance_id != waived.acceptance_id
    )
    observations = (waiver, _observation(_HEAD, "finalize", covers=rest))
    return FinalizeDeliveryChange(
        operation_id="finalize",
        exact_head=_HEAD,
        observations=observations,
        review=_review(semantics, observations),
    )


def test_finalizer_waiver_cites_the_request_the_user_answered(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    criteria = acceptance_criteria(runtime.contract)
    waived = next(item for item in criteria if item.outcome_id == "OUT-001")
    kept = next(item for item in criteria if item.outcome_id != "OUT-001")
    _store_requests(
        runtime,
        tmp_path,
        _answered_waiver_request(waived, "waive-criterion", "waive"),
        _answered_waiver_request(kept, "keep-criterion", "keep-required"),
    )
    proof = _finalize_with_waiver(runtime, waived, "waive-criterion")

    receipt = runtime.finalize_change(proof, _AT)

    assert receipt.observations == proof.observations
    stored = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    coverage = {
        item.acceptance_id: item.status for item in evaluate_acceptance_evidence(runtime.contract, stored).criteria
    }
    assert coverage[waived.acceptance_id] == "waived"
    assert set(coverage.values()) == {"covered", "waived"}


@pytest.mark.parametrize("variant", ["criterion", "version", "keep-required"])
def test_finalizer_waiver_citing_a_request_for_another_criterion_or_version_is_refused(
    tmp_path: Path, variant: str
) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    waived = next(item for item in acceptance_criteria(runtime.contract) if item.outcome_id == "OUT-001")
    scope = {
        "criterion": DeliveryAcceptanceRef(acceptance_id="AC-099", acceptance_version=waived.acceptance_version),
        "version": DeliveryAcceptanceRef(
            acceptance_id=waived.acceptance_id, acceptance_version=acceptance_version("an earlier statement")
        ),
    }.get(variant)
    decision = "keep-required" if variant == "keep-required" else "waive"
    _store_requests(runtime, tmp_path, _answered_waiver_request(waived, "waive-criterion", decision, scope))
    proof = _finalize_with_waiver(runtime, waived, "waive-criterion")
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryAcceptanceEvidenceError) as raised:
        runtime.finalize_change(proof, _AT)

    assert "request-not-applicable" in _gaps(raised)
    assert runtime.frontier_bytes() == before
    assert runtime.finalization() is None


@pytest.mark.parametrize("variant", ["task-review", "stale-basis", "mismatch", "missing-record", "failed-record"])
def test_finalization_refuses_each_review_and_record_gap(tmp_path: Path, variant: str) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    _cover_all_task_results(runtime, tmp_path)
    semantics = _semantics(runtime)
    observation = _observation(_HEAD, "finalize")
    observations: tuple[DeliveryObservationReceipt, ...] = (observation,)
    review = _review(semantics, observations)
    if variant == "task-review":
        review = _review(None, observations)
    elif variant == "stale-basis":
        review = _review(_semantics(runtime, "4" * 40), observations)
    elif variant == "mismatch":
        review = _review(semantics, (_observation(_HEAD, "finalize", procedure="other"),))
    elif variant == "missing-record":
        observations = (_observation(_HEAD, "finalize", result=DeliveryMissingResult(owner="agent", reason="Later.")),)
        review = _review(semantics, observations)
    else:
        observations = (_observation(_HEAD, "finalize", result=DeliveryCommandResult(exit_status=2)),)
        review = _review(semantics, observations)
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryAcceptanceEvidenceError) as raised:
        runtime.finalize_change(
            FinalizeDeliveryChange(operation_id="finalize", exact_head=_HEAD, observations=observations, review=review),
            _AT,
        )

    expected = {
        "task-review": "review-basis-missing",
        "stale-basis": "review-basis-stale",
        "mismatch": "review-observations-mismatch",
        "missing-record": "missing",
        "failed-record": "failed",
    }[variant]
    assert expected in _gaps(raised)
    assert runtime.frontier_bytes() == before


def test_finalization_without_a_diff_base_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    _cover_all_task_results(runtime, tmp_path)
    review = _review(_semantics(runtime), ())
    monkeypatch.setattr(DeliveryRuntime, "finalization_diff_base", lambda _self, _frontier=None: None)

    with pytest.raises(DeliveryAcceptanceEvidenceError) as raised:
        runtime.finalize_change(FinalizeDeliveryChange(operation_id="finalize", exact_head=_HEAD, review=review), _AT)

    assert "finalization-basis-unavailable" in _gaps(raised)
    assert runtime.finalization_semantics(_HEAD).code == "finalization-basis-unavailable"


def test_a_real_oversized_finalization_context_is_refused_whole_and_finalization_writes_nothing(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    first = frontier.bindings[0]
    constraints = tuple(f"Constraint {index:03}: " + "keep the assembled behaviour " * 40 for index in range(240))
    large = DeliveryTaskDefinition.model_validate(first.tasks[0].model_dump() | {"constraints": constraints})
    result = _task_result("RESULT-001", "delivery-runtime", runtime.authority_digest, large, "1" * 40)
    oversized = frontier.model_copy(
        update={
            "bindings": (first.model_copy(update={"tasks": (large,), "results": (result,)}), *frontier.bindings[1:])
        }
    )
    (tmp_path / "changes/delivery-runtime/frontier.json").write_bytes(_canonical(oversized))
    _cover_all_task_results(runtime, tmp_path)
    stored = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    diff_base = runtime.finalization_diff_base()
    assert diff_base is not None
    complete = build_finalization_semantics(
        runtime.contract, stored, contract_digest=runtime.authority_digest, change_head=_HEAD, diff_base=diff_base
    )
    assert sum(len(item.encode()) for item in constraints) > FINALIZATION_SEMANTICS_MAX_BYTES

    refusal = runtime.finalization_semantics(_HEAD)

    assert refusal == DeliveryContextRefusal(
        code="finalization-context-oversized",
        measured_bytes=measure_semantics(complete),
        budget_bytes=FINALIZATION_SEMANTICS_MAX_BYTES,
    )
    basis = finalization_basis_digest(
        runtime.authority_digest,
        _HEAD,
        diff_base,
        tuple(result_digest(item) for binding in stored.bindings for item in binding.results),
        acceptance_criteria(runtime.contract),
    )
    assert basis == complete.basis_digest
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="finalization",
            basis_digest=basis,
            observation_ids=(),
            exact_commit=_HEAD,
            author_id="finalizer",
            reviewer_id="build-reviewer",
            evidence=("Reviewed the exact head.",),
            reviewed_at=_AT,
        )
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryAcceptanceEvidenceError) as raised:
        runtime.finalize_change(FinalizeDeliveryChange(operation_id="finalize", exact_head=_HEAD, review=review), _AT)

    assert _gaps(raised) == ["finalization-context-oversized"]
    assert runtime.frontier_bytes() == before
    assert runtime.finalization() is None


# --- Stored-byte contract ---------------------------------------------------------------------------


def test_v18_frontier_reads_keep_its_bytes_and_the_first_mutation_stores_19(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    payload = json.loads(path.read_bytes()) | {"schema_version": 18}
    stored = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(stored)
    reread = DeliveryRuntime(tmp_path, runtime.contract)

    assert reread.frontier_bytes() == stored
    reread.bindings()
    assert path.read_bytes() == stored

    _activate(reread, "OUT-001", "claim-001")

    assert json.loads(path.read_bytes())["schema_version"] == 19
    assert hashlib.sha256(path.read_bytes()).hexdigest() != hashlib.sha256(stored).hexdigest()


def test_typed_results_keep_identity_through_task_result_round_trip(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, stages=_COMPLETED)
    result = runtime.show_binding("OUT-001").results[0]

    assert DeliveryTaskResult.model_validate_json(result.model_dump_json(), strict=True) == result
