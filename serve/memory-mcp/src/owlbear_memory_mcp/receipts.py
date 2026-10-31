"""Assessment receipts committed in the shared repository, so a step never stops on a receipt it wrote (#753)."""

from __future__ import annotations

import contextlib
import subprocess
from typing import TYPE_CHECKING

from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import storage, writer_lock
from owlbear_memory.errors import MemoryBusyError

from owlbear_memory_mcp.git import _git, commit_move, format_git_failure, repo_locked

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator
    from pathlib import Path


@contextlib.contextmanager
def committed(root: Path | None, memory_dir: Path | None, entry_ids: Collection[str], task_id: str) -> Iterator[None]:
    """Around one assess_memories batch: commit the receipts it writes to entry files committed before it.

    Unbound (*root* and *memory_dir* None) nothing else happens. Bound to the shared repository, the batch runs under
    its lock and then the memory folder's writer lock, as make_global does; a file changed or untracked before the
    batch is another writer's and is never committed. Nothing is pushed: Delivery's next publication pushes it.
    """
    if root is None or memory_dir is None:
        yield
        return
    with contextlib.ExitStack() as held:
        try:
            held.enter_context(repo_locked(root))
            held.enter_context(writer_lock(memory_dir))
            clean = [path for path in _batch_files(memory_dir, set(entry_ids)) if not _changed(path)]
        except (MemoryBusyError, TimeoutError) as exc:
            raise ToolError(str(exc)) from exc
        except (subprocess.CalledProcessError, OSError) as exc:
            msg = f"nothing was assessed: the shared repository {root} could not be read: {_detail(exc)}"
            raise ToolError(msg) from exc
        yield
        written: list[Path] = []
        try:
            written = [path for path in clean if path.exists() and _changed(path)]
            if written:
                commit_move(written, f"chore: memory assessments ({task_id}, memory-mcp)")
        except (subprocess.CalledProcessError, OSError) as exc:
            names = ", ".join(path.name for path in written or clean)
            msg = (
                f"the receipts were recorded but not committed: {names} in {memory_dir} stay uncommitted, "
                f"so Delivery's refresh stops on them: {_detail(exc)}"
            )
            raise ToolError(msg) from exc


def _batch_files(memory_dir: Path, ids: set[str]) -> list[Path]:
    """The batch's entry files, found by the id they hold: a file's name need not be its id."""
    return [path for path in sorted(memory_dir.glob("*.md")) if getattr(storage.read_entry(path), "id", None) in ids]


def _changed(path: Path) -> bool:
    """Whether Git shows *path* as anything but committed and unchanged: modified, staged, untracked or ignored."""
    return bool(_git(path.parent, "status", "--porcelain", "--ignored", "--", path.name))


def _detail(exc: BaseException) -> str:
    return format_git_failure(exc) if isinstance(exc, subprocess.CalledProcessError) else str(exc)
