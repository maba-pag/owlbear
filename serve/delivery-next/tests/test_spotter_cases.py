"""Spotter cases (Improvement design §4): stages, versions, rollback, the regression gate, releases, reset, prompt."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import stat
from typing import Any

import pytest

from owlbear_delivery_next.improvement import assumptions, case_intake, case_replay, cases, pilot_seed, spotter
from owlbear_delivery_next.improvement.case_replay import _counts, _result
from owlbear_delivery_next.improvement.cases import CaseError
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.state_store import spotter_test


def card(text: str = "the agent stops with work unfinished") -> dict[str, Any]:
    return {"step": "build", "intent": {"task": text, "later_requests": [], "answers": []}, "moment": {"kind": "x"}}


def new(  # noqa: PLR0913 - a case as each test needs it
    call: str = "none",
    *,
    stage: str = "test",
    source: str = "pilot",
    reserve: bool = False,
    unscored: str = "",
    assumption: str = "",
    text: str = "",
    example: str = "",
) -> str:
    """A case added through the store's own path; a test case or example gets its review."""
    cid = cases.freeze(
        card(text or call),
        {
            "source": source,
            "reserve": reserve,
            "unscored": unscored,
            "family": f"session:{call}",
            "assumption": assumption,
        },
    )
    entry = {"stage": "candidate", "call": call, "why": f"why {call}", "example": "", "review": None}
    if stage != "candidate":
        entry = cases.edited(cid, entry, stage="test", reviewed_by="sol")
    cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
    if stage == "example":
        set_example(cid, example or f"moment of {call}")
    return cid


def set_example(cid: str, example: str) -> None:
    """Choose or demote an example with the same passed-run authorization used by the gate."""
    with cases.locked():
        cur = cases.current()
        edits = {cid: cases.edited(cid, cur["cases"][cid], stage="example" if example else "test", example=example)}
        rid = f"r-{cid}-{cur['n']}"
        cases.append(
            "runs.jsonl",
            {"id": rid, "kind": "regression", "result": "passed", "parent": cur["n"], "edits": cases.digest(edits)},
        )
        cases.commit(cur["n"], edits, "t", "promote", rid)


def spend(meter: Meter, cost: float | None) -> None:
    """One session's spend on *meter*, as a look reports it: one billed call, then its confirmed total."""
    share = meter.part()
    share.call(cost)
    share.ended(cost, confirmed=True)


def looker(answers: dict[str, dict[str, str]], cost: Any = 0.1, seen: list | None = None):
    """A fake look: per prompt side ("before"/"after", told by the prompt's examples), each card's category."""

    async def look(the_card: dict[str, Any], prompt: cases.Prompt, meter: Meter) -> dict[str, Any]:
        side = "after" if "Example" in prompt.text and prompt.cases > 0 and prompt.text.count("###") > 0 else "before"
        if seen is not None:
            seen.append((the_card["intent"]["task"], side, meter.limit))
        spend(meter, cost(the_card) if callable(cost) else cost)
        said = answers.get(side, {}).get(the_card["intent"]["task"], "none")
        return {"category": said, "note": ""} if said != "garbage" else {"category": "failed"}

    return look


def run(request: dict[str, Any], look, limit: float = 50.0, look_limit: float = 1.0) -> dict[str, Any]:
    return asyncio.run(case_replay.run(request, look, Meter(limit, "replay-run"), look_limit))


def test_a_case_is_frozen_owner_only_and_every_change_is_a_new_version() -> None:
    cid = new("hand-off-fitness", stage="candidate")
    folder = cases.place()
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    for path in (folder / f"{cid}.json", folder / "cards" / f"{cid}.json.gz", folder / "versions.jsonl"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert cases.card(cid) == card("hand-off-fitness")
    entry = cases.current()["cases"][cid]
    with cases.locked():
        cases.commit(1, {cid: {**entry, "why": "another why"}}, "t", "edit")
    assert [v["n"] for v in cases.versions()] == [1, 2]
    assert cases.version(1)["cases"][cid]["why"] == "why hand-off-fitness"  # history kept
    with gzip.open(folder / "cards" / f"{cid}.json.gz", "wt") as out:
        json.dump(card("changed"), out)
    with pytest.raises(CaseError, match="not the one frozen"):
        cases.card(cid)


def test_a_test_case_needs_a_review_of_exactly_its_card_call_and_why() -> None:
    cid = new("none", stage="candidate")
    entry = cases.current()["cases"][cid]
    with pytest.raises(CaseError, match="needs a review"):
        cases.commit(1, {cid: {**entry, "stage": "test"}}, "t", "unreviewed")
    reviewed = cases.edited(cid, entry, stage="test", reviewed_by="owner")
    assert cases.commit(1, {cid: reviewed}, "t", "reviewed") == 2
    changed = cases.edited(cid, reviewed, why="a new reason")  # no longer what was reviewed
    with pytest.raises(CaseError, match="needs a review"):
        cases.commit(2, {cid: changed}, "t", "edit")
    with pytest.raises(cases.Stale):
        cases.commit(1, {cid: reviewed}, "t", "stale parent")


def test_reserve_synthetic_and_unscored_cases_are_never_examples_and_examples_stay_bounded() -> None:
    for kw in ({"reserve": True}, {"source": "synthetic"}, {"unscored": "TD-435 is absent"}):
        cid = new("course-and-constraints", **kw)
        entry = cases.edited(cid, cases.current()["cases"][cid], stage="example", example="a moment")
        assert any("never an example" in why for why in cases.problems({cid: entry}))
    big = new("hand-off-fitness")
    entry = cases.edited(big, cases.current()["cases"][big], stage="example", example="x" * (cases.EXAMPLE + 1))
    assert any("at most" in why for why in cases.problems({big: entry}))
    selected = {}
    for i in range(cases.EXAMPLES // cases.EXAMPLE):
        cid = new("none", text=f"n{i}")
        selected[cid] = cases.edited(
            cid, cases.current()["cases"][cid], stage="example", example="y" * (cases.EXAMPLE - 10)
        )
    selected[big] = cases.edited(big, cases.current()["cases"][big], stage="example", example="z" * 500)
    assert any("more than the prompt" in why for why in cases.problems(selected))


def test_the_active_examples_change_only_with_a_passed_regression_of_that_change() -> None:
    cid = new("hand-off-fitness")
    cur = cases.current()
    edits = {cid: cases.edited(cid, cur["cases"][cid], stage="example", example="a moment")}
    with pytest.raises(CaseError, match="regression run to pass"):
        cases.commit(cur["n"], edits, "t", "no run")
    with cases.locked():
        cases.append(
            "runs.jsonl",
            {
                "id": "r-1",
                "kind": "regression",
                "result": "passed",
                "parent": cur["n"],
                "edits": cases.digest({cid: {**edits[cid], "example": "other"}}),
            },
        )
    with pytest.raises(CaseError, match="regression run to pass"):
        cases.commit(cur["n"], edits, "t", "another change's run", "r-1")


def _regression_setup() -> tuple[str, dict[str, Any]]:
    """Only the scored positive/silent pair and the reviewed case to promote."""
    new("hand-off-fitness", text="pos")
    new("none", text="neg")
    chosen = new("hand-off-fitness", text="chosen")
    cur = cases.current()
    edits = {chosen: cases.edited(chosen, cur["cases"][chosen], stage="example", example="a hand-off with gaps")}
    return chosen, case_replay.regression(edits, "owner", "promote")


def test_a_regression_freezes_only_the_scored_test_cases_and_both_prompts_before_any_look() -> None:
    new("course-and-constraints", text="reserved", reserve=True)
    new("course-and-constraints", text="unscored", unscored="its decision is absent")
    chosen, request = _regression_setup()
    tasks = {cases.card(cid)["intent"]["task"] for cid in request["frozen"]}
    assert tasks == {"pos", "neg"}  # not the reserve, the unscored case or the example to be
    assert chosen not in request["frozen"]
    before, after = request["prompts"]["before"], request["prompts"]["after"]
    assert "a hand-off with gaps" in after["text"]
    assert "a hand-off with gaps" not in before["text"]
    assert after["hash"] == hashlib.sha256(after["text"].encode()).hexdigest()[:12]


def test_an_empty_comparison_is_refused() -> None:
    chosen = new("hand-off-fitness")
    cur = cases.current()
    edits = {chosen: cases.edited(chosen, cur["cases"][chosen], stage="example", example="m")}
    with pytest.raises(CaseError, match="no test case is left"):
        case_replay.regression(edits, "owner", "promote")


@pytest.mark.parametrize(
    ("before", "after", "risen"),
    [
        ({"pos": "hand-off-fitness"}, {"pos": "hand-off-fitness", "neg": "course-and-constraints"}, "false notes"),
        ({"pos": "hand-off-fitness"}, {"pos": "none"}, "misses"),
        ({"pos": "hand-off-fitness"}, {"pos": "course-and-constraints"}, "wrong categories"),
        ({"pos": "none"}, {"pos": "hand-off-fitness", "neg": "irreversible-harm"}, "false notes"),
    ],
)
def test_a_change_is_refused_when_any_count_rises_with_no_trade(before, after, risen) -> None:
    expected = {"pos": "hand-off-fitness", "neg": "none"}
    answers = {
        cid: {
            side: {"grade": case_replay.grade(want, said.get(cid, "none"))}
            for side, said in (("before", before), ("after", after))
        }
        for cid, want in expected.items()
    }
    counts = _counts(answers)
    request = {"kind": "regression", "frozen": expected}
    assert _result(request, answers, "", counts) == f"refused: {risen} rose"


def test_a_passing_result_on_a_changed_store_is_refused_as_stale_and_not_rerun() -> None:
    chosen, request = _regression_setup()
    new("none", stage="candidate")  # the store moves on while the replay runs
    out = run(request, looker({}))
    assert out["result"] == "passed"
    assert out["applied"].startswith("refused as stale")
    assert cases.current()["cases"][chosen]["stage"] == "test"


def test_a_passing_result_refused_while_a_spotter_test_runs_is_recorded_and_not_rerun() -> None:
    chosen, request = _regression_setup()
    spotter_test.declare("fewer re-runs", "B", "A")
    spotter_test.start({"model": "m", "effort": "high", "context": "", "prompt": "p", "prompt_hash": "ab12cd34",
                        "cases": cases.current()["n"]})  # fmt: skip
    out = run(request, looker({}))
    assert (out["result"], out["applied"].split(": ")[0]) == ("passed", "refused while a Spotter test is active")
    lines = (cases.place() / "runs.jsonl").read_text().splitlines()
    applied = [r for r in map(json.loads, lines) if r["id"] == out["id"] and "applied" in r]
    assert [(r["applied"], r["why"]) for r in applied] == [(None, out["applied"])]
    assert cases.current()["cases"][chosen]["stage"] == "test"


def test_the_run_stops_at_its_credit_limit_and_each_look_has_its_own_meter_inside_the_runs() -> None:
    _, request = _regression_setup()
    seen: list = []
    out = run(request, looker({}, cost=0.4, seen=seen), limit=1.0, look_limit=0.5)
    assert out["result"].startswith("refused: stopped")
    assert [s[2] for s in seen] == [0.5, 0.5, 0.5]
    assert (out["credits"]["stopped"], out["credits"]["stopped_by"]) == ("reached", "replay-run")
    assert len(seen) == 3  # no look starts once the run's limit is reached


@pytest.mark.parametrize(
    ("last", "limit", "why"),
    [
        (0.25, 1.0, "the replay-run spend is reached"),  # the run's limit reached exactly on the final look
        (None, 50.0, "the replay-run spend is unknown"),  # the final look's spend unknown
        (0.6, 50.0, "the look spend is reached"),  # the final look passed its own limit
    ],
)
def test_a_meter_closed_by_the_final_look_vetoes_activation_whatever_the_answers(last, limit, why) -> None:
    chosen, request = _regression_setup()
    looks: list = []

    def cost(_card: dict[str, Any]) -> float | None:
        looks.append(1)
        return last if len(looks) == 4 else 0.25

    out = run(request, looker({}, cost=cost), limit=limit, look_limit=0.5)
    assert len(looks) == 4
    assert out["result"] == f"refused: stopped: {why}"
    assert "applied" not in out
    assert cases.current()["cases"][chosen]["stage"] == "test"


def test_unknown_spend_admits_no_further_look() -> None:
    _, request = _regression_setup()
    seen: list = []
    out = run(request, looker({}, cost=None, seen=seen))
    assert len(seen) == 1
    assert out["result"].startswith("refused: stopped")
    assert out["credits"]["credits_known"] is False


def test_an_unusable_answer_is_retried_once_on_the_same_meter_then_refuses() -> None:
    _, request = _regression_setup()
    seen: list = []
    out = run(request, looker({"before": {"pos": "garbage"}}, seen=seen))
    assert out["result"].startswith("refused: case")
    assert seen.count(("pos", "before", 1.0)) == 2


def test_a_rollback_that_changes_the_examples_is_replayed_and_refused_when_worse() -> None:
    new("hand-off-fitness", text="pos")
    new("none", text="neg")
    ex = new("hand-off-fitness", text="ex", stage="example")
    before_example = cases.current()["n"]
    set_example(ex, "")
    edits = cases.rollback_edits(before_example)
    with pytest.raises(CaseError, match="regression run to pass"):
        cases.commit(cases.current()["n"], edits, "t", "rollback without a run")
    request = case_replay.regression(edits, "owner", f"rollback to {before_example}")
    out = run(request, looker({"before": {"pos": "hand-off-fitness"}, "after": {"pos": "none"}}))
    assert out["result"] == "refused: misses rose"
    assert cases.current()["cases"][ex]["stage"] == "test"


def test_a_release_is_its_manifest_and_examples_alone_make_none() -> None:
    new("hand-off-fitness", text="pos")
    new("none", text="neg", reserve=True)
    rid, made = case_replay.release("owner")
    assert made
    assert case_replay.release("owner") == (rid, False)
    set_example(new("none", text="ex"), "a moment")  # a new reviewed case changes the corpus: a new release
    rid2, made = case_replay.release("owner")
    assert made
    assert rid2 != rid
    ex = next(c for c, e in cases.current()["cases"].items() if e["stage"] == "example")
    set_example(ex, "")  # choosing examples alone: the same corpus, the same release
    assert case_replay.release("owner") == (rid2, False)


def test_a_release_compares_once_claimed_before_its_first_look_even_if_it_stops() -> None:
    new("hand-off-fitness", text="pos", reserve=True)
    new("none", text="neg", reserve=True)
    set_example(new("none", text="ex"), "a moment")
    rid, _ = case_replay.release("owner")
    first = case_replay.comparison(rid, 0, cases.current()["n"], "owner")
    second = case_replay.comparison(rid, 0, cases.current()["n"], "owner")  # asked before the first ran
    out = run(first, looker({}, cost=0.6), limit=0.5)
    assert out["result"].startswith("incomplete: stopped")
    assert case_replay.claimed(rid)
    said = f"incomplete: CaseError: release {rid} already used its one comparison on the reserve"
    assert run(second, looker({}))["result"] == said  # never a second use
    with pytest.raises(CaseError, match="already used"):
        case_replay.comparison(rid, 0, 1, "owner")


def test_a_comparison_never_substitutes_a_missing_version() -> None:
    new("hand-off-fitness", text="pos", reserve=True)
    rid, _ = case_replay.release("owner")
    with pytest.raises(CaseError, match="no version 99"):
        case_replay.comparison(rid, 0, 99, "owner")


def test_reset_retires_every_assumption_for_good() -> None:
    real = new("none", text="real")
    pilot_seed.synthetic("owner")
    synthetic = [c for c in cases.current()["cases"] if cases.fact(c)["source"] == "synthetic"]
    assert len(synthetic) == 6
    assert all(not cases.fact(c)["reserve"] for c in synthetic)
    with_synthetic = cases.current()["n"]
    rid, _ = case_replay.release("owner")
    retired, n = cases.reset()
    assert set(retired) == set(assumptions.KNOWN)  # the chats follower's rules too, though never used here
    assert set(cases.current()["cases"]) == {real}
    with pytest.raises(CaseError, match="reset"):
        pilot_seed.synthetic("owner")
    cases.commit(n, cases.rollback_edits(with_synthetic), "t", "rollback")
    assert set(cases.current()["cases"]) == {real}  # a rollback never revives them
    assert any(cases.fact(c)["source"] == "synthetic" for c in cases.version(with_synthetic)["cases"])  # history kept
    with pytest.raises(CaseError, match="release definition was reset"):
        case_replay.release("owner")
    with pytest.raises(CaseError, match="release definition was reset"):
        case_replay.comparison(rid, 0, 1, "owner")
    assert cases.reset() == ([], None)


def test_the_prompt_snapshot_is_exactly_what_is_hashed_and_names_its_version() -> None:
    base = cases.snapshot(verbose=False)
    assert base.text == cases.PROMPT.read_text()
    assert base.cases == 0
    assert not base.gap
    assert base.hash == hashlib.sha256(cases.PROMPT.read_bytes()).hexdigest()[:12]  # as before any example
    verbose = cases.snapshot(verbose=True)
    assert verbose.text.endswith(cases.VERBOSE)
    assert verbose.hash != base.hash


def test_an_unreadable_store_gives_the_base_prompt_and_says_so() -> None:
    new("none")
    (cases.place() / "versions.jsonl").write_text("{broken\n")
    got = cases.snapshot(verbose=False)
    assert (got.text, got.cases) == (cases.PROMPT.read_text(), 0)
    assert "could not be read" in got.gap


def test_a_case_from_an_old_record_keeps_what_the_record_has() -> None:
    folder = spotter.root()
    old = {
        "id": "rec1",
        "at": "2026-10-26T10:00:00+00:00",
        "project": "p",
        "change": "c1",
        "step": "build",
        "session": "s",
        "look": "hand-off",
        "call": "x",
        "verdict": "note",
    }  # before categories and cases
    (folder / "records-2026-10-26.jsonl").write_text(json.dumps(old) + "\n")
    with gzip.open(folder / "cards" / "rec1.json.gz", "wt") as out:
        json.dump(card(), out)
    cid = case_intake.from_record("rec1", "hand-off-fitness", "the result had gaps", "owner")
    f = cases.fact(cid)
    assert (f["source"], f["family"], f["provenance"]["record"]["change"]) == ("record", "change:c1", "c1")
    assert cases.current()["cases"][cid]["stage"] == "candidate"
    assert case_intake.side("change:c1") == ("reserve" if f["reserve"] else "dev")


def test_a_comparison_whose_prompt_cannot_be_read_is_refused_with_the_whole_reason(tmp_path, monkeypatch) -> None:
    new("hand-off-fitness", text="pos", reserve=True)
    rid, _ = case_replay.release("owner")
    monkeypatch.setattr(cases, "PROMPT", tmp_path)  # a folder where the prompt's file belongs

    with pytest.raises(CaseError) as refused:
        case_replay.comparison(rid, 0, 1, "owner")

    said = f"the Spotter's prompt cannot be read: IsADirectoryError: [Errno 21] Is a directory: '{tmp_path}'"
    assert str(refused.value) == said
