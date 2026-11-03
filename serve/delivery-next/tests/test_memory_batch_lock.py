"""#877: a hand chat's memory batch waits out a publication's rebase; its commit stays on the branch and is pushed."""

import subprocess
import threading
import time
from pathlib import Path

from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.change_flow.worktree import git
from owlbear_delivery_next.local_system.data_repo import DataRepo

# reference-transaction: once, when a rebase moves the branch, wait until the test releases it
HOOK = """#!/bin/sh
[ "$1" = committed ] || exit 0
case "$(cat)" in *" refs/heads/main"*) ;; *) exit 0 ;; esac
[ -d "{admin}/rebase-merge" ] && [ ! -e "{paused}" ] || exit 0
: > "{paused}"
i=0
while [ ! -e "{release}" ] && [ $i -lt 600 ]; do sleep 0.05; i=$((i + 1)); done
exit 0
"""


def curated(folder: Path, title: str) -> Path:
    engine = MemoryEngine(folder)
    entry = engine.save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip
    engine.edit(entry.id, {"scope_agents": ["builder"]}, expected_revision=entry.revision)
    return folder / f"{entry.id}.md"


def bare(remote: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # CI sets safe.bareRepository=explicit: the bare remote is always named
    return subprocess.run(["git", f"--git-dir={remote}", *args], capture_output=True, check=False)  # noqa: S603, S607


def waited(path: Path, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() > end:
            return False
        time.sleep(0.02)
    return True


def behind(root: Path, remote: Path, tmp_path: Path) -> None:
    """Another machine pushed and the checkout has an unpushed save: a publication's push is rejected and it rebases."""
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "shop" / "other.txt").write_text("from another machine")
    git(other, "add", "-A")
    git(other, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "other machine")
    git(other, "push", "-q")
    (root / "shop" / "earlier.txt").write_text("earlier")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "earlier unpushed save")


def pausing(root: Path, tmp_path: Path) -> tuple[Path, Path]:
    """Install the hook in the checkout; the file it makes once paused, and the one that releases it."""
    admin = Path(git(root, "rev-parse", "--absolute-git-dir").strip())
    paused, release, hooks = tmp_path / "paused", tmp_path / "release", tmp_path
    (hooks / "reference-transaction").write_text(HOOK.format(admin=admin, paused=paused, release=release))
    (hooks / "reference-transaction").chmod(0o755)
    git(root, "config", "core.hooksPath", str(hooks))
    return paused, release


def test_a_memory_batch_during_a_publications_rebase_waits_and_its_commit_reaches_the_remote(shared_repo, tmp_path):
    from owlbear_memory_mcp.git import commit_batch  # noqa: PLC0415 - the browser job syncs only this package

    root, remote = shared_repo
    shared, memory = DataRepo(root), root / "shop" / "memory"
    memory.mkdir(parents=True)
    curated(memory, "Old lesson")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    git(root, "push", "-q")
    behind(root, remote, tmp_path)
    paused, release = pausing(root, tmp_path)
    entry = curated(memory, "Hand chat lesson")  # the hand chat's batch, not committed yet
    note = root / "shop" / "note.txt"
    note.write_text("holder")
    holder: dict[str, object] = {}
    batch: dict[str, object] = {}

    def hold() -> None:
        try:
            with shared.locked():
                holder["said"] = shared.publish([note], "holder: a save")
        except Exception as exc:  # noqa: BLE001 - reported by the assertions below
            holder["error"] = exc

    def commit() -> None:
        try:
            batch["sha"] = commit_batch(memory, session_type="review").commit_sha
        except Exception as exc:  # noqa: BLE001 - reported by the assertions below
            batch["error"] = exc

    h = threading.Thread(target=hold)
    h.start()
    assert waited(paused, 30), holder
    b = threading.Thread(target=commit)
    b.start()
    b.join(2)  # before the repository lock, the batch commits inside the pause; with it, it waits
    release.touch()
    h.join(35)
    b.join(35)

    assert holder == {"said": ""}
    assert "error" not in batch, batch
    sha = batch["sha"]
    assert subprocess.run(["git", "merge-base", "--is-ancestor", sha, "main"], cwd=root, check=False).returncode == 0  # noqa: S603, S607
    assert git(root, "status", "--porcelain", "--", "shop/memory") == ""
    with shared.locked():
        assert shared.publish([], "again") == ""
    assert bare(remote, "show", f"main:shop/memory/{entry.name}").stdout == entry.read_bytes()
