"""Daemon lifecycle — PID file, logging, and async run loop.

Provides the building blocks for ``bearclaw run``:

- :class:`PidFile` — context manager that writes/removes ``owlbear.pid``
- :func:`setup_logging` — ``RotatingFileHandler`` + stderr ``StreamHandler``
- :func:`run_daemon` — async receive → turn → send loop with sentinel shutdown
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import signal
import sys
from typing import TYPE_CHECKING, Self

import httpx
import logfire
import openai
from pydantic_ai import Agent

from owlbear.providers.copilot import create_copilot_model

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import FrameType

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.core.agent import OwlBearAgent

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3


def _is_auth_error(exc: Exception) -> bool:
    """Return True if *exc* is an authentication/authorization error.

    Detects ``httpx.HTTPStatusError`` with status 401 or 403,
    ``openai.AuthenticationError``, and ``openai.PermissionDeniedError``.
    """
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403):
        return True
    return isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError))


def _is_process_alive(pid: int) -> bool:
    """Check whether *pid* refers to a running process (cross-platform)."""
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    else:
        return True


# ---------------------------------------------------------------------------
# PidFile context manager
# ---------------------------------------------------------------------------


class PidFile:
    """Context manager that writes the current PID on enter and removes it on exit.

    On enter, if the PID file already exists:

    - **Stale** (process dead): the file is removed and re-created.
    - **Alive** (process running): :exc:`RuntimeError` is raised.

    Parameters
    ----------
    path:
        Absolute path to the PID file (e.g. ``config_dir / "owlbear.pid"``).
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self) -> Self:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if self._path.exists():
            existing_pid = int(self._path.read_text().strip())
            if _is_process_alive(existing_pid):
                msg = (
                    f"OwlBear daemon already running (PID {existing_pid}). "
                    "Stop it first with `bearclaw stop`."
                )
                raise RuntimeError(msg)
            # Stale PID — remove and proceed
            logger.info("Removing stale PID file (PID %d no longer alive)", existing_pid)
            self._path.unlink()

        self._path.write_text(str(os.getpid()))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self._path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def setup_logging(log_file: Path) -> logging.Logger:
    """Configure the root logger with a rotating file handler and stderr output.

    Parameters
    ----------
    log_file:
        Path to the log file (e.g. ``config_dir / "owlbear.log"``).

    Returns
    -------
    logging.Logger
        The root logger, configured with both handlers.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    return root


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------

# Module-level shutdown flag set by signal handlers
_shutdown: bool = False


def _make_signal_handler() -> Callable[[int, FrameType | None], None]:
    """Return a signal handler that sets the module-level shutdown flag."""

    def _handler(signum: int, frame: FrameType | None) -> None:  # noqa: ARG001
        global _shutdown  # noqa: PLW0603
        logger.info("Received signal %s — shutting down", signum)
        _shutdown = True

    return _handler


def configure_otel(otel_endpoint: str) -> None:
    """Configure the Logfire SDK to export spans to an OTLP endpoint.

    Sets ``OTEL_EXPORTER_OTLP_ENDPOINT`` in the process environment and
    calls :func:`logfire.configure` with ``send_to_logfire=False``.

    Parameters
    ----------
    otel_endpoint:
        The OTLP endpoint URL (e.g. ``http://localhost:4318``).
    """
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otel_endpoint
    logfire.configure(send_to_logfire=False, additional_span_processors=[])
    logger.info("OTel configured — exporting to %s", otel_endpoint)


async def run_daemon(
    *,
    channel: ChannelPlugin,
    agent: OwlBearAgent,
    config_dir: Path,
    settings: OwlBearSettings | None = None,
    otel_endpoint: str | None = None,
) -> None:
    """Run the daemon receive → turn → send loop.

    The loop exits when any of the following occurs:

    - The channel returns ``None`` (EOF / disconnect)
    - The sentinel file ``config_dir / "owlbear.stop"`` appears
    - A signal (SIGINT / SIGTERM) sets the shutdown flag

    Parameters
    ----------
    channel:
        The I/O channel to read from and write to.
    agent:
        The OwlBearAgent that processes each message.
    config_dir:
        Directory containing PID and sentinel files.
    settings:
        Optional application settings for downstream token refresh.
    otel_endpoint:
        Optional OTLP endpoint URL. When set, Logfire SDK is configured
        before instrumentation.
    """
    global _shutdown  # noqa: PLW0603
    _shutdown = False

    # --- Observability bootstrap ---
    if otel_endpoint:
        configure_otel(otel_endpoint)
    Agent.instrument_all()

    sentinel = config_dir / "owlbear.stop"

    # Install signal handlers (cross-platform — NOT loop.add_signal_handler)
    handler = _make_signal_handler()
    prev_sigint = signal.signal(signal.SIGINT, handler)
    prev_sigterm = signal.signal(signal.SIGTERM, handler)

    try:
        logger.info("Daemon started on channel '%s'", channel.name)

        while not _shutdown:
            # Check sentinel each iteration
            if sentinel.exists():
                logger.info("Sentinel file detected — shutting down")
                break

            message = await channel.receive()
            if message is None:
                logger.info("Channel returned None — shutting down")
                break

            # Re-check shutdown after potentially blocking receive
            if _shutdown:
                break

            if not message.strip():
                continue

            try:
                response = await agent.turn(message)
                await channel.send(response)
            except Exception as exc:
                if _is_auth_error(exc) and settings is not None:
                    try:
                        new_model = await create_copilot_model(settings)
                        agent.update_model(new_model)
                        response = await agent.turn(message)
                        await channel.send(response)
                    except Exception as retry_exc:
                        logger.exception("Token refresh/retry failed")
                        await channel.send(f"Error: {retry_exc}")
                else:
                    logger.exception("Error processing message")
                    await channel.send(f"Error: {exc}")

    finally:
        # Restore previous signal handlers
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)

        # Clean up sentinel file
        sentinel.unlink(missing_ok=True)

        logger.info("Daemon stopped")
