"""Typed evidence records, the single coverage evaluator and scoped-request applicability (N03-A)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceRef, acceptance_criteria, acceptance_version
from owlbear_delivery.delivery_runtime import (
    DeliveryCommandResult,
    DeliveryConfirmationScope,
    DeliveryFinalization,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryLegacyObservationReceipt,
    DeliveryManualProcedureResult,
    DeliveryMissingResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWaivedResult,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.evidence import (
    FINALIZATION_SEMANTICS_MAX_BYTES,
    DeliveryContextRefusal,
    evaluate_acceptance_evidence,
    finalization_basis_digest,
    finalization_semantics_or_refusal,
    measure_semantics,
    observation_gaps,
    request_applies,
    resolve_request,
)
from owlbear_delivery.runtime_models import _receipt_digest
from owlbear_delivery.target_contract import DeliveryContract, DeliveryOutcome, DeliveryPlanScope

AT = datetime(2026, 10, 4, 12, tzinfo=UTC)
CHANGE = "evidence-change"
COMMIT = "1" * 40


def _contract(*statements: str) -> DeliveryContract:
    outcome = DeliveryOutcome(
        outcome_id="OUT-001",
        title="Evidence",
        promise="Prove it.",
        acceptance=tuple(f"AC-{index:03}: {statement}" for index, statement in enumerate(statements, start=1)),
        commitment_ids=(),
        dependency_ids=(),
    )
    return DeliveryContract(
        change_id=CHANGE,
        title="Evidence",
        commitments=(),
        outcomes=(outcome,),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            {"source_name": "intent.md", "sha256": "a" * 64},
            {"source_name": "design.md", "sha256": "b" * 64},
        ),
    )


def _ref(contract: DeliveryContract, index: int) -> DeliveryAcceptanceRef:
    return acceptance_criteria(contract)[index].ref


def _observation(**changes: object) -> DeliveryObservationReceipt:
    values: dict[str, object] = {
        "change_id": CHANGE,
        "task_or_finalization_id": "TASK-001",
        "exact_commit": COMMIT,
        "observation_kind": "pytest",
        "procedure": "uv run pytest tests/test_report.py",
        "result": DeliveryCommandResult(exit_status=0),
        "covers": (),
        "observer_or_runner_identity": "pytest",
        "observed_at": AT,
    }
    values.update(changes)
    return DeliveryObservationReceipt.create(DeliveryObservation(**values))


def _legacy() -> DeliveryLegacyObservationReceipt:
    values = {
        "schema_version": 1,
        "change_id": CHANGE,
        "task_or_finalization_id": "TASK-001",
        "step_id": None,
        "exact_commit": COMMIT,
        "observation_kind": "pytest",
        "command_or_procedure": "uv run pytest",
        "exit_status_or_artifact_locator": "exit:0",
        "observer_or_runner_identity": "pytest",
        "observed_at": AT,
    }
    candidate = DeliveryLegacyObservationReceipt.model_construct(observation_id="0" * 64, **values)
    return DeliveryLegacyObservationReceipt(observation_id=_receipt_digest(candidate, "observation_id"), **values)


def _review(observations: tuple[str, ...] | None = None, **changes: object) -> DeliveryReviewReceipt:
    values: dict[str, object] = {
        "exact_commit": COMMIT,
        "author_id": "builder",
        "reviewer_id": "build-reviewer",
        "evidence": ("Reviewed.",),
        "reviewed_at": AT,
        "review_mode": "task",
    }
    if observations is not None:
        values |= {"review_mode": "finalization", "observation_ids": observations, "basis_digest": "c" * 64}
    values.update(changes)
    return DeliveryReviewReceipt.create(DeliveryReview(**values))


def _result(*observations: DeliveryObservationReceipt | DeliveryLegacyObservationReceipt) -> DeliveryTaskResult:
    return DeliveryTaskResult(
        result_id="RESULT-001",
        change_id=CHANGE,
        authority_digest="a" * 64,
        task_id="TASK-001",
        task_digest="b" * 64,
        completed_commit=COMMIT,
        observations=observations,
        review=_review(),
    )


_TASK = DeliveryTaskDefinition(
    task_id="TASK-001",
    outcome_id="OUT-001",
    plan_scope_id="SCOPE-001",
    title="Evidence",
    result="Proved.",
    commitment_ids=(),
    dependency_ids=(),
    required_outputs=("report",),
    maintained_surfaces=("tests",),
    constraints=(),
    exclusions=(),
    acceptance_observations=("pytest",),
    proof_boundaries=("unit",),
)


def _binding(
    results: tuple[DeliveryTaskResult, ...] = (),
    requests: tuple[DeliveryRequest, ...] = (),
) -> OutcomeAuthorityBinding:
    return OutcomeAuthorityBinding(
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        tasks=(_TASK,) if results else (),
        results=results,
        requests=requests,
    )


def _frontier(
    results: tuple[DeliveryTaskResult, ...] = (),
    requests: tuple[DeliveryRequest, ...] = (),
) -> DeliveryFrontier:
    return DeliveryFrontier(bindings=(_binding(results, requests),))


def _scoped_request(  # noqa: PLR0913
    contract: DeliveryContract,
    *,
    kind: str,
    decision: str | None,
    procedure: str = "manual check",
    acceptance: tuple[DeliveryAcceptanceRef, ...] | None = None,
    outcome_id: str = "OUT-001",
) -> DeliveryRequest:
    """Return a waiver or person-only request, resolved with ``decision`` as the user answered it in Cockpit."""
    return DeliveryRequest(
        request_id=f"REQ-{kind}-{decision}",
        kind=DeliveryRequestKind.DECISION,
        outcome_id=outcome_id,
        summary="Confirm.",
        options=tuple(
            DeliveryRequestOption(option_id=option, label=option)
            for option in (("waive", "keep-required") if kind == "waive" else ("passed", "failed"))
        ),
        applies_to=DeliveryConfirmationScope(
            kind=kind,
            acceptance=acceptance or (_ref(contract, 0),),
            procedure=procedure,
        ),
        resolution=DeliveryRequestResolution(selected_option_id=decision) if decision is not None else None,
    )


# --- Typed results -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("result", "verdict"),
    [
        (DeliveryCommandResult(exit_status=0), "passed"),
        (DeliveryCommandResult(exit_status=1), "failed"),
        (
            DeliveryCommandResult(exit_status=1, expectation="expected-failure", expected_exit_status=1),
            "expected-negative",
        ),
        (DeliveryCommandResult(exit_status=2, expectation="expected-failure", expected_exit_status=1), "failed"),
        (DeliveryCommandResult(exit_status=0, expectation="expected-failure", expected_exit_status=1), "failed"),
        (DeliveryMissingResult(owner="assisted-check", reason="Needs a browser."), "missing"),
    ],
)
def test_command_and_missing_verdicts_are_derived_never_asserted(result: object, verdict: str) -> None:
    assert _observation(result=result).verdict == verdict


def test_expected_failure_requires_a_nonzero_expected_status_and_success_forbids_one() -> None:
    with pytest.raises(ValidationError, match="expected exit status"):
        DeliveryCommandResult(exit_status=1, expectation="expected-failure")
    with pytest.raises(ValidationError, match="expected exit status"):
        DeliveryCommandResult(exit_status=0, expected_exit_status=1)
    with pytest.raises(ValidationError, match="nonzero"):
        DeliveryCommandResult(exit_status=0, expectation="expected-failure", expected_exit_status=0)
    with pytest.raises(ValidationError):
        DeliveryCommandResult.model_validate_json('{"kind":"command","exit_status":"0"}', strict=True)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"provenance": "human-confirmed", "request_id": "REQ"}, "human-confirmed provenance applies"),
        (
            {"result": DeliveryManualProcedureResult(assessment="passed"), "provenance": "human-confirmed"},
            "resolved request",
        ),
        ({"request_id": "REQ"}, "resolved request"),
        ({"result": DeliveryWaivedResult(reason="Not needed.")}, "resolved request"),
        ({"locator": "https://example.com/report"}, "locator"),
        ({"locator": "path:../secret"}, "locator"),
        ({"locator": "path:has space"}, "locator"),
        ({"locator": "web:report"}, "locator"),
        ({"covers": (DeliveryAcceptanceRef(acceptance_id="AC-001", acceptance_version="a" * 64),) * 2}, "at most once"),
    ],
)
def test_observation_shape_rejects_untyped_or_unsafe_records(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _observation(**changes)


def test_artifacts_need_a_locator() -> None:
    with pytest.raises(ValidationError, match="locator"):
        _observation(result={"kind": "artifact", "assessment": "passed"})


def test_schema_one_receipts_round_trip_with_unchanged_identity_in_the_union() -> None:
    legacy = _legacy()
    result = _result(legacy, _observation())

    reparsed = DeliveryTaskResult.model_validate_json(result.model_dump_json(), strict=True)

    assert reparsed == result
    assert reparsed.observations[0].observation_id == legacy.observation_id
    assert isinstance(reparsed.observations[0], DeliveryLegacyObservationReceipt)


def test_schema_one_review_keeps_bytes_and_identity_and_rejects_n03_fields() -> None:
    values = {
        "schema_version": 1,
        "exact_commit": COMMIT,
        "author_id": "builder",
        "reviewer_id": "build-reviewer",
        "disposition": "pass",
        "evidence": ("Reviewed.",),
        "reviewed_at": AT,
    }
    candidate = DeliveryReviewReceipt.model_construct(review_id="0" * 64, **values)
    legacy = DeliveryReviewReceipt(review_id=_receipt_digest(candidate, "review_id"), **values)

    assert set(legacy.model_dump(mode="json")) == {*values, "review_id"}
    with pytest.raises(ValidationError, match="schema-1 Delivery review"):
        DeliveryReview(**(values | {"review_mode": "task"}))
    with pytest.raises(ValidationError, match="review mode"):
        DeliveryReview(**(values | {"schema_version": 2}))


def test_frontier_18_and_finalization_2_reject_n03_content() -> None:
    contract = _contract("One.")
    typed = _result(_observation(covers=(_ref(contract, 0),)))
    with pytest.raises(ValidationError, match="schema 18 cannot carry"):
        DeliveryFrontier(schema_version=18, bindings=(_binding((typed,)),))
    with pytest.raises(ValidationError, match="schema 18 cannot carry"):
        DeliveryFrontier(
            schema_version=18,
            bindings=(_binding(requests=(_scoped_request(contract, kind="waive", decision=None),)),),
        )
    with pytest.raises(ValidationError, match="schema-2 Delivery finalization"):
        DeliveryFinalizationReceipt.create(
            DeliveryFinalization(
                schema_version=2,
                operation_id="TASK-001",
                change_id=CHANGE,
                exact_head=COMMIT,
                authority_digest="a" * 64,
                result_digests=("b" * 64,),
                observations=(_observation(task_or_finalization_id="TASK-001"),),
                review=_review(),
                finalized_at=AT,
            )
        )


# --- Evaluator -----------------------------------------------------------------------------------


def test_last_record_wins_in_authority_order_then_finalization_request() -> None:
    contract = _contract("One.", "Two.", "Three.")
    one, two, three = (_ref(contract, index) for index in range(3))
    results = (
        _result(
            _observation(covers=(one, two)),
            _observation(covers=(two,), result=DeliveryMissingResult(owner="agent", reason="Not yet."), summary="2"),
        ),
    )
    frontier = _frontier(results)

    task_only = evaluate_acceptance_evidence(contract, frontier)
    finalized = evaluate_acceptance_evidence(
        contract, frontier, (_observation(task_or_finalization_id="FIN", covers=(two, three)),)
    )

    assert [item.status for item in task_only.criteria] == ["covered", "missing", "uncovered"]
    assert [item.reason for item in task_only.gaps] == ["missing", "uncovered"]
    assert [item.status for item in finalized.criteria] == ["covered", "covered", "covered"]
    assert finalized.gaps == ()


def test_legacy_evidence_makes_otherwise_uncovered_criteria_unknown_never_covered() -> None:
    contract = _contract("One.", "Two.")
    coverage = evaluate_acceptance_evidence(
        contract, _frontier((_result(_legacy(), _observation(covers=(_ref(contract, 0),))),))
    )

    assert [item.status for item in coverage.criteria] == ["covered", "unknown"]
    assert coverage.gaps[0].reason == "unknown-legacy-only"


def test_stale_versions_and_unknown_ids_never_cover_and_are_admissibility_gaps() -> None:
    contract = _contract("One.")
    stale = DeliveryAcceptanceRef(acceptance_id="AC-001", acceptance_version=acceptance_version("Old."))
    unknown = DeliveryAcceptanceRef(acceptance_id="AC-009", acceptance_version="a" * 64)
    observation = _observation(covers=(stale, unknown))

    gaps = observation_gaps(observation, _frontier(), acceptance_criteria(contract), "OUT-001")

    assert [gap.reason for gap in gaps] == ["stale-acceptance-version", "unknown-acceptance"]
    assert evaluate_acceptance_evidence(contract, _frontier((_result(observation),))).criteria[0].status == "uncovered"
    assert [gap.reason for gap in observation_gaps(_legacy(), _frontier(), (), None)] == ["legacy-observation"]


def _waiver(contract: DeliveryContract, request: DeliveryRequest, **changes: object) -> DeliveryObservationReceipt:
    values: dict[str, object] = {
        "procedure": "manual check",
        "result": DeliveryWaivedResult(reason="User waived."),
        "provenance": "human-confirmed",
        "request_id": request.request_id,
        "covers": (_ref(contract, 0),),
    }
    return _observation(**(values | changes))


def test_waiver_citing_the_user_resolved_request_satisfies_and_stays_shown_as_waived() -> None:
    contract = _contract("One.")
    request = _scoped_request(contract, kind="waive", decision="waive")
    waiver = _waiver(contract, request)
    frontier = _frontier((_result(waiver),), (request,))

    assert resolve_request(frontier, "OUT-001", request.request_id) == request
    assert request_applies(request, waiver, "OUT-001") is None
    assert evaluate_acceptance_evidence(contract, frontier).criteria[0].status == "waived"


@pytest.mark.parametrize(
    ("variant", "reason"),
    [
        ("unanswered", "request-unresolved"),
        ("outcome", "request-not-applicable"),
        ("criterion", "request-not-applicable"),
        ("version", "request-not-applicable"),
        ("procedure", "request-not-applicable"),
        ("keep-required", "request-not-applicable"),
        ("kind", "request-not-applicable"),
    ],
)
def test_waiver_citing_an_inapplicable_request_does_not_satisfy(variant: str, reason: str) -> None:
    contract = _contract("One.", "Two.")
    acceptance = {
        "criterion": (_ref(contract, 1),),
        "version": (DeliveryAcceptanceRef(acceptance_id="AC-001", acceptance_version=acceptance_version("Old.")),),
    }.get(variant)
    request = _scoped_request(
        contract,
        kind="confirm-check" if variant == "kind" else "waive",
        decision={"keep-required": "keep-required", "kind": "passed", "unanswered": None}.get(variant, "waive"),
        procedure="other check" if variant == "procedure" else "manual check",
        acceptance=acceptance,
        outcome_id="OUT-002" if variant == "outcome" else "OUT-001",
    )
    waiver = _waiver(contract, request)

    gaps = observation_gaps(waiver, _frontier((), (request,)), acceptance_criteria(contract), "OUT-001")

    assert [gap.reason for gap in gaps] == [reason]
    coverage = evaluate_acceptance_evidence(contract, _frontier((_result(waiver),), (request,)))
    assert coverage.criteria[0].status == "uncovered"


def test_person_only_check_requires_the_matching_answer_and_a_retained_request() -> None:
    contract = _contract("One.")
    passed = _scoped_request(contract, kind="confirm-check", decision="passed")
    failed = _scoped_request(contract, kind="confirm-check", decision="failed")

    def manual(request_id: str) -> DeliveryObservationReceipt:
        return _observation(
            procedure="manual check",
            result=DeliveryManualProcedureResult(assessment="passed"),
            provenance="human-confirmed",
            request_id=request_id,
            covers=(_ref(contract, 0),),
        )

    criteria = acceptance_criteria(contract)
    frontier = _frontier((), (passed, failed))
    assert observation_gaps(manual(passed.request_id), frontier, criteria, "OUT-001") == ()
    assert [gap.reason for gap in observation_gaps(manual(failed.request_id), frontier, criteria, "OUT-001")] == [
        "request-not-applicable"
    ]
    assert [gap.reason for gap in observation_gaps(manual("REQ-absent"), frontier, criteria, "OUT-001")] == [
        "request-unresolved"
    ]


def test_finalization_waiver_resolves_its_request_in_the_covered_outcome() -> None:
    contract = _contract("One.")
    request = _scoped_request(contract, kind="waive", decision="waive")
    waiver = _waiver(contract, request, task_or_finalization_id="FIN")
    frontier = _frontier((), (request,))

    assert observation_gaps(waiver, frontier, acceptance_criteria(contract), None) == ()
    assert evaluate_acceptance_evidence(contract, frontier, (waiver,)).criteria[0].status == "waived"


# --- Basis and budget ----------------------------------------------------------------------------


def test_basis_digest_binds_every_input() -> None:
    contract = _contract("One.")
    criteria = acceptance_criteria(contract)
    base = finalization_basis_digest("a" * 64, "1" * 40, "2" * 40, ("b" * 64,), criteria)

    assert base == finalization_basis_digest("a" * 64, "1" * 40, "2" * 40, ("b" * 64,), criteria)
    assert base != finalization_basis_digest("a" * 64, "3" * 40, "2" * 40, ("b" * 64,), criteria)
    assert base != finalization_basis_digest("a" * 64, "1" * 40, "4" * 40, ("b" * 64,), criteria)
    assert base != finalization_basis_digest("a" * 64, "1" * 40, "2" * 40, (), criteria)
    assert base != finalization_basis_digest("a" * 64, "1" * 40, "2" * 40, ("b" * 64,), ())


def test_semantics_are_complete_within_budget_and_refused_whole_above_it(monkeypatch: pytest.MonkeyPatch) -> None:
    contract = _contract("One.")
    frontier = _frontier((_result(_observation(covers=(_ref(contract, 0),))),))
    semantics = finalization_semantics_or_refusal(
        contract, frontier, contract_digest="a" * 64, change_head="1" * 40, diff_base="2" * 40
    )
    assert not isinstance(semantics, DeliveryContextRefusal)
    measured = measure_semantics(semantics)
    assert measured <= FINALIZATION_SEMANTICS_MAX_BYTES

    monkeypatch.setattr("owlbear_delivery.evidence.FINALIZATION_SEMANTICS_MAX_BYTES", measured)
    assert (
        finalization_semantics_or_refusal(
            contract, frontier, contract_digest="a" * 64, change_head="1" * 40, diff_base="2" * 40
        )
        == semantics
    )
    monkeypatch.setattr("owlbear_delivery.evidence.FINALIZATION_SEMANTICS_MAX_BYTES", measured - 1)
    refused = finalization_semantics_or_refusal(
        contract, frontier, contract_digest="a" * 64, change_head="1" * 40, diff_base="2" * 40
    )
    assert refused == DeliveryContextRefusal(
        code="finalization-context-oversized", measured_bytes=measured, budget_bytes=measured - 1
    )
    assert finalization_semantics_or_refusal(
        contract, frontier, contract_digest="a" * 64, change_head="1" * 40, diff_base=None
    ) == DeliveryContextRefusal(code="finalization-basis-unavailable")
