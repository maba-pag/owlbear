"""Stuck-step repair boundaries: checks, unfinished edits, public issues and approved preparation settings."""

import json
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import check_hint, preparation, repair_tools, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, Recovery
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Environment,
    Exit,
    Plan,
    Step,
    StepKind,
    Task,
    VisualState,
    Waiting,
)
from owlbear_delivery_next.change_contracts.preparation import DataPermissions, Preparation
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.repair_records import PreparationProposal, Witness
from owlbear_delivery_next.change_contracts.repair_tools import Defect
from owlbear_delivery_next.change_flow import loop, stuck, worktree
from owlbear_delivery_next.github.account import Origin
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import stop_routes
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import prepared
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import check, defect_issue, prepare, repair_copy, sessions, step_repair

NOW = datetime(2026, 11, 7, 12, tzinfo=UTC)
SYNTHETIC_METRICS = """import json, os, shutil, sys
from pathlib import Path

action, home = sys.argv[1], Path.home()
root = Path(__file__).resolve().parents[1]
assert home == root / ".fixture-home", (action, home, root)
assert "LIVE_SECRET" not in os.environ
ledger = home / "metrics.json"
data = {"authenticated": True, "runs": [{"name": "synthetic-run", "cost": 1.25}]}
if action == "restore":
    home.mkdir(parents=True, exist_ok=True)
    ledger.unlink(missing_ok=True)
elif action == "seed":
    ledger.write_text(json.dumps(data))
elif action in {"verify", "preview"}:
    assert json.loads(ledger.read_text()) == data
elif action == "cleanup":
    if os.environ.get("CLEANUP_CONTROL") and Path(os.environ["CLEANUP_CONTROL"]).exists():
        raise RuntimeError("synthetic cleanup temporarily unavailable")
    shutil.rmtree(home)
else:
    raise ValueError(action)
print(json.dumps({"action": action, "home": str(home), "cwd": str(Path.cwd()), "data": data}))
"""


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = tmp_path / "work"
    (work / "tests").mkdir(parents=True)
    for name, text in {"a.txt": "a\n", "b.txt": "b\n", "tests/test_a.py": "def test_a():\n    assert 1\n"}.items():
        (work / name).write_text(text)
    worktree.git(work, "init", "-q", "-b", "c1")
    worktree.git(work, "add", ".")
    worktree.git(work, "commit", "-q", "-m", "base")
    return work


def stuck_change() -> Change:
    c = Change(
        slug="c1", brief=Brief(version=1, approved_version=1, challenged=1, scope=["."]),
        plan=Plan(tasks=[Task(id="t1", title="t1", scope=["."])]), step=Step(kind=StepKind.BUILD, task="t1"),
    )  # fmt: skip
    stuck.start(c, "project-env:build:check-pytest", "the check pytest cannot finish", NOW)
    return c


def test_a_fix_that_weakens_a_test_is_never_applied(repo, tmp_path) -> None:
    c, at = stuck_change(), tmp_path / "copy"
    r = c.repairs.current
    r.base, r.fix = repair_copy.copy(repo, at), "patch"
    (at / "tests/test_a.py").write_text("import pytest\n\n\n@pytest.mark.skip\ndef test_a():\n    assert 1\n")
    head = worktree.git(repo, "rev-parse", "HEAD")
    store = SimpleNamespace(log=lambda *_: None, write=lambda *_: None)
    step_repair._proven(store, None, c, (repo, at), ("true",), 60.0, Profile())  # noqa: SLF001
    assert "weakens a check" in c.stop.reason
    assert "tests/test_a.py (adds a suppression or skip)" in c.stop.reason
    assert (worktree.git(repo, "rev-parse", "HEAD"), c.repairs.done[-1].commit) == (head, "")  # nothing applied


def test_a_selector_fix_is_held_even_when_its_own_empty_check_passes(repo, tmp_path, monkeypatch) -> None:
    package = repo / "serve/tools"
    source = package / "src/owlbear_tools"
    source.mkdir(parents=True)
    (package / "pyproject.toml").write_text('[project.scripts]\ntest = "owlbear_tools.testing:test_main"\n')
    for name, text in {
        "testing.py": "from owlbear_tools import task_scope, missing_selector\n",
        "task_scope.py": "from . import task_testing\n",
        "task_testing.py": "from .test_impact import select\n\ndef commands():\n    return ['tests/test_a.py']\n",
        "test_impact.py": "from owlbear_tools import test_dependencies\n",
        "test_dependencies.py": "FORMAT = 1\n",
    }.items():
        (source / name).write_text(text)
    worktree.git(repo, "add", "serve/tools")
    worktree.git(repo, "commit", "-q", "-m", "root selector")
    c, at = stuck_change(), tmp_path / "copy"
    c.brief.scope = ["serve/tools"]
    r = c.repairs.current
    r.base, r.fix = repair_copy.copy(repo, at), "patch"
    path = "serve/tools/src/owlbear_tools/task_testing.py"
    (at / path).write_text("def commands():\n    return []\n")
    witness = (check_hint.task_command(check_hint.qualified(".", "uv run test --changed"), r.base, r.base),)
    head = worktree.git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(
        step_repair,
        "_ran",
        lambda _at, commands, *_: Witness(
            commands=list(commands), exit=0, seconds=0.0, output="No test scope matched."
        ),
    )
    store = SimpleNamespace(log=lambda *_: None, write=lambda *_: None)
    step_repair._proven(  # noqa: SLF001
        store,
        None,
        c,
        (repo, at),
        tuple(command.replace("uv run ", "uv run --locked ", 1) for command in witness),
        60.0,
        Profile(),
    )
    assert worktree.git(repo, "rev-parse", "HEAD") == head
    assert r.held == [f"changes {path}, which the step's check runs, so it proves nothing alone"]
    assert all(
        step_repair._named(f"serve/tools/src/owlbear_tools/{name}.py", witness, repo)  # noqa: SLF001
        for name in ("testing", "task_scope", "task_testing", "test_impact", "test_dependencies")
    )
    missing = "serve/tools/src/owlbear_tools/missing_selector.py"
    assert not (repo / missing).exists()
    assert step_repair._named(missing, witness, repo)  # noqa: SLF001
    assert step_repair._named(path, ("python -m owlbear_tools.testing --changed",), repo)  # noqa: SLF001
    assert all(
        step_repair._named(path, (command,), repo)  # noqa: SLF001
        for command in (
            'python -c "from owlbear_tools.testing import test_main; test_main()"',
            "python <<'PY'\nfrom owlbear_tools.testing import test_main\ntest_main()\nPY",
        )
    )
    assert step_repair._named(path, ('sh -c "uv run test --changed"',), repo)  # noqa: SLF001
    (source / "task_scope.py").write_text("def broken(\n")
    reason = step_repair._check_hold(path, witness, repo)  # noqa: SLF001
    assert "cannot inspect the unchanged check" in reason
    assert "task_scope.py" in reason
    assert "proves nothing alone" in reason
    (source / "task_scope.py").write_text("from . import task_testing\n")
    malformed = repo / "serve/aaa/pyproject.toml"
    malformed.parent.mkdir()
    malformed.write_text("[project\n")
    worktree.git(repo, "add", "serve/aaa/pyproject.toml")
    reason = step_repair._check_hold(path, witness, repo)  # noqa: SLF001
    assert "TOMLDecodeError" in reason
    assert str(malformed) in reason
    assert "proves nothing alone" in reason
    (package / "pyproject.toml").write_text("[project\n")
    monkeypatch.setattr(worktree, "tracking", lambda *_: "c1")
    prof = Profile(
        entries={
            "check:.": ProfileEntry(state="known", value="uv run test --changed", evidence="owner confirmed"),
        }
    )
    bound = step_repair._witness(c, prof, repo)  # noqa: SLF001
    assert len(bound) == 1
    assert f"--task-base {r.base}" in bound[0]
    assert "--target " in bound[0]
    assert "TOMLDecodeError" in r.evidence
    assert "serve/tools/pyproject.toml" in r.evidence


def test_a_fix_reaches_the_branch_without_touching_the_steps_unfinished_edits(repo, tmp_path) -> None:
    (repo / "a.txt").write_text("a, unstaged\n")
    (repo / "b.txt").write_text("b, staged\n")
    worktree.git(repo, "add", "b.txt")
    (repo / "u.txt").write_text("untracked\n")
    at = tmp_path / "copy"
    base = repair_copy.copy(repo, at)
    (at / "c.txt").write_text("the fix\n")
    repair_copy.changed(at, base)
    fix = repair_copy.commit(at, "fix")
    new = repair_copy.apply(repo, "c1", base, fix, "fix: c")
    assert worktree.git(repo, "show", "--name-only", "--format=", new).split() == ["c.txt"]  # the fix alone
    assert ((repo / "a.txt").read_text(), (repo / "u.txt").read_text()) == ("a, unstaged\n", "untracked\n")
    assert worktree.git(repo, "diff", "--cached", "--name-only").split() == ["b.txt"]  # still staged, unchanged
    (at / "a.txt").write_text("a, by the repair\n")  # the same file as the unfinished edit
    repair_copy.changed(at, base)
    again = repair_copy.commit(at, "fix a")
    with pytest.raises(repair_copy.RepairError, match=r"a\.txt, which hold the step's unfinished edits"):
        repair_copy.apply(repo, "c1", base, again, "fix: a")
    assert ((repo / "a.txt").read_text(), worktree.git(repo, "rev-parse", "HEAD").strip()) == ("a, unstaged\n", new)


def test_a_private_projects_defect_text_naming_it_is_held_not_filed(repo, monkeypatch) -> None:
    made: list[str] = []
    issues = SimpleNamespace(find=lambda _m: None, create=lambda title, _body: made.append(title))
    monkeypatch.setattr(defect_issue, "OwlbearIssues", lambda *_: issues)
    monkeypatch.setattr(defect_issue.Origin, "of", classmethod(lambda *_: Origin("github.com", "acme", "secret-shop")))
    monkeypatch.setattr(defect_issue.repo_target, "view", lambda *_: SimpleNamespace(visibility="private"))
    store = SimpleNamespace(name="secret-shop", root=repo / "store")
    path = "serve/tools/src/owlbear_tools/testing.py:216"
    named = Defect(
        title="--changed runs the full suite", text="secret-shop's a.txt routes to the full suite", paths=[path]
    )
    said = defect_issue.file(store, repo, named)
    held = "it names this private project, or that could not be checked (a.txt, secret-shop)"
    assert said.startswith(f"held for you, not filed: {held}")
    assert made == []


def _ask_missing_preparation(repo, store, proposal, monkeypatch):
    c = Change(
        slug="c1",
        brief=Brief(
            version=4,
            approved_version=4,
            challenged=4,
            ui=True,
            scope=["app"],
            visual=[
                VisualState(
                    name="Metrics populated",
                    path="/metrics",
                    expect="Authenticated metrics show synthetic-run and cost 1.25",
                )
            ],
        ),
        step=Step(kind=StepKind.CHECK, task="visual"),
    )
    c.names.branch, c.names.target = "owlbear/c1", "c1"
    c.names.worktree = str(worktree.ensure(repo, repo / ".git", c.slug, c.names.branch, c.names.target))
    assert store.read_config().preparations is None
    failure = prepare.unsafe(store.settings())
    assert (failure.exit, failure.setup, failure.operational) == (Exit.RETRY, True, True)
    assert prepare.refused(store, Lock(c.slug), c)
    c = store.read(c.slug)
    assert (c.step.kind, c.step.task, c.brief.approved_version, c.env, c.stop) == (
        StepKind.CHECK,
        "visual",
        4,
        None,
        None,
    )
    assert (c.repairs.current.cause, c.repairs.current.evidence) == (
        "project-env:check:preparation-missing",
        failure.reason,
    )
    before, head, calls = store.config_path.read_bytes(), worktree.git(store.shared.root, "rev-parse", "HEAD"), []

    def model_result(_store, cfg):
        calls.append(cfg)
        assert cfg.submit is repair_tools.PREPARATION
        assert cfg.checks == ()
        assert "Current preparations:\nnull" in cfg.message
        assert failure.reason in cfg.message
        assert "Standing data permissions:" in cfg.message
        assert '"HOME"' in cfg.message
        assert all(text in cfg.message for text in ("Metrics populated", "/metrics", "synthetic-run", "1.25"))
        payload = repair_tools.PreparationResult(
            cause="The approved metrics view reads HOME/metrics.json but no test copy is declared.",
            tried=[repair_tools.Try(fix="Use committed app/fixture.py synthetic metrics", outcome="Seed and verify")],
            fix="preparation",
            preparation=proposal,
        )
        return Run(
            cfg.session_id,
            "result",
            payload,
            model_check="verified",
            usage={"credits": 0.25, "models": {}},
            termination=Termination(confirmed=True),
        )

    monkeypatch.setattr(sessions, "run", model_result)
    step_repair.run(store, Lock(c.slug), c, repo)
    c = store.read(c.slug)
    r, q = c.repairs.current, loop.open_question(c)
    assert (r.phase, q.subject, q.cause, r.preparations_before) == ("asked", "reserved", failure.cause, None)
    assert [(o.id, o.label, o.next) for o in q.options] == [
        ("yes", "Save this preparation and run the step again", stuck.APPLY),
        ("no", "Don't apply it; stop with what was tried", stuck.DECLINE),
    ]
    assert json.loads(r.diff) == {"preparations": [proposal.option.model_dump(mode="json")]}
    assert all(text in q.text for text in (r.diff, proposal.description, failure.reason, r.witness.output))
    assert q.text.startswith("Save this test preparation and run the step again?")
    assert c.outcome.reason == "Approve the proposed test preparation"
    assert "Data permissions do not change" in q.text
    assert "No changes no settings" in q.text
    assert (r.witness.exit, r.witness.commands) == (
        0,
        [proposal.option.restore, proposal.option.seed, proposal.verify, proposal.option.cleanup],
    )
    proof = [json.loads(line) for line in r.witness.output.splitlines() if line.startswith("{")]
    assert [p["action"] for p in proof] == ["restore", "seed", "verify", "cleanup"]
    clean = calls[0].worktree.with_name(f"{calls[0].worktree.name}-preparation-proof")
    assert {p["home"] for p in proof} == {str(clean / ".fixture-home")}
    assert not calls[0].worktree.exists()
    assert (store.config_path.read_bytes(), worktree.git(store.shared.root, "rev-parse", "HEAD")) == (before, head)
    return c, calls


def _decline_missing_preparation(store, asked):
    before, head = store.config_path.read_bytes(), worktree.git(store.shared.root, "rev-parse", "HEAD")
    r, q = asked.repairs.current, loop.open_question(asked)
    declined = loop.fold(asked, [AnswerItem(question=q.id, option="no", at=NOW)], NOW)
    store.write(Lock(asked.slug), declined)
    kept = store.read(asked.slug)
    assert (kept.repairs.current, kept.outcome.exit, kept.repairs.done[-1].phase) == (None, Exit.STOP, "stopped")
    assert (kept.repairs.done[-1].preparation, kept.repairs.done[-1].witness) == (r.preparation, r.witness)
    explanation = stop_routes.shown(kept, store)["reason"]
    assert all(text in explanation for text in ("you declined the fix", r.diff, r.witness.output, r.evidence))
    assert explanation == kept.stop.reason
    assert (store.config_path.read_bytes(), worktree.git(store.shared.root, "rev-parse", "HEAD")) == (before, head)


def _publish_missing_preparation(store, asked, remote, repo, monkeypatch):
    q = loop.open_question(asked)
    approved = loop.fold(asked, [AnswerItem(question=q.id, option="yes", at=NOW)], NOW)
    assert approved.repairs.current.phase == "approved"
    stale = approved.model_copy(deep=True)
    remote_head = worktree.git(remote, "rev-parse", "HEAD")
    offline = remote.with_name("offline.git")
    publish = DataRepo.publish

    def offline_publish(shared, path, message, until=None):
        remote.rename(offline)
        try:
            return publish(shared, path, message, until)
        finally:
            offline.rename(remote)

    with monkeypatch.context() as disconnected:
        disconnected.setattr(DataRepo, "publish", offline_publish)
        step_repair.run(store, Lock(approved.slug), approved, repo)
    held = store.read(approved.slug)
    assert (held.repairs.current.phase, held.repairs.current.applied, held.repairs.done) == ("approved", "", [])
    assert (held.outcome.exit, held.stop.action) == (Exit.STOP, stuck.RERUN)
    assert "the approved preparation is not published:" in held.stop.reason
    assert str(remote) in held.stop.reason
    assert "a held automatic change cannot be checked:" in held.stop.reason
    assert worktree.git(remote, "rev-parse", "HEAD") == remote_head
    written = store.config_path.read_bytes()
    config_history = worktree.git(store.shared.root, "log", "--format=%H", "--", str(store.config_path))
    assert json.loads(written)["preparations"] == json.loads(asked.repairs.current.diff)["preparations"]
    recovered = loop.fold(held, [Recovery(action=held.stop.action, at=NOW)], NOW)
    assert recovered.stop is None
    assert recovered.repairs.current.phase == "approved"
    step_repair.run(store, Lock(recovered.slug), recovered, repo)
    applied = store.read(recovered.slug)
    assert (applied.repairs.current, applied.stop, applied.outcome) == (None, None, None)
    assert (applied.step.kind, applied.step.task, applied.brief.approved_version) == (StepKind.CHECK, "visual", 4)
    assert (applied.repairs.done[-1].phase, applied.repairs.done[-1].applied) == ("applied", "preparation metrics")
    assert store.config_path.read_bytes() == written
    assert worktree.git(store.shared.root, "log", "--format=%H", "--", str(store.config_path)) == config_history
    relative = store.config_path.relative_to(store.shared.root).as_posix()
    assert worktree.git(remote, "show", f"HEAD:{relative}").strip() == written.decode().strip()
    assert store.shared.pending() == ""
    return applied, stale


def _exercise_saved_preparation(store, c, repo, proposal):
    root, settings, events = Path(c.names.worktree), store.settings(), []
    recipe = tools.CheckRecipe(
        command=shlex.join([sys.executable, "fixture.py", "preview", "{port}"]),
        directory="app",
        ready_url="http://127.0.0.1:{port}/",
        summary="Synthetic metrics preview",
        preparation="metrics",
        reason="The approved metrics state needs an authenticated populated ledger",
    )
    c.env = Environment(
        check="visual", command=recipe.command, directory=recipe.directory, ready_url=recipe.ready_url, port=0
    )
    ctx = prepare.context(store, c, settings, root)
    chosen = prepare.chosen(store, Lock(c.slug), c, root, recipe, ctx, loop.StepResult(exit=Exit.PENDING))
    assert chosen.exit == Exit.PENDING
    before = store.root / "before"
    worktree.git(repo, "worktree", "add", "--detach", str(before), "c1")
    try:
        before_env = prepare.merge_base(store, c, settings, events.append)(before)
        assert before_env["HOME"] == str(before / ".fixture-home")
        assert json.loads((before / ".fixture-home/metrics.json").read_text())["authenticated"] is True
        assert prepare.end(store, c, repo, settings, events.append) is None
        assert not before.exists()
        result = prepare.launch(store, c, settings, events.append)
        assert (result.exit, result.waiting) == (Exit.PENDING, Waiting.CHECK_START)
        env = prepare.environ(store, c)
        assert env["HOME"] == str(root / ".fixture-home") != before_env["HOME"]
        assert set(env) - {"HOME"} <= set(preparation.BASE)
        assert "LIVE_SECRET" not in env
        assert prepare.read(store, c.slug, "visual").option == proposal.option
        assert store.read_config().preparations[0].isolation == {"HOME": ".fixture-home"}
        log = store.root / "preview.log"
        proc = check.start(c.env, root, log, env)
        assert proc is not None
        check.release(proc)
        try:
            assert proc.wait(timeout=10) == 0
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
        preview = json.loads(log.read_text())
        assert (preview["action"], preview["cwd"], preview["home"]) == ("preview", str(root / "app"), env["HOME"])
        c.env = None
        assert prepare.end(store, c, repo, settings, events.append) is None
        assert not (root / ".fixture-home").exists()
        assert prepare.left(store, c) == []
        assert any(e.get("event") == "prepared-end" and e.get("cleanup") == "ok" for e in events)
    finally:
        if before.exists():
            worktree.git(repo, "worktree", "remove", "--force", str(before))


def _reject_ignored_preparation(store, asked, proposal, repo, monkeypatch):
    absolute = False
    dirty = asked.model_copy(deep=True)
    dirty.questions = []
    dirty.repairs.current.phase = "running"
    assert (
        store.save(
            store.config_path,
            Layer,
            lambda cur: cur.model_copy(update={"preparations": None}),
            "reset the isolated fixture",
            owner=True,
        )
        == ""
    )

    def ignored_model_result(_store, cfg):
        helper = cfg.worktree / ".owlbear/scratch/verify.py"
        helper.parent.mkdir(parents=True)
        helper.write_text("print('only the model copy has this helper')\n")
        command = str(helper) if absolute else ".owlbear/scratch/verify.py"
        contaminated = proposal.model_copy(update={"verify": shlex.join([sys.executable, command])})
        return Run(
            cfg.session_id,
            "result",
            repair_tools.PreparationResult(
                cause="The model left an ignored helper outside its source diff.",
                tried=[repair_tools.Try(fix="Use an ignored verification helper", outcome="Exists in the model copy")],
                fix="preparation",
                preparation=contaminated,
            ),
            model_check="verified",
            usage={"credits": 0.0, "models": {}},
            termination=Termination(confirmed=True),
        )

    monkeypatch.setattr(sessions, "run", ignored_model_result)
    step_repair.run(store, Lock(dirty.slug), dirty, repo)
    rejected = store.read(dirty.slug)
    assert loop.open_question(rejected) is None
    assert rejected.repairs.current is None
    assert rejected.repairs.done[-1].witness.exit != 0
    assert "verify.py" in rejected.stop.reason
    assert "No such file" in rejected.stop.reason
    assert store.read_config().preparations is None
    absolute = True
    dirty = asked.model_copy(deep=True)
    dirty.questions = []
    dirty.repairs.current.phase = "running"
    step_repair.run(store, Lock(dirty.slug), dirty, repo)
    rejected = store.read(dirty.slug)
    assert loop.open_question(rejected) is None
    assert rejected.repairs.done[-1].witness is None
    assert "depends on its throwaway Repairer checkout" in rejected.stop.reason
    assert store.read_config().preparations is None


def _reject_escaping_home(store, c, repo, owner_home):
    root = Path(c.names.worktree)
    home = root / ".fixture-home"
    home.symlink_to(owner_home, target_is_directory=True)
    c.env = Environment(check="visual", command="true", directory="app", ready_url="http://127.0.0.1:{port}/")
    events = []
    try:
        result = prepare.launch(store, c, store.settings(), events.append)
        assert result.exit == Exit.RETRY
        assert "resolves outside" in result.reason
        with pytest.raises(prepare.PrepareError, match="resolves outside"):
            prepare.environ(store, c)
        active = prepare.read(store, c.slug, "visual")
        prepared.write(store, c.slug, active.model_copy(update={"open": True, "snapshot_only": False}))
        c.env = None
        assert prepare.end(store, c, repo, store.settings(), events.append) is None
        assert prepare.read(store, c.slug, "visual").open
        assert events[-1]["outstanding"] is True
        assert "resolves outside" in events[-1]["cleanup"]
        assert (owner_home / "metrics.json").read_bytes() == b'{"private": "owner ledger must stay unchanged"}\n'
    finally:
        home.unlink()
    source = root / "app"
    unfinished = source / "unfinished.txt"
    unfinished.write_text("unfinished source must survive preparation")
    home.symlink_to(source, target_is_directory=True)
    c.env = Environment(check="visual", command="true", directory="app", ready_url="http://127.0.0.1:{port}/")
    try:
        result = prepare.launch(store, c, store.settings(), events.append)
        assert result.exit == Exit.RETRY
        assert "redirects to source directory" in result.reason
        with pytest.raises(prepare.PrepareError, match="redirects to source directory"):
            prepare.environ(store, c)
        active = prepare.read(store, c.slug, "visual")
        prepared.write(store, c.slug, active.model_copy(update={"open": True, "snapshot_only": False}))
        c.env = None
        assert prepare.end(store, c, repo, store.settings(), events.append) is None
        assert "redirects to source directory" in events[-1]["cleanup"]
        assert unfinished.read_text() == "unfinished source must survive preparation"
        assert (source / "fixture.py").is_file()
    finally:
        home.unlink()
        unfinished.unlink()
    home.mkdir()
    assert prepare.end(store, c, repo, store.settings(), events.append) is None
    assert not prepare.read(store, c.slug, "visual").open
    assert not home.exists()


def _reject_remote_preparation(store, asked, repo, remote, other):
    worktree.git(repo, "clone", "--quiet", str(remote), str(other))
    path = other / store.config_path.relative_to(store.shared.root)
    owner = Layer.model_validate_json(path.read_text()).model_copy(update={"preparations": []})
    path.write_text(owner.model_dump_json(indent=1))
    worktree.git(other, "add", ".")
    worktree.git(other, "commit", "-qm", "owner changes preparation from another clone")
    worktree.git(other, "push", "--quiet")
    head = worktree.git(remote, "rev-parse", "HEAD")
    q = loop.open_question(asked)
    approved = loop.fold(asked, [AnswerItem(question=q.id, option="yes", at=NOW)], NOW)
    step_repair.run(store, Lock(approved.slug), approved, repo)
    held = store.read(approved.slug)
    assert held.repairs.current.phase == "approved"
    assert held.outcome.exit == Exit.STOP
    assert held.repairs.current.applied == ""
    assert store.read_config().preparations == []
    assert worktree.git(remote, "rev-parse", "HEAD") == head
    assert "preparations changed after this proposal was shown; nothing was overwritten" in held.stop.reason


def _retain_failed_trial(store, asked, proposal, repo, monkeypatch):
    control = store.root / "cleanup-held"
    control.write_text("simulate a temporarily unavailable cleanup")
    option = proposal.option.model_copy(
        update={"isolation": proposal.option.isolation | {"CLEANUP_CONTROL": str(control)}}
    )
    failed = asked.model_copy(deep=True)
    failed.questions = []
    failed.repairs.current.phase = "running"
    calls = []

    def cleanup_model_result(_store, cfg):
        calls.append(cfg)
        return Run(
            cfg.session_id,
            "result",
            repair_tools.PreparationResult(
                cause="The synthetic cleanup is temporarily unavailable.",
                tried=[repair_tools.Try(fix="Use the committed synthetic fixture", outcome="Cleanup reports failure")],
                fix="preparation",
                preparation=proposal.model_copy(update={"option": option}),
            ),
            model_check="verified",
            usage={"credits": 0.0, "models": {}},
            termination=Termination(confirmed=True),
        )

    monkeypatch.setattr(sessions, "run", cleanup_model_result)
    step_repair.run(store, Lock(failed.slug), failed, repo)
    held = store.read(failed.slug)
    assert held.outcome.exit == Exit.RETRY
    assert held.stop is None
    assert loop.open_question(held) is None
    owed = prepare.left(store, held)
    assert len(owed) == 1
    assert owed[0].trial
    clean = Path(owed[0].home)
    assert (clean / "app/fixture.py").is_file()
    assert "synthetic cleanup temporarily unavailable" in held.outcome.reason
    before_retry = len(store.events(held.slug))
    assert prepare.cleanup_records(store, held, datetime.now(UTC)) == []
    assert prepare.ran(store, Lock(held.slug), held, repo, runnable=True)
    assert len(store.events(held.slug)) == before_retry
    held.outcome.wake_at = NOW
    assert prepare.ran(store, Lock(held.slug), held, repo, runnable=True)
    assert prepare.left(store, held)[0].open
    assert clean.is_dir()
    assert len(calls) == 1
    control.unlink()
    held.outcome.wake_at = NOW
    drop = repair_copy.drop

    def interrupted_drop(source, at):
        if at == clean:
            msg = "interrupted before cleaned trial disposal"
            raise OSError(msg)
        drop(source, at)

    with monkeypatch.context() as interrupted:
        interrupted.setattr(repair_copy, "drop", interrupted_drop)
        with pytest.raises(OSError, match="interrupted before cleaned trial disposal"):
            prepare.ran(store, Lock(held.slug), held, repo, runnable=False)
    assert not prepare.left(store, held)[0].open
    assert clean.is_dir()
    assert not (clean / ".fixture-home").exists()
    assert not prepare.ran(store, Lock(held.slug), held, repo, runnable=False)
    assert prepare.left(store, held) == []
    assert not clean.exists()
    assert store.read_config().preparations is None


def test_missing_visual_preparation_requires_owner_approval_before_project_settings_write(
    repo, tmp_path, shared_repo, monkeypatch
) -> None:
    """Reconstructed c1-like approved inputs cross the model-to-settings boundary, never the live host."""
    home = tmp_path / "owner-home"
    home.mkdir()
    sentinel = home / "metrics.json"
    sentinel.write_bytes(b'{"private": "owner ledger must stay unchanged"}\n')
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LIVE_SECRET", "must-not-reach-synthetic-processes")
    (repo / "app").mkdir()
    (repo / "app/fixture.py").write_text(SYNTHETIC_METRICS)
    (repo / ".gitignore").write_text(".owlbear/\n")
    worktree.git(repo, "add", "app/fixture.py", ".gitignore")
    worktree.git(repo, "commit", "-qm", "synthetic metrics fixture")
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "synthetic-project")
    initial = Layer(preparations=None, data=DataPermissions(isolation=["HOME"]), widths=[1280], pr_labels=["keep"])
    assert store.save(store.config_path, Layer, lambda _: initial, "fixture project settings", owner=True) == ""
    global_before = store.shared.global_path.read_bytes() if store.shared.global_path.exists() else None
    proposal = PreparationProposal(
        option=Preparation(
            id="metrics",
            kind="data-only",
            isolation={"HOME": ".fixture-home"},
            restore=shlex.join([sys.executable, "app/fixture.py", "restore"]),
            seed=shlex.join([sys.executable, "app/fixture.py", "seed"]),
            cleanup=shlex.join([sys.executable, "app/fixture.py", "cleanup"]),
        ),
        description="Committed app/fixture.py seeds an authenticated synthetic run costing 1.25 into a "
        "worktree-relative HOME; cleanup deletes that HOME. No live data or permissions change.",
        verify=shlex.join([sys.executable, "app/fixture.py", "verify"]),
    )
    asked, calls = _ask_missing_preparation(repo, store, proposal, monkeypatch)
    _decline_missing_preparation(store, asked.model_copy(deep=True))
    assert sentinel.read_bytes() == b'{"private": "owner ledger must stay unchanged"}\n'
    assert (
        store.save(
            store.config_path,
            Layer,
            lambda cur: cur.model_copy(update={"widths": [1440]}),
            "owner changed unrelated widths",
            owner=True,
        )
        == ""
    )
    applied, stale = _publish_missing_preparation(store, asked.model_copy(deep=True), shared_repo[1], repo, monkeypatch)
    assert store.read_config().model_dump(exclude={"preparations", "widths"}) == initial.model_dump(
        exclude={"preparations", "widths"}
    )
    assert store.read_config().widths == [1440]
    _exercise_saved_preparation(store, applied, repo, proposal)
    _reject_escaping_home(store, applied, repo, home)
    other = proposal.option.model_copy(update={"id": "owner-added"})
    assert (
        store.save(
            store.config_path,
            Layer,
            lambda cur: cur.model_copy(update={"preparations": [proposal.option, other]}),
            "owner added another preparation",
            owner=True,
        )
        == ""
    )
    current, head = store.config_path.read_bytes(), worktree.git(store.shared.root, "rev-parse", "HEAD")
    step_repair.run(store, Lock(stale.slug), stale, repo)
    refused = store.read(stale.slug)
    assert (refused.repairs.current.phase, refused.repairs.current.applied, refused.repairs.done) == (
        "approved",
        "",
        [],
    )
    assert "preparations changed after this proposal was shown; nothing was overwritten" in refused.stop.reason
    assert (store.config_path.read_bytes(), worktree.git(store.shared.root, "rev-parse", "HEAD")) == (current, head)
    assert store.read_config().preparations == [proposal.option, other]
    assert len(calls) == 1
    _reject_ignored_preparation(store, asked, proposal, repo, monkeypatch)
    _retain_failed_trial(store, asked, proposal, repo, monkeypatch)
    _reject_remote_preparation(store, asked.model_copy(deep=True), repo, shared_repo[1], tmp_path / "other-settings")
    assert (store.shared.global_path.read_bytes() if store.shared.global_path.exists() else None) == global_before
    assert not store.machine_path.exists()
    assert sentinel.read_bytes() == b'{"private": "owner ledger must stay unchanged"}\n'
    assert not (home / ".fixture-home").exists()
