"""Copilot OAuth device-flow authentication.

Implements the GitHub device-flow OAuth for VS Code Copilot access:

1. ``request_device_code()`` — start the device flow
2. ``poll_for_access_token()`` — poll until user authorizes
3. ``exchange_for_copilot_token()`` — swap GitHub token for Copilot session token
4. ``derive_base_url()`` — parse API endpoint from token
5. ``load_or_refresh_token()`` — convenience: load cached or run full flow

Uses httpx for HTTP and truststore for system SSL certificates.
"""

from __future__ import annotations

import asyncio
import json
import ssl
import time
from pathlib import Path
from typing import Any

import httpx
import truststore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
"""VS Code OAuth app client ID (public, not a secret)."""

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"  # noqa: S105
DEFAULT_COPILOT_BASE = "https://api.individual.githubcopilot.com"

_DEFAULT_TOKEN_PATH = Path.home() / ".owlbear" / "copilot_token.json"

_EDITOR_HEADERS: dict[str, str] = {
    "Editor-Version": "vscode/1.99.0",
    "Editor-Plugin-Version": "copilot-chat/0.25.2025012401",
    "User-Agent": "GitHubCopilotChat/0.25.2025012401",
    "X-Github-Api-Version": "2025-01-21",
}
"""Required editor headers — GitHub returns 403 without them."""

_TOKEN_EXPIRY_MARGIN = 60
"""Seconds before actual expiry to consider a token stale."""


# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------


def _ssl_context() -> ssl.SSLContext:
    """Create an SSL context backed by the OS trust store."""
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


# ---------------------------------------------------------------------------
# Device-flow functions
# ---------------------------------------------------------------------------


async def request_device_code() -> dict[str, Any]:
    """Start the device-flow by requesting a device code from GitHub.

    Returns a dict with keys: ``device_code``, ``user_code``,
    ``verification_uri``, ``expires_in``, ``interval``.
    """
    async with httpx.AsyncClient(verify=_ssl_context()) as client:
        resp = await client.post(
            DEVICE_CODE_URL,
            data={"client_id": COPILOT_CLIENT_ID, "scope": "read:user"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def poll_for_access_token(
    device_code: str,
    *,
    interval: int,
    expires_in: int,
) -> str:
    """Poll GitHub until the user authorizes the device code.

    Handles ``authorization_pending`` (retry) and ``slow_down``
    (increase interval by 5s). Raises ``TimeoutError`` if the
    device code expires before authorization.

    Returns the GitHub access token string.
    """
    start = time.time()
    async with httpx.AsyncClient(verify=_ssl_context()) as client:
        while time.time() - start < expires_in:
            resp = await client.post(
                ACCESS_TOKEN_URL,
                data={
                    "client_id": COPILOT_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            data = resp.json()

            error = data.get("error")
            if error == "authorization_pending":
                await asyncio.sleep(interval)
                continue
            if error == "slow_down":
                interval += 5
                await asyncio.sleep(interval)
                continue
            if "access_token" in data:
                return data["access_token"]

            msg = f"Unexpected OAuth error: {data}"
            raise RuntimeError(msg)

    msg = "Device code expired before authorization completed"
    raise TimeoutError(msg)


async def exchange_for_copilot_token(access_token: str) -> dict[str, Any]:
    """Exchange a GitHub access token for a Copilot session token.

    Calls ``/copilot_internal/v2/token`` and returns the full
    response dict (contains ``token`` and ``expires_at``).
    """
    async with httpx.AsyncClient(verify=_ssl_context()) as client:
        resp = await client.get(
            COPILOT_TOKEN_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                **_EDITOR_HEADERS,
            },
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Token parsing
# ---------------------------------------------------------------------------


def derive_base_url(token: str) -> str:
    """Parse ``proxy-ep`` from a Copilot token and derive the API base URL.

    The Copilot token is semicolon-delimited (e.g.
    ``tid=…;exp=…;proxy-ep=proxy.individual.githubcopilot.com``).
    This function finds the ``proxy-ep`` field and converts
    ``proxy.`` → ``api.`` in the hostname.

    Returns ``DEFAULT_COPILOT_BASE`` if ``proxy-ep`` is not present.
    """
    for part in token.split(";"):
        key_val = part.strip().split("=", 1)
        if len(key_val) == 2 and key_val[0].strip() == "proxy-ep":  # noqa: PLR2004
            host = key_val[1].strip()
            api_host = host.replace("proxy.", "api.", 1)
            return f"https://{api_host}"
    return DEFAULT_COPILOT_BASE


# ---------------------------------------------------------------------------
# Token caching
# ---------------------------------------------------------------------------


def save_token(token_data: dict[str, Any], path: Path | None = None) -> None:
    """Persist token data to a JSON file.

    Creates parent directories if they don't exist.
    """
    path = path or _DEFAULT_TOKEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token_data))


def load_token(path: Path | None = None) -> dict[str, Any] | None:
    """Load a cached token from disk.

    Returns ``None`` if the file is missing or the token has expired
    (with a 60-second safety margin).
    """
    path = path or _DEFAULT_TOKEN_PATH
    if not path.exists():
        return None

    data: dict[str, Any] = json.loads(path.read_text())
    expires_at = data.get("expires_at", 0)

    if expires_at - time.time() <= _TOKEN_EXPIRY_MARGIN:
        return None

    return data


# ---------------------------------------------------------------------------
# Convenience: load-or-refresh
# ---------------------------------------------------------------------------


async def load_or_refresh_token(path: Path | None = None) -> str:
    """Return a valid Copilot token, loading from cache or running the full flow.

    If a cached token exists and is still valid (beyond the 60-second
    safety margin), it is returned immediately. Otherwise the full
    device-flow OAuth sequence is executed and the new token is cached.
    """
    path = path or _DEFAULT_TOKEN_PATH

    cached = load_token(path)
    if cached is not None:
        return cached["token"]

    # Full device-flow
    device = await request_device_code()
    print(  # noqa: T201
        f"\n→ Open {device['verification_uri']} and enter code: {device['user_code']}\n"
    )
    access_token = await poll_for_access_token(
        device["device_code"],
        interval=device["interval"],
        expires_in=device["expires_in"],
    )
    copilot_data = await exchange_for_copilot_token(access_token)
    save_token(copilot_data, path)
    return copilot_data["token"]
