"""A step's own assessment receipts never stop Delivery's refresh before publish (#753).

The memory server is bound to a real clone of a shared repository as Delivery binds it, and the real
`decision_store.refresh` runs on that clone: a mocked refresh would not see the uncommitted receipt.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_store
from owlbear_memory_mcp import tools
from owlbear_memory_mcp.server import AppContext

_TS = "2026-10-01T10:00:00+00:00"
_TASK = "retro-proof-build"
_SUBJECT = f"chore: memory assessments ({_TASK}, memory-mcp)"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def entry(entry_id: str, state: MemoryState, title: str = "Pin the runtime") -> MemoryEntry:
    return MemoryEntry(
        id=entry_id, title=title, content=f"{title}: what to know.", categories=["process"], confidence=0.8,
        state=state, scope_agents=["builder"], source_agent="builder", created_at=_TS, updated_at=_TS,
        approved_at=_TS if state is MemoryState.APPROVED else None,
    )  # fmt: skip


def seed(folder: Path, name: str, item: MemoryEntry) -> Path:
    path = folder / name
    storage.write_entry(path, item, memory_dir=folder)
    return path


@pytest.fixture
def shared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A bare remote and this machine's clone of it, holding a project's memory folder and Global memory."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR"):
        monkeypatch.delenv(name, raising=False)  # inherited from a hook, Git would work on another repository
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    base = tmp_path.resolve()
    remote, data = base / "remote.git", base / "data"
    git(base, "init", "-q", "--bare", "-b", "main", str(remote))
    git(base, "clone", "-q", str(remote), str(data))
    git(data, "config", "user.name", "t")
    git(data, "config", "user.email", "t@t")
    (data / "memory").mkdir()
    (data / "memory" / ".gitkeep").write_text("")
    folder = data / "proj" / "memory"
    folder.mkdir(parents=True)
    return SimpleNamespace(base=base, remote=remote, data=data, folder=folder)


def publish(shared: SimpleNamespace) -> None:
    git(shared.data, "add", "-A")
    git(shared.data, "commit", "-qm", "seed")
    git(shared.data, "push", "-q", "-u", "origin", "main")


def elsewhere(shared: SimpleNamespace) -> str:
    """Another machine pushes a decision; the remote's new commit."""
    other = shared.base / "other"
    git(shared.base, "clone", "-q", str(shared.remote), str(other))
    git(other, "config", "user.name", "o")
    git(other, "config", "user.email", "o@o")
    (other / "proj" / "decisions").mkdir(parents=True)
    (other / "proj" / "decisions" / "D-01OTHER.md").write_text("---\nid: D-01OTHER\n---\nAnother machine's.\n")
    git(other, "add", "-A")
    git(other, "commit", "-qm", "decision")
    git(other, "push", "-q")
    return git(other, "rev-parse", "HEAD")


async def assess(shared: SimpleNamespace, *items: tuple[str, str]) -> list[dict[str, object]]:
    # The context the memory server builds from Delivery's environment (preload.memory).
    engine = MemoryEngine(shared.folder)
    context = AppContext(engine=engine, memory_dir=shared.folder, global_dir=shared.data / "memory")
    batch = [{"entry_id": i, "revision": engine.get_entry(i).revision, "bucket": b} for i, b in items]
    ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))
    return (await tools.assess_memories(ctx, assessments=batch, task_id=_TASK))["results"]


@pytest.mark.asyncio
async def test_a_steps_own_receipt_no_longer_stops_the_refresh_before_publish(shared: SimpleNamespace) -> None:
    """Change retro-proof stopped before publish on the didnt_use receipt its own build step wrote."""
    kept = "550e8400-e29b-41d4-a716-446655447530"
    path = seed(shared.folder, "kept-name.md", entry(kept, MemoryState.APPROVED))
    publish(shared)
    pushed = elsewhere(shared)

    [result] = await assess(shared, (kept, "didnt_use"))

    assert (result["success"], result["already_applied"]) == (True, False)
    assert decision_store.refresh(DataRepo(root=shared.data)) == ""
    assert git(shared.data, "merge-base", "--is-ancestor", pushed, "HEAD") == ""
    assert git(shared.data, "status", "--porcelain", "--untracked-files=no") == ""
    assert git(shared.data, "show", "--name-only", "--format=%s", "HEAD").splitlines() == [
        _SUBJECT, "", "proj/memory/kept-name.md"
    ]  # fmt: skip
    assert git(shared.data, "ls-remote", "origin", "main").split()[0] == pushed  # nothing pushed
    assert MemoryEngine(shared.folder).get_entry(kept).didnt_use_count == 1

    head, before = git(shared.data, "rev-parse", "HEAD"), path.read_bytes()
    [again] = await assess(shared, (kept, "didnt_use"))

    assert (again["success"], again["already_applied"]) == (True, True)
    assert (git(shared.data, "rev-parse", "HEAD"), path.read_bytes()) == (head, before)
    assert git(shared.data, "status", "--porcelain", "--untracked-files=no") == ""


@pytest.mark.asyncio
async def test_only_files_committed_before_the_batch_are_committed_and_other_dirt_still_stops_the_refresh(
    shared: SimpleNamespace,
) -> None:
    """Another writer's staged change and pending memory stay out of the receipt commit and still stop publish."""
    clean, dirty, pending = (f"550e8400-e29b-41d4-a716-44665544753{n}" for n in (1, 2, 3))
    seed(shared.folder, "a.md", entry(clean, MemoryState.APPROVED))
    seed(shared.folder, "b.md", entry(dirty, MemoryState.APPROVED))
    publish(shared)
    seed(shared.folder, "b.md", entry(dirty, MemoryState.APPROVED, title="Pin the runtime, edited elsewhere"))
    git(shared.data, "add", "proj/memory/b.md")
    staged = git(shared.data, "rev-parse", ":proj/memory/b.md")
    committed_b = git(shared.data, "rev-parse", "HEAD:proj/memory/b.md")
    seed(shared.folder, "c.md", entry(pending, MemoryState.PENDING))
    (shared.folder / "notes.txt").write_text("scratch\n")

    results = await assess(shared, (clean, "outstanding"), (dirty, "outstanding"), (pending, "outstanding"))

    assert [r["success"] for r in results] == [True, True, False]
    assert git(shared.data, "show", "--name-only", "--format=%s", "HEAD").splitlines() == [
        _SUBJECT, "", "proj/memory/a.md"
    ]  # fmt: skip
    assert git(shared.data, "rev-parse", ":proj/memory/b.md") == staged
    assert git(shared.data, "rev-parse", "HEAD:proj/memory/b.md") == committed_b
    tracked = git(shared.data, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    assert "proj/memory/c.md" not in tracked
    assert "proj/memory/notes.txt" not in tracked
    refused = decision_store.refresh(DataRepo(root=shared.data))
    assert refused.startswith("not refreshed: 1 uncommitted file(s) in ")


@pytest.mark.asyncio
async def test_a_failed_commit_is_reported_and_leaves_the_receipt_uncommitted(shared: SimpleNamespace) -> None:
    """A commit Git refuses is shown with Git's own output; the receipt stays recorded, nothing is staged."""
    kept = "550e8400-e29b-41d4-a716-446655447534"
    seed(shared.folder, "a.md", entry(kept, MemoryState.APPROVED))
    publish(shared)
    hook = shared.data / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook refused' >&2\nexit 1\n")
    hook.chmod(0o755)
    head = git(shared.data, "rev-parse", "HEAD")

    with pytest.raises(ToolError) as raised:
        await assess(shared, (kept, "outstanding"))

    assert all(part in str(raised.value) for part in ("a.md", "not committed", "hook refused"))
    assert git(shared.data, "rev-parse", "HEAD") == head
    assert git(shared.data, "diff", "--cached", "--name-only") == ""
    assert MemoryEngine(shared.folder).get_entry(kept).outstanding_count == 1


@pytest.mark.asyncio
async def test_receipts_written_before_a_failing_write_are_still_committed(
    shared: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later entry's write failure still surfaces, and the receipts already written do not stop the refresh."""
    first, second = (f"550e8400-e29b-41d4-a716-44665544753{n}" for n in (5, 6))
    seed(shared.folder, "a.md", entry(first, MemoryState.APPROVED))
    seed(shared.folder, "b.md", entry(second, MemoryState.APPROVED))
    publish(shared)
    record = MemoryEngine.record_assessment

    def full_disk(engine: MemoryEngine, entry_id: str, *args: object, **kwargs: object) -> object:
        if entry_id == second:
            raise OSError(28, "No space left on device")
        return record(engine, entry_id, *args, **kwargs)

    monkeypatch.setattr(MemoryEngine, "record_assessment", full_disk)

    with pytest.raises(OSError, match="No space left"):
        await assess(shared, (first, "outstanding"), (second, "outstanding"))

    assert git(shared.data, "show", "--name-only", "--format=%s", "HEAD").splitlines() == [
        _SUBJECT, "", "proj/memory/a.md"
    ]  # fmt: skip
    assert decision_store.refresh(DataRepo(root=shared.data)) == ""


@pytest.mark.asyncio
async def test_a_hook_that_sweeps_other_files_into_the_receipt_commit_is_reported(shared: SimpleNamespace) -> None:
    """A pre-commit hook running `git add -A` cannot pass pending memory off as a receipt commit."""
    kept, pending = (f"550e8400-e29b-41d4-a716-44665544753{n}" for n in (7, 8))
    seed(shared.folder, "a.md", entry(kept, MemoryState.APPROVED))
    publish(shared)
    seed(shared.folder, "c.md", entry(pending, MemoryState.PENDING))
    (shared.folder / "notes.txt").write_text("scratch\n")
    hook = shared.data / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexec git add -A\n")
    hook.chmod(0o755)

    with pytest.raises(ToolError) as raised:
        await assess(shared, (kept, "outstanding"))

    assert all(part in str(raised.value) for part in ("proj/memory/c.md", "proj/memory/notes.txt"))
    assert "a.md" not in str(raised.value)  # the receipt itself is as written
