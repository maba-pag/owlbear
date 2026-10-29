"""The CLI's calibration replay: the running host's managed job runs it, never this process."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.commands.chat_client import NOT_RUNNING, NOT_SERVED
from owlbear_delivery_next.project_host import host
from owlbear_delivery_next.state_store import project_home

if TYPE_CHECKING:
    from pathlib import Path

TIMEOUT = 3600.0  # the replay judges every decided round through the SDK, which takes a while
UNKNOWN = "the host's answer was lost, so the replay may have run: check the Impeccable page before starting it again"
CUT = (OSError, ValueError, http.client.HTTPException)
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy


def replay(repo: Path) -> tuple[bool, str]:
    """The calibration replay on the running host of *repo*'s project: (ok, its report or why it did not run)."""
    try:
        pid = project_home.clone_id(project_home.clone_dir(repo))
    except CUT:
        pid = None
    if pid is None:
        return False, NOT_SERVED.format(repo=repo)
    rec = host.running_at(project_home.home(pid), chat_contract.HostFound)
    if rec is None or not rec.token:
        return False, NOT_RUNNING.format(repo=repo)
    url = f"{rec.url}{f'p/{rec.project}/' if rec.project else ''}api/next/impeccable/replay"
    headers = {"Authorization": f"Bearer {rec.token}", "Content-Type": "application/json", "X-OwlBear-Use": "cli"}
    request = urllib.request.Request(url, data=b"{}", method="POST", headers=headers)  # noqa: S310 - loopback
    try:
        with _LOCAL.open(request, timeout=TIMEOUT) as response:
            out = json.load(response)
    except urllib.error.HTTPError as exc:
        return False, _refused(exc)
    except CUT as exc:
        return False, f"{UNKNOWN} ({exc})"
    return bool(out.get("ok")), str(out.get("report", ""))


def _refused(exc: urllib.error.HTTPError) -> str:
    """What the host said it refused, or that its answer to a started replay was lost."""
    try:
        out = json.load(exc)
    except CUT:
        out = {}
    said = str(out.get("detail") or f"the host answered {exc.code}")
    return f"{UNKNOWN} ({said})" if exc.code >= 500 and exc.code != 503 else said  # noqa: PLR2004 - HTTP status
