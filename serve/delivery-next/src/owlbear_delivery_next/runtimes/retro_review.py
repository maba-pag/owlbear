"""One ``retro-review`` session for the Spotter cases (Improvement design §4, §6): tool-less, within its meter.

It checks a candidate's card against its call, or minimises and sanitises a case for publication. Like a look, it runs
in an empty folder without the project's or the user's configuration, noted in the chatlogs manifest so it is never
taken for a chat, and its teardown is bounded.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import TYPE_CHECKING, Any

from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionReject

from owlbear_delivery_next.improvement import spotter
from owlbear_delivery_next.improvement.events import as_dict
from owlbear_delivery_next.runtimes import chatlogs, spotter_look
from owlbear_delivery_next.runtimes.copilot_cli import cli_path
from owlbear_delivery_next.runtimes.model_choices import takes_effort

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.improvement.credits import Meter

SECONDS = 180.0  # an answer's deadline


async def asked(message: str, meter: Meter, role: RoleModel) -> str:
    """The session's last answer to *message*; its spend charged to *meter* (None: unknown, which closes it).

    Raises:
        RuntimeError: *meter* has no credits left, so the session never starts.
    """
    if not meter.open():
        raise RuntimeError(meter.report()["stopped"] or "no credits left for this review")
    said: list[str] = []

    def heard(ev: Any) -> None:  # noqa: ANN401 - an SDK event
        d = as_dict(ev)
        if d.get("type") == "assistant.message" and (text := (d.get("data") or {}).get("content")):
            said.append(text)

    client, session, sid, nano = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path())), None, "", None
    try:
        await client.start()
        effort = role.effort if role.effort and await takes_effort(client, role.model) else None
        with tempfile.TemporaryDirectory(prefix="owlbear-retro-review-") as empty:
            session = await client.create_session(
                model=role.model,
                reasoning_effort=effort,
                context_tier="long_context" if role.context == "long" else None,
                available_tools=[],
                mcp_servers={},
                enable_config_discovery=False,
                included_builtin_skills=[],
                enable_file_hooks=False,
                skip_custom_instructions=True,
                working_directory=empty,
                on_event=heard,
                on_permission_request=lambda *_: PermissionDecisionReject(feedback="a review has no tools"),
            )
            sid = getattr(session, "session_id", "") or ""
            started = {
                "event": "started",
                "session": sid,
                "kind": "retro-review",
                "role": "retro-review",
                "job": "",
                "worktree": empty,
            }
            await spotter.offload(chatlogs.note, started)
            await session.send_and_wait(message, timeout=SECONDS)
            try:
                nano = getattr(await session.rpc.usage.get_metrics(), "total_nano_aiu", None)
            except Exception:  # noqa: BLE001 - an unread usage is unknown spend
                nano = None
    finally:
        # STAND-IN until feat/run-credit-limits: its Limit charges each usage event and stops the session at the limit
        meter.charge(nano / 1e9 if nano is not None else None)
        await spotter.through(asyncio.ensure_future(spotter_look.teardown(client, session, sid)))
    return said[-1] if said else ""
