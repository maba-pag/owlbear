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
from owlbear_delivery_next.improvement.cases import CaseError
from owlbear_delivery_next.improvement.credit_meter import Meter


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
    with cases.locked():
        cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
        if stage != "candidate":
            done = cases.edited(cid, entry, stage="test", reviewed_by="sol")
            cases.commit(cases.current()["n"], {cid: done}, "t", "review")
    if stage == "example":
        promote(cid, example or f"moment of {call}")
    return cid


def promote(cid: str, example: str) -> None:
    """Make *cid* an example as a passed regression would: its run is written first."""
    with cases.locked():
        cur = cases.current()
        edits = {cid: cases.edited(cid, cur["cases"][cid], stage="example", example=example)}
        rid = f"r-{cid}"
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
        with pytest.raises(CaseError, match="never an example"):
            promote(cid, "a moment")
    big = new("hand-off-fitness")
    with pytest.raises(CaseError, match="at most"):
        promote(big, "x" * (cases.EXAMPLE + 1))
    for i in range(cases.EXAMPLES // cases.EXAMPLE):
        promote(new("none", text=f"n{i}"), "y" * (cases.EXAMPLE - 10))
    with pytest.raises(CaseError, match="more than the prompt"):
        promote(big, "z" * 500)


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
    """Two scored test cases (one positive, one silent), a reserve and an unscored one; a candidate to promote."""
    new("hand-off-fitness", text="pos")
    new("none", text="neg")
    new("course-and-constraints", text="reserved", reserve=True)
    new("course-and-constraints", text="unscored", unscored="its decision is absent")
    chosen = new("hand-off-fitness", text="chosen")
    cur = cases.current()
    edits = {chosen: cases.edited(chosen, cur["cases"][chosen], stage="example", example="a hand-off with gaps")}
    return chosen, case_replay.regression(edits, "owner", "promote")


def test_a_regression_freezes_only_the_scored_test_cases_and_both_prompts_before_any_look() -> None:
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


def test_a_tie_passes_and_writes_the_change_onto_the_version_it_was_asked_against() -> None:
    chosen, request = _regression_setup()
    seen: list = []
    out = run(request, looker({"before": {"pos": "hand-off-fitness"}, "after": {"pos": "hand-off-fitness"}}, seen=seen))
    assert out["result"] == "passed"
    assert out["applied"] == request["parent"] + 1
    assert cases.current()["cases"][chosen]["stage"] == "example"
    assert cases.snapshot(verbose=False).cases == out["applied"]
    assert len(seen) == 4
    kept = case_replay.results()
    assert kept[0]["frozen"] == request["frozen"]
    assert kept[1]["applied"] == out["applied"]


@pytest.mark.parametrize(
    ("before", "after", "risen"),
    [
        ({"pos": "hand-off-fitness"}, {"pos": "hand-off-fitness", "neg": "course-and-constraints"}, "false notes"),
        ({"pos": "hand-off-fitness"}, {"pos": "none"}, "misses"),
        ({"pos": "hand-off-fitness"}, {"pos": "course-and-constraints"}, "wrong categories"),
    ],
)
def test_a_change_is_refused_when_any_count_rises_with_no_trade(before, after, risen) -> None:
    chosen, request = _regression_setup()
    out = run(request, looker({"before": before, "after": after}))
    assert out["result"] == f"refused: {risen} rose"
    assert cases.current()["cases"][chosen]["stage"] == "test"


def test_fewer_misses_never_buy_a_new_false_note() -> None:
    _, request = _regression_setup()
    out = run(
        request, looker({"before": {"pos": "none"}, "after": {"pos": "hand-off-fitness", "neg": "irreversible-harm"}})
    )
    assert out["result"] == "refused: false notes rose"


def test_a_passing_result_on_a_changed_store_is_refused_as_stale_and_not_rerun() -> None:
    chosen, request = _regression_setup()
    new("none", stage="candidate")  # the store moves on while the replay runs
    out = run(request, looker({}))
    assert out["result"] == "passed"
    assert out["applied"].startswith("refused as stale")
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
    with cases.locked():
        cur = cases.current()
        demoted = cases.edited(ex, cur["cases"][ex], stage="test")
        cases.append(
            "runs.jsonl",
            {
                "id": "r-d",
                "kind": "regression",
                "result": "passed",
                "parent": cur["n"],
                "edits": cases.digest({ex: demoted}),
            },
        )
        cases.commit(cur["n"], {ex: demoted}, "t", "demote", "r-d")
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
    promote(new("none", text="ex"), "a moment")  # a new reviewed case changes the corpus: a new release
    rid2, made = case_replay.release("owner")
    assert made
    assert rid2 != rid
    with cases.locked():  # choosing the examples alone: the same corpus, the same release
        cur = cases.current()
        ex = next(c for c, e in cur["cases"].items() if e["stage"] == "example")
        demoted = cases.edited(ex, cur["cases"][ex], stage="test")
        cases.append(
            "runs.jsonl",
            {
                "id": "r-x",
                "kind": "regression",
                "result": "passed",
                "parent": cur["n"],
                "edits": cases.digest({ex: demoted}),
            },
        )
        cases.commit(cur["n"], {ex: demoted}, "t", "demote", "r-x")
    assert case_replay.release("owner") == (rid2, False)


def test_a_release_compares_once_claimed_before_its_first_look_even_if_it_stops() -> None:
    new("hand-off-fitness", text="pos", reserve=True)
    new("none", text="neg", reserve=True)
    promote(new("none", text="ex"), "a moment")
    rid, _ = case_replay.release("owner")
    first = case_replay.comparison(rid, 0, cases.current()["n"], "owner")
    second = case_replay.comparison(rid, 0, cases.current()["n"], "owner")  # asked before the first ran
    out = run(first, looker({}, cost=0.6), limit=0.5)
    assert out["result"].startswith("incomplete: stopped")
    assert case_replay.claimed(rid)
    assert run(second, looker({}))["result"].startswith("incomplete: release")  # never a second use
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
    assert set(retired) == {assumptions.RELEASE, assumptions.SYNTHETIC}
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
    promote(new("hand-off-fitness"), "the agent stopped with two criteria unmet")
    shown = cases.snapshot(verbose=False)
    assert "the agent stopped with two criteria unmet" in shown.text
    assert "`hand-off-fitness`" in shown.text
    assert shown.cases == cases.current()["n"]
    assert shown.hash == hashlib.sha256(shown.text.encode()).hexdigest()[:12]


def test_an_unreadable_store_gives_the_base_prompt_and_says_so() -> None:
    new("none")
    (cases.place() / "versions.jsonl").write_text("{broken\n")
    got = cases.snapshot(verbose=False)
    assert (got.text, got.cases) == (cases.PROMPT.read_text(), 0)
    assert "could not be read" in got.gap


def test_a_spotter_record_keeps_the_hash_and_version_of_the_prompt_it_sent() -> None:
    promote(new("hand-off-fitness"), "a moment")
    prompt = cases.snapshot(verbose=False)
    ctx = spotter.Context(
        project="p",
        change="c",
        step="build",
        looks=("hand-off",),
        sample_rate=0,
        verbose=False,
        model="m",
        effort="",
        budget=50,
        prompt=prompt,
    )
    sent: list = []

    async def judge(_card: dict[str, Any], c: spotter.Context) -> tuple[str, float]:
        sent.append(c.prompt)
        return '{"category": "none", "note": ""}', 0.1

    async def main() -> None:
        spot = spotter.Spotter(ctx, lambda: "s", judge)
        spot.handed_off("call", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    [line] = (spotter.place() / f"records-{spotter._today()}.jsonl").read_text().splitlines()  # noqa: SLF001
    rec = json.loads(line)
    assert (rec["prompt"], rec["cases"]) == (prompt.hash, prompt.cases)
    assert sent == [prompt]


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
