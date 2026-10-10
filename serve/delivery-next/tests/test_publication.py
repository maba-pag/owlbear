import json
import subprocess
import tarfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, loop, profile, tools
from owlbear_delivery_next.git.remote_git import RemoteGitWriteUnknown, classify_write_readback, read_remote_ref
from owlbear_delivery_next.github import merge_offer
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.provider import (
    Check,
    ConversationItem,
    FailureCode,
    MergeResult,
    MergeStatus,
    ProviderError,
    PullRequest,
    Refusal,
    Rules,
    ThreadComment,
    classify_checks,
    merge_request_body,
)
from owlbear_delivery_next.models import (
    Answer,
    AnswerItem,
    Brief,
    Change,
    ConsentItem,
    Criterion,
    Environment,
    Exit,
    Inputs,
    ItemRef,
    Names,
    PersonCheck,
    Plan,
    Profile,
    ProfileEntry,
    Question,
    Response,
    Review,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.sdk_adapter import Run
from owlbear_delivery_next.setup import Check as SetupCheck
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import check, cleanup, conversation, engine, follow, merge, publish, review, worktree
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
    gh = FakeGh(pr(head=B))
    c = loop.fold(change(worktree=str(clone), head=B), [ConsentItem(at=NOW, head=A)], NOW)
    cx = ctx(tmp_path, gh, prof(**ASKING))
    _, result = merge.run(cx, c)
    offer = cx.events("c1", "merge-offer")[-1]
    assert (result.exit, result.cause) == (Exit.ASK, loop.CONSENT)
    assert result.reason.startswith(f"approve merging {B[:7]}, changed since {A[:7]} (1 commit(s)")
    assert (offer["head"], offer["void"]) == (B, A)
    assert gh.merges == []


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


def comment(cid, body, author="o", kind="comment"):
    return ConversationItem(id=cid, kind=kind, author=author, body=body, url=f"https://github.com/o/r/pull/7#{cid}")


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
    gh = ChatGh(pr(head=A), comment("b1", "Coverage: 91%", "github-actions"))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
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
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    c, _ = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (gh.resolved, c.handled[0].resolved) == (["t1"], True)
    gh.items = [i.model_copy(update={"resolved": False}) for i in gh.items]
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result.exit, result.fix_task.id, gh.resolved) == (Exit.BACK, f"{first}-2", ["t1"])


def test_an_acknowledged_resolve_is_recorded_at_once_and_a_later_unresolve_reopens_without_resolving(tmp_path):
    gh = ChatGh(pr(head=A), thread("t1", ("h1", "o", "why?")))
    cx = ctx(tmp_path, gh)
    c, result = follow.conversation(cx, change(), gh.pr, StepKind.FOLLOW)
    first = result.fix_task.id
    c = handled(c, result, "answered", "Because.")
    c, result = follow.conversation(cx, c, gh.pr, StepKind.FOLLOW)
    assert (result, gh.resolved, c.handled[0].resolved) == (None, ["t1"], True)
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
    review_, _ = tools.parse(
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
        {"comments": page([node("c2", "second")])},
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
    assert [(i.id, i.kind) for i in items] == [
        ("c1", "comment"),
        ("c2", "comment"),
        ("r1", "review"),
        ("r3", "review"),
        ("t1", "thread"),
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
    assert client.post("/api/next/changes/c1/check-results", json=body).json() == {"accepted": "check-result"}


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
    p.answer = Answer(at=NOW, passed=True, inputs=loop.check_inputs(c, p, check.fingerprints(c, p)))
    for path, version in (("a.txt", None), ("app/page.ts", "preview")):
        (clone / path).write_text("2\n")
        git(clone, "commit", "-qam", path)
        assert getattr(loop.next_check(c, check.declared(c)), "id", None) == version
    assert check.pending(c, env).reason.endswith("asked again: changed app/page.ts")


def test_publish_waits_for_the_network_and_asks_for_other_readiness_fixes():
    ok = [SetupCheck("network", ok=True, detail=""), SetupCheck("github cli", ok=True, detail="")]
    assert publish.gate(ok, NOW) is None
    net = publish.gate([SetupCheck("network", ok=False, detail="timed out", fix="Connect")], NOW)
    assert (net.exit, net.waiting, net.wake_at, net.who) == (
        Exit.PENDING,
        Waiting.NETWORK,
        NOW + timedelta(minutes=1),
        "delivery",
    )
    fix = "Run `gh auth login --hostname github.com`"
    auth = publish.gate([*ok, SetupCheck("github sign-in", ok=False, detail="expired", fix=fix)], NOW)
    assert (auth.exit, auth.cause, auth.reason.endswith(fix)) == (Exit.ASK, "auth:publish:github sign-in", True)
    assert [o.next for o in auth.question.options] == [StepKind.PUBLISH, "pause"]


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
    gh.pr, gh.checks, cx.now = pr(head=A), (), NOW
    m = loop.fold(change(worktree=str(clone)), [ConsentItem(at=NOW, head=A)], NOW)
    m, early = merge.run(cx, m)
    cx.now = NOW + timedelta(minutes=10)
    _, late = merge.run(cx, m)
    assert (early.waiting, late.exit, late.question.options[0].next) == (Waiting.CHECK_START, Exit.ASK, StepKind.MERGE)


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


def test_a_required_merge_queue_is_an_owner_action_and_never_submitted(tmp_path, clone):
    queued = Rules(state="known", evidence="rules merge_queue", types=("merge_queue",), queue_required=True)
    gh = FakeGh(pr(head=A))
    gh.read_rules = lambda _repo, _branch: queued
    p = profile.confirm(prof(**profile.rule_entries(queued)), profile.RULES, "merge_queue", NOW)
    _, result = merge.run(ctx(tmp_path, gh, p), change(worktree=str(clone)))
    assert (result.exit, result.waiting, result.who) == (Exit.PENDING, Waiting.OWNER_ACTION, "you")
    assert result.reason == "merge PR #7 in GitHub (merge queue not supported (TD-22))"
    assert gh.merges == []


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


def test_a_failing_check_on_the_merged_target_asks_and_a_passing_one_cleans_up(tmp_path):
    gh = FakeGh(pr(head=A, state="closed", merged=True, merge_commit_sha=B))
    target_checks(gh, ("test", "completed", "failure"))
    cx = ctx(tmp_path, gh)
    c = change(StepKind.CLEANUP)
    _, result = cleanup.run(cx, c)
    assert (result.exit, result.cause) == (Exit.ASK, loop.TARGET)
    assert result.question.text == "The merged result fails test on main (https://ci/1). Start a new Change to fix it."
    assert [o.id for o in result.question.options] == ["done", "pause"]
    target_checks(gh, ("test", "completed", "success"))
    assert cleanup.target_check(cx, change(StepKind.CLEANUP), gh.pr)[1] is None


def test_pausing_at_a_failing_target_check_holds_cleanup_but_a_plain_pause_does_not():
    c = change(StepKind.CLEANUP)
    c.intent.paused_at = NOW
    assert loop.next_step(c, NOW) == c.step
    question = Question(step=StepKind.CLEANUP, text="fails", cause=loop.TARGET, answer=Answer(option="pause", at=NOW))
    c.questions.append(question)
    assert loop.next_step(c, NOW) is None


def test_running_target_checks_wait_within_the_window_then_cleanup_proceeds(tmp_path):
    gh = FakeGh(pr(head=A, state="closed", merged=True, merge_commit_sha=B))
    target_checks(gh, ("test", "in_progress", None))
    cx = ctx(tmp_path, gh)
    c, held = cleanup.target_check(cx, change(StepKind.CLEANUP), gh.pr)
    assert (held.exit, held.waiting) == (Exit.PENDING, Waiting.CI)
    cx.now = NOW + timedelta(hours=1)
    c, held = cleanup.target_check(cx, c, gh.pr)
    assert (held, c.missing) == (None, None)
    assert cx.events("c1", "target-checks-unfinished")[-1]["sha"] == B


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
    for _ in ("build", "review"):
        c = loop.apply(c, loop.StepResult(exit=Exit.DONE), NOW)
    assert (c.step.kind, c.step.task) == (StepKind.BUILD, "t1")


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


def test_a_fix_task_has_a_short_title_and_carries_every_finding_up_to_its_bound(clone):
    finding = {"place": "a.txt:1", "problem": "AC-1: " + "p" * 400, "fix": "f" * 400}
    review_, _ = tools.parse(
        tools.ReviewResult, {"verdict": "fix", "findings": [finding] * 6, "covered_paths": ["a.txt"]}
    )
    c = change(StepKind.REVIEW)
    c.step.task = "t1"
    run = Run("s", "result", review_, head=worktree.head(clone))
    fix = review.recorded(c, None, run, clone, loop.StepResult(exit=Exit.RETRY, reason="cut")).fix_task
    assert (fix.title, fix.detail.count("- a.txt:1: AC-1: "), len(fix.detail)) == (
        "Fix 6 review finding(s) of task t1",
        5,
        4000,
    )
    assert fix.detail.endswith("\n[truncated]")
    assert not review.findings(review_, 10_000).endswith("[truncated]")


# Reopen and the pre-push hook


@pytest.mark.parametrize("push", ["yes", "no"])
def test_reopen_reopens_the_pr_when_permitted_else_asks_the_owner(tmp_path, push):
    gh = FakeGh(pr(head=B, state="closed"))
    c, _ = loop.schedule(change(StepKind.FOLLOW), [], NOW, "closed")
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question="q1", option="reopen")], NOW, "closed")
    c, result = follow.run(ctx(tmp_path, gh, prof(**{profile.PUSH: ProfileEntry(state="known", value=push)})), c)
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
