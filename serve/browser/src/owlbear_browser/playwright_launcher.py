"""Playwright-based browser launcher with Microsoft SSO extension support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Self

from playwright.async_api import async_playwright

from owlbear_browser._errors import SSOExtensionNotFoundError
from owlbear_browser.fetcher import BrowserContentFetcher

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

    from owlbear_browser.contract import AcquisitionRequest, AcquisitionResult

__all__ = [
    "AuthenticationCapabilities",
    "PlaywrightLauncher",
    "SSOExtensionNotFoundError",
    "build_playwright_args",
    "find_sso_extension",
]

_SSO_EXT_ID = "ppnbnpeolgkicgegkbkbjmhlideopiji"
_EXT_REL = Path("Google") / "Chrome" / "User Data" / "Default" / "Extensions" / _SSO_EXT_ID


@dataclass(frozen=True, slots=True)
class AuthenticationCapabilities:
    """Authentication integrations available to the launched browser."""

    persistent_session: bool
    visible_manual_auth: bool
    microsoft_sso: bool


def find_sso_extension() -> Path:
    """Locate the Microsoft SSO extension path.

    Checks ``SSO_EXTENSION_PATH`` env var first (must point to an existing
    directory).  Falls back to the versioned subfolder under
    ``%LOCALAPPDATA%/Google/Chrome/User Data/Default/Extensions/{_SSO_EXT_ID}``.

    Returns:
        Path to the versioned extension directory.

    Raises:
        SSOExtensionNotFoundError: When the extension cannot be found or the
            env-var path does not exist.
    """
    override = os.environ.get("SSO_EXTENSION_PATH")
    if override is not None:
        p = Path(override)
        if not p.exists():
            msg = f"SSO_EXTENSION_PATH points to a non-existent path: {override}"
            raise SSOExtensionNotFoundError(msg)
        return p

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    ext_root = Path(local_appdata) / _EXT_REL
    if not ext_root.exists():
        msg = f"SSO extension directory not found: {ext_root}"
        raise SSOExtensionNotFoundError(msg)

    version_dirs = [d for d in ext_root.iterdir() if d.is_dir()]
    if not version_dirs:
        msg = f"No version subfolders found in SSO extension directory: {ext_root}"
        raise SSOExtensionNotFoundError(msg)

    return version_dirs[0]


def build_playwright_args(sso_ext_path: Path) -> list[str]:
    """Build Playwright Chromium launch args that load the SSO extension.

    Args:
        sso_ext_path: Path to the versioned SSO extension directory.

    Returns:
        List of ``--flag=value`` strings for ``launch_persistent_context``.
    """
    return [
        f"--disable-extensions-except={sso_ext_path}",
        f"--load-extension={sso_ext_path}",
    ]


class PlaywrightLauncher:
    """Async context manager that launches Chromium with the SSO extension.

    Args:
        sso_ext_path: Path to the versioned SSO extension directory.  If
            ``None`` (the default), the path is auto-discovered via
            :func:`find_sso_extension` at :meth:`launch` time.
        user_data_dir: Path to the persistent Chromium profile directory.
    """

    def __init__(
        self,
        sso_ext_path: Path | None = None,
        user_data_dir: str = "",
        max_pending_pages: int = 1,
        *,
        headless: bool = False,
    ) -> None:
        self._sso_ext_path = sso_ext_path
        self._user_data_dir = user_data_dir or str(Path.home() / ".owlbear" / "browser-profile")
        if max_pending_pages < 1:
            msg = "max_pending_pages must be at least 1"
            raise ValueError(msg)
        self._max_pending_pages = max_pending_pages
        self._headless = headless
        self._context: BrowserContext | None = None
        self._fetcher: BrowserContentFetcher | None = None
        self._pw = None
        self._capabilities = AuthenticationCapabilities(
            persistent_session=False,
            visible_manual_auth=False,
            microsoft_sso=False,
        )

    @property
    def capabilities(self) -> AuthenticationCapabilities:
        """Return authentication capabilities detected at launch."""
        return self._capabilities

    async def launch(self) -> None:
        """Launch Chromium with the SSO extension and open a persistent context."""
        sso_ext_path = self._sso_ext_path
        if sso_ext_path is None:
            try:
                sso_ext_path = find_sso_extension()
            except SSOExtensionNotFoundError:
                sso_ext_path = None
        cm = async_playwright()
        self._pw = await cm.__aenter__()
        args = build_playwright_args(sso_ext_path) if sso_ext_path is not None else []
        try:
            self._context = await self._pw.chromium.launch_persistent_context(
                self._user_data_dir,  # type: ignore[arg-type]
                headless=self._headless,
                args=args,
            )
        except Exception:
            await self._pw.stop()
            self._pw = None
            raise
        self._capabilities = AuthenticationCapabilities(
            persistent_session=True,
            visible_manual_auth=not self._headless,
            microsoft_sso=sso_ext_path is not None,
        )

        self._fetcher = BrowserContentFetcher(self._context)

    async def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        """Acquire content through the launcher's public browser capability."""
        if self._fetcher is None:
            msg = "Launcher not started — call launch() first"
            raise RuntimeError(msg)
        return await self._fetcher.acquire(request)

    async def page(self) -> Page:
        """Return the first page from the persistent context."""
        if self._context is None:
            msg = "Launcher not started — call launch() first"
            raise RuntimeError(msg)
        if not self._context.pages:
            return await self._context.new_page()
        return self._context.pages[0]

    async def close(self) -> None:
        """Close the persistent context and stop the Playwright instance."""
        fetcher = self._fetcher
        context = self._context
        playwright = self._pw
        self._fetcher = None
        self._context = None
        self._pw = None
        self._capabilities = AuthenticationCapabilities(
            persistent_session=False,
            visible_manual_auth=False,
            microsoft_sso=False,
        )
        first_error: Exception | None = None
        if fetcher is not None:
            try:
                await fetcher.close()
            except Exception as exc:  # noqa: BLE001 - later resources still require cleanup.
                first_error = exc
        if context is not None:
            try:
                await context.close()
            except Exception as exc:  # noqa: BLE001 - later resources still require cleanup.
                if first_error is None:
                    first_error = exc
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception as exc:  # noqa: BLE001 - preserve the first cleanup failure.
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    async def __aenter__(self) -> Self:
        await self.launch()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
