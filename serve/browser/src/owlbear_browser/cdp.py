"""CDP connection manager and SSO redirect detection for Edge automation."""

from __future__ import annotations

import contextlib
import subprocess
from typing import TYPE_CHECKING, Any, Self

from owlbear_browser._errors import AuthenticationRequired, CDPConnectionError

if TYPE_CHECKING:
    import types

_DEFAULT_PORT = 9222

_IDP_DOMAINS: tuple[str, ...] = (
    "login.microsoftonline.com",
    "accounts.google.com",
    "login.okta.com",
    "login.windows.net",
)


async def playwright_connect_over_cdp(endpoint_url: str) -> Any:  # noqa: ANN401
    """Connect to a running browser instance over CDP at *endpoint_url*.

    This thin wrapper is defined at module level so tests can patch it
    without having Playwright installed. The real Playwright import is
    deferred to call time (lazy import).

    Args:
        endpoint_url: Full CDP WebSocket endpoint, e.g. ``http://127.0.0.1:9222``.

    Returns:
        A Playwright ``Browser`` object connected over CDP.
    """
    from playwright.async_api import async_playwright  # lazy — playwright optional at import time  # noqa: PLC0415

    p = await async_playwright().start()
    return await p.chromium.connect_over_cdp(endpoint_url)


class CDPConnectionManager:
    """Manages a long-lived CDP connection to a running Edge instance.

    Usage::

        manager = CDPConnectionManager(port=9222)
        await manager.connect()
        # ... interact with browser ...
        await manager.disconnect()

        # Or with a subprocess handle (returned by launch_edge):
        async with manager:
            pass  # subprocess is terminated on exit
    """

    def __init__(
        self,
        port: int = _DEFAULT_PORT,
        process: subprocess.Popen[bytes] | None = None,
    ) -> None:
        self._port = port
        self._process: subprocess.Popen[bytes] | None = process
        self._browser: Any = None
        self._is_connected: bool = False

    @property
    def is_connected(self) -> bool:
        """``True`` when a browser connection is currently active."""
        return self._is_connected

    async def __aenter__(self) -> Self:
        """Connect on entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Disconnect and terminate the Edge subprocess on exit."""
        await self.disconnect()
        if self._process is not None:
            with contextlib.suppress(OSError):
                self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(OSError):
                    self._process.kill()

    async def connect(self) -> None:
        """Connect to Edge over CDP on 127.0.0.1.

        Raises:
            CDPConnectionError: When the connection attempt times out.
        """
        endpoint_url = f"http://127.0.0.1:{self._port}"
        try:
            self._browser = await playwright_connect_over_cdp(endpoint_url)
        except TimeoutError as exc:
            msg = f"CDP connection timed out: {endpoint_url}"
            raise CDPConnectionError(msg) from exc
        self._is_connected = True

    async def disconnect(self) -> None:
        """Close the browser connection and mark the manager as disconnected."""
        if self._browser is not None:
            await self._browser.close()
        self._browser = None
        self._is_connected = False

    async def check_sso_redirect(self, page: Any) -> None:  # noqa: ANN401
        """Detect SSO redirects and login forms on *page*.

        Checks are performed in order:

        1. URL contains a known IdP domain (e.g. ``login.microsoftonline.com``).
        2. A ``input[type='password']`` element is present (login form).

        Raises:
            AuthenticationRequired: When an SSO redirect or login form is detected.
        """
        for domain in _IDP_DOMAINS:
            if domain in page.url:
                msg = f"SSO redirect detected: {page.url}"
                raise AuthenticationRequired(msg)

        login_field = page.query_selector("input[type='password']")
        if login_field is not None:
            msg = "Login form detected on page"
            raise AuthenticationRequired(msg)
