"""Playwright-based browser launcher with Microsoft SSO extension support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Self

from playwright.async_api import async_playwright

from owlbear_browser._errors import SSOExtensionNotFoundError

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

__all__ = [
    "PlaywrightLauncher",
    "SSOExtensionNotFoundError",
    "build_playwright_args",
    "find_sso_extension",
]

_SSO_EXT_ID = "ppnbnpeolgkicgegkbkbjmhlideopiji"
_EXT_REL = (
    Path("Google") / "Chrome" / "User Data" / "Default" / "Extensions" / _SSO_EXT_ID
)


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
    ) -> None:
        self._sso_ext_path = sso_ext_path
        self._user_data_dir = user_data_dir
        self._context: BrowserContext | None = None
        self._pw = None

    @property
    def context(self) -> BrowserContext | None:
        """Return the active BrowserContext, or None if not launched."""
        return self._context

    async def launch(self) -> None:
        """Launch Chromium with the SSO extension and open a persistent context."""
        sso_ext_path = (
            self._sso_ext_path
            if self._sso_ext_path is not None
            else find_sso_extension()
        )
        cm = async_playwright()
        self._pw = await cm.__aenter__()
        args = build_playwright_args(sso_ext_path)
        self._context = await self._pw.chromium.launch_persistent_context(
            self._user_data_dir,  # type: ignore[arg-type]
            headless=False,
            args=args,
        )

    async def close(self) -> None:
        """Close the persistent context and stop the Playwright instance."""
        if self._context is not None:
            await self._context.close()
        if self._pw is not None:
            self._pw.stop()

    async def __aenter__(self) -> Self:
        await self.launch()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    @property
    def page(self) -> Page:
        """Return the first page from the persistent context."""
        if self._context is None:
            msg = "Launcher not started — call launch() first"
            raise RuntimeError(msg)
        return self._context.pages[0]
