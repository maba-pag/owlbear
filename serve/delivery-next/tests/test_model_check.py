"""TD-94: only usage proves the model; a mismatch reruns once after a wait, an unknown one stops, unread credits
never show 0."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from owlbear_delivery_next import sdk_adapter, sdk_usage, sessions, subagents, vscode_adapter
from owlbear_delivery_next.models import Exit, StepKind
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import Gate
from owlbear_delivery_next.session_result import Run, to_result
from owlbear_delivery_next.spend import ModelSpend, Spend
from owlbear_delivery_next.vscode_contract import Outcome

NOW = datetime(2026, 10, 15, 2, tzinfo=UTC)
MODEL = "gpt-6-luna"


def test_a_wrong_model_voids_the_result_and_reruns_before_the_quota_or_an_unknown_model_counts() -> None:
    run = Run("s", ending="result", termination=Termination(confirmed=True), quota=True)
    gate = Gate(SimpleNamespace(), run, lambda **_: None, lambda: None)
    gate.wrong_model("a turn ran on gpt-6-sol, the step needs gpt-6-luna")
    run.usage_unread = "the usage at the step's end could not be read (RuntimeError)"
    assert (run.ending, run.payload, run.model_check) == ("error", None, "mismatch")
    result = to_result(run, StepKind.BUILD, NOW)
    assert (result.exit, result.cause) == (Exit.RETRY, "tooling:build:wrong-model")
    assert result.reason == "wrong model: a turn ran on gpt-6-sol, the step needs gpt-6-luna"
    assert not sessions.unread(run)  # the known mismatch wins over the unknown model's stop


def test_only_growth_of_the_steps_own_model_proves_it() -> None:
    grown = {"models": {MODEL: {"tokens": 90}}}
    assert sdk_usage.unproven({}, grown, MODEL) == ""
    assert sdk_usage.unproven({"models": {MODEL: {"tokens": 90}}}, grown, MODEL) == (
        "the usage does not show the step's model gpt-6-luna"
    )
    other = {"models": {"claude-haiku-5.5": {"tokens": 40}}}
    assert sdk_usage.unproven({}, other, MODEL) == "the usage does not show the step's model gpt-6-luna"
    assert sdk_usage.unproven({"error": "RuntimeError"}, grown, MODEL) == ""  # unread() names that one


def _session(*reads: dict) -> SimpleNamespace:
    left = list(reads)

    async def metrics() -> SimpleNamespace:
        r = left.pop(0)
        models = {
            name: SimpleNamespace(
                total_nano_aiu=None, usage=SimpleNamespace(input_tokens=t, output_tokens=0, cache_read_tokens=0)
            )
            for name, t in r.items()
        }
        return SimpleNamespace(total_nano_aiu=None, model_metrics=models)

    return SimpleNamespace(rpc=SimpleNamespace(usage=SimpleNamespace(get_metrics=metrics)))


def _step(usage: dict, *, ending: str = "result") -> SimpleNamespace:
    events: list[dict] = []
    run = Run("s", ending=ending, usage=usage)
    return SimpleNamespace(
        run=run,
        sending=True,
        billed={},
        cfg=SimpleNamespace(model=MODEL),
        log=lambda **e: events.append(e),
        events=events,
        gate=Gate(SimpleNamespace(), run, lambda **_: None, lambda: None),
        watch=subagents.Watch(allowed=False),
    )


def test_an_sdk_result_whose_model_the_usage_does_not_show_is_read_again_then_unknown(monkeypatch) -> None:
    monkeypatch.setattr(sdk_adapter, "USAGE_PAUSE", 0)
    late = _step({"models": {}})
    asyncio.run(sdk_adapter._proven(late, _session({MODEL: 12})))  # noqa: SLF001
    assert (late.run.model_check, late.run.usage_unread) == ("verified", "")
    missing = _step({"models": {}})
    asyncio.run(sdk_adapter._proven(missing, _session({})))  # noqa: SLF001
    assert missing.run.model_check == "unknown"
    assert missing.run.usage_unread == "the usage does not show the step's model gpt-6-luna"
    assert missing.events == [{"event": "usage-unread", "reason": missing.run.usage_unread}]
    errored = _step({"models": {}}, ending="error")  # nothing to process: no gate, and still no proof
    asyncio.run(sdk_adapter._proven(errored, _session()))  # noqa: SLF001
    assert (errored.run.model_check, errored.run.usage_unread) == ("unknown", "")


def test_the_second_usage_read_is_checked_for_a_wrong_model_and_a_mismatch_is_final(monkeypatch) -> None:
    monkeypatch.setattr(sdk_adapter, "USAGE_PAUSE", 0)
    st = _step({"models": {}})
    asyncio.run(sdk_adapter._proven(st, _session({MODEL: 12, "mai-code-1.1-flash": 5})))  # noqa: SLF001
    assert (st.run.ending, st.run.model_check, st.run.usage_unread) == ("error", "mismatch", "")
    assert st.run.detail == "wrong model: the usage names mai-code-1.1-flash, the step needs gpt-6-luna"
    late = _step({"models": {}})
    late.run.model_check = "mismatch"  # an event during the read
    asyncio.run(sdk_adapter._proven(late, _session({MODEL: 12})))  # noqa: SLF001
    assert late.run.model_check == "mismatch"


def test_only_a_judges_verdict_is_held_for_its_round_and_any_other_unproven_ending_gates() -> None:
    done = Termination(confirmed=True)
    verdict = Run("v", ending="result", payload=object(), usage_unread="x", termination=done)
    asked = Run("a", ending="ask", payload=object(), usage_unread="x", termination=done)
    assert (sessions.held(verdict), sessions.held(asked)) == (True, False)


def test_a_window_result_needs_a_usage_report_naming_the_steps_model() -> None:
    run = Run("w", ending="result", runtime="window")
    vscode_adapter._proven(run, Outcome("complete", tokens={}), MODEL)  # noqa: SLF001
    assert (run.model_check, run.usage_unread) == (
        "unknown",
        "no usage report of the window named the step's model gpt-6-luna",
    )
    run = Run("w", ending="result", runtime="window")
    vscode_adapter._proven(run, Outcome("complete", tokens={MODEL: 120}), MODEL)  # noqa: SLF001
    assert (run.model_check, run.usage_unread) == ("verified", "")
    wrong = Run("w", ending="error", runtime="window", model_check="mismatch")
    vscode_adapter._proven(wrong, Outcome("wrong-model", tokens={"gpt-6-sol": 9}), MODEL)  # noqa: SLF001
    assert (wrong.model_check, wrong.usage_unread) == ("mismatch", "")


def test_unread_credits_make_the_total_a_lower_bound_until_the_session_reports_them() -> None:
    spend = Spend().plus({"credits": 2.0, "models": {MODEL: {"credits": 2.0, "tokens": 10}}}, "s1")
    spend = spend.plus({"credits": None, "models": {"claude-opus-5.5": {"credits": None, "tokens": 30}}}, "w1")
    assert (spend.credits, spend.unread, spend.shown()) == (2.0, ["w1"], "2.00+ credits (unknown for 1 session)")
    assert spend.models["claude-opus-5.5"] == ModelSpend(credits_unread=True, tokens=30)
    spend = spend.plus({"error": "RuntimeError"}, "s2")
    assert spend.shown() == "2.00+ credits (unknown for 2 sessions)"
    spend = spend.plus({"credits": 1.0, "models": {"claude-opus-5.5": {"credits": 1.0, "tokens": 40}}}, "w1")
    assert (spend.unread, spend.models["claude-opus-5.5"].credits_unread) == (["s2"], False)
    assert Spend().plus({"credits": None, "models": {}}, "w2").shown() == "credits unknown for 1 session"


def test_a_failed_report_marks_the_sessions_models_unread_even_after_a_known_zero() -> None:
    spend = Spend().plus({"credits": 0.0, "models": {MODEL: {"credits": 0.0, "tokens": 4}}}, "s1")
    spend = spend.plus({"error": "RuntimeError"}, "s1")
    assert (spend.unread, spend.models[MODEL].credits_unread) == (["s1"], True)
    spend = spend.plus({"credits": 0.5, "models": {MODEL: {"credits": 0.5, "tokens": 9}}}, "s1")
    assert (spend.unread, spend.models[MODEL]) == ([], ModelSpend(credits=0.5, tokens=9))
