"""Copilot device-flow OAuth and token management for LLMExtractor.

Implements the GitHub device-flow (RFC 8628) to obtain a short-lived Copilot
JWT, with file-based caching at ~/.owlbear/copilot_token.json.
"""

from __future__ import annotations

import asyncio
import json
import ssl
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL = "https://github.com/login/device/code"
_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105
_COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"  # noqa: S105
DEFAULT_COPILOT_BASE = "https://api.individual.githubcopilot.com"

_DEFAULT_TOKEN_PATH = Path.home() / ".owlbear" / "copilot_token.json"
_EXPIRY_MARGIN = 60  # seconds

_EDITOR_HEADERS = {
    "Editor-Version": "vscode/1.97.1",
    "Editor-Plugin-Version": "copilot-chat/0.27.3",
    "User-Agent": "GitHubCopilotChat/0.27.3",
    "X-Github-Api-Version": "2025-04-01",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _ssl_context() -> ssl.SSLContext:
    try:
        import truststore  # noqa: PLC0415

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def _http_client() -> object:
    """Return an httpx.AsyncClient configured for Copilot requests."""
    import httpx  # noqa: PLC0415

    return httpx.AsyncClient(verify=_ssl_context(), headers=_EDITOR_HEADERS)


def _find_vscode_version() -> str:
    """Return the installed VS Code version string (e.g. '1.97.1')."""
    import subprocess  # noqa: PLC0415

    result = subprocess.run(
        ["code", "--version"],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    lines = result.stdout.strip().splitlines()
    if not lines:
        msg = "No output from 'code --version'"
        raise ValueError(msg)
    return lines[0]


def detect_editor_versions() -> dict[str, str]:
    """Return editor header dict using dynamically detected VS Code version.

    Falls back to static defaults on any OS or parse error.
    """
    try:
        version = _find_vscode_version()
        headers = dict(_EDITOR_HEADERS)
        headers["Editor-Version"] = f"vscode/{version}"
    except Exception:  # noqa: BLE001
        return dict(_EDITOR_HEADERS)
    else:
        return headers


# ---------------------------------------------------------------------------
# Device-flow OAuth
# ---------------------------------------------------------------------------


async def request_device_code() -> dict[str, Any]:
    """POST to the GitHub device-flow endpoint and return the response dict."""
    async with _http_client() as client:
        resp = await client.post(
            DEVICE_CODE_URL,
            data={"client_id": COPILOT_CLIENT_ID, "scope": "read:user"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    sys.stderr.write(f"Open https://github.com/login/device and enter code: {data.get('user_code')}\n")
    return data


async def poll_for_access_token(
    device_code: str,
    interval: float = 5,
    timeout: float = 900.0,  # noqa: ASYNC109
) -> str:
    """Poll GitHub until the user authorises the device flow.

    Handles ``authorization_pending`` (sleep and retry) and ``slow_down``
    (increase interval by 5).  Raises ``TimeoutError`` when *timeout* elapses.
    """
    deadline = time.monotonic() + timeout
    while True:
        if time.monotonic() >= deadline:
            msg = "Device flow timed out waiting for user authorisation"
            raise TimeoutError(msg)
        async with _http_client() as client:
            resp = await client.post(
                _ACCESS_TOKEN_URL,
                data={
                    "client_id": COPILOT_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        error = data.get("error")
        if error == "authorization_pending":
            await asyncio.sleep(interval)
        elif error == "slow_down":
            interval += 5
            await asyncio.sleep(interval)
        elif error:
            msg = f"OAuth error: {error}"
            raise RuntimeError(msg)
        else:
            return data["access_token"]


async def exchange_for_copilot_token(access_token: str) -> dict[str, Any]:
    """Exchange a GitHub OAuth access token for a short-lived Copilot JWT."""
    async with _http_client() as client:
        resp = await client.get(
            _COPILOT_TOKEN_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Token URL derivation
# ---------------------------------------------------------------------------


def derive_base_url(token: str) -> str:
    """Extract the API base URL from the Copilot token's ``proxy-ep`` field.

    Converts ``proxy.<host>`` to ``api.<host>``.  Returns
    :data:`DEFAULT_COPILOT_BASE` when the field is absent or the token is empty.
    """
    for part in token.split(";"):
        if part.startswith("proxy-ep="):
            proxy_host = part.split("=", 1)[1]
            api_host = proxy_host.replace("proxy.", "api.", 1)
            return f"https://{api_host}"
    return DEFAULT_COPILOT_BASE


# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------


def save_token(token_data: dict[str, Any], path: Path | None = None) -> None:
    """Write *token_data* as JSON to *path* (default: ``~/.owlbear/copilot_token.json``)."""
    p = path or _DEFAULT_TOKEN_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(token_data))
    p.chmod(0o600)


def load_token(path: Path | None = None) -> dict[str, Any] | None:
    """Load a cached Copilot token.

    Returns ``None`` when the file is missing, contains invalid JSON, or the
    token expires within :data:`_EXPIRY_MARGIN` seconds.
    """
    p = path or _DEFAULT_TOKEN_PATH
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, ValueError):
        return None
    else:
        if data.get("expires_at", 0) <= time.time() + _EXPIRY_MARGIN:
            return None
        return data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def get_copilot_token(token_path: Path | None = None) -> str:
    """Return a valid Copilot JWT, using the cache when possible.

    On a cache miss the full device-flow is executed and the result is saved.
    Raises :class:`TimeoutError` if the user does not complete authorisation.
    """
    cached = load_token(path=token_path)
    if cached:
        return cached["token"]
    device_data = await request_device_code()
    access_token = await poll_for_access_token(
        device_data["device_code"],
        interval=device_data.get("interval", 5),
        timeout=device_data.get("expires_in", 900.0),
    )
    copilot_data = await exchange_for_copilot_token(access_token)
    save_token(copilot_data, path=token_path)
    return copilot_data["token"]
