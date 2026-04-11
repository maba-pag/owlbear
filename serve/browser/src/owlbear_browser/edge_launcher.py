"""High-level Edge CDP launcher — launch, connect, and close an Edge browser session."""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_browser.launcher import build_launch_args, find_edge_binary

if TYPE_CHECKING:
    from owlbear_browser.cdp import CDPConnectionManager

__all__ = ["EdgeCDPLauncher"]

_DEFAULT_PORT = 9222


class EdgeCDPLauncher:
    """High-level launcher that manages an Edge subprocess and CDP connection.

    Args:
        binary_path: Path to the Edge binary.  If ``None``, resolved via
            :func:`~owlbear_browser.launcher.find_edge_binary`.
        port: Remote debugging port (default 9222).
        user_data_dir: Optional Edge user-data directory path.
    """

    def __init__(
        self,
        binary_path: str | Path | None = None,
        port: int = _DEFAULT_PORT,
        user_data_dir: str = "",
    ) -> None:
        self._binary_path: Path | None = Path(binary_path) if binary_path is not None else None
        self._port = port
        self._user_data_dir = user_data_dir
        self._process: subprocess.Popen[bytes] | None = None
        self._manager: CDPConnectionManager | None = None

    async def launch(self) -> None:
        """Launch an Edge subprocess with CDP enabled.

        Raises:
            FileNotFoundError: When *binary_path* does not resolve to an existing file.
            EdgeNotFoundError: When no Edge binary can be found (no *binary_path* given).
            OSError: When the subprocess fails to start.
        """
        if self._binary_path is not None:
            if not self._binary_path.exists():
                msg = f"Edge binary not found: {self._binary_path}"
                raise FileNotFoundError(msg)
            binary = self._binary_path
        else:
            binary = find_edge_binary()

        args = build_launch_args(port=self._port, user_data_dir=self._user_data_dir)
        cmd = [str(binary), *args]
        self._process = subprocess.Popen(cmd)  # noqa: S603,ASYNC220

        from owlbear_browser.cdp import CDPConnectionManager  # noqa: PLC0415

        self._manager = CDPConnectionManager(port=self._port, process=self._process)

    async def connect(self) -> None:
        """Connect to Edge over CDP.

        If :meth:`launch` was called first, this establishes the CDP WebSocket
        connection to the running Edge instance.
        """
        if self._manager is not None:
            await self._manager.connect()

    async def close(self) -> None:
        """Close the CDP connection and terminate the Edge subprocess.

        Safe to call even when :meth:`launch` has not been called or has
        already completed its cleanup.
        """
        if self._manager is not None:
            await self._manager.disconnect()
            self._manager = None
        if self._process is not None:
            with contextlib.suppress(OSError):
                self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except OSError:
                pass
            self._process = None
