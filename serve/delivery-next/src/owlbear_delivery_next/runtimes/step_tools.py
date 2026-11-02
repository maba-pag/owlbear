"""A step session's Delivery tools: the handlers the SDK calls and the tools it is given (D4 §3.2).

``sdk_adapter._Step`` inherits ``StepTools`` and keeps the session lifecycle. A result tool ends the step through its
``Gate``; a helper answers off the loop and the turn goes on. The submit call is shown to the step's Spotter before
Delivery accepts it, and Delivery's answer after; the accepting runs in a worker thread so lints never hold the loop
(TD-87) and a cancelled handler still keeps the answer.

When the Spotter's look at the hand-off could act (``acts.could_act``), the submit waits for that look, at most
``wait()`` seconds, one budget for the look's whole course, a wait for a slot included: a note it answers with refuses
the hand-off, as a failed call tallied ``spotter`` (never ``rejected``, never an invalid result), and the agent goes
on; the next submission is looked at again. A stop to ask ends the step first, so Delivery never accepts the
hand-off. A look that gives none, fails or outlasts the wait leaves the hand-off to Delivery as before; the look's act
says why.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING

from copilot.tools import Tool, ToolInvocation, ToolResult

from owlbear_delivery_next.change_contracts import tool_schema, tools
from owlbear_delivery_next.improvement import acts, spotter
from owlbear_delivery_next.runtimes import tool_workers, watch_feed
from owlbear_delivery_next.runtimes.results import ENDED, Gate

if TYPE_CHECKING:
    from owlbear_delivery_next.runtimes.sdk_adapter import Session


def wait() -> float:
    """Seconds a submit waits for the look at its hand-off: a slot and an answer, each within LOOK, and a teardown.

    Read when the submit comes, so it is always the sum of the bounds the look keeps (``spotter``).
    """
    return 2 * spotter.LOOK + spotter.TEARDOWN


class StepTools:
    """The tool handlers of one step session; the session gives its settings, gate, workers and watcher."""

    cfg: Session
    gate: Gate
    workers: tool_workers.Workers
    feed: watch_feed.Feed | None

    def _handle(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:
        text, ok = self.gate.call(spec, inv.arguments)
        kind = "success" if ok else "rejected" if text == ENDED else "failure"
        return ToolResult(text_result_for_llm=text, result_type=kind)

    async def _helped(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:  # off the loop: deadlines hold
        return ToolResult(text_result_for_llm=(await self.workers.call(lambda: self.gate.call(spec, inv.arguments)))[0])

    async def _submitted(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:  # lints off the loop (TD-87)
        if note := await self._looked(inv):
            with self.gate._lock:  # noqa: SLF001 - the gate's own tally, under its lock
                self.gate._tally(spec.name, "spotter")  # noqa: SLF001
            self.gate.log(event="tool", tool=spec.name, accepted=False, errors=["the Spotter refused the hand-off"])
            watch_feed.spotted(self.feed, lambda s: s.answered(inv.tool_call_id, "spotter"))
            return ToolResult(text_result_for_llm=note, result_type="failure")
        return await self.workers.call(lambda: self._answered(spec, inv))

    async def _looked(self, inv: ToolInvocation) -> str | None:
        """The Spotter's look at this hand-off, before Gate accepts it; the note it refuses it with, if it waits."""
        spot = self.feed.spotter if self.feed is not None else None
        held = spot is not None and acts.could_act(spot.ctx)
        waiter: list[asyncio.Future[str | None] | None] = []
        watch_feed.spotted(self.feed, lambda s: waiter.append(s.handed_off(inv.tool_call_id, inv.arguments, held=held)))
        if not waiter or waiter[0] is None:
            return None
        try:
            return await asyncio.wait_for(asyncio.shield(waiter[0]), wait())
        except TimeoutError:
            waiter[0].cancel()  # the look goes on; a note it gives later is expired
            return None

    def _answered(self, spec: tools.Spec, inv: ToolInvocation) -> ToolResult:  # in its thread: kept if cancelled
        result = self._handle(spec, inv)
        watch_feed.spotted(self.feed, lambda s: s.answered(inv.tool_call_id, str(result.result_type)))
        return result

    def tools(self) -> list[Tool]:
        """The step's Delivery tools for the SDK, each bound to its spec and handler."""
        helped = {spec for spec, _ in self.cfg.helpers}  # these answer, and the turn goes on; so does a first look
        made = partial(Tool, skip_permission=True)
        handlers = {
            s: self._helped if s in helped else self._submitted if s is self.cfg.submit else self._handle
            for s in self.gate.specs
        }
        return [
            made(s.name, s.description, partial(handlers[s], s), tool_schema.schema(s),
                 is_terminal=s not in helped and s is not self.cfg.first_look)
            for s in self.gate.specs
        ]  # fmt: skip
