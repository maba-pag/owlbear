"""What one SDK session billed, read at the step's start and end: the input of the model check (TD-32, TD-53, TD-54)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from copilot.session import CopilotSession

READ = 10.0  # seconds for one usage request
USAGE_PAUSE = 2.0  # seconds before the one repeated usage read (TD-54)


def unexpected_models(
    before: dict[str, Any], after: dict[str, Any], model: str | None, subagents: set[str]
) -> list[str]:
    """Models billed during this invocation that are neither the step's nor a logged subagent's.

    An unknown baseline (a failed read on resume) or a failed final read checks nothing; the events still do.
    """
    if "error" in before or "error" in after:
        return []
    old, new = before.get("models") or {}, after.get("models") or {}
    grew = {m for m, v in new.items() if m not in old or (v or {}).get("tokens") != (old[m] or {}).get("tokens")}
    return sorted(grew - {model} - subagents)


async def _usage(session: CopilotSession, requested: str | None) -> dict[str, Any]:
    try:
        m = await asyncio.wait_for(session.rpc.usage.get_metrics(), READ)
    except Exception as exc:  # noqa: BLE001 - experimental RPC; usage is reported, never required
        return {"error": type(exc).__name__}
    nano = getattr(m, "total_nano_aiu", None)
    models = {
        name: {
            "credits": (getattr(mm, "total_nano_aiu", None) or 0) / 1e9,
            "tokens": mm.usage.input_tokens + mm.usage.output_tokens,
        }
        for name, mm in (getattr(m, "model_metrics", None) or {}).items()
    }
    mismatch = bool(requested and models and requested not in models)
    return {"credits": None if nano is None else nano / 1e9, "models": models, "model_mismatch": mismatch}


async def usage_read(session: CopilotSession, requested: str | None) -> dict[str, Any]:
    """The usage, read once more after a pause when the first read fails (TD-54)."""
    usage = await _usage(session, requested)
    if "error" in usage:
        await asyncio.sleep(USAGE_PAUSE)
        usage = await _usage(session, requested)
    return usage


def unread(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Why the model check cannot run for this invocation; empty when both reads it needs worked (TD-54)."""
    if "error" in before:
        return f"the usage before the resumed turn could not be read ({before['error']})"
    if "error" in after:
        return f"the usage at the step's end could not be read ({after['error']})"
    return ""
