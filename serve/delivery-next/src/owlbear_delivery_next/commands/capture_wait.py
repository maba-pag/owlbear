"""await_capture (chat contract 7): the shaping chat waits for its draft's capture of the target's current pages.

The capture runs once a UI draft with states and a recipe is saved (D-01M61V2GR0C6JV2R6KJ0WR4PNB). The wait is only
read, like await_challenge's, and ends well inside the Copilot client's 180 s cut of a tool call.
"""

from __future__ import annotations

import time
import urllib.parse
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.project_host import api

if TYPE_CHECKING:
    from owlbear_delivery_next.commands.chat_client import Chat

POLL = 5.0  # seconds between reads
STILL = "the capture still runs: call await_capture again at once"
_pause = time.sleep


def wait(chat: Chat, change: str, deadline: float) -> dict[str, Any]:
    """Read the draft's capture until it has ended, a read fails, or *deadline*; then what the chat reads."""
    code, rows = chat.call("GET", "/changes")
    if code != HTTPStatus.OK:
        return {"error": rows.get("error") or rows.get("detail")}
    slug = next((r.get("slug") for r in rows if r.get("handle") == change), None)
    if slug is None:
        return {"error": f"change: {change} is not a Change here - use a handle from show_status"}
    while True:
        code, now = chat.call("GET", f"/chat/capture/{urllib.parse.quote(slug)}")
        ended = code == HTTPStatus.OK and not now.get("running")
        if ended or code not in {HTTPStatus.OK, HTTPStatus.SERVICE_UNAVAILABLE} or time.monotonic() >= deadline:
            break
        _pause(POLL)  # 503: the host is handing over
    if code != HTTPStatus.OK:
        return {"error": now.get("error") or now.get("detail"), "next": STILL}
    if now.get("running"):
        return {"running": True, "version": now.get("version"), "next": STILL}
    return now | {"changes_page": api.link(chat.record())}
