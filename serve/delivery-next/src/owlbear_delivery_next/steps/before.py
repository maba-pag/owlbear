"""TD-24 "before" screenshots: the brief's states rendered at the merge-base with the visual check's own recipe.

Once per Change, after the preparing Builder returned the visual check's recipe and before the host launches it,
a runner checks out the merge-base in a temporary detached worktree, runs the profile's install commands for the
Change's scope, launches the same recipe there, captures every state and disposes of all it started. The card
shows these beside the "after" screenshots. A failure is a note on the card (B25); it never gates.
"""

from __future__ import annotations

import contextlib
import os
import shlex
import shutil
import signal
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.models import VISUAL, Environment, StepKind, VisualResult
from owlbear_delivery_next.steps import check, visual, worktree

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.profile_record import Profile

INSTALL_WITHIN = 600.0  # seconds per install command


def due(c: Change) -> bool:
    """The visual check's recipe is known and not yet launched, and this Change has no "before" capture yet."""
    e = c.env
    at_check = (c.step.kind, c.step.task) == (StepKind.CHECK, VISUAL)
    return bool(e and e.check == VISUAL and e.launched_at is None and c.before is None and c.brief.visual) and at_check


def _journal(log: Callable[[dict[str, Any]], None], pids: dict[int, float | None]) -> None:
    """Persist started PIDs first, so the host finds them if this runner dies."""
    log({"event": "pids", "at": datetime.now(UTC).isoformat(), "pids": {str(p): t for p, t in pids.items()}})


def _run(argv: list[str], cwd: Path, log: Callable[[dict[str, Any]], None]) -> str:
    """Run one install command in its own group; a note if it failed, empty on success."""
    try:
        proc = subprocess.Popen(  # noqa: S603 - argument vector of an install command the owner made known
            argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True,
        )  # fmt: skip
    except OSError as exc:
        return f"`{shlex.join(argv)}` did not start: {exc}"
    created = check.created(proc.pid)
    try:
        _journal(log, {proc.pid: created})
        out, _ = proc.communicate(timeout=INSTALL_WITHIN)
    except subprocess.TimeoutExpired:
        return f"`{shlex.join(argv)}` took over {INSTALL_WITHIN:.0f} s"
    finally:  # timed out, interrupted or done: nothing of its group outlives the temporary worktree
        if check.members(proc.pid, created):  # not once its id names a newer group
            with contextlib.suppress(OSError):
                os.killpg(proc.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.communicate(timeout=5)  # an escaped child may hold the pipe open
    if proc.returncode:
        last = next((x for x in reversed(out.decode(errors="replace").splitlines()) if x.strip()), "")
        return f"`{shlex.join(argv)}` failed: {last.strip()[:200]}"
    return ""


def _remove(repo: Path, tmp: Path) -> None:
    for step in (
        lambda: worktree.git(repo, "worktree", "remove", "--force", "--force", str(tmp)),
        lambda: shutil.rmtree(tmp, ignore_errors=True),
        lambda: worktree.git(repo, "worktree", "prune"),
    ):
        with contextlib.suppress(subprocess.SubprocessError, OSError):
            step()


def _serve(  # noqa: PLR0913 - the widths come from the settings
    c: Change, root: Path, out: Path, log: Callable[[dict[str, Any]], None], notes: list[str], *, widths: Sequence[int]
) -> list[visual.Shot]:
    """Launch the Change's recipe in *root*, capture its states once it answers, dispose of it whatever happens."""
    r = c.env
    if r is None:
        return []
    e = Environment(check=VISUAL, command=r.command, directory=r.directory, ready_url=r.ready_url)
    if check.answers(e.ready_url):
        notes.append(f"something else already answers at {e.ready_url}")
        return []
    proc = check.start(e, root, out / "preview.log")
    if proc is None:
        notes.append(f"`{e.command}` did not start at the merge-base")
        return []
    e = e.model_copy(update={"pgid": proc.pid, "pids": {proc.pid: check.created(proc.pid)}})
    try:
        _journal(log, e.pids)
        if (pids := check.ready(e, proc)) is None:
            notes.append(f"the recipe did not answer at {e.ready_url} for the merge-base")
            return []
        e = e.model_copy(update={"pids": pids})
        _journal(log, pids)
        return visual.CAPTURE(visual.root(e.ready_url), c.brief.visual, out, widths)
    finally:
        if left := check.dispose(e):
            notes.append(f"preview processes {sorted(left)} did not stop")


def capture(  # noqa: PLR0913 - the capture's widths come from the settings, like the visual check's
    c: Change,
    repo: Path,
    out_for: Callable[[str], Path],
    profile: Profile,
    log: Callable[[dict[str, Any]], None],
    *,
    widths: Sequence[int],
) -> VisualResult:
    """Render the brief's states at the merge-base; the findings say why any state is missing (B25)."""
    path, now, e = Path(c.names.worktree), datetime.now(UTC), c.env
    if e is None:
        return VisualResult(head="", tree="", findings=["no recipe to render"], at=now)
    try:
        base = worktree.git(path, "merge-base", "HEAD", worktree.tracking(path, c.names.target)).strip()
        tree = visual.tree(path, base)
    except (subprocess.SubprocessError, OSError) as exc:
        return VisualResult(head="", tree="", findings=[f"the merge-base could not be read: {exc}"[:300]], at=now)
    shots: list[visual.Shot] = []
    notes: list[str] = []
    tmp: Path | None = None
    try:
        out = out_for(base)
        out.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="owlbear-before-"))
        worktree.git(repo, "worktree", "add", "--quiet", "--detach", str(tmp), base)
        scope = sorted({p for t in (c.plan.tasks if c.plan else []) for p in t.scope} | set(c.brief.scope))
        for package, command in worktree.installs(profile, scope):
            if note := _run(shlex.split(command), tmp / package.strip("/") if package not in {"", "."} else tmp, log):
                notes.append(note)
                break
        else:
            shots = _serve(c, tmp, out, log, notes, widths=widths)
    except Exception as exc:  # noqa: BLE001 - the "before" capture never gates the Change (B25)
        notes.append(f"{type(exc).__name__}: {exc}"[:300])
    finally:
        if tmp is not None:
            _remove(repo, tmp)
    notes += [f"{s.state} at {s.width}px: {s.error}" for s in shots if s.error]
    states = {s.name: s.version for s in c.brief.visual}
    files = [s.file for s in shots if s.file]
    errors = [e for s in shots for e in s.errors]
    return VisualResult(
        head=base, tree=tree, states=states, files=files, widths=list(widths), errors=errors, findings=notes, at=now
    )
