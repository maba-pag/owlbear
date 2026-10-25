"""TD-56: a session result TD-54 kept unprocessed, and the owner's "accept" of it.

The result is held with the step, brief version and worktree HEAD it depends on. Accepting processes it as if the
session had just returned, but only while all three still match; otherwise the step runs again. Only an agent
step's own session is held: a session judging inside a step (plan challenge, brief challenge, visual review) judges
inputs Delivery does not hold, so its unread usage still only reruns the step.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.failures import UNREAD, VISUAL_MODEL
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.workflow_steps import decision

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Option, Question
    from owlbear_delivery_next.change_contracts.visual_records import VisualRound
    from owlbear_delivery_next.state_store.store import Lock, Store

ACCEPT = "accept"  # the gate question's option that processes the held result
HEAD_SECONDS = 3  # the page polls through this check; a slower Git offers no accept rather than stalling it
# Fields a result model no longer has, dropped from a result held before the change; a new call stays strict.
# A build's changed_paths had to equal the paths Delivery read at its head, so they stand in for its own record.
OBSOLETE = {"BuildResult": ("changed_paths",)}


class HeldRun(BaseModel):
    """The parts of a session's run its processing reads; usage is not kept, since the gate already counted it."""

    session_id: str
    ending: str
    detail: str = ""
    head: str | None = None
    changed: list[str] = []  # the paths the commits change at head, as Delivery read them; empty in older holds
    payload: dict[str, Any] | None = None  # {"model": a result model's name, "args": its fields}
    denials: list[str] = []
    denied: dict[str, str] = {}
    runtime: str = "sdk"
    quota: bool = False
    quota_reset: datetime | None = None


class Held(BaseModel):
    """What the held result depends on, the gate question that offers it, and the result itself."""

    question: str
    kind: str
    task: str | None
    mode: str | None
    brief: int
    head: str
    at: datetime
    run: HeldRun


def _path(store: Store, slug: str) -> Path:
    return store.root / "changes" / slug / "held.json"


def _dump(run: Run) -> HeldRun:
    p = run.payload
    return HeldRun(
        session_id=run.session_id,
        ending=run.ending,
        detail=run.detail,
        head=run.head,
        changed=run.changed,
        payload={"model": type(p).__name__, "args": p.model_dump(mode="json")} if p else None,
        denials=run.denials,
        denied=run.denied,
        runtime=run.runtime,
        quota=run.quota,
        quota_reset=run.quota_reset,
    )


def _load(data: HeldRun) -> Run:
    """The held run, whose processes were confirmed gone when it was held; its payload is a result model.

    Raises:
        ValueError: The payload names no result model.
    """
    p = data.payload
    model = getattr(tools, str(p.get("model")), None) if p else None
    if p and not (isinstance(model, type) and issubclass(model, tools.Args)):
        msg = f"held payload {p.get('model')!r} is not a result model"
        raise ValueError(msg)
    args, old = _current(p)
    return Run(
        data.session_id,
        ending=data.ending,  # type: ignore[arg-type] - checked by the ending dispatch, which refuses unknown ones
        payload=model.model_validate(args) if p and model else None,
        detail=data.detail,
        head=data.head,
        changed=list(data.changed) or old,
        denials=list(data.denials),
        denied=dict(data.denied),
        runtime=data.runtime,
        usage={"error": "held"},  # counted when the gate logged the session
        termination=Termination(confirmed=True),
        quota=data.quota,
        quota_reset=data.quota_reset,
    )


def _current(payload: dict[str, Any] | None) -> tuple[object, list[str]]:
    """A held payload's fields without those its model no longer has, and an older build's changed_paths."""
    args = payload.get("args") if payload else None
    if not isinstance(args, dict):
        return args, []
    gone = OBSOLETE.get(str(payload.get("model")), ()) if payload else ()
    paths = args.get("changed_paths") if "changed_paths" in gone else None
    kept = {k: v for k, v in args.items() if k not in gone}
    return kept, [str(x) for x in paths] if isinstance(paths, list) else []


def keep(store: Store, lock: Lock, change: Change, run: Run, head: str) -> None:
    """Hold an agent step's unread result for the gate question just asked, with what it depends on.

    A held build's session ends at *head*: its span closes there, as a recorded session's does (TD-210).
    """
    lock.check(change.slug)
    s, asked = change.step, change.outcome.question if change.outcome else None
    task = next((t for t in change.plan.tasks if t.id == s.task), None) if change.plan else None
    if s.kind == StepKind.BUILD and task and task.spans and task.spans[-1].endswith(".."):
        task.spans[-1] += head
        store.write(lock, change)
    held = Held(
        question=asked or "",
        kind=s.kind,
        task=s.task,
        mode=s.mode,
        brief=change.brief.version,
        head=head,
        at=datetime.now(UTC),
        run=_dump(run),
    )
    atomic_write(_path(store, change.slug), held.model_dump_json())


def _accepted(change: Change, question: str) -> bool:
    """Whether the owner chose "accept" on the gate question that offered this hold."""
    q = next((q for q in change.questions if q.id == question and (q.cause or "").endswith(f":{UNREAD}")), None)
    return bool(q and q.answer and q.answer.option == ACCEPT)


def head(path: Path) -> str | None:
    """The worktree HEAD a held result depends on; None when Git cannot read it quickly, so nothing is offered."""
    try:
        done = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
            [worktree.GIT, "rev-parse", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
            timeout=HEAD_SECONDS,
        )
    except OSError, subprocess.SubprocessError:
        return None
    return done.stdout.strip()


def _read(store: Store, slug: str) -> Held | None:
    try:
        return Held.model_validate_json(_path(store, slug).read_text())
    except OSError, ValueError, ValidationError:
        return None


def _matches(held: Held, change: Change) -> bool:
    """The step, brief version and commit the hold depends on are still the Change's."""
    s, where = change.step, change.names.worktree
    same = (held.kind, held.task, held.mode, held.brief) == (s.kind, s.task, s.mode, change.brief.version)
    return same and bool(where) and head(Path(where)) == held.head


def offered(store: Store, change: Change, question: Question) -> list[Option]:
    """The question's options as offered now: "accept" only while what it would accept still matches (TD-56, TD-94).

    A held step result needs its hold; a visual round needs every input its verdicts depended on.
    """
    cause = question.cause or ""
    if all(o.id != ACCEPT for o in question.options) or not cause.endswith((f":{UNREAD}", f":{VISUAL_MODEL}")):
        return question.options
    if cause.endswith(f":{VISUAL_MODEL}"):
        kept, where = (change.visual_rounds[-1] if change.visual_rounds else None), change.names.worktree
        if kept is not None and kept.outcome == "model" and where and _visual_holds(store, change, kept, Path(where)):
            return question.options
        return [o for o in question.options if o.id != ACCEPT]
    hold = _read(store, change.slug)
    if hold is not None and hold.question == question.id and _matches(hold, change):
        return question.options
    return [o for o in question.options if o.id != ACCEPT]


def _visual_holds(store: Store, change: Change, kept: VisualRound, where: Path) -> bool:
    """The round's capture and every input its verdicts depended on, widths included, are still the Change's."""
    try:
        widths = (change.before.widths if change.before else None) or store.settings().widths or []
    except Exception:  # noqa: BLE001 - unreadable settings offer no accept rather than fail the page
        return False
    return decision.matches(change, kept, head(where), widths)


def take(store: Store, lock: Lock, change: Change) -> Run | None:
    """The held result when the owner accepted it and it still matches the step, brief version and HEAD.

    An accepted hold stays on disk until `consume` records it once its result is durably applied; a stale or
    declined one is removed here.
    """
    lock.check(change.slug)
    file = _path(store, change.slug)
    if not file.exists():
        return None
    held = _read(store, change.slug)
    try:
        run = _load(held.run) if held else None
    except ValueError, ValidationError, TypeError:
        run = None
    if held is None or run is None or not _accepted(change, held.question):
        file.unlink(missing_ok=True)
        return None
    if not _matches(held, change):
        file.unlink(missing_ok=True)
        at = datetime.now(UTC).isoformat(timespec="seconds")
        store.log(lock, change.slug, {"event": "held-stale", "at": at, "session": run.session_id})
        return None
    return run


def consume(store: Store, lock: Lock, slug: str, run: Run) -> None:
    """Record an accepted hold once its result is durably applied, then remove it."""
    lock.check(slug)
    at = datetime.now(UTC).isoformat(timespec="seconds")
    store.log(lock, slug, {"event": "held-accepted", "at": at, "session": run.session_id})
    _path(store, slug).unlink(missing_ok=True)
