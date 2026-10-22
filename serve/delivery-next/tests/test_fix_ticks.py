"""A finished Change ticks off the decision fix entries it verified (TD-428, decision system §9.3)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts.models import Change, Exit, Names, Step, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
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


def test_a_merged_change_ticks_only_the_items_its_changed_files_cover(tmp_path, shared, github, merged):
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


def test_the_change_is_found_under_this_clone_s_id_and_an_owner_s_tick_meanwhile_is_kept(
    tmp_path, shared, github, merged
):
    repo, sha = merged
    (repo / ".git" / "owlbear-delivery").mkdir()
    (repo / ".git" / "owlbear-delivery" / "clone-id").write_text("abc123\n")
    fix = entry(shared, FIX, ["a.py", "docs/c.md"], change="abc123/c1")
    elsewhere = entry(shared, FIX.replace("D1", "D2"), ["a.py"], change="zzz999/c1")  # another clone's c1
    issue = github.issues[int(fix)]
    issue["body"] = issue["body"].replace("- [ ] docs/c.md", "- [x] docs/c.md", 1)  # ticked on GitHub

    finish(tmp_path, shared, repo, Gh(pr(sha)))

    assert (now(shared, fix).status, ticks(now(shared, fix).text)) == ("done", {"a.py": True, "docs/c.md": True})
    assert now(shared, elsewhere).status == "in-change"


@pytest.mark.usefixtures("github")
@pytest.mark.parametrize("ended", ["abandoned", "unchanged"])
def test_a_change_that_merged_nothing_ticks_nothing_and_reopens_its_fixes(tmp_path, shared, merged, ended):
    repo, _ = merged
    fix = entry(shared, FIX, ["a.py", "!docs/c.md"])
    gh = Gh(pr(None, merged=False) if ended == "abandoned" else None)

    finish(tmp_path, shared, repo, gh, "abandon" if ended == "abandoned" else None)

    assert (now(shared, fix).status, ticks(now(shared, fix).text)) == ("open", {"a.py": False, "docs/c.md": True})
    assert "Verified by" not in now(shared, fix).text


@pytest.mark.usefixtures("github")
def test_an_abandoning_change_whose_pr_merged_anyway_credits_nothing(tmp_path, shared, merged):
    repo, sha = merged
    fix = entry(shared, FIX, ["a.py"])

    finish(tmp_path, shared, repo, Gh(pr(sha)), "abandon")

    assert (now(shared, fix).status, ticks(now(shared, fix).text)) == ("open", {"a.py": False})


def scheduled(shared: DataRepo, impact: Impact, change: str) -> str:
    """A path-free report's fix entry, scheduled and launched into *change* from the backlog."""
    fields = {"scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.DECIDED, "actor": "owner", "created_at": NOW}
    old = Decision(id=new_id(), title="Notes live in SQLite", statement="SQLite.", state=State.REPLACED, **fields)
    new = Decision(id=new_id(), title="Notes live in Postgres", statement="Postgres.", state=State.IN_FORCE,
                   links=(Link(type=LinkType.REPLACES, target=old.id),), **fields)  # fmt: skip
    [made] = decision_fixes.schedule(shared, Report(old, new, "forbids", (impact,)), new.revision)
    return Backlog(shared, PROJECT).update(made["id"], {"change": change, "status": "in-change"}).id


@pytest.mark.usefixtures("github")
@pytest.mark.parametrize("launched", ["confirmed", "unknown"])
def test_a_path_free_fix_is_completed_by_the_merged_change_launched_from_it_and_by_no_other(
    tmp_path, shared, merged, launched
):
    repo, sha = merged
    built = {"slug": "c0", "title": "Notes", "pr": f"{URL[:-1]}5", "from": "merged"}
    impacts = {"confirmed": Impact(PROJECT, "confirmed", "built under it", (built,), ()),
               "unknown": Impact(PROJECT, "unknown", "no record", (), ())}  # fmt: skip
    fix = scheduled(shared, impacts.pop(launched), "c1")
    unrelated = scheduled(shared, impacts.popitem()[1], "c9")

    finish(tmp_path, shared, repo, Gh(pr(sha)))

    done = now(shared, fix)
    assert (done.status, all(ticks(done.text).values()), done.evidence[-1]) == ("done", True, URL)
    assert f"Verified by Change c1 ({URL}), merged: its checklist names no files." in done.text
    left = now(shared, unrelated)
    assert (left.status, any(ticks(left.text).values()), "Verified by" in left.text) == ("in-change", False, False)


@pytest.mark.usefixtures("github")
def test_a_merge_that_changed_no_files_does_not_complete_a_path_free_fix(shared):
    impact = Impact(PROJECT, "unknown", "no record", (), ())
    fix = now(shared, scheduled(shared, impact, "c1"))

    fields = decision_fixes._verify(frozenset(), {"c1"}, PROJECT, ("c1", URL))(fix, "")  # noqa: SLF001

    assert fields["status"] == "open"
    assert not any(ticks(fields["text"]).values())
    assert "Verified by" not in fields["text"]


@pytest.mark.usefixtures("github")
def test_an_entry_reassigned_meanwhile_is_left_as_it_is(tmp_path, shared, merged, monkeypatch):
    repo, sha = merged
    fix = entry(shared, FIX, ["a.py"])
    revise = Backlog.revise

    def reassigned_first(self, entry_id, work):
        Backlog(shared, PROJECT).update(entry_id, {"change": "c9"})  # the owner moved it to another Change
        return revise(self, entry_id, work)

    monkeypatch.setattr(Backlog, "revise", reassigned_first)
    finish(tmp_path, shared, repo, Gh(pr(sha)))

    assert (now(shared, fix).change, now(shared, fix).status, ticks(now(shared, fix).text)) == (
        "c9", "in-change", {"a.py": False})  # fmt: skip


@pytest.mark.parametrize("failure", ["github", "diff"])
def test_a_failure_leaves_the_fixes_as_they_were_and_cleanup_finishes_with_a_notice(
    tmp_path, shared, github, merged, failure
):
    repo, sha = merged
    fix = entry(shared, FIX, ["a.py"])
    before = github.issues[int(fix)]["body"]
    github.down = failure == "github"

    cx = finish(tmp_path, shared, repo, Gh(pr(sha if failure == "github" else "f" * 40)))

    github.down = False
    assert (github.issues[int(fix)]["body"], now(shared, fix).status) == (before, "in-change")
    [event] = cx.events("c1", "decision-fixes")
    assert event["notice"].startswith("the decision fixes of c1 were not updated: ")
