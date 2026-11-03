"""A brief amendment on one Change (TD-185): what applies alone, what asks the owner, what it voids, what resumes."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import evidence
from owlbear_delivery_next.change_contracts.amend_tools import Affected, CandidateItem, CandidateResult, VerdictResult
from owlbear_delivery_next.change_contracts.decision_records import BriefDecision, DecisionBaseline
from owlbear_delivery_next.change_contracts.evidence import next_check, review_valid, visual_valid
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, BriefApproval, ObjectionItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Criterion,
    Exit,
    Inputs,
    PersonCheck,
    Plan,
    Question,
    Review,
    Step,
    StepKind,
    Task,
    VisualState,
    VisualStep,
)
from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.change_contracts.visual_records import VisualResult
from owlbear_delivery_next.change_flow import amend_apply, amending, loop
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import chat_routes
from owlbear_delivery_next.runtimes import amendments, step_input
from owlbear_delivery_next.state_store import change_record
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import queue

NOW = datetime(2026, 11, 4, 9, tzinfo=UTC)
K = StepKind
AC1, AC2 = "greet() trims the name", "Says Hallo"
ASKS = ["yes", "within", "reshape", "stop"]


def passed(**criteria: int) -> Answer:
    return Answer(at=NOW, passed=True, inputs=Inputs(criteria=criteria, procedure=1))


def change(kind: StepKind = K.BUILD, task: str | None = "t1") -> Change:
    """Approved v3: AC-1 generated, AC-2 the owner's; two UI states, two passed person checks, one constraint."""
    brief = Brief(
        version=3, approved_version=3, challenged=3, approved_at=NOW, title="Greet", outcome="greet(name) greets",
        scope=["packages/app"], criteria=[Criterion(id="AC-1", text=AC1), Criterion(id="AC-2", text=AC2, version=2)],
        ui=True, specified=["AC-2"],
        visual=[VisualState(name="home", path="/", expect="shows Hallo", version=3),
                VisualState(name="about", path="/about", expect="shows the team", version=3)],
        decisions=[BriefDecision(id="D-1", question="Which store?", answer="SQLite only", origin="approved")],
    )  # fmt: skip
    checks = [
        PersonCheck(id="check-1", criteria=["AC-1"], steps=["open /"], expect="it greets",
                    answer=passed(**{"AC-1": 1})),
        PersonCheck(id="check-2", criteria=["AC-2"], steps=["open /about"], expect="it shows the team",
                    answer=passed(**{"AC-2": 2})),
    ]  # fmt: skip
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["a.txt"]), Task(id="t2", title="two", scope=["b.txt"])])
    c = Change(slug="c1", brief=brief, checks=checks, plan=plan, step=Step(kind=kind, task=task))
    brief.approved = [brief.model_copy(deep=True, update={"checks": [p.model_copy(deep=True) for p in checks]})]
    return c


def item(field: str = "criterion", key: str = "AC-1", text: str = "greet() trims spaces", **more) -> CandidateItem:
    return CandidateItem(field=field, key=key, text=text, why="tabs are not names", **more)


def verdict(said: str = "equivalent", **more) -> VerdictResult:
    return VerdictResult(verdict=said, **{"reasons": "AC-3 covers what AC-1 over-specified", "qualifies": True} | more)


def through(c: Change, *items: CandidateItem, source: str = "worker", said: VerdictResult | None = None, **start):
    """One amendment from *source*: the shaper's candidate, then one clean challenge round."""
    a = amending.start(c, source, reason="AC-1 is over-specific", now=NOW, **start)
    amending.prepared(c, CandidateResult(items=list(items) or [item()]), RoundPolicy(), NOW)
    amending.judged(c, said or verdict(), "c1-challenge", NOW)
    return a


def options(c: Change) -> list[str]:
    q = loop.open_question(c)
    return [o.id for o in q.options] if q else []


def answer(c: Change, option: str, text: str = "") -> list:
    dropped: list = []
    q = loop.open_question(c)
    assert amending.answered(c, AnswerItem(question=q.id, option=option, text=text, at=NOW), NOW, dropped)
    return dropped


def test_a_qualifying_replacement_of_a_generated_criterion_applies_alone_and_keeps_the_reference():
    c = change()
    a = through(c)

    assert (a.state, a.level, a.version, c.brief.version, c.brief.approved_version) == (
        "applied",
        "autonomous",
        4,
        4,
        4,
    )
    assert ([k.text for k in c.brief.criteria], c.brief.specified) == (["greet() trims spaces", AC2], ["AC-2"])
    assert (c.brief.reference, amend_apply.reference(c), [b.version for b in c.brief.approved]) == (None, 3, [3, 4])
    assert (c.amending, c.step.kind, c.step.task, c.outcome) == (None, K.BUILD, "t1", None)  # the task runs again


@pytest.mark.parametrize(
    "said",
    [
        verdict(qualifies=False),  # equivalent, but not shown by independent evidence
        verdict(build_only=True),  # only the failing build motivates it
        verdict(qualifies=False, reasons="a rewording of AC-1, which is neither redundant nor over-specific"),
        verdict(tightening="AC-1 now also trims tabs: one more test"),
        verdict(widens=True),
    ],
)
def test_an_equivalent_candidate_that_does_not_qualify_asks_the_owner(said):
    c = change()
    a = through(c, said=said)

    assert (a.state, c.brief.version, c.amending.phase, options(c)) == ("proposed", 3, "ask", ASKS)
    q = loop.open_question(c)
    assert all(x in q.text for x in (AC1, "greet() trims spaces", "AC-1 is over-specific", "Redone after it"))


@pytest.mark.parametrize(
    "candidate",
    [
        item(key="AC-2", text="Says Hallo or Hello"),
        item(key="", text="greet() keeps inner spaces"),
        item("ui", "", "false"),
    ],
)
def test_an_owner_specified_item_an_addition_or_another_field_never_applies_alone(candidate):
    c = change()
    through(c, candidate)

    assert (c.brief.version, options(c)) == (3, ASKS)


def test_a_sum_of_equivalent_amendments_is_judged_together_and_the_second_asks():
    c = change()
    through(c)  # A1 applies alone
    a2 = amending.start(c, "worker", reason="AC-2 is too strict", now=NOW)
    amending.prepared(c, CandidateResult(items=[item(key="AC-1", text="greet() keeps the name")]), RoundPolicy(), NOW)

    told = amendments.challenge(c, a2, Path(), recheck=False)

    assert "## The reference version v3" in told
    assert (
        f"- A1 (v4, autonomous): criterion:AC-1 '{AC1}' -> 'greet() trims spaces'" in told
    )  # the challenger judges A2 together with A1
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)
    assert (a2.reference, c.brief.version, options(c)) == (3, 4, ASKS)


@pytest.mark.parametrize("said", ["weaker", "unsure"])
def test_a_weaker_or_unsure_candidate_applies_only_with_his_yes_and_then_moves_the_reference(said):
    c = change()
    through(c)  # A1 applies alone, so it counts toward a later candidate's weakening
    a2 = through(c, item(key="AC-1", text="greet() keeps the name"), said=verdict(said, qualifies=False))
    assert (a2.state, c.brief.version, [x.id for x in amend_apply.since(c)]) == ("proposed", 4, ["A1"])

    answer(c, "yes")

    assert (a2.state, a2.level, a2.choice, c.brief.version, c.brief.reference) == ("applied", "approved", "yes", 5, 5)
    assert (amend_apply.since(c), "AC-1" in c.brief.specified) == ([], True)  # his wording is now his own


@pytest.mark.parametrize(
    ("candidate", "applied"),
    [
        (item(key="AC-2", text="Says Hallo or Hello"), lambda c: c.brief.criteria[1].text == "Says Hallo or Hello"),
        (item("ui", "", "false"), lambda c: c.brief.ui is False),
        (
            item("visual", "home", "shows Hello"),
            lambda c: (c.brief.visual[0].expect, c.brief.visual[0].version) == ("shows Hello", 4),
        ),
        (
            item("check", "check-1", "it greets twice"),
            lambda c: (c.checks[0].expect, c.checks[0].answer) == ("it greets twice", None),
        ),
        (
            item("scope", "packages/app", "packages/app and packages/web"),
            lambda c: c.brief.scope == ["packages/app and packages/web"],
        ),
        (
            item("decision", "D-1", "SQLite or Postgres"),
            lambda c: (
                [(d.answer, d.replaces, d.scope) for d in c.brief.decisions]
                == [("SQLite or Postgres", "D-1", "change")]
            ),
        ),
    ],
)
def test_with_his_yes_each_amendable_field_applies(candidate, applied):
    c = change()
    a = through(c, candidate, said=verdict("weaker", qualifies=False))
    assert options(c) == ASKS

    answer(c, "yes")

    assert (a.state, a.level, c.brief.version, applied(c)) == ("applied", "approved", 4, True)
    assert c.brief.approved[0].model_dump(exclude={"approved"}) == change().brief.approved[0].model_dump(
        exclude={"approved"}
    )  # the earlier version is never edited


def test_an_outcome_or_non_goal_change_is_refused_for_reshaping():
    c = change()
    a = amending.start(c, "worker", reason="it should also say goodbye", now=NOW)

    amending.prepared(c, CandidateResult(refuse="saying goodbye is a new outcome"), RoundPolicy(), NOW)

    assert (a.state, a.refused, options(c)) == (
        "refused",
        "saying goodbye is a new outcome",
        ["within", "reshape", "stop"],
    )
    assert answer(c, "reshape") != []  # reshaping needs his reason
    answer(c, "reshape", "add a farewell to the brief")
    assert (a.state, a.choice, c.intent.words, c.intent.hold) == (
        "refused",
        "reshape",
        "add a farewell to the brief",
        True,
    )


def test_a_candidate_prepared_against_one_version_is_never_applied_to_the_next():
    c = change()
    a = amending.start(c, "worker", reason="AC-1 is over-specific", now=NOW)
    amending.prepared(c, CandidateResult(items=[item()]), RoundPolicy(), NOW)
    c.brief.version = 4  # another version was made meanwhile

    amending.judged(c, verdict(), "c1-challenge", NOW)

    assert (a.state, a.base, c.amending.phase, [k.text for k in c.brief.criteria]) == (
        "proposed",
        3,
        "prepare",
        [AC1, AC2],
    )


def test_an_owner_source_applies_what_his_answer_said_and_asks_only_about_more():
    c = change()
    a = through(c, item("scope", "packages/app", "packages/web"), source="answer", said=verdict("weaker"))
    assert (a.state, a.level, options(c)) == ("applied", "decided", [])  # no second question about his own answer

    c = change()
    a = through(c, item("scope", "packages/app", "packages/web"), source="answer",
                said=verdict("weaker", beyond="it also drops packages/app"))  # fmt: skip
    assert (a.state, options(c)) == ("proposed", ASKS)
    assert "Beyond your answer: it also drops packages/app" in loop.open_question(c).text


@pytest.mark.parametrize(
    ("level", "kind", "task", "then"),
    [
        ("autonomous", K.BUILD, "t1", (K.BUILD, "t1", None)),
        ("approved", K.BUILD, "t1", (K.PLAN, None, Exit.BACK)),  # replanned with the whole plan
        ("approved", K.REVIEW, "t1", (K.PLAN, None, Exit.BACK)),
        ("approved", K.PLAN, None, (K.PLAN, None, None)),
        ("approved", K.REVIEW, None, (K.REVIEW, None, None)),  # the final review
        ("approved", K.CHECK, "check-1", (K.CHECK, "check-1", None)),
    ],
)
def test_the_stopped_step_resumes_on_the_new_version_by_its_level(level, kind, task, then):
    c = change(kind, task)
    said = verdict() if level == "autonomous" else verdict("weaker", qualifies=False)
    through(c, said=said)
    if level == "approved":
        answer(c, "yes")

    assert (c.step.kind, c.step.task, c.outcome.exit if c.outcome else None, c.brief.version) == (*then, 4)


def test_the_replan_is_told_which_task_stopped_and_what_is_done():
    c = change(K.BUILD, "t2")
    c.plan.tasks[0].done = True
    through(c, said=verdict("weaker", qualifies=False))
    answer(c, "yes")

    assert c.outcome.reason == "brief v4 (A1) stopped task t2; done before it, their work on the branch: t1 (one)"


def test_a_widening_amendment_has_unpicked_decisions_reassessed():
    c = change()
    said = {"D-p1": {"title": "Plain HTML", "statement": "No build"}}
    revisions = {"D-p1": "r1", "D-p2": "r1"}
    c.decisions_baseline = DecisionBaseline(commit="abc", at=NOW, revisions=revisions, said=said, picked=True)
    through(c, item("scope", "packages/app", "packages/app and packages/web"), said=verdict("weaker", widens=True))
    answer(c, "yes")

    assert c.decisions_baseline.revisions == {"D-p1": "r1"}  # D-p2 goes to the picker before work resumes


def final(c: Change) -> Review:
    return Review(commit="h1", inputs=Inputs(criteria={"AC-1": 1, "AC-2": 2}), verdict="pass", brief=c.brief.version)


def test_a_constraint_amendment_voids_the_final_review_until_one_of_the_new_version_passes():
    c = change(K.REVIEW, None)
    old = final(c)
    assert review_valid(c, old, {})

    through(c, item("scope", "packages/app", "packages/web"), source="answer", said=verdict("weaker"))

    assert (c.brief.version, review_valid(c, old, {}), review_valid(c, final(c), {})) == (4, False, True)


def test_changed_and_named_evidence_is_redone_and_the_rest_keeps_its_result():
    c = change(K.CHECK, "check-1")
    c.visual = VisualResult(head="h1", tree="t1", states={"home": 3, "about": 3}, criteria={"AC-1": 1, "AC-2": 2},
                            passed=True, at=NOW)  # fmt: skip
    named = verdict(
        "weaker", qualifies=False, affected=[Affected(item="check:check-1", reason="it reads the home page")]
    )
    through(c, item("visual", "home", "shows Hello"), said=named)
    answer(c, "yes")

    assert (c.visual.states, visual_valid(c, "h1", "t1")) == ({"home": 0, "about": 3}, False)
    assert ([p.answer is None for p in c.checks], next_check(c, {}).id) == ([True, False], "check-1")


def test_a_changed_criterion_redoes_only_the_checks_that_cover_it_and_a_removed_one_none():
    c = change(K.CHECK, "check-1")
    through(c, item("criterion", "AC-1", "greet() trims spaces"), item("criterion", "AC-2", "", remove=True),
            said=verdict("weaker", qualifies=False))  # fmt: skip
    answer(c, "yes")

    assert ([p.criteria for p in c.checks], [p.answer is not None for p in c.checks]) == ([["AC-1"], []], [True, True])
    held = [evidence.check_valid(p.answer.inputs, evidence.check_inputs(c, p, {})) for p in c.checks]
    assert (held, next_check(c, {}).id) == ([False, True], "check-1")  # its recorded AC-1 is an earlier version


@pytest.mark.parametrize(
    ("how", "then"),
    [
        (
            "within",
            lambda c: (c.step.kind, c.outcome, c.intent.hold, c.intent.abandoned_at) == (K.BUILD, None, False, None),
        ),
        ("reshape", lambda c: (c.intent.words, c.intent.hold) == ("Not this way", True)),
        ("stop", lambda c: c.intent.abandoned_at == NOW),
    ],
)
def test_a_declined_candidate_stays_listed_with_his_reason_and_work_goes_his_way(how, then):
    c = change()
    a = through(c, said=verdict("weaker", qualifies=False))

    assert answer(c, how, "Not this way" if how != "stop" else "") == []

    assert (c.amendments, a.state, a.choice, c.amending, c.brief.version) == ([a], "declined", how, None, 3)
    assert (a.declined, then(c)) == ("Not this way" if how != "stop" else "", True)


def test_an_answer_source_declined_within_the_brief_reopens_his_question():
    c = change()
    asked = loop.apply(c, loop.StepResult(exit=Exit.ASK, question=Question(step=K.BUILD, text="Which language?")), NOW)
    q = loop.open_question(asked)
    q.answer = Answer(option=None, text="greet in French too", at=NOW, kind="brief_change")
    asked.outcome = None
    a = through(asked, item("scope", "packages/app", "packages/fr"), source="answer", question=q.id,
                said=verdict("weaker", beyond="it adds a package"))  # fmt: skip

    answer(asked, "within", "English only after all")

    assert (a.state, loop.open_question(asked).id, q.answer) == ("declined", q.id, None)


def test_an_objection_names_only_the_tasks_built_on_the_amendment():
    c = change(task="t2")
    c.plan.tasks[0].done = True  # built before it
    through(c)
    c.plan.tasks[1].done = True

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)

    assert "Built and judged on it since: tasks t2," in loop.open_question(c).text


def test_an_objection_after_a_replan_names_its_tasks_though_their_ids_repeat():
    c = change(task="t2")
    c.plan.tasks[0].done = True  # built before it, in plan v1
    through(c)
    c.plan = Plan(version=2, tasks=[Task(id="t1", title="again", scope=["a.txt"], done=True)])  # replanned, built

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)

    assert "Built and judged on it since: tasks t1," in loop.open_question(c).text


def test_an_objection_pauses_dependent_work_and_a_revert_is_a_new_version():
    c = change()
    a1 = through(c)  # v4: AC-1 reworded alone
    assert amending.objectable(c, "A1") == ""

    amending.objected(c, ObjectionItem(amendment="A1", text="AC-1 was right", at=NOW), NOW)

    q = loop.open_question(c)
    assert ([o.id for o in q.options], "AC-1 was right" in q.text, "can't be undone" in q.text) == (
        ["revert", "keep", "reshape"],
        True,
        True,
    )
    assert loop.next_step(c, NOW) is None  # dependent work waits on his choice
    answer(c, "revert", "AC-1 was right")
    revert = amending.current(c)
    assert (a1.objection, revert.source, revert.reverts, [(i.key, i.old, i.new) for i in revert.items]) == (
        "revert",
        "revert",
        "A1",
        [("AC-1", "greet() trims spaces", AC1)],
    )
    amending.opened(c, revert, RoundPolicy())  # a revert's exact items need no shaper
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)

    assert (revert.level, c.brief.version, c.brief.criteria[0].text) == ("approved", 5, AC1)
    assert [b.criteria[0].text for b in c.brief.approved] == [AC1, "greet() trims spaces", AC1]


def test_a_revert_brings_back_what_was_removed_or_changed_as_it_was():
    c = change()
    c.brief.visual[1].steps = [VisualStep(do="click", target="Team")]
    c.checks[1].visual = True
    c.brief.approved = [
        c.brief.model_copy(deep=True, update={"approved": [], "checks": [p.model_copy(deep=True) for p in c.checks]})
    ]
    shape = lambda b, checks: (  # noqa: E731
        sorted((k.id, k.text) for k in b.criteria), sorted((s.name, s.path, s.expect, str(s.steps)) for s in b.visual),
        sorted((p.id, tuple(p.criteria), tuple(p.steps), p.expect, p.visual) for p in checks),
    )  # fmt: skip
    was = shape(c.brief, c.checks)
    exact = amend_apply.exact
    a1 = amending.start(c, "revert", reason="the owner's wording", now=NOW, items=[
        exact(c, "visual", "home", "shows Hi", path="/hi"),
        exact(c, "check", "check-1", "it says hi", steps=["open /hi"]),
        exact(c, "check", "check-2", "", remove=True), exact(c, "visual", "about", "", remove=True),
        exact(c, "criterion", "AC-2", "", remove=True),
    ])  # fmt: skip
    amending.opened(c, a1, RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge", NOW)
    assert (a1.state, shape(c.brief, c.checks) != was) == ("applied", True)

    amending.objected(c, ObjectionItem(amendment=a1.id, at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)

    assert shape(c.brief, c.checks) == was
    assert [(k.id, k.version) for k in c.brief.criteria] == [("AC-1", 1), ("AC-2", 3)]  # its evidence is stale
    assert [(p.id, p.procedure, p.answer) for p in c.checks] == [("check-1", 3, None), ("check-2", 2, None)]


@pytest.mark.parametrize(("how", "then"), [("keep", (None, False)), ("reshape", ("AC-1 needs reshaping", True))])
def test_keeping_or_reshaping_after_an_objection_leads_where_it_says(how, then):
    c = change()
    through(c)
    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)

    answer(c, how, "AC-1 needs reshaping" if how == "reshape" else "")

    assert (c.amendments[0].objection, c.amending, c.brief.version) == (how, None, 4)
    assert (c.intent.words or None, c.intent.hold) == then


def test_the_chat_reads_back_only_a_candidate_left_for_him_to_adopt():
    c = change()
    through(c)  # applied: already in the brief
    kept = c.amendments[0].model_copy(deep=True, update={"id": "A2", "state": "recorded"})  # a follow-up's candidate
    c.amendments.append(kept)

    (said,) = chat_routes.brief(c)["proposed_wording"]

    assert (said["field"], said["key"], said["old"], said["new"]) == ("criterion", "AC-1", AC1, "greet() trims spaces")


def test_an_objection_at_the_merge_step_takes_a_queued_merge_out():
    c = change(K.MERGE, None)
    through(c)
    before = c.model_copy(deep=True)

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)

    assert (queue.leaving(before, before), queue.leaving(before, c)) == (False, True)


class Records:
    """What a finished Change's record needs of the store: the shared repository and the project's folder in it."""

    def __init__(self, root: Path) -> None:
        self.shared, self.name = DataRepo(root), "shop-site"


def test_levels_survive_a_reload_and_the_finished_record_carries_every_version_and_amendment(tmp_path, shared_repo):
    c = change()
    for b in (c.brief, *c.brief.approved):
        b.decisions = []  # an archived decision needs a minted id
    alone = through(c)  # a qualifying replacement of the generated AC-1
    approved = through(c, item("check", "check-2", "it shows the whole team"), said=verdict("weaker", qualifies=False))
    answer(c, "yes")
    decided = through(c, item("scope", "packages/app", "packages/app only"), source="answer")
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)

    back = store.read("c1")

    assert [(a.id, a.state, a.level, a.version) for a in back.amendments] == [
        (alone.id, "applied", "autonomous", 4), (approved.id, "applied", "approved", 5),
        (decided.id, "applied", "decided", 6),
    ]  # fmt: skip
    assert change_record.save(Records(shared_repo[0]), back, None, NOW) == ""
    (path,) = (shared_repo[0] / "shop-site" / "changes").glob("*-c1.json")
    record = json.loads(path.read_text())
    assert [v["version"] for v in record["versions"]] == [3, 4, 5, 6]
    assert record["versions"][0]["criteria"][0]["text"] == AC1  # the first version as it was approved
    assert [(a["id"], a["level"]) for a in record["amendments"]] == [
        (alone.id, "autonomous"),
        (approved.id, "approved"),
        (decided.id, "decided"),
    ]


def test_a_whitespace_change_is_a_change():
    c = change()
    c.brief.criteria[0].text = "Prints `Hello  Ada`"

    a = through(c, item(text="Prints `Hello Ada`"))

    assert [(i.old, i.new) for i in a.items] == [("Prints `Hello  Ada`", "Prints `Hello Ada`")]
    assert (a.state, c.brief.criteria[0].text) == ("applied", "Prints `Hello Ada`")


def test_a_removed_criterion_brought_back_is_covered_again_by_its_checks():
    c = change()
    through(c, item(key="AC-1", text="", remove=True), said=verdict("weaker", qualifies=False))
    answer(c, "yes")
    assert c.checks[0].criteria == []  # check-1 kept its pass, covering nothing

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)

    assert (c.checks[0].criteria, next_check(c, {}).id) == (["AC-1"], "check-1")  # it reruns


def test_a_check_states_the_criteria_it_covers_and_every_shape_is_shown_where_it_is_judged():
    c = change()
    a = amending.start(c, "worker", reason="a check per criterion", now=NOW)
    wrong = CandidateResult(items=[item("check", "", "it says hi", covers=["AC-9"]), item(covers=["AC-2"])])
    assert amendments.check(wrong, amendments.amendable(c)) == [
        "items: covers AC-9 - not criteria of the brief", "items: covers is only for a check"
    ]  # fmt: skip
    new = item("check", "", "it says hi", steps=["open /hi"], covers=["AC-2"])
    amending.prepared(c, CandidateResult(items=[new]), RoundPolicy(), NOW)
    assert "check:(new) '' -> 'it says hi' (steps: open /hi) (covers AC-2)" in amendments.challenge(
        c, a, Path(), recheck=False
    )
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge", NOW)
    assert "add check: 'it says hi' (steps: open /hi) (covers AC-2)" in loop.open_question(c).text

    answer(c, "yes")

    assert [(p.id, p.criteria, p.steps) for p in c.checks][2] == ("check-3", ["AC-2"], ["open /hi"])


def test_his_approval_of_a_brief_version_is_the_reference_weakening_is_judged_from():
    c = change(K.SHAPE, None)
    c.brief.version = c.brief.challenged = 4  # reshaped after v3

    c = loop.fold(c, [BriefApproval(version=4, at=NOW)], NOW)

    assert (c.brief.reference, amend_apply.reference(c)) == (4, 4)


def test_the_final_review_is_told_the_scope_it_judges_a_constraint_against():
    tree = SimpleNamespace(base="a" * 40, head="b" * 40, changed=())
    c = change(K.REVIEW, None)

    assert "Scope (a constraint): packages/app" in step_input.review(c, None, Path(), tree)
    assert "Scope (a constraint)" not in step_input.review(c, c.plan.tasks[0], Path(), tree)
