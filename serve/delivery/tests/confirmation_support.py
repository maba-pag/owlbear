"""Shared N03 fixtures: a Planner blocked on a scoped request, and a Change with every evidence status."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from serve.delivery.tests import test_portfolio_application as portfolio_fixture
from serve.delivery.tests.test_portfolio_application import _acquire_planning_claim, _canonical, _portfolio

from owlbear_delivery import DeliveryStage
from owlbear_delivery.acceptance_criteria import acceptance_criteria
from owlbear_delivery.delivery_runtime import (
    BlockDelivery,
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
    DeliveryWaivedResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery import PortfolioApplication
    from owlbear_delivery.delivery_runtime import DeliveryRuntime
    from owlbear_delivery.target_contract import DeliveryContract

SCOPED_REQUEST_ID = "confirm-criterion"
WAIVER_REQUEST_ID = "waive-sign-off"
EVIDENCE_STATUSES = {
    "AC-001": "covered",
    "AC-002": "missing",
    "AC-003": "waived",
    "AC-004": "uncovered",
    "AC-005": "uncovered",
}


def scoped_request_case(tmp_path: Path, kind: str = "waive") -> tuple[PortfolioApplication, DeliveryRuntime, Path]:
    """Return a portfolio whose Planner blocked on one scoped ``waive`` or ``confirm-check`` request."""
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    criterion = acceptance_criteria(runtime.contract)[0]
    decisions = ("waive", "keep-required") if kind == "waive" else ("passed", "failed")
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id=claim.claim_id,
            block_id="confirm-block",
            reason="The criterion needs the user",
            unblock_condition="The user answers the request in Cockpit",
            expected_evidence=("user confirmation",),
            locators=("SCOPE-001",),
            request=DeliveryRequest(
                request_id=SCOPED_REQUEST_ID,
                kind=DeliveryRequestKind.DECISION,
                outcome_id="OUT-001",
                summary="Confirm the acceptance criterion",
                options=tuple(DeliveryRequestOption(option_id=item, label=item) for item in decisions),
                applies_to=DeliveryConfirmationScope(kind=kind, acceptance=(criterion.ref,), procedure="manual check"),
            ),
        ),
    )
    return application, runtime, state_root


def extra_waiver_ids(count: int) -> tuple[str, ...]:
    """Return the IDs of the additional sign-off criteria a multi-waiver case adds after ``AC-004``."""
    return tuple(f"AC-{100 + index:03d}" for index in range(count))


def _evidence_contract(extra_waivers: int) -> Callable[..., DeliveryContract]:
    def build(*args: object, **kwargs: object) -> DeliveryContract:
        contract = _ORIGINAL_CONTRACT(*args, **kwargs)
        acceptance = {
            "OUT-001": (
                "AC-001: The launch is observable.",
                "AC-002: The launch renders in a browser.",
                "AC-003: The launch has a manual sign-off.",
                "AC-004: The launch is documented.",
                *(
                    f"{item}: The launch has sign-off {index}."
                    for index, item in enumerate(extra_waiver_ids(extra_waivers))
                ),
            ),
            "OUT-002": ("AC-005: The report is retained.",),
        }
        return contract.model_copy(
            update={
                "outcomes": tuple(
                    outcome.model_copy(update={"acceptance": acceptance[outcome.outcome_id]})
                    for outcome in contract.outcomes
                )
            }
        )

    return build


_ORIGINAL_CONTRACT = portfolio_fixture._contract  # noqa: SLF001


def evidence_projection_case(
    tmp_path: Path, waived_count: int = 1
) -> tuple[PortfolioApplication, DeliveryRuntime, Path]:
    """Return a completed two-outcome Change whose criteria hold every non-legacy status (EVIDENCE_STATUSES).

    ``waived_count`` above one adds that many minus one further criteria waived by the same request.
    """
    with patch.object(portfolio_fixture, "_contract", _evidence_contract(waived_count - 1)):
        application, runtimes, _coordinator, state_root = _portfolio(
            tmp_path, {"change-a": DeliveryStage.COMPLETED}, include_independent=True
        )
    runtime = runtimes["change-a"]
    criteria = acceptance_criteria(runtime.contract)
    covered, missing, sign_off = (item.ref for item in criteria[:3])
    extra = set(extra_waiver_ids(waived_count - 1))
    waived = (sign_off, *(item.ref for item in criteria if item.acceptance_id in extra))
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    binding = frontier.bindings[0]
    (result,) = binding.results

    def record(procedure: str, **changes: object) -> DeliveryObservationReceipt:
        values: dict[str, object] = {
            "change_id": "change-a",
            "task_or_finalization_id": result.task_id,
            "exact_commit": result.completed_commit,
            "observation_kind": "pytest",
            "procedure": procedure,
            "result": DeliveryCommandResult(exit_status=0),
            "observer_or_runner_identity": "pytest",
            "observed_at": result.review.reviewed_at,
        }
        return DeliveryObservationReceipt.create(DeliveryObservation(**(values | changes)))

    request = DeliveryRequest(
        request_id=WAIVER_REQUEST_ID,
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Waive the manual sign-off",
        options=tuple(DeliveryRequestOption(option_id=item, label=item) for item in ("waive", "keep-required")),
        applies_to=DeliveryConfirmationScope(kind="waive", acceptance=waived, procedure="manual sign-off"),
        resolution=DeliveryRequestResolution(selected_option_id="waive", provenance="user-confirmed"),
    )
    observations = (
        *result.observations,
        record("uv run pytest tests/test_launch.py", covers=(covered,), locator="path:reports/launch.txt"),
        record(
            "browser check",
            result=DeliveryMissingResult(owner="assisted-check", reason="Needs a browser."),
            covers=(missing,),
        ),
        record(
            "manual sign-off",
            result=DeliveryWaivedResult(reason="The user waived the sign-off."),
            provenance="human-confirmed",
            request_id=WAIVER_REQUEST_ID,
            covers=waived,
        ),
    )
    binding = binding.model_copy(
        update={"results": (result.model_copy(update={"observations": observations}),), "requests": (request,)}
    )
    seeded = frontier.model_copy(update={"bindings": (binding, *frontier.bindings[1:])})
    (state_root / "changes/change-a/frontier.json").write_bytes(_canonical(seeded))
    return application, runtime, state_root
