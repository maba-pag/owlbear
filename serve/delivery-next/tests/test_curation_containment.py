"""#746: a refused curation run's edits never reach the remote, while every other writer's commits still do."""

import re
import subprocess
import threading
import time
from pathlib import Path

import pytest
from owlbear_memory import MemoryBusyError, MemoryCategory, MemoryEngine, MemoryState, storage, writer_lock

from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult
from owlbear_delivery_next.change_flow.worktree import git
from owlbear_delivery_next.local_system import data_place, preload
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, curation_tree
from owlbear_delivery_next.runtimes.session_result import Run

REPORT = MemoryCurationResult(summary="curated", entries=[])
CURATOR = "chore: memory curation batch (memory-mcp, memory-curator)"
HELD = re.compile(r"refs/owlbear/curation/[0-9a-f]{32}")
FULL = "[Errno 28] No space left on device"


@pytest.fixture
def repo(shared_repo) -> Path:
    data = shared_repo[0]
    for name in ("owlbear", "shop"):
        (data / name / "memory").mkdir(parents=True)
    (data / "memory").mkdir()  # Global
    return data


@pytest.fixture
def remote(shared_repo) -> Path:
    return shared_repo[1]


def pending(folder: Path, title: str):
    return MemoryEngine(folder).save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip


def curated(folder: Path, title: str):
    entry = pending(folder, title)
    return MemoryEngine(folder).edit(entry.id, {"scope_agents": ["builder"]}, expected_revision=entry.revision)


def reword(folder: Path, entry_id: str, content: str):
    engine = MemoryEngine(folder)
    return engine.edit(entry_id, {"content": content}, expected_revision=engine.get_entry(entry_id).revision)


def rel(entry, folder: str = "shop") -> str:
    return f"{folder}/memory/{entry.id}.md"


def pushed(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    git(repo, "push", "-q")


def committed(memory: Path, *paths: str) -> str:
    """The curator's commit, as `commit_batch` makes it in the checkout it works in; its id."""
    top = Path(git(memory, "rev-parse", "--show-toplevel").strip())
    git(top, "add", "-A", "--", *paths)
    git(top, "commit", "-qm", CURATOR)
    return git(top, "rev-parse", "HEAD").strip()


def bare(remote: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # CI sets safe.bareRepository=explicit: the bare remote is always named
    return subprocess.run(["git", f"--git-dir={remote}", *args], capture_output=True, check=False)  # noqa: S603, S607


def remote_has(remote: Path, sha: str) -> bool:
    assert bare(remote, "rev-parse", "--verify", "-q", "main").returncode == 0  # readable, so absence is real
    return bare(remote, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def remote_bytes(remote: Path, path: str) -> bytes | None:
    found = bare(remote, "show", f"main:{path}")
    return found.stdout if found.returncode == 0 else None


def publish_other(repo: Path, name: str) -> str:
    """Another writer's save, published as every save is; the commit it made."""
    shared, path = DataRepo(repo), repo / "shop" / f"notes-{name}.txt"
    path.write_text(name)
    with shared.locked():
        made = shared.commit(path, f"other writer: {name}")
        assert (made, bool(made.commit)) == ("", True)
        assert shared.publish([], "nothing new") == ""
    return made.commit


def drained(job: curation.Curation, folder: str = "shop") -> curation.FolderRun:
    end = time.monotonic() + 30
    while job.worker is not None:
        assert time.monotonic() < end, "the curation queue did not drain"
        time.sleep(0.02)
    return job.load().folders[folder]


def held(repo: Path, reason: str, path: str) -> bytes:
    """What the ref the reason names holds at *path*."""
    found = HELD.search(reason)
    assert found, reason
    return subprocess.run(["git", "show", f"{found.group()}:{path}"], cwd=repo, capture_output=True, check=True).stdout  # noqa: S603, S607


REFUSALS = {
    "unread": {"ending": "result", "payload": REPORT, "usage_unread": "no tokens"},
    "no-report": {"ending": "result"},
    "error-with-report": {"ending": "error", "payload": REPORT, "detail": "model unavailable"},
    "unconfirmed": {"ending": "result", "payload": REPORT},
}


@pytest.mark.parametrize("refusal", list(REFUSALS))
def test_a_refused_runs_commit_never_reaches_the_remote_while_another_writers_does(repo, remote, refusal) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    before = (repo / rel(entry)).read_bytes()
    made = {}

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        made["curator"] = committed(cfg.memory, "shop/memory")
        made["bytes"] = (cfg.memory / f"{entry.id}.md").read_bytes()
        if refusal != "unconfirmed":
            return Run(cfg.session_id, termination=Termination(confirmed=True), **REFUSALS[refusal])
        shared, notes = DataRepo(repo), repo / "shop" / "notes.txt"
        notes.write_text("other")
        with shared.locked():  # another writer commits while the session lingers on with Git's index lock
            made["other"] = shared.commit(notes, "other writer").commit
        admin = Path(git(cfg.memory, "rev-parse", "--absolute-git-dir").strip())
        (admin / "index.lock").write_text("")
        return Run(cfg.session_id, runtime_pid=4242, pids={4242: 1.0},
                   termination=Termination(confirmed=False, survivors=(4242,)), **REFUSALS[refusal])  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    if refusal == "unconfirmed":
        other = made["other"]
        with DataRepo(repo).locked():
            assert DataRepo(repo).publish([], "a later publication") == ""
    else:
        other = publish_other(repo, "after")
    assert (remote_has(remote, other), remote_has(remote, made["curator"])) == (True, False)
    assert (remote_bytes(remote, rel(entry)), (repo / rel(entry)).read_bytes()) == (before, before)
    assert bare(remote, "for-each-ref", "refs/owlbear").stdout == b""
    assert row.state == "failed"
    assert held(repo, row.reason, rel(entry)) == made["bytes"]


def test_a_publication_during_a_run_never_carries_its_commit(repo, remote) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    before = (repo / rel(entry)).read_bytes()
    made = {}

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        made["curator"] = committed(cfg.memory, "shop/memory")
        made["other"] = publish_other(repo, "during")
        return Run(cfg.session_id, termination=Termination(confirmed=True), **REFUSALS["unread"])

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    assert (remote_has(remote, made["other"]), remote_has(remote, made["curator"])) == (True, False)
    assert (remote_bytes(remote, rel(entry)), (repo / rel(entry)).read_bytes()) == (before, before)
    assert (row.state, bool(HELD.search(row.reason))) == ("failed", True)


@pytest.mark.parametrize("commits", [True, False], ids=["committed", "uncommitted"])
def test_an_exception_after_an_edit_holds_it_and_the_failed_row_names_where(repo, remote, commits, caplog) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    before = (repo / rel(entry)).read_bytes()
    made = {}

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: a first edit")
        made["curator"] = committed(cfg.memory, "shop/memory") if commits else ""
        reword(cfg.memory, entry.id, "Lesson: an edit never committed")
        made["bytes"] = (cfg.memory / f"{entry.id}.md").read_bytes()
        raise RuntimeError("x" * 400)

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    other = publish_other(repo, "after")
    assert remote_has(remote, other)
    assert not commits or not remote_has(remote, made["curator"])
    assert (remote_bytes(remote, rel(entry)), (repo / rel(entry)).read_bytes()) == (before, before)
    assert (row.state, f"RuntimeError: {'x' * 400}" in row.reason) == ("failed", True)
    assert held(repo, row.reason, rel(entry)) == made["bytes"]
    (logged,) = [r for r in caplog.records if r.name == curation.__name__]
    assert "x" * 400 in caplog.text
    assert logged.exc_info is not None


def test_a_run_that_raises_and_cannot_be_held_shows_both_failures_in_full_in_its_row_and_log(
    repo, monkeypatch, caplog
) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    real = subprocess.run
    said = f"fatal: {FULL} " * 9

    def run_(argv, *args, **kw):
        if argv[:2] == ["git", "update-ref"]:
            return subprocess.CompletedProcess(argv, 1, "", said)
        return real(argv, *args, **kw)

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        msg = f"the session broke{' and said more' * 30}"
        raise RuntimeError(msg)

    monkeypatch.setattr(curation_tree.subprocess, "run", run_)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    ran = f"RuntimeError: the session broke{' and said more' * 30}"
    assert row.state == "failed"
    assert f"{ran}; its edits are not held in a curation ref: DataRepoError: git update-ref failed: {said.strip()}" in (
        row.reason
    )
    (logged,) = [r for r in caplog.records if r.name == curation.__name__]
    assert (ran in caplog.text, said.strip() in caplog.text, logged.exc_info is not None) == (True, True, True)


def test_a_run_whose_entry_changed_meanwhile_is_refused_whole_and_the_other_change_is_published(repo, remote) -> None:
    a, b = curated(repo / "shop" / "memory", "First"), curated(repo / "shop" / "memory", "Second")
    pushed(repo, "two curated entries")
    before_a = (repo / rel(a)).read_bytes()
    made = {}

    def run(cfg) -> Run:
        reword(cfg.memory, a.id, "First: the curator's version")
        reword(cfg.memory, b.id, "Second: the curator's version")
        committed(cfg.memory, "shop/memory")
        made["a"], made["b"] = (cfg.memory / f"{a.id}.md").read_bytes(), (cfg.memory / f"{b.id}.md").read_bytes()
        shared = DataRepo(repo)
        with shared.locked():  # the Memory page saves B meanwhile
            reword(repo / "shop" / "memory", b.id, "Second: the owner's version")
            assert shared.publish(repo / rel(b), "memory shop: edit") == ""
        made["other"] = (repo / rel(b)).read_bytes()
        return Run(cfg.session_id, ending="result", payload=REPORT, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    assert row.state == "failed"
    assert row.reason.startswith(f"ended result: refused, {rel(b)} changed meanwhile; ")
    assert ((repo / rel(a)).read_bytes(), (repo / rel(b)).read_bytes()) == (before_a, made["other"])
    assert (remote_bytes(remote, rel(a)), remote_bytes(remote, rel(b))) == (before_a, made["other"])
    assert (held(repo, row.reason, rel(a)), held(repo, row.reason, rel(b))) == (made["a"], made["b"])
    assert not curation.legacy_uncertain(row)


@pytest.mark.parametrize("folder", ["shop.lock", "shop..v2"])
def test_a_folder_name_git_takes_for_no_ref_name_still_holds_a_refused_runs_edits(repo, folder) -> None:
    entry = curated(repo / folder / "memory", "Lesson")
    pushed(repo, "a curated entry")
    made = {}

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: an edit never committed")
        made["bytes"] = (cfg.memory / f"{entry.id}.md").read_bytes()
        return Run(cfg.session_id, termination=Termination(confirmed=True), **REFUSALS["unread"])

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start(folder)
    row = drained(job, folder)

    assert row.state == "failed"
    assert held(repo, row.reason, rel(entry, folder)) == made["bytes"]


def test_an_accepted_run_whose_push_fails_stands_and_a_later_publication_carries_it(repo, remote, monkeypatch) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    real, made = DataRepo._push, {}  # noqa: SLF001

    def push(self, until):
        if not made.get("failed"):
            made["failed"] = True
            raise OSError(28, "No space left on device")
        return real(self, until)

    def run(cfg) -> Run:
        made["bytes"] = (
            reword(cfg.memory, entry.id, "Lesson: the curator's version")
            and (cfg.memory / f"{entry.id}.md").read_bytes()
        )
        return Run(cfg.session_id, ending="result", payload=REPORT, termination=Termination(confirmed=True))

    monkeypatch.setattr(DataRepo, "_push", push)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    assert (row.state, row.reason) == ("done", f"written, but not published: OSError: {FULL}")
    assert git(repo, "for-each-ref", "refs/owlbear").strip() == ""
    other = publish_other(repo, "after")
    assert (remote_has(remote, other), remote_bytes(remote, rel(entry))) == (True, made["bytes"])


def test_an_accepted_run_publishes_its_edits_once_and_leaves_pending_and_receipts_local(repo, remote) -> None:
    shop, owlbear = repo / "shop" / "memory", repo / "owlbear" / "memory"
    c, d, g, o = curated(shop, "Assessed"), curated(shop, "Pruned"), curated(shop, "Shared"), curated(owlbear, "Own")
    (repo / "memory").rmdir()  # Global's folder appears with its first entry
    pushed(repo, "curated entries")
    p1, p2 = pending(shop, "To curate"), pending(shop, "Left pending")
    c = MemoryEngine(shop).get_entry(c.id)
    MemoryEngine(shop).record_assessment(c.id, "outstanding", task_id="task-1", expected_revision=c.revision)
    seed = {p1.id: (repo / rel(p1)).read_bytes(), c.id: (repo / rel(c)).read_bytes()}
    start = bare(remote, "rev-parse", "main").stdout.strip().decode()
    made = {}

    def run(cfg) -> Run:
        top = cfg.memory.parent.parent
        assert {i: (cfg.memory / f"{i}.md").read_bytes() for i in seed} == seed  # uncommitted files are seeded
        MemoryEngine(cfg.memory).edit(p1.id, {"scope_agents": ["builder"]}, expected_revision=p1.revision)
        (cfg.memory / f"{d.id}.md").unlink()
        preload.global_memory(cfg.memory).mkdir(exist_ok=True)
        git(top, "mv", rel(g), f"memory/{g.id}.md")
        reword(top / "owlbear" / "memory", o.id, "Own: the curator's version")
        reword(cfg.memory, p2.id, "Left pending: reworded")
        committed(cfg.memory, rel(p1), rel(d), rel(o, "owlbear"))  # git mv staged G
        made["p3"] = pending(shop, "Saved meanwhile")
        made.update(
            {path: (top / path).read_bytes() for path in (rel(p1), f"memory/{g.id}.md", rel(o, "owlbear"), rel(p2))}
        )
        return Run(cfg.session_id, ending="result", payload=REPORT, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    (new,) = bare(remote, "rev-list", f"{start}..main").stdout.decode().split()
    assert bare(remote, "log", "-1", "--format=%s", new).stdout.decode().strip() == (
        "chore: memory curation of shop (machine host)"
    )
    paths = bare(remote, "diff-tree", "--no-commit-id", "--name-only", "-r", new).stdout.decode().split()
    assert set(paths) == {rel(p1), rel(d), rel(g), f"memory/{g.id}.md", rel(o, "owlbear")}
    for path in (rel(p1), f"memory/{g.id}.md", rel(o, "owlbear")):
        assert remote_bytes(remote, path) == made[path] == (repo / path).read_bytes()
    assert storage.read_entry_bytes_strict(made[rel(p1)]).state == MemoryState.CURATED
    for path in (rel(d), rel(g)):
        assert (remote_bytes(remote, path), (repo / path).exists()) == (None, False)
    status = git(repo, "status", "--porcelain", "--", "shop/memory")
    assert f" M {rel(c)}" in status.splitlines()  # the receipt stays the checkout's own
    assert (repo / rel(c)).read_bytes() == seed[c.id]
    assert {f"?? {rel(p2)}", f"?? {rel(made['p3'])}"} <= set(status.splitlines())
    assert (repo / rel(p2)).read_bytes() == made[rel(p2)]
    assert row.state == "done"
    assert p2.id not in row.seen
    assert job.due("shop")


def test_an_accepted_run_never_publishes_a_deletion_the_memory_batch_deferred(repo, remote) -> None:
    """A duplicate ID whose newer copy is pending: the memory server keeps the original published until curated."""
    from owlbear_memory_mcp.git import commit_batch  # noqa: PLC0415 - the browser job syncs only this package

    shop = repo / "shop" / "memory"
    entry = curated(shop, "Lesson")
    pushed(repo, "a curated entry")
    before = (repo / rel(entry)).read_bytes()
    newer = {"title": "Newer copy", "state": MemoryState.PENDING, "updated_at": "2099-08-30T00:00:00+00:00"}
    storage.write_entry(shop / "newer-copy.md", entry.model_copy(update=newer), memory_dir=shop)
    made = {}

    def run(cfg) -> Run:
        MemoryEngine(cfg.memory).get_entries()  # the server's first read repairs the duplicate ID
        made["deferred"] = commit_batch(cfg.memory, session_type="curation").deferred_deletions
        return Run(cfg.session_id, ending="result", payload=REPORT, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    other = publish_other(repo, "after")
    assert (made["deferred"], row.state) == ((rel(entry),), "done")
    assert (remote_has(remote, other), remote_bytes(remote, rel(entry))) == (True, before)
    assert git(repo, "ls-files", "--", rel(entry)).strip() == rel(entry)  # still tracked, deleted only here

    def curate(cfg) -> Run:  # a later run curates the copy; its batch now commits the original's deletion
        (survivor,) = [e for e in MemoryEngine(cfg.memory).get_entries() if e.id == entry.id]
        MemoryEngine(cfg.memory).edit(entry.id, {"scope_agents": ["builder"]}, expected_revision=survivor.revision)
        assert commit_batch(cfg.memory, session_type="curation").commit_sha
        return Run(cfg.session_id, ending="result", payload=REPORT, termination=Termination(confirmed=True))

    later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=curate)
    later.start("shop")
    assert drained(later).state == "done"
    listed = bare(remote, "ls-tree", "-r", "--name-only", "main", "--", "shop/memory").stdout.decode().split()
    assert listed == ["shop/memory/newer-copy.md"]  # the original's deletion published with its curated copy


LOCKED = "git worktree failed: locked"


@pytest.mark.parametrize("raises", [False, True], ids=["refused", "raised"])
def test_a_finished_runs_worktree_left_listed_is_logged_and_named_in_its_row(repo, monkeypatch, caplog, raises) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    real, failing = curation_tree._git, []  # noqa: SLF001

    def git_(cwd, *args, **kw):
        if failing and args == ("worktree", "prune"):
            raise curation_tree.DataRepoError(LOCKED)
        return real(cwd, *args, **kw)

    def run(cfg) -> Run:
        failing.append(True)  # the seed's own prune ran
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        if raises:
            msg = "the session broke: " + "x" * 400  # longer than a row's reason keeps
            raise RuntimeError(msg)
        return Run(cfg.session_id, termination=Termination(confirmed=True), **REFUSALS["unread"])

    monkeypatch.setattr(curation_tree, "_git", git_)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")

    row = drained(job)
    assert (row.state, curation_tree.LISTED in row.reason, bool(HELD.search(row.reason))) == ("failed", True, True)
    assert [r.getMessage() for r in caplog.records if r.name == curation_tree.__name__] == [
        f"{repo} still lists a finished curation run's worktree: {LOCKED}"
    ]


def test_a_seed_reads_the_checkout_under_its_memory_writer_locks(repo, monkeypatch) -> None:
    curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    real, busy = curation_tree._files, []  # noqa: SLF001

    def files(root, dirs):
        if root == repo:

            def save() -> None:  # a memory save from another thread
                try:
                    with writer_lock(repo / "shop" / "memory", timeout=0.05):
                        busy.append(False)
                except MemoryBusyError:
                    busy.append(True)

            other = threading.Thread(target=save)
            other.start()
            other.join()
        return real(root, dirs)

    monkeypatch.setattr(curation_tree, "_files", files)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=lambda cfg: Run(
        cfg.session_id, termination=Termination(confirmed=True), **REFUSALS["unread"]
    ))  # fmt: skip
    job.start("shop")
    drained(job)
    assert busy == [True]


def test_the_checkout_lists_held_runs_as_its_own_and_no_finished_runs_worktree(repo) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        return Run(cfg.session_id, termination=Termination(confirmed=True), **REFUSALS["unread"])

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    drained(job)

    assert data_place.inventory(DataRepo(repo)) == ["1 refused memory curation run(s) held under refs/owlbear/curation"]
