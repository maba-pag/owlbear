import json
import subprocess
import tarfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import evidence, failures, tool_schema, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, ConsentItem, IntentItem, RestartItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Criterion,
    Environment,
    ErrorKind,
    Exit,
    Inputs,
    ItemRef,
    MergeConsent,
    Names,
    PersonCheck,
    Plan,
    Question,
    QueueClaim,
    Response,
    Review,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.round_records import RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import budgets, loop, round_flow, worktree
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.git.remote_git import RemoteGitWriteUnknown, classify_write_readback, read_remote_ref
from owlbear_delivery_next.github import gh_queue, merge_offer
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.provider import (
    Check,
    CiState,
    ConversationItem,
    EnqueueResult,
    EnqueueStatus,
    FailureCode,
    GroupRun,
    MergeMethod,
    MergeResult,
    MergeStatus,
    ProviderError,
    PullRequest,
    QueueEntry,
    QueueEvent,
    QueueState,
    Refusal,
    Repository,
    Rules,
    ThreadComment,
    classify_checks,
    merge_request_body,
)
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host import host as scheduler
from owlbear_delivery_next.runtimes.readiness import Check as SetupCheck
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import Lock, SharedError, Store
from owlbear_delivery_next.workflow_steps import (
    check,
    cleanup,
    conversation,
    disposable,
    engine,
    follow,
    merge,
    publish,
    queue,
    review,
)

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
A, B = "681d75b8f76e8c9a53053a9054812a449926e2aa", "b" * 40  # A: the clone fixture's base commit (fixed dates)
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
        monkeypatch.setenv(f"GIT_{who}_DATE", "2026-10-10T12:00:00Z")


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
    assert git(work, "rev-parse", "HEAD") == A
    return work


def pr(head=B, **fields):
    base = {"repository": "o/r", "number": 7, "node_id": "n", "url": "https://github.com/o/r/pull/7"}
    base |= {"head_branch": "owlbear/c1", "head_sha": head, "base_branch": "main", "draft": False, "state": "open"}
    return PullRequest(**(base | {"merged": False, "mergeable": True, "merge_state": "clean"} | fields))


class FakeGh:
    def __init__(self, current):
        self.pr, self.merges, self.result = current, [], MergeResult(status=MergeStatus.UNKNOWN)
        self.checks = (Check(name="test", status="completed", conclusion="success"),)
        self.after, self.reopened, self.commit_checks, self.review = None, [], (), (None, ())

    def observe_commit_checks(self, _repo, _sha):
        return self.commit_checks

    def review_request(self, _repo, _number):
        return self.review

    def mark_ready(self, _pr):
        return None

    def reopen_pull_request(self, _repo, number):
        self.reopened.append(number)
        self.pr = self.pr.model_copy(update={"state": "open"})

    def read_conversation(self, _repo, _number):
        return ()

    def viewer(self):
        return "delivery"

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


ASKING = {profile.ASK: ProfileEntry(state="known", value="yes")}


def ctx(tmp_path, gh, p=None, repo=None):
    return engine.Ctx(Store(tmp_path / "store"), Lock("c1"), repo or tmp_path, p or prof(), gh, NOW)


def change(kind=StepKind.MERGE, worktree="", head=A, **fields):
    if kind == StepKind.MERGE:
        fields.setdefault("reviews", [Review(commit=head, inputs=Inputs(), verdict="pass")])
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["src"], checks=["npm test"])])
    names = Names(branch="owlbear/c1", target="main", worktree=worktree, pr=7)
    return Change(slug="c1", brief=Brief(version=1), plan=plan, step=Step(kind=kind), names=names, **fields)


# Consent voiding on head change


def test_consent_holds_only_for_the_exact_head():
    assert merge_offer.consent(None, A) == "missing"
    assert merge_offer.consent(A, A) == "valid"
    assert merge_offer.consent(A, B) == "void"


def test_a_head_change_voids_consent_shows_the_delta_and_asks_again(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    c = change(worktree=str(clone))
    c.consent = MergeConsent(head=B, at=NOW)  # given while B waited for it
    cx = ctx(tmp_path, gh, prof(**ASKING))
    _, result = merge.run(cx, c)
    offer = cx.events("c1", "merge-offer")[-1]
    assert (result.exit, result.cause) == (Exit.ASK, loop.CONSENT)
    assert result.reason.startswith(f"approve merging {A[:7]}, changed since {B[:7]} (1 commit(s)")
    assert (offer["head"], offer["void"]) == (A, B)
    assert gh.merges == []


def test_a_locally_integrated_but_unpublished_head_goes_back_to_publish_and_never_merges(tmp_path, clone):
    git(clone, "commit", "-q", "--allow-empty", "-m", "integrated locally")
    gh = FakeGh(pr(head=A))
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    cause = failures.cause_key(ErrorKind.GATE, StepKind.MERGE, "local-head")
    assert (result.exit, result.back_to, result.cause) == (Exit.BACK, StepKind.PUBLISH, cause)
    assert gh.merges == []


def test_a_pr_head_someone_else_pushed_goes_back_to_publish_without_reading_it_locally(tmp_path, clone):
    gh = FakeGh(pr(head="f" * 40))  # an owner commit on the PR branch, never fetched into the worktree (live G2)
    final = Review(commit=A, inputs=Inputs(), verdict="pass", tree=git(clone, "rev-parse", "HEAD^{tree}"))
    c = loop.fold(change(worktree=str(clone), reviews=[final]), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh, prof(**ASKING)), c)
    cause = failures.cause_key(ErrorKind.GATE, StepKind.MERGE, "review")
    assert (result.exit, result.back_to, result.cause) == (Exit.BACK, StepKind.PUBLISH, cause)
    assert gh.merges == []


def test_unknown_declared_checks_ask_the_owner_once_per_workflow_digest_before_merging(tmp_path, clone):
    head, entries = ci_head(clone, "${{ inputs.n }}")
    gh = FakeGh(pr(head=head))
    gh.checks = ()
    p = prof(**entries)
    cx = ctx(tmp_path, gh, p)
    cx.store.root.mkdir()
    c, result = merge.run(cx, change(worktree=str(clone), head=head))
    assert (result.exit, [o.id for o in result.question.options]) == (Exit.ASK, ["none", "names", "pause"])
    assert result.cause.endswith(f"declared-{profile.digest_of(entries[profile.DECLARED])}")
    assert gh.merges == []
    c = loop.apply(c, result, NOW)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=c.outcome.question, option="none")], NOW)
    saving = cx.store.write_profile

    def locked(_profile) -> None:
        msg = "the shared settings are locked"
        raise SharedError(msg)

    cx.store.write_profile = locked
    assert follow.declared(cx, c, gh.pr, StepKind.MERGE) == ((), None)  # the answer holds though unsaved
    assert [e["reason"] for e in cx.store.events(c.slug) if e.get("event") == "profile-not-saved"] == [
        "the shared settings are locked"
    ]
    cx.store.write_profile, cx.profile = saving, p
    names, held = follow.declared(cx, c, gh.pr, StepKind.MERGE)
    assert (names, held, profile.value(cx.profile, profile.DECLARED)) == ((), None, "none")
    assert profile.known(cx.store.read_profile(), profile.DECLARED)


def _commit_workflow(clone, name, text):
    (clone / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (clone / ".github" / "workflows" / name).write_text(text)
    git(clone, "add", ".github")
    git(clone, "commit", "-q", "-m", f"add {name}")
    return git(clone, "rev-parse", "HEAD")


def ci_head(clone, *names):
    """Commit a pull-request workflow whose jobs report *names*; return the head and the profile's CI entries there."""
    jobs = "".join(f'  j{i}: {{name: "{n}", runs-on: x}}\n' for i, n in enumerate(names))
    head = _commit_workflow(clone, "ci.yml", f"on: pull_request\njobs:\n{jobs}")
    texts = profile.workflow_texts_at(clone, head)
    return head, profile.ci_entries({n: profile.workflow(t) for n, t in texts.items()}, profile.flows_digest(texts))


def test_a_none_confirmation_does_not_survive_a_workflow_the_change_adds(tmp_path, clone):
    texts = profile.workflow_texts_at(clone, A)
    detected = profile.ci_entries({}, profile.flows_digest(texts))[profile.DECLARED]
    p = prof(**{profile.DECLARED: detected.model_copy(update={"state": "unknown"})})
    cx = ctx(tmp_path, FakeGh(pr(head=A)), profile.confirm(p, profile.DECLARED, "none", NOW))
    cx.store.root.mkdir()
    assert follow.declared(cx, change(worktree=str(clone)), cx.gh.pr, StepKind.FOLLOW) == ((), None)
    matrix = "on: pull_request\njobs:\n  t:\n    strategy: {matrix: {os: [a, b]}}\n"
    head = _commit_workflow(clone, "matrix.yml", matrix)
    gh = FakeGh(pr(head=head))
    gh.checks = (Check(name="t (a)", status="completed", conclusion="failure"),)
    cx.gh = gh
    c = change(StepKind.FOLLOW, worktree=str(clone), head=head)
    c, result = follow.run(cx, c)
    assert (result.exit, "workflows changed" in result.reason) == (Exit.ASK, True)
    assert follow.run(cx, c)[1].cause == result.cause  # asked once per digest
    c = loop.apply(c, result, NOW)
    answer = AnswerItem(at=NOW, question=c.outcome.question, option="names", text="t (a), t (b)")
    c, _ = loop.schedule(c, [answer], NOW)
    _, result = follow.run(cx, c)
    assert (result.exit, result.back_to, result.fix_task.title) == (
        Exit.BACK,
        StepKind.BUILD,
        "Fix the failing CI check t (a)",
    )
    assert profile.value(cx.profile, profile.DECLARED) == "none"  # the Change's answer does not rewrite the profile


def test_the_merge_carries_the_consented_head_as_its_sha_guard(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    gh.result = MergeResult(status=MergeStatus.MERGED, sha=B)
    gh.after = pr(head=A, state="closed", merged=True, merge_commit_sha=B)
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.exit, gh.merges[0].expected_head_sha) == (Exit.DONE, A)
    assert merge_request_body(gh.merges[0]) == b'{"merge_method":"squash","sha":"' + A.encode() + b'"}'


def test_a_review_comment_after_ci_goes_back_to_build_before_any_merge(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    item = ConversationItem(id="r9", kind="comment", author="o", body="throw on zero")
    gh.read_conversation = lambda _repo, _number: (item,)
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    c, result = merge.run(ctx(tmp_path, gh), c)
    tid = f"pr-r9-{conversation.version(item, [('r9', 'throw on zero')])[:8]}"
    assert (result.exit, result.back_to, result.fix_task.id) == (Exit.BACK, StepKind.BUILD, tid)
    assert gh.merges == []
    after = loop.apply(c, result, NOW)
    assert (after.step.kind, after.step.task) == (StepKind.BUILD, tid)


# Pull-request conversation items (TD-15, TD-16)


class ChatGh(FakeGh):
    def __init__(self, current, *items):
        super().__init__(current)
        self.items, self.posts, self.resolved, self.before_post, self.ack = list(items), [], [], None, True

    def read_conversation(self, _repo, _number):
        return tuple(self.items)

    def post_reply(self, _repo, _number, item, body):
        if self.before_post:
            self.before_post()
        rid = f"reply{len(self.posts) + 1}"
        self.posts.append((item.id, body))
        if item.kind == "thread":
            self.add(item.id, (rid, "delivery", body))
        else:
            quoted = f"> {item.url}\n\n{body}"
            self.items.append(comment(rid, quoted, "delivery"))
        return rid

    def resolve_thread(self, thread_id):
        self.resolved.append(thread_id)
        if self.ack:
            self.items = [i.model_copy(update={"resolved": True}) if i.id == thread_id else i for i in self.items]
        return self.ack

    def add(self, tid, *new):
        old = next(i for i in self.items if i.id == tid)
        notes = [(x.id, x.author, x.body) for x in old.comments]
        self.items[self.items.index(old)] = thread(tid, *notes, *new, resolved=old.resolved, outdated=old.outdated)


def comment(cid, body, author="o", kind="comment", *, bot=False):
    url = f"https://github.com/o/r/pull/7#{cid}"
    return ConversationItem(id=cid, kind=kind, author=author, body=body, url=url, bot=bot)


def thread(tid, *comments, resolved=False, outdated=False):
    notes = tuple(ThreadComment(id=i, author=a, body=b) for i, a, b in comments)
    return ConversationItem(
        id=tid,
        kind="thread",
        author=notes[0].author,
        body="\n".join(f"{n.author}: {n.body}" for n in notes),
        url=f"https://github.com/o/r/pull/7#{tid}",
        path="src/a.py",
        resolved=resolved,
        outdated=outdated,
        comments=notes,
    )


def handled(c, result, how, text, commit=None):
    """Apply the back-to-build result and mark its task done with the Builder's accepted response."""
    c = loop.apply(c, result, NOW)
    task = next(t for t in c.plan.tasks if t.id == result.fix_task.id)
    task.done, task.response = True, Response(how=how, text=text, commit=commit)
    return c


def test_an_answered_comment_is_replied_to_once_and_then_the_merge_proceeds(tmp_path, clone):
    gh = ChatGh(pr(head=A), comment("c1", "why not a dict?"))
    gh.result = MergeResult(status=MergeStatus.MERGED, sha=B)
    gh.after = pr(head=A, state="closed", merged=True, merge_commit_sha=B)
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    cx = ctx(tmp_path, gh)
    c, result = merge.run(cx, c)
    tid = result.fix_task.id
    assert (result.exit, tid[:6], result.fix_task.item.kind) == (Exit.BACK, "pr-c1-", "comment")
    c = handled(c, result, "answered", "A list keeps the order.")
    c = c.model_copy(update={"step": Step(kind=StepKind.MERGE)})
    c = loop.fold(c, [ConsentItem(at=NOW, head=A)], NOW)
    c, result = merge.run(cx, c)
    assert result.exit == Exit.DONE, result.reason
    assert len(gh.posts) == 1
    assert gh.posts[0][1] == f"A list keeps the order.\n\n<!-- delivery:c1:c1:{tid} -->"
    assert [(h.item, h.how, h.reply_id) for h in c.handled] == [("c1", "answered", "reply1")]
    assert follow.conversation(cx, c, gh.pr, StepKind.MERGE)[1] is None
    assert len(gh.posts) == 1
    assert [e["item"] for e in cx.events("c1", "reply")] == ["c1"]


def test_a_bot_comment_handled_as_no_action_posts_nothing_and_records_the_reason(tmp_path):
    gh = ChatGh(pr(head=A), comment("b1", "Coverage: 91%", "github-actions", bot=True))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    assert result.fix_task.item.bot
    c = handled(c, result, "no-action", "automated coverage notice")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.posts) == (None, [])
    assert [(h.how, h.text, h.reply_id) for h in c.handled] == [("no-action", "automated coverage notice", None)]
    store = Store(tmp_path / "api")
    store.write(Lock("c1"), c)
    app = api.create_app(store, "t", Host())
    client = TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})
    shown = client.get("/api/next/changes/c1").json()["handled"]
    assert [(h["item"], h["how"], h["text"]) for h in shown] == [("b1", "no-action", "automated coverage notice")]


def test_a_fixed_thread_is_published_before_its_reply_names_the_pr_head_then_resolved(tmp_path, clone):
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    base = git(clone, "rev-parse", "HEAD")
    (clone / "a.txt").write_text("fixed\n")
    git(clone, "commit", "-qam", "fix")
    fix = git(clone, "rev-parse", "HEAD")
    gh = ChatGh(pr(head=base), thread("t1", ("h1", "o", "off by one")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(worktree=str(clone)), gh.pr, StepKind.FOLLOW)
    tid = result.fix_task.id
    assert tid.startswith("pr-t1-")
    c = handled(c, result, "fixed", "Now counts from zero.", fix)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.back_to, gh.posts, c.handled) == (Exit.BACK, StepKind.PUBLISH, [], [])
    (clone / "b.txt").write_text("later\n")
    git(clone, "add", "b.txt")
    git(clone, "commit", "-qm", "later")
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    head = git(clone, "rev-parse", "HEAD")
    gh.pr = pr(head=head)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert result is None
    assert gh.posts == [("t1", f"Now counts from zero.\n\nFixed in {head[:7]}.\n\n<!-- delivery:c1:t1:{tid} -->")]
    assert gh.resolved == ["t1"]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.resolved) == (None, ["t1"])
    assert [(h.item, h.how, h.resolved) for h in c.handled] == [("t1", "fixed", True)]


def test_a_reply_whose_acknowledgement_was_lost_is_not_posted_again(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    c = handled(c, result, "answered", "Answered.")
    gh.items.append(comment("x1", f"> url\n\nAnswered.\n\n<!-- delivery:c1:c1:{result.fix_task.id} -->", "delivery"))
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.posts) == (None, [])
    assert [h.reply_id for h in c.handled] == ["x1"]


def test_a_person_commenting_during_the_fix_keeps_the_thread_open_with_a_new_task(tmp_path):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "rename it")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.item.version
    c = handled(c, result, "fixed", "Renamed.", A)
    gh.before_post = lambda: gh.add("t1", ("h2", "o", "also the test"))
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert len(gh.posts) == 1
    assert gh.resolved == []
    assert [(h.item, h.resolved) for h in c.handled] == [("t1", False)]
    assert (result.exit, result.fix_task.item.version != first) == (Exit.BACK, True)
    assert result.fix_task.id == f"pr-t1-{result.fix_task.item.version[:8]}"


def task_for(c, item, tid):
    """A plan task carrying a conversation item reference, as an earlier round left it."""
    ref = ItemRef(id=item, kind="thread", version="old", task=tid)
    c.plan.tasks.append(Task(id=tid, title="answer", item=ref))
    return conversation.marker(c.slug, item, tid)


def test_a_wrong_premise_on_a_review_request_asks_the_owner_instead_of_replanning_the_change():
    ref = ItemRef(id="t1", kind="thread", version="v", task="pr-t1-v", url="https://x/pull/7#r1")
    task = Task(id="pr-t1-v", title="answer", item=ref, detail="boecht: handle min > max\n\nhttps://x/pull/7#r1")
    replan = loop.StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause="scope:build:brief", reason="not in brief")
    premise = tools.WrongPremise(stage="brief", reason="not in the brief", evidence=["src/math.ts:1"])
    asked = conversation.disputed(task, premise, replan)
    assert (asked.exit, asked.back_to, [o.next for o in asked.question.options]) == (
        Exit.ASK,
        None,
        [StepKind.BUILD, StepKind.BUILD, "pause"],
    )
    assert "handle min > max" in asked.question.text
    assert "not in the brief" in asked.question.text
    target = tools.WrongPremise(stage="target", reason="needs main", evidence=["x"])
    assert conversation.disputed(task, target, replan) is replan  # a missing target commit still integrates
    assert conversation.disputed(Task(id="t", title="plan task"), premise, replan) is replan


def test_a_person_quoting_a_full_delivery_marker_still_opens_a_task(tmp_path):
    c = change()
    mark = task_for(c, "c9", "pr-c9-old")
    gh = ChatGh(pr(head=A), comment("d1", f"Done.\n\n{mark}", "delivery"), comment("c2", f"quoting {mark}", "o"))
    c, result = follow.conversation(ctx(tmp_path, gh), c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.fix_task.item.id) == (Exit.BACK, "c2")
    assert [s.item.id for s in conversation.open_items(c, gh.items, lambda: "delivery")] == ["c2"]


def test_an_unresolved_thread_ending_with_delivery_is_open_while_a_person_is_unanswered(tmp_path):
    c = change()
    mark = task_for(c, "t1", "pr-t1-old")
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "q"), ("d1", "delivery", f"Done.\n\n{mark}")))
    c, result = follow.conversation(ctx(tmp_path, gh), c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.fix_task.item.id, result.fix_task.id != "pr-t1-old") == (Exit.BACK, "t1", True)


def test_editing_a_handled_issue_comment_reopens_it_with_a_new_task(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "answered", "Because.")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert result is None
    gh.items[0] = comment("c1", "why? and why a list?")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.fix_task.id[:6], result.fix_task.id != first) == (Exit.BACK, "pr-c1-", True)


def test_deleting_the_latest_person_comment_does_not_spin(tmp_path):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "rename it")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    c = handled(c, result, "answered", "Renamed.")
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    c.step = Step(kind=StepKind.FOLLOW)
    gh.add("t1", ("h2", "o", "and the test"))
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    c = loop.apply(c, result, NOW)
    c.step = Step(kind=StepKind.FOLLOW)
    c, again = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (again.exit, again.fix_task.id) == (Exit.BACK, result.fix_task.id)
    c = loop.apply(c, again, NOW)
    old = gh.items[0]
    gh.items = [thread("t1", *[(x.id, x.author, x.body) for x in old.comments if x.id != "h2"], resolved=old.resolved)]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert result is None
    assert sum(t.id.startswith("pr-t1-") for t in c.plan.tasks) == 2


def test_a_deleted_delivery_reply_is_reposted_after_looking_for_a_replay(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    tid = result.fix_task.id
    c = handled(c, result, "answered", "Because.")
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    gh.items = [i for i in gh.items if i.id != "reply1"]
    gh.items.append(comment("x9", f"Because.\n\n<!-- delivery:c1:c1:{tid} -->", "delivery"))
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, len(gh.posts), c.handled[0].reply_id) == (None, 1, "x9")
    gh.items = [i for i in gh.items if i.id != "x9"]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, len(gh.posts), c.handled[0].reply_id) == (None, 2, "reply2")
    assert gh.posts[1] == ("c1", f"Because.\n\n<!-- delivery:c1:c1:{tid} -->")


def test_a_thread_a_person_unresolves_after_delivery_resolved_it_opens_again_unresolved(tmp_path):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "why?")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "answered", "Because.")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.resolved, c.handled[0].resolved) == (None, ["t1"], True)
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (gh.resolved, c.handled[0].resolved) == (["t1"], True)
    gh.items = [i.model_copy(update={"resolved": False}) for i in gh.items]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.fix_task.id, gh.resolved) == (Exit.BACK, f"{first}-2", ["t1"])


def test_an_unacknowledged_resolve_holds_the_merge_until_a_read_shows_it(tmp_path):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "why?")))
    gh.ack = False
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    c = handled(c, result, "answered", "Because.")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.waiting, c.handled[0].resolved) == (Exit.PENDING, Waiting.GITHUB, False)
    gh.items = [i.model_copy(update={"resolved": True}) for i in gh.items]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, c.handled[0].resolved) == (None, True)


def test_a_resolved_thread_whose_human_comment_was_edited_reopens(tmp_path):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "why?")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "answered", "Because.")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.items[0].resolved) == (None, True)
    notes = [(x.id, x.author, "why? and why a list?" if x.id == "h1" else x.body) for x in gh.items[0].comments]
    gh.items = [thread("t1", *notes, resolved=True)]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.fix_task.id[:6], result.fix_task.id != first) == (Exit.BACK, "pr-t1-", True)


def test_a_resolved_thread_whose_fix_was_rewritten_away_reopens(tmp_path, clone):
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    base = git(clone, "rev-parse", "HEAD")
    (clone / "a.txt").write_text("fixed\n")
    git(clone, "commit", "-qam", "fix")
    fix = git(clone, "rev-parse", "HEAD")
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    gh = ChatGh(pr(head=fix), thread("t1", ("h1", "o", "off by one")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(worktree=str(clone)), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "fixed", "Counts from zero.", fix)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.items[0].resolved) == (None, True)
    git(clone, "push", "-q", "-f", "origin", f"{base}:refs/heads/owlbear/c1")
    gh.pr = pr(head=base)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.back_to, result.fix_task.id) == (Exit.BACK, StepKind.BUILD, f"{first}-2")


def test_a_person_editing_during_a_repost_is_reassessed_and_blocks_the_merge(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "answered", "Because.")
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    gh.items = [i for i in gh.items if i.id != "reply1"]
    gh.before_post = lambda: gh.items.__setitem__(0, comment("c1", "why? and why a list?"))
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert len(gh.posts) == 2
    assert (result.exit, result.fix_task.id != first) == (Exit.BACK, True)


def test_the_fourth_repost_of_a_disappearing_reply_asks_the_owner(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    c = handled(c, result, "answered", "Because.")
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    for _ in range(3):
        gh.items = [i for i in gh.items if i.author != "delivery"]
        c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
        assert result is None
    assert (len(gh.posts), c.handled[0].reposts) == (4, 3)
    gh.items = [i for i in gh.items if i.author != "delivery"]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert result.exit == Exit.ASK
    assert result.question.text == (
        "Delivery's reply on https://github.com/o/r/pull/7#c1 keeps disappearing; "
        "reply manually or let Delivery post again"
    )
    assert len(gh.posts) == 4


def _no_user(*_):
    return subprocess.CompletedProcess((), 1, b"", b"HTTP 403: Resource not accessible by integration")


def test_an_empty_conversation_passes_with_a_credential_that_cannot_read_the_viewer(tmp_path):
    gh = ChatGh(pr(head=A))
    gh.viewer = GhProvider(tmp_path, runner=_no_user).viewer
    assert follow.conversation(ctx(tmp_path, gh), change(), gh.pr, StepKind.FOLLOW)[1] is None


def test_a_pending_replay_with_a_credential_that_cannot_read_the_viewer_names_gh_auth_login(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    c = handled(c, result, "answered", "Answered.")
    gh.items.append(comment("x1", f"Answered.\n\n<!-- delivery:c1:c1:{result.fix_task.id} -->", "delivery"))
    gh.viewer = GhProvider(tmp_path, runner=_no_user).viewer
    with pytest.raises(ProviderError) as raised:
        follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (raised.value.code, raised.value.retry_safe) == (FailureCode.AUTHENTICATION_REQUIRED, False)
    assert gh.posts == []
    asked = engine.failed(c, raised.value, NOW)
    assert (asked.exit, "/user" in asked.reason, "gh auth login" in asked.reason) == (Exit.ASK, True, True)


def test_a_force_rewritten_head_without_the_fix_reopens_the_handled_item(tmp_path, clone):
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    base = git(clone, "rev-parse", "HEAD")
    (clone / "a.txt").write_text("fixed\n")
    git(clone, "commit", "-qam", "fix")
    fix = git(clone, "rev-parse", "HEAD")
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    gh = ChatGh(pr(head=fix), comment("c1", "off by one"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(worktree=str(clone)), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "fixed", "Counts from zero.", fix)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, len(gh.posts)) == (None, 1)
    git(clone, "push", "-q", "-f", "origin", f"{base}:refs/heads/owlbear/c1")
    gh.pr = pr(head=base)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.back_to, result.fix_task.id) == (Exit.BACK, StepKind.BUILD, f"{first}-2")


def test_a_review_repair_of_a_conversation_task_replies_with_its_response_and_the_published_head(tmp_path, clone):
    (clone / "a.txt").write_text("fixed\n")
    git(clone, "commit", "-qam", "fix")
    fix = git(clone, "rev-parse", "HEAD")
    commit(clone, "later.txt")
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    head = git(clone, "rev-parse", "HEAD")
    gh = ChatGh(pr(head=head), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(worktree=str(clone)), gh.pr, StepKind.FOLLOW)
    c = handled(c, result, "answered", "First answer.")
    root = c.plan.tasks[-1]
    review_, _ = tool_schema.parse(
        tools.ReviewResult,
        {"verdict": "fix", "findings": [{"place": "a", "problem": "p", "fix": "f"}], "covered_paths": ["a.txt"]},
    )
    c.step = Step(kind=StepKind.REVIEW, task=root.id)
    run = Run("s", "result", review_, head=worktree.head(clone))
    repair = review.recorded(c, root, run, clone, loop.StepResult(exit=Exit.RETRY, reason="cut")).fix_task
    assert repair.item == root.item
    repair.done, repair.response = True, Response(how="fixed", text="Repaired.", commit=fix)
    c.plan.tasks.append(repair)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert result is None
    assert gh.posts == [("c1", f"Repaired.\n\nFixed in {head[:7]}.\n\n<!-- delivery:c1:c1:{root.id} -->")]
    assert [(h.how, h.text) for h in c.handled] == [("fixed", "Repaired.")]


@pytest.mark.parametrize("callback", ["delivered", "replaced"])
def test_a_builder_response_survives_the_session_replacing_the_change_and_is_replied(
    tmp_path, clone, monkeypatch, callback
):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, opened = follow.conversation(cx, change(worktree=str(clone)), gh.pr, StepKind.FOLLOW)
    tid = opened.fix_task.id
    cx.store.write(cx.lock, loop.apply(c, opened, NOW))
    built = tools.BuildResult(summary="s", changed_paths=[], checks=[], response={"how": "fixed", "text": "Done."})

    async def build(cfg):
        getattr(cfg.journal, callback)()  # rebinds the runner's ``change`` to a copy mid-session
        commit(clone, "fix.txt")
        head = git(clone, "rev-parse", "HEAD")
        return Run(cfg.session_id, "result", built, head=head, termination=processes.Termination(confirmed=True))

    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: clone)
    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._agent(cx.store, cx.lock, cx.store.read("c1"), clone)  # noqa: SLF001
    after, head = cx.store.read("c1"), git(clone, "rev-parse", "HEAD")
    task = next(t for t in after.plan.tasks if t.id == tid)
    assert task.response == Response(how="fixed", text="Done.", commit=head)
    task.done = True  # the task review passed
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/owlbear/c1")
    gh.pr = pr(head=head)
    _, held = follow.conversation(cx, after, gh.pr, StepKind.FOLLOW)
    assert held is None
    assert gh.posts == [("c1", f"Done.\n\nFixed in {head[:7]}.\n\n<!-- delivery:c1:c1:{tid} -->")]


def test_an_unresolved_outdated_thread_blocks_the_merge(tmp_path, clone):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "stale?"), outdated=True))
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.exit, result.fix_task.id[:6], gh.merges) == (Exit.BACK, "pr-t1-", [])


def test_an_open_item_whose_task_is_unfinished_goes_back_to_build_with_that_task(tmp_path):
    gh = ChatGh(pr(head=A), comment("c1", "why?"))
    cx = ctx(tmp_path, gh)
    c, first = follow.conversation(cx, change(), gh.pr, StepKind.MERGE)
    c = loop.apply(c, first, NOW)
    c, result = follow.conversation(cx, c, gh.pr, StepKind.MERGE)
    assert (result.exit, result.back_to, result.fix_task.id) == (Exit.BACK, StepKind.BUILD, first.fix_task.id)
    c.step = Step(kind=StepKind.MERGE)
    c = loop.apply(c, result, NOW)
    assert sum(t.id == first.fix_task.id for t in c.plan.tasks) == 1


def done(stdout):
    return subprocess.CompletedProcess((), 0, json.dumps(stdout).encode(), b"")


def page(nodes=(), cursor=None):
    return {"pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor}, "nodes": list(nodes)}


def test_gh_reads_every_conversation_page_and_keeps_changes_requested_empty_reviews(tmp_path):
    def node(cid, body, **extra):
        return {"id": cid, "url": f"u/{cid}", "body": body, "author": {"login": "o"}, **extra}

    reviewed = [
        node("r1", "", state="CHANGES_REQUESTED"),
        node("r2", "", state="APPROVED"),
        node("r3", "x", state="COMMENTED"),
    ]
    notes = page([node(f"h{n}", "q") for n in range(100)], "K1")
    more = page([node("h100", "more"), node("h101", "ok <!-- delivery:c1:t:p -->", author=None)])
    threaded = [{"id": "t1", "path": "a.py", "isResolved": False, "isOutdated": True, "comments": notes}]
    pages = [
        {
            "comments": page([node("c1", "first")], "C1"),
            "reviews": page(reviewed),
            "reviewThreads": page(threaded),
        },
        {"comments": page([node("c2", "second", author={"login": "github-actions", "__typename": "Bot"})])},
    ]
    calls, threads = [], []

    def runner(argv, data, _timeout, _cwd):
        body = json.loads(data)
        if "ThreadComments" in body["query"]:
            threads.append(body["variables"])
            return done({"data": {"node": {"comments": more}}})
        calls.append((argv, body["variables"]))
        return done({"data": {"repository": {"pullRequest": pages[len(calls) - 1]}}})

    items = GhProvider(tmp_path, runner=runner).read_conversation("o/r", 7)
    assert [(i.id, i.kind, i.bot) for i in items] == [
        ("c1", "comment", False),
        ("c2", "comment", True),
        ("r1", "review", False),
        ("r3", "review", False),
        ("t1", "thread", False),
    ]
    assert calls[0][0][:4] == ("gh", "api", "--hostname", "github.com")
    assert {k: calls[1][1][k] for k in ("c", "wc", "wr", "wt")} == {"c": "C1", "wc": True, "wr": False, "wt": False}
    t = items[-1]
    assert threads == [{"id": "t1", "after": "K1"}]
    assert (t.author, len(t.comments), t.outdated, t.comments[-1].author) == ("o", 102, True, "ghost")
    assert (items[2].state, items[3].state) == ("CHANGES_REQUESTED", "COMMENTED")
    opened = [s.item.id for s in conversation.open_items(change(), items, lambda: "delivery")]
    assert opened == ["c1", "c2", "r1", "r3", "t1"]


def test_gh_replies_in_threads_by_graphql_and_quotes_other_items_in_an_issue_comment(tmp_path):
    calls = []

    def runner(argv, data, _timeout, _cwd):
        calls.append((argv, json.loads(data)))
        if "graphql" in argv:
            return done({"data": {"addPullRequestReviewThreadReply": {"comment": {"id": "R1"}}}})
        return done({"node_id": "IC1"})

    gh = GhProvider(tmp_path, runner=runner)
    assert gh.post_reply("o/r", 7, thread("t1", ("h1", "o", "q")), "ok") == "R1"
    assert calls[-1][1]["variables"] == {"id": "t1", "body": "ok"}
    assert gh.post_reply("o/r", 7, comment("c1", "q"), "ok") == "IC1"
    assert "repos/o/r/issues/7/comments" in calls[-1][0]
    assert calls[-1][1] == {"body": "> https://github.com/o/r/pull/7#c1\n\nok"}


class Host:
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

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
    failed = client.post("/api/next/changes/c1/check-results", json=body | {"passed": False, "note": "  "})
    assert (failed.status_code, "fix task" in failed.json()["detail"]) == (422, True)  # the note is the fix task
    assert client.post("/api/next/changes/c1/check-results", json=body).json() == {"accepted": "check-result"}
    shown_change = client.get("/api/next/changes/c1").json()
    assert (shown_change["asks_merge"], shown_change["deletes_branch"]) == (False, False)  # the profile's defaults


def test_a_saved_person_check_is_voided_by_revised_steps_or_a_commit_in_its_scope(clone, tmp_path):
    store, url = Store(tmp_path / "store"), "http://127.0.0.1:4173/"
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    steps = {"name": "preview", "steps": ["Open the preview"], "expect": "Hallo, Ada!"}
    brief = {"title": "Greet", "outcome": "The preview greets the owner.", "criteria": ["The page greets Ada"]}
    brief |= {"scope": ["app/"], "person_checks": [steps]}
    client.post("/api/next/briefs", json=brief)
    env = Environment(check="preview", command="npm run preview", directory=".", ready_url=url, ready_at=NOW)
    with store.lock("greet") as lock:
        store.write(lock, store.read("greet").model_copy(update={"env": env}))
    old = client.get("/api/next/changes/greet").json()["checks"][0]["inputs"]
    client.post("/api/next/briefs", json=brief | {"change": "c1", "person_checks": [steps | {"expect": "Hi"}]})
    result = {"check": "preview", "passed": True, "inputs": old}
    stale = client.post("/api/next/changes/greet/check-results", json=result)
    assert stale.json()["detail"] == "This check changed since you opened it; reload"
    (clone / "app").mkdir()
    (clone / "app" / "page.ts").write_text("1\n")
    git(clone, "add", ".")
    git(clone, "commit", "-q", "-m", "app")
    c = store.read("greet")
    c.names.worktree, p = str(clone), c.checks[0]
    assert (p.paths, p.procedure) == (["app/"], 2)
    p.answer = Answer(at=NOW, passed=True, inputs=evidence.check_inputs(c, p, check.fingerprints(c, p)))
    for path, version in (("a.txt", None), ("app/page.ts", "preview")):
        (clone / path).write_text("2\n")
        git(clone, "commit", "-qam", path)
        assert getattr(evidence.next_check(c, check.declared(c)), "id", None) == version
    assert check.pending(c, env).reason.endswith("asked again: changed app/page.ts")


def test_publish_waits_for_the_network_and_asks_for_other_readiness_fixes():
    ok = [SetupCheck("network", ok=True, detail=""), SetupCheck("github cli", ok=True, detail="")]
    assert publish.gate(ok, NOW) is None
    net = publish.gate([SetupCheck("network", ok=False, detail="timed out", fix="Connect")], NOW)
    assert (net.exit, net.cause, net.wake_at) == (Exit.RETRY, "network:publish:readiness", NOW + timedelta(minutes=1))
    fix = "Run `gh auth login --hostname github.com`"
    auth = publish.gate([*ok, SetupCheck("github sign-in", ok=False, detail="expired", fix=fix)], NOW)
    assert (auth.exit, auth.cause, auth.reason.endswith(fix)) == (Exit.ASK, "auth:publish:github sign-in", True)
    assert [o.next for o in auth.question.options] == [StepKind.PUBLISH, "pause"]


def test_offline_readiness_is_an_episode_that_asks_only_after_a_day():
    c, at = change(StepKind.PUBLISH), NOW
    offline = [SetupCheck("network", ok=False, detail="timed out", fix="Connect")]
    while at < NOW + budgets.EPISODE_ASK:
        c = loop.apply(c, publish.gate(offline, at), at)
        assert (c.outcome.exit, c.outcome.waiting) == (Exit.PENDING, Waiting.NETWORK)
        at = c.outcome.wake_at
    c = loop.apply(c, publish.gate(offline, at), at)
    assert c.outcome.exit == Exit.ASK


@pytest.mark.parametrize(
    ("code", "kind"),
    [
        (FailureCode.UNAVAILABLE, "network"),
        (FailureCode.TIMEOUT, "network"),
        (FailureCode.RATE_LIMITED, "capacity"),
        (FailureCode.INVALID_RESPONSE, "tooling"),
    ],
)
def test_adapter_failures_share_the_readiness_classification(code, kind):
    result = engine.failed(change(StepKind.PUBLISH), ProviderError(code, "pr", "boom", retry_safe=True), NOW)
    assert (result.exit, result.cause) == (Exit.RETRY, f"{kind}:publish:github")


def test_an_invalid_provider_response_asks_after_three_of_the_same():
    c = change(StepKind.PUBLISH)
    for exits in (Exit.RETRY, Exit.RETRY, Exit.ASK):
        bad = ProviderError(FailureCode.INVALID_RESPONSE, "pr", "unexpected shape", retry_safe=True)
        c = loop.apply(c, engine.failed(c, bad, NOW), NOW)
        assert c.outcome.exit == exits


def test_publish_returns_to_the_final_review_unless_head_is_the_final_reviewed_head(clone, tmp_path):
    head = git(clone, "rev-parse", "HEAD")
    final = Review(commit=B, inputs=Inputs(), verdict="pass")
    c = change(StepKind.PUBLISH, worktree=str(clone), reviews=[final])
    _, result = publish.run(ctx(tmp_path, FakeGh(pr())), c)
    assert loop.apply(c, result, NOW).step == Step(kind=StepKind.REVIEW, mode="final")
    assert publish.reviewed(c.model_copy(update={"reviews": [final.model_copy(update={"commit": head})]}), clone, head)


class Interrupted(BaseException):
    """The runner dies the moment GitHub has created the PR, before Delivery reads the answer."""


@pytest.mark.parametrize("lost", [Interrupted, ProviderError(FailureCode.TIMEOUT, "create", "x", retry_safe=False)])
def test_a_pr_created_before_an_interruption_is_found_again_and_never_created_twice(tmp_path, lost):
    gh, made = FakeGh(None), []

    def create(_repo, _branch, _target, _title, _body):
        made.append(1)
        gh.pr = pr(head=A, draft=True)
        raise lost

    gh.find_pull_request = lambda *_a: gh.pr
    gh.create_pull_request = create
    c, cx = change(StepKind.PUBLISH), ctx(tmp_path, gh)
    if lost is Interrupted:
        with pytest.raises(Interrupted):
            publish.pull_request(cx, c, A)
    else:  # an unknown create is read back at once
        assert publish.pull_request(cx, c, A).number == 7
    found = publish.pull_request(cx, c, A)  # the next runner
    assert (found.number, made) == (7, [1])


def test_a_pr_head_lagging_the_push_is_observed_again_shortly_without_budget(clone, tmp_path):
    commit(clone, "fix.txt")
    head = git(clone, "rev-parse", "HEAD")
    c = change(StepKind.PUBLISH, worktree=str(clone), reviews=[Review(commit=head, inputs=Inputs(), verdict="pass")])
    gh = FakeGh(pr(head=A))
    gh.find_pull_request = lambda *_a: gh.pr
    cx = ctx(tmp_path, gh)
    _, result = publish.run(cx, c)
    assert (result.exit, result.waiting, result.wake_at) == (Exit.PENDING, Waiting.NETWORK, cx.poll())
    after = loop.apply(c, result, NOW)
    assert (after.outcome.exit, after.budgets.causes) == (Exit.PENDING, {})
    cx.now = NOW + timedelta(minutes=9)
    assert publish.run(cx, after)[1].exit == Exit.PENDING  # within ten minutes of the first lag
    cx.now = NOW + timedelta(minutes=10)
    _, asked = publish.run(cx, after)
    assert (asked.exit, [o.label for o in asked.question.options]) == (Exit.ASK, ["Done, continue", "Pause"])
    assert all(s in asked.reason for s in (gh.pr.url, A, head))
    assert publish.run(cx, after)[1].exit == Exit.PENDING  # after "Done, continue" a new ten-minute window starts
    gh.pr = pr(head=head)
    assert publish.run(cx, after)[1].exit == Exit.DONE
    assert after.lag is None


def test_a_pr_head_lag_with_a_moved_branch_republishes_instead_of_waiting(clone, tmp_path, monkeypatch):
    head = git(clone, "rev-parse", "HEAD")
    c, gh = change(StepKind.PUBLISH, worktree=str(clone)), FakeGh(pr(head=A))
    monkeypatch.setattr(publish, "read_remote_ref", lambda *_a: B)
    pushed = []
    monkeypatch.setattr(
        publish, "push", lambda _p, _c, h: pushed.append(h) or engine.integrate(c, StepKind.PUBLISH, "x")
    )
    result = publish.lagging(ctx(tmp_path, gh), c, gh.pr, head)
    assert (result.exit, pushed, c.lag) == (Exit.BACK, [head], None)


# CI classification


def test_a_missing_declared_check_is_never_passed():
    checks = (
        Check(name="test", status="completed", conclusion="success"),
        Check(name="lint", status="completed", conclusion="failure"),
    )
    state = classify_checks(checks, declared=("test", "build"), required=())
    assert (state.passed, state.missing, [c.name for c in state.failed]) == (("test",), ("build",), ["lint"])


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


def test_a_check_that_never_starts_is_pending_then_asks_the_owner_in_follow_and_merge(tmp_path, clone):
    gh, state = FakeGh(pr(head=B)), classify_checks((), ("test",), ())
    cx = ctx(tmp_path, gh)
    c = follow.episode(cx, change(StepKind.FOLLOW), B, state)
    cx.now = NOW + timedelta(minutes=1)
    _, early = follow.missing(cx, follow.episode(cx, c, B, state), gh.pr, state)
    assert (early.exit, early.waiting, c.missing.since) == (Exit.PENDING, Waiting.CHECK_START, NOW)
    cx.now = NOW + timedelta(minutes=10)
    _, late = follow.missing(cx, c, gh.pr, state)
    assert late.exit == Exit.ASK
    assert "test never started on PR #7" in late.reason
    assert follow.episode(cx, c, B, classify_checks(gh.checks, ("test",), ())).missing is None
    head, entries = ci_head(clone, "test")
    gh.pr, gh.checks, cx.now, cx.profile = pr(head=head), (), NOW, prof(**entries)
    m = loop.fold(change(worktree=str(clone), head=head), [ConsentItem(at=NOW, head=head)], NOW)
    m, early = merge.run(cx, m)
    cx.now = NOW + timedelta(minutes=10)
    _, late = merge.run(cx, m)
    assert (early.waiting, late.exit, late.question.options[0].next) == (Waiting.CHECK_START, Exit.ASK, StepKind.MERGE)


def test_a_failing_check_goes_back_to_build_with_its_log(tmp_path, clone):
    head, entries = ci_head(clone, "test")
    gh = FakeGh(pr(head=head))
    gh.checks = (Check(name="test", status="completed", conclusion="failure", job_id=9),)
    _, result = follow.run(ctx(tmp_path, gh, prof(**entries)), change(StepKind.FOLLOW, worktree=str(clone)))
    assert (result.exit, result.back_to, result.cause) == (Exit.BACK, StepKind.BUILD, "checks:follow:test")
    assert result.fix_task.origin == "ci"
    assert "fails only in CI" in result.fix_task.detail


def test_a_failing_check_neither_declared_nor_required_blocks_the_merge_and_goes_back_to_build(tmp_path, clone):
    head, entries = ci_head(clone, "test")
    gh = FakeGh(pr(head=head))
    merged(gh)
    gh.checks += (Check(name="lint", status="completed", conclusion="failure"),)
    _, result = merge.run(ctx(tmp_path, gh, prof(**entries)), change(worktree=str(clone), head=head))
    assert (result.exit, result.back_to, result.cause, result.fix_task.title, gh.merges) == (
        Exit.BACK,
        StepKind.BUILD,
        "checks:merge:lint",
        "Fix the failing CI check lint",
        [],
    )


def test_unreadable_workflow_files_at_the_head_are_pending_and_never_merged(tmp_path, clone, monkeypatch):
    gh = FakeGh(pr(head=B))  # B is neither here nor fetchable: the branch was never pushed
    _, result = follow.run(ctx(tmp_path, gh), change(StepKind.FOLLOW, worktree=str(clone)))
    assert (result.exit, result.waiting, result.reason) == (
        Exit.PENDING,
        Waiting.NETWORK,
        f"reading the workflow files at {B[:7]}",
    )
    gh = FakeGh(pr(head=A))
    merged(gh)
    monkeypatch.setattr(profile, "workflow_texts_at", lambda _repo, _rev: None)
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.exit, result.waiting, gh.merges) == (Exit.PENDING, Waiting.NETWORK, [])


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
def test_an_unknown_merge_is_read_back_before_any_replay(tmp_path, clone, after, exit_):
    gh = FakeGh(pr(head=A))
    if after == "merged":
        gh.after = pr(head=A, state="closed", merged=True, merge_commit_sha=B)
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.exit, len(gh.merges)) == (exit_, 1)
    if exit_ == Exit.RETRY:
        assert result.cause == "network:merge:merge"


# Automatic merge gate (TD-15) and no merge queue (TD-22)


def merged(gh, sha=B):
    gh.result = MergeResult(status=MergeStatus.MERGED, sha=sha)
    gh.after = gh.pr.model_copy(update={"state": "closed", "merged": True, "merge_commit_sha": sha})


def test_without_ask_before_merge_a_gated_head_merges_without_consent(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    merged(gh)
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone)))
    assert (result.exit, len(gh.merges), profile.value(prof(), profile.ASK, "no")) == (Exit.DONE, 1, "no")
    asked = ctx(tmp_path, FakeGh(pr(head=A)), prof(**ASKING))
    _, result = merge.run(asked, change(worktree=str(clone)))
    assert (result.exit, result.cause) == (Exit.ASK, loop.CONSENT)


def test_a_head_without_a_valid_final_review_goes_back_to_publish(tmp_path, clone):
    gh = FakeGh(pr(head=B))
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone), head=A))
    assert (result.exit, result.back_to, result.cause, gh.merges) == (
        Exit.BACK,
        StepKind.PUBLISH,
        "gate:merge:review",
        [],
    )


def test_a_required_human_review_is_pending_naming_the_reviewers(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    gh.review = ("REVIEW_REQUIRED", ("alice", "team/core"))
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone)))
    assert (result.exit, result.waiting, result.reason) == (
        Exit.PENDING,
        Waiting.REVIEWER,
        "waiting for review by alice, team/core",
    )
    assert gh.merges == []


def test_a_refusal_naming_reviews_is_pending_and_a_moved_head_retries(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    gh.result = MergeResult(status=MergeStatus.REFUSED, refusal=Refusal.RULES_FAILED, message="Review required")
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone)))
    assert (result.exit, result.waiting) == (Exit.PENDING, Waiting.REVIEWER)
    gh.result = MergeResult(status=MergeStatus.REFUSED, refusal=Refusal.HEAD_CHANGED)
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone)))
    assert (result.exit, result.cause) == (Exit.RETRY, "conflict:merge:head")


def test_a_held_target_lock_is_pending_and_nothing_is_merged(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    cx = ctx(tmp_path, gh)
    with cx.store.merge_lock("main") as mine:
        assert mine
        _, result = merge.run(cx, change(worktree=str(clone)))
    assert (result.exit, result.waiting, result.who, result.reason) == (
        Exit.PENDING,
        Waiting.GITHUB,
        "delivery",
        "another Change is merging into main",
    )
    assert gh.merges == []
    with cx.store.merge_lock("other") as other:
        assert other


def test_a_check_failing_between_the_reads_prevents_the_merge(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    results = iter([gh.checks, (Check(name="test", status="completed", conclusion="failure"),)])
    gh.observe_checks = lambda _repo, _number, _head: next(results)
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone)))
    assert (result.exit, result.back_to, result.cause, gh.merges) == (
        Exit.BACK,
        StepKind.BUILD,
        "checks:merge:test",
        [],
    )


def test_a_conversation_item_arriving_between_the_reads_prevents_the_merge(tmp_path, clone):
    gh = ChatGh(pr(head=A))
    reads = iter([(), (comment("c9", "wait"),)])
    gh.read_conversation = lambda _repo, _number: next(reads)
    _, result = merge.run(ctx(tmp_path, gh), change(worktree=str(clone)))
    assert (result.exit, result.fix_task.id[:6], gh.merges) == (Exit.BACK, "pr-c9-", [])


def target_checks(gh, *checks):
    gh.commit_checks = tuple(Check(name=n, status=s, conclusion=k, url="https://ci/1") for n, s, k in checks)


def test_a_failing_check_on_the_merged_target_drafts_one_fix_change_and_cleanup_completes(worktree_with_work, tmp_path):
    clone, wt = worktree_with_work
    gh = FakeGh(pr(head=A, state="closed", merged=True, merge_commit_sha=B))
    target_checks(gh, ("test", "completed", "failure"))
    cx = ctx(tmp_path, gh, repo=clone)
    c = change(StepKind.CLEANUP, worktree=str(wt))
    c.names.branch = "owlbear/c2"
    assert cleanup.target_check(cx, c, gh.pr)[1] is None
    _, result = cleanup.run(cx, c)  # re-entry: the same failure drafts nothing more
    assert result.exit == Exit.DONE, result.reason
    [slug] = cx.store.slugs()
    fix = cx.store.read(slug)
    assert (fix.step.kind, "https://ci/1" in fix.brief.outcome) == (StepKind.SHAPE, True)
    assert [e["fix"] for e in cx.events("c1", "fix-drafted")] == [slug]


def test_a_pause_never_holds_cleanup():
    c = change(StepKind.CLEANUP)
    c.intent.paused_at = NOW
    assert loop.next_step(c, NOW) == c.step


def test_running_target_checks_have_no_deadline_and_a_late_failure_drafts_one_fix(tmp_path):
    gh = FakeGh(pr(head=A, state="closed", merged=True, merge_commit_sha=B))
    target_checks(gh, ("test", "in_progress", None))
    cx = ctx(tmp_path, gh)
    cx.store.root.mkdir()
    c, held = cleanup.target_check(cx, change(StepKind.CLEANUP), gh.pr)
    assert (held.exit, held.waiting, held.reason) == (Exit.PENDING, Waiting.CI, "1 of 1 checks running on main")
    first = held.wake_at - cx.now
    cx.now = NOW + timedelta(seconds=301)
    c, held = cleanup.target_check(cx, c, gh.pr)
    assert (held.exit, held.wake_at - cx.now > first) == (Exit.PENDING, True)  # still running: pending, slower poll
    target_checks(gh, ("test", "completed", "failure"))
    c, held = cleanup.target_check(cx, c, gh.pr)
    assert (held, len(cx.events("c1", "fix-drafted")), len(cx.store.slugs())) == (None, 1, 1)


def test_a_failed_target_check_drafts_its_fix_and_waits_for_the_others(tmp_path):
    gh = FakeGh(pr(head=A, state="closed", merged=True, merge_commit_sha=B))
    target_checks(gh, ("test", "completed", "failure"), ("lint", "in_progress", None))
    cx = ctx(tmp_path, gh)
    cx.store.root.mkdir()
    c, held = cleanup.target_check(cx, change(StepKind.CLEANUP), gh.pr)
    assert (held.exit, len(cx.events("c1", "fix-drafted"))) == (Exit.PENDING, 1)
    c, held = cleanup.target_check(cx, c, gh.pr)
    assert (held.exit, len(cx.store.slugs())) == (Exit.PENDING, 1)  # the same failure drafts once
    target_checks(gh, ("test", "completed", "failure"), ("lint", "completed", "failure"))
    c, held = cleanup.target_check(cx, c, gh.pr)
    assert (held, [e["key"].split(":")[1] for e in cx.events("c1", "fix-drafted")]) == (None, ["test", "lint"])
    assert len(cx.store.slugs()) == 2


def test_never_started_target_checks_wait_within_the_window_then_cleanup_proceeds(tmp_path):
    gh = FakeGh(pr(head=A, state="closed", merged=True, merge_commit_sha=B))
    target_checks(gh)
    cx = ctx(tmp_path, gh)
    c, held = cleanup.target_check(cx, change(StepKind.CLEANUP), gh.pr)
    assert (held.exit, held.reason) == (Exit.PENDING, "waiting up to 5 min for test to start on main")
    cx.now = NOW + timedelta(seconds=301)
    c, held = cleanup.target_check(cx, c, gh.pr)
    assert (held, c.missing) == (None, None)
    assert cx.events("c1", "target-checks-unfinished")[-1] | {"at": 0} == {
        "event": "target-checks-unfinished",
        "at": 0,
        "sha": B,
        "missing": ["test"],
    }


def test_unknown_rules_make_merging_human_assisted(tmp_path, clone):
    gh = FakeGh(pr(head=A))
    p = prof().model_copy(update={"entries": prof().entries | profile.rule_entries(FORBIDDEN)})
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
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


def test_cleanup_removes_the_worktree_only_after_bundle_and_archive_verify(worktree_with_work, tmp_path):
    clone, wt = worktree_with_work
    inv = cleanup.inventory(wt, "owlbear/c2", ["origin/main", "absent-ref"])
    assert len(inv.commits) == 1
    assert sorted(inv.dirty) == ["a.txt", "new.txt", "staged.txt"]
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


def test_cleanup_removes_the_change_s_read_only_worktree_with_its_own(worktree_with_work, tmp_path):
    clone, wt = worktree_with_work
    cx = ctx(tmp_path, FakeGh(pr()), repo=clone)
    copy = disposable.prepare(wt, cx.store, "c1")
    (copy.path / "note.txt").write_text("a reviewer's scratch\n")
    c = change(StepKind.CLEANUP, worktree=str(wt))
    c.names.branch, c.names.pr = "owlbear/c2", None
    _, result = cleanup.run(cx, c)
    assert (result.exit, wt.exists(), copy.path.exists()) == (Exit.DONE, False, False)
    assert str(copy.path) not in git(clone, "worktree", "list")
    assert not any("note.txt" in p for p in result.preserved)


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


def test_ignored_files_are_archived_unless_regenerable_and_large_ones_keep_the_worktree(
    worktree_with_work, tmp_path, monkeypatch
):
    clone, wt = worktree_with_work
    git(wt, "config", "core.excludesFile", str(tmp_path / "ignore"))
    (tmp_path / "ignore").write_text(".env\nnode_modules/\n")
    (wt / ".env").write_text("SECRET=1\n")
    (wt / "node_modules").mkdir()
    (wt / "node_modules" / "x.js").write_text("x\n")
    c = change(StepKind.CLEANUP, worktree=str(wt))
    c.names.branch, c.names.pr = "owlbear/c2", None
    monkeypatch.setattr(cleanup, "LARGE", 1)
    _, kept = cleanup.run(ctx(tmp_path, FakeGh(pr()), repo=clone), c)
    assert (kept.exit, "workspace kept" in kept.reason, wt.exists()) == (Exit.DONE, True, True)
    monkeypatch.setattr(cleanup, "LARGE", 50 * 1024 * 1024)
    _, result = cleanup.run(ctx(tmp_path, FakeGh(pr()), repo=clone), c)
    assert (result.exit, wt.exists()) == (Exit.DONE, False)
    with tarfile.open(result.preserved[-1]) as tar:
        assert tar.extractfile("files/.env").read() == b"SECRET=1\n"
        assert not any("node_modules" in n for n in tar.getnames())


def test_a_staged_version_the_working_tree_replaced_is_archived_and_verified(worktree_with_work, tmp_path):
    _, wt = worktree_with_work
    (wt / "a.txt").write_text("staged B\n")
    git(wt, "add", "a.txt")
    (wt / "a.txt").write_text("worktree C\n")
    inv = cleanup.inventory(wt, "owlbear/c2", ["origin/main"])
    archive = cleanup.preserve(wt, "owlbear/c2", inv, tmp_path / "kept", "s")[-1]
    with tarfile.open(archive) as tar:
        assert tar.extractfile("index/0/a.txt").read() == b"staged B\n"
        assert tar.extractfile("files/a.txt").read() == b"worktree C\n"
        assert b"+staged B" in tar.extractfile("staged.diff").read()


# CI detection from workflow files


@pytest.mark.parametrize(
    ("text", "events"),
    [
        ("on: pull_request", {"pull_request"}),
        ("on: [push, pull_request]", {"push", "pull_request"}),
        ("on:\n  pull_request_target:\n    types: [opened]\n  push:\n", {"pull_request_target", "push"}),
        ("'on': merge_group", {"merge_group"}),
    ],
)
def test_workflow_triggers_parse_in_every_form(text, events):
    assert profile.workflow(text).events == frozenset(events)


def test_unresolved_triggers_or_check_names_stay_unknown_never_no_ci():
    flows = {
        "ci.yml": profile.workflow("on: [push, pull_request]\njobs:\n  test:\n    name: Unit tests\n  lint: {}\n"),
        "queue.yml": profile.workflow("on: merge_group\njobs:\n  e2e: {}\n"),
        "push.yml": profile.workflow("on: push\njobs:\n  deploy: {}\n"),
    }
    e = profile.ci_entries(flows)
    assert (e[profile.WORKFLOWS].value, e[profile.DECLARED].value) == ("ci.yml, queue.yml", "Unit tests, lint")
    assert e[profile.DECLARED].state == "known"
    flows["matrix.yml"] = profile.workflow("on: pull_request\njobs:\n  t:\n    strategy: {matrix: {os: [a, b]}}\n")
    flows["bad.yml"] = profile.workflow("on: [unclosed")
    assert profile.workflow("on: push\nenv:\n  RELEASE_TAG: 2026-02-30\njobs:\n  a: {}\n") == flows["bad.yml"]
    e = profile.ci_entries(flows)
    assert (e[profile.WORKFLOWS].state, e[profile.DECLARED].state) == ("unknown", "unknown")
    assert "matrix.yml" in e[profile.DECLARED].evidence


# Integration triggers


def test_a_moved_target_integrates_before_merging_whatever_github_reports(tmp_path, clone):
    git(clone, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(clone, "reset", "-q", "--hard", "HEAD~1")
    gh = FakeGh(pr(head=A))
    c = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    _, result = merge.run(ctx(tmp_path, gh), c)
    assert (result.back_to, result.cause, result.fix_task.origin) == (
        StepKind.BUILD,
        "conflict:merge:origin/main",
        "integration",
    )
    assert gh.merges == []


def test_a_builder_needing_target_work_integrates_then_resumes_its_task(clone):
    c = change(StepKind.BUILD, worktree=str(clone))
    c.step.task = "t1"
    c = loop.apply(c, engine.needs_target(c, clone, "greet() exists only on main", NOW), NOW)
    assert (c.step.task, c.plan.tasks[-1].origin) == ("t2", "integration")
    assert "greet() exists only on main" in c.plan.tasks[-1].detail
    c = loop.apply(c, loop.StepResult(exit=Exit.DONE), NOW)  # its build; the task's next round reviews the merge
    assert (c.step.kind, c.step.task, c.plan.tasks[-1].done) == (StepKind.BUILD, "t1", True)


def test_a_target_premise_from_a_session_whose_processes_remain_is_never_acted_on(tmp_path, clone, monkeypatch):
    cx = ctx(tmp_path, FakeGh(pr(head=A)))
    c = change(StepKind.BUILD, worktree=str(clone))
    c.step.task = "t1"
    cx.store.write(cx.lock, c)
    premise, _ = tool_schema.parse(
        tools.WrongPremise, {"stage": "target", "reason": "greet() exists only on main", "evidence": ["main"]}
    )

    async def build(cfg):
        return Run(cfg.session_id, "premise", premise, termination=processes.Termination(confirmed=False, unknown=(7,)))

    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: clone)
    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._agent(cx.store, cx.lock, cx.store.read("c1"), clone)  # noqa: SLF001
    after = cx.store.read("c1")
    assert (after.outcome.exit, [t.id for t in after.plan.tasks]) == (Exit.STOP, ["t1"])


def commit(cwd, name):
    (cwd / name).write_text(f"{name}\n")
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", name)


def test_a_task_is_measured_from_its_own_start_without_merged_target_paths(clone):
    commit(clone, "b.txt")
    since = worktree.head(clone)
    git(clone, "switch", "-q", "main")
    commit(clone, "d.txt")
    git(clone, "push", "-q", "origin", "main")
    git(clone, "switch", "-q", "owlbear/c1")
    commit(clone, "c.txt")
    git(clone, "merge", "-q", "--no-edit", "origin/main")
    assert (worktree.observe(clone, "main", since).changed, worktree.observe(clone, "main").changed) == (
        ("c.txt",),
        ("b.txt", "c.txt"),
    )


def test_findings_beyond_one_tasks_detail_limit_are_kept_whole_across_repair_tasks(clone):
    findings = [{"place": f"a.txt:{i}", "problem": "AC-1: " + "p" * 400, "fix": "f" * 400} for i in range(10)]
    review_, _ = tool_schema.parse(
        tools.ReviewResult, {"verdict": "fix", "findings": findings, "covered_paths": ["a.txt"]}
    )
    c = change(StepKind.REVIEW)
    c.step.task = "t1"
    run = Run("s", "result", review_, head=worktree.head(clone))
    r = review.recorded(c, None, run, clone, loop.StepResult(exit=Exit.RETRY, reason="cut"))
    lines = review.lines(review_)
    assert (len("\n".join(lines)) > 4000, r.review.findings) == (True, lines)  # the record keeps every finding
    tasks = [r.fix_task, *r.more_fixes]
    assert [t.title for t in tasks] == [f"Fix 10 review finding(s) of task t1 (part {i} of 3)" for i in (1, 2, 3)]
    assert all(len(t.detail) <= 4000 for t in tasks)
    assert "\n".join(t.detail for t in tasks).splitlines() == lines  # none lost, none cut
    c = loop.apply(c, r, NOW)
    assert ([t.id for t in c.plan.tasks[-3:]], c.step.task) == (["t2", "t3", "t4"], "t2")
    assert {t.fixes for t in c.plan.tasks[-3:]} == {"t1"}


def test_a_repaired_task_resolves_only_after_every_part_and_the_parts_run_before_later_tasks():
    c = change(StepKind.REVIEW)
    c.plan.tasks += [Task(id="t2", title="two")] + [Task(id=f"t{i}", title="part", fixes="t1") for i in (3, 4, 5)]
    c.step.task, steps = "t3", []
    for _ in range(3):
        c = loop.apply(c, loop.StepResult(exit=Exit.DONE, reason="pass"), NOW)
        steps.append((c.step.task, c.plan.tasks[0].done))
        c.step = Step(kind=StepKind.REVIEW, task=c.step.task)
    assert steps == [("t4", False), ("t5", False), ("t2", True)]


# Reopen and the pre-push hook


@pytest.mark.parametrize("push", ["yes", "no"])
def test_reopen_reopens_the_pr_when_permitted_else_asks_the_owner(tmp_path, clone, push):
    head, entries = ci_head(clone, "test")
    gh = FakeGh(pr(head=head, state="closed"))
    c, _ = loop.schedule(change(StepKind.FOLLOW, worktree=str(clone)), [], NOW, "closed")
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question="q1", option="reopen")], NOW, "closed")
    pushing = {profile.PUSH: ProfileEntry(state="known", value=push)}
    c, result = follow.run(ctx(tmp_path, gh, prof(**entries, **pushing)), c)
    if push == "yes":
        assert (result.exit, gh.reopened, bool(c.questions[0].effect_observed_at)) == (Exit.DONE, [7], True)
    else:
        assert (result.exit, gh.reopened, c.questions[0].effect_observed_at) == (Exit.ASK, [], None)
        assert result.reason.startswith("Reopen PR #7 in GitHub")


def test_a_silent_rejecting_pre_push_hook_becomes_a_builder_fix_after_readback(clone):
    hook = clone / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    result = publish.push(clone, change(StepKind.PUBLISH), git(clone, "rev-parse", "HEAD"))
    assert (result.back_to, result.cause) == (StepKind.BUILD, "commit-policy:publish:pre-push")
    assert read_remote_ref(clone, "origin", "refs/heads/owlbear/c1") is None
    assert not publish.hook_rejected(128, b"fatal: Could not read from remote repository.", hook=True)
    assert not publish.hook_rejected(1, b" ! [remote rejected] main (protected branch)", hook=True)


# TD-226: merging through a merge queue, with a provider fake shaped by the live proof (TD-279)

QUEUED = Rules(
    state="known",
    evidence="rules merge_queue",
    types=("merge_queue",),
    queue_required=True,
    queue_method=MergeMethod.MERGE,
)
GROUP = "c" * 40
ADDED = QueueEvent(id="ATMQE_1", kind="added", at=NOW, actor="maba-pag")


def removal(reason, rid="RFMQE_1", actor="github-merge-queue", before=GROUP):
    return QueueEvent(id=rid, kind="removed", at=NOW + timedelta(minutes=1), actor=actor, reason=reason, before=before)


def entry(state="QUEUED", position=1, group=None):
    return QueueEntry(state=state, position=position, group_sha=group, enqueued_at=NOW)


class QueueGh(FakeGh):
    """The provider fake with a merge queue; ``state`` is what each read returns."""

    def __init__(self, current):
        super().__init__(current)
        self.state = QueueState(merged=False, open=True, head_sha=current.head_sha)
        self.enqueued, self.dequeued, self.answer = [], [], EnqueueResult(status=EnqueueStatus.ENQUEUED)
        self.runs, self.dequeue_fails, self.ordered = (), False, False

    def read_rules(self, _repo, _branch):
        return QUEUED

    def read_queue(self, _repo, _number):
        s = self.state
        if self.ordered or not (s.added and s.removed):
            return s
        return s.model_copy(update={"removed_last": s.removed.at >= s.added.at})  # timeline order follows time here

    def enqueue(self, _pull, head):
        self.enqueued.append(head)
        if self.answer.status == EnqueueStatus.ENQUEUED:
            self.state = self.state.model_copy(update={"entry": entry(), "added": ADDED})
            return self.answer.model_copy(update={"queued_at": NOW})
        return self.answer

    def dequeue(self, pull):
        if self.dequeue_fails:
            raise ProviderError(FailureCode.UNAVAILABLE, "dequeue", "down", retry_safe=True)
        self.dequeued.append(pull.number)
        self.state = self.state.model_copy(update={"entry": None, "removed": removal("manual", "RFMQE_9", "maba-pag")})

    def group_runs(self, _repo, sha):
        return tuple(r for r in self.runs if r.head_sha == sha)

    def group_log(self, _repo, run_id, _lines=40):
        return f"##[error]run {run_id} failed in the group"


def qprof():
    return profile.confirm(prof(**profile.rule_entries(QUEUED)), profile.RULES, "merge_queue", NOW)


def queue_step(tmp_path, gh, c):
    cx = ctx(tmp_path, gh, qprof())
    cx.store.root.mkdir(exist_ok=True)
    return merge.run(cx, c)


def queued_change(clone, **fields):
    c = change(worktree=str(clone), **fields)
    c.queue = QueueClaim(head=A, at=NOW, queued_at=NOW, settled=True)
    return c


def test_a_passing_gate_enqueues_the_exact_head_once_and_never_merges_directly(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    c, result = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (result.exit, result.waiting, result.reason) == (
        Exit.PENDING,
        Waiting.GITHUB,
        "PR #7 added to the merge queue",
    )
    assert (gh.enqueued, gh.merges, c.queue.head, c.queue.settled) == ([A], [], A, True)
    c, result = queue_step(tmp_path, gh, c)
    assert (result.reason, gh.enqueued) == ("PR #7 in the merge queue: position 1, queued", [A])


def test_an_already_queued_refusal_settles_and_a_stale_head_retries(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.answer = EnqueueResult(status=EnqueueStatus.REFUSED, message="Pull request is already in the queue")
    c, result = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (result.exit, c.queue.settled) == (Exit.PENDING, True)
    stale = "Failed to add PR #7: expected head oid does not match the current head oid"
    gh.answer = EnqueueResult(status=EnqueueStatus.REFUSED, message=stale)
    c, result = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (result.exit, result.cause, c.queue) == (Exit.RETRY, "conflict:merge:head", None)


@pytest.mark.parametrize("status", [EnqueueStatus.UNKNOWN, EnqueueStatus.ENQUEUED])
def test_an_attempt_without_evidence_is_never_sent_again_and_then_asks(tmp_path, clone, status):
    gh = QueueGh(pr(head=A))
    gh.answer = EnqueueResult(status=status)
    c, _ = queue_step(tmp_path, gh, change(worktree=str(clone)))
    gh.state = QueueState(merged=False, open=True, head_sha=A)  # GitHub shows nothing of it
    for _ in range(queue.QUIET - 1):
        c, result = queue_step(tmp_path, gh, c)
        assert (result.exit, result.waiting) == (Exit.PENDING, Waiting.GITHUB)
    c, result = queue_step(tmp_path, gh, c)
    assert (result.exit, result.cause, gh.enqueued) == (Exit.ASK, queue.UNSEEN, [A])
    c = loop.apply(c, result, NOW)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=c.outcome.question, option="again")], NOW)
    gh.answer = EnqueueResult(status=EnqueueStatus.ENQUEUED)
    c, result = queue_step(tmp_path, gh, c)
    assert (gh.enqueued, result.reason) == ([A, A], "PR #7 added to the merge queue")


def test_a_persons_entry_is_adopted_and_gated(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"entry": entry("AWAITING_CHECKS", group=GROUP), "added": ADDED})
    c, result = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (c.queue.adopted, gh.enqueued) == (True, [])
    assert result.reason == "PR #7 in the merge queue: position 1, awaiting checks"


def test_a_gate_failing_while_queued_takes_the_pr_out_before_routing(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED})
    c, result = queue_step(tmp_path, gh, queued_change(clone, reviews=[]))  # no valid final review of the head
    assert (result.exit, result.back_to, gh.dequeued) == (Exit.BACK, StepKind.PUBLISH, [7])
    assert (c.queue, c.queue_seen) == (None, "RFMQE_9")


def test_failed_group_checks_become_one_fix_task_from_that_group_handled_once(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    run = {"branch": "gh-readonly-queue/main/pr-7-x", "status": "completed", "conclusion": "failure", "updated_at": NOW}
    gh.runs = (GroupRun(id=41, head_sha=GROUP, **run), GroupRun(id=42, head_sha="d" * 40, **run))
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal("failed_checks")})
    c, result = queue_step(tmp_path, gh, queued_change(clone))
    assert (result.exit, result.back_to, c.queue, c.queue_seen) == (Exit.BACK, StepKind.BUILD, None, "RFMQE_1")
    assert "run 41 failed in the group" in result.fix_task.detail
    assert "run 42" not in result.fix_task.detail  # another group's run is never blamed
    c.queue = QueueClaim(head=A, at=NOW, settled=True)  # a later attempt never handles that removal again
    gh.state = gh.state.model_copy(update={"entry": entry()})
    _, result = queue_step(tmp_path, gh, c)
    assert result.exit == Exit.PENDING


@pytest.mark.parametrize(
    ("reason", "actor", "cause"),
    [
        ("checks_timed_out", "github-merge-queue", queue.TIMED_OUT),
        ("manual", "maba-pag", queue.REMOVED),
        ("something_new", "github-merge-queue", queue.REMOVED),
    ],
)
def test_other_removals_ask_and_are_never_enqueued_again_on_their_own(tmp_path, clone, reason, actor, cause):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal(reason, actor=actor)})
    _, result = queue_step(tmp_path, gh, queued_change(clone))
    assert (result.exit, result.cause, gh.enqueued) == (Exit.ASK, cause, [])
    assert [o.id for o in result.question.options] == ["again", "pause"]


def test_a_removal_before_any_attempt_is_not_handled(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal("manual", actor="maba-pag")})
    c, result = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (result.reason, c.queue_seen, gh.enqueued) == ("PR #7 added to the merge queue", "RFMQE_1", [A])


def test_a_merge_by_the_queue_ends_the_step(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.state = QueueState(merged=True, open=False, head_sha=A, added=ADDED, removed=removal("merged"))
    c, result = queue_step(tmp_path, gh, queued_change(clone))
    assert (result.exit, c.queue) == (Exit.DONE, None)


def test_the_gate_lets_the_queue_merge_with_its_own_method_and_ignores_blocked():
    blocked = pr(head=A, merge_state="blocked")
    args = {
        "target": "main",
        "ci": CiState(),
        "rules_confirmed": True,
        "can_push": True,
        "methods": (MergeMethod.MERGE,),
    }
    queued = merge_offer.decide(blocked, rules=QUEUED, method=MergeMethod.SQUASH, **args)
    direct = merge_offer.decide(blocked, rules=Rules(state="known", evidence="x"), method=MergeMethod.MERGE, **args)
    assert (queued.action, direct.block) == ("merge", merge_offer.Block.PROTECTION)


def test_restart_is_refused_for_a_direct_merge_in_flight_but_not_while_queued():
    c = change(consent=MergeConsent(head=A, at=NOW), loops={"final": RoundLoop(subject="final", policy=RoundPolicy())})
    assert round_flow.restartable(c) == "a merge is under way"
    c.queue = QueueClaim(head=A, at=NOW, settled=True)
    assert round_flow.restartable(c) == ""


def fold_store(tmp_path, monkeypatch, gh, c):
    store = Store(tmp_path / "s")
    store.root.mkdir()
    store.write_profile(qprof())
    with store.lock("c1") as lock:
        store.write(lock, c)
    monkeypatch.setattr(profile, "provider", lambda _p, _r: gh)
    store.put_inbox("c1", IntentItem(at=NOW, intent="pause"))
    return store


def fold_pause(store, tmp_path):
    with store.lock("c1") as lock:
        folded, _ = store.fold(lock, "c1", NOW, leave=queue.barrier(store, tmp_path))
    return folded


def test_a_pause_takes_the_queued_pr_out_before_it_folds(tmp_path, monkeypatch):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED})
    c = change()
    c.queue = QueueClaim(head=A, at=NOW, settled=True)
    folded = fold_pause(fold_store(tmp_path, monkeypatch, gh, c), tmp_path)
    assert (folded.intent.paused_at, folded.queue, folded.queue_seen, gh.dequeued) == (NOW, None, "RFMQE_9", [7])


def test_a_failed_dequeue_keeps_the_pause_waiting_and_unacknowledged(tmp_path, monkeypatch):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED})
    gh.dequeue_fails = True
    store = fold_store(tmp_path, monkeypatch, gh, change())  # a person's entry: no claim of Delivery's
    assert (fold_pause(store, tmp_path).intent.paused_at, store.read("c1").inbox_acked) == (None, [])
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox WHERE slug = 'c1'").fetchone() == (1,)
    gh.dequeue_fails = False
    assert (fold_pause(store, tmp_path).intent.paused_at, gh.dequeued) == (NOW, [7])


def test_a_paused_host_takes_the_queued_pr_out_before_the_pause_applies(tmp_path, monkeypatch):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED})
    gh.dequeue_fails = True
    c = change()
    c.queue = QueueClaim(head=A, at=NOW, settled=True)
    store = fold_store(tmp_path, monkeypatch, gh, c)
    paused = scheduler.Host(store, tmp_path, paused=lambda: True)
    paused.observe_pr = lambda _slug: ("open", True)  # only a PR's end applies while paused (TD-303)
    assert paused.tick(NOW) == []
    assert (store.read("c1").intent.paused_at, store.read("c1").queue is not None) == (None, True)  # waits (TD-226)
    gh.dequeue_fails = False
    assert paused.tick(NOW) == []
    after = store.read("c1")
    assert (after.intent.paused_at, after.queue, gh.dequeued) == (NOW, None, [7])  # TD-284


@pytest.mark.parametrize("settled", [False, True])
def test_an_attempt_without_a_trace_keeps_the_pause_waiting_until_the_owner_answers(tmp_path, monkeypatch, settled):
    gh = QueueGh(pr(head=A))
    asked = Question(id="q1", step=StepKind.MERGE, text="no trace", cause=queue.UNSEEN, options=[queue.PAUSE])
    c = change(questions=[asked])
    c.queue = QueueClaim(head=A, at=NOW, settled=settled, quiet=queue.QUIET)
    store = fold_store(tmp_path, monkeypatch, gh, c)
    assert (fold_pause(store, tmp_path).intent.paused_at, gh.dequeued) == (None, [])
    store.put_inbox("c1", AnswerItem(at=NOW, question="q1", option="pause"))
    folded = fold_pause(store, tmp_path)
    assert (folded.intent.paused_at is not None, folded.queue) == (True, None)


def test_a_merged_pr_keeps_a_restart_waiting_until_the_fold_sees_the_merge(tmp_path, monkeypatch):
    gh = QueueGh(pr(head=A))
    gh.state = QueueState(merged=True, open=False, head_sha=A, removed=removal("merged"))
    c = change(loops={"final": RoundLoop(subject="final", policy=RoundPolicy())})
    store = fold_store(tmp_path, monkeypatch, gh, c)
    store.put_inbox("c1", RestartItem(at=NOW))
    with store.lock("c1") as lock:
        assert store.fold(lock, "c1", NOW, leave=queue.barrier(store, tmp_path))[0].step.kind == StepKind.MERGE
        folded, _ = store.fold(lock, "c1", NOW, "merged", leave=queue.barrier(store, tmp_path))
    assert (folded.step.kind, folded.step.mode) == (StepKind.CLEANUP, None)


def test_a_rules_question_takes_a_queued_pr_out_first(tmp_path, clone):
    gh = QueueGh(pr(head=A))  # the target now requires a queue; the profile still says it does not
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED})
    p = profile.confirm(prof(**profile.rule_entries(Rules(state="known", evidence="before"))), profile.RULES, "x", NOW)
    cx = ctx(tmp_path, gh, p)
    cx.store.root.mkdir()
    c, result = merge.run(cx, change(worktree=str(clone)))
    assert (result.exit, gh.dequeued, c.queue) == (Exit.ASK, [7], None)


def test_a_restart_never_counts_as_the_owners_answer_about_an_untraced_attempt(tmp_path, monkeypatch):
    gh = QueueGh(pr(head=A))
    asked = Question(id="q1", step=StepKind.MERGE, text="no trace", cause=queue.UNSEEN, options=[queue.PAUSE])
    c = change(questions=[asked], loops={"final": RoundLoop(subject="final", policy=RoundPolicy())})
    c.queue = QueueClaim(head=A, at=NOW, quiet=queue.QUIET)
    store = fold_store(tmp_path, monkeypatch, gh, c)
    store.put_inbox("c1", RestartItem(at=NOW))
    with store.lock("c1") as lock:
        folded, _ = store.fold(lock, "c1", NOW, leave=queue.barrier(store, tmp_path))
    assert (folded.step.kind, folded.queue is not None) == (StepKind.MERGE, True)


def test_a_removal_at_the_adopted_entrys_own_time_stays_to_be_handled(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    same = removal("failed_checks").model_copy(update={"at": NOW})
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED, "removed": same})
    c, _ = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (c.queue.adopted, c.queue_seen) == (True, "")


def test_a_removal_older_than_the_attempt_is_not_its_own(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    old = removal("failed_checks").model_copy(update={"at": NOW - timedelta(hours=1)})
    gh.state = gh.state.model_copy(update={"entry": entry(), "added": ADDED, "removed": old})
    _, result = queue_step(tmp_path, gh, queued_change(clone))
    assert (result.exit, result.reason) == (Exit.PENDING, "PR #7 in the merge queue: position 1, queued")


def test_a_removal_is_this_attempts_only_after_the_added_event_of_its_own_entry(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.ordered = True  # an earlier attempt's added and removed events; this attempt's added is not visible yet
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal("failed_checks"), "removed_last": True})
    c = change(worktree=str(clone))
    c.queue = QueueClaim(head=A, at=NOW, queued_at=NOW + timedelta(minutes=5), settled=True)
    c, result = queue_step(tmp_path, gh, c)
    assert (result.exit, c.queue is not None) == (Exit.PENDING, True)
    c.queue = QueueClaim(head=A, at=NOW, settled=False)  # an unknown send is bound to no entry: nothing is its own
    c, result = queue_step(tmp_path, gh, c)
    assert (result.exit, c.queue is not None) == (Exit.PENDING, True)


def test_a_visible_removal_is_repaired_before_the_owners_again(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal("failed_checks")})
    asked = Question(id="q1", step=StepKind.MERGE, text="no trace", cause=queue.UNSEEN, options=[queue.AGAIN])
    asked.answer = Answer(option="again", at=NOW)
    _, result = queue_step(tmp_path, gh, queued_change(clone, questions=[asked]))
    assert (result.back_to, gh.enqueued) == (StepKind.BUILD, [])


def test_a_restart_waits_for_the_owners_answer_about_an_untraced_attempt(tmp_path, monkeypatch):
    gh = QueueGh(pr(head=A))
    asked = Question(id="q1", step=StepKind.MERGE, text="no trace", cause=queue.UNSEEN, options=[queue.PAUSE])
    c = change(questions=[asked], loops={"final": RoundLoop(subject="final", policy=RoundPolicy())})
    c.queue = QueueClaim(head=A, at=NOW, quiet=queue.QUIET)
    assert round_flow.restartable(c) == "answer the merge-queue question first"
    store = fold_store(tmp_path, monkeypatch, gh, c)
    store.put_inbox("c1", RestartItem(at=NOW))
    store.put_inbox("c1", AnswerItem(at=NOW, question="q1", option="pause"))
    folded = fold_pause(store, tmp_path)
    assert (folded.intent.paused_at is not None, folded.queue, folded.step.kind) == (True, None, StepKind.MERGE)


def test_an_entry_seen_under_the_merge_lock_is_followed_not_sent_again(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    reads = iter([gh.state, gh.state.model_copy(update={"entry": entry(), "added": ADDED})])
    gh.read_queue = lambda _r, _n: next(reads)
    c, result = queue_step(tmp_path, gh, change(worktree=str(clone)))
    assert (gh.enqueued, c.queue.adopted, result.exit) == ([], True, Exit.PENDING)


def test_unreadable_group_diagnostics_still_give_one_fix_task_and_handle_the_removal(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    gh.group_runs = lambda _r, _s: (_ for _ in ()).throw(
        ProviderError(FailureCode.UNAVAILABLE, "runs", "x", retry_safe=True)
    )
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal("failed_checks")})
    c, result = queue_step(tmp_path, gh, queued_change(clone))
    assert (result.back_to, c.queue_seen) == (StepKind.BUILD, "RFMQE_1")
    assert "could not be read" in result.fix_task.detail


def test_group_fixes_score_by_failing_workflow_so_fewer_is_progress(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    run = {"head_sha": GROUP, "branch": "gh-readonly-queue/main/pr-7-x", "status": "completed", "updated_at": NOW}
    gh.runs = (
        GroupRun(id=1, name="Python", conclusion="failure", **run),
        GroupRun(id=2, name="Static", conclusion="failure", **run),
    )
    gh.state = gh.state.model_copy(update={"added": ADDED, "removed": removal("failed_checks")})
    _, result = queue_step(tmp_path, gh, queued_change(clone))
    assert (result.score.failing, result.score.findings) == (2, ["Python", "Static"])


def test_a_replacement_entry_rebinds_so_its_removal_is_repaired(tmp_path, clone):
    gh = QueueGh(pr(head=A))
    later = NOW + timedelta(minutes=3)
    b = QueueEvent(id="ATMQE_2", kind="added", at=later, actor="maba-pag")
    replaced = entry().model_copy(update={"enqueued_at": later})
    gh.state = gh.state.model_copy(
        update={"entry": replaced, "added": b, "removed": removal("manual", actor="maba-pag")}
    )
    c, _ = queue_step(tmp_path, gh, queued_change(clone))  # bound to the first entry at NOW
    assert c.queue.queued_at == later
    gone = removal("failed_checks", rid="RFMQE_2").model_copy(update={"at": later + timedelta(minutes=1)})
    gh.state = gh.state.model_copy(update={"entry": None, "removed": gone})
    _, result = queue_step(tmp_path, gh, c)
    assert result.back_to == StepKind.BUILD


def test_the_profile_keeps_only_the_merge_methods_the_pull_request_rule_allows(clone):
    gh = FakeGh(pr(head=A))
    methods = (MergeMethod.SQUASH, MergeMethod.MERGE, MergeMethod.REBASE)
    gh.read_repository = lambda: Repository(
        repository="o/r", url="https://github.com/o/r", default_branch="main", methods=methods, can_push=True,
        delete_branch_on_merge=False,
    )  # fmt: skip
    gh.read_rules = lambda _r, _b: Rules(
        state="known", evidence="rules pull_request", allowed_methods=(MergeMethod.MERGE,)
    )
    found = profile.detect(clone, gh, None)
    assert (profile.value(found, profile.METHODS), profile.value(found, profile.METHOD)) == ("merge", "merge")


def test_the_queue_read_takes_the_group_commit_and_the_latest_events():
    added = {
        "__typename": "AddedToMergeQueueEvent",
        "createdAt": "2026-10-17T17:30:40Z",
        "actor": {"login": "maba-pag"},
    }
    gone = {"__typename": "RemovedFromMergeQueueEvent", "id": "R1", "createdAt": "2026-10-17T17:33:45Z"}
    gone |= {"reason": "failed_checks", "actor": {"login": "github-merge-queue"}, "beforeCommit": {"oid": GROUP}}
    queued = {
        "state": "AWAITING_CHECKS",
        "position": 1,
        "enqueuedAt": "2026-10-17T17:35:01Z",
        "headCommit": {"oid": GROUP},
    }
    nodes = [added | {"id": "A1"}, gone, added | {"id": "A2", "actor": None}]
    pull = {
        "state": "OPEN",
        "merged": False,
        "headRefOid": A,
        "mergeQueueEntry": queued,
        "timelineItems": {"nodes": nodes},
    }
    q = gh_queue._state(pull)  # noqa: SLF001 - the parser of GitHub's answer as recorded live
    assert (q.entry.group_sha, q.added.id, q.removed.reason, q.removed.before) == (GROUP, "A2", "failed_checks", GROUP)
    assert q.removed_last is False  # A2 was added after R1
    assert gh_queue._state(pull | {"timelineItems": {"nodes": nodes[:2]}}).removed_last is True  # noqa: SLF001
    building = pull | {"mergeQueueEntry": queued | {"headCommit": None, "state": "QUEUED"}}
    assert gh_queue._state(building).entry.group_sha is None  # noqa: SLF001 - no group is built yet
