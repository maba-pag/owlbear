"""Shared N03-A fixture: one Planning claim blocked on a request scoped to one acceptance criterion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from serve.delivery.tests.test_portfolio_application import _acquire_planning_claim, _portfolio

from owlbear_delivery import DeliveryStage
from owlbear_delivery.acceptance_criteria import acceptance_criteria
from owlbear_delivery.delivery_runtime import (
    BlockDelivery,
    DeliveryConfirmationScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
)

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery import PortfolioApplication
    from owlbear_delivery.delivery_runtime import DeliveryRuntime

SCOPED_REQUEST_ID = "confirm-criterion"


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
