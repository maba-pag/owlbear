"""A test review (C-26): its start from the Maintenance page, then the TESTS step's parallel reviewers (TD-373).

The owner's Start approves the fixed brief and plan (TD-390), so the Change begins at TESTS with its worktree at the
target's HEAD, the commit every share is judged at. One runner runs each unfinished share's reviewer, read-only, in
waves of its session grant; a share that submits its verdicts has ended, and the next runner reruns only the others.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import curation_tools, tools
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    ErrorKind,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
)
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.change_flow.curation_flow import CURATE
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.runtimes import sdk_adapter, session_result
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.briefs import new_slug, next_number
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import curation_shares, sessions

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Lock, Store

TITLE = "Review the tests"
OUTCOME = "Tests that protect no behaviour beyond another test are retired or merged; every other test stays"
CRITERIA = (
    (
        "Every retired or merged test names the behaviour it protected, a plausible bug and the remaining test that "
        "still catches it"
    ),
    "Security guards, incident regressions and public-contract tests stay",
    "A test in doubt stays",
    "The suite is measured before and after with the same command and scope, and no test that passed before fails",
)
RULES = (
    "Check each retire and merge verdict of the test reviewers against the code; apply what holds and keep what does "
    "not. Edit only tests. Rewrite-lower notes are not applied in this review."
)
STARTING = threading.Lock()  # one start at a time in this process, the project's only host


class StartError(Exception):
    """A test review that cannot start; ``status`` is the HTTP answer."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the answer's status and words."""
        super().__init__(text)
        self.status = status


def open_review(store: Store) -> Change | None:
    """The project's test review that has not finished, if any: one runs at a time."""
    for slug in store.slugs():
        try:
            c = store.read(slug)
        except StoreError:  # an unreadable Change is shown on the Changes page, not here
            continue
        if c.tests and not c.finished_at:
            return c
    return None


def _target(store: Store, repo: Path) -> tuple[str, str]:
    target = profile.value(store.read_profile() or Profile(), profile.DEFAULT, "main")
    return target, worktree.git(repo, "rev-parse", worktree.tracking(repo, target)).strip()


def offer(store: Store, repo: Path) -> dict[str, Any]:
    """What the dialog shows before a start: the packages with tests, the shares, the roles, the sessions limit."""
    settings, found = store.settings(), []
    if (open_ := open_review(store)) is None:
        _, commit = _target(store, repo)
        found = [
            {"path": p.path, "files": len(p.files), "lines": p.lines, "shares": len(curation_shares.split([p]))}
            for p in curation_shares.packages(repo, commit)
        ]
    chosen = {r: settings.agents[r] for r in ("test-reviewer", "test-curator")}
    return {
        "open": {"slug": open_.slug, "handle": open_.handle} if open_ else None,
        "packages": found,
        "roles": {r: {"model": a.model, "effort": a.effort, "context": a.context} for r, a in chosen.items()},
        "sessions": settings.sessions,
    }


def start(store: Store, repo: Path, chosen: list[str], now: datetime) -> Change:
    """The owner's Start: one Change with the approved fixed brief and plan, its commit pinned, at TESTS (TD-390).

    Starts run one at a time; each takes its own handle number first, so a start that failed half way never lends
    its slug, branch or worktree to the next.

    Raises:
        StartError: A test review is open, or no chosen package has tests.
    """
    with STARTING:
        return _start(store, repo, chosen, now)


def _start(store: Store, repo: Path, chosen: list[str], now: datetime) -> Change:
    if open_ := open_review(store):
        raise StartError(409, f"the test review {open_.handle} has not finished")
    target, commit = _target(store, repo)
    picked = {p.path: p for p in curation_shares.packages(repo, commit) if p.path in chosen}
    if not picked:
        raise StartError(422, "choose at least one package with tests")
    number = next_number(store)
    store.issue(number)
    slug = new_slug(f"{TITLE} {number}", store.slugs())
    branch = f"owlbear/{slug}"
    path = worktree.ensure(repo, git_common_dir(repo), slug, branch, target)
    head = worktree.head(path)
    packages = [p for p in curation_shares.packages(repo, head) if p.path in picked]
    scope = [p.path for p in packages]
    criteria = [Criterion(id=f"AC-{i}", text=t) for i, t in enumerate(CRITERIA, 1)]
    brief = Brief(version=1, title=TITLE, outcome=OUTCOME, scope=scope, criteria=criteria, challenged=1)
    brief.approved_version, brief.approved_at = 1, now
    brief.approved = [brief.model_copy(deep=True)]
    c = Change(
        slug=slug, handle=f"c{number}", profile_version=(store.read_profile() or Profile()).version, brief=brief,
        plan=Plan(tasks=[Task(id=CURATE, title="Curate the tests", scope=scope, detail=RULES)]),
        step=Step(kind=StepKind.TESTS), names=Names(branch=branch, target=target, worktree=str(path)),
        tests=TestReview(commit=head, packages=scope, shares=curation_shares.split(packages)),
    )  # fmt: skip
    with store.lock(slug) as lock:
        store.write(lock, c)
    return c


def _message(t: TestReview, i: int) -> str:
    share, mine = t.shares[i], set(t.shares[i].paths)
    near = [p for s in t.shares for p in s.paths if p not in mine and p.split("/")[0] == share.paths[0].split("/")[0]]
    lines = [
        f"# Test review: share {i + 1} of {len(t.shares)}",
        f"Judge each test of these files at commit {t.commit[:12]}, read-only:",
        *(f"- {p}" for p in share.paths),
        "",
        "Other reviewers judge these tests at the same time; a bug may still be caught there:",
        *(f"- {p}" for p in near[:300]),
        "",
        "## Finish",
        "Call submit_result with your verdicts, how many tests stay, and every file you read in covered_paths.",
    ]
    return "\n".join(lines)


def _session(store: Store, lock: Lock, t: TestReview, i: int, at: Path) -> sdk_adapter.Session:
    return sdk_adapter.Session(
        kind=StepKind.REVIEW, worktree=at, session_id="", message=_message(t, i), resume=False,
        policy=Policy(at, write=False), observe=lambda: tools.Worktree(t.commit, t.commit), checks=(),
        submit=curation_tools.TEST_REVIEW, journal=sdk_adapter.Journal(lambda e: store.log(lock, lock.slug, e)),
        memory=sessions.memory(store),
    )  # fmt: skip


def run(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """Run the unfinished shares' reviewers; record each submitted review; the step's exit follows the rest.

    Raises:
        sessions.UsageUnreadError: A submitted review's model is unknown: the owner decides (TD-54).
    """
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree, change.step.started_at = str(path), datetime.now(UTC)
    store.write(lock, change)
    t = change.tests
    if t is None or worktree.head(path) != t.commit:  # never judged at another commit than the one pinned
        _end(store, lock, change, _moved(t.commit if t else "", worktree.head(path)))
        return
    left = [i for i, s in enumerate(t.shares) if s.ended is None]

    def made(at: Path) -> list[tuple[str, sdk_adapter.Session]]:
        return [(curation_tools.REVIEW_LABEL, _session(store, lock, t, i, at)) for i in left]

    try:
        judged = sessions.judges(store, lock, change, path, made, store.settings(), hold=True) if left else []
    except sessions.UsageUnreadError as exc:  # what did submit is kept; the owner decides the rest (TD-54)
        _kept(store, lock, left, exc.runs)  # in the round's order; the gated run itself is neither kept nor held
        raise
    ran = [done for _, done in judged]
    if gate := _kept(store, lock, left, ran):
        raise gate
    c = store.read(lock.slug)
    _end(store, lock, c, _exit(len(c.tests.shares) if c.tests else 0, ran))


def _kept(
    store: Store, lock: Lock, left: list[int], runs: list[session_result.Run]
) -> sessions.UsageUnreadError | None:
    """Record each submitted review whose model is known; log every held one's usage but the first, which gates."""
    c = store.read(lock.slug)  # the judges' spend and logs
    shares, held = c.tests.shares if c.tests else [], list[session_result.Run]()
    for i, done in zip(left, runs, strict=False):
        if isinstance(done.payload, curation_tools.TestReviewResult) and not sessions.unread(done):
            shares[i].review, shares[i].ended = done.payload, "reviewed"
        elif sessions.held(done):
            held.append(done)
    store.write(lock, c)
    for done in held[1:]:
        sessions.logged(store, lock, store.read(lock.slug), done, {"kind": curation_tools.REVIEW_LABEL, "exit": "held"})
    return sessions.UsageUnreadError(held[0], curation_tools.REVIEW_LABEL) if held else None


def _exit(shares: int, runs: list[session_result.Run]) -> loop.StepResult:
    """A session not confirmed gone stops the Change; else the first share without a review fails the step."""
    gone = next((r for r in runs if not (r.termination and r.termination.confirmed)), None)
    failed = next((r for r in runs if not isinstance(r.payload, curation_tools.TestReviewResult)), None)
    if run := gone or failed:
        return session_result.to_result(run, StepKind.TESTS, datetime.now(UTC))
    return loop.StepResult(exit=Exit.DONE, reason=f"every one of {shares} share(s) ended")


def _moved(commit: str, head: str) -> loop.StepResult:
    reason = f"the test review's worktree is at {head[:12]}, not at the commit it reviews, {commit[:12]}"
    stop = Stop(
        kind=ErrorKind.STATE, reason=reason, action="Abandon the test review and start another",
        resume="The worktree is back at the reviewed commit", at=datetime.now(UTC),
    )  # fmt: skip
    return loop.StepResult(exit=Exit.STOP, reason=reason, stop=stop)


def _end(store: Store, lock: Lock, c: Change, result: loop.StepResult) -> None:
    now = datetime.now(UTC)
    store.write(lock, loop.apply(c, result, now))
    sessions.out(f"{c.slug}: tests {result.exit}: {result.reason}")
