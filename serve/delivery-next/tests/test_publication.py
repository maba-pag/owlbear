import subprocess
import tarfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, loop, profile
from owlbear_delivery_next.git.remote_git import RemoteGitWriteUnknown, classify_write_readback, read_remote_ref
from owlbear_delivery_next.github import merge_offer
from owlbear_delivery_next.github.provider import (
    Check,
    MergeMethod,
    MergeRequest,
    MergeResult,
    MergeStatus,
    PullRequest,
    Rules,
    classify_checks,
    merge_request_body,
)
from owlbear_delivery_next.models import (
    Brief,
    Change,
    ConsentItem,
    Criterion,
    Environment,
    Exit,
    Inputs,
    Names,
    PersonCheck,
    Plan,
    Profile,
    ProfileEntry,
    Review,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import cleanup, engine, follow, merge, publish
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
A, B = "a" * 40, "b" * 40
FORBIDDEN = Rules(state="unknown", evidence="HTTP 403: Upgrade to GitHub Pro")
TIMED_OUT = "timed out"


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


@pytest.fixture
def clone(tmp_path):
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(work, "switch", "-q", "-c", "owlbear/c1")
    return work


def pr(head=B, **fields):
    base = {"repository": "o/r", "number": 7, "node_id": "n", "url": "https://github.com/o/r/pull/7"}
    base |= {"head_branch": "owlbear/c1", "head_sha": head, "base_branch": "main", "draft": False, "state": "open"}
    return PullRequest(**(base | {"merged": False, "mergeable": True, "merge_state": "clean"} | fields))


class FakeGh:
    def __init__(self, current):
        self.pr, self.merges, self.result = current, [], MergeResult(status=MergeStatus.UNKNOWN)
        self.checks = (Check(name="test", status="completed", conclusion="success"),)
        self.after = None

    def read_rules(self, _repo, _branch):
        return FORBIDDEN

    def read_pull_request(self, _repo, _number):
        return self.pr

    def observe_checks(self, _repo, _number, _head):
        return self.checks

    def compare(self, _repo, base, head):
        return f"1 commit(s): owner edit · files: a.txt ({base[:1]}..{head[:1]})"

    def request_merge(self, request):
        self.merges.append(request)
        self.pr = self.after or self.pr
        return self.result

    def job_log(self, _repo, _job, _lines=40):
        return "AssertionError: fails only in CI"


def prof(**extra):
    entries = {
        profile.REPO: ProfileEntry(state="known", value="o/r"),
        profile.METHOD: ProfileEntry(state="known", value="squash"),
        profile.METHODS: ProfileEntry(state="known", value="squash, merge"),
        profile.PUSH: ProfileEntry(state="known", value="yes"),
        profile.DECLARED: ProfileEntry(state="known", value="test"),
        **profile.rule_entries(FORBIDDEN),
    }
    p = Profile(version=1, entries=entries | extra)
    return profile.confirm(p, profile.RULES, "none", NOW)


def ctx(tmp_path, gh, p=None, repo=None):
    return engine.Ctx(Store(tmp_path / "store"), Lock("c1"), repo or tmp_path, p or prof(), gh, NOW)


def change(kind=StepKind.MERGE, worktree="", **fields):
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["src"], checks=["npm test"])])
    names = Names(branch="owlbear/c1", target="main", worktree=worktree, pr=7)
    return Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=kind), names=names, **fields)


# Consent voiding on head change


def test_consent_holds_only_for_the_exact_head():
    assert merge_offer.consent(None, A) == "missing"
    assert merge_offer.consent(A, A) == "valid"
    assert merge_offer.consent(A, B) == "void"


def test_a_head_change_voids_consent_shows_the_delta_and_asks_again(tmp_path):
    gh = FakeGh(pr(head=B))
    c = loop.fold(change(), [ConsentItem(at=NOW, head=A)], NOW)
    cx = ctx(tmp_path, gh)
    _, result = merge.run(cx, c)
    offer = cx.events("c1", "merge-offer")[-1]
    assert (result.exit, result.cause) == (Exit.ASK, loop.CONSENT)
    assert result.reason.startswith(f"approve merging {B[:7]}, changed since {A[:7]} (1 commit(s)")
    assert (offer["head"], offer["void"]) == (B, A)
    assert gh.merges == []


def test_the_merge_carries_the_consented_head_as_its_sha_guard(tmp_path):
    gh = FakeGh(pr(head=A))
    gh.result = MergeResult(status=MergeStatus.MERGED, sha=B)
    gh.after = pr(head=A, state="closed", merged=True, merge_commit_sha=B)
    c = loop.fold(change(), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.exit, gh.merges[0].expected_head_sha) == (Exit.DONE, A)
    assert merge_request_body(gh.merges[0]) == b'{"merge_method":"squash","sha":"' + A.encode() + b'"}'


class Host:
    wake = type("W", (), {"set": lambda _self: None})()

    def activity(self, _slug):
        return Activity(host_up=True)


def test_consent_api_accepts_only_the_offered_head(tmp_path):
    store = Store(tmp_path / "store")
    c = loop.apply(change(), engine.ask(StepKind.MERGE, "approve merging bbbbbbb", loop.CONSENT), NOW)
    store.write(Lock("c1"), c)
    store.log(Lock("c1"), "c1", {"event": "merge-offer", "head": B, "url": "u", "checks": [], "delta": ""})
    app = api.create_app(store, "t", Host())
    client = TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})
    assert client.post("/api/next/changes/c1/merge-consent", json={"head": A}).status_code == 409
    assert client.post("/api/next/changes/c1/answers", json={"question": "q1"}).status_code == 409
    assert client.post("/api/next/changes/c1/merge-consent", json={"head": B}).json() == {"accepted": "merge-consent"}


def test_a_check_result_is_accepted_only_for_the_inputs_the_page_showed(tmp_path):
    store, url = Store(tmp_path / "store"), "http://127.0.0.1:4173/"
    env = Environment(check="preview", command="npm run preview", directory=".", ready_url=url, ready_at=NOW)
    c = change(StepKind.CHECK, checks=[PersonCheck(id="preview", criteria=["AC-1"])], env=env)
    c.brief.criteria = [Criterion(id="AC-1", text="greets")]
    store.write(Lock("c1"), c)
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )

    def shown():
        return client.get("/api/next/changes/c1").json()["checks"][0]["inputs"]

    old = shown()
    store.write(Lock("c1"), c.model_copy(update={"env": env.model_copy(update={"pids": {9: 1.0}, "launched_at": NOW})}))
    assert shown() == old  # a relaunch alone changes no input
    c.brief.criteria[0].version = 2
    store.write(Lock("c1"), c)
    stale = client.post("/api/next/changes/c1/check-results", json={"check": "preview", "passed": True, "inputs": old})
    assert (stale.status_code, stale.json()["detail"]) == (409, "This check changed since you opened it; reload")
    body = {"check": "preview", "passed": True, "inputs": shown()}
    assert client.post("/api/next/changes/c1/check-results", json=body).json() == {"accepted": "check-result"}


def test_publish_returns_to_the_final_review_unless_head_is_the_final_reviewed_head(clone, tmp_path):
    head = git(clone, "rev-parse", "HEAD")
    final = Review(commit=A, inputs=Inputs(), verdict="pass")
    c = change(StepKind.PUBLISH, worktree=str(clone), reviews=[final])
    _, result = publish.run(ctx(tmp_path, FakeGh(pr())), c)
    assert loop.apply(c, result, NOW).step == Step(kind=StepKind.REVIEW, mode="final")
    assert publish.reviewed(c.model_copy(update={"reviews": [final.model_copy(update={"commit": head})]}), clone, head)


# CI classification


def test_a_missing_declared_check_is_never_passed():
    checks = (
        Check(name="test", status="completed", conclusion="success"),
        Check(name="lint", status="completed", conclusion="failure"),
    )
    state = classify_checks(checks, declared=("test", "build"), required=())
    assert (state.passed, state.missing, state.failed, state.ignored) == (("test",), ("build",), (), ("lint",))


def test_required_and_github_required_checks_are_expected_and_the_latest_run_wins():
    early, late = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
    checks = (
        Check(name="test", status="completed", conclusion="failure", completed_at=late),
        Check(name="test", status="completed", conclusion="success", completed_at=early),
        Check(name="e2e", status="in_progress", required=True),
    )
    state = classify_checks(checks, declared=(), required=("test", "sign"))
    assert [c.name for c in state.failed] == ["test"]
    assert (state.running, state.missing) == (("e2e",), ("sign",))


def test_a_check_that_never_starts_is_pending_then_asks_the_owner(tmp_path):
    gh, state = FakeGh(pr(head=B)), classify_checks((), ("test",), ())
    cx = ctx(tmp_path, gh)
    cx.store.log(cx.lock, "c1", {"event": "publish", "head": B, "at": NOW.isoformat()})
    cx.now = NOW + timedelta(minutes=1)
    _, early = follow.missing(cx, change(StepKind.FOLLOW), gh.pr, state)
    assert (early.exit, early.waiting) == (Exit.PENDING, Waiting.CHECK_START)
    cx.now = NOW + timedelta(minutes=10)
    _, late = follow.missing(cx, change(StepKind.FOLLOW), gh.pr, state)
    assert late.exit == Exit.ASK
    assert "test never started on PR #7" in late.reason


def test_a_failing_check_goes_back_to_build_with_its_log(tmp_path):
    gh = FakeGh(pr(head=B))
    gh.checks = (Check(name="test", status="completed", conclusion="failure", job_id=9),)
    _, result = follow.run(ctx(tmp_path, gh), change(StepKind.FOLLOW))
    assert (result.exit, result.back_to, result.cause) == (Exit.BACK, StepKind.BUILD, "checks:follow:test")
    assert result.fix_task.origin == "ci"
    assert "fails only in CI" in result.fix_task.detail


# Readback decisions on unknown push and merge results


def test_write_readback_replays_only_on_confirmed_absence():
    assert classify_write_readback(A, intended=A, expected_old=None) == "applied"
    assert classify_write_readback(None, intended=A, expected_old=None) == "not-applied"
    assert classify_write_readback(B, intended=A, expected_old=None) == "conflict"
    assert merge_offer.readback(pr(head=A, state="closed", merged=True, merge_commit_sha=B), A) == "applied"
    assert merge_offer.readback(pr(head=A), A) == "not-applied"
    assert merge_offer.readback(pr(head=B), A) == "conflict"


@pytest.mark.parametrize(("applied", "pushes"), [(True, 1), (False, 2)])
def test_an_unknown_push_is_read_back_and_replayed_only_when_absent(clone, monkeypatch, applied, pushes):
    real, calls = publish.run_remote_git, []

    def flaky(path, args, *, kind):
        calls.append(args)
        if len(calls) == 1:
            if applied:
                real(path, args, kind=kind)
            raise RemoteGitWriteUnknown(TIMED_OUT, timed_out=True)
        return real(path, args, kind=kind)

    monkeypatch.setattr(publish, "run_remote_git", flaky)
    (clone / "b.txt").write_text("b\n")
    git(clone, "add", "b.txt")
    git(clone, "commit", "-q", "-m", "b")
    head = git(clone, "rev-parse", "HEAD")
    assert publish.push(clone, change(StepKind.PUBLISH), head) is None
    assert (len(calls), read_remote_ref(clone, "origin", "refs/heads/owlbear/c1")) == (pushes, head)


@pytest.mark.parametrize(("after", "exit_"), [("merged", Exit.DONE), ("open", Exit.RETRY)])
def test_an_unknown_merge_is_read_back_before_any_replay(tmp_path, after, exit_):
    gh = FakeGh(pr(head=A))
    if after == "merged":
        gh.after = pr(head=A, state="closed", merged=True, merge_commit_sha=B)
    c = loop.fold(change(), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.exit, len(gh.merges)) == (exit_, 1)
    if exit_ == Exit.RETRY:
        assert result.cause == "network:merge:merge"


def test_a_required_queue_is_submitted_without_bypass_and_enqueued_is_pending(tmp_path):
    body = merge_request_body(
        MergeRequest(repository="o/r", number=1, expected_head_sha=A, method=MergeMethod.SQUASH, queue=True)
    )
    assert b'"bypass_rules":false' in body
    assert b"merge_action" not in body
    queued = Rules(state="known", evidence="rules merge_queue", types=("merge_queue",), queue_required=True)
    decision = merge_offer.decide(
        pr(head=A),
        target="main",
        ci=classify_checks((), (), ()),
        rules=queued,
        rules_confirmed=True,
        method=MergeMethod.SQUASH,
        methods=(MergeMethod.SQUASH,),
        can_push=True,
    )
    assert decision.action == "queue"
    gh = FakeGh(pr(head=A))
    gh.result = MergeResult(status=MergeStatus.ENQUEUED)
    c = loop.fold(change(), [ConsentItem(at=NOW, head=A)], NOW)
    result = merge.submit(ctx(tmp_path, gh), c, gh.pr, queue=True)
    assert (result.exit, result.waiting, gh.merges[0].queue) == (Exit.PENDING, Waiting.MERGE_QUEUE, True)


def test_unknown_rules_make_merging_human_assisted(tmp_path):
    gh = FakeGh(pr(head=A))
    p = prof().model_copy(update={"entries": prof().entries | profile.rule_entries(FORBIDDEN)})
    c = loop.fold(change(), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh, p), c)
    assert (result.exit, result.who, result.waiting) == (Exit.PENDING, "you", Waiting.OWNER_ACTION)
    assert "merge PR #7 in GitHub" in result.reason
    assert gh.merges == []


# Preservation: nothing is lost before the worktree is removed


@pytest.fixture
def worktree_with_work(clone, tmp_path):
    git(clone, "switch", "-q", "main")
    wt = tmp_path / "wt"
    git(clone, "worktree", "add", "-q", str(wt), "-b", "owlbear/c2")
    (wt / "kept.txt").write_text("unmerged\n")
    git(wt, "add", "kept.txt")
    git(wt, "commit", "-q", "-m", "unmerged")
    (wt / "a.txt").write_text("edited\n")
    (wt / "staged.txt").write_text("staged\n")
    git(wt, "add", "staged.txt")
    (wt / "new.txt").write_text("untracked\n")
    return clone, wt


def test_inventory_finds_unmerged_commits_and_every_uncommitted_path(worktree_with_work):
    _, wt = worktree_with_work
    inv = cleanup.inventory(wt, "owlbear/c2", ["origin/main", "absent-ref"])
    assert len(inv.commits) == 1
    assert sorted(inv.dirty) == ["a.txt", "new.txt", "staged.txt"]


def test_cleanup_removes_the_worktree_only_after_bundle_and_archive_verify(worktree_with_work, tmp_path):
    clone, wt = worktree_with_work
    c = change(StepKind.CLEANUP, worktree=str(wt))
    c.names.branch, c.names.pr = "owlbear/c2", None
    _, result = cleanup.run(ctx(tmp_path, FakeGh(pr()), repo=clone), c)
    assert result.exit == Exit.DONE
    assert not wt.exists()
    bundle, archive = result.preserved
    assert git(clone, "bundle", "verify", "--quiet", bundle) == ""
    with tarfile.open(archive) as tar:
        assert {"changes.diff", "index.txt", "files/a.txt", "files/new.txt", "files/staged.txt"} <= set(tar.getnames())
        assert tar.extractfile("files/new.txt").read() == b"untracked\n"


def test_failed_preservation_stops_and_leaves_the_worktree_untouched(worktree_with_work, tmp_path, monkeypatch):
    clone, wt = worktree_with_work

    def broken(*_args):
        raise cleanup.PreservationError(wt)

    monkeypatch.setattr(cleanup, "preserve", broken)
    c = change(StepKind.CLEANUP, worktree=str(wt))
    c.names.branch, c.names.pr = "owlbear/c2", None
    _, result = cleanup.run(ctx(tmp_path, FakeGh(pr()), repo=clone), c)
    assert result.exit == Exit.STOP
    assert result.stop.action.startswith(f"Copy or delete {wt}")
    assert (wt / "new.txt").read_text() == "untracked\n"
    assert (wt / "kept.txt").exists()
