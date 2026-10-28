"""Retro's judge, bars and review (#715 gates H6/K1, F4/G1, F5, H7, J7, J5, L1) with a scripted paid call."""

import gzip
import json

import pytest

from owlbear_delivery_next.improvement import (
    retro_bars,
    retro_calls,
    retro_judge,
    retro_segments,
    retro_store,
    retro_units,
    spotter,
)
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement.retro_calls import Paid, StoppedError, Work
from owlbear_delivery_next.improvement.retro_segments import Part, Prepared


def _evidence(message):
    return json.loads(message.split("```json\n")[-1].rsplit("\n```", 1)[0])


class Asked:
    """A scripted paid call: *answer(evidence, agent)* gives each answer; every message is kept."""

    def __init__(self, answer):
        self.answer, self.messages = answer, []

    def __call__(self, _key, message, agent):
        self.messages.append(message)
        said = self.answer(_evidence(message), agent)
        if isinstance(said, Paid):
            return said
        return Paid(json.dumps(said), 1.0, float(len(self.messages)))


SHOWN = {"title": "a case", "body": "the look should have said hand-off-fitness"}
WRONG = {"call": "hand-off-fitness"}


def _record(rid, cutoff, look="handoff", category="lint", **more):
    (spotter.root() / "cards").mkdir(parents=True, exist_ok=True)
    (spotter.root() / "cards" / f"{rid}.json.gz").write_bytes(gzip.compress(json.dumps({"seen": "x" * 900}).encode()))
    return {"id": rid, "look": look, "category": category, "cutoff": cutoff, "session": "s1", "step": "chat", **more}


def _work(ask, records=(), parts=None, run="run-1", uid="chat:s1", **more):
    parts = parts if parts is not None else [Part("s1.p1", "s1", 1, 10, "s1.e3 agent: done\ns1.e4 result bash ok", "")]
    return Work(
        run,
        uid,
        {"rev": "r1"},
        {"kind": "chat", "family": uid, "gaps": []},
        list(records),
        Prepared(parts=parts),
        ask,
        **more,
    )


def _graded(evidence, skip=(), value="worth-it"):
    return {
        "findings": [],
        "grades": [{"record": r["id"], "grade": value} for r in evidence["records"] if r["id"] not in skip],
    }


def test_fifty_records_are_each_graded_once_within_bounded_batches_and_missed_only_on_sampled_silence():
    parts = [
        Part(f"s1.p{i}", "s1", i * 100 + 1, i * 100 + 99, f"s1.e{i * 100 + 1} " + "y" * 20_000, "") for i in range(3)
    ]
    records = [_record(f"r{n:02}", (n % 3) * 100 + 5) for n in range(47)]
    records += [_record("silent", 6, look="sample", category="none"), _record("loud", 7), _record("gap", 0)]
    ask = Asked(
        lambda ev, _a: {
            "findings": [],
            "grades": [
                {"record": r["id"], "grade": "missed", "call": "hand-off-fitness"}
                if r["id"] in {"silent", "loud"}
                else {"record": r["id"], "grade": "worth-it"}
                for r in ev["records"]
                if r["id"] != "r01"
            ],
        }
    )

    retro_judge.judge(_work(ask, records, parts))

    assert len(ask.messages) > 1
    assert all(len(m) <= retro_judge.BATCH for m in ask.messages)
    got = {g["record"]: g for g in retro_store.grades()}
    assert sorted(got) == sorted(r["id"] for r in records)
    assert sum(len(_evidence(m)["records"]) for m in ask.messages) == 49
    assert (got["r01"]["grade"], got["r01"]["reason"]) == ("not-assessable", "not answered")
    assert (got["silent"]["grade"], got["loud"]["grade"], got["gap"]["grade"]) == (
        "missed",
        "not-assessable",
        "not-assessable",
    )


def test_class_grades_count_only_real_assessable_final_grades_and_keep_the_rest_apart():
    base = {"look": "handoff", "category": "lint", "unit": "u", "rev": "r1"}
    retro_store.add_grades(
        [
            {"id": "rg-1", "record": "1", "grade": "worth-it", **base},
            {"id": "rg-2", "record": "2", "grade": "not-assessable", **base},
            {"id": "rg-3", "record": "3", "grade": "wrong", "preliminary": True, **base},
            {"id": "rg-4", "record": "4", "grade": "wrong", "provenance": "synthetic", **base},
        ]
    )

    counts = retro_store.class_grades()[("handoff", "lint")]

    assert (counts["worth-it"], counts["wrong"], counts["not-assessable"], counts["preliminary"]) == (1, 0, 1, 1)


def _finding(fid, family, target="agent:builder", cause="missing-context"):
    return {
        "id": fid,
        "family": family,
        "unit": family,
        "cause": cause,
        "target": target,
        "status": "known",
        "provenance": "real",
        "what": f"{fid} went wrong",
        "mechanism": "it guessed",
        "quotes": ["q"],
        "at": f"2026-01-01T00:00:0{fid[-1]}",
    }


def _judged(*uids, exposure=("agent:builder",)):
    def put(table):
        for uid in uids:
            table["units"][uid] = {
                "kind": "chat",
                "family": uid,
                "judged_at": "2026-01-02",
                "exposure": list(exposure),
                "revisions": [{"rev": "r1", "state": "judged"}],
            }

    retro_store.update(put)


def _sorting(groups):
    def answer(ev, _agent):
        return {
            "assign": {
                f["id"]: next(f"new:{k}" for k, ids in groups.items() if f["id"] in ids) for f in ev["findings"]
            },
            "new": {k: f"mechanism {k}" for k in groups},
        }

    return answer


def test_three_families_sharing_one_confirmed_mechanism_make_one_proposal_and_another_target_stays_apart():
    retro_store.add_findings([_finding(f"f{i}", f"chat:u{i}") for i in range(1, 4)])
    retro_store.add_findings([_finding("f4", "chat:u1", target="agent:reviewer")])
    ask = Asked(_sorting({"a": {"f1", "f2", "f3"}}))

    made = retro_bars.propose(_work(ask), [])

    (snap,) = props.proposals()
    assert made == [snap["id"]]
    assert (snap["kind"], snap["target"], sorted(snap["findings"])) == ("lesson", "agent:builder", ["f1", "f2", "f3"])
    assert len(ask.messages) == 1


def test_a_confirm_batchs_sorting_is_kept_in_one_write_so_a_failing_disk_never_leaves_part_of_it(monkeypatch):
    retro_store.add_findings([_finding(f"f{i}", f"chat:u{i}") for i in range(1, 4)])
    writes, real = [], retro_store.append

    def append(name, *rows):
        if name == retro_bars.ASSIGNED:
            if writes:
                msg = "the disk is full"
                raise OSError(msg)
            writes.append(rows)
        real(name, *rows)

    monkeypatch.setattr(retro_store, "append", append)
    retro_bars.propose(_work(Asked(_sorting({"a": {"f1", "f2", "f3"}}))), [])

    assert sorted(retro_bars.assignments()) == ["f1", "f2", "f3"]


def test_a_confirm_message_stays_within_its_bound_however_long_the_findings_it_sorts():
    long = " ".join(f"step{i}" for i in range(6_000))
    retro_store.add_findings([_finding("f1", "chat:u1") | {"what": long}, _finding("f2", "chat:u2") | {"what": long}])
    ask = Asked(_sorting({"a": {"f1", "f2"}}))

    retro_bars.propose(_work(ask), [])

    assert [len(m) <= retro_judge.BATCH for m in ask.messages] == [True]
    assert sorted(retro_bars.assignments()) == ["f1", "f2"]


@pytest.mark.parametrize(
    "said",
    [{"assign": {"f1": "new:a"}, "new": {"a": "one reason"}}, {"assign": {"f1": "m-x", "f2": "none"}, "new": {}}],
)
def test_a_sorting_that_leaves_a_finding_unsorted_stops_the_run_and_sorts_nothing(said):
    retro_store.add_findings([_finding("f1", "chat:u1"), _finding("f2", "chat:u2")])

    with pytest.raises(StoppedError, match="not valid"):
        retro_bars.propose(_work(Asked(lambda _ev, _a: said)), [])

    assert retro_bars.assignments() == {}


def test_two_families_whose_findings_the_confirm_batch_separates_do_not_meet_the_bar():
    retro_store.add_findings([_finding("f1", "chat:u1"), _finding("f2", "chat:u2")])

    assert retro_bars.propose(_work(Asked(_sorting({"a": {"f1"}, "b": {"f2"}}))), []) == []
    assert props.proposals() == []


def test_two_mechanisms_over_four_families_make_two_proposals_with_counterexamples_from_exposure():
    retro_store.add_findings([_finding(f"f{i}", f"chat:u{i}") for i in range(1, 5)])
    _judged("chat:u1", "chat:u2", "chat:u3", "chat:u4", "chat:u5")
    _judged("chat:u6", exposure=("agent:reviewer",))

    retro_bars.propose(_work(Asked(_sorting({"a": {"f1", "f2"}, "b": {"f3", "f4"}}))), [])

    one, two = sorted(props.proposals(), key=lambda p: p["findings"])
    assert (one["findings"], two["findings"]) == (["f1", "f2"], ["f3", "f4"])
    assert one["counterexamples"]["count"] == 3
    assert "chat:u5" in one["counterexamples"]["sample"] + two["counterexamples"]["sample"]


def test_a_grown_proposal_is_reviewed_within_bounds_bound_to_its_digest_and_a_leak_is_rejected_locally():
    big = [_finding(f"g{i:02}", f"chat:u{i}") | {"quotes": ["z" * 600] * 3} for i in range(40)]
    retro_store.add_findings(big)
    kept = props.file("real|lesson|k1", [f["id"] for f in big], kind="lesson", provenance="real")
    leaky = props.file("real|lesson|k2", ["g00"], kind="lesson", provenance="real")

    def body(ev, _agent):
        said = "see /Users/someone/x" if ev["id"] == leaky else ev["id"]
        return {"verdict": "survive", "why": "holds", "risks": [], "publishable": {"title": "t", "body": said}}

    ask = Asked(body)

    assert retro_judge.review(_work(ask)) == 2

    first = next(m for m in ask.messages if kept in m)
    assert len(first) <= retro_judge.REVIEW
    assert "more findings omitted" in first
    snaps = props.folded()
    assert (snaps[kept]["state"], snaps[kept]["review_digest"]) == ("waiting", snaps[kept]["evidence"])
    assert (snaps[leaky]["state"], snaps[leaky]["why"]) == ("rejected", "leak: a home path")


def test_an_empty_answer_at_the_limit_stops_the_run_and_the_button_completes_it_reusing_kept_batches():
    parts = [Part(f"s1.p{i}", "s1", i * 10 + 1, i * 10 + 9, f"s1.e{i * 10 + 1} " + "y" * 30_000, "") for i in (1, 2)]
    records = [_record("a", 12), _record("b", 22)]
    cut = Asked(lambda ev, _a: Paid("", 1.0, 2.0, cut=True) if ev["parts"][0]["ref"] == "s1.p2" else _graded(ev))

    with pytest.raises(StoppedError, match="cut off"):
        retro_judge.run(_work(cut, records, parts))

    assert [g["record"] for g in retro_store.grades()] == ["a"]
    assert retro_store.attempts(retro_store.lines("batches.jsonl")[-1]["key"])
    again = Asked(_graded)
    retro_judge.run(_work(again, records, parts, run="run-2"))
    assert len(again.messages) == 1
    assert sorted(g["record"] for g in retro_store.grades()) == ["a", "b"]


def test_a_part_carried_into_a_second_batch_for_its_records_yields_its_findings_once():
    parts = [Part("s1.p1", "s1", 1, 99, "s1.e3 agent: done " + "y" * 55_000, "")]
    records = [_record(f"r{n:02}", 5) for n in range(30)]
    found = {"refs": ["s1.e3"], "quotes": ["agent: done"], "what": "it said done untested", "cause": "instruction-gap"}
    ask = Asked(lambda ev, _a: _graded(ev) | {"findings": [found]})

    retro_judge.judge(_work(ask, records, parts))

    assert len(ask.messages) > 1
    assert (len(retro_store.all_findings()), len(retro_store.grades())) == (1, 30)


def test_a_grade_only_run_proposes_a_case_for_a_late_record_graded_wrong():
    def said(_ev, agent):
        if agent == "retro-review":
            return {"verdict": "survive", "why": "holds", "risks": [], "publishable": SHOWN}
        return {"findings": [], "grades": [{"record": "late", "grade": "wrong", "call": "hand-off-fitness"}]}

    out = retro_judge.run(_work(Asked(said), [_record("late", 3)], grade_only=True))

    [case] = out["proposals"]
    assert (props.folded()[case]["kind"], props.folded()[case]["call"]) == ("spotter-case", "hand-off-fitness")


@pytest.mark.parametrize("shown", [{}, {"title": "a case"}, {"title": "a case", "body": " "}])
def test_a_survivor_without_a_title_and_body_is_an_attempt_and_its_retry_keeps_them_bounded(shown):
    review = {"verdict": "survive", "why": "holds", "risks": [], "publishable": shown}
    said = {"retro-review": review, "retro": {"findings": [], "grades": [{"record": "w", "grade": "wrong"} | WRONG]}}
    ask = Asked(lambda _ev, agent: said[agent])

    with pytest.raises(StoppedError, match="not valid"):
        retro_judge.run(_work(ask, [_record("w", 3)], grade_only=True))
    [due] = props.due_reviews()
    review["publishable"] = {"title": "t" * 200, "body": "b" * 2000, "path": "/Users/x"}
    retro_judge.review(_work(ask, run="run-2"))

    got = props.folded()[due["id"]]
    assert (got["state"], got["publishable"]) == ("waiting", {"title": "t" * 120, "body": "b" * 1500})


def test_a_wrong_grade_of_an_earlier_revision_whose_case_was_never_filed_gets_it_from_a_later_run():
    retro_store.add_grades([retro_units.grade(_record("old", 3), "r0", "wrong", "fine", should="hand-off-fitness")])
    w = _work(Asked(lambda *_: {}))

    [case] = retro_bars.cases(w)

    assert (props.folded()[case]["record"], retro_bars.cases(w), len(props.folded())) == ("old", [], 1)


def test_a_review_reads_a_graded_records_moment_reason_and_right_call_and_a_fixes_steps():
    def said(_ev, agent):
        if agent == "retro-review":
            return {"verdict": "survive", "why": "holds", "risks": [], "publishable": SHOWN}
        return {"findings": [], "grades": [{"record": "w", "grade": "wrong", "reason": "it was fine", "call": "none"}]}

    ask = Asked(said)
    retro_judge.run(_work(ask, [_record("w", 3)], grade_only=True))
    fix = _finding("f1", "chat:u1", "tool:bash", "tool-defect") | {"steps": "run bash twice", "cost": "an hour"}
    retro_store.add_findings([fix])
    retro_bars.propose(_work(ask), ["f1"])
    retro_judge.review(_work(ask, run="run-2"))

    case, delivery = (_evidence(m) for m in ask.messages if "## The proposal" in m)
    [graded] = case["findings"]
    assert "handoff look at event 3 of session s1, it said lint" in graded["what"]
    assert graded["mechanism"] == "it was fine; it should have said none"
    assert delivery["findings"][0]["steps"] == "run bash twice"


SECRET = "ghp_" + "b" * 36


def test_a_secret_in_a_records_note_or_card_or_in_a_findings_text_never_leaves_in_a_message():
    noted = _record("n", 3, note=f"token {SECRET}")
    carded = _record("c", 4) | {"card": {"env": f"GITHUB_TOKEN={SECRET}"}}
    leaky = [_finding(f"f{i}", f"chat:u{i}") | {"what": f"it printed {SECRET}"} for i in (1, 2)]
    retro_store.add_findings(leaky)
    ask = Asked(lambda ev, agent: _graded(ev) if "records" in ev else _sorting({"a": {"f1", "f2"}})(ev, agent))

    retro_judge.judge(_work(ask, [noted, carded]))
    retro_bars.propose(_work(ask), [])
    ask.answer = lambda _ev, _a: {"verdict": "survive", "why": "", "risks": [], "publishable": SHOWN}
    retro_judge.review(_work(ask))

    assert len(ask.messages) == 3
    assert not [m for m in ask.messages if SECRET in m]


def test_a_judging_message_stays_within_its_bound_when_the_capture_is_all_quotes_and_accents():
    folder = retro_units.folder("s1")
    folder.mkdir(parents=True)
    said = ['"' * 900 + "é" * 500] * 60
    log = "".join(json.dumps({"type": "assistant.message", "data": {"content": s}}) + "\n" for s in said)
    (folder / "log.jsonl.gz").write_bytes(gzip.compress(log.encode()))
    (folder / "sidecar.json").write_text(json.dumps({"session": "s1", "outputs": []}))
    w = _work(Asked(_graded), [_record("a", 3)])
    w.prepared = retro_segments.prepare(["s1"], "done")

    sent = [message for _, _, message in retro_judge.judging(w)]

    assert len(sent) > 1
    assert max(len(m) for m in sent) <= retro_judge.BATCH


@pytest.mark.parametrize(
    "said",
    [
        {"findings": [{"refs": ["s1.e3"], "quotes": "done"}], "grades": []},
        {"findings": [], "grades": [{"record": 7, "grade": "worth-it"}]},
        {"findings": [{"refs": ["s1.e3"], "quotes": ["done"], "target": {"agent": "builder"}}], "grades": []},
        {"findings": [{"refs": ["s1.e3"], "quotes": ["done"], "catchable": "false"}], "grades": []},
        {"findings": [], "grades": [{"record": "a", "grade": "wrong", "call": ""}]},
        *({"findings": [], "grades": [{"record": "a", "grade": bad}]} for bad in (False, None, [], {}, "bogus")),
    ],
)
def test_a_malformed_judgement_stops_the_run_kept_as_an_attempt_with_nothing_derived(said):
    w = _work(Asked(lambda _ev, _a: said), [_record("a", 3)])

    with pytest.raises(StoppedError, match="not valid"):
        retro_judge.judge(w)

    assert (retro_store.grades(), retro_store.all_findings()) == ([], [])
    assert retro_store.attempts(retro_store.lines("batches.jsonl")[-1]["key"])


def test_a_saved_answer_no_longer_valid_stops_the_run_instead_of_being_derived_from():
    w = _work(Asked(_graded), [_record("a", 3)])
    [(_, _, message)] = retro_judge.judging(w)
    batch = retro_calls.key(w, "judge", message)
    retro_store.keep(batch, "run-0", {"findings": [{"quotes": "x"}], "grades": []}, 1.0)

    with pytest.raises(StoppedError, match="saved answer"):
        retro_judge.judge(w)

    assert (retro_store.grades(), w.ask.messages) == ([], [])
