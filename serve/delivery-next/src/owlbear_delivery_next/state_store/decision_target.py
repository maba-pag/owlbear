"""Where a decision publication goes: the remote branch it was read for once, and the continuation bound to it.

`decision_sync` publishes to the target read when a publication begins and carries it to every later step, so a branch
checked out meanwhile, even at the same commit, never retargets a commit already checked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo


class Target(NamedTuple):
    """Where a publication goes: the local branch, its remote and remote branch, and that branch's fetched copy.

    Read once, when the publication starts, and carried with it: a branch checked out later never retargets it.
    """

    branch: str
    remote: str
    ref: str
    tracking: str


class Continuation(NamedTuple):
    """A publication going on after its commit landed: that commit, and the target it was published to.

    Every step of the continuation, its catch-up rebase and every flag round included, goes on only while the
    checkout still follows that target and HEAD is that commit or one already on its remote branch.
    """

    own: str
    goal: Target | None


def target(shared: DataRepo, until: float) -> Target | None:
    """The checked-out branch and the remote branch it follows; None when it follows none, or HEAD is detached."""
    branch = shared.git("symbolic-ref", "-q", "HEAD", until=until)
    name = branch.stdout.strip()
    if branch.returncode or not name:
        return None
    fields = "%(upstream:remotename)%00%(upstream:remoteref)%00%(upstream)"
    said = shared.git("for-each-ref", f"--format={fields}", name, until=until)
    remote, ref, tracking = ([*said.stdout.strip().split("\0"), "", ""])[:3]
    if said.returncode or not remote or not ref.startswith("refs/heads/") or not tracking.startswith("refs/remotes/"):
        return None
    return Target(name, remote, ref, tracking)


def push_commit(shared: DataRepo, commit: str, goal: Target | None, until: float) -> str:
    """Push exactly *commit* to *goal*'s remote branch, never forced; why not, else nothing.

    The commit is named by its id and the destination by the remote and branch read when the publication began, so
    neither HEAD nor the branch checked out by the time the push runs changes what is sent or where.
    """
    if goal is None:
        return "the checkout's branch follows no remote branch, so nothing was pushed"
    sent = shared.git("push", "-q", goal.remote, f"{commit}:{goal.ref}", until=until)
    return sent.stderr.strip()[:200] or "git push failed" if sent.returncode else ""
