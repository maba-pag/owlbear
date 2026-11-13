"""A brief amendment on one Change (TD-185): what applies alone, what asks the owner, what it voids, what resumes."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import evidence
from owlbear_delivery_next.change_contracts.amend_tools import (
    Action,
    Affected,
    CandidateItem,
    CandidateResult,
    VerdictResult,
)
from owlbear_delivery_next.change_contracts.amendment_records import AmendedItem
from owlbear_delivery_next.change_contracts.decision_records import BriefDecision, DecisionBaseline
from owlbear_delivery_next.change_contracts.env_records import Environment
from owlbear_delivery_next.change_contracts.evidence import next_check, review_valid, visual_valid
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, BriefApproval, IntentItem, ObjectionItem
from owlbear_delivery_next.change_contracts.models import (
    VISUAL,
    Answer,
    Brief,
    Change,
    Criterion,
    Exit,
    Inputs,
    PersonCheck,
    Plan,
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
from owlbear_delivery_next.state_store import briefs, change_record
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import check, queue

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


@pytest.mark.parametrize(
    "said",
    [
        verdict(qualifies=False),  # equivalent, but not shown by independent evidence
        verdict(build_only=True),  # only the failing build motivates it
        verdict(tightening="AC-1 now also trims tabs: one more test"),
        verdict(widens=True),
        verdict("weaker", qualifies=False),
        verdict("unsure", qualifies=False),
    ],
    ids=["unproven", "build-only", "tightening", "widening", "weaker", "unsure"],
)
def test_a_candidate_that_does_not_qualify_asks_the_owner(said):
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

    assert [p.criteria for p in c.checks] == [p.criteria for p in c.brief.approved[-1].checks] == [["AC-1"], []]
    assert [p.answer is not None for p in c.checks] == [True, True]
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
    old = c.brief.approved[0].model_dump()
    a1 = amending.start(c, "worker", reason="the home page greets after a click", now=NOW)
    swapped = [item("check", "check-1", "it says hi", actions=[]), item("visual", "home", "Hi", visual=True)]
    assert amendments.check(CandidateResult(items=swapped), amendments.amendable(c)) == [
        "items: actions are only for a visual state", "items: visual is only for a check"
    ]  # fmt: skip
    clicks = [Action(do="type", target="Name", text="Ada"), Action(do="click", target="Greet")]
    candidate = [
        item("visual", "home", "shows Hello Ada", path="/hi", actions=clicks),
        item("check", "check-1", "it says hi", steps=["open /hi"], visual=True),
        item("check", "check-2", "", remove=True),
        item("visual", "about", "", remove=True),
        item("criterion", "AC-1", "", remove=True),
    ]
    amending.prepared(c, CandidateResult(items=candidate), RoundPolicy(), NOW)
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge", NOW)
    text = loop.open_question(c).text
    assert 'actions: type "Ada" into "Name"; click "Greet"' in text
    assert "(judged by look)" in text
    answer(c, "yes")
    assert (a1.state, [k.id for k in c.brief.criteria], [p.id for p in c.checks]) == ("applied", ["AC-2"], ["check-1"])
    assert [(s.name, s.path, s.expect, s.steps) for s in c.brief.visual] == [
        (
            "home",
            "/hi",
            "shows Hello Ada",
            [VisualStep(do="type", target="Name", text="Ada"), VisualStep(do="click", target="Greet")],
        )
    ]
    assert (c.checks[0].criteria, c.checks[0].steps, c.checks[0].visual) == ([], ["open /hi"], True)

    amending.objected(c, ObjectionItem(amendment=a1.id, at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)

    assert sorted((k.id, k.text, k.version) for k in c.brief.criteria) == [("AC-1", AC1, 2), ("AC-2", AC2, 2)]
    assert sorted((s.name, s.path, s.expect, [(x.do, x.target) for x in s.steps]) for s in c.brief.visual) == [
        ("about", "/about", "shows the team", [("click", "Team")]),
        ("home", "/", "shows Hallo", []),
    ]
    assert [(p.id, p.criteria, p.steps, p.expect, p.visual) for p in c.checks] == [
        ("check-1", ["AC-1"], ["open /"], "it greets", False),
        ("check-2", ["AC-2"], ["open /about"], "it shows the team", True),
    ]
    assert [(p.id, p.procedure, p.answer) for p in c.checks] == [("check-1", 3, None), ("check-2", 2, None)]
    assert (next_check(c, {}).id, c.brief.approved[0].model_dump()) == ("check-1", old)


@pytest.mark.parametrize(("how", "then"), [("keep", (None, False)), ("reshape", ("AC-1 needs reshaping", True))])
def test_keeping_or_reshaping_after_an_objection_leads_where_it_says(how, then):
    c = change()
    through(c)
    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)

    answer(c, how, "AC-1 needs reshaping" if how == "reshape" else "")

    assert (c.amendments[0].objection, c.amending, c.brief.version) == (how, None, 4)
    assert (c.intent.words or None, c.intent.hold) == then


class Records:
    """What a finished Change's record needs of the store: the shared repository and the project's folder in it."""

    def __init__(self, root: Path) -> None:
        self.shared, self.name = DataRepo(root), "shop-site"


def test_amendment_authority_reference_and_history_survive_reload(tmp_path, shared_repo):
    c = change()
    for b in (c.brief, *c.brief.approved):
        b.decisions = []  # an archived decision needs a minted id
    alone = through(c)  # a qualifying replacement of the generated AC-1
    assert (alone.state, alone.level, alone.version, c.brief.version, c.brief.approved_version) == (
        "applied",
        "autonomous",
        4,
        4,
        4,
    )
    assert ([k.text for k in c.brief.criteria], c.brief.specified) == (["greet() trims spaces", AC2], ["AC-2"])
    assert (c.brief.reference, amend_apply.reference(c), [b.version for b in c.brief.approved]) == (None, 3, [3, 4])
    assert (c.amending, c.step.kind, c.step.task, c.outcome) == (None, K.BUILD, "t1", None)

    approved = amending.start(c, "worker", reason="AC-1 is too strict", now=NOW)
    amending.prepared(c, CandidateResult(items=[item(text="greet() keeps the name")]), RoundPolicy(), NOW)
    told = amendments.challenge(c, approved, Path(), recheck=False)
    assert "## The reference version v3" in told
    assert f"- A1 (v4, autonomous): criterion:AC-1 '{AC1}' -> 'greet() trims spaces'" in told
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)
    assert (approved.state, amend_apply.reference(c), c.brief.version, options(c)) == ("proposed", 3, 4, ASKS)
    assert [a.id for a in amend_apply.since(c)] == ["A1"]
    answer(c, "yes")
    assert (approved.state, approved.level, approved.choice, c.brief.version, c.brief.reference) == (
        "applied",
        "approved",
        "yes",
        5,
        5,
    )
    assert (amend_apply.since(c), "AC-1" in c.brief.specified) == ([], True)
    decided = through(c, item("scope", "packages/app", "packages/app only"), source="answer")
    assert (decided.state, decided.level, options(c), c.brief.reference) == ("applied", "decided", [], 6)
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
    assert (c.checks[0].criteria, c.checks[0].answer is not None) == ([], True)

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)

    assert (c.checks[0].criteria, next_check(c, {}).id) == (["AC-1"], "check-1")


def test_a_check_states_the_criteria_it_covers_and_every_shape_is_shown_where_it_is_judged():
    c = change()
    a = amending.start(c, "worker", reason="a check per criterion", now=NOW)
    wrong = CandidateResult(items=[item("check", "", "it says hi", covers=["AC-9"]), item(covers=["AC-2"])])
    assert amendments.check(wrong, amendments.amendable(c)) == [
        "items: covers AC-9 - not criteria the brief keeps or the candidate adds", "items: covers is only for a check"
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


@pytest.mark.parametrize(
    "candidate", [item("visual", "home", "shows Hello"), item("check", "check-1", "it greets twice")]
)
def test_a_qualifying_replacement_of_a_generated_visual_state_or_person_check_applies_alone(candidate):
    c = change()
    a = through(c, candidate)

    assert (a.state, a.level, c.brief.version) == ("applied", "autonomous", 4)

    c = change()
    c.brief.specified.append(f"screen:{candidate.key}" if candidate.field == "visual" else f"check:{candidate.key}")
    through(c, candidate)

    assert (c.brief.version, options(c)) == (3, ASKS)  # the owner's own asks him


def test_the_challenger_names_affected_evidence_the_way_the_brief_does():
    c = change()
    named = lambda *x: verdict(affected=[Affected(item=i, reason="it reads the home page") for i in x])  # noqa: E731

    assert amendments.check(named("visual:home", "check:check-9"), amendments.amendable(c)) == [
        f"affected: {x} is no visual state or person check of the brief - name it screen:<state name> or "
        "check:<check id>" for x in ("visual:home", "check:check-9")
    ]  # fmt: skip
    assert amendments.check(named("screen:home", "check:check-2"), amendments.amendable(c)) == []


def test_a_check_cannot_cover_a_criterion_the_same_candidate_removes():
    c = change()
    removes = CandidateResult(
        items=[item(text="", remove=True), item("check", "check-1", "it greets", covers=["AC-1"])]
    )

    assert amendments.check(removes, amendments.amendable(c)) == [
        "items: covers AC-1 - not criteria the brief keeps or the candidate adds"
    ]


def test_removing_the_person_check_that_stopped_goes_on_to_the_next_check():
    c = change(K.CHECK, "check-1")
    through(c, item("check", "check-1", "", remove=True), said=verdict("weaker", qualifies=False))
    answer(c, "yes")

    assert ([p.id for p in c.checks], c.step.kind) == (["check-2"], K.FOLLOW)


@pytest.mark.parametrize("intent", ["change", "abandon"])
def test_reshaping_or_stopping_ends_a_waiting_amendment_and_a_late_yes_approves_nothing(intent):
    c = change()
    through(c, said=verdict("weaker", qualifies=False))
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [IntentItem(at=NOW, intent=intent, text="greet in French")], NOW)
    c.brief.version = 4  # the shaper's next draft
    dropped: list = []
    c, _ = loop.schedule(c, [AnswerItem(question=q.id, option="yes", at=NOW)], NOW, dropped=dropped)

    assert [why for _, why in dropped] == [f"question {q.id}: the amendment it asks about has ended"]
    assert (c.amendments[0].state, c.amending, c.brief.approved_version) == ("declined", None, 3)


def test_removing_every_visual_state_while_the_visual_check_stopped_goes_on_to_the_next_check():
    c = change(K.CHECK, VISUAL)
    gone = [item("visual", s.name, "", remove=True) for s in c.brief.visual]
    through(c, item("ui", "", "false"), *gone, said=verdict("weaker", qualifies=False))
    answer(c, "yes")

    assert (c.brief.visual, c.step.kind) == ([], K.FOLLOW)


@pytest.mark.parametrize("path", ["/etc", "../app", "~/app"])
def test_a_scope_amendment_stays_inside_the_repository(path):
    c = change()
    outside = CandidateResult(items=[item("scope", "packages/app", path)])

    assert amendments.check(outside, amendments.amendable(c)) == [
        f'items: scope {path} is not repository-relative - e.g. "packages/app"'
    ]


@pytest.mark.parametrize(("field", "key"), [("criterion", "AC-1"), ("check", "check-1")])
def test_an_item_added_after_a_removal_never_takes_its_id_so_reverting_the_removal_keeps_both(field, key):
    c = change()
    through(c, item(field, key, "", remove=True), said=verdict("weaker", qualifies=False))
    answer(c, "yes")
    through(c, item(field, "", "a new one", steps=["open /new"]), said=verdict("weaker", qualifies=False))
    answer(c, "yes")
    added = c.amendments[1].items[0].key

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-3", NOW)

    held = {k.id: k.text for k in c.brief.criteria} | {p.id: p.expect for p in c.checks}
    assert (added != key, held[added], key in held) == (True, "a new one", True)


@pytest.mark.parametrize("objection", [False, True])
def test_reshaping_an_amendment_at_the_merge_step_leaves_it_so_the_pr_never_merges(objection):
    c = change(K.MERGE, None)
    through(c, said=verdict() if objection else verdict("weaker", qualifies=False))
    if objection:
        amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
        assert amending.owned(loop.open_question(c)) == ("A1", "objection")
    before, q = c.model_copy(deep=True), loop.open_question(c)

    c, _ = loop.schedule(c, [AnswerItem(question=q.id, option="reshape", text="greet in French", at=NOW)], NOW)

    assert (c.step.kind, c.intent.hold, queue.leaving(before, c)) == (K.SHAPE, False, True)


@pytest.mark.parametrize("intent", ["change", "abandon"])
def test_a_yes_folded_after_reshaping_or_stopping_in_the_same_batch_approves_nothing(intent):
    c = change()
    through(c, said=verdict("weaker", qualifies=False))
    q, dropped = loop.open_question(c), []
    items = [IntentItem(at=NOW, intent=intent, text="greet in French"), AnswerItem(question=q.id, option="yes", at=NOW)]

    c, _ = loop.schedule(c, items, NOW, dropped=dropped)

    assert [why for _, why in dropped] == [f"question {q.id}: the amendment it asks about has ended"]
    assert (c.amendments[0].state, c.amending, c.brief.version) == ("declined", None, 3)


def test_repeated_objections_remove_a_queued_merge_each_time():
    c = change(K.MERGE, None)
    through(c)
    before = c.model_copy(deep=True)
    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
    assert (queue.leaving(before, before), queue.leaving(before, c)) == (False, True)
    answer(c, "keep")
    before = c.model_copy(deep=True)

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW.replace(hour=10)), NOW)

    assert queue.leaving(before, c)


def test_a_version_approved_before_checks_were_kept_with_it_still_reverts_a_check_as_it_was():
    c = change()
    c.brief.approved[0].checks = []  # approved by an older build
    was = [(p.id, p.steps, p.expect, p.criteria) for p in c.checks]
    changed = item("check", "check-1", "it greets twice", steps=["open /twice"])
    through(c, changed, said=verdict("weaker", qualifies=False))
    answer(c, "yes")

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-2", NOW)

    assert [(p.id, p.steps, p.expect, p.criteria) for p in c.checks] == was


def test_recorded_candidates_read_back_their_complete_shape():
    c = change()
    through(c)
    recorded = c.amendments[0].model_copy(deep=True, update={"id": "A2", "state": "recorded"})
    steps = [VisualStep(do="click", target="Team")]
    recorded.items += [
        AmendedItem(field="visual", new="shows the team", path="/team", actions=steps),
        AmendedItem(field="check", new="it greets", steps=["open /"], covers=["AC-1"], visual=True),
        AmendedItem(field="decision", new="SQLite", question="Which store?"),
    ]
    c.amendments.append(recorded)

    criterion, *said = chat_routes.brief(c)["proposed_wording"]

    assert (criterion["field"], criterion["key"], criterion["old"], criterion["new"]) == (
        "criterion",
        "AC-1",
        AC1,
        "greet() trims spaces",
    )
    assert [(x["path"], x["actions"], x["steps"], x["covers"], x["visual"], x["question"]) for x in said] == [
        ("/team", [{"do": "click", "target": "Team", "text": ""}], [], [], None, ""),
        ("", None, ["open /"], ["AC-1"], True, ""),
        ("", None, [], [], None, "Which store?"),
    ]


def test_a_brief_an_amendment_removed_a_criterion_from_is_read_back_and_saved_again_by_place(tmp_path):
    store = Store(tmp_path / "store")
    first = {"title": "Greet", "outcome": "greet(name) greets the person", "scope": ["packages/app"],
             "criteria": [AC1, AC2]}  # fmt: skip
    code, out = briefs.save_brief(store, first | {"specified": ["AC-2"], "person_checks": [
        {"name": "check-2", "steps": ["open /about"], "expect": "it shows the team", "covers": ["AC-2"]}]})  # fmt: skip
    assert code == 200
    with store.lock(out["slug"]) as lock:  # what removing AC-1 by an amendment, then reshaping, leaves
        c = store.read(out["slug"])
        c.brief.criteria = c.brief.criteria[1:]
        store.write(lock, c)

    code, _ = briefs.save_visual(store, {"change": out["change"], "ui": False})
    read = chat_routes.brief(c := store.read(out["slug"]))
    more = first | {"change": out["change"], "criteria": [AC2, "Says Hi in French"], "specified": read["specified"]}
    code_more, _ = briefs.save_brief(store, more | {"person_checks": [
        {"name": "check-2", "steps": ["open /about"], "expect": "it shows the team", "covers": p["covers"]}
        for p in read["person_checks"]]})  # fmt: skip
    after = store.read(out["slug"])

    assert (code, read["specified"], [p["covers"] for p in read["person_checks"]]) == (200, ["AC-1"], [["AC-1"]])
    assert [(k.id, k.version) for k in c.brief.criteria] == [("AC-2", 1)]
    assert (code_more, [k.id for k in after.brief.criteria], after.checks[0].criteria) == (
        200,
        ["AC-2", "AC-3"],
        ["AC-2"],
    )
    assert after.brief.specified == ["AC-2"]


def test_a_yes_folded_with_the_pr_seen_merged_approves_nothing_and_the_amendment_moves_on_whole():
    c = change(K.MERGE, None)
    through(c, said=verdict("weaker", qualifies=False))
    q, dropped, before = loop.open_question(c), [], c.model_copy(deep=True)

    c, step = loop.schedule(c, [AnswerItem(question=q.id, option="yes", at=NOW)], NOW, "merged", dropped=dropped)

    (why,) = [why for _, why in dropped]
    assert why == f"question {q.id}: the PR merged first; the amendment goes on as a new Change"
    assert (c.amendments, c.amending, c.brief) == (before.amendments, before.amending, before.brief)
    assert step.kind == K.CLEANUP  # where the amendment step hands it, candidate and all, to a new Change


@pytest.mark.parametrize("how", ["changed", "named"])
def test_a_check_the_amendment_changes_or_names_no_longer_covers_a_criterion_it_removed(how):
    c = change()
    removal = item("criterion", "AC-2", "", remove=True)
    weaker = verdict("weaker", qualifies=False)
    if how == "changed":
        through(c, removal, item("check", "check-2", "it shows the whole team"), said=weaker)
    else:
        named = [Affected(item="check:check-2", reason="it reads the team page")]
        through(c, removal, said=verdict("weaker", qualifies=False, affected=named))
    answer(c, "yes")

    assert [p.criteria for p in c.checks] == [p.criteria for p in c.brief.approved[-1].checks] == [["AC-1"], []]


def test_a_criterion_added_after_an_amendment_removed_one_never_takes_an_id_an_approved_version_held(tmp_path):
    store = Store(tmp_path / "store")
    first = {"title": "Greet", "outcome": "greet(name) greets the person", "scope": ["packages/app"],
             "criteria": [AC1, AC2]}  # fmt: skip
    code, out = briefs.save_brief(store, first)
    with store.lock(out["slug"]) as lock:  # what an approved amendment removing AC-2 leaves
        c = store.read(out["slug"])
        c.brief.approved = [c.brief.model_copy()]
        c.brief.criteria = c.brief.criteria[:1]
        store.write(lock, c)

    code_more, _ = briefs.save_brief(store, first | {"change": out["change"], "criteria": [AC1, "Says Hi in French"]})

    assert (code, code_more) == (200, 200)
    assert [k.id for k in store.read(out["slug"]).brief.criteria] == ["AC-1", "AC-3"]  # a revert brings AC-2 back


def test_a_scope_amendment_binds_every_person_check_to_the_new_scope():
    c = change(K.CHECK, None)
    before = {"packages/app/greet.py": "f1"}
    for p in c.checks:
        p.paths = evidence.coverage(c)
        p.answer.inputs.paths = before
    assert next_check(c, before) is None

    through(c, item("scope", "", "packages/web"), said=verdict("weaker", qualifies=False))
    answer(c, "yes")

    assert [p.paths for p in c.checks] == [["a.txt", "b.txt", "packages/app", "packages/web"]] * 2
    assert next_check(c, before | {"packages/web/team.py": "f2"}).id == "check-1"  # a change there redoes them


def test_a_check_answer_never_settles_past_his_open_objection():
    c = change()
    through(c)
    c.step = Step(kind=K.CHECK, task="check-1")
    p = c.checks[0]
    p.answer = Answer(at=NOW, passed=True, inputs=evidence.check_inputs(c, p, {}))
    c.env = Environment(check="check-1", command="npm run x", directory=".", ready_url="http://127.0.0.1:{port}/")
    assert check.action(c, live=True, paths={}) == "settle"

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)

    assert check.action(c, live=True, paths={}) == "dispose"  # his answer to the objection comes first


def test_a_new_check_covers_just_the_criterion_its_candidate_adds():
    c = change()
    a = amending.start(c, "worker", reason="French needs its own check", now=NOW)
    french = item("criterion", "", "Says Bonjour")
    one, two = (item("check", "", "it says bonjour", steps=["open /fr"], covers=[k]) for k in ("AC-3", "AC-4"))
    ids = ", ".join(f"AC-{n}" for n in range(3, 13))
    assert f"Criteria the candidate adds take, in the order listed, the ids {ids}" in amendments.prepare(c, a, Path())
    assert amendments.check(CandidateResult(items=[two, french]), amendments.amendable(c)) == [
        "items: covers AC-4 - not criteria the brief keeps or the candidate adds"
    ]  # it adds one criterion

    amending.prepared(c, CandidateResult(items=[one, french]), RoundPolicy(), NOW)
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge", NOW)
    answer(c, "yes")

    assert [(p.id, p.criteria) for p in c.checks][-1] == ("check-3", ["AC-3"])
    assert [k.id for k in c.brief.criteria] == ["AC-1", "AC-2", "AC-3"]


def test_reverting_a_decision_amendment_another_amended_since_restores_the_decision_in_place():
    c = change()
    for words in ("SQLite and Postgres", "Postgres only"):
        through(c, item("decision", c.brief.decisions[0].id, words), said=verdict("weaker", qualifies=False))
        answer(c, "yes")
    latest = c.brief.decisions[0].id

    amending.objected(c, ObjectionItem(amendment="A1", at=NOW), NOW)
    answer(c, "revert")
    amending.opened(c, amending.current(c), RoundPolicy())
    amending.judged(c, verdict("weaker", qualifies=False), "c1-challenge-3", NOW)

    assert [(d.question, d.answer, d.replaces) for d in c.brief.decisions] == [("Which store?", "SQLite only", latest)]


def test_two_new_decisions_with_the_same_answer_keep_their_own_ids():
    c = change()
    one, two = (item("decision", "", "Yes", question=q) for q in ("Keep the cache?", "Keep the log?"))
    through(c, one, two, said=verdict("weaker", qualifies=False))
    answer(c, "yes")

    assert len({d.id for d in c.brief.decisions}) == 3


def test_a_candidate_may_not_grow_the_brief_past_a_shaped_briefs_limits():
    full = [item("criterion", "", f"Says hello in language {n}") for n in range(1, 9)]
    last = item("check", "", "it greets", steps=["open /"], covers=["AC-10"])
    assert amendments.check(CandidateResult(items=[*full, last]), amendments.amendable(change())) == []

    adds = [item("criterion", "", f"Says hello in language {n}") for n in range(1, 10)]
    allowed = amendments.amendable(change())

    assert amendments.check(CandidateResult(items=adds), allowed) == [
        "items: the brief would hold 11 criteria, more than 10 - merge or remove some"
    ]
    assert amendments.check(CandidateResult(items=[*adds, item("criterion", "AC-1", "", remove=True)]), allowed) == []
