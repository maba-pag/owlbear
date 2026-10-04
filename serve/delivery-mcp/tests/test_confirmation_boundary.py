"""N03-A user-only requests and typed evidence refusals through the assembled Delivery MCP server."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from serve.delivery.tests.confirmation_support import SCOPED_REQUEST_ID as _REQUEST
from serve.delivery.tests.confirmation_support import scoped_request_case as _scoped_case
from serve.delivery.tests.evidence_support import finalization_proof

from owlbear_delivery.delivery_runtime import DeliveryAcceptanceEvidenceError, DeliveryEvidenceGap
from owlbear_delivery.evidence import DeliveryContextRefusal
from owlbear_delivery_mcp.target_server import assemble_target_server


def _diagnostic(result: Any) -> dict[str, object]:
    _prefix, marker, content = result.content[0].text.partition("{")
    assert marker, result.content[0].text
    return json.loads(marker + content)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["waive", "confirm-check"])
async def test_mcp_answer_refuses_a_waiver_or_person_only_request(tmp_path: Path, kind: str) -> None:
    application, runtime, _state_root = _scoped_case(tmp_path, kind=kind)
    before = runtime.frontier_bytes()
    decision = "waive" if kind == "waive" else "passed"

    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool(
            "answer",
            {
                "change_id": "change-a",
                "request_id": _REQUEST,
                "expected_frontier_digest": hashlib.sha256(before).hexdigest(),
                "resolution": {"selected_option_id": decision, "provenance": "user-confirmed"},
            },
        )

    assert result.is_error
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_DELIVERY_CONFIRMATION"
    assert diagnostic["retry_safe"] is False
    assert "Cockpit" in str(diagnostic["detail"])
    assert runtime.frontier_bytes() == before


@pytest.mark.asyncio
async def test_registered_finalize_refusal_carries_the_exact_bounded_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _runtime, _state_root = _scoped_case(tmp_path)
    gaps = (
        DeliveryEvidenceGap(acceptance_id="AC-001", reason="uncovered"),
        DeliveryEvidenceGap(reason="review-basis-stale"),
    )

    def refuse(*_args: object) -> None:
        raise DeliveryAcceptanceEvidenceError(gaps)

    monkeypatch.setattr(application, "finalize_change", refuse)
    proof = finalization_proof(
        DeliveryContextRefusal(code="finalization-basis-unavailable"),
        change_id="change-a",
        exact_head="1" * 40,
        operation_id="finalize-change-a",
        observed_at=datetime(2026, 10, 4, tzinfo=UTC),
        procedure="uv run pytest",
        author_id="finalizer",
        reviewer_id="build-reviewer",
        evidence="Reviewed.",
    )

    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool(
            "finalize_change", {"change_id": "change-a", "finalization": proof.model_dump(mode="json")}
        )

    assert result.is_error
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_DELIVERY_ACCEPTANCE_EVIDENCE"
    assert diagnostic["retry_safe"] is False
    assert diagnostic["gaps"] == [gap.model_dump(mode="json") for gap in gaps]
