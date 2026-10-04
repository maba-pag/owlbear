"""N03-A single-use consent and the SDK request-state boundary through the assembled server (D13, I11, P16)."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import mcp_types as types
import pytest
from mcp import Client
from mcp.server import request_state as request_state_module
from mcp.shared.exceptions import MCPError
from mcp_types import INVALID_PARAMS
from serve.delivery.tests.confirmation_support import SCOPED_REQUEST_ID as _REQUEST
from serve.delivery.tests.confirmation_support import scoped_request_case as _scoped_case

from owlbear_delivery.application_models import DeliveryChangeIntent, DeliveryChangeIntentKind
from owlbear_delivery.consent_generation import ConsentGenerationStore
from owlbear_delivery.delivery_runtime import (
    DeliveryConfirmationScope,
    DeliveryFrontier,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRuntime,
    DeliveryUserConfirmation,
)
from owlbear_delivery.runtime_transaction import TransactionConflictError
from owlbear_delivery_mcp.target_server import assemble_target_server

_MODERN = "2026-07-28"
_GENERATIONS = Path("changes/change-a/consent-generations")
_AFFIRMATIVE = {"waive": "waive", "confirm-check": "passed"}


def _arguments(runtime: DeliveryRuntime, decision: str = "waive") -> dict[str, object]:
    return {
        "change_id": "change-a",
        "request_id": _REQUEST,
        "expected_frontier_digest": hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        "resolution": {"selected_option_id": decision, "provenance": "user-confirmed"},
    }


def _never_asked(seen: list[object]) -> Any:
    async def record(_context: object, params: types.ElicitRequestParams) -> types.ElicitResult:
        seen.append(params)
        return types.ElicitResult(action="cancel")

    return record


def _accepting(decision: str, seen: list[types.ElicitRequestParams]) -> Any:
    async def accept(_context: object, params: types.ElicitRequestParams) -> types.ElicitResult:
        seen.append(params)
        return types.ElicitResult(action="accept", content={"decision": decision})

    return accept


def _diagnostic(result: types.CallToolResult) -> dict[str, object]:
    _prefix, marker, content = result.content[0].text.partition("{")
    assert marker, result.content[0].text
    return json.loads(marker + content)


def _generations(state_root: Path) -> dict[str, bytes]:
    directory = state_root / _GENERATIONS
    return {path.name: path.read_bytes() for path in sorted(directory.glob("*.json"))} if directory.is_dir() else {}


def _store(state_root: Path) -> ConsentGenerationStore:
    return ConsentGenerationStore(state_root, "change-a")


def _request(runtime: DeliveryRuntime) -> DeliveryRequest:
    return next(request for binding in runtime.bindings() for request in binding.requests)


def _responses(asked: types.InputRequiredResult, action: str, decision: str | None = None) -> dict[str, Any]:
    (key,) = asked.input_requests
    return {key: types.ElicitResult(action=action, content={"decision": decision} if action == "accept" else None)}


async def _ask(client: Client, arguments: dict[str, object]) -> types.InputRequiredResult:
    result = await client.session.call_tool("answer", arguments, allow_input_required=True)
    assert isinstance(result, types.InputRequiredResult), result
    return result


async def _round(
    client: Client,
    arguments: dict[str, object],
    asked: types.InputRequiredResult,
    action: str,
    decision: str | None = None,
) -> types.CallToolResult | types.InputRequiredResult:
    return await client.session.call_tool(
        "answer",
        arguments,
        input_responses=_responses(asked, action, decision),
        request_state=asked.request_state,
        allow_input_required=True,
    )


def _modern(application: object, seen: list[object] | None = None) -> Client:
    return Client(
        assemble_target_server(application),
        mode=_MODERN,
        elicitation_callback=_never_asked(seen if seen is not None else []),
    )


def _unrelated_frontier_write(application: Any, runtime: DeliveryRuntime) -> None:
    """Defer the Change: a frontier write that touches neither the request nor the ledger."""
    before = runtime.frontier_bytes()
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(before).hexdigest(),
            reason="Unrelated operator write",
        )
    )
    assert runtime.frontier_bytes() != before


def _assert_unanswered(runtime: DeliveryRuntime, before: bytes) -> None:
    assert runtime.frontier_bytes() == before
    assert runtime.confirmations() == ()
    assert _request(runtime).resolution is None


# --- Unexpected failures are not refusals ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_unexpected_failure_while_planning_the_question_is_an_internal_error_not_a_refusal(
    tmp_path: Path, mode: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    corrupt = state_root / _GENERATIONS / "00000001.json"
    corrupt.parent.mkdir(parents=True)
    corrupt.write_bytes(b"{not a generation\n")
    before = runtime.frontier_bytes()
    seen: list[object] = []

    with caplog.at_level(logging.ERROR):
        async with Client(
            assemble_target_server(application), mode=mode, elicitation_callback=_never_asked(seen)
        ) as client:
            result = await client.call_tool("answer", _arguments(runtime))

    assert result.is_error
    assert result.content[0].text == "Error executing tool answer"
    assert "ERR_DELIVERY_CONFIRMATION" not in result.content[0].text
    assert any(record.exc_info is not None for record in caplog.records)
    assert seen == []
    _assert_unanswered(runtime, before)
    assert corrupt.read_bytes() == b"{not a generation\n"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_typed_failure_while_planning_the_question_keeps_its_own_delivery_code(
    tmp_path: Path, mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()

    def contended(*_args: object, **_kwargs: object) -> None:
        message = "consent generation sequence is contended"
        raise TransactionConflictError(message)

    monkeypatch.setattr(ConsentGenerationStore, "create", contended)

    async with Client(assemble_target_server(application), mode=mode, elicitation_callback=_never_asked([])) as client:
        result = await client.call_tool("answer", _arguments(runtime))

    assert result.is_error
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_TRANSACTION_CONFLICT"
    assert diagnostic["retry_safe"] is True
    _assert_unanswered(runtime, before)
    assert _generations(state_root) == {}


# --- SDK request-state boundary (P16) -------------------------------------------------------------


def _flipped(state: str) -> str:
    middle = len(state) // 2
    return state[:middle] + ("A" if state[middle] != "A" else "B") + state[middle + 1 :]


async def _assert_boundary_refuses(
    client: Client, arguments: dict[str, object], asked: types.InputRequiredResult, state: str
) -> None:
    with pytest.raises(MCPError) as raised:
        await client.session.call_tool(
            "answer",
            arguments,
            input_responses=_responses(asked, "accept", "waive"),
            request_state=state,
            allow_input_required=True,
        )
    assert raised.value.code == INVALID_PARAMS
    assert "Invalid or expired requestState" in str(raised.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["forged", "other-request", "other-frontier", "foreign-key", "expired", "restart"])
async def test_request_state_the_sdk_boundary_rejects_reaches_no_resolver_or_handler(
    tmp_path: Path, variant: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    planned: list[object] = []

    def refuse_planning() -> None:
        monkeypatch.setattr(application, "prepare_request_confirmation", lambda *args, **_kwargs: planned.append(args))

    async with _modern(application) as minting, _modern(application) as foreign:
        asked = await _ask(minting, arguments)
        minted = _generations(state_root)
        assert len(minted) == 1
        refuse_planning()
        sent, state, client = arguments, asked.request_state, minting
        if variant == "forged":
            state = _flipped(state)
        elif variant == "other-request":
            sent = arguments | {"request_id": "another-request"}
        elif variant == "other-frontier":
            sent = arguments | {"expected_frontier_digest": "0" * 64}
        elif variant == "expired":
            real = time.time
            monkeypatch.setattr(request_state_module, "time", SimpleNamespace(time=lambda: real() + 601))
        elif variant == "foreign-key":
            await foreign.list_tools()
            client = foreign
        if variant != "restart":
            await _assert_boundary_refuses(client, sent, asked, state)
    if variant == "restart":
        # A re-assembled server has a new process-local key that never sealed this state.
        async with _modern(application) as restarted:
            await restarted.list_tools()
            await _assert_boundary_refuses(restarted, arguments, asked, asked.request_state)

    assert planned == []
    _assert_unanswered(runtime, before)
    assert _generations(state_root) == minted
    monkeypatch.undo()
    seen: list[types.ElicitRequestParams] = []
    async with Client(
        assemble_target_server(application), mode=_MODERN, elicitation_callback=_accepting("waive", seen)
    ) as client:
        accepted = await client.call_tool("answer", arguments)
    assert not accepted.is_error, accepted.content
    assert len(seen) == 1
    (confirmation,) = runtime.confirmations()
    assert confirmation.generation_id == _store(state_root).read(1)[0].generation_id


@pytest.mark.asyncio
async def test_frontier_advanced_between_rounds_consumes_the_question_as_frontier_changed(tmp_path: Path) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    arguments = _arguments(runtime)
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        _unrelated_frontier_write(application, runtime)
        advanced = runtime.frontier_bytes()
        first = await _round(client, arguments, asked, "accept", "waive")
        written = _generations(state_root)
        again = await _round(client, arguments, asked, "accept", "waive")

    for result in (first, again):
        assert isinstance(result, types.CallToolResult)
        assert result.is_error
        assert "answer frontier changed" in str(_diagnostic(result)["detail"])
    generation = _store(state_root).read(1)[0]
    assert generation.disposition is not None
    assert (generation.disposition.outcome, generation.disposition.code) == ("refused", "frontier-changed")
    assert _generations(state_root) == written
    _assert_unanswered(runtime, advanced)


def _assert_deferred_refusal(result: object) -> None:
    assert isinstance(result, types.CallToolResult)
    assert result.is_error
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_DELIVERY_RUNTIME_CONFLICT"
    assert "deferred" in str(diagnostic["detail"])


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_an_accepted_answer_the_lifecycle_recheck_refuses_consumes_its_generation(
    tmp_path: Path, mode: str
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    _unrelated_frontier_write(application, runtime)
    deferred = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    seen: list[types.ElicitRequestParams] = []

    async with Client(
        assemble_target_server(application), mode=mode, elicitation_callback=_accepting("waive", seen)
    ) as client:
        result = await client.call_tool("answer", arguments)

    assert len(seen) == 1
    _assert_deferred_refusal(result)
    generation = _store(state_root).read(1)[0]
    assert generation.state == "answered"
    assert generation.disposition is not None
    assert (generation.disposition.outcome, generation.disposition.code) == ("refused", "change-deferred")
    _assert_unanswered(runtime, deferred)


@pytest.mark.asyncio
async def test_resending_an_answer_the_lifecycle_recheck_refused_returns_the_same_refusal(tmp_path: Path) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    _unrelated_frontier_write(application, runtime)
    deferred = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        first = await _round(client, arguments, asked, "accept", "waive")
        recorded = _generations(state_root)
        again = await _round(client, arguments, asked, "accept", "waive")

    for result in (first, again):
        _assert_deferred_refusal(result)
    assert _generations(state_root) == recorded
    assert _store(state_root).read(1)[0].disposition.code == "change-deferred"
    _assert_unanswered(runtime, deferred)


# --- Single use (D13 *Single use*, I11), modern route ---------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("later_write", [False, True], ids=["immediately", "after-unrelated-write"])
async def test_resending_the_accepted_round_returns_the_original_resolution_and_writes_nothing(
    tmp_path: Path, *, later_write: bool
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    arguments = _arguments(runtime)
    seen: list[object] = []
    async with _modern(application, seen) as client:
        asked = await _ask(client, arguments)
        applied = await _round(client, arguments, asked, "accept", "waive")
        assert isinstance(applied, types.CallToolResult)
        assert not applied.is_error, applied.content
        if later_write:
            _unrelated_frontier_write(application, runtime)
        settled = runtime.frontier_bytes()
        generations = _generations(state_root)
        resent = await _round(client, arguments, asked, "accept", "waive")
        substituted = await _round(client, arguments, asked, "accept", "keep-required")
        fresh = await client.session.call_tool("answer", arguments, allow_input_required=True)

    (confirmation,) = runtime.confirmations()
    for result in (resent, substituted, fresh):
        assert isinstance(result, types.CallToolResult), result
        assert not result.is_error, result.content
        assert result.structured_content["request"]["resolution"]["confirmation_id"] == confirmation.confirmation_id
    assert seen == []
    assert runtime.frontier_bytes() == settled
    assert _generations(state_root) == generations
    assert confirmation.decision == "waive"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["waive", "confirm-check"])
@pytest.mark.parametrize("action", ["decline", "cancel"])
async def test_a_refused_question_never_turns_affirmative_and_only_a_new_call_asks_again(
    tmp_path: Path, kind: str, action: str
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path, kind=kind)
    before = runtime.frontier_bytes()
    affirmative = _AFFIRMATIVE[kind]
    arguments = _arguments(runtime, affirmative)
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        refused = await _round(client, arguments, asked, action)
        recorded = _generations(state_root)
        replayed = await _round(client, arguments, asked, "accept", affirmative)
        assert _generations(state_root) == recorded
        _assert_unanswered(runtime, before)

        renewed = await _ask(client, arguments)
        stale = await _round(client, arguments, asked, "accept", affirmative)
        _assert_unanswered(runtime, before)
        accepted = await _round(client, arguments, renewed, "accept", affirmative)

    outcome = "declined" if action == "decline" else "cancelled"
    for result in (refused, replayed):
        assert isinstance(result, types.CallToolResult)
        diagnostic = _diagnostic(result)
        assert diagnostic["code"] == "ERR_DELIVERY_CONFIRMATION"
        assert diagnostic["detail"].startswith("declined")
    old, new = _store(state_root).read(1)[0], _store(state_root).read(2)[0]
    assert old.disposition is not None
    assert old.disposition.outcome == outcome
    assert new.generation_id != old.generation_id
    (old_question,) = asked.input_requests.values()
    (new_question,) = renewed.input_requests.values()
    assert new_question.params.message != old_question.params.message
    assert new.generation_id in new_question.params.message
    # The SDK re-asks an answer given to the older rendering instead of consuming it.
    assert isinstance(stale, types.InputRequiredResult)
    assert isinstance(accepted, types.CallToolResult)
    assert not accepted.is_error, accepted.content
    (confirmation,) = runtime.confirmations()
    assert confirmation.generation_id == new.generation_id
    assert new == _store(state_root).read(2)[0]
    assert _store(state_root).read(2)[0].disposition.outcome == "accepted"


def _ordered_application_answers(
    application: Any, monkeypatch: pytest.MonkeyPatch, winner: str | None
) -> threading.Barrier:
    """Hold both continuation rounds at the owning lock, then let ``winner`` (or either) take it first."""
    apply = application.apply_request_confirmation
    barrier = threading.Barrier(2, timeout=20)
    winner_done = threading.Event()

    def ordered(*args: Any) -> Any:
        response = args[-1]
        action = response.action if response is not None else None
        barrier.wait()
        if winner is not None and action != winner:
            assert winner_done.wait(20)
        try:
            return apply(*args)
        finally:
            if action == winner:
                winner_done.set()

    monkeypatch.setattr(application, "apply_request_confirmation", ordered)
    return barrier


@pytest.mark.asyncio
@pytest.mark.parametrize("winner", ["accept", "decline"])
async def test_competing_first_answers_record_exactly_one_disposition(
    tmp_path: Path, winner: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    results: dict[str, types.CallToolResult | types.InputRequiredResult] = {}
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        _ordered_application_answers(application, monkeypatch, winner)

        async def send(action: str) -> None:
            results[action] = await _round(client, arguments, asked, action, "waive" if action == "accept" else None)

        async with anyio.create_task_group() as group:
            group.start_soon(send, "accept")
            group.start_soon(send, "decline")
        monkeypatch.undo()
        recorded = _generations(state_root)
        replays = {action: await _round(client, arguments, asked, action, "waive") for action in ("accept", "decline")}

    generation = _store(state_root).read(1)[0]
    assert generation.disposition is not None
    assert _generations(state_root) == recorded
    if winner == "accept":
        assert generation.disposition.outcome == "accepted"
        (confirmation,) = runtime.confirmations()
        for result in (*results.values(), *replays.values()):
            assert isinstance(result, types.CallToolResult)
            assert not result.is_error, result.content
            assert result.structured_content["request"]["resolution"]["confirmation_id"] == (
                confirmation.confirmation_id
            )
    else:
        assert generation.disposition.outcome == "declined"
        _assert_unanswered(runtime, before)
        for result in (*results.values(), *replays.values()):
            assert isinstance(result, types.CallToolResult)
            assert _diagnostic(result)["detail"].startswith("declined")


@pytest.mark.asyncio
async def test_two_concurrent_identical_acceptances_record_one_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    arguments = _arguments(runtime)
    results: list[types.CallToolResult | types.InputRequiredResult] = []
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        _ordered_application_answers(application, monkeypatch, None)

        async def send() -> None:
            results.append(await _round(client, arguments, asked, "accept", "waive"))

        async with anyio.create_task_group() as group:
            group.start_soon(send)
            group.start_soon(send)

    (confirmation,) = runtime.confirmations()
    assert len(results) == 2
    for result in results:
        assert isinstance(result, types.CallToolResult)
        assert not result.is_error, result.content
        assert result.structured_content["request"]["resolution"]["confirmation_id"] == confirmation.confirmation_id
    assert _store(state_root).read(1)[0].disposition.outcome == "accepted"
    assert len(_generations(state_root)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture", ["no-generation", "other-binding"])
async def test_continuation_without_the_matching_open_generation_is_question_closed(
    tmp_path: Path, fixture: str
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        if fixture == "no-generation":
            (state_root / _GENERATIONS / "00000001.json").unlink()
        else:
            _store(state_root).create(
                use="waive",
                subject_id=_REQUEST,
                binding_digest="f" * 64,
                created_at=datetime(2026, 10, 4, tzinfo=UTC),
            )
        fixture_generations = _generations(state_root)
        result = await _round(client, arguments, asked, "accept", "waive")

    assert isinstance(result, types.CallToolResult)
    diagnostic = _diagnostic(result)
    assert diagnostic["code"] == "ERR_DELIVERY_CONFIRMATION"
    assert diagnostic["detail"].startswith("question-closed")
    assert _generations(state_root) == fixture_generations
    _assert_unanswered(runtime, before)


@pytest.mark.asyncio
async def test_crash_between_generation_write_and_question_reasks_the_same_open_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    create = ConsentGenerationStore.create

    def crash_after_write(store: ConsentGenerationStore, **values: Any) -> Any:
        create(store, **values)
        message = "injected crash after the generation write"
        raise OSError(message)

    monkeypatch.setattr(ConsentGenerationStore, "create", crash_after_write)
    async with _modern(application) as client:
        crashed = await client.session.call_tool("answer", arguments, allow_input_required=True)
    monkeypatch.undo()
    assert isinstance(crashed, types.CallToolResult)
    assert crashed.is_error
    assert crashed.content[0].text == "Error executing tool answer"
    stranded = _store(state_root).read(1)[0]
    assert stranded.state == "open"
    _assert_unanswered(runtime, before)

    seen: list[types.ElicitRequestParams] = []
    async with Client(
        assemble_target_server(application), mode=_MODERN, elicitation_callback=_accepting("waive", seen)
    ) as client:
        accepted = await client.call_tool("answer", arguments)

    assert not accepted.is_error, accepted.content
    assert len(_generations(state_root)) == 1
    assert stranded.generation_id in seen[0].message
    (confirmation,) = runtime.confirmations()
    assert confirmation.generation_id == stranded.generation_id


@pytest.mark.asyncio
@pytest.mark.parametrize("then", ["unchanged", "frontier-advanced"])
async def test_an_affirmative_answer_whose_transaction_never_committed_applies_at_most_once(
    tmp_path: Path, then: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    before = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    resolve = DeliveryRuntime.resolve_request
    crashes = [1]

    def crash_before_commit(self: DeliveryRuntime, *args: Any, **kwargs: Any) -> Any:
        if crashes:
            crashes.pop()
            message = "injected crash before the answer transaction commits"
            raise OSError(message)
        return resolve(self, *args, **kwargs)

    monkeypatch.setattr(DeliveryRuntime, "resolve_request", crash_before_commit)
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        crashed = await _round(client, arguments, asked, "accept", "waive")
        assert isinstance(crashed, types.CallToolResult)
        assert crashed.content[0].text == "Error executing tool answer"
        assert _store(state_root).read(1)[0].state == "open"
        _assert_unanswered(runtime, before)
        if then == "frontier-advanced":
            _unrelated_frontier_write(application, runtime)
        expected_frontier = runtime.frontier_bytes()
        reapplied = await _round(client, arguments, asked, "accept", "waive")
        written = _generations(state_root)
        settled = runtime.frontier_bytes()
        again = await _round(client, arguments, asked, "accept", "waive")

    generation = _store(state_root).read(1)[0]
    assert _generations(state_root) == written
    assert runtime.frontier_bytes() == settled
    assert isinstance(reapplied, types.CallToolResult)
    assert isinstance(again, types.CallToolResult)
    if then == "unchanged":
        assert not reapplied.is_error, reapplied.content
        assert not again.is_error, again.content
        (confirmation,) = runtime.confirmations()
        assert generation.disposition.confirmation_id == confirmation.confirmation_id
    else:
        assert (generation.disposition.outcome, generation.disposition.code) == ("refused", "frontier-changed")
        for result in (reapplied, again):
            assert "answer frontier changed" in str(_diagnostic(result)["detail"])
        _assert_unanswered(runtime, expected_frontier)


# --- Bounded ledger (I8, I10) ---------------------------------------------------------------------


def _fill_ledger(runtime: DeliveryRuntime, state_root: Path, count: int) -> None:
    """Write ``count`` valid ledger entries for other requests of this Change (fixture)."""
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    scope = _request(runtime).applies_to
    assert isinstance(scope, DeliveryConfirmationScope)
    entries = tuple(
        DeliveryUserConfirmation.create(
            change_id="change-a",
            request=DeliveryRequest(
                request_id=f"earlier-{index:03}",
                kind=DeliveryRequestKind.DECISION,
                outcome_id="OUT-001",
                summary="An earlier confirmation",
                options=(
                    DeliveryRequestOption(option_id="waive", label="waive"),
                    DeliveryRequestOption(option_id="keep-required", label="keep-required"),
                ),
                applies_to=scope,
            ),
            decision="keep-required",
            question_digest=hashlib.sha256(f"question-{index}".encode()).hexdigest(),
            generation_id=hashlib.sha256(f"generation-{index}".encode()).hexdigest(),
            confirmed_at=datetime(2026, 10, 4, tzinfo=UTC),
        )
        for index in range(count)
    )
    content = frontier.model_copy(update={"confirmations": entries}).model_dump(mode="json")
    (state_root / "changes/change-a/frontier.json").write_bytes(
        (json.dumps(content, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["legacy", _MODERN])
async def test_the_257th_confirmation_is_a_recorded_ledger_full_refusal_that_keeps_refusing(
    tmp_path: Path, mode: str
) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    _fill_ledger(runtime, state_root, 256)
    full = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    seen: list[types.ElicitRequestParams] = []

    async with Client(
        assemble_target_server(application), mode=mode, elicitation_callback=_accepting("waive", seen)
    ) as client:
        first = await client.call_tool("answer", arguments)
        renewed = await client.call_tool("answer", arguments)

    for result in (first, renewed):
        diagnostic = _diagnostic(result)
        assert diagnostic["code"] == "ERR_DELIVERY_CONFIRMATION"
        assert diagnostic["detail"].startswith("ledger-full")
    assert len(seen) == 2
    for sequence in (1, 2):
        disposition = _store(state_root).read(sequence)[0].disposition
        assert disposition is not None
        assert (disposition.outcome, disposition.code) == ("refused", "ledger-full")
    assert runtime.frontier_bytes() == full
    assert len(runtime.confirmations()) == 256
    assert _request(runtime).resolution is None


@pytest.mark.asyncio
async def test_resending_a_ledger_full_answer_refuses_again_without_a_write(tmp_path: Path) -> None:
    application, runtime, state_root = _scoped_case(tmp_path)
    _fill_ledger(runtime, state_root, 256)
    full = runtime.frontier_bytes()
    arguments = _arguments(runtime)
    async with _modern(application) as client:
        asked = await _ask(client, arguments)
        first = await _round(client, arguments, asked, "accept", "waive")
        recorded = _generations(state_root)
        again = await _round(client, arguments, asked, "accept", "waive")

    for result in (first, again):
        assert isinstance(result, types.CallToolResult)
        assert _diagnostic(result)["detail"].startswith("ledger-full")
    assert _generations(state_root) == recorded
    assert runtime.frontier_bytes() == full
