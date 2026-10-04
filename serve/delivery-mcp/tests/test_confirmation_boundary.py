"""N03-A user-only confirmation through the assembled Delivery MCP server (D13, R14, I11)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mcp_types as types
import pytest
from mcp import Client
from serve.delivery.tests.confirmation_support import SCOPED_REQUEST_ID as _REQUEST
from serve.delivery.tests.confirmation_support import scoped_request_case as _scoped_case
from serve.delivery.tests.evidence_support import finalization_proof

from owlbear_delivery.consent_generation import ConsentGenerationStore
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceEvidenceError,
    DeliveryConfirmationError,
    DeliveryEvidenceGap,
    DeliveryRequest,
    DeliveryRequestResolution,
    DeliveryRuntime,
)
from owlbear_delivery.evidence import DeliveryContextRefusal
from owlbear_delivery.portfolio_application import DeliveryAnswer, DeliveryAnswerKind
from owlbear_delivery_mcp.target_server import assemble_target_server

_MODERN = "2026-07-28"


def _arguments(runtime: DeliveryRuntime, decision: str = "waive") -> dict[str, object]:
    return {
        "change_id": "change-a",
        "request_id": _REQUEST,
        "expected_frontier_digest": hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        "resolution": {"selected_option_id": decision, "provenance": "user-confirmed"},
    }


def _callback(action: str, decision: str | None, seen: list[types.ElicitRequestParams]) -> Any:
    async def answer(_context: object, params: types.ElicitRequestParams) -> types.ElicitResult:
        seen.append(params)
        content = {"decision": decision} if action == "accept" else None
        return types.ElicitResult(action=action, content=content)

    return answer


def _diagnostic(result: Any) -> dict[str, object]:
    _prefix, marker, content = result.content[0].text.partition("{")
    assert marker, result.content[0].text
    return json.loads(marker + content)


def _request(runtime: DeliveryRuntime) -> DeliveryRequest:
    return next(request for binding in runtime.bindings() for request in binding.requests)


def _generation(state_root: Path, kind: str = "waive") -> Any:
    latest = ConsentGenerationStore(state_root, "change-a").latest(kind, _REQUEST)
    return None if latest is None else latest[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_scoped_answer_records_exactly_one_user_confirmation_on_each_route(tmp_path: Path, mode: str) -> None:
    application, runtime, state_root = _scoped_case(tmp_path, kind="confirm-check")
    seen: list[types.ElicitRequestParams] = []
    server = assemble_target_server(application)

    async with Client(server, mode=mode, elicitation_callback=_callback("accept", "passed", seen)) as client:
        first = await client.call_tool("answer", _arguments(runtime, "passed"))
        replay = await client.call_tool("answer", _arguments(runtime, "passed"))

    assert not first.is_error, first.content
    assert not replay.is_error, replay.content
    assert len(seen) == 1
    (confirmation,) = runtime.confirmations()
    assert confirmation.channel == "mcp-elicitation"
    assert confirmation.decision == "passed"
    generation = _generation(state_root, "confirm-check")
    assert generation is not None
    assert generation.state == "answered"
    assert generation.disposition.outcome == "accepted"
    assert confirmation.generation_id == generation.generation_id
    resolution = _request(runtime).resolution
    assert resolution is not None
    assert resolution.confirmation_id == confirmation.confirmation_id
    assert first.structured_content["request"]["resolution"]["confirmation_id"] == confirmation.confirmation_id


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
@pytest.mark.parametrize("action", ["decline", "cancel"])
async def test_declined_or_cancelled_question_writes_only_its_generation(
    tmp_path: Path, mode: str, action: str
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    seen: list[types.ElicitRequestParams] = []

    async with Client(
        assemble_target_server(application), mode=mode, elicitation_callback=_callback(action, None, seen)
    ) as client:
        result = await client.call_tool("answer", _arguments(runtime))

    assert result.is_error
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_DELIVERY_CONFIRMATION"
    assert "declined" in str(diagnostic["detail"]) or "cancelled" in str(diagnostic["detail"])
    assert runtime.frontier_bytes() == before
    assert runtime.confirmations() == ()
    assert _request(runtime).resolution is None
    generation = _generation(state_root)
    assert generation is not None
    assert generation.disposition.outcome == ("declined" if action == "decline" else "cancelled")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_agent_cannot_fabricate_a_confirmation_without_a_question_channel(tmp_path: Path, mode: str) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()

    async with Client(assemble_target_server(application), mode=mode) as client:
        result = await client.call_tool("answer", _arguments(runtime))

    assert result.is_error
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_DELIVERY_CONFIRMATION"
    assert diagnostic["retry_safe"] is False
    assert runtime.frontier_bytes() == before
    assert runtime.confirmations() == ()
    assert _generation(state_root) is None


@pytest.mark.asyncio
async def test_caller_cannot_supply_the_injected_confirmation_parameter(tmp_path: Path) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    forged = _arguments(runtime) | {"confirmation": {"plan": None, "response": {"action": "accept"}}}

    async with Client(assemble_target_server(application)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        result = await client.call_tool("answer", forged)

    assert "confirmation" not in tools["answer"].input_schema.get("properties", {})
    assert result.is_error
    assert _diagnostic(result)["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert runtime.frontier_bytes() == before
    assert _generation(state_root) is None


@pytest.mark.asyncio
async def test_declined_waiver_decision_is_recorded_and_never_satisfies(tmp_path: Path) -> None:
    application, runtime, _state_root = _scoped_case(tmp_path)
    seen: list[types.ElicitRequestParams] = []

    async with Client(
        assemble_target_server(application), elicitation_callback=_callback("accept", "keep-required", seen)
    ) as client:
        result = await client.call_tool("answer", _arguments(runtime, "keep-required"))

    assert not result.is_error, result.content
    (confirmation,) = runtime.confirmations()
    assert confirmation.decision == "keep-required"
    assert not confirmation.affirmative


def test_core_answer_refuses_a_scoped_request_without_the_boundary(tmp_path: Path) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryConfirmationError) as raised:
        application.answer(
            DeliveryAnswer(
                change_id="change-a",
                kind=DeliveryAnswerKind.REQUEST,
                request_id=_REQUEST,
                resolution=DeliveryRequestResolution(selected_option_id="waive", provenance="user-confirmed"),
                expected_frontier_digest=hashlib.sha256(before).hexdigest(),
            )
        )

    assert raised.value.reason == "confirmation-required"
    assert runtime.frontier_bytes() == before
    assert _generation(state_root) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_a_declined_question_is_never_reopened_and_a_new_call_asks_a_fresh_one(tmp_path: Path, mode: str) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    store = ConsentGenerationStore(state_root, "change-a")
    declined: list[types.ElicitRequestParams] = []
    accepted: list[types.ElicitRequestParams] = []

    async with Client(
        assemble_target_server(application), mode=mode, elicitation_callback=_callback("decline", None, declined)
    ) as client:
        first = await client.call_tool("answer", _arguments(runtime))
    async with Client(
        assemble_target_server(application), mode=mode, elicitation_callback=_callback("accept", "waive", accepted)
    ) as client:
        second = await client.call_tool("answer", _arguments(runtime))

    assert first.is_error
    assert not second.is_error, second.content
    old, _content = store.read(1)
    new, _content = store.read(2)
    assert old.disposition.outcome == "declined"
    assert new.disposition.outcome == "accepted"
    assert old.generation_id != new.generation_id
    assert declined[0].message != accepted[0].message
    (confirmation,) = runtime.confirmations()
    assert confirmation.generation_id == new.generation_id


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
