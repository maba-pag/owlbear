"""TD-56: a session result TD-54 kept unprocessed, and the owner's "accept" of it.

The result is held with the step, brief version and worktree HEAD it depends on. Accepting processes it as if the
session had just returned, but only while all three still match; otherwise the step runs again. Only an agent
step's own session is held: a session judging inside a step (plan challenge, brief challenge, visual review) judges
inputs Delivery does not hold, so its unread usage still only reruns the step.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.failures import UNREAD, VISUAL_MODEL
from owlbear_delivery_next.change_contracts.held_records import HeldRecord, HeldRun
from owlbear_delivery_next.change_contracts.models import Change, Exit, StepKind
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.runtimes import session_result
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.workflow_steps import decision, sessions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Option, Question
    from owlbear_delivery_next.change_contracts.visual_records import VisualRound
    from owlbear_delivery_next.runtimes import sdk_adapter
    from owlbear_delivery_next.state_store.store import Lock, Store

ACCEPT = "accept"  # the gate question's option that processes the held result
HEAD_SECONDS = 3  # the page polls through this check; a slower Git offers no accept rather than stalling it
UNRECORDED = "the usage of a session held by an older build was not recorded; it is unknown, not zero"
# Fields a result model no longer has, dropped from a result held before the change; a new call stays strict.
# A build's changed_paths had to equal the paths Delivery read at its head, so they stand in for its own record.
OBSOLETE = {"BuildResult": ("changed_paths",)}
READ_ONLY = frozenset({StepKind.PLAN, StepKind.REVIEW})  # their sessions run in the Change's read-only worktree


class Held(HeldRecord):
    """A held record in the held file, with the Change the gate question was asked on (RUN-04).

    The hold is the first durable record of a session whose usage stayed unread: it keeps the Change, the step label,
    and the run with its accounting, so counting it needs no session.
    """

    change: Change | None = None  # None in a hold an older build kept; its Change is then the stored one


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
        usage=run.usage,
        usage_unread=run.usage_unread,
        model_check=run.model_check,
        subagents=run.subagents,
        tool_calls=run.tool_calls,
        counted=True,
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


def hold(  # noqa: PLR0913, PLR0917 - the store, its lock, the step's change and run, the head and the step label
    store: Store, lock: Lock, change: Change, run: Run, head: str, label: dict[str, Any]
) -> Held:
    """Hold an agent step's unread result for the gate question just asked, before anything is counted (RUN-04).

    A held build's session ends at *head*: its span closes there, as a recorded session's does (TD-210). The Change
    written here is a copy: the stored Change gets the span and the count with the hold's accounting. When the held
    file cannot be written, the Change keeps the same record in `held_fallback`, so the gate and its count still
    survive; the caller's Change write is then the only durable write, and its failure is raised to the caller.
    """
    lock.check(change.slug)
    snap = change.model_copy(deep=True)
    s, asked = snap.step, snap.outcome.question if snap.outcome else None
    task = next((t for t in snap.plan.tasks if t.id == s.task), None) if snap.plan else None
    if s.kind == StepKind.BUILD and task and task.spans and task.spans[-1].endswith(".."):
        task.spans[-1] += head
    held = Held(
        question=asked or "",
        kind=s.kind,
        task=s.task,
        mode=s.mode,
        brief=change.brief.version,
        head=head,
        at=datetime.now(UTC),
        run=_dump(run),
        label=label,
        change=snap,
    )
    try:
        atomic_write(_path(store, change.slug), held.model_dump_json())
    except OSError:
        snap.held_fallback = HeldRecord.model_validate(held.model_dump(exclude={"change"}))
    return held


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
    """The held record: the held file when it is written, else the one the Change keeps (RUN-04)."""
    try:
        return Held.model_validate_json(_path(store, slug).read_text())
    except OSError, ValueError, ValidationError:
        pass
    record = store.read(slug).held_fallback
    return Held.model_validate(record.model_dump()) if record is not None else None


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
    held = _read(store, change.slug)
    if held is None or gen(held) in change.accepted_holds:
        return None
    try:
        run = _load(held.run)
    except ValueError, ValidationError, TypeError:
        run = None
    if run is None or not _accepted(change, held.question):
        _path(store, change.slug).unlink(missing_ok=True)
        return None
    if not _matches(held, change):
        _path(store, change.slug).unlink(missing_ok=True)
        at = datetime.now(UTC).isoformat(timespec="seconds")
        store.log(lock, change.slug, {"event": "held-stale", "at": at, "session": run.session_id})
        return None
    return run


def gen(held: Held) -> str:
    """The identity of a held result: its session and when it was kept, so each hold is distinct (RUN-04)."""
    return f"{held.run.session_id}@{held.at.isoformat()}"


def uncounted(store: Store, change: Change) -> Held | None:
    """The hold on disk whose usage and tool calls the Change does not count yet, if any (RUN-04)."""
    held = _read(store, change.slug)
    return held if held is not None and gen(held) not in change.counted_holds else None


def accounted(data: HeldRun) -> Run:
    """The held run with the usage and tool calls its gate kept, so counting it happens exactly once.

    A hold an older build kept has no usage record: its usage is unknown and counts as unread, never as zero.
    """
    run = _load(data)
    if not data.counted:
        return replace(run, usage={"error": "held-unrecorded"}, usage_unread=UNRECORDED)
    return replace(
        run,
        usage=dict(data.usage),
        usage_unread=data.usage_unread,
        model_check=data.model_check,
        subagents=list(data.subagents),
        tool_calls={k: dict(v) for k, v in data.tool_calls.items()},
    )


class Deferred:
    """An accepted hold's post-session writes, kept in memory until its receipted result is written (RUN-04).

    A failed final write then leaves the stored Change as it was before those writes, so a restart runs them once.
    Other slugs and reads pass through to the store.
    """

    def __init__(self, store: Store, slug: str) -> None:
        self._store = store
        self._slug = slug
        self._change: Change | None = None
        self._events: list[tuple[Lock, str, dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - the store's other methods pass through
        return getattr(self._store, name)

    def read(self, slug: str) -> Change:
        """The slug's Change as last written here, else as the store has it."""
        if slug == self._slug and self._change is not None:
            return self._change.model_copy(deep=True)
        return self._store.read(slug)

    def write(self, lock: Lock, change: Change) -> None:
        """Hold this slug's Change in memory; other slugs are written through."""
        if change.slug != self._slug:
            return self._store.write(lock, change)
        self._change = change.model_copy(deep=True)
        return None

    def log(self, lock: Lock, slug: str, event: dict[str, Any]) -> None:
        """Hold this slug's events in memory; other slugs are logged through."""
        if slug != self._slug:
            return self._store.log(lock, slug, event)
        self._events.append((lock, slug, event))
        return None

    def flush(self) -> None:
        """The buffered events, once the receipted result is durable."""
        for lock, slug, event in self._events:
            self._store.log(lock, slug, event)
        self._events.clear()


def receipted(store: Store, change: Change, accepted: Run | None) -> Change:
    """The Change with an accepted hold's identity recorded, so its result is written with the receipt."""
    if accepted is None:
        return change
    held = _read(store, change.slug)
    if held is None:
        msg = "the accepted held result is unreadable; the step stays for a restart"
        raise OSError(msg)
    change.accepted_holds = [*change.accepted_holds, gen(held)]
    return change


def consume(store: Store, lock: Lock, slug: str) -> None:
    """Remove an accepted hold once its result is durably recorded; its event is logged once.

    A hold the Change kept as its fallback is cleared from the Change last, so a failed step leaves it for the retry.
    """
    lock.check(slug)
    held = _read(store, slug)
    if held is not None:
        gen_ = gen(held)
        if gen_ not in {e.get("gen") for e in store.events(slug) if e.get("event") == "held-accepted"}:
            at = datetime.now(UTC).isoformat(timespec="seconds")
            store.log(lock, slug, {"event": "held-accepted", "at": at, "session": held.run.session_id, "gen": gen_})
    _path(store, slug).unlink(missing_ok=True)
    kept = store.read(slug)
    if kept.held_fallback is not None:
        kept.held_fallback = None
        store.write(lock, kept)


def settled(store: Store, lock: Lock, change: Change) -> bool:
    """Whether the hold on disk is already recorded with the Change: then it is only cleaned up, never applied again."""
    held = _read(store, change.slug)
    if held is None or gen(held) not in change.accepted_holds:
        return False
    consume(store, lock, change.slug)
    return True


def kept_session(
    store: Store, lock: Lock, change: Change, path: Path, config: Callable[[Path], sdk_adapter.Session]
) -> Run:
    """The step's own session, a read-only one in the Change's read-only worktree.

    An unread one names the Change worktree, whose HEAD is the commit judged, so the gate can hold its result (TD-56).
    """

    def own(cfgs: list[sdk_adapter.Session]) -> list[Run]:
        try:
            return [sessions.run(store, cfgs[0])]
        except sessions.UsageUnreadError as exc:
            exc.worktree = path
            raise

    if change.step.kind in READ_ONLY:
        return sessions.isolated(store, lock, change, path, lambda at: [config(at)], own)[0]
    return own([config(path)])[0]


def write_result(  # noqa: PLR0913, PLR0917 - the receipt needs the store, lock, change, hold and deferred writes
    store: Store,
    lock: Lock,
    change: Change,
    accepted: Run | None,
    final: Change,
    post: Store | Deferred,
) -> None:
    """Write a step's result with an accepted hold's receipt, then remove the hold once that write is durable."""
    store.write(lock, receipted(store, final, accepted))
    if isinstance(post, Deferred):  # the logs its writes deferred follow the receipted result
        post.flush()
    if accepted:  # a failed write, or a failed cleanup, leaves the hold: the receipt stops it running again
        consume(store, lock, change.slug)


def gate_unread(store: Store, lock: Lock, exc: sessions.UsageUnreadError) -> None:
    """TD-54: the owner decides; an agent step's own result is held so it can be accepted instead (TD-56).

    The hold is written before anything is counted. When the held file cannot be written, the Change keeps the same
    record, so the run is never lost and never paid for again; the gate and its count then come from that one Change.
    """
    kept = store.read(lock.slug)  # what the step wrote before and during the session; nothing after it
    here = head(exc.worktree) if exc.worktree else None
    here = here if here and exc.run.head in {None, here} else None  # the result's own commit is still HEAD
    label = {"label": exc.label} if exc.label else {}  # whose session it was, when not the step's own (TD-376)
    if here:
        gated = loop.apply(kept, session_result.usage_gate(exc.run, kept.step.kind, accept=True), datetime.now(UTC))
        counted_hold(store, lock, hold(store, lock, gated, exc.run, here, label))
        return
    gated = loop.apply(kept, session_result.usage_gate(exc.run, kept.step.kind, accept=False), datetime.now(UTC))
    store.write(lock, gated)
    sessions.logged(store, lock, gated, exc.run, {"kind": kept.step.kind, "exit": Exit.ASK} | label)


def counted_hold(store: Store, lock: Lock, pending: Held) -> None:
    """A held session counts once, with the gate question it was asked on, and only then does the step wait (RUN-04).

    An older hold keeps no Change of its own, so the stored one is the base it counts on.
    """
    change = pending.change or store.read(lock.slug)
    change.counted_holds = [*change.counted_holds, gen(pending)]
    sessions.logged(
        store, lock, change, accounted(pending.run), {"kind": pending.kind, "exit": Exit.ASK} | pending.label
    )
