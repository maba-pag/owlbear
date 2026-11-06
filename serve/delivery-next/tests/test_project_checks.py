"""A plan step starts only once the owner confirmed the check commands of the packages its brief touches (#968)."""

import json
import subprocess
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    ErrorKind,
    Exit,
    Names,
    Question,
    Step,
    StepKind,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.github.provider import MergeMethod, Repository, Rules
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import answers
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes import step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import Lock, Store, StoreError
from owlbear_delivery_next.workflow_steps import project_checks

ASKED = cause_key(ErrorKind.GATE, StepKind.PLAN, "checks-")
APP, LIB = "packages/app", "packages/lib"


class GitHub:
    def read_repository(self):
        return Repository(
            repository="acme/shop-site",
            url="https://github.com/acme/shop-site",
            default_branch="main",
            methods=(MergeMethod.MERGE,),
            can_push=True,
            delete_branch_on_merge=False,
        )

    def read_rules(self, _repository, _target):
        return Rules(state="known", evidence="rules", allowed_methods=(MergeMethod.MERGE,), strict=False)


class Sessions:
    """The planner and its challenge; each plan's tasks name *checks*."""

    def __init__(self, checks: list[str]) -> None:
        self.checks, self.told = checks, []
        self.scope = ["a.txt"]

    async def __call__(self, cfg):
        self.told.append(cfg)
        if cfg.submit is tools.PLAN:
            checks = [
                c
                for c in cfg.checks
                if c in self.checks or c.partition(" && {\n")[2].removesuffix("\n}") in self.checks
            ]
            payload = tools.PlanResult(tasks=[{"title": "one", "goal": "AC-1", "scope": self.scope, "checks": checks}])
        else:
            payload = tools.ReviewResult(verdict="pass")
        return Run(cfg.session_id, "result", payload, termination=Termination(confirmed=True))

    def planned(self) -> list:
        return [cfg for cfg in self.told if cfg.submit is tools.PLAN]


def entry() -> ProfileEntry:
    return ProfileEntry(state="known", value="npm test", evidence="package.json scripts.test")


def confirmed(prof: Profile, home: str, value: str = "npm test") -> Profile:
    return profile.confirm(prof, f"check:{home}", value, datetime.now(UTC))


def git(repo, *args) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)  # noqa: S603, S607 - fixed test commands


def committed(repo, files: dict[str, str]) -> None:
    for name, text in files.items():
        (repo / name).write_text(text)
    git(repo, "add", *files)
    git(repo, "commit", "-qm", "manifests")


@pytest.fixture
def store(tmp_path, change_repo, monkeypatch) -> Store:
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    return Store(tmp_path / "store")


def made(store: Store, repo, scope: list[str], slug: str = "c1") -> None:
    names = Names(branch=f"owlbear/{slug}", target="main", worktree=str(repo))
    brief = Brief(version=1, approved_version=1, challenged=1, scope=scope)
    store.write(Lock(slug), Change(slug=slug, brief=brief, step=Step(kind=StepKind.PLAN), names=names))


def step(store: Store, repo, slug: str = "c1") -> Change:
    c = store.read(slug)
    runner._step(store, Lock(slug), c, c.step, repo)  # noqa: SLF001
    return store.read(slug)


def answer(store: Store, option: str, text: str = "") -> Change:
    q = next(q for q in store.read("c1").questions if q.answer is None)
    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option=option, text=text))
    return store.fold(Lock("c1"), "c1", datetime.now(UTC))[0]


def asked(c: Change) -> tuple[str, list[str]]:
    """The open question's text and option ids; the step waits on it, and it is an engine decision."""
    q = c.questions[-1]
    assert (c.outcome.exit, q.answer, q.cause.startswith(ASKED)) == (Exit.ASK, None, True)
    return q.text, [o.id for o in q.options]


def sessions(monkeypatch, checks: list[str] | None = None) -> Sessions:
    fake = Sessions(["npm test"] if checks is None else checks)
    monkeypatch.setattr(runner.sdk_adapter, "run", fake)
    return fake


def test_no_profile_is_detected_saved_and_asked_about(store, change_repo, monkeypatch):
    committed(change_repo, {"package.json": json.dumps({"scripts": {"test": "vitest"}})})
    monkeypatch.setattr(project_checks.profile, "provider", lambda *_a: GitHub())
    fake = sessions(monkeypatch)
    made(store, change_repo, ["src"])
    text, options = asked(step(store, change_repo))
    assert (options, fake.told) == (["detected", "typed", "pause"], [])
    assert "`.` (detected: `npm test`)" in text
    assert store.read_profile().entries[profile.REPO].value == "acme/shop-site"


def redetected(repo) -> Profile:
    """``check:.`` confirmed at setup, then detected again with another command."""
    committed(repo, {"package.json": json.dumps({"scripts": {"test": "vitest"}})})
    prof = confirmed(profile.detect(repo, GitHub(), None), ".")
    committed(repo, {"pnpm-lock.yaml": ""})
    return profile.detect(repo, GitHub(), prof)


@pytest.mark.parametrize(
    ("built", "scope", "named", "options"),
    [
        (lambda _r: Profile(entries={"check:.": entry()}), ["src"], "`.` (detected: `npm test`)", ["detected"]),
        (redetected, ["src"], "`.` (detected: `pnpm test`)", ["detected"]),
        (
            lambda _r: confirmed(Profile(entries={f"check:{APP}": entry(), f"check:{LIB}": entry()}), APP),
            [f"{LIB}/x.ts"],
            f"Not confirmed yet: `{LIB}` (detected: `npm test`).",
            ["detected"],
        ),
        (lambda _r: Profile(), ["src"], "`.` (none detected)", []),
        (
            lambda _r: confirmed(Profile(entries={f"check:{APP}": entry()}), APP),
            ["scripts/release.sh"],
            "`.` (none",
            [],
        ),
    ],
    ids=["detected", "re-detected", "other-package", "empty", "outside-packages"],
)
def test_an_unconfirmed_check_asks_the_owner_before_any_session(  # noqa: PLR0913, PLR0917 - the case's parts
    store, change_repo, monkeypatch, built, scope, named, options
):
    store.write_profile(built(change_repo))
    fake = sessions(monkeypatch)
    made(store, change_repo, scope)
    text, ids = asked(step(store, change_repo))
    assert (ids, fake.told) == ([*options, "typed", "pause"], [])
    assert named in text


def test_the_detected_commands_once_confirmed_are_the_plans_and_saved(store, change_repo, monkeypatch, tmp_path):
    store.write_profile(Profile(entries={"check:.": entry()}))
    fake = sessions(monkeypatch)
    made(store, change_repo, ["src"])
    step(store, change_repo)
    answer(store, "detected")
    c = step(store, change_repo)
    (cfg,) = fake.planned()
    assert (c.step.kind, cfg.checks) == (StepKind.BUILD, ("cd . && {\nnpm test\n}",))
    assert f"`{cfg.checks[0]}`" in cfg.message
    plan = tools.PlanResult(tasks=[{"title": "one", "goal": "AC-1", "scope": ["src"], "checks": list(cfg.checks)}])
    assert tools.check_plan(plan, tools.Worktree("a", "a"), cfg.checks, ["src"], cfg.packages) == []
    assert profile.is_confirmed(Store(tmp_path / "store").read_profile().entries["check:."])
    assert any(e.get("event") == "profile-confirmed" and e.get("key") == "check:." for e in store.events("c1"))


def test_one_question_settles_every_package_so_later_changes_plan_without_asking(store, change_repo, monkeypatch):
    store.write_profile(Profile(entries={f"check:{APP}": entry(), f"check:{LIB}": entry()}))
    fake = sessions(monkeypatch)
    made(store, change_repo, [f"{APP}/x.ts"])
    text, _ = asked(step(store, change_repo))
    assert f"`{APP}` (detected: `npm test`), `{LIB}` (detected: `npm test`)" in text
    answer(store, "detected")
    step(store, change_repo)
    made(store, change_repo, [f"{LIB}/y.ts"], "c2")
    assert (step(store, change_repo, "c2").step.kind, len(fake.planned())) == (StepKind.BUILD, 2)


def test_a_confirmed_root_check_covers_a_package_and_its_own_unconfirmed_one_is_withheld(
    store, change_repo, monkeypatch
):
    (change_repo / APP).mkdir(parents=True)
    committed(
        change_repo,
        {
            "Makefile": "check:\n\t@pwd\n",
            f"{APP}/package.json": json.dumps({"scripts": {"test": "vitest"}}),
        },
    )
    prof = Profile(
        entries={
            f"check:{APP}": ProfileEntry(state="known", value="make check", evidence="detected package check"),
            f"install:{APP}": ProfileEntry(state="known", value="npm install", evidence="package.json"),
        }
    )
    store.write_profile(confirmed(prof, ".", "make check"))
    fake = sessions(monkeypatch, ["make check"])
    fake.scope = [APP]
    made(store, change_repo, [f"{APP}/x.ts"])
    change = step(store, change_repo)
    assert change.step.kind == StepKind.BUILD
    (cfg,) = fake.planned()
    assert cfg.checks == ("cd . && {\nmake check\n}",)
    plan = tools.PlanResult(
        tasks=[
            {
                "title": "one",
                "goal": "AC-1",
                "scope": [APP],
                "checks": [f"cd {APP} && make check"],
            }
        ]
    )
    assert tools.check_plan(plan, tools.Worktree("a", "a"), cfg.checks, [APP], cfg.packages)
    parts = step_input.session(change, store.read_profile(), change_repo, {})
    assert parts.checks == cfg.checks
    assert f"- `{parts.checks[0]}`" in parts.message
    ran = subprocess.run(  # noqa: S603 - the fixture's emitted make command
        ["/bin/sh", "-c", parts.checks[0]],
        cwd=change_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ran.stdout.strip() == str(change_repo)


def test_typed_commands_are_read_back_and_saved_only_when_the_owner_saves_them(
    store, change_repo, monkeypatch, tmp_path
):
    store.write_profile(Profile(entries={f"check:{APP}": entry(), f"check:{LIB}": entry()}))
    before = store.read_profile()
    fake = sessions(monkeypatch, ["b"])
    made(store, change_repo, [f"{APP}/x.ts"])
    step(store, change_repo)
    answer(store, "typed", f"{APP}: a")
    text, options = asked(step(store, change_repo))
    assert (f"- `{APP}`: `a`" in text, options) == (True, ["save", "again", "pause"])
    answer(store, "again")
    asked(step(store, change_repo))
    answer(store, "typed", ".: b\npackages/typo: c")
    text, options = asked(step(store, change_repo))
    assert ("Not understood: packages/typo: c" in text, options) == (True, ["again", "pause"])
    answer(store, "again")
    asked(step(store, change_repo))
    assert (Store(tmp_path / "store").read_profile(), fake.told) == (before, [])
    answer(store, "typed", ".: b")
    text, _ = asked(step(store, change_repo))
    assert ("- `.`: `b`" in text, Store(tmp_path / "store").read_profile()) == (True, before)
    answer(store, "save")
    assert step(store, change_repo).step.kind == StepKind.BUILD
    root = Store(tmp_path / "store").read_profile().entries["check:."]
    assert (root.value, profile.is_confirmed(root), fake.planned()[0].checks) == ("b", True, ("cd . && {\nb\n}",))
    made(store, change_repo, [f"{LIB}/y.ts"], "c2")
    assert step(store, change_repo, "c2").step.kind == StepKind.BUILD


def test_a_paused_answer_plans_nothing_and_is_never_delivered(store, change_repo, monkeypatch):
    store.write_profile(Profile(entries={"check:.": entry()}))
    fake = sessions(monkeypatch)
    made(store, change_repo, ["src"])
    step(store, change_repo)
    c = answer(store, "pause")
    assert (c.intent.paused_at is not None, c.questions[-1].delivered_at, fake.told) == (True, None, [])


def test_an_unpublished_profile_is_logged_and_the_planner_starts(store, change_repo, monkeypatch, tmp_path):
    store.write_profile(Profile(entries={"check:.": entry()}))
    write = store.write_profile
    monkeypatch.setattr(store, "write_profile", lambda prof, **kw: write(prof, **kw) or "not published: offline")
    fake = sessions(monkeypatch)
    made(store, change_repo, ["src"])
    step(store, change_repo)
    answer(store, "detected")
    step(store, change_repo)
    logged = [e["notice"] for e in store.events("c1") if e.get("event") == "profile-unpublished"]
    assert (logged, len(fake.planned())) == (["not published: offline"], 1)
    assert profile.is_confirmed(Store(tmp_path / "store").read_profile().entries["check:."])


def test_a_failed_save_raises_before_any_session_and_the_rerun_saves(store, change_repo, monkeypatch):
    store.write_profile(Profile(entries={"check:.": entry()}))
    fake = sessions(monkeypatch)
    made(store, change_repo, ["src"])
    step(store, change_repo)
    answer(store, "detected")
    write = store.write_profile

    def broken(_prof, **_kw):
        msg = "profile: disk said no"
        raise StoreError(msg)

    monkeypatch.setattr(store, "write_profile", broken)
    with pytest.raises(StoreError, match="disk said no"):
        step(store, change_repo)
    assert fake.told == []
    monkeypatch.setattr(store, "write_profile", write)
    assert step(store, change_repo).step.kind == StepKind.BUILD
    assert profile.is_confirmed(store.read_profile().entries["check:."])


def test_the_question_is_an_engine_decision_the_changes_page_answers(store, change_repo, monkeypatch):
    store.write_profile(Profile(entries={"check:.": entry()}))
    sessions(monkeypatch)
    made(store, change_repo, ["src"])
    c = step(store, change_repo)
    q = c.questions[-1]
    assert answers.shown(q, [])["ordinary"] is False
    item = answers.answer_item(store, c, answers.AnswerBody(question=q.id, option="detected"))
    assert isinstance(item, AnswerItem)
    labels = " ".join(o.label for o in q.options)
    assert ("every task" in labels, "before anything is saved" in labels) == (True, True)


@pytest.mark.parametrize("question", ["absent", "unrelated", "checks"])
def test_only_a_real_checks_question_needs_the_profile_to_settle(store, change_repo, question):
    store.write_profile(Profile(entries={"check:.": entry()}))
    made(store, change_repo, ["src"])
    c = store.read("c1")
    if question == "checks":
        c = step(store, change_repo)  # the real planner prerequisite asks, even without a PR
        asked(c)
    elif question == "unrelated":
        c = loop.apply(
            c,
            loop.StepResult(exit=Exit.ASK, question=Question(step=StepKind.PLAN, text="Which language?")),
            datetime.now(UTC),
        )
    before = c.model_copy(deep=True)
    malformed = '{"format": 5, "entries":'
    (store.root / "profile.json").write_text(malformed)
    assert c.names.pr is None
    if question == "checks":
        with pytest.raises(StoreError):
            project_checks.settle(store, c, datetime.now(UTC))
    else:
        project_checks.settle(store, c, datetime.now(UTC))
    assert c == before
    assert (store.root / "profile.json").read_text() == malformed


def test_a_change_already_asking_plans_once_another_change_s_answer_settles_the_checks(
    store, change_repo, monkeypatch, tmp_path
):
    store.write_profile(Profile(entries={"check:.": entry()}))
    sessions(monkeypatch)
    for slug in ("c1", "c2"):
        made(store, change_repo, ["src"], slug)
        asked(step(store, change_repo, slug))
    answer(store, "detected")
    step(store, change_repo)
    host = Host(store, tmp_path, spawn=lambda _slug: None)
    assert host._one("c2", datetime.now(UTC))  # noqa: SLF001 - one pass: planning is due without another answer
    c = store.read("c2")
    q = c.questions[-1]
    assert (q.answer.option, loop.next_step(c, datetime.now(UTC))) == ("settled", c.step)
    late = answers.answer_item(store, c, answers.AnswerBody(question=q.id, option="detected"))
    assert late == (409, f"question {q.id} is not open")
