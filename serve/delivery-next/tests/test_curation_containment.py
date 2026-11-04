"""#746: a refused curation run's edits never reach the remote, while every other writer's commits still do."""

import functools
import logging
import multiprocessing
import re
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from owlbear_memory import MemoryBusyError, MemoryCategory, MemoryEngine, MemoryState, storage, writer_lock

from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult
from owlbear_delivery_next.change_flow.worktree import git
from owlbear_delivery_next.local_system import curation_apply, data_place, preload
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, curation_resume, curation_snapshots, curation_tree
from owlbear_delivery_next.runtimes.session_result import Run

REPORT = MemoryCurationResult(summary="curated", entries=[])
CURATOR = "chore: memory curation batch (memory-mcp, memory-curator)"
HELD = re.compile(r"refs/owlbear/curation/[0-9a-f]{32}")
WHOLE = "the session broke at its start\n" + "and then in its middle\n" * 30 + "and at its end"
NOTE = "a note added on the way up"
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
    "error-with-report": {"ending": "error", "payload": REPORT, "detail": "model unavailable " * 30},
    "unconfirmed": {"ending": "result", "payload": REPORT},
}


@pytest.mark.parametrize("refusal", list(REFUSALS))
def test_a_refused_runs_commit_never_reaches_the_remote_while_another_writers_does(
    repo, remote, refusal, caplog
) -> None:
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
    (logged,) = [r.getMessage() for r in caplog.records if r.name == curation.__name__]
    assert row.reason in logged


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


@pytest.mark.parametrize("case", ["raised/exited", "raised/timed-out", "returned/exited", "returned/timed-out"])
def test_a_failed_run_that_cannot_be_held_shows_both_failures_in_full_in_its_row_and_log(
    repo, monkeypatch, caplog, case, whole_error
) -> None:
    ends, git_ = case.split("/")
    entry = curated(repo / "shop" / "memory", "Lesson")
    real, ran_git = subprocess.run, []
    printed = f"printed {whole_error}"

    def run_(argv, *args, **kw):
        if argv[:2] == ["git", "update-ref"]:
            ran_git.append(argv)
            if git_ == "exited":
                return subprocess.CompletedProcess(argv, 1, printed, whole_error)
            raise subprocess.TimeoutExpired(argv, 60, output=printed.encode(), stderr=whole_error.encode())
        return real(argv, *args, **kw)

    broke = f"the session broke{' and said more' * 30}"

    def run(cfg) -> Run:
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        if ends == "returned":  # an SDK failure comes back as the run's result
            return Run(cfg.session_id, ending="error", detail=broke, termination=Termination(confirmed=True))
        exc = RuntimeError(WHOLE)
        exc.add_note(NOTE)
        raise exc

    monkeypatch.setattr(curation_tree.subprocess, "run", run_)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    row = drained(job)

    ran = f"RuntimeError: {WHOLE}\n{NOTE}" if ends == "raised" else f"ended error: {broke}"
    argv = ran_git[0]
    git_said = (
        f"CalledProcessError: Command '{argv}' returned non-zero exit status 1."
        if git_ == "exited" else f"TimeoutExpired: Command '{argv}' timed out after 60 seconds"
    )  # fmt: skip
    failed = f"DataRepoError: git update-ref failed: {git_said}\nstderr:\n{whole_error}\nstdout:\n{printed}"
    assert row.state == "failed"
    unheld = f"its edits are not held in a curation ref: {failed}"
    if ends == "raised":
        assert row.reason == f"RuntimeError: {ran}; {unheld}"
    else:
        assert row.reason == f"RuntimeError: RuntimeError: {ran}; {unheld}; {unheld}"
    (logged,) = [r for r in caplog.records if r.name == curation.__name__]
    assert (failed in caplog.text, logged.exc_info is not None) == (True, True)


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
    MemoryEngine(shop).record_assessment(
        c.id, "outstanding", task_id="task-1", expected_revision=c.revision, stale_factor=50
    )
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
def test_a_finished_runs_worktree_left_listed_is_logged_and_named_in_its_row(
    repo, monkeypatch, caplog, raises, whole_error
) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    real, failing = curation_tree._git, []  # noqa: SLF001

    def git_(cwd, *args, **kw):
        if failing and args == ("worktree", "prune"):
            exc = curation_tree.DataRepoError(f"{LOCKED}\n{whole_error}")
            exc.add_note(NOTE)
            raise exc
        return real(cwd, *args, **kw)

    def run(cfg) -> Run:
        failing.append(True)  # the seed's own prune ran
        reword(cfg.memory, entry.id, "Lesson: the curator's version")
        if raises:
            exc = RuntimeError(WHOLE)
            exc.add_note(NOTE)
            raise exc
        return Run(cfg.session_id, termination=Termination(confirmed=True), **REFUSALS["unread"])

    monkeypatch.setattr(curation_tree, "_git", git_)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")

    row = drained(job)
    pruning = f"DataRepoError: {LOCKED}\n{whole_error}\n{NOTE}"
    listed = f"its worktree is still listed: {pruning}"
    assert (row.state, bool(HELD.search(row.reason))) == ("failed", True)
    where = f"its edits are held, never published, in {HELD.search(row.reason).group()}"
    if raises:  # each wrapper on the way up keeps the whole failure, note included
        ran = f"RuntimeError: {WHOLE}\n{NOTE}"
        assert row.reason == f"RuntimeError: {listed}; RuntimeError: {where}; {ran}"
    else:
        assert row.reason == f"ended result: the model is unknown: no tokens; {where}; {listed}"
    assert [r.getMessage() for r in caplog.records if r.name == curation_tree.__name__] == [
        f"{repo} still lists a finished curation run's worktree: {pruning}"
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


KEY = "shop:" + "0" * 32
CUT = "was cut short while its files were copied in"


def _accepting(tree: curation_tree.Tree):
    return functools.partial(tree.accept, "shop", KEY, None)


def _until_stopped(act, copied: str, watched: tuple[str, ...]) -> None:
    """A host doing *act*, stopped for good once the first of *watched* is copied in, or once an apply's record is
    written when *watched* is empty: the parent kills it."""

    def stop(name: str) -> None:
        Path(copied).write_text(name)
        time.sleep(120)

    real, record = curation_tree.atomic_write, curation_apply.write

    def write(path, *args, **kw) -> None:
        real(path, *args, **kw)
        if Path(path).name in watched:
            stop(Path(path).name)

    def kept(*args) -> None:
        record(*args)
        if not watched:
            stop("")

    curation_tree.atomic_write, curation_apply.write = write, kept
    act()


def _stop(act, at: Path, watched: tuple[str, ...] = ()) -> str:
    """Do *act* in a child the parent kills where `_until_stopped` stops; the file it copied last."""
    copied = at / "copied"
    copied.unlink(missing_ok=True)
    child = multiprocessing.get_context("spawn").Process(target=_until_stopped, args=(act, str(copied), watched))
    child.start()
    end = time.monotonic() + 30
    while not copied.exists():
        assert child.is_alive(), "the host stopped before it copied a file in"
        assert time.monotonic() < end, "the host copied nothing in"
        time.sleep(0.05)
    child.kill()
    child.join()
    return copied.read_text()


def _run(repo: Path, at: Path, curate) -> curation_tree.Tree:
    """A run seeded from the checkout, whose curator calls *curate* with its worktree and commits."""
    tree = curation_tree.seed(DataRepo(repo), at / "run", ["owlbear", "shop"])
    curate(tree.root)
    git(tree.root, "add", "-A")
    git(tree.root, "commit", "-qm", CURATOR)
    return tree


def stopped(repo: Path, remote: Path, at: Path) -> SimpleNamespace:
    """An accepted run whose apply a stop cut short after the first of its two curated files was copied in.

    Its run rewords A and adds B, curated in shop, and removes owlbear's curated C with its own commit; it rewords
    pending P and deletes owlbear's D without a commit, as the memory server defers a deletion.
    """
    shop, owlbear = repo / "shop" / "memory", repo / "owlbear" / "memory"
    a, c, d = curated(shop, "Reworded"), curated(owlbear, "Removed"), curated(owlbear, "Deferred")
    pushed(repo, "curated entries")
    p = pending(shop, "Pending")
    seed = {rel(e, f): (repo / rel(e, f)).read_bytes() for e, f in ((a, "shop"), (c, "owlbear"), (d, "owlbear"))}
    tree = curation_tree.seed(DataRepo(repo), at / "run", ["owlbear", "shop"])
    reword(tree.root / "shop" / "memory", a.id, "Reworded: the curator's version")
    b = curated(tree.root / "shop" / "memory", "Added")
    reword(tree.root / "shop" / "memory", p.id, "Pending: reworded")
    (tree.root / rel(d, "owlbear")).unlink()
    git(tree.root, "rm", "-q", "--", rel(c, "owlbear"))
    git(tree.root, "commit", "-qm", CURATOR)
    target = {rel(e): (tree.root / rel(e)).read_bytes() for e in (a, b, p)}
    first = f"shop/memory/{_stop(_accepting(tree), at, (f'{a.id}.md', f'{b.id}.md'))}"
    second = ({rel(a), rel(b)} - {first}).pop()
    assert curation_apply.read(DataRepo(repo)) is not None
    assert ((repo / first).read_bytes(), curation_tree._read(repo / second)) == (target[first], seed.get(second))  # noqa: SLF001
    assert [e for e in (c, d) if (repo / rel(e, "owlbear")).exists()] == []  # removed first, as the apply does
    start = remote_main(remote)
    return SimpleNamespace(first=first, second=second, c=c, d=d, p=p, seed=seed, target=target, start=start)


def idle(repo: Path) -> curation.Curation:
    return curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=lambda _cfg: pytest.fail("ran"))


def remote_main(remote: Path) -> str:
    return bare(remote, "rev-parse", "main").stdout.decode().strip()


def test_a_stop_while_an_accepted_runs_files_are_copied_in_publishes_none_until_the_restart_finishes_them(
    repo, remote, tmp_path, caplog
) -> None:
    """#875: a hand chat's batch commits a copied file, yet no push of the checkout runs until the set is whole."""
    from owlbear_memory_mcp.git import commit_batch, cut_short  # noqa: PLC0415 - the browser job syncs only this package

    left = stopped(repo, remote, tmp_path)
    shared = DataRepo(repo)
    sha = commit_batch(repo / "shop" / "memory", session_type="curation").commit_sha
    assert git(repo, "show", "--name-only", "--format=", sha).split() == [left.first]

    sent = shared.git("push", "origin", f"{sha}:refs/heads/main")
    with shared.locked():
        notice = shared.publish([], "a later writer")
    assert (sent.returncode, CUT in sent.stderr, CUT in notice, CUT in cut_short(repo)) == (1, True, True, True)
    assert remote_main(remote) == left.start

    job = idle(repo)
    with job.lock:
        runs = job.load()
        runs.folders["shop"] = curation.FolderRun(state="failed", reason=curation.INTERRUPTED)
        job._write(runs)  # noqa: SLF001 - the row a restart leaves
    with caplog.at_level(logging.WARNING):
        resumed = curation_resume.recover(job)

    assert (resumed.folder, resumed.done) == ("shop", True)
    for path, did in (
        (left.first, "as the run left it"), (left.second, "written now"),
        (rel(left.c, "owlbear"), "as the run left it"), (rel(left.d, "owlbear"), "as the run left it"),
    ):  # fmt: skip
        assert f"{path}: {did}" in resumed.said
    assert resumed.said.endswith("; published")
    assert remote_has(remote, sha)
    for path in (left.first, left.second):
        assert remote_bytes(remote, path) == left.target[path] == (repo / path).read_bytes()
    removed = rel(left.c, "owlbear")
    assert (remote_bytes(remote, removed), (repo / removed).exists()) == (None, False)
    deferred = rel(left.d, "owlbear")  # its deletion stays uncommitted, as the run's commits did not make it
    assert (remote_bytes(remote, deferred), (repo / deferred).exists()) == (left.seed[deferred], False)
    assert (remote_bytes(remote, rel(left.p)), (repo / rel(left.p)).read_bytes()) == (None, left.target[rel(left.p)])
    assert git(repo, "status", "--porcelain").splitlines() == [f" D {deferred}", f"?? {rel(left.p)}"]
    assert curation_apply.read(shared) is None
    assert "memory curation of shop: finished the apply a stop cut short: " in caplog.text
    assert job.load().folders["shop"].reason == (
        f"{curation.INTERRUPTED}; its accepted edits were finished afterwards: {resumed.said}"
    )
    assert curation_tree.resume(shared) is None


def test_a_file_changed_after_the_stop_is_kept_and_published_with_the_rest(repo, remote, tmp_path) -> None:
    shop = repo / "shop" / "memory"
    x, y = curated(shop, "Saved later"), curated(shop, "Untouched")
    pushed(repo, "curated entries")

    def curate(root: Path) -> None:
        reword(root / "shop" / "memory", x.id, "Saved later: the curator's version")
        reword(root / "shop" / "memory", y.id, "Untouched: the curator's version")

    tree = _run(repo, tmp_path, curate)
    target = (tree.root / rel(y)).read_bytes()
    _stop(_accepting(tree), tmp_path)
    changed = reword(shop, x.id, "Saved later: a hand chat's version")

    resumed = curation_tree.resume(DataRepo(repo))

    assert resumed.done
    assert f"{rel(x)}: changed after the stop; that version is kept" in resumed.said
    assert f"{rel(y)}: written now" in resumed.said
    assert remote_bytes(remote, rel(x)) == (repo / rel(changed)).read_bytes()
    assert remote_bytes(remote, rel(y)) == target


def _made_global(entry):
    return lambda root: git(root, "mv", rel(entry), f"memory/{entry.id}.md")


@pytest.mark.parametrize("during", ["accept", "recovery"])
def test_a_stop_while_an_entry_is_made_global_never_leaves_it_in_both_folders(repo, remote, tmp_path, during) -> None:
    g = curated(repo / "shop" / "memory", "Shared")
    pushed(repo, "a curated entry")
    moved = f"memory/{g.id}.md"
    accepting = _accepting(_run(repo, tmp_path, _made_global(g)))

    if during == "accept":
        _stop(accepting, tmp_path, (f"{g.id}.md",))
    else:
        _stop(accepting, tmp_path)
        _stop(functools.partial(curation_tree.resume, DataRepo(repo)), tmp_path, (f"{g.id}.md",))

    assert ((repo / rel(g)).exists(), (repo / moved).exists()) == (False, True)
    assert curation_tree.resume(DataRepo(repo)).done
    assert (remote_bytes(remote, rel(g)), remote_bytes(remote, moved)) == (None, (repo / moved).read_bytes())


def test_an_entry_changed_after_a_stop_before_its_move_stays_where_it_was(repo, remote, tmp_path) -> None:
    """A hand chat's challenge of an entry a stopped run made Global keeps it in its project; no Global copy remains."""
    shop = repo / "shop" / "memory"
    g = curated(shop, "Shared")
    pushed(repo, "a curated entry")
    _stop(_accepting(_run(repo, tmp_path, _made_global(g))), tmp_path)
    challenged = MemoryEngine(shop).get_entry(g.id)
    MemoryEngine(shop).record_factually_wrong(g.id, task_id="task-1", expected_revision=challenged.revision)

    resumed = curation_tree.resume(DataRepo(repo))

    moved = f"memory/{g.id}.md"
    assert resumed.done
    assert f"{moved}: left as it was, as {rel(g)} of its entry changed after the stop" in resumed.said
    assert (remote_bytes(remote, rel(g)), remote_bytes(remote, moved)) == ((repo / rel(g)).read_bytes(), None)
    assert MemoryEngine(shop).get_entry(g.id).state == MemoryState.CONTESTED
    assert not (repo / moved).exists()


@pytest.mark.parametrize(
    "refusal",
    [
        "this automatic trigger is off in the machine settings; it waits until it is turned on",
        f"{curation_snapshots.UNSET[0]}agents.curator.model{curation_snapshots.UNSET[1]}",
    ],
)
def test_a_refusal_whose_folders_apply_stays_cut_short_is_still_one_with_one_note(repo, refusal) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    shared = DataRepo(repo)
    seed = (repo / rel(entry)).read_bytes()
    step = curation_apply.Step(curation_apply.digest(seed), "the run's version", removed=False)
    curation_apply.write(shared, curation_apply.Apply("shop", {rel(entry): step}))
    (Path(git(repo, "rev-parse", "--absolute-git-dir").strip()) / "index.lock").write_text("")  # a lingering Git's
    job, at = idle(repo), datetime.now(UTC)
    with job.lock:
        runs = job.load()
        runs.folders["shop"] = curation.FolderRun(state="failed", started_at=at, ended_at=at, reason=refusal)
        job._write(runs)  # noqa: SLF001 - a refusal main wrote before any session

    curation_resume.recover(job)
    resumed = curation_resume.recover(job)

    row = job.load().folders["shop"]
    assert (curation_snapshots.refused(row), curation.legacy_uncertain(row)) == (True, False)
    assert row.reason == f"{refusal}; its accepted edits could not be finished yet: {resumed.said}"


def test_an_apply_that_cannot_be_finished_keeps_its_hold_and_refuses_the_next_run(
    repo, remote, tmp_path, caplog
) -> None:
    e = curated(repo / "owlbear" / "memory", "Elsewhere")
    left = stopped(repo, remote, tmp_path)
    shared = DataRepo(repo)
    before = (repo / rel(e, "owlbear")).read_bytes()
    record = curation_apply.where(shared).read_bytes()
    lock = Path(git(repo, "rev-parse", "--absolute-git-dir").strip()) / "index.lock"
    lock.write_text("")  # a lingering Git process's

    job = idle(repo)
    with caplog.at_level(logging.ERROR):
        resumed = curation_resume.recover(job)
    with shared.locked():
        notice = shared.publish([], "a later writer")

    assert (resumed.done, "not committed: " in resumed.said, CUT in resumed.said, CUT in notice) == (
        False, True, True, True
    )  # fmt: skip
    assert "memory curation of shop: could not finish the apply a stop cut short: " in caplog.text
    assert job.load().folders["shop"].reason == f"its accepted edits could not be finished yet: {resumed.said}"
    assert (curation_apply.where(shared).read_bytes(), remote_main(remote)) == (record, left.start)

    made = {}

    def run(cfg) -> Run:
        made["bytes"] = (
            reword(cfg.memory, e.id, "Elsewhere: the curator's version") and (cfg.memory / f"{e.id}.md").read_bytes()
        )
        return Run(cfg.session_id, ending="result", payload=REPORT, termination=Termination(confirmed=True))

    later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    later.start("owlbear")
    row = drained(later, "owlbear")

    assert (row.state, row.reason.startswith("ended result: refused, "), CUT in row.reason) == ("failed", True, True)
    assert held(repo, row.reason, rel(e, "owlbear")) == made["bytes"]
    assert ((repo / rel(e, "owlbear")).read_bytes(), remote_bytes(remote, rel(e, "owlbear"))) == (before, before)
    assert curation_apply.where(shared).read_bytes() == record

    lock.unlink()
    assert curation_tree.resume(shared).done
    assert remote_bytes(remote, left.second) == left.target[left.second]


def test_a_restart_that_cannot_open_the_shared_repository_logs_why_and_goes_on(caplog) -> None:
    def shared() -> DataRepo:
        msg = "the git folder of /data cannot be found: not a git repository"
        raise DataRepoError(msg)

    job = curation.Curation(Slots(lambda: 1), shared=shared, run=lambda _cfg: pytest.fail("ran"))
    resumed = curation_resume.recover(job)

    said = "DataRepoError: the git folder of /data cannot be found: not a git repository"
    assert resumed == curation_tree.Resumed("", done=False, said=said)
    assert "the apply a stop cut short could not be checked: " + said in caplog.text


def _hold(memory: str, acquired, release) -> None:
    with writer_lock(memory, timeout=5):
        acquired.set()
        release.wait(timeout=30)


def test_an_apply_whose_folder_another_process_holds_stays_cut_short(repo, monkeypatch) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    shared, seed = DataRepo(repo), (repo / rel(entry)).read_bytes()
    step = curation_apply.Step(curation_apply.digest(seed), "the run's version", removed=False)
    curation_apply.write(shared, curation_apply.Apply("shop", {rel(entry): step}))
    monkeypatch.setattr(curation_tree, "writer_lock", functools.partial(writer_lock, timeout=0.1))
    spawn = multiprocessing.get_context("spawn")
    acquired, release = spawn.Event(), spawn.Event()
    holder = spawn.Process(target=_hold, args=(str(repo / "shop" / "memory"), acquired, release))
    holder.start()
    try:
        assert acquired.wait(timeout=30)
        resumed = curation_tree.resume(shared)
    finally:
        release.set()
        holder.join()

    assert (resumed.done, resumed.said.startswith("MemoryBusyError: "), CUT in resumed.said) == (False, True, True)
    assert ((repo / rel(entry)).read_bytes(), curation_apply.read(shared) is not None) == (seed, True)


def test_a_curation_run_is_seeded_with_the_global_settings_whole_memory_values_included(repo, tmp_path) -> None:
    """The curator's memory server reads the settings beside its worktree: one copy of Global's file, byte for byte."""
    text = '{"format": 21, "curator_threshold": 90, "memory": {"stale_factor": 50, "purge_days": 14}}'
    (repo / "config.json").write_text(text)

    tree = curation_tree.seed(DataRepo(repo), tmp_path / "run", ["shop"])

    assert (tree.root / "config.json").read_text() == text


def test_an_apply_finished_first_leads_the_refusal_of_a_run_whose_file_changed_meanwhile(repo, tmp_path) -> None:
    entry = curated(repo / "shop" / "memory", "Lesson")
    pushed(repo, "a curated entry")
    tree = curation_tree.seed(DataRepo(repo), tmp_path / "run", ["shop"])
    reword(tree.root / "shop" / "memory", entry.id, "Lesson: the curator's version")
    reword(repo / "shop" / "memory", entry.id, "Lesson: saved meanwhile")

    refusal, notice = tree.accept("shop", KEY, curation_tree.Resumed("shop", done=True, said="x: written now"))

    assert refusal.startswith("first finished the apply a stop cut short of shop: x: written now; refused, ")
    assert (f"{rel(entry)} changed meanwhile" in refusal, notice) == (True, "")
