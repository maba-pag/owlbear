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

    from owlbear_delivery_next.models import Change, VisualState
    from owlbear_delivery_next.profile_record import Profile

INSTALL_WITHIN = 600.0  # seconds per install command


def due(c: Change) -> bool:
    """The visual check's recipe is known and not yet launched, and this Change has no "before" capture yet."""
    e = c.env
    at_check = (c.step.kind, c.step.task) == (StepKind.CHECK, VISUAL)
    return bool(e and e.check == VISUAL and e.launched_at is None and c.before is None and c.brief.visual) and at_check


def _run(argv: list[str], cwd: Path) -> str:
    """Run one install command in its own group; a note if it failed, empty on success."""
    try:
        proc = subprocess.Popen(  # noqa: S603 - argument vector of an install command the owner made known
            argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True,
        )  # fmt: skip
    except OSError as exc:
        return f"`{shlex.join(argv)}` did not start: {exc}"
    try:
        out, _ = proc.communicate(timeout=INSTALL_WITHIN)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return f"`{shlex.join(argv)}` took over {INSTALL_WITHIN:.0f} s"
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


def _serve(
    e: Environment, root: Path, out: Path, states: Sequence[VisualState], log: Callable[[dict[str, Any]], None]
) -> tuple[Environment, list[visual.Shot], str]:
    """Launch the recipe in *root*, capture *states* once it answers; the environment started, shots, a note."""
    if check.answers(e.ready_url):
        return e, [], f"something else already answers at {e.ready_url}"
    proc = check.start(e, root, out / "preview.log")
    if proc is None:
        return e, [], f"`{e.command}` did not start at the merge-base"
    e = e.model_copy(update={"pgid": proc.pid, "pids": {proc.pid: check.created(proc.pid)}})
    log({"event": "pids", "at": datetime.now(UTC).isoformat(), "pids": {str(p): t for p, t in e.pids.items()}})
    if (pids := check.ready(e, proc)) is None:
        return e, [], f"the recipe did not answer at {e.ready_url} for the merge-base"
    e = e.model_copy(update={"pids": pids})
    log({"event": "pids", "at": datetime.now(UTC).isoformat(), "pids": {str(p): t for p, t in pids.items()}})
    return e, visual.CAPTURE(visual.root(e.ready_url), states, out), ""


def capture(
    c: Change, repo: Path, out_for: Callable[[str], Path], profile: Profile, log: Callable[[dict[str, Any]], None]
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
    out, tmp = out_for(base), Path(tempfile.mkdtemp(prefix="owlbear-before-"))
    out.mkdir(parents=True, exist_ok=True)
    env = Environment(check=VISUAL, command=e.command, directory=e.directory, ready_url=e.ready_url)
    shots: list[visual.Shot] = []
    notes: list[str] = []
    try:
        worktree.git(repo, "worktree", "add", "--quiet", "--detach", str(tmp), base)
        scope = sorted({p for t in (c.plan.tasks if c.plan else []) for p in t.scope} | set(c.brief.scope))
        for package, command in worktree.installs(profile, scope):
            if note := _run(shlex.split(command), tmp / package.strip("/") if package not in {"", "."} else tmp):
                notes.append(note)
                break
        else:
            env, shots, note = _serve(env, tmp, out, c.brief.visual, log)
            notes += [note] if note else []
    except Exception as exc:  # noqa: BLE001 - the "before" capture never gates the Change (B25)
        notes.append(f"{type(exc).__name__}: {exc}"[:300])
    finally:
        if env.pgid is not None and (left := check.dispose(env)):
            notes.append(f"preview processes {sorted(left)} did not stop")
        _remove(repo, tmp)
    notes += [f"{s.state} at {s.width}px: {s.error}" for s in shots if s.error]
    states = {s.name: s.version for s in c.brief.visual}
    files = [s.file for s in shots if s.file]
    return VisualResult(head=base, tree=tree, states=states, files=files, findings=notes, at=now)
