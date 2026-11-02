"""How the Spotter acts in a Delivery step's session (Improvement design §4, "Live delivery"; #717).

``StepActor`` is the step's actuator (``spotter.Context.act``), bound once the session opens. Each act's note starts
with its token (``acts.TOKEN``) and is sent with the Spotter's own agent source, so no reader takes it for the owner's:

- ``steer``: the note goes into the running turn (``mode="immediate"``);
- ``stop-and-resume``: the step marks the abort as its own, aborts the turn, then sends the note, which starts the next;
  an abort or send that fails ends the step ``spotter-ask``, "The Spotter could not stop and resume this step:
  <error>", after the harm wording when harm stopped it;
- ``stop-and-ask`` (and ``ask``, a repeat's escalation): the step ends ``spotter-ask`` with the owner's question, "The
  Spotter stopped this step for irreversible harm: <note>" when harm stopped it, then its turn is marked and aborted;
- at a hand-off the submit waits for (``acts.could_act``), any other note is the submit's answer instead: the hand-off
  is refused with it and the agent goes on. A hand-off the submit no longer waits for was answered already: its note
  is ``expired``.

An act's dispatch is no delivery: a note is ``delivered`` once the session's own event feed shows the runtime took it
(its ``user.message`` with the id ``send`` returned, or the refused submit's completion), else ``unconfirmed`` after
``BOUND`` seconds. A stop to ask is delivered when it ends the step; one that comes after the step ended is ``expired``.
What raises goes to the Spotter, which keeps it on the act as ``failed``. Each SDK request (``send``, ``abort``) is
bounded as the step's own (``sdk_teardown.CALL``) and never retried: one that outlasts the bound raises too. A stop to
ask has ended the step before its abort, so the step's teardown stops the runtime if the abort fails. An act cancelled
during a request is ``failed`` with "cancelled: <the request>", and one cancelled while it waits for its confirmation
``unconfirmed``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
from typing import TYPE_CHECKING, Any

from copilot.session import AgentMessageSource

from owlbear_delivery_next.improvement import acts, spotter
from owlbear_delivery_next.runtimes.sdk_teardown import CALL, call

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    from copilot.session import CopilotSession

    from owlbear_delivery_next.runtimes.sdk_adapter import _Step

BOUND = 60.0  # seconds a note may take to show in the session's log
SOURCE = AgentMessageSource("owlbear-spotter")
ASKS = frozenset({"stop-and-ask", "ask"})
HARM = "The Spotter stopped this step for irreversible harm: {note}"
STOPPED = "The Spotter stopped this step: {note}"
UNRESUMED = "The Spotter could not stop and resume this step: {error}"
NOTE, ABORT = "the Spotter's note", "the Spotter's abort"  # the SDK requests, as a bound or cancellation names them


class StepActor:
    """The Spotter's actuator in one step's session; its confirmations come from the step's event handler."""

    def __init__(
        self,
        session: CopilotSession,
        step: _Step,
        spot: spotter.Spotter,
        *,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        """Bind the step's open *session*, the step, its Spotter (where acts are written); *sleep* waits the bound."""
        self.session, self.step, self.spot, self.sleep = session, step, spot, sleep
        self.waiting: dict[str, asyncio.Future[None]] = {}  # a message or call id: its confirmation
        self.logged: set[str] = set()  # ids the runtime logged before their sender knew them

    async def __call__(self, record: spotter.Record, act: acts.Act) -> None:
        """Dispatch *act*, the finding of *record*, and wait for the runtime to confirm it (bounded)."""
        note = f"{act.token} {act.note}"
        if act.act in ASKS:
            await self.stop_ask(record, act)
        elif record.look == "hand-off":
            waiter = self.spot.hand_offs.get(record.call)
            if waiter is None or waiter.done():
                await self._update(record, delivery="expired", error="the hand-off was answered before the look ended")
                return
            self.waiting[record.call] = asyncio.get_running_loop().create_future()
            waiter.set_result(note)
            await self._confirmed(record, record.call)
        elif act.act == "stop-and-resume":
            await self.stop_resume(record, act, note)
        else:
            await self.steer(record, note)

    async def steer(self, record: spotter.Record, note: str) -> None:
        """The note into the running turn."""
        sending = self.session.send(note, mode="immediate", source=SOURCE)
        await self._confirmed(record, await self._called(record, sending, NOTE))

    async def stop_resume(self, record: spotter.Record, act: acts.Act, note: str) -> None:
        """Abort the turn as the step's own stop, then send the note, which starts the next turn.

        An abort or send that fails ends the step with the owner's question naming the failure, so its teardown stops
        the runtime the Spotter could not stop; the act says what failed.
        """
        try:
            await self._abort(record)
            sent = await self._called(record, self.session.send(note, source=SOURCE), NOTE)
        except Exception as exc:
            failed = UNRESUMED.format(error=f"{type(exc).__name__}: {exc}")
            self.step.gate.finish("spotter-ask", None, f"{HARM.format(note=act.note)} {failed}" if act.harm else failed)
            raise
        await self._confirmed(record, sent)

    async def stop_ask(self, record: spotter.Record, act: acts.Act) -> None:
        """End the step with the owner's question, then abort the turn as the step's own stop.

        The step ends first, so no submit accepted while the abort is pending can take its place, and an abort that
        fails leaves the step's teardown to stop the runtime; the act says the abort failed.
        """
        was = self.step.gate.finish("spotter-ask", None, (HARM if act.harm else STOPPED).format(note=act.note))
        await self._abort(record)
        await self._update(record, **({"delivery": "expired", "error": "the step had ended"} if was else
                                      {"delivery": "delivered"}))  # fmt: skip

    def seen(self, kind: str, ev: Any) -> None:  # noqa: ANN401 - an SDK session event, on the step's loop
        """A message the runtime logged, or a call it completed: the note it carries is delivered."""
        if kind == "user.message":
            key = getattr(ev.data, "message_id", None)
        elif kind == "tool.execution_complete":
            key = getattr(ev.data, "tool_call_id", None)
        else:
            return
        if not key:
            return
        waiter = self.waiting.get(key)
        if waiter is None:
            self.logged.add(key)
        elif not waiter.done():
            waiter.set_result(None)

    async def _abort(self, record: spotter.Record) -> None:
        """Abort the turn, its idle marked as the step's own stop: no wrong choice, no reminder (``step_budget``).

        The mark stays until that idle or the step's end, even when the abort fails: a timed-out one may still land.
        """
        self.step.aborted = True
        await self._called(record, self.session.abort(), ABORT)

    async def _called[T](self, record: spotter.Record, request: Coroutine[Any, Any, T], what: str) -> T:
        """One SDK request, bounded as the step's own (``sdk_teardown.CALL``); a cancelled one leaves the act failed."""
        try:
            return await call(request, what, CALL)
        except asyncio.CancelledError:
            failed = functools.partial(acts.update, delivery="failed", error=f"cancelled: {what}")
            spotter.WORK.submit(failed, self.spot.folder, record.id)
            raise

    async def _confirmed(self, record: spotter.Record, key: str) -> None:
        waiter = self.waiting.setdefault(key, asyncio.get_running_loop().create_future())
        if key in self.logged:
            waiter.set_result(None)
        bound = asyncio.ensure_future(self.sleep(BOUND))
        try:
            await asyncio.wait({waiter, bound}, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:  # the step's end stopped the wait: never left pending
            unseen = functools.partial(acts.update, delivery="unconfirmed",
                                       error="the step ended before the runtime showed it")  # fmt: skip
            spotter.WORK.submit(unseen, self.spot.folder, record.id)
            raise
        finally:
            bound.cancel()
            self.waiting.pop(key, None)
        await self._update(record, delivery="delivered" if waiter.done() else "unconfirmed")

    async def _update(self, record: spotter.Record, **fields: str) -> None:
        await spotter.offload(functools.partial(acts.update, self.spot.folder, record.id, **fields))


def bind(st: _Step, session: CopilotSession) -> None:
    """Once *session* is open, its step's Spotter (if any) acts through a ``StepActor`` on it."""
    spot = st.feed.spotter if st.feed is not None else None
    if spot is None:
        return
    st.actor = StepActor(session, st, spot)
    spot.ctx = dataclasses.replace(spot.ctx, act=st.actor)
