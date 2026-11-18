"""Configuration approval through the worker Gate, owner answers, repairs and the Changes page."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from owlbear_quality import ledger
from owlbear_quality import run as lint_run
from owlbear_quality.inspect import added
from playwright.sync_api import expect

from owlbear_delivery_next.change_contracts import approval_tools, curation_tools, exception_tools, tools
from owlbear_delivery_next.change_contracts.decision_records import Decision as ChangeDecision
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import answer_kinds, loop, quality, stuck, worktree
from owlbear_delivery_next.local_system import lint
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter, session_result, step_answers
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import approvals, exception_workers, exceptions, repair_copy, session_choice
from owlbear_delivery_next.workflow_steps.step_repair import _apply as apply_repair
from owlbear_delivery_next.workflow_steps.step_repair import _proven as prove_repair

from .test_approval_view import big
from .test_change_page_view import opened

NOW = datetime(2026, 11, 17, 21, tzinfo=UTC)
MANIFEST = '[project]\nname = "fixture"\nversion = "1"\ndependencies = []\n\n[tool.ruff]\nline-length = 100\n'
WHY = "The new package needs this lint configuration to meet the approved work."
COMMANDS = (("/usr/bin/true",),)


def commit(path: Path, files: dict[str, str | bytes]) -> str:
    for name, content in files.items():
        at = path / name
        at.parent.mkdir(parents=True, exist_ok=True)
        at.write_bytes(content if isinstance(content, bytes) else content.encode())
    worktree.git(path, "add", "--", *files)
    worktree.git(path, "commit", "-qm", "fixture work")
    return worktree.head(path)


@pytest.fixture
def project(change_repo: Path) -> tuple[Path, Change, str]:
    base = commit(change_repo, {"pyproject.toml": MANIFEST})
    worktree.git(change_repo, "branch", "-f", "main", base)
    c = Change(
        slug="c1",
        names=Names(branch="owlbear/c1", target="main", worktree=str(change_repo)),
        brief=Brief(version=1, approved_version=1, challenged=1, scope=["."]),
        plan=Plan(tasks=[Task(id="t1", title="Build", scope=["."], base=base)]),
        step=Step(kind=StepKind.BUILD, task="t1", session="builder"),
    )
    return change_repo, c, base


def gate(path: Path, c: Change, since: str, store: Store | None = None, *, curated: bool = False) -> Gate:
    store = store or Store(path.parent / "store")
    judge = exception_workers.Asked(store, Lock(c.slug), lambda: c, path)
    cfg = sdk_adapter.Session(
        kind=StepKind.BUILD,
        worktree=path,
        session_id="builder",
        message="Build",
        resume=False,
        policy=Policy(path),
        observe=lambda: worktree.observe(path, c.names.target, since),
        checks=(),
        lint_commands=COMMANDS,
        quality=lambda: quality.check(c, path, COMMANDS, folder=store.root),
        helpers=(judge.helper(),),
        submit=curation_tools.TEST_CURATION if curated else tools.SUBMIT,
        role="test-curator" if curated else "builder",
    )
    run = Run("builder", model_check="verified", termination=Termination(confirmed=True))
    return Gate(cfg, run, lambda **_e: None, lambda: None)


def submit(g: Gate) -> tuple[str, bool]:
    return g.call(tools.SUBMIT, {"summary": "Built", "checks": []})


def request(path: Path, c: Change, since: str, store: Store | None = None) -> Change:
    store = store or Store(path.parent / "store")
    g = gate(path, c, since, store)
    assert g.call(approval_tools.REQUEST, {"why": WHY})[1]
    result = session_result.to_result(g.run, c.step.kind, NOW)
    result = approvals.Requests(store, COMMANDS).requested(c, g.run, path, result)
    assert result.exit == Exit.ASK
    return loop.apply(c, result, NOW)


def test_dependency_only_is_accepted_but_configuration_needs_the_exact_approval(project, tmp_path) -> None:
    path, c, base = project
    dependency = MANIFEST.replace("dependencies = []", 'dependencies = ["requests"]')
    commit(path, {"pyproject.toml": dependency})
    assert submit(gate(path, c, base))[1]
    configuration = dependency.replace("100", "110")
    commit(path, {"pyproject.toml": configuration})
    refused, ok = submit(gate(path, c, base))
    assert not ok
    assert "pyproject.toml" in refused
    assert "request_approval" in refused
    c = request(path, c, base)
    q = c.questions[-1]
    assert "-line-length = 100" in q.text
    assert "+line-length = 110" in q.text
    assert WHY in q.text
    c = loop.fold(c, [AnswerItem(question=q.id, option="approve", at=NOW)], NOW)
    assert answer_kinds.delivered_next(c).id == q.id
    store = Store(tmp_path / "store")
    store.write(Lock(c.slug), c)
    answered, _, _, resume = session_choice.opening(store, Lock(c.slug), c, c.plan.tasks[0])
    assert resume
    assert c.step.session == "builder"
    assert "Approve: resume the step" in step_answers.answer(answered)
    assert submit(gate(path, c, base))[1]
    commit(path, {"pyproject.toml": configuration.replace("110", "120")})
    assert not submit(gate(path, c, base))[1]


def test_configuration_still_refuses_after_the_five_lint_refusals(project, monkeypatch) -> None:
    path, c, base = project
    commit(path, {"pyproject.toml": MANIFEST.replace("100", "110")})
    monkeypatch.setattr(lint_run, "run", lambda *_: lint_run.Outcome("failed", "a real lint finding"))
    g = gate(path, c, base)
    for _ in range(lint.REFUSALS):
        text, ok = submit(g)
        assert not ok
        assert "lint: " in text
    assert g.run.invalid == 0
    text, ok = submit(g)
    assert not ok
    assert "configuration:" in text
    assert "lint: " not in text
    assert not g.done
    assert g.run.invalid == 1


def test_a_merged_target_update_in_the_builders_shared_file_needs_no_approval(project) -> None:
    path, c, base = project
    commit(path, {"pyproject.toml": MANIFEST.replace("dependencies = []", 'dependencies = ["requests"]')})
    worktree.git(path, "checkout", "-q", "main")
    target = commit(path, {"pyproject.toml": MANIFEST.replace("100", "110")})
    worktree.git(path, "checkout", "-q", c.names.branch)
    worktree.git(path, "merge", "-q", "--no-edit", "main")
    assert quality.current(c, path)[0] == target
    assert submit(gate(path, c, base))[1]


@pytest.mark.parametrize("earlier_unapproved", [False, True])
def test_an_approved_repair_covers_its_patch_but_not_earlier_unapproved_configuration(
    project,
    tmp_path,
    earlier_unapproved,
) -> None:
    path, c, base = project
    if earlier_unapproved:
        commit(path, {"pyproject.toml": MANIFEST.replace("100", "110")})
    stuck.start(c, "project-env:build:check-fixture", "The declared check needs repair", NOW)
    r = c.repairs.current
    store, lock, at = Store(tmp_path / "store"), Lock(c.slug), tmp_path / "repair"
    r.base, r.fix = repair_copy.copy(path, at), "patch"
    content = (at / "pyproject.toml").read_text()
    content = (
        content.replace("dependencies = []", 'dependencies = ["requests"]')
        if earlier_unapproved
        else content.replace("100", "110")
    )
    (at / "pyproject.toml").write_text(content)
    if not earlier_unapproved:
        (at / "lefthook.yml").write_text("pre-commit:\n  commands: {}\n")
    try:
        prove_repair(store, lock, c, (path, at), ("true",), 60.0, Profile())
        assert r.phase == "asked"
        if not earlier_unapproved:
            assert any("lefthook.yml" in why for why in r.held)
        c = loop.fold(c, [AnswerItem(question=r.question, option="yes", at=NOW)], NOW)
        assert c.repairs.current.phase == "approved"
        apply_repair(store, lock, c, path, Profile())
    finally:
        repair_copy.drop(path, at)
    approved = c.repairs.done[-1].approved_configuration
    assert bool(approved) is not earlier_unapproved
    assert submit(gate(path, c, base))[1] is not earlier_unapproved


def test_requests_refuse_empty_or_unshowable_changes_without_asking(project) -> None:
    path, c, base = project
    g = gate(path, c, base)
    g.call(approval_tools.REQUEST, {"why": WHY})
    result = approvals.Requests(Store(path.parent / "store"), COMMANDS).requested(
        c, g.run, path, session_result.to_result(g.run, StepKind.BUILD, NOW)
    )
    assert result.exit == Exit.RETRY
    assert "no unapproved" in result.reason
    for content in ("x" * (repair_copy.SHOWN + 1), b"\x00binary"):
        commit(path, {"lefthook.yml": content})
        g = gate(path, c, base)
        g.call(approval_tools.REQUEST, {"why": WHY})
        result = approvals.Requests(Store(path.parent / "store"), COMMANDS).requested(
            c, g.run, path, session_result.to_result(g.run, StepKind.BUILD, NOW)
        )
        assert result.exit == Exit.RETRY
        assert "too long or binary" in result.reason
        assert c.questions == []
        assert "request_approval:" in c.step.question_errors[0]


@pytest.mark.browser
def test_configuration_question_shows_the_patch_and_resumes_after_the_answer(c1, pds, project) -> None:
    path, c, base = project
    commit(path, {"pyproject.toml": MANIFEST.replace("100", "110")})
    requested = request(path, c, base)
    q = requested.questions[-1]

    def edit(change: Change) -> None:
        change.step = requested.step
        change.questions = requested.questions
        change.outcome = requested.outcome

    store, _ = c1
    with opened(c1, pds, edit) as page:
        form = page.locator("section.act", has_text="Question q1")
        expect(form).to_contain_text(WHY)
        patch = form.get_by_label("The configuration patch")
        expect(patch).to_contain_text("-line-length = 100")
        expect(patch).to_contain_text("+line-length = 110")
        pds.settled(page)
        for name in ("Approve:", "Decline:", "Pause"):
            control = form.get_by_label(name, exact=False)
            expect(control).to_be_visible()
            big(control)
        primary = form.locator('p-button:not([variant="secondary"])')
        expect(primary).to_have_count(1)
        expect(primary).to_have_text("Answer")
        big(primary)
        measure = form.locator(".configuration-question")
        assert measure.evaluate("""e => {
            const context = document.createElement('canvas').getContext('2d');
            context.font = getComputedStyle(e).font;
            return e.getBoundingClientRect().width <= context.measureText('0'.repeat(75)).width + 1;
        }""")
        form.get_by_label("Approve:", exact=False).check()
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.split("?")[0].endswith("/answers")):
            form.get_by_role("button", name="Answer").click()
        store.fold(Lock("c1-fixture"), "c1-fixture", NOW)
        page.reload()
        expect(page.locator("section.act", has_text="Question q1")).to_have_count(0)
        expect(page.locator("#detail .status")).to_contain_text("starting builder")
        answered = store.read("c1-fixture").questions[-1]
        assert answered.answer.option == "approve"
        assert answered.delivered_at is None
        assert answered.id == q.id


@pytest.fixture
def scripted_judge(monkeypatch):
    contexts, replies = [], ["accepted"]

    async def run(cfg):
        assert cfg.role == "quality-judge"
        assert cfg.job == exceptions.JOB
        assert not cfg.policy.write
        context = json.loads((cfg.worktree / "exceptions-context.json").read_text())
        contexts.append(context)
        verdicts = [
            {
                "id": i["id"],
                "verdict": "accepted" if replies[0] == "omit" else replies[0],
                "reason": "Evidence: this boundary is generated.",
            }
            for i in context["items"]
        ]
        done = Run(
            cfg.session_id, model_check="verified", termination=Termination(confirmed=True), usage={"credits": 2.0}
        )
        judge = Gate(cfg, done, lambda **_e: None, lambda: None)
        if replies[0] == "omit":
            text, ok = judge.call(exception_tools.SUBMIT, {"verdicts": verdicts[:-1]})
            assert not ok
            assert len(verdicts) == 2
            assert verdicts[-1]["id"] in text
            assert not judge.done
            return Run(
                cfg.session_id, "error", detail=text, model_check="verified", termination=Termination(confirmed=True)
            )
        assert judge.call(exception_tools.SUBMIT, {"verdicts": verdicts})[1]
        return done

    monkeypatch.setattr(exceptions.sdk_adapter, "run", run)
    return contexts, replies


def judged(g: Gate) -> dict:
    text, ok = g.call(exception_tools.HELPER, {})
    assert ok
    return json.loads(text)


def test_a_build_needs_its_judges_acceptance_and_the_judge_receives_own_decisions(project, picking, scripted_judge):
    path, c, base = project
    c.decisions.append(ChangeDecision(text="Generated boundary names remain unchanged.", origin="decided", at=NOW))
    commit(path, {"edge.txt": "# editorconfig-checker-disable-next-line\ngenerated_name\n"})
    store = picking.store
    refused, ok = submit(gate(path, c, base, store))
    assert not ok
    assert "judge_exceptions" in refused
    where = spend_ledger.Where.of(store, change=c.slug, step="build")
    with spend_ledger.at(where):
        asked = exception_workers.Asked(store, Lock(c.slug), lambda: c, path)
        g = gate(path, c, base, store)
        g.cfg = replace(g.cfg, helpers=(asked.helper(),))
        answer = asked.settled(lambda: judged(g))
    assert answer["verdicts"][0]["verdict"] == "accepted"
    assert submit(g)[1]
    context = scripted_judge[0][0]
    assert any("Generated boundary names remain unchanged." in d["statement"] for d in context["decisions"])
    assert c.spend.credits == 2.0
    assert store.events(c.slug)[-1]["kind"] == exceptions.JOB


def test_a_test_curators_suppression_needs_judging_too(project, picking, scripted_judge):
    path, c, base = project
    head = commit(path, {"tests/test_edge.py": "# editorconfig-checker-disable-next-line\nvalue = 1\n"})
    g = gate(path, c, base, picking.store, curated=True)
    measure = {"command": "true", "tests": 1, "seconds": 0.1}
    result = {
        "applied": [{"test": "tests/test_edge.py", "action": "merge", "change": "Merged duplicate"}],
        "before": measure | {"commit": base},
        "after": measure | {"commit": head},
        "summary": "Merged",
    }
    assert not g.call(curation_tools.TEST_CURATION, result)[1]
    assert judged(g)["verdicts"][0]["verdict"] == "accepted"
    assert g.call(curation_tools.TEST_CURATION, result)[1]
    assert len(scripted_judge[0]) == 1


def test_a_refused_suppression_needs_the_owners_approve(project, picking, scripted_judge):
    path, c, base = project
    scripted_judge[1][0] = "refused"
    head = commit(path, {"edge.txt": "# editorconfig-checker-disable-next-line\ngenerated_name\n"})
    g = gate(path, c, base, picking.store)
    assert judged(g)["verdicts"][0]["verdict"] == "refused"
    assert not submit(g)[1]
    c = request(path, c, base, picking.store)
    q = c.questions[-1]
    assert "generated_name" in q.text
    assert "Evidence: this boundary is generated." in q.text
    assert ":suppressions-" in q.cause
    picking.store.write(Lock(c.slug), c)
    picking.store.put_inbox(c.slug, AnswerItem(question=q.id, option="approve", at=NOW))
    c, _ = picking.store.fold(Lock(c.slug), c.slug, NOW)
    identity = added(quality.git, path, base, head)[0].identity
    rows = ledger.counting(picking.store.root, identity, scope=c.slug)
    assert [row["by"] for row in rows] == ["owner"]
    assert submit(gate(path, c, base, picking.store))[1]


def test_removing_an_accepted_blocks_terminator_needs_another_verdict(project, picking, scripted_judge):
    path, c, base = project
    block = "# fmt: off\nvalue = 1\n# fmt: on\nother = 2\n"
    commit(path, {"fixture.py": block})
    g = gate(path, c, base, picking.store)
    assert judged(g)["verdicts"][0]["verdict"] == "accepted"
    assert submit(g)[1]
    assert len(scripted_judge[0]) == 1
    commit(path, {"fixture.py": block.replace("# fmt: on\n", "")})
    assert not submit(gate(path, c, base, picking.store))[1]


def test_an_extra_identical_copy_above_an_accepted_one_needs_its_own_change_verdict(project, picking, scripted_judge):
    path, c, base = project
    copy = "# editorconfig-checker-disable-next-line\ngenerated_name\n"
    commit(path, {"edge.txt": copy})
    g = gate(path, c, base, picking.store)
    assert judged(g)["verdicts"][0]["verdict"] == "accepted"
    assert submit(g)[1]
    commit(path, {"edge.txt": copy + copy})
    g = gate(path, c, base, picking.store)
    assert not submit(g)[1]
    assert judged(g)["verdicts"][-1]["verdict"] == "accepted"
    assert len(scripted_judge[0][-1]["items"]) == 1
    assert submit(g)[1]


def test_a_judge_cannot_omit_an_item_and_a_failed_run_writes_no_verdict(project, picking, scripted_judge):
    path, c, base = project
    scripted_judge[1][0] = "omit"
    commit(
        path,
        {
            "edge.txt": "# editorconfig-checker-disable-next-line\nfirst\n"
            "# editorconfig-checker-disable-next-line\nsecond\n"
        },
    )
    g = gate(path, c, base, picking.store)
    assert "e2" in judged(g)["failed"]
    assert not (picking.store.root / ledger.FILE).exists()
    assert not submit(g)[1]
