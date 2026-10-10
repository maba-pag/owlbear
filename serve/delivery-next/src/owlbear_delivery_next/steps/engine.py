"""Engine steps' shared context and exits: Git in the worktree, GitHub through the provider (D3 §3.2, §3.3)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next import failures, loop, profile
from owlbear_delivery_next.git.remote_git import RemoteGitError, RemoteGitFailed, RemoteGitTimeout, run_remote_git
from owlbear_delivery_next.github.provider import FailureCode, ProviderError
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import ErrorKind, Exit, Option, Profile, Question, StepKind, Stop, Task, Waiting
from owlbear_delivery_next.steps import conversation, worktree

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.github.provider import Provider, Rules
    from owlbear_delivery_next.loop import PrState, Seen
    from owlbear_delivery_next.models import Actor, Change
    from owlbear_delivery_next.store import Lock, Store

type Step = Callable[[Ctx, Change], tuple[Change, StepResult]]
type Origin = Literal["review", "ci", "pr-feedback", "integration"]


@dataclass
class Ctx:
    """What an engine step reads and writes besides the Change: store, repository, profile and provider."""

    store: Store
    lock: Lock
    repo: Path
    profile: Profile
    gh: Provider
    now: datetime

    @property
    def repository(self) -> str:
        """``owner/name`` of the profile's repository."""
        return profile.value(self.profile, profile.REPO)

    def poll(self) -> datetime:
        """When a pending condition is observed again."""
        return self.now + timedelta(seconds=int(profile.value(self.profile, profile.POLL, "20")))

    def log(self, slug: str, event: str, **fields: object) -> None:
        """Append one activity event."""
        at = datetime.now(UTC).isoformat(timespec="seconds")
        self.store.log(self.lock, slug, {"event": event, "at": at, **fields})

    def events(self, slug: str, event: str) -> list[dict[str, object]]:
        """Return the retained activity events of one kind, oldest first."""
        return [e for e in self.store.events(slug) if e.get("event") == event]


def git_ok(path: Path, *args: str) -> bool:
    """Run one local Git query and return whether it exited 0."""
    return (
        subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
            [worktree.GIT, *args], cwd=path, capture_output=True, check=False, timeout=60
        ).returncode
        == 0
    )


def head(path: Path) -> str:
    """The worktree's HEAD commit."""
    return worktree.git(path, "rev-parse", "HEAD").strip()


def fetch(path: Path, branch: str) -> None:
    """Update ``origin/<branch>`` with a bounded remote read.

    Raises:
        RemoteGitFailed: The fetch did not succeed.
    """
    spec = f"+refs/heads/{branch}:refs/remotes/origin/{branch}"
    done = run_remote_git(path, ("fetch", "--quiet", "--no-tags", "origin", spec), kind="read")
    if done.returncode != 0:
        msg = f"fetch of {branch} failed: {done.stderr.decode(errors='replace').strip()[-200:]}"
        raise RemoteGitFailed(msg, retry_safe=True, result=done)


def contains(path: Path, ancestor: str, ref: str = "HEAD") -> bool:
    """Whether *ancestor* is already in *ref*."""
    return git_ok(path, "merge-base", "--is-ancestor", ancestor, ref)


def task(c: Change, title: str, origin: Origin, detail: str = "", tid: str | None = None) -> Task:
    """A fix task over the plan's scope with the first task's checks; appended without a new plan version."""
    tasks = c.plan.tasks if c.plan else []
    scope = list(dict.fromkeys(p for t in tasks for p in t.scope))
    checks = tasks[0].checks if tasks else []
    tid = tid or f"t{len(tasks) + 1}"
    return Task(id=tid, title=title, scope=scope, checks=checks, origin=origin, detail=detail[-4000:])


def back(kind: ErrorKind, step: StepKind, subject: str, reason: str, fix: Task) -> StepResult:
    """Back to build with one appended task; counted per cause."""
    cause = failures.cause_key(kind, step, subject)
    return StepResult(exit=Exit.BACK, back_to=StepKind.BUILD, cause=cause, reason=reason, fix_task=fix)


def integrate(c: Change, step: StepKind, ref: str, detail: str = "") -> StepResult:
    """Integration runs as a Builder task (DR3): merge *ref* into the branch before publishing or merging."""
    title = f"Merge {ref} into this branch with `git merge {ref}`, resolve any conflicts, run the checks, commit"
    return back(ErrorKind.CONFLICT, step, ref, f"updating with {ref}", task(c, title, "integration", detail))


def needs_target(c: Change, path: Path, reason: str, now: datetime) -> StepResult:
    """I6: the task needs a target commit or API this branch lacks; integrate during build, then resume the task."""
    try:
        fetch(path, c.names.target)
    except RemoteGitError as exc:
        return failed(c, exc, now)
    return integrate(c, StepKind.BUILD, f"origin/{c.names.target}", f"The Builder of {c.step.task} needs: {reason}")


def pending(waiting: Waiting, reason: str, wake: datetime | None, who: Actor = "github") -> StepResult:
    """Pending on an observed condition; none consumes budget."""
    return StepResult(exit=Exit.PENDING, waiting=waiting, reason=reason, who=who, wake_at=wake)


def ask(step: StepKind, text: str, cause: str | None, options: list[Option] | None = None) -> StepResult:
    """Ask the owner; the answer's option names the step that follows."""
    question = Question(step=step, text=text, cause=cause, options=options or [])
    return StepResult(exit=Exit.ASK, reason=text, cause=cause, question=question)


def continue_or_pause(step: StepKind) -> list[Option]:
    """The two options of an owner action question."""
    return [Option(id="done", label="Done, continue", next=step), Option(id="pause", label="Pause", next="pause")]


def rules_changed(ctx: Ctx, c: Change) -> tuple[StepResult | None, Rules]:
    """Re-read effective rules and required checks; a difference from the profile becomes ``ask`` showing it."""
    diffs, rules = profile.reread(ctx.profile, ctx.gh, c.names.target)
    if not diffs:
        return None, rules
    text = f"Branch rules differ from the profile ({'; '.join(diffs)}); run `owlbear-next profile` to confirm them"
    cause = failures.cause_key(ErrorKind.GATE, c.step.kind, "rules")
    return ask(c.step.kind, text, cause, continue_or_pause(c.step.kind)), rules


def failed(c: Change, exc: Exception, now: datetime) -> StepResult:
    """Map provider and remote Git failures: sign-in asks with the command; the rest retry as classified."""
    kind = c.step.kind
    if isinstance(exc, ProviderError) and exc.code == FailureCode.AUTHENTICATION_REQUIRED:
        text = f"GitHub refused the credential ({exc}): run `gh auth login` (or `gh auth refresh`), then continue"
        return ask(kind, text, failures.cause_key(ErrorKind.AUTH, kind, "gh"), continue_or_pause(kind))
    if isinstance(exc, ProviderError) and exc.code == FailureCode.CONFLICT and not exc.retry_safe:
        stop = Stop(kind=ErrorKind.GATE, reason=str(exc), action="Resolve it in GitHub", resume="GitHub agrees", at=now)
        return StepResult(exit=Exit.STOP, reason=str(exc), stop=stop)
    cause = failures.cause_key(classify(exc), kind, "github" if isinstance(exc, ProviderError) else "git")
    return StepResult(exit=Exit.RETRY, cause=cause, reason=str(exc)[:300], wake_at=now + timedelta(minutes=1))


def classify(exc: Exception) -> ErrorKind:
    """A typed transport failure is the environment's episode; any other provider or Git failure is a defect."""
    if isinstance(exc, ProviderError):
        if exc.code == FailureCode.RATE_LIMITED:
            return ErrorKind.CAPACITY
        return ErrorKind.NETWORK if exc.code in _TRANSPORT else ErrorKind.TOOLING
    if isinstance(exc, RemoteGitTimeout) or getattr(exc, "timed_out", False):
        return ErrorKind.NETWORK
    return failures.transient(str(exc)) or ErrorKind.TOOLING


_TRANSPORT = frozenset({FailureCode.UNAVAILABLE, FailureCode.TIMEOUT, FailureCode.RESPONSE_UNKNOWN})


def run(step: Step, ctx: Ctx, c: Change) -> tuple[Change, StepResult]:
    """Run one engine step; a typed provider or remote Git failure becomes its exit."""
    try:
        return step(ctx, c)
    except (ProviderError, RemoteGitError) as exc:
        return c, failed(c, exc, ctx.now)


def unsupported(c: Change, now: datetime) -> StepResult:
    """``integrate`` runs as a Builder task in this slice; the step kind itself stops."""
    reason = f"step {c.step.kind} runs as a Builder task in this version"
    stop = Stop(kind=ErrorKind.TOOLING, reason=reason, action="Upgrade OwlBear", resume="The step is supported", at=now)
    return StepResult(exit=Exit.STOP, reason=reason, stop=stop)


def pr_state(gh: Provider, repository: str, c: Change, offered: str | None = None) -> Seen:
    """The PR's terminal state for the scheduler, None when unreadable; reads the conversation only for consent."""
    if c.names.pr is None or not repository or c.finished_at:
        return None, False
    try:
        pr = gh.read_pull_request(repository, c.names.pr)
        state: PrState = "merged" if pr.merged else pr.state
        if state != "open" or not loop.waiting_consent(c):
            return state, False
        items = gh.read_conversation(repository, pr.number)
        opened = [s.item.id for s in conversation.open_items(c, items, gh.viewer)]
    except ProviderError:
        return None, False
    return state, loop.consent_moved(c, offered, pr.head_sha, opened)


def observe(store: Store, repo: Path, slug: str) -> Seen:
    """The PR's terminal state of one Change, read from GitHub with the profile's provider."""
    prof = store.read_profile() or Profile()
    offered = next((e.get("head") for e in reversed(store.events(slug)) if e.get("event") == "merge-offer"), None)
    return pr_state(profile.provider(prof, repo), profile.value(prof, profile.REPO), store.read(slug), offered)
