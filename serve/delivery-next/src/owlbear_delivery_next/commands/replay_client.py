"""The CLI's calibration replay: the running host's managed job runs it, never this process."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.project_host import host

TIMEOUT = 3600.0  # the replay judges every decided round through the SDK, which takes a while
UNKNOWN = "the host's answer was lost, so the replay may have run: check the Impeccable page before starting it again"
CUT = (OSError, ValueError, http.client.HTTPException)
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy


def replay() -> tuple[bool, str]:
    """Replay OwlBear's decided rounds on the machine host."""
    rec = host.running_at(local_home.root())
    if rec is None or not rec.token:
        return False, "the OwlBear machine host is not running; start it with `owlbear start`"
    try:
        out = _post(f"{rec.url}api/next/impeccable/replay", rec.token)
    except urllib.error.HTTPError as exc:
        return False, _refused(exc)
    except CUT as exc:
        return False, f"{UNKNOWN} ({exc})"
    return bool(out.get("ok")), str(out.get("report", ""))


def _post(url: str, token: str) -> dict:
    """The host's answer to an empty POST at *url*."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-OwlBear-Use": "cli"}
    request = urllib.request.Request(url, data=b"{}", method="POST", headers=headers)  # noqa: S310 - loopback
    with _LOCAL.open(request, timeout=TIMEOUT) as response:
        return json.load(response)


def _refused(exc: urllib.error.HTTPError) -> str:
    """What the host said it refused, or that its answer to a started replay was lost."""
    try:
        out = json.load(exc)
    except CUT:
        out = {}
    said = str(out.get("detail") or f"the host answered {exc.code}")
    return f"{UNKNOWN} ({said})" if exc.code >= 500 and exc.code != 503 else said  # noqa: PLR2004 - HTTP status
