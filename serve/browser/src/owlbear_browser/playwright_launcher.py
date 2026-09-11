"""Playwright-based browser launcher for managed Edge and Chromium."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Self

from playwright.async_api import async_playwright

from owlbear_browser._errors import (
    ManagedEdgeUnavailableError,
    ManagedProfileInUseError,
    SSOExtensionNotFoundError,
)
from owlbear_browser.fetcher import BrowserContentFetcher

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

    from owlbear_browser.contract import AcquisitionRequest, AcquisitionResult

__all__ = [
    "AuthenticationCapabilities",
    "BrowserMode",
    "ManagedEdgeUnavailableError",
    "ManagedProfileInUseError",
    "PlaywrightLauncher",
    "SSOExtensionNotFoundError",
    "build_playwright_args",
    "find_sso_extension",
]

_SSO_EXT_ID = "ppnbnpeolgkicgegkbkbjmhlideopiji"
_EXT_REL = Path("Google") / "Chrome" / "User Data" / "Default" / "Extensions" / _SSO_EXT_ID


class BrowserMode(StrEnum):
    """Browser engine selected by resolved composition settings."""

    CHROMIUM = "chromium"
    MANAGED_EDGE = "managed-edge"


def _prefer_cleanup_error(
    current: BaseException | None,
    candidate: BaseException,
) -> BaseException:
    """Prefer later control-flow failures over ordinary cleanup errors."""
    if current is None or (isinstance(current, Exception) and not isinstance(candidate, Exception)):
        return candidate
    return current


@dataclass(frozen=True, slots=True)
class AuthenticationCapabilities:
    """Mechanical browser capabilities, without an authentication claim."""

    mode: BrowserMode
    owned_persistent_profile: bool
    visible_manual_auth: bool


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
    """Async context manager that launches a resolved browser mode.

    Args:
        sso_ext_path: Path to the versioned SSO extension directory.  If
            ``None`` (the default), the path is auto-discovered via
            :func:`find_sso_extension` at :meth:`launch` time.
        user_data_dir: Path to the persistent Chromium profile directory.
        mode: Resolved browser mode.
    """

    def __init__(
        self,
        sso_ext_path: Path | None = None,
        user_data_dir: str = "",
        max_pending_pages: int = 1,
        *,
        headless: bool = False,
        mode: BrowserMode | str = BrowserMode.CHROMIUM,
    ) -> None:
        self._sso_ext_path = sso_ext_path
        self._mode = BrowserMode(mode)
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
            mode=self._mode,
            owned_persistent_profile=False,
            visible_manual_auth=False,
        )

    @property
    def capabilities(self) -> AuthenticationCapabilities:
        """Return authentication capabilities detected at launch."""
        return self._capabilities

    async def launch(self) -> None:
        """Launch the resolved browser mode with an owned persistent context."""
        cm = async_playwright()
        self._pw = await cm.__aenter__()
        launch_kwargs: dict[str, object] = {"headless": self._headless}
        if self._mode is BrowserMode.MANAGED_EDGE:
            launch_kwargs.update(channel="msedge", chromium_sandbox=True, headless=False)
        else:
            sso_ext_path = self._sso_ext_path
            if sso_ext_path is None:
                try:
                    sso_ext_path = find_sso_extension()
                except SSOExtensionNotFoundError:
                    sso_ext_path = None
            launch_kwargs["args"] = build_playwright_args(sso_ext_path) if sso_ext_path else []
        try:
            self._context = await self._pw.chromium.launch_persistent_context(
                self._user_data_dir,  # type: ignore[arg-type]
                **launch_kwargs,
            )
        except Exception as exc:
            await self._pw.stop()
            self._pw = None
            if self._mode is BrowserMode.MANAGED_EDGE:
                message = str(exc).lower()
                if ("processsingleton" in message or "profile directory" in message) and "already in use" in message:
                    raise ManagedProfileInUseError from exc
                if "distribution 'msedge' is not found" in message or "executable doesn't exist" in message:
                    raise ManagedEdgeUnavailableError from exc
            raise
        self._capabilities = AuthenticationCapabilities(
            mode=self._mode,
            owned_persistent_profile=True,
            visible_manual_auth=not self._headless or self._mode is BrowserMode.MANAGED_EDGE,
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
            mode=self._mode,
            owned_persistent_profile=False,
            visible_manual_auth=False,
        )
        first_error: BaseException | None = None
        if fetcher is not None:
            try:
                await fetcher.close()
            except BaseException as exc:  # noqa: BLE001 - later resources still require cleanup.
                first_error = _prefer_cleanup_error(first_error, exc)
        if context is not None:
            try:
                await context.close()
            except BaseException as exc:  # noqa: BLE001 - later resources still require cleanup.
                first_error = _prefer_cleanup_error(first_error, exc)
        if playwright is not None:
            try:
                await playwright.stop()
            except BaseException as exc:  # noqa: BLE001 - preserve the first cleanup failure.
                first_error = _prefer_cleanup_error(first_error, exc)
        if first_error is not None:
            raise first_error

    async def __aenter__(self) -> Self:
        await self.launch()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
