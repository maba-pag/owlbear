"""Where a decision publication goes: the remote branch it was read for once, and the continuation bound to it.

`decision_sync` publishes to the target read when a publication begins and carries it to every later step, so a branch
checked out meanwhile, even at the same commit, never retargets a commit already checked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    import subprocess

    from owlbear_delivery_next.local_system.data_repo import DataRepo


class Target(NamedTuple):
    """Where a publication goes: its branch, remote, remote branch, fetched copy and the remote's addresses then.

    The addresses are its one fetch address and its push addresses, each a whole value. Read once, when the
    publication starts, and carried with it: a branch checked out later never retargets it, and a remote pointed at
    another repository later never receives or proves what was checked against the first.
    """

    branch: str
    remote: str
    ref: str
    tracking: str
    fetch: str
    pushes: tuple[str, ...]


class Continuation(NamedTuple):
    """A publication going on after its commit landed: that commit, and the target it was published to.

    Every step of the continuation, its catch-up rebase and every flag round included, goes on only while the
    checkout still follows that target and HEAD is that commit or one already on its remote branch.
    """

    own: str
    goal: Target | None


def target(shared: DataRepo, until: float) -> Target | None:
    """The checked-out branch, the remote branch it follows and that remote's addresses; None when it lacks one.

    None when it follows no remote branch, HEAD is detached, or the remote's addresses cannot be read whole.
    """
    branch = shared.git("symbolic-ref", "-q", "HEAD", until=until)
    name = branch.stdout.strip()
    if branch.returncode or not name:
        return None
    fields = "%(upstream:remotename)%00%(upstream:remoteref)%00%(upstream)"
    said = shared.git("for-each-ref", f"--format={fields}", name, until=until)
    remote, ref, tracking = ([*said.stdout.strip().split("\0"), "", ""])[:3]
    if said.returncode or not remote or not ref.startswith("refs/heads/") or not tracking.startswith("refs/remotes/"):
        return None
    found = addresses(shared, remote, until)
    return Target(name, remote, ref, tracking, *found) if found else None


def addresses(shared: DataRepo, remote: str, until: float) -> tuple[str, tuple[str, ...]] | None:
    """*remote*'s one fetch address and its push addresses as Git prints them; None when Git cannot say.

    Each line is kept whole, spaces and all. A remote that names no single fetch address is also None.
    """
    fetched = _lines(shared.git("remote", "get-url", remote, until=until))
    pushes = _lines(shared.git("remote", "get-url", "--push", "--all", remote, until=until))
    if fetched is None or pushes is None or len(fetched) != 1 or not fetched[0] or not all(pushes):
        return None
    return fetched[0], tuple(pushes)


def _lines(said: subprocess.CompletedProcess[str]) -> list[str] | None:
    """Git's newline-terminated values, each kept whole; a failed command or unterminated output is unknown."""
    if said.returncode or not said.stdout.endswith("\n"):
        return None
    return said.stdout[:-1].split("\n")


def moved(shared: DataRepo, goal: Target, until: float) -> str:
    """Why *goal*'s remote no longer has the addresses it had when the publication began; nothing when it does.

    The addresses themselves are never shown: they may hold credentials.
    """
    if addresses(shared, goal.remote, until) == (goal.fetch, goal.pushes):
        return ""
    return f"the remote {goal.remote} points elsewhere than when this publication began, so nothing was pushed"


def push_commit(shared: DataRepo, commit: str, goal: Target | None, until: float) -> str:
    """Push exactly *commit* to *goal*'s remote branch, never forced; why not, else nothing.

    The commit is named by its id and the destination by the remote and branch read when the publication began, so
    neither HEAD nor the branch checked out by the time the push runs changes what is sent or where. The remote's
    addresses must still be those it had then: checked first, and again as the push's guard, after the shared
    checkout's own probes and immediately before Git starts the push, so a repoint during those probes sends nothing.
    Only the moment between that last read and Git starting is left, as for any check made before a command runs.
    """
    if goal is None:
        return "the checkout's branch follows no remote branch, so nothing was pushed"
    if why := moved(shared, goal, until):
        return why
    sent = shared.git(
        "push", "-q", goal.remote, f"{commit}:{goal.ref}", until=until, guard=lambda: moved(shared, goal, until)
    )
    return sent.stderr.strip()[:200] or "git push failed" if sent.returncode else ""
