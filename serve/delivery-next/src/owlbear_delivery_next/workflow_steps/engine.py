"""Engine steps' shared context and exits: Git in the worktree, GitHub through the provider (D3 §3.2, §3.3)."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.change_contracts import failures
from owlbear_delivery_next.change_contracts.models import (
    ErrorKind,
    Exit,
    Option,
    Question,
    StepKind,
    Stop,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import asking, delivery_target, loop, worktree
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.git.access import PushRefused
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.git.remote_git import RemoteGitError, RemoteGitFailed, RemoteGitTimeout, run_remote_git
from owlbear_delivery_next.github.account import AccountMissing
from owlbear_delivery_next.github.provider import FailureCode, ProviderError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.settings.config import SettingsUnset, pref
from owlbear_delivery_next.state_store import github_writer
from owlbear_delivery_next.workflow_steps import conversation

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Actor, Change
    from owlbear_delivery_next.change_flow.loop import PrState, Seen
    from owlbear_delivery_next.git.access import Access
    from owlbear_delivery_next.github.account import Writer
    from owlbear_delivery_next.github.provider import Provider, PullRequest, Rules
    from owlbear_delivery_next.state_store.store import Lock, Store

type Step = Callable[[Ctx, Change], tuple[Change, StepResult]]
type Origin = Literal["review", "ci", "pr-feedback", "integration"]


@dataclass
class Ctx:
    """What an engine step reads and writes besides the Change: store, repository, profile, provider and writer.

    ``writer`` is the account the project's GitHub writes are made by (TD-402); unset, it is the project's setting.
    """

    store: Store
    lock: Lock
    repo: Path
    profile: Profile
    gh: Provider
    now: datetime
    writer: Writer | None = None

    def __post_init__(self) -> None:
        if self.writer is None:
            self.writer = github_writer.of(self.store, self.repo)

    @property
    def repository(self) -> str:
        """``owner/name`` of the profile's repository."""
        return profile.value(self.profile, profile.REPO)

    def poll(self) -> datetime:
        """When a pending condition is observed again."""
        return self.now + timedelta(seconds=pref(self.store.settings(), "ci_poll_seconds"))

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


def fetch(path: Path, branch: str, access: Access) -> None:
    """Update ``origin/<branch>`` with a bounded remote read.

    Raises:
        RemoteGitFailed: The fetch did not succeed.
    """
    spec = f"+refs/heads/{branch}:refs/remotes/origin/{branch}"
    done = run_remote_git(path, ("fetch", "--quiet", "--no-tags", "origin", spec), kind="read", access=access)
    if done.returncode != 0:
        msg = f"fetch of {branch} failed: {done.stderr.decode(errors='replace').strip()}"
        raise RemoteGitFailed(msg, retry_safe=True, result=done)


def contains(path: Path, ancestor: str, ref: str = "HEAD") -> bool:
    """Whether *ancestor* is already in *ref*."""
    return git_ok(path, "merge-base", "--is-ancestor", ancestor, ref)


def task(c: Change, title: str, origin: Origin, detail: str = "", tid: str | None = None) -> Task:
    """A fix task over the plan's scope and package checks; appended without a new plan version."""
    tasks = c.plan.tasks if c.plan else []
    scope = list(dict.fromkeys(p for t in tasks for p in t.scope))
    checks = list(dict.fromkeys(check for task in tasks for check in task.checks))
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


def needs_target(c: Change, path: Path, reason: str, now: datetime, writer: Writer) -> StepResult:
    """I6: the task needs a target commit or API this branch lacks; integrate during build, then resume the task."""
    try:
        fetch(path, c.names.target, writer.access())
    except (RemoteGitError, ProviderError) as exc:
        return failed(c, exc, now)
    return integrate(c, StepKind.BUILD, f"origin/{c.names.target}", f"The Builder of {c.step.task} needs: {reason}")


def pending(waiting: Waiting, reason: str, wake: datetime | None, who: Actor = "github") -> StepResult:
    """Pending on an observed condition; none consumes budget."""
    return StepResult(exit=Exit.PENDING, waiting=waiting, reason=reason, who=who, wake_at=wake)


def ask(
    step: StepKind,
    text: str,
    cause: str | None,
    options: list[Option] | None = None,
    *,
    subject: Literal["product", "reserved"] | None = None,
) -> StepResult:
    """Ask the owner; the answer's option names the step that follows. After approval *subject* says why it is his."""
    question = Question(step=step, text=text, cause=cause, options=options or [], subject=subject)
    return StepResult(exit=Exit.ASK, reason=text, cause=cause, question=question)


def blocked(cause: str, said: str, detail: str, now: datetime | None = None) -> StepResult:
    """Delivery's own problem that only an action outside the Change ends: never a question (#1168).

    The step stops with the plain reason first and the whole evidence after it; "Run the step again" clears it.
    """
    reason = f"{said}.\n\nDetails: {detail}" if detail else said
    kind = ErrorKind(failures.kind_of(cause))
    at = now or datetime.now(UTC)
    stop = Stop(kind=kind, reason=reason, action=asking.RERUN, resume="the step runs again", at=at)
    return StepResult(exit=Exit.STOP, cause=cause, reason=reason, stop=stop)


PAUSE = Option(id="pause", label="No: pause this Change", next="pause")
_RULES = {  # the profile's rule entries in the owner's words
    profile.RULES: "kinds of rules on the branch",
    profile.REQUIRED: "checks GitHub requires before merging",
    profile.QUEUE: "merging only through the merge queue",
    profile.STRICT: "the branch must be up to date before merging",
    profile.RESOLUTION: "review conversations must be resolved before merging",
}


def _was(old: ProfileEntry | None) -> str:
    if old is None:
        return "not recorded"
    return old.value if old.state == "known" else "not readable"


def rules_changed(ctx: Ctx, c: Change) -> tuple[StepResult | None, Rules]:
    """Re-read effective rules and required checks against the profile.

    Rules GitHub would not show stop the step. A difference is the owner's yes or no on the rules as they are now;
    his yes to exactly these differences records them in the profile, and the step goes on.
    """
    diffs, rules = profile.reread(ctx.profile, ctx.gh, c.names.target)
    kind, target = c.step.kind, c.names.target
    if not diffs:
        return None, rules  # rules recorded as unreadable stay so: the merge gate handles them as before
    if rules.state == "unknown":
        cause = failures.cause_key(ErrorKind.GATE, kind, "rules-unread")
        said = f"Delivery could not read the merge rules of {target} on GitHub, so it cannot tell what a merge needs"
        return blocked(cause, said, rules.evidence, ctx.now), rules
    shown = hashlib.sha256("\n".join(diffs).encode()).hexdigest()[:12]
    cause = failures.cause_key(ErrorKind.GATE, kind, f"rules-{shown}")
    agreed = (q for q in c.questions if q.cause == cause and q.answer and not q.effect_observed_at)
    if (q := next(agreed, None)) is not None and q.answer and q.answer.option == "yes":
        ctx.profile = profile.adopt(ctx.profile, rules, ctx.now)
        ctx.store.write_profile(ctx.profile)
        q.effect_observed_at = ctx.now
        ctx.log(c.slug, "profile-confirmed", key="branch rules", value="; ".join(diffs))
        return None, rules
    read = profile.rule_entries(rules)
    lines = [
        f"{words}: was {_was(ctx.profile.entries.get(key))}, now {read[key].value}"
        for key, words in _RULES.items()
        if any(d.startswith(f"{key}:") for d in diffs)
    ]
    text = (
        f"The merge rules of {target} on GitHub differ from what Delivery recorded for this project: "
        f"{'; '.join(lines)}. Go on under the rules as they are now?"
    )
    options = [Option(id="yes", label="Yes: record them and go on", next=kind), PAUSE]
    return ask(kind, text, cause, options, subject="reserved"), rules


def failed(c: Change, exc: Exception, now: datetime) -> StepResult:
    """Map provider and remote Git failures: a refused sign-in or push stops with what to do; the rest retry."""
    kind = c.step.kind
    if isinstance(exc, AccountMissing | PushRefused):  # its text names the account, the cause and the fix (TD-402)
        error, subject = (ErrorKind.AUTH, "gh") if isinstance(exc, AccountMissing) else (ErrorKind.GATE, "ssh")
        said = "Delivery cannot reach GitHub as this project's account. Once it can, run the step again"
        return blocked(failures.cause_key(error, kind, subject), said, failure(exc), now)
    if isinstance(exc, ProviderError) and exc.code == FailureCode.AUTHENTICATION_REQUIRED:
        said = (
            "GitHub refused Delivery's sign-in. Sign in again in a terminal (`gh auth login`, or `gh auth refresh`), "
            "then run the step again"
        )
        return blocked(failures.cause_key(ErrorKind.AUTH, kind, "gh"), said, failure(exc), now)
    if isinstance(exc, ProviderError) and exc.code == FailureCode.CONFLICT and not exc.retry_safe:
        reason = failure(exc)
        stop = Stop(kind=ErrorKind.GATE, reason=reason, action="Resolve it in GitHub", resume="GitHub agrees", at=now)
        return StepResult(exit=Exit.STOP, reason=reason, stop=stop)
    cause = failures.cause_key(classify(exc), kind, "github" if isinstance(exc, ProviderError) else "git")
    reason = failure(exc)  # the classification above reads str(exc): the notes and streams never change it
    said = f"{type(exc).__name__}: {exc}"  # retries sign it without the notes, whose partial output varies
    return StepResult(exit=Exit.RETRY, cause=cause, reason=reason, classified=said, wake_at=now + timedelta(minutes=1))


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


def landed(ctx: Ctx, c: Change, pr: PullRequest) -> StepResult | None:
    """Validate a terminal merge before releasing its queue claim; otherwise ask or keep waiting."""
    if not pr.merged:
        return pending(Waiting.GITHUB, f"PR #{pr.number} is not confirmed merged", ctx.poll())
    if why := delivery_target.mismatch(c, pr, ctx.repository):
        c.stop = delivery_target.stop(c, why, ctx.now)
        return StepResult(exit=Exit.ASK, question=delivery_target.question(c, why))
    c.queue = None
    return None


def pr_state(gh: Provider, repository: str, c: Change, offered: str | None = None) -> Seen:
    """The PR's terminal state for the scheduler, None when unreadable; reads the conversation only for consent."""
    if c.names.pr is None or not repository or c.finished_at:
        return None, False
    try:
        pr = gh.read_pull_request(repository, c.names.pr)
        if pr.merged and delivery_target.mismatch(c, pr, repository):
            return "misdelivered", False
        state: PrState = "merged" if pr.merged else pr.state
        if state != "open" or not loop.waiting_consent(c):
            return state, False
        items = gh.read_conversation(repository, pr.number)
        opened = [s.item.id for s in conversation.open_items(c, items, gh.viewer)]
    except ProviderError, SettingsUnset:  # an unset account observes nothing, as unreachable GitHub does
        return None, False
    return state, loop.consent_moved(c, offered, pr.head_sha, opened)


def observe(store: Store, repo: Path, slug: str) -> Seen:
    """The PR's terminal state of one Change, read from GitHub with the profile's provider."""
    c = store.read(slug)
    if c.names.pr is None:
        return None, False
    prof = store.read_profile() or Profile()
    offered = next((e.get("head") for e in reversed(store.events(slug)) if e.get("event") == "merge-offer"), None)
    gh = profile.provider(prof, repo, github_writer.of(store, repo))
    return pr_state(gh, profile.value(prof, profile.REPO), c, offered)
