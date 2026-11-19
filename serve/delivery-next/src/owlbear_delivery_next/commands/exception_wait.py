"""Short HTTP waits for the chat's exception judge, never a long-running MCP call."""

from __future__ import annotations

import time
import urllib.parse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from owlbear_delivery_next.commands.chat_client import Chat

OK = 200
WAIT, POLL = 70.0, 5.0


def start(chat: Chat, path: str, base: str, proposed: list[dict] | None) -> dict[str, Any]:
    """Start once, then read the id until the answer or the tool's wait ends."""
    deadline = time.monotonic() + WAIT
    code, out = chat.call("POST", "/chat/exceptions", {"path": path, "base": base, "proposed": proposed})
    if code != OK:
        return {"failed": why(code, out)}
    return read(chat, out["run_id"], deadline)


def read(chat: Chat, run_id: str, deadline: float | None = None) -> dict[str, Any]:
    """Return the whole answer, whole failure, or the id to await again."""
    deadline = time.monotonic() + WAIT if deadline is None else deadline
    while True:
        code, now = chat.call("GET", f"/chat/exceptions/{urllib.parse.quote(run_id, safe='')}")
        if code == OK and not now.get("running"):
            return now["answer"]
        if code not in {OK, 503}:
            return {"failed": why(code, now)}
        if time.monotonic() >= deadline:
            out = {"running": True, "run_id": run_id, "next": "Call await_exceptions with this run_id at once."}
            return out | ({"error": why(code, now)} if code != OK else {})
        time.sleep(POLL)


def why(code: int, out: dict[str, Any]) -> str:
    """A validation answer names the first field to fix, without losing the host's reason."""
    detail = out.get("detail") or out.get("error") or out.get("failed")
    if isinstance(detail, list) and detail:
        first = detail[0]
        return f"{'.'.join(map(str, first['loc']))}: {first['msg']}"
    return str(detail or f"the host answered {code}")
