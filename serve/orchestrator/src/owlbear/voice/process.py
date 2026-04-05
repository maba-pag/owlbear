"""VoiceProcessManager — manages the voice addon subprocess lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Self

from owlbear.errors import OwlBearError
from owlbear.voice.protocol import ShutdownMsg, StatusMsg, out_adapter

if TYPE_CHECKING:
    from owlbear.voice.protocol import VoiceInMessage, VoiceOutMessage

__all__ = [
    "VoiceInitTimeout",
    "VoiceProcessError",
    "VoiceProcessManager",
    "VoiceRestartBudgetExhausted",
]

_log = logging.getLogger(__name__)

# Default init_timeout value — used as a sentinel so that processes
# spawned without an explicit timeout (e.g. in shutdown-sequence tests
# that mock asyncio.wait_for globally) still complete __aenter__ normally.
_DEFAULT_INIT_TIMEOUT: float = 30.0

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

_STREAMS_NONE = "subprocess streams are None"


class VoiceProcessError(OwlBearError):
    """Raised when the voice addon process encounters a fatal error."""


class VoiceInitTimeout(VoiceProcessError):
    """Raised when the voice addon does not send a ready message in time."""


class VoiceRestartBudgetExhausted(VoiceProcessError):
    """Raised when the restart budget has been exhausted."""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class VoiceProcessManager:
    """Manages the voice addon subprocess and NDJSON message exchange.

    Used as an async context manager; the subprocess is launched on entry
    and terminated on exit.
    """

    def __init__(
        self,
        command: list[str],
        *,
        init_timeout: float = _DEFAULT_INIT_TIMEOUT,
        shutdown_timeout: float = 5.0,
        kill_timeout: float = 2.0,
        max_restarts: int = 3,
    ) -> None:
        self._command = command
        self._init_timeout: float = init_timeout
        self._shutdown_timeout = shutdown_timeout
        self._kill_timeout = kill_timeout
        self._max_restarts = max_restarts

        self._proc: asyncio.subprocess.Process | None = None
        self._queue: asyncio.Queue[VoiceOutMessage] = asyncio.Queue()
        self._read_task: asyncio.Task[None] | None = None
        self._restart_count = 0
        self._shutting_down = False
        self._process_crashed = False
        self._fatal_error: BaseException | None = None

    # -- context manager ---------------------------------------------------

    async def __aenter__(self) -> Self:
        await self._spawn_and_handshake()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.shutdown()
        if self._fatal_error is not None:
            raise self._fatal_error

    # -- public API --------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        """True when the managed process is running."""
        if self._proc is None:
            return False
        return self._proc.returncode is None

    async def send(self, msg: VoiceInMessage) -> None:
        """Serialize and send *msg* to the voice addon over stdin."""
        if self._proc is None or self._proc.stdin is None:
            return
        payload = (msg.model_dump_json() + "\n").encode()
        self._proc.stdin.write(payload)
        try:
            await self._proc.stdin.drain()
        except BrokenPipeError:
            _log.warning("BrokenPipeError on send — scheduling restart")
            await self._handle_crash()
            raise
        # Yield so the read loop can process any pending I/O
        await asyncio.sleep(0)

    async def receive(self) -> VoiceOutMessage:
        """Return the next message from the internal queue."""
        return await self._queue.get()

    async def shutdown(self) -> None:
        """Gracefully shut down the voice addon process (6-phase)."""
        self._shutting_down = True

        # Cancel the read loop first
        if self._read_task is not None and not self._read_task.done():
            self._read_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._read_task
            self._read_task = None

        if self._proc is None:
            return

        proc = self._proc

        # Phase 1: send ShutdownMsg (skip if process already crashed)
        if proc.stdin is not None and not self._process_crashed:
            try:
                payload = (ShutdownMsg().model_dump_json() + "\n").encode()
                proc.stdin.write(payload)
                await proc.stdin.drain()
            except (BrokenPipeError, OSError, ConnectionResetError):
                pass  # skip to phase 2

        # Phases 2-6: close, wait, terminate, wait, kill
        await self._shutdown_phases_2_to_6(proc)

    # -- internal ----------------------------------------------------------

    async def _shutdown_phases_2_to_6(
        self, proc: asyncio.subprocess.Process
    ) -> None:
        """Execute shutdown phases 2-6 (close stdin, then kill)."""
        # Phase 2: close stdin
        if proc.stdin is not None:
            with contextlib.suppress(OSError):
                proc.stdin.close()

        # Phase 3: wait with shutdown_timeout
        try:
            await asyncio.wait_for(
                proc.wait(), timeout=self._shutdown_timeout
            )
        except TimeoutError:
            pass
        else:
            self._proc = None
            return

        # Phase 4: terminate
        with contextlib.suppress(ProcessLookupError):
            proc.terminate()

        # Phase 5: wait with kill_timeout
        try:
            await asyncio.wait_for(
                proc.wait(), timeout=self._kill_timeout
            )
        except TimeoutError:
            pass
        else:
            self._proc = None
            return

        # Phase 6: kill
        with contextlib.suppress(ProcessLookupError):
            proc.kill()

        self._proc = None

    async def _spawn_and_handshake(self) -> None:
        """Spawn the subprocess and wait for ready status."""
        # Cancel any existing read loop before starting a new one
        if self._read_task is not None and not self._read_task.done():
            current = asyncio.current_task()
            if self._read_task is not current:
                self._read_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._read_task
            self._read_task = None

        proc = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )
        if proc.stdin is None or proc.stdout is None:
            msg = _STREAMS_NONE
            raise RuntimeError(msg)

        self._proc = proc
        self._shutting_down = False

        # Read lines until ready or EOF
        while True:
            try:
                line = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=self._init_timeout
                )
            except TimeoutError as exc:
                proc.kill()
                timeout_msg = f"Voice addon did not send ready within {self._init_timeout}s"
                raise VoiceInitTimeout(timeout_msg) from exc
            if not line:
                proc.kill()
                timeout_msg = "Voice addon did not send ready (EOF received)"
                raise VoiceInitTimeout(timeout_msg)
            try:
                parsed = out_adapter.validate_json(line)
            except Exception:  # noqa: BLE001
                _log.warning("Malformed JSON during handshake: %s", line)
                continue
            if isinstance(parsed, StatusMsg) and parsed.state == "ready":
                break
            # Non-ready messages are queued
            self._queue.put_nowait(parsed)

        # Reset restart counter and crash flag on successful init
        self._restart_count = 0
        self._process_crashed = False

        # Start background read loop
        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Background task: read NDJSON from stdout and push to queue."""
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        while True:
            line = await proc.stdout.readline()
            if not line:
                # EOF — process crashed
                self._process_crashed = True
                if not self._shutting_down:
                    await self._handle_crash()
                return
            try:
                parsed = out_adapter.validate_json(line)
            except Exception:  # noqa: BLE001
                _log.warning("Malformed NDJSON line: %s", line)
                continue
            self._queue.put_nowait(parsed)

    async def _handle_crash(self) -> None:
        """Attempt restart or raise budget exhausted."""
        self._restart_count += 1
        if self._restart_count > self._max_restarts:
            budget_msg = f"Exceeded max restarts ({self._max_restarts})"
            exc = VoiceRestartBudgetExhausted(budget_msg)
            self._fatal_error = exc
            raise exc
        _log.info("Restarting voice addon (attempt %d)", self._restart_count)
        await self._spawn_and_handshake()

