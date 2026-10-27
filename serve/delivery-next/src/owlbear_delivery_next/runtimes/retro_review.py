"""One ``retro-review`` session for the Spotter cases (Improvement design §4, §6): tool-less, within its meter.

It checks a candidate's card against its call, or minimises and sanitises a case for publication. Like a look, it runs
in an empty folder without the project's or the user's configuration, noted in the chatlogs manifest so it is never
taken for a chat, and its teardown is bounded. Its billed calls are charged to the run's meter as they are reported
(``runtimes.credit_limit.Limit``); once the meter closes the turn is aborted, and the session's share is reconciled
with its reported total at its end. Like a look's, each session is its own run in the spend ledger
(D-01M5XCDF6G60VG5GHTWF5QSSDE): its own usage, ending, the meter's limit and stop (``spotter_look.Spent``).
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from functools import partial
from typing import TYPE_CHECKING, Any

from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionReject

from owlbear_delivery_next.improvement import spotter
from owlbear_delivery_next.improvement.events import as_dict
from owlbear_delivery_next.runtimes import chatlogs, spotter_look
from owlbear_delivery_next.runtimes.copilot_cli import cli_path
from owlbear_delivery_next.runtimes.credit_limit import Limit
from owlbear_delivery_next.runtimes.model_choices import takes_effort
from owlbear_delivery_next.state_store import spend_ledger

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.improvement.credit_meter import Meter

SECONDS = 180.0  # an answer's deadline


async def asked(message: str, meter: Meter, role: RoleModel) -> str:
    """The session's last answer to *message*, its spend charged to *meter*; "" when the meter stopped it first.

    Raises:
        RuntimeError: *meter* is closed, so the session never starts.
    """
    if not meter.admit():
        msg = f"the {meter.report()['stopped_by']} spend is {meter.report()['stopped']}: no review starts"
        raise RuntimeError(msg)
    said: list[str] = []
    limit = Limit(meter)

    def heard(ev: Any) -> None:  # noqa: ANN401 - an SDK event
        d = as_dict(ev)
        if d.get("type") == "assistant.message" and (text := (d.get("data") or {}).get("content")):
            said.append(text)
        limit.heard(ev)

    client, session, sid = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path())), None, ""
    confirmed = False
    spent = spotter_look.Spent(uuid.uuid4().hex, spend_ledger.where(), meter, role.model, agent="retro-review", job="")
    try:
        await client.start()
        effort = role.effort if role.effort and await takes_effort(client, role.model) else None
        with tempfile.TemporaryDirectory(prefix="owlbear-retro-review-") as empty:
            session = await client.create_session(
                model=role.model, reasoning_effort=effort,
                context_tier="long_context" if role.context == "long" else None, available_tools=[], mcp_servers={},
                enable_config_discovery=False, included_builtin_skills=[], enable_file_hooks=False,
                skip_custom_instructions=True, working_directory=empty, on_event=heard,
                on_permission_request=lambda *_: PermissionDecisionReject(feedback="a review has no tools"),
            )  # fmt: skip
            sid = getattr(session, "session_id", "") or ""
            limit.part.started(sid)
            spent.started(sid)
            started = {"event": "started", "session": sid, "kind": "retro-review", "role": "retro-review", "job": "",
                       "worktree": empty}  # fmt: skip
            await spotter.offload(chatlogs.note, started)
            confirmed = await limit.turn(
                session.send_and_wait(message, timeout=SECONDS), partial(_abort, session), spotter.TEARDOWN
            )
    finally:
        await spotter.through(asyncio.ensure_future(_end(client, session, limit, spent, confirmed=confirmed)))
    return said[-1] if said else ""


async def _end(
    client: Any, session: Any, limit: Limit, spent: spotter_look.Spent, *, confirmed: bool,  # noqa: ANN401
) -> None:  # fmt: skip
    """Reconcile the session's share with its reported total, record its run, then tear it down; each bounded."""
    if session is None:
        limit.part.ended(0.0, confirmed=True)  # no session, no turn: nothing was billed
    else:
        await limit.settle(partial(spent.metrics, session), confirmed=confirmed, bound=spotter.TEARDOWN)
    spent.ended(limit.part, confirmed=confirmed)
    await spotter_look.teardown(client, session, spent.sid)


async def _abort(session: Any) -> None:  # noqa: ANN401 - the SDK session
    await session.abort()
