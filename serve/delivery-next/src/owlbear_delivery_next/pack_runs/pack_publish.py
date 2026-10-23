"""A design pack update's way into ``main`` (step 3c, TD-325, TD-368): commit, branch, pull request, CI and merge.

The commit lands on ``pack/<run>`` from the base pinned when the candidate was made; the pull request to ``main`` is
opened ready, with the starting project's labels and marker (TD-308). The required checks come from ``main``'s rules
and must pass at the pull request's current head, an empty or pending observation never counting as green. Behind
``main``, GitHub's update-branch brings the branch up to date at the expected head and CI is awaited again; the merge
is a merge commit at the expected head, a lost answer read back before anything is repeated. Every step reconciles
with GitHub first, so a retry after a host restart pushes nothing twice and opens no second pull request. Whatever
stops it asks the owner (``Held``): try again after fixing it, or discard.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.design_packs import pack_git
from owlbear_delivery_next.github.provider import (
    MergeMethod,
    MergeRequest,
    MergeStatus,
    ProviderError,
    PullRequest,
    Refusal,
    classify_checks,
)
from owlbear_delivery_next.settings.config import SettingsUnset

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.github.provider import Provider
    from owlbear_delivery_next.pack_runs.pack_job import Job

ROUNDS = 3  # update-branch rounds before the owner is asked
WORKTREE = "design-pack-commit"  # the disposable worktree of the commit, under the store
MARKER = "Opened by OwlBear Delivery for a design pack update."


class Held(Exception):  # noqa: N818 - how publication hands over to the owner
    """Publication cannot go on without the owner; the reason says why."""


class Publication(BaseModel):
    """Where the update goes and how far it got; kept with the run, so a retry reconciles instead of repeating."""

    model_config = ConfigDict(extra="forbid")

    root: str  # the package's checkout
    repository: str
    base: str  # the commit pinned when the candidate was made
    branch: str
    body: str = ""  # the pull request's text, kept so a retry opens the same one
    commit: str = ""
    number: int = 0
    url: str = ""
    merged: str = ""  # the merge commit on main


def publish(job: Job, pub: Publication, files: dict[str, str | None], title: str) -> str:
    """Take the update into ``main``; the merge commit.

    Raises:
        Held: The owner decides: a refused push, a failed check, a conflict, a closed pull request, rules that
            cannot be read, CI that does not finish, or the update-branch rounds running out.
    """
    live, body = job.live, pub.body
    src = pack_git.Source(Path(pub.root), pub.repository, pub.base)
    gh = live.github(src.root)
    if pub.number and (pr := gh.read_pull_request(pub.repository, pub.number)).merged:  # a lost answer, read back first
        return _done(job, gh, pub, pr.merge_commit_sha or "")
    if not pub.commit:
        at = job.store.root / WORKTREE
        pub.commit = _held(job, "commit", lambda: pack_git.commit(src, files, f"{title}\n\n{body}", at, live.git),
                           lambda c: f"{c[:12]} on {pub.branch}")  # fmt: skip
        job.published(pub)
    _held(job, "push", lambda: pack_git.push(src, pub.commit, pub.branch, live.git), lambda _o: pub.branch)
    pr = _held(job, "pull-request", lambda: _opened(job, gh, pub, title, body), lambda p: p.url)
    pub.number, pub.url = pr.number, pr.url
    job.published(pub)
    merged = _held(job, "merge", lambda: _merged(job, gh, pub), lambda sha: f"merged as {sha[:12]}")
    return _done(job, gh, pub, merged)


def _done(job: Job, gh: Provider, pub: Publication, merged: str) -> str:
    pub.merged = merged
    job.published(pub)
    with contextlib.suppress(ProviderError):
        gh.delete_branch(pub.repository, pub.branch)
    return merged


def preflight(gh: Provider, repository: str) -> str:
    """Whether ``gh`` on this machine may push to *repository*: checked before any download or session.

    Raises:
        Held: It may not, with what to do.
    """
    try:
        found = gh.read_repository()
    except ProviderError as exc:
        msg = f"gh cannot read {repository} ({exc}); sign in with `gh auth login` and run the update again"
        raise Held(msg) from exc
    if found.repository.casefold() != repository.casefold() or not found.can_push:
        msg = f"gh on this machine cannot push to {repository}; sign in as an account that can, then run it again"
        raise Held(msg)
    return f"gh may push to {found.repository}"


def _held[T](job: Job, name: str, work: Callable[[], T], said: Callable[[T], str]) -> T:
    """One stage whose failure goes to the owner instead of ending the run."""

    def guarded() -> T:
        try:
            return work()
        except Held:
            raise
        except Exception as exc:
            raise Held(str(exc)) from exc

    return job.do(name, guarded, said, hold=Held)


def _opened(job: Job, gh: Provider, pub: Publication, title: str, body: str) -> PullRequest:
    """The update's pull request: found again, or opened ready with the project's labels and marker."""
    pr = gh.read_pull_request(pub.repository, pub.number) if pub.number else None
    pr = pr or gh.find_pull_request(pub.repository, pub.branch, pack_git.BASE)
    if pr is not None and pr.state == "closed" and not pr.merged:
        msg = f"the pull request {pr.url} was closed; reopen it and try again, or discard"
        raise Held(msg)
    settings = job.store.settings()
    try:
        settings.need("pr_marker", "pr_labels")
    except SettingsUnset as exc:
        raise Held(str(exc)) from exc
    if pr is None:
        text = f"{body}\n\n{MARKER}" if settings.pr_marker else body
        pr = gh.create_pull_request(pub.repository, pub.branch, pack_git.BASE, title, text)
    try:  # on a pull request found again too: its creation's answer may have been lost before its labels
        if settings.pr_labels:
            gh.add_labels(pub.repository, pr.number, list(settings.pr_labels))
    except ProviderError as exc:  # a label never holds the update (TD-308)
        job.log(f"the labels {', '.join(settings.pr_labels)} were not added: {exc}")
    if pr.draft:
        gh.mark_ready(pr)
    return pr


def _merged(job: Job, gh: Provider, pub: Publication) -> str:
    """Wait for the required checks at the current head, bring the branch up to date, merge; the merge commit."""
    rules = gh.read_rules(pub.repository, pack_git.BASE)
    if rules.state != "known":
        msg = f"the rules of {pack_git.BASE} could not be read ({rules.evidence}); fix access and try again"
        raise Held(msg)
    for _ in range(ROUNDS):
        pr = gh.read_pull_request(pub.repository, pub.number)
        if pr.merged:
            return pr.merge_commit_sha or ""
        if pr.state == "closed":
            msg = f"the pull request {pr.url} was closed; reopen it and try again, or discard"
            raise Held(msg)
        if not _green(job, gh, pr, rules.required_checks):
            continue  # the head moved while the checks ran
        if pr.merge_state == "behind":
            gh.update_branch(pub.repository, pr.number, pr.head_sha)
            _moved(job, gh, pr)
            continue
        request = MergeRequest(repository=pub.repository, number=pr.number, expected_head_sha=pr.head_sha,
                               method=MergeMethod.MERGE)  # fmt: skip
        done = gh.request_merge(request)
        if done.status == MergeStatus.MERGED and done.sha:
            return done.sha
        if done.status == MergeStatus.REFUSED and done.refusal not in {Refusal.HEAD_CHANGED, Refusal.NOT_MERGEABLE}:
            msg = f"GitHub refused the merge of {pr.url}: {done.refusal} {done.message or ''}".strip()
            raise Held(msg)
        job.log(f"the merge of {pr.url} did not land ({done.status}); reading it back")  # a lost answer is read first
    pr = gh.read_pull_request(pub.repository, pub.number)
    if pr.merged:
        return pr.merge_commit_sha or ""
    msg = f"{pr.url} could not be merged after {ROUNDS} rounds of bringing it up to date; try again or discard"
    raise Held(msg)


def _green(job: Job, gh: Provider, pr: PullRequest, required: tuple[str, ...]) -> bool:
    """Wait until every check at the head passed: True; False when the head moved meanwhile.

    Raises:
        Held: A check failed, or CI did not finish in time.
    """
    live, waited = job.live, 0.0
    while waited <= live.ci_wait:
        now = gh.read_pull_request(pr.repository, pr.number)
        if now.head_sha != pr.head_sha:
            return False
        ci = classify_checks(gh.observe_checks(pr.repository, pr.number, pr.head_sha), (), required)
        if ci.failed:
            names = ", ".join(c.name for c in ci.failed)
            msg = f"CI failed at {pr.head_sha[:12]} of {pr.url}: {names}; fix it and try again, or discard"
            raise Held(msg)
        if ci.passed and not ci.running and not ci.missing:
            return True
        live.sleep(live.poll)
        waited += live.poll
    msg = f"CI at {pr.head_sha[:12]} of {pr.url} did not finish in {live.ci_wait / 60:.0f} minutes; try again later"
    raise Held(msg)


def _moved(job: Job, gh: Provider, pr: PullRequest) -> None:
    """Wait for the branch to leave the head GitHub's update-branch started from."""
    live, waited = job.live, 0.0
    while waited <= live.ci_wait and gh.read_pull_request(pr.repository, pr.number).head_sha == pr.head_sha:
        live.sleep(live.poll)
        waited += live.poll
