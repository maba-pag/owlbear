"""A finished Change ticks off the decision fix entries it verified (TD-428, decision system §9.3)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts.models import Change, Exit, Names, Step, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import decision_fixes
from owlbear_delivery_next.state_store.backlog import Backlog
from owlbear_delivery_next.state_store.decision_impact import Impact, Report
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import cleanup, engine

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
FIX = "Apply decision D1 in shop-site: Notes live in Postgres"
HEAD = "Old rule (D0, revision r0) …\nNew rule (D1, revision r1) …\n\nTick each item once a Change has verified it:"
URL = "https://github.com/o/r/pull/7"


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)


@pytest.fixture
def merged(tmp_path) -> tuple[Path, str]:
    """The project's clone and a merge commit only its remote holds: the PR changed a.py and src/x/b.py.

    docs/c.md changed on main meanwhile, outside the PR.
    """
    bare, work, other = tmp_path / "shop.git", tmp_path / "shop", tmp_path / "other"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    write(work, {"a.py": "a\n", "src/x/b.py": "b\n", "docs/c.md": "c\n"})
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    git(work, "remote", "add", "origin", str(bare))
    git(work, "push", "-q", "-u", "origin", "main")
    git(tmp_path, "clone", "-q", str(bare), str(other))
    git(other, "switch", "-qc", "owlbear/c1")
    write(other, {"a.py": "a2\n", "src/x/b.py": "b2\n"})
    git(other, "commit", "-qam", "the Change")
    git(other, "switch", "-q", "main")
    write(other, {"docs/c.md": "c2\n"})
    git(other, "commit", "-qam", "elsewhere")
    git(other, "merge", "-q", "--no-ff", "-m", "Merge pull request #7", "owlbear/c1")
    git(other, "push", "-q", "origin", "main")
    return work, git(other, "rev-parse", "HEAD")


@pytest.fixture
def shared(shared_repo) -> DataRepo:
    repo = DataRepo(shared_repo[0])
    repo.claim(PROJECT, "github.com/acme/shop-site")
    return repo


class Gh:
    def __init__(self, pr: PullRequest | None) -> None:
        self.pr = pr

    def read_pull_request(self, _repo, _number):
        return self.pr

    def observe_commit_checks(self, _repo, _sha):
        return ()

    def close_pull_request(self, _repo, _number):
        return None


def pr(sha: str | None, *, merged: bool = True) -> PullRequest:
    return PullRequest(repository="o/r", number=7, node_id="n", url=URL, head_branch="owlbear/c1", head_sha="a" * 40,
                       base_branch="main", draft=False, state="closed", merged=merged,
                       merge_commit_sha=sha)  # fmt: skip


def finish(tmp_path: Path, shared: DataRepo, repo: Path, gh: Gh, mode: str | None = None) -> engine.Ctx:
    store = Store(tmp_path / "store", shared, PROJECT)
    store.root.mkdir(parents=True, exist_ok=True)
    p = Profile(version=1, entries={profile.REPO: ProfileEntry(state="known", value="o/r")})
    cx = engine.Ctx(store, Lock("c1"), repo, p, gh, NOW)
    names = Names(branch="owlbear/c1", target="main", pr=7 if gh.pr else None)
    _, result = cleanup.run(cx, Change(slug="c1", step=Step(kind=StepKind.CLEANUP, mode=mode), names=names))
    assert result.exit == Exit.DONE, result.reason
    return cx


def entry(shared: DataRepo, title: str, items: list[str], change: str = "c1", head: str = HEAD) -> str:
    text = "\n".join([head, *(f"- [{'x' if i.startswith('!') else ' '}] {i.lstrip('!')}" for i in items)])
    backlog = Backlog(shared, PROJECT)
    made, _ = backlog.add(title, text, "owner")
    fields = {"projects": [PROJECT], "change": change, "status": "in-change", "kind": "improvement"}
    return backlog.update(made.id, fields).id


def now(shared: DataRepo, entry_id: str):
    return Backlog(shared, PROJECT).current(entry_id)


def ticks(text: str) -> dict[str, bool]:
    return {line[6:]: line[3] == "x" for line in text.splitlines() if line.startswith("- [")}


def test_merged_cleanup_credits_only_this_changes_verified_work(tmp_path, shared, github, merged):
    repo, sha = merged
    partial = entry(shared, FIX, [f"Change c0: Notes ({URL[:-1]}5)", "a.py", "src/x/", "src/y/", "docs/c.md", "!e.py"])
    whole = entry(shared, FIX.replace("D1", "D2"), ["a.py", "src/x/b.py"])
    other = entry(shared, "Tidy a.py", ["a.py"])  # not a decision fix
    later = entry(shared, FIX.replace("D1", "D3"), ["a.py"], change="c2")  # another Change's
    finish(tmp_path, shared, repo, Gh(pr(sha)))

    left = now(shared, partial)
    assert ticks(left.text) == {f"Change c0: Notes ({URL[:-1]}5)": False, "a.py": True, "src/x/": True,
                                "src/y/": False, "docs/c.md": False, "e.py": True}  # fmt: skip
    assert (left.status, left.evidence[-1]) == ("open", URL)
    assert f"Verified by Change c1 ({URL}): 2 item(s) ticked." in left.text
    done = now(shared, whole)
    assert (done.status, github.issues[int(whole)]["state"], all(ticks(done.text).values())) == ("done", "closed", True)
    for untouched in (other, later):
        assert (now(shared, untouched).status, ticks(now(shared, untouched).text)) == ("in-change", {"a.py": False})
    (repo / ".git" / "owlbear-delivery").mkdir()
    (repo / ".git" / "owlbear-delivery" / "clone-id").write_text("abc123\n")
    owner = entry(shared, FIX.replace("D1", "D4"), ["a.py", "docs/c.md"], change="abc123/c1")
    elsewhere = entry(shared, FIX.replace("D1", "D5"), ["a.py"], change="zzz999/c1")
    issue = github.issues[int(owner)]
    issue["body"] = issue["body"].replace("- [ ] docs/c.md", "- [x] docs/c.md", 1)
    finish(tmp_path, shared, repo, Gh(pr(sha)))
    assert (now(shared, owner).status, ticks(now(shared, owner).text)) == ("done", {"a.py": True, "docs/c.md": True})
    assert (now(shared, elsewhere).status, ticks(now(shared, elsewhere).text)) == ("in-change", {"a.py": False})


@pytest.mark.usefixtures("github")
@pytest.mark.parametrize("ended", ["abandoned", "unchanged", "merged-while-abandoning"])
def test_cleanup_without_delivery_reopens_without_credit(tmp_path, shared, change_repo, ended):
    items = ["a.txt"] if ended == "merged-while-abandoning" else ["a.py", "!docs/c.md"]
    expected = {"a.txt": False} if ended == "merged-while-abandoning" else {"a.py": False, "docs/c.md": True}
    fix = entry(shared, FIX, items)
    observed = None
    if ended == "abandoned":
        observed = pr(None, merged=False)
    elif ended == "merged-while-abandoning":
        observed = pr(git(change_repo, "rev-parse", "HEAD"))
    finish(tmp_path, shared, change_repo, Gh(observed), None if ended == "unchanged" else "abandon")
    assert (now(shared, fix).status, ticks(now(shared, fix).text)) == ("open", expected)
    assert "Verified by" not in now(shared, fix).text


def scheduled(shared: DataRepo, impact: Impact, change: str) -> str:
    """A path-free report's fix entry, scheduled and launched into *change* from the backlog."""
    fields = {"scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.DECIDED, "actor": "owner", "created_at": NOW}
    old = Decision(id=new_id(), title="Notes live in SQLite", statement="SQLite.", state=State.REPLACED, **fields)
    new = Decision(id=new_id(), title="Notes live in Postgres", statement="Postgres.", state=State.IN_FORCE,
                   links=(Link(type=LinkType.REPLACES, target=old.id),), **fields)  # fmt: skip
    [made] = decision_fixes.schedule(shared, Report(old, new, "forbids", (impact,)), new.revision)
    return Backlog(shared, PROJECT).update(made["id"], {"change": change, "status": "in-change"}).id


@pytest.mark.usefixtures("github")
def test_path_free_fix_requires_its_own_nonempty_merged_change(shared):
    built = {"slug": "c0", "title": "Notes", "pr": f"{URL[:-1]}5", "from": "merged"}
    impacts = (
        Impact(PROJECT, "confirmed", "built under it", (built,), ()),
        Impact(PROJECT, "unknown", "no record", (), ()),
    )
    fixes = [scheduled(shared, impact, "c1") for impact in impacts]
    unrelated = [scheduled(shared, impact, "c9") for impact in impacts]
    fix = now(shared, fixes[1])
    fields = decision_fixes._verify(frozenset(), {"c1"}, PROJECT, ("c1", URL))(fix, "")  # noqa: SLF001

    assert fields["status"] == "open"
    assert not any(ticks(fields["text"]).values())
    assert "Verified by" not in fields["text"]
    decision_fixes.verified(Backlog(shared, PROJECT), "c1", None, frozenset({"a.py", "src/x/b.py"}), URL)
    for entry_id in fixes:
        done = now(shared, entry_id)
        assert (done.status, all(ticks(done.text).values()), done.evidence[-1]) == ("done", True, URL)
        assert f"Verified by Change c1 ({URL}), merged: its checklist names no files." in done.text
    for entry_id in unrelated:
        left = now(shared, entry_id)
        assert (left.status, any(ticks(left.text).values()), "Verified by" in left.text) == ("in-change", False, False)


@pytest.mark.usefixtures("github")
def test_fix_reassignment_is_rechecked_during_revision(shared, monkeypatch):
    fix = entry(shared, FIX, ["a.py"])
    revise = Backlog.revise

    def reassigned_first(self, entry_id, work):
        Backlog(shared, PROJECT).update(entry_id, {"change": "c9"})  # the owner moved it to another Change
        return revise(self, entry_id, work)

    monkeypatch.setattr(Backlog, "revise", reassigned_first)
    decision_fixes.verified(Backlog(shared, PROJECT), "c1", None, frozenset({"a.py"}), URL)

    assert (now(shared, fix).change, now(shared, fix).status, ticks(now(shared, fix).text)) == (
        "c9", "in-change", {"a.py": False})  # fmt: skip


@pytest.mark.parametrize("failure", ["github", "diff"])
def test_fix_update_failure_preserves_records_and_finishes_cleanup_with_a_notice(
    shared, github, merged, whole_error, failure
):
    repo, sha = merged  # the clone lies in the test's tmp_path, beside the store finish makes
    missing = "f" * 40
    fix = entry(shared, FIX, ["a.py"])
    before = github.issues[int(fix)]["body"]
    github.down = failure == "github"
    diff = [worktree.GIT, "diff", "--name-only", "--no-renames", "-z", f"{missing}^1", missing]
    real_run, failed = subprocess.run, []

    def longer_error(command, *args, **kwargs):  # the real diff fails; a long whole error is added to its own
        try:
            return real_run(command, *args, **kwargs)
        except subprocess.CalledProcessError as exc:
            if command == diff:
                failed.append((exc.cmd, exc.returncode, exc.stderr))
                exc.stderr += whole_error.encode()
            raise

    with pytest.MonkeyPatch.context() as patched:
        if failure == "diff":
            patched.setattr(subprocess, "run", longer_error)
        cx = finish(repo.parent, shared, repo, Gh(pr(sha if failure == "github" else missing)))

    github.down = False
    assert (github.issues[int(fix)]["body"], now(shared, fix).status) == (before, "in-change")
    [event] = cx.events("c1", "decision-fixes")
    if failure == "github":
        assert event["notice"].startswith("the decision fixes of c1 were not updated: ")
        return
    [(command, status, said)] = failed
    assert (command, status) == (diff, 128)
    assert missing.encode() in said  # Git's own error, naming the missing merge, is what the notice carries
    assert event["notice"] == (
        "the decision fixes of c1 were not updated: CalledProcessError: "
        f"Command '{diff}' returned non-zero exit status 128.\n{said.decode()}{whole_error}"
    )
