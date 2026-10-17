"""TD-24 "before" screenshots: the brief's states rendered at the merge-base with the visual check's own recipe.

Once per Change, after the preparing Builder returned the visual check's recipe and before the host launches it,
a runner checks out the merge-base in a temporary detached worktree, runs the profile's install commands for the
Change's scope, launches the same recipe there, captures every state and disposes of all it started. The card
shows these beside the "after" screenshots. A failure is a note on the card (B25); it never gates.
"""

from __future__ import annotations

import contextlib
import shlex
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.models import VISUAL, Environment, StepKind
from owlbear_delivery_next.change_contracts.visual_records import VisualResult
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.workflow_steps import check, design, visual

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.profile_record import Profile
    from owlbear_delivery_next.change_contracts.visual_records import DetectorScan


def due(c: Change) -> bool:
    """The visual check's recipe is known and not yet launched, and this Change has no "before" capture yet."""
    e = c.env
    at_check = (c.step.kind, c.step.task) == (StepKind.CHECK, VISUAL)
    return bool(e and e.check == VISUAL and e.launched_at is None and c.before is None and c.brief.visual) and at_check


def _remove(repo: Path, tmp: Path) -> None:
    for step in (
        lambda: worktree.git(repo, "worktree", "remove", "--force", "--force", str(tmp)),
        lambda: shutil.rmtree(tmp, ignore_errors=True),
        lambda: worktree.git(repo, "worktree", "prune"),
    ):
        with contextlib.suppress(subprocess.SubprocessError, OSError):
            step()


def _serve(  # noqa: PLR0913 - the widths come from the settings, the test copy from the check's preparation
    c: Change,
    root: Path,
    out: Path,
    log: Callable[[dict[str, Any]], None],
    notes: list[str],
    *,
    widths: Sequence[int],
    prepare: Callable[[Path], dict[str, str]] | None = None,
) -> list[visual.Shot]:
    """Prepare the test copy, launch the Change's recipe in *root*, capture its states, dispose of all it started."""
    r = c.env
    if r is None:
        return []
    e = Environment(check=VISUAL, command=r.command, directory=r.directory, ready_url=r.ready_url)
    if check.answers(e.ready_url):
        notes.append(f"something else already answers at {e.ready_url}")
        return []
    try:
        env = prepare(root) if prepare else None  # TD-96: the same frozen snapshot the "after" capture restores
    except Exception as exc:  # noqa: BLE001 - the "before" capture never gates the Change (B25)
        notes.append(f"the test copy at the merge-base: {exc}"[:300])
        return []
    proc = check.start(e, root, out / "preview.log", env)
    if proc is None:
        notes.append(f"`{e.command}` did not start at the merge-base")
        return []
    e = e.model_copy(update={"pgid": proc.pid, "pids": {proc.pid: check.created(proc.pid)}})
    try:
        check.journal(log, e.pids)
        if (pids := check.ready(e, proc)) is None:
            notes.append(f"the recipe did not answer at {e.ready_url} for the merge-base")
            return []
        e = e.model_copy(update={"pids": pids})
        check.journal(log, pids)
        states = [s for s in c.brief.visual if prepare or not s.steps]  # steps run only on a test copy (TD-96)
        notes += [f"{s.name}: its steps need a test preparation" for s in c.brief.visual if s not in states]
        return visual.CAPTURE(visual.root(e.ready_url), states, out, widths, pack=design.pack())
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
    prepare: Callable[[Path], dict[str, str]] | None = None,
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
    sources: list[DetectorScan] = []
    tmp: Path | None = None
    try:
        out = out_for(base)
        out.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="owlbear-before-"))
        worktree.git(repo, "worktree", "add", "--quiet", "--detach", str(tmp), base)
        scope = sorted({p for t in (c.plan.tasks if c.plan else []) for p in t.scope} | set(c.brief.scope))
        for package, command in worktree.installs(profile, scope):
            if note := check.run(
                shlex.split(command), tmp / package.strip("/") if package not in {"", "."} else tmp, log
            ):
                notes.append(note)
                break
        else:
            shots = _serve(c, tmp, out, log, notes, widths=widths, prepare=prepare)
        if scan := design.sources(tmp, visual.ui_paths(c, worktree.head(path)), design.pack()):
            sources.append(scan)  # the Change's UI paths in the merge-base's whole tree, after the screenshots
    except Exception as exc:  # noqa: BLE001 - the "before" capture never gates the Change (B25)
        notes.append(f"{type(exc).__name__}: {exc}"[:300])
    finally:
        if tmp is not None:
            _remove(repo, tmp)
    notes += [f"{s.state} at {s.width}px: {s.error}" for s in shots if s.error]
    states = {s.name: s.version for s in c.brief.visual}
    files = [s.file for s in shots if s.file]
    errors = [e for s in shots for e in s.errors]
    scans = [s.design for s in shots if s.design] + sources
    return VisualResult(
        head=base,
        tree=tree,
        states=states,
        files=files,
        widths=list(widths),
        errors=errors,
        design=scans,
        findings=notes,
        at=now,
    )
