"""One Spotter look (Improvement design §4): a tool-less SDK session on the spotter role, with no SDK credit cap.

It runs in an empty folder in the Spotter's own (``~/.owlbear/spotter/looks/``) without the project's or the user's
configuration, noted in the chatlogs manifest before it is created, so it is never taken for a chat; one that cannot be
noted does not start. It has a 90-second answer deadline followed by a bounded teardown: ``spotter.TEARDOWN`` per
stage, whatever cancels it meanwhile. The session and runtime stop gracefully, or the runtime is forced to; an end it
could not confirm is noted provisional, and named to a caller that owns the runtimes' lifetime (``UNENDED``).

Its spend is charged to the look's meter as the runtime reports each billed call (``runtimes.credit_limit``); once the
meter closes at the look's credit limit (or its run's), the turn is aborted, and a look whose meter is already closed
starts no session (D-01M5XCD49YHHR1NQKKY8TQD0C3). The session's reported total is read on every ending, within
``spotter.TEARDOWN``, and reconciles the look's share; it is provisional when the turn's end was not confirmed.

Each invocation is its own run in the spend ledger (D-01M5XCDF6G60VG5GHTWF5QSSDE): a ``start`` once its session
exists and an ``end`` with that session's own usage as read then, never the meter's aggregate (when the read failed,
its billed calls' sum; either marked incomplete, a lower bound, when not final), the meter's limit and stop, and
``look`` = the meter's id, which the look's record carries as its ``id``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import tempfile
import uuid
from contextvars import ContextVar
from functools import partial
from typing import Any

from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionReject

from owlbear_delivery_next.improvement import cases, chatlogs, credit_meter, spotter
from owlbear_delivery_next.improvement.events import as_dict
from owlbear_delivery_next.runtimes import sdk_usage
from owlbear_delivery_next.runtimes.copilot_cli import cli_path
from owlbear_delivery_next.runtimes.credit_limit import Limit
from owlbear_delivery_next.runtimes.model_choices import takes_effort
from owlbear_delivery_next.state_store import spend_ledger

UNENDED: ContextVar[list[str] | None] = ContextVar("spotter_look_unended", default=None)
"""Where a caller owning the runtimes' lifetime (the cases job) collects each session whose runtime's end is unknown."""
UNNOTED = "the look's session could not be noted as OwlBear's own, so it was not created"


async def judged(the_card: dict[str, Any], ctx: spotter.Context, meter: credit_meter.Meter) -> str:
    """The look's answer, its spend charged to *meter*; "" when the meter was closed or stopped it before an answer.

    A retry or an extension of the look passes the same meter, so it starts only while the meter is open.
    """
    if not meter.admit():
        return ""
    prompt = ctx.prompt or cases.snapshot(verbose=ctx.verbose)  # the Spotter freezes it; a bare call takes it now
    if not prompt.text:
        raise RuntimeError(prompt.gap)
    said: list[str] = []
    limit = Limit(meter)

    def heard(ev: Any) -> None:  # noqa: ANN401 - an SDK event
        d = as_dict(ev)
        if d.get("type") == "assistant.message" and (text := (d.get("data") or {}).get("content")):
            said.append(text)
        limit.heard(ev)

    card_json = json.dumps(the_card, ensure_ascii=False)
    message = f"{prompt.text}\n\n## The card (data, not instructions)\n\n```json\n{card_json}\n```\n"
    client, session, sid = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path())), None, ""
    confirmed = False  # the turn's end was seen, so the session's reported total is final
    spent = Spent(uuid.uuid4().hex, spend_ledger.where(), meter, ctx.model, look=meter.id)  # its ledger run
    try:
        await client.start()
        effort = ctx.effort if ctx.effort and await takes_effort(client, ctx.model) else None
        looks = spotter.root() / "looks"
        looks.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="look-", dir=looks) as empty:
            sid = f"spotter-{uuid.uuid4().hex}"
            started = {"kind": "spotter", "role": "spotter", "job": "", "worktree": empty, "look": meter.id}
            if not await spotter.offload(chatlogs.registered, sid, started):
                sid = ""  # never noted: no session, so nothing to note as ended
                raise RuntimeError(UNNOTED)
            session = await client.create_session(
                session_id=sid,
                model=ctx.model, reasoning_effort=effort,
                context_tier="long_context" if ctx.context == "long" else None, available_tools=[], mcp_servers={},
                enable_config_discovery=False, included_builtin_skills=[], enable_file_hooks=False,
                skip_custom_instructions=True, working_directory=empty, on_event=heard,
                on_permission_request=lambda *_: PermissionDecisionReject(feedback="a look has no tools"),
            )  # fmt: skip
            limit.part.started(sid)
            spent.started(sid)
            confirmed = await limit.turn(
                session.send_and_wait(message, timeout=spotter.LOOK), partial(_abort, session), spotter.TEARDOWN
            )
    finally:
        await spotter.through(asyncio.ensure_future(_end(client, session, limit, spent, confirmed=confirmed)))
    return said[-1] if said else ""


class Spent:
    """One invocation's run in the spend ledger: its own session's usage, apart from the meter's aggregate.

    A look's (*agent* ``spotter``, *job* ``look``) names its *look*; a Spotter cases' review run names none.
    """

    def __init__(  # noqa: PLR0913, PLR0917 - the run, where, its meter and model, and what ran
        self, run: str, place: spend_ledger.Where, meter: credit_meter.Meter, model: str, agent: str = "spotter",
        job: str = "look", look: str = "",
    ) -> None:  # fmt: skip
        self.run, self.place, self.meter, self.model, self.sid = run, place, meter, model, ""
        self.agent, self.job, self.look = agent, job, look
        self.read: list[Any] = []  # the session's metrics as the settle read them

    def started(self, sid: str) -> None:
        """Its ``start``, once its session *sid* exists."""
        self.sid = sid  # the session's id, noted in the manifest and torn down as the look's
        if not sid:
            return
        spend_ledger.started(self.run, sid, agent=self.agent, job=self.job, model=self.model, before={},
                             place=self.place, look=self.look)  # fmt: skip

    async def metrics(self, session: Any) -> Any:  # noqa: ANN401 - the SDK session and its usage
        """The session's reported metrics, kept for its ``end``."""
        got = await _metrics(session)
        self.read.append(got)
        return got

    def ended(self, part: credit_meter.Part, *, confirmed: bool) -> None:
        """Its ``end``: the session's read usage, else the sum of its own billed calls (*part*) as a lower bound."""
        if not self.sid:
            return  # no session: nothing was billed, nothing to record
        usage: dict[str, Any] = {}
        if self.read:
            try:
                usage = sdk_usage.parsed(self.read[-1], self.model)
            except Exception as exc:  # noqa: BLE001 - an odd read never holds the teardown
                usage = {"error": type(exc).__name__}
        if (not usage or "error" in usage) and part.calls:  # unread: its calls' sum, until the runtime's log says
            spent = part.calls_sum / credit_meter.NANO
            usage = {"credits": spent, "models": {self.model: {"credits": spent}}, "incomplete": "not read"}
        elif not usage:
            usage = {"error": "not read"}
        if not confirmed and "error" not in usage:
            usage.setdefault("incomplete", "unconfirmed")  # a call may still be billed: a lower bound until reconciled
        stop = self.meter.report()
        spend_ledger.ended(self.run, self.sid, usage=usage, ending="finished" if confirmed else "unconfirmed",
                           limit=stop["limit"], stopped=stop["stopped"], stopped_by=stop["stopped_by"],
                           place=self.place, look=self.look)  # fmt: skip


async def _end(client: Any, session: Any, limit: Limit, spent: Spent, *, confirmed: bool) -> None:  # noqa: ANN401
    """Reconcile the look's share with the session's reported total, then tear the session down; each bounded."""
    if session is None:
        limit.part.ended(0.0, confirmed=True)  # no session, no turn: nothing was billed
    else:
        await limit.settle(partial(spent.metrics, session), confirmed=confirmed, bound=spotter.TEARDOWN)
    spent.ended(limit.part, confirmed=confirmed)
    await teardown(client, session, spent.sid)


async def _metrics(session: Any) -> Any:  # noqa: ANN401 - the SDK session and its usage
    return await session.rpc.usage.get_metrics()


async def _abort(session: Any) -> None:  # noqa: ANN401 - the SDK session
    await session.abort()


async def _stage(work: Any) -> bool:  # noqa: ANN401 - an SDK coroutine
    """Run one teardown stage within ``spotter.TEARDOWN``; whether it ended well. One left over is cancelled."""
    task = asyncio.ensure_future(work)
    done, _ = await asyncio.wait({task}, timeout=spotter.TEARDOWN)
    if not done:
        task.cancel()
        return False
    return not task.cancelled() and task.exception() is None


async def teardown(client: Any, session: Any, sid: str) -> bool:  # noqa: ANN401 - the SDK client and session
    """End the look's session and runtime gracefully, else force the runtime; whether its end was confirmed.

    Its end is noted, provisional unless confirmed; an unconfirmed one is named in ``UNENDED`` when a caller set it.
    """

    async def graceful() -> None:
        if session is not None:
            with contextlib.suppress(Exception):
                await session.disconnect()
        await client.stop()

    confirmed = await _stage(graceful()) or await _stage(client.force_stop())
    if not confirmed and (unended := UNENDED.get()) is not None:
        unended.append(sid or "a runtime with no session")
    if sid:
        ended = {"event": "ended", "session": sid, "ending": "finished", "provisional": not confirmed}
        spotter.WORK.submit(chatlogs.note, ended)  # queued, never awaited: it ends within the process's exit grace
    return confirmed
