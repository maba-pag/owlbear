"""The brief's states rendered at a commit in a throwaway worktree: "before" at the check, the current pages in shaping.

The visual check's "before" (TD-24): after the preparing Builder returned the check's recipe and before the host
launches it, a runner checks out the merge-base, runs the profile's install commands for the Change's scope, launches
the brief's recipe (else the check's) there on the check's test copy, captures every state and disposes of all it
started. Each new check environment gets its own (D-01M6Q4B6VV4Z05WFQ1BD4X95HJ). The card shows these
beside the "after" screenshots. The shaping capture (D-01M61V2GR0C6JV2R6KJ0WR4PNB) renders the target's tip the same
way with the brief's recipe, on its own test copy, which ends in that checkout before it is removed. A failure is a
note on the card (B25); neither gates.
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

from owlbear_delivery_next.change_contracts.models import VISUAL, BriefRecipe, Environment, StepKind
from owlbear_delivery_next.change_contracts.visual_records import VisualResult
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.change_flow.amend_apply import STALE
from owlbear_delivery_next.workflow_steps import check, decision, design, visual

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from owlbear_delivery_next.change_contracts.models import Change, VisualState
    from owlbear_delivery_next.change_contracts.profile_record import Profile
    from owlbear_delivery_next.change_contracts.visual_records import DetectorScan
    from owlbear_delivery_next.impeccable.pack_files import Installed


def due(c: Change) -> bool:
    """The visual check's recipe is known and not yet launched, and a state has no "before" of its version yet."""
    e = c.env
    at_check = (c.step.kind, c.step.task) == (StepKind.CHECK, VISUAL)
    missing = c.before is None or any(c.before.states.get(s.name) != s.version for s in c.brief.visual)
    return bool(e and e.check == VISUAL and e.launched_at is None and missing and c.brief.visual) and at_check


def reset(c: Change, head: str) -> None:
    """A new visual check environment gets its own "before" on its own snapshot (D-01M6Q4B6VV4Z05WFQ1BD4X95HJ).

    The last round's "before" stays only while the owner's answer settles that round (his decision, or his waiver of
    the model check) for the same head and brief version, which captures nothing again. After an amendment that
    voided some states of a passed check, the states it keeps keep their "after" and so their "before"
    (D-01M6GBBY578CY7F5N863EXHYEQ); the voided ones, as the "after" capture takes them, are marked for both sides.
    """
    if c.env is None or c.env.check != VISUAL:  # a person check's environment leaves the visual check's evidence
        return
    if c.before is not None and (r := c.visual) and len(redo := visual.redone(c, head, r.tree)) < len(c.brief.visual):
        c.before = c.before.model_copy(update={"states": c.before.states | {s.name: STALE for s in redo}})
        return
    kept = c.visual_rounds[-1] if c.visual_rounds else None
    if kept is None or c.before is None:
        c.before = None
        return
    decided = kept.outcome == "ask" and kept.decision is not None and (kept.head, kept.brief) == (head, c.brief.version)
    waived = kept.outcome == "model" and kept.model_waived and decision.matches(c, kept, head, kept.widths)
    if not ((decided or waived) and kept.before == c.before.identity()):  # as decision.decided and .waived settle it
        c.before = None


def _remove(repo: Path, tmp: Path) -> None:
    for step in (
        lambda: worktree.git(repo, "worktree", "remove", "--force", "--force", str(tmp)),
        lambda: shutil.rmtree(tmp, ignore_errors=True),
        lambda: worktree.git(repo, "worktree", "prune"),
    ):
        with contextlib.suppress(subprocess.SubprocessError, OSError):
            step()


type Prepare = Callable[[Path], dict[str, str]]
type Inside = Callable[[Path, list[str]], None]


def _serve(  # noqa: PLR0913, PLR0917 - the recipe, its states and where they render; widths from the settings
    recipe: Environment | BriefRecipe,
    states: Sequence[VisualState],
    root: Path,
    out: Path,
    log: Callable[[dict[str, Any]], None],
    notes: list[str],
    *,
    widths: Sequence[int],
    where: str,
    prepare: Prepare | None = None,
    pack: Installed | None = None,
) -> list[visual.Shot]:
    """Prepare the test copy, launch *recipe* in *root*, capture its states, dispose of all it started.

    With *pack*, the design detector scans each page; only the check's "before" needs that.
    """
    try:
        env = prepare(root) if prepare else None  # TD-96: the same frozen snapshot the "after" capture restores
    except Exception as exc:  # noqa: BLE001 - a capture never gates the Change (B25)
        notes.append(f"the test copy at {where}: {worktree.failure(exc)}")
        return []
    e = Environment(
        check=VISUAL, command=recipe.command, directory=recipe.directory, ready_url=recipe.ready_url,
        port=check.free_port(),
    )  # fmt: skip
    if check.answers(check.url(e)):  # picked once the copy is ready, right before the launch takes it
        notes.append(f"something else already answers at {check.url(e)}")
        return []
    since = check.size(log_file := out / "preview.log")
    proc = check.start(e, root, log_file, env)
    if proc is None:
        notes.append(f"`{e.command}` did not start at {where}")
        return []
    e = e.model_copy(update={"pgid": proc.pid, "pids": {proc.pid: check.created(proc.pid)}})
    try:
        check.journal(log, e.pids)
        check.release(proc)
        if (pids := check.ready(e, proc)) is None:
            e = check.unready(e, proc)
            notes.append(f"for {where}, {check.unanswered(e, proc, log_file, since)}")
            return []
        e = e.model_copy(update={"pids": pids})
        check.journal(log, pids)
        shown = [s for s in states if prepare or not s.steps]  # steps run only on a test copy (TD-96)
        notes += [f"{s.name}: its steps need a test preparation" for s in states if s not in shown]
        return visual.CAPTURE(visual.root(check.url(e)), shown, out, widths, pack=pack)
    finally:
        if left := check.dispose(e):
            notes.append(f"preview processes {sorted(left)} did not stop")


def _render(  # noqa: PLR0913, PLR0917 - what is rendered where, and the hooks around it
    repo: Path,
    base: str,
    recipe: Environment | BriefRecipe,
    states: Sequence[VisualState],
    out: Path,
    log: Callable[[dict[str, Any]], None],
    *,
    installs: Sequence[tuple[str, str]],
    widths: Sequence[int],
    where: str,
    prepare: Prepare | None = None,
    inside: Inside | None = None,
    pack: Installed | None = None,
) -> tuple[list[visual.Shot], list[str]]:
    """Render *states* at *base* in a throwaway worktree; *inside* runs in it, even after a failure, before removal."""
    shots: list[visual.Shot] = []
    notes: list[str] = []
    tmp: Path | None = None
    try:
        out.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="owlbear-before-"))
        worktree.git(repo, "worktree", "add", "--quiet", "--detach", str(tmp), base)
        for package, command in installs:
            if note := check.run(
                shlex.split(command), tmp / package.strip("/") if package not in {"", "."} else tmp, log
            ):
                notes.append(note)
                break
        else:
            shots = _serve(recipe, states, tmp, out, log, notes, widths=widths, where=where, prepare=prepare, pack=pack)
    except Exception as exc:  # noqa: BLE001 - a capture never gates the Change (B25)
        notes.append(worktree.failure(exc))
    finally:
        if tmp is not None:
            if inside is not None:
                try:
                    inside(tmp, notes)
                except Exception as exc:  # noqa: BLE001 - its error is the capture's note, whole
                    notes.append(worktree.failure(exc))
            _remove(repo, tmp)
    return shots, notes + [f"{s.state} at {s.width}px: {s.error}" for s in shots if s.error]


def _result(  # noqa: PLR0913, PLR0917 - one result from every captured input
    c: Change, base: str, tree: str, shots: Sequence[visual.Shot], notes: list[str], widths: Sequence[int],
    *, scans: Sequence[DetectorScan] = (), at: datetime,
) -> VisualResult:  # fmt: skip
    return VisualResult(
        head=base,
        tree=tree,
        states={s.name: s.version for s in c.brief.visual},
        files=[s.file for s in shots if s.file],
        widths=list(widths),
        errors=[e for s in shots for e in s.errors],
        design=[s.design for s in shots if s.design] + list(scans),
        findings=notes,
        at=at,
    )


def capture(  # noqa: PLR0913 - the capture's widths come from the settings, like the visual check's
    c: Change,
    repo: Path,
    out_for: Callable[[str], Path],
    profile: Profile,
    log: Callable[[dict[str, Any]], None],
    *,
    widths: Sequence[int],
    prepare: Prepare | None = None,
) -> VisualResult:
    """Render the brief's states at the merge-base; the findings say why any state is missing (B25).

    The merge-base is read again at each capture, so a moved target is captured anew. The brief's recipe renders it
    when the brief has one (it rendered the target in shaping), else the check's.
    """
    path, now, e = Path(c.names.worktree), datetime.now(UTC), c.env
    tried = {s.name: s.version for s in c.brief.visual}  # a failed attempt is one too: it is not due again (B25)
    if e is None:
        return VisualResult(head="", tree="", states=tried, findings=["no recipe to render"], at=now)
    try:
        base = worktree.git(path, "merge-base", "HEAD", worktree.tracking(path, c.names.target)).strip()
        tree = visual.tree(path, base)
    except (subprocess.SubprocessError, OSError) as exc:
        why = f"the merge-base could not be read: {worktree.failure(exc)}"
        return VisualResult(head="", tree="", states=tried, findings=[why], at=now)
    sources: list[DetectorScan] = []

    def scan(tmp: Path, _notes: list[str]) -> None:  # the Change's UI paths in the merge-base's whole tree
        if found := design.sources(tmp, visual.ui_paths(c, worktree.head(path)), design.pack()):
            sources.append(found)

    scope = sorted({p for t in (c.plan.tasks if c.plan else []) for p in t.scope} | set(c.brief.scope))
    old = c.before if c.before is not None and c.before.head == base else None  # kept for the states it still holds
    states = [s for s in c.brief.visual if old is None or old.states.get(s.name) != s.version]
    shots, notes = _render(
        repo, base, c.brief.recipe or e, states, out_for(base), log, installs=worktree.installs(profile, scope),
        widths=widths, where="the merge-base", prepare=prepare, inside=scan, pack=design.pack(),
    )  # fmt: skip
    new = _result(c, base, tree, shots, notes, widths, scans=sources, at=now)
    if old is None:
        return new
    kept = {s.name for s in c.brief.visual} - {s.name for s in states}
    return new.model_copy(update={
        "files": [f for f in old.files if f.rsplit("-", 1)[0] in kept] + new.files,
        "errors": [x for x in old.errors if x.state in kept] + new.errors,
        "design": [d for d in old.design if d.kind != "source" and d.state in kept] + new.design,
    })  # fmt: skip


def at_target(  # noqa: PLR0913 - the capture's widths come from the settings, its test copy from its preparation
    c: Change,
    repo: Path,
    out: Path,
    profile: Profile,
    log: Callable[[dict[str, Any]], None],
    *,
    widths: Sequence[int],
    fetch: Callable[[Path, str], None],
    prepare: Prepare | None = None,
    finish: Inside | None = None,
) -> VisualResult:
    """The shaping capture: the brief's states at the freshly fetched target, with the brief's recipe (B25).

    *finish* ends its test copy in the throwaway checkout before it is removed; a fetch that fails ends it whole.
    """
    now, r, target = datetime.now(UTC), c.brief.recipe, c.names.target
    if r is None:
        return VisualResult(head="", tree="", findings=["the brief has no render recipe"], at=now)
    try:
        fetch(repo, target)
        base = worktree.git(repo, "rev-parse", f"{worktree.tracking(repo, target)}^{{commit}}").strip()
        tree = visual.tree(repo, base)
    except Exception as exc:  # noqa: BLE001 - a capture never gates; the owner reads its error whole
        return VisualResult(
            head="", tree="", findings=[f"the target {target} could not be read: {worktree.failure(exc)}"], at=now
        )
    shots, notes = _render(
        repo, base, r, c.brief.visual, out, log, installs=worktree.installs(profile, sorted(c.brief.scope)),
        widths=widths, where="the target", prepare=prepare, inside=finish,
    )  # fmt: skip
    return _result(c, base, tree, shots, notes, widths, at=now)
