"""Read-only sessions run in the Change's one read-only worktree, reset to the judged commit before each session (each
judge in the window, each SDK judge batch); refs they create or move void them."""

import argparse
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from owlbear_delivery_next import briefs, cli, loop, profile_record, runner, sdk_adapter, sessions, tools
from owlbear_delivery_next.models import Brief, Change, ErrorKind, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.steps import disposable, worktree
from owlbear_delivery_next.store import Lock, Store, StoreError, git_common_dir

K = StepKind
VOIDED = "policy:review:read-only-write"
REFUSED = "state:review:read-only-worktree"


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def store(tmp_path, change_repo, monkeypatch) -> Store:
    """A Change whose task t1 is under review in ``change_repo``."""
    store = Store(tmp_path / "store")
    names = Names(branch="owlbear/c1", target="main", worktree=str(change_repo))
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["a.txt"], base=git(change_repo, "rev-parse", "main"))])
    change = Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=K.REVIEW, task="t1"), names=names)
    store.write(Lock("c1"), change)
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    return store


def reviewer(monkeypatch, act=lambda _cfg: None, *, confirmed: bool = True) -> list[sdk_adapter.Session]:
    """A reviewer that passes after *act*; the sessions it was given."""
    seen = []

    async def fake(cfg):
        seen.append(cfg)
        head = git(cfg.worktree, "rev-parse", "HEAD")
        act(cfg)
        payload = tools.ReviewResult(verdict="pass", covered_paths=["a.txt"])
        return Run(cfg.session_id, "result", payload, head=head, termination=Termination(confirmed=confirmed))

    monkeypatch.setattr(runner.sdk_adapter, "run", fake)
    return seen


def reviewed(store: Store, repo: Path) -> Change:
    """Run task t1's review step again, whatever an earlier run left."""
    change = store.read("c1")
    change.step, change.stop = Step(kind=K.REVIEW, task="t1"), None
    runner._step(store, Lock("c1"), change, change.step, repo)  # noqa: SLF001
    return store.read("c1")


def commit(repo: Path, name: str, text: str) -> str:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-qm", name)
    return git(repo, "rev-parse", "HEAD")


def test_a_review_runs_in_the_change_s_read_only_worktree_at_its_head_which_stays(store, change_repo, monkeypatch):
    head, base, seen = git(change_repo, "rev-parse", "HEAD"), git(change_repo, "rev-parse", "main"), []

    def act(cfg):
        seen.append((cfg.observe(), git(change_repo, "worktree", "list", "--porcelain")))

    cfg = (reviewer(monkeypatch, act), reviewed(store, change_repo))[0][0]
    at, (observed, listed) = cfg.worktree, seen[0]
    assert at == disposable.path(change_repo, "c1")
    assert (at.parent.parent, at.name) == (worktree.data_root(), "c1.ro")
    assert f"worktree {at}\nHEAD {head}\ndetached" in listed
    assert (cfg.policy.root, cfg.policy.write) == (at, False)
    assert (str(at) in cfg.message, str(change_repo) in cfg.message) == (True, False)
    assert (observed.head, observed.base) == (head, base)  # the same commits the Change worktree reports
    assert at.is_dir()  # its VS Code window stays valid
    assert f"worktree {at}\nHEAD {head}\ndetached" in git(change_repo, "worktree", "list", "--porcelain")
    assert disposable.live(store.root / "changes" / "c1") is None
    assert store.read("c1").outcome.exit == Exit.DONE


def test_the_read_only_worktree_is_reused_and_reset_to_the_next_head(store, change_repo, monkeypatch):
    commit(change_repo, ".gitignore", "*.log\n")

    def act(cfg):
        (cfg.worktree / "a.txt").write_text("changed\n")
        (cfg.worktree / "new.txt").write_text("new\n")
        (cfg.worktree / "deep").mkdir()
        (cfg.worktree / "deep" / "x.txt").write_text("x\n")
        (cfg.worktree / "out.log").write_text("ignored\n")

    first = reviewer(monkeypatch, act)
    reviewed(store, change_repo)
    at = first[0].worktree
    assert (at / "new.txt").exists()  # nothing removes it after the session
    head = commit(change_repo, "a.txt", "b\n")
    found = []
    second = reviewer(monkeypatch, lambda cfg: found.append(git(cfg.worktree, "status", "--porcelain", "--ignored")))
    c = reviewed(store, change_repo)
    assert (second[0].worktree, git(at, "rev-parse", "HEAD"), found) == (at, head, ["!! out.log"])
    assert (at / "a.txt").read_text() == "b\n"
    assert not any((at / p).exists() for p in ("new.txt", "deep"))
    assert (at / "out.log").read_text() == "ignored\n"  # ignored files, installed dependencies among them, stay
    assert c.outcome.exit == Exit.DONE


def test_files_a_review_writes_never_reach_the_change_worktree_and_its_result_stands(store, change_repo, monkeypatch):
    def act(cfg):
        (cfg.worktree / "a.txt").write_text("changed\n")
        (cfg.worktree / "new.txt").write_text("new\n")

    reviewer(monkeypatch, act)
    c = reviewed(store, change_repo)
    assert git(change_repo, "status", "--porcelain") == ""
    assert (change_repo / "a.txt").read_text() == "a\n"
    assert c.outcome.exit == Exit.DONE


@pytest.mark.parametrize(
    ("args", "said"),
    [
        (("branch", "probe-branch"), "created branch probe-branch"),
        (("tag", "v1"), "created tag v1"),
        (("branch", "-f", "main", "HEAD"), "moved branch main"),
    ],
)
def test_a_ref_a_review_creates_or_moves_voids_its_result(store, change_repo, monkeypatch, args, said):
    seen = reviewer(monkeypatch, lambda cfg: git(cfg.worktree, *args))
    c = reviewed(store, change_repo)
    assert (c.outcome.exit, c.outcome.cause) == (Exit.RETRY, VOIDED)
    assert c.outcome.reason == f"a read-only step changed the repository: {said}"
    assert git(change_repo, "for-each-ref", "--format=%(refname:short)", f"refs/*/{said.rsplit(' ', 1)[1]}")
    events = [e for e in store.events("c1") if e.get("event") == "read-only-violation"]
    assert [e["refs"] for e in events] == [[said]]
    assert seen[0].worktree.is_dir()


def test_a_read_only_worktree_switched_to_a_branch_is_detached_again_by_the_next_session(
    store, change_repo, monkeypatch
):
    reviewer(monkeypatch, lambda cfg: git(cfg.worktree, "switch", "-q", "-c", "probe-branch"))
    c = reviewed(store, change_repo)
    assert c.outcome.reason == "a read-only step changed the repository: created branch probe-branch"
    seen = reviewer(monkeypatch)
    c = reviewed(store, change_repo)
    at = seen[0].worktree
    assert (at, c.outcome.exit) == (disposable.path(change_repo, "c1"), Exit.DONE)
    assert f"worktree {at}\nHEAD {git(change_repo, 'rev-parse', 'HEAD')}\ndetached" in git(
        change_repo, "worktree", "list", "--porcelain"
    )


def test_concurrent_change_branches_and_branches_other_worktrees_hold_are_not_violations(
    tmp_path, store, change_repo, monkeypatch
):
    other = tmp_path / "other"
    git(change_repo, "worktree", "add", "-q", "-b", "feature", str(other), "main")

    def act(cfg):
        git(cfg.worktree, "branch", "owlbear/x")
        git(other, "commit", "-q", "--allow-empty", "-m", "elsewhere")

    reviewer(monkeypatch, act)
    assert reviewed(store, change_repo).outcome.exit == Exit.DONE


def test_a_read_only_worktree_whose_processes_are_not_confirmed_gone_is_not_reset(store, change_repo, monkeypatch):
    seen = reviewer(monkeypatch, lambda cfg: (cfg.worktree / "left.txt").write_text("x\n"), confirmed=False)
    c = reviewed(store, change_repo)
    at = seen[0].worktree
    assert (c.outcome.exit, disposable.live(store.root / "changes" / "c1")) == (Exit.STOP, at)
    commit(change_repo, "a.txt", "b\n")
    c = reviewed(store, change_repo)
    assert (c.outcome.exit, c.outcome.cause, len(seen)) == (Exit.RETRY, REFUSED, 1)
    assert c.outcome.reason == f"the processes of the last read-only session in {at} are not confirmed gone"
    assert ((at / "left.txt").exists(), (at / "a.txt").read_text()) == (True, "a\n")  # untouched
    disposable.settled(store.root / "changes" / "c1")  # what the host does once its scan finds none
    again = reviewer(monkeypatch)
    assert reviewed(store, change_repo).outcome.exit == Exit.DONE
    assert (again[0].worktree, (at / "left.txt").exists(), len(seen)) == (at, False, 1)


def test_a_runner_that_fails_mid_session_leaves_the_read_only_worktree_marked(tmp_path, change_repo, monkeypatch):
    store = Store(tmp_path / "store")
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.CHECK))

    async def broken(_cfg):
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(sessions.sdk_adapter, "run", broken)
    with pytest.raises(OSError, match="disk full"):
        sessions.judges(store, Lock("c1"), change, change_repo, lambda at: [("visual-review", judge(at, "m"))])
    assert disposable.live(store.root / "changes" / "c1") == disposable.path(change_repo, "c1")


def test_an_unread_review_is_held_against_the_change_worktree(store, change_repo, monkeypatch):
    seen = []

    async def fake(cfg):
        seen.append(cfg.worktree)
        head = git(cfg.worktree, "rev-parse", "HEAD")
        done = Run(cfg.session_id, "result", tools.ReviewResult(verdict="pass"), head=head, usage_unread="unread")
        done.termination = Termination(confirmed=True)
        return done

    monkeypatch.setattr(runner.sdk_adapter, "run", fake)
    c = reviewed(store, change_repo)
    assert [o.id for o in loop.open_question(c).options] == ["accept", "retry"]
    assert (seen[0] != change_repo, disposable.live(store.root / "changes" / "c1")) == (True, None)


def judge(at: Path, message: str) -> sdk_adapter.Session:
    return sdk_adapter.Session(
        kind=K.REVIEW,
        worktree=at,
        session_id="",
        message=message,
        resume=False,
        policy=Policy(at, write=False),
        observe=tools.Worktree,
        checks=(),
    )


def test_judges_of_a_batch_share_the_read_only_worktree_and_a_violation_voids_each(tmp_path, change_repo, monkeypatch):
    store, seen = Store(tmp_path / "store"), []
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.CHECK))
    store.write(Lock("c1"), change)

    async def fake(cfg):
        seen.append(cfg.worktree)
        if cfg.message == "second":
            git(cfg.worktree, "tag", "probe")
        payload = tools.ReviewResult(verdict="pass")
        return Run(cfg.session_id, "result", payload, head="h", termination=Termination(confirmed=True))

    monkeypatch.setattr(sessions.sdk_adapter, "run", fake)
    made = lambda at: [("visual-review", judge(at, "first")), ("design-review", judge(at, "second"))]  # noqa: E731
    ran = sessions.judges(store, Lock("c1"), change, change_repo, made)
    assert (len(seen), set(seen)) == (2, {disposable.path(change_repo, "c1")})
    assert [(r.exit, r.cause) for r, _ in ran] == [(Exit.RETRY, "policy:check:read-only-write")] * 2
    assert [run.payload for _, run in ran] == [None, None]


def test_the_planner_and_its_challenge_each_judge_a_clean_head_in_the_read_only_worktree(
    tmp_path, change_repo, monkeypatch
):
    store, seen = Store(tmp_path / "store"), []
    names = Names(branch="owlbear/c1", target="main", worktree=str(change_repo))
    change = Change(slug="c1", brief=Brief(version=1, approved_version=1, challenged=1), step=Step(kind=K.PLAN))
    store.write(Lock("c1"), change.model_copy(update={"names": names}))
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    (change_repo / "left.txt").write_text("an earlier step's edit\n")

    async def fake(cfg):
        seen.append((cfg.worktree, cfg.message, git(cfg.worktree, "status", "--porcelain")))
        (cfg.worktree / "scratch.txt").write_text("the planner's note\n")
        task = {"title": "one", "goal": "AC-1", "scope": ["a.txt"], "checks": ["true"]}
        payload = tools.PlanResult(tasks=[task]) if cfg.submit is tools.PLAN else tools.ReviewResult(verdict="pass")
        return Run(cfg.session_id, "result", payload, termination=Termination(confirmed=True))

    monkeypatch.setattr(runner.sdk_adapter, "run", fake)
    change = store.read("c1")
    runner._step(store, Lock("c1"), change, change.step, change_repo)  # noqa: SLF001
    assert store.read("c1").outcome.exit == Exit.DONE
    (planner, said, dirty), (challenger, challenged, clean) = seen
    assert (planner, challenger) == (disposable.path(change_repo, "c1"),) * 2
    assert (str(planner) in said, str(challenger) in challenged, dirty, clean) == (True, True, "", "")


@pytest.fixture
def ro(change_repo) -> Path:
    """Where the Change's read-only worktree belongs, not yet created."""
    at = disposable.path(change_repo, "c1")
    at.parent.mkdir(parents=True, exist_ok=True)
    return at


def test_custody_refuses_a_symlink_a_foreign_worktree_and_a_plain_folder_touching_nothing(tmp_path, change_repo, ro):
    store, target = Store(tmp_path / "store"), tmp_path / "target"
    git(change_repo, "worktree", "add", "-q", "--detach", str(target))
    ro.symlink_to(target)
    assert disposable.prepare(change_repo, store, "c1") == f"{ro} is a symlink"
    ro.unlink()
    foreign_repo = tmp_path / "foreign"
    git(tmp_path, "init", "-q", str(foreign_repo))
    git(foreign_repo, "commit", "-q", "--allow-empty", "-m", "x")
    git(foreign_repo, "worktree", "add", "-q", "--detach", str(ro))
    (ro / "kept.txt").write_text("theirs\n")
    assert disposable.prepare(change_repo, store, "c1") == f"{ro} is not a worktree of {change_repo}'s repository"
    assert ((ro / "kept.txt").exists(), git(ro, "rev-parse", "HEAD")) == (True, git(foreign_repo, "rev-parse", "HEAD"))
    git(foreign_repo, "worktree", "remove", "--force", str(ro))
    ro.mkdir()
    (ro / "kept.txt").write_text("someone's\n")
    assert "is not a worktree of" in disposable.prepare(change_repo, store, "c1")
    assert (ro / "kept.txt").exists()
    outside = tmp_path / "c1.ro"
    git(change_repo, "worktree", "add", "-q", "--detach", str(outside))
    assert disposable.custody(change_repo, outside, []) == f"{outside} is not under {worktree.data_root()}"
    assert "is not named" in disposable.custody(change_repo, target, [])


def test_a_refused_read_only_worktree_retries_the_step_without_a_session(store, change_repo, ro, monkeypatch):
    ro.mkdir()
    seen = reviewer(monkeypatch)
    c = reviewed(store, change_repo)
    assert (c.outcome.exit, c.outcome.cause, seen) == (Exit.RETRY, REFUSED, [])
    assert c.outcome.reason == f"{ro} is not a worktree of {change_repo}'s repository"


def test_removal_keeps_a_worktree_whose_processes_are_not_confirmed_gone_or_out_of_custody(tmp_path, change_repo, ro):
    store = Store(tmp_path / "store")
    folder = store.root / "changes" / "c1"
    assert disposable.remove(change_repo, store, "c1") == ""  # nothing to remove
    copy = disposable.prepare(change_repo, store, "c1")
    assert isinstance(copy, disposable.Copy)
    disposable.begin(folder, ro)
    assert "not confirmed gone" in disposable.remove(change_repo, store, "c1")
    disposable.settled(folder)
    assert (disposable.remove(change_repo, store, "c1"), ro.exists()) == ("", False)
    assert str(ro) not in git(change_repo, "worktree", "list")
    target = tmp_path / "target"
    target.mkdir()
    ro.symlink_to(target)
    assert disposable.remove(change_repo, store, "c1") == f"{ro} is a symlink"
    assert (ro.is_symlink(), target.is_dir()) == (True, True)


def states(*checkouts: Path) -> list[tuple[str, str, str]]:
    """Each checkout's branch, HEAD and status, untracked and ignored files included."""
    return [
        (git(c, "symbolic-ref", "HEAD"), git(c, "rev-parse", "HEAD"), git(c, "status", "--porcelain", "--ignored"))
        for c in checkouts
    ]


@pytest.mark.parametrize("into", ["change", "primary"])
def test_a_read_only_worktree_whose_git_file_points_at_another_checkout_is_refused_touching_nothing(
    tmp_path, change_repo, into
):
    store = Store(tmp_path / "store")
    own = worktree.path_for(git_common_dir(change_repo), "c2")
    git(change_repo, "worktree", "add", "-q", "-b", "owlbear/c2", str(own), "main")
    store.write(Lock("c2"), Change(slug="c2", names=Names(branch="owlbear/c2", target="main", worktree=str(own))))
    copy = disposable.prepare(own, store, "c2")
    assert isinstance(copy, disposable.Copy)
    for checkout in (own, change_repo):
        (checkout / "wip.txt").write_text("unsaved\n")  # what a reset or clean there would lose
    (copy.path / "kept.txt").write_text("x\n")
    other = own if into == "change" else change_repo
    (copy.path / ".git").write_text(f"gitdir: {git(other, 'rev-parse', '--path-format=absolute', '--git-dir')}\n")
    before = states(own, change_repo)
    assert disposable.prepare(own, store, "c2") == f"{copy.path} is not a worktree of {own}'s repository"
    assert disposable.remove(change_repo, store, "c2") == f"{copy.path} is not a worktree of {change_repo}'s repository"
    assert states(own, change_repo) == before
    assert ((copy.path / "kept.txt").exists(), (own / "wip.txt").exists(), (change_repo / "wip.txt").exists()) == (
        True,
        True,
        True,
    )


def test_a_change_s_own_worktree_is_never_taken_for_a_read_only_one(tmp_path, change_repo):
    store = Store(tmp_path / "store")
    copy = disposable.prepare(change_repo, store, "c1")
    (copy.path / "kept.txt").write_text("x\n")
    store.write(Lock("c2"), Change(slug="c2", names=Names(worktree=str(copy.path))))  # however it came to be
    assert disposable.prepare(change_repo, store, "c1") == f"{copy.path} is a Change's own worktree"
    assert disposable.remove(change_repo, store, "c1") == f"{copy.path} is a Change's own worktree"
    assert (copy.path / "kept.txt").exists()


def test_a_change_name_never_holds_a_dot(tmp_path):
    store = Store(tmp_path / "store")
    with pytest.raises(ValidationError):
        Change(slug="c1.ro")
    with pytest.raises(StoreError, match=r"c1\.ro"):
        store.read("c1.ro")
    with pytest.raises(StoreError, match=r"c1\.ro"), store.lock("c1.ro"):
        pass
    a = argparse.Namespace(
        change="c1.ro", title="t", outcome="o", criterion=[], scope=[], check=[], install=[], person_check=[],
        target="main",
    )  # fmt: skip
    with pytest.raises(ValidationError):
        cli.seed(store, a)
    assert (store.slugs(), store.read_profile(), (store.root / "changes" / "c1.ro").exists()) == ([], None, False)
    assert briefs.new_slug("Release v1.2 notes", []) == "release-v1-2-notes"


def test_each_window_judge_finds_the_read_only_worktree_reset(tmp_path, change_repo, monkeypatch):
    monkeypatch.setattr(profile_record, "WINDOW_PAUSED", False)
    store, seen = Store(tmp_path / "store"), []
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.CHECK))
    store.write(Lock("c1"), change)
    store.write_profile(Profile(runtime="vscode"))

    def window(cfg, _inbox):
        seen.append((cfg.message, git(cfg.worktree, "status", "--porcelain", "--ignored")))
        (cfg.worktree / "a.txt").write_text("the first judge's edit\n")
        (cfg.worktree / "new.txt").write_text("x\n")
        payload = tools.ReviewResult(verdict="pass")
        return Run(cfg.session_id, "result", payload, head="h", termination=Termination(confirmed=True))

    monkeypatch.setattr(sessions.vscode_adapter, "run", window)
    made = lambda at: [("visual-review", judge(at, "first")), ("design-review", judge(at, "second"))]  # noqa: E731
    ran = sessions.judges(store, Lock("c1"), change, change_repo, made)
    assert seen == [("first", ""), ("second", "")]
    assert [r.exit for r, _ in ran] == [Exit.DONE, Exit.DONE]


def test_a_review_that_moves_a_ref_with_its_usage_unread_is_retried_for_the_violation(store, change_repo, monkeypatch):
    async def fake(cfg):
        git(cfg.worktree, "tag", "probe")
        payload = tools.ReviewResult(verdict="pass", covered_paths=["a.txt"])
        done = Run(cfg.session_id, "result", payload, usage={"credits": 2.0}, usage_unread="no usage event")
        done.termination = Termination(confirmed=True)
        return done

    monkeypatch.setattr(runner.sdk_adapter, "run", fake)
    c = reviewed(store, change_repo)
    assert (c.outcome.exit, c.outcome.cause, loop.open_question(c)) == (Exit.RETRY, VOIDED, None)
    assert (c.budgets.causes[VOIDED].count, list(c.budgets.causes)) == (1, [VOIDED])
    assert not (store.root / "changes" / "c1" / "held.json").exists()
    steps = [e for e in store.events("c1") if e.get("event") == "step"]
    assert [(e["ending"], e["usage_unread"], e["usage"]) for e in steps] == [
        ("read-only-write", "no usage event", {"credits": 2.0})
    ]
    assert c.spend.credits == 2.0


def test_a_review_that_changes_shared_git_settings_stops_for_the_owner_and_nothing_is_restored(
    store, change_repo, monkeypatch
):
    hook = Path(git(change_repo, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "hooks" / "pre-push"

    def act(cfg):
        git(cfg.worktree, "config", "core.hooksPath", "/elsewhere")
        hook.write_text("#!/bin/sh\n")
        git(cfg.worktree, "tag", "probe")  # the shared settings decide, not the moved ref

    reviewer(monkeypatch, act)
    c = reviewed(store, change_repo)
    assert (c.outcome.exit, c.stop.kind) == (Exit.STOP, ErrorKind.POLICY)
    assert "added config core.hookspath=/elsewhere" in c.stop.reason
    assert "added hook pre-push" in c.stop.reason
    assert (git(change_repo, "config", "core.hooksPath"), hook.exists()) == ("/elsewhere", True)
    assert [e["changes"][0] for e in store.events("c1") if e.get("event") == "read-only-tampered"] == [
        "added config core.hookspath=/elsewhere"
    ]


def test_a_review_that_only_sets_a_branch_upstream_passes(store, change_repo, monkeypatch):
    reviewer(monkeypatch, lambda cfg: git(cfg.worktree, "config", "branch.main.remote", "origin"))
    assert reviewed(store, change_repo).outcome.exit == Exit.DONE


def test_a_judge_that_moves_a_ref_with_its_usage_unread_is_retried_for_the_violation(
    tmp_path, change_repo, monkeypatch
):
    store = Store(tmp_path / "store")
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.CHECK))
    store.write(Lock("c1"), change)

    async def fake(cfg):
        git(cfg.worktree, "tag", "probe")
        done = Run(cfg.session_id, "result", tools.ReviewResult(verdict="pass"), usage_unread="no usage event")
        done.termination = Termination(confirmed=True)
        return done

    monkeypatch.setattr(sessions.sdk_adapter, "run", fake)
    ran = sessions.judges(store, Lock("c1"), change, change_repo, lambda at: [("visual-review", judge(at, "m"))])
    assert [(r.exit, r.cause) for r, _ in ran] == [(Exit.RETRY, "policy:check:read-only-write")]
    steps = [e for e in store.events("c1") if e.get("event") == "step"]
    assert [(e["kind"], e["usage_unread"]) for e in steps] == [("visual-review", "no usage event")]
