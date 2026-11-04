"""The brief's and the plan's versions on the Change page: which challenge read which version, and what it found."""

from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import Brief, Change, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.round_records import (
    BRIEF,
    PLAN,
    RoundFinding,
    RoundLoop,
    RoundPolicy,
    Verdict,
)
from owlbear_delivery_next.change_flow import brief_rounds, versions
from owlbear_delivery_next.state_store.store import Lock, Store

LEGACY_2 = "Challenges 1 to 2 ran before versions were recorded per challenge"


def briefed(version: int, *verdicts: Verdict, findings=(), step: Step | None = None, **loop) -> Change:
    """Brief *version* after *verdicts*; its loop ended, and the version is approvable, unless *loop* says otherwise."""
    rounds = max((v.round for v in verdicts), default=0)
    lp = RoundLoop(subject=BRIEF, policy=RoundPolicy(), round=rounds, findings=list(findings), verdicts=list(verdicts))
    loop = {"ended": "clean"} | loop
    ended = version if loop["ended"] else None
    c = Change(slug="c1", brief=Brief(version=version, challenged=ended), step=step or Step(kind=StepKind.SHAPE))
    c.loops[BRIEF] = lp.model_copy(update=loop)
    return c


def found(raised: int, state: str = "fixed", n: int = 1) -> RoundFinding:
    return RoundFinding(id=f"F{n}", text="AC-1: untestable - fix: name the output", raised=raised, state=state)


def shown(listed: dict) -> list[tuple[int, str, list[str], list[str]]]:
    return [(v["n"], v["state"], [x["label"] for x in v["challenges"]], v["actions"]) for v in listed["versions"]]


def test_c1_lists_v2_and_v3_challenged_and_v4_not(c1):
    _store, app = c1
    http = TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer tok"})
    d = http.get("/api/next/changes/c1-fixture").json()

    assert shown(d["brief"]["versions"]) == [
        (1, "unreviewed", [], []),
        (2, "findings", ["Challenge 1"], []),
        (3, "findings", ["Challenge 2"], []),
        (4, "unreviewed", [], ["approve"]),
    ]
    assert (d["brief"]["versions"]["legacy"], d["brief"]["unreviewed"], d["brief"]["unapprovable"]) == ("", True, "")
    assert [v["word"] for v in d["brief"]["versions"]["versions"]][1:] == ["findings", "findings", "not challenged"]
    assert d["plan_versions"] == {"versions": [], "legacy": ""}


def test_a_clean_verdict_is_green():
    c = briefed(2, Verdict(round=1, version=1), Verdict(round=2, version=2), findings=[found(1)], head="2")

    assert shown(versions.brief(c)) == [
        (1, "findings", ["Challenge 1"], []),
        (2, "clean", ["Challenge 2"], ["approve"]),
    ]


def test_an_upheld_rejection_waits_for_you():
    """The dispute of test_brief_rounds: the last round's rejection, not accepted, waits on the owner."""
    checked = Verdict(round=1, version=2, recheck=True, upheld=1)
    c = briefed(2, Verdict(round=1, version=1), checked, findings=[found(1, "escalated")], head="2", ended="")

    assert shown(versions.brief(c)) == [
        (1, "findings", ["Challenge 1"], []),
        (2, "waits", ["Rejections checked after challenge 1"], ["approve"]),
    ]
    assert versions.brief(c)["versions"][1]["word"] == "waits for you"
    assert brief_rounds.approvable(c) == "a finding of its challenge waits for your decision"  # Approve shows, off


def test_a_running_challenge_is_blue():
    running = Step(kind=StepKind.SHAPE, mode="challenge")
    c = briefed(2, Verdict(round=1, version=1), findings=[found(1)], step=running, ended="")
    c.brief.requested = 2

    assert shown(versions.brief(c)) == [(1, "findings", ["Challenge 1"], []), (2, "running", [], ["approve"])]


def test_a_rejections_only_check_is_not_a_challenge():
    """An accepted rejection leaves v2 unreviewed: no full round read it, and no challenge is counted."""
    c = briefed(
        2, Verdict(round=1, version=1), Verdict(round=1, version=2, recheck=True), findings=[found(1, "withdrawn")]
    )
    c.loops[BRIEF].unreviewed = ["v2"]

    listed = versions.brief(c)

    assert shown(listed) == [
        (1, "findings", ["Challenge 1"], []),
        (2, "unreviewed", ["Rejections checked after challenge 1"], ["approve"]),
    ]
    assert listed["legacy"] == ""


def test_a_legacy_loop_says_only_what_it_knows():
    """Two rounds before versions were recorded, then one that was: v1 to v3 are not recorded, never guessed."""
    c = briefed(4, Verdict(round=3, version=4), findings=[found(1), found(2, n=2)], round=3)

    listed = versions.brief(c)

    assert listed["legacy"] == LEGACY_2
    assert shown(listed) == [
        (1, "unknown", [], []),
        (2, "unknown", [], []),
        (3, "unknown", [], []),
        (4, "clean", ["Challenge 3"], ["approve"]),
    ]
    assert listed["versions"][0]["word"] == "not recorded"


def test_an_old_rejection_upheld_later_keeps_its_version_orange(tmp_path):
    """Round 2 raised nothing new but did not accept round 1's rejection; the owner then resolved it."""
    c = briefed(2, Verdict(round=1, version=1), Verdict(round=2, version=2, upheld=1), findings=[found(1, "owner-fix")])
    store = Store(tmp_path)
    store.write(Lock(c.slug), c)

    assert shown(versions.brief(store.read(c.slug))) == [
        (1, "findings", ["Challenge 1"], []),
        (2, "findings", ["Challenge 2"], ["approve"]),
    ]


def test_plan_versions_and_a_legacy_plan_head():
    """Two plan rounds read hashes, the third read v3; a replaced task loop in the history is no plan challenge."""
    task_loop = RoundLoop(subject="t1", policy=RoundPolicy(), round=2)
    lp = RoundLoop(
        subject=PLAN, policy=RoundPolicy(), round=3, verdicts=[Verdict(round=3, version=3)], history=[task_loop]
    )
    c = Change(slug="c1", plan=Plan(version=3, tasks=[Task(id="t1", title="part 1", scope=["src"])]))
    c.loops[PLAN] = lp

    listed = versions.plan(c)

    assert listed["legacy"] == LEGACY_2
    assert shown(listed) == [(1, "unknown", [], []), (2, "unknown", [], []), (3, "clean", ["Challenge 3"], [])]
