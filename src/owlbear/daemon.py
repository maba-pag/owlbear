"""Daemon lifecycle — PID file, logging, and async run loop.

Provides the building blocks for ``bearclaw run``:

- :class:`PidFile` — context manager that writes/removes ``owlbear.pid``
- :func:`setup_logging` — ``RotatingFileHandler`` + stderr ``StreamHandler``
- :func:`run_daemon` — async receive → turn → send loop with sentinel shutdown
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import random
import signal
import sys
from typing import TYPE_CHECKING, Self

import logfire
from pydantic_ai import Agent

from owlbear.core.errors import ErrorCategory, classify_error
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

# Transient retry constants
_TRANSIENT_MAX_RETRIES = 3
_TRANSIENT_BACKOFF_BASE = 1.0  # seconds
_TRANSIENT_BACKOFF_MAX = 30.0  # seconds
_JITTER_FACTOR = 0.5


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


async def _recover_from_error(
    exc: Exception,
    message: str,
    *,
    agent: OwlBearAgent,
    channel: ChannelPlugin,
    settings: OwlBearSettings | None,
) -> None:
    """Apply classified recovery strategy for a failed ``agent.turn()`` call.

    - **TRANSIENT**: exponential backoff with jitter, up to 3 retries.
    - **AUTH**: token refresh via :func:`create_copilot_model`, retry once.
    - **PERMANENT / TOOL_SEMANTIC / AUTH without settings**: log and send error.
    """
    category = classify_error(exc)

    if category is ErrorCategory.TRANSIENT:
        last_exc: Exception = exc
        for attempt in range(1, _TRANSIENT_MAX_RETRIES + 1):
            delay = min(
                _TRANSIENT_BACKOFF_BASE * (2 ** (attempt - 1)),
                _TRANSIENT_BACKOFF_MAX,
            )
            jitter = random.uniform(0, delay * _JITTER_FACTOR)  # noqa: S311
            await asyncio.sleep(delay + jitter)
            try:
                response = await agent.turn(message)
                await channel.send(response)
            except Exception as retry_exc:  # noqa: BLE001
                last_exc = retry_exc
                logger.warning(
                    "Transient retry %d/%d failed: %s",
                    attempt,
                    _TRANSIENT_MAX_RETRIES,
                    retry_exc,
                )
            else:
                return
        logger.exception("Transient retries exhausted", exc_info=last_exc)
        await channel.send(f"Error: {last_exc}")

    elif category is ErrorCategory.AUTH and settings is not None:
        try:
            new_model = await create_copilot_model(settings)
            agent.update_model(new_model)
            response = await agent.turn(message)
            await channel.send(response)
        except Exception as retry_exc:
            logger.exception("Token refresh/retry failed")
            await channel.send(f"Error: {retry_exc}")

    else:  # PERMANENT, TOOL_SEMANTIC, or AUTH without settings
        logger.exception("Error processing message")
        await channel.send(f"Error: {exc}")


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
            except Exception as exc:  # noqa: BLE001
                await _recover_from_error(
                    exc, message, agent=agent, channel=channel, settings=settings,
                )

    finally:
        # Restore previous signal handlers
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)

        # Clean up sentinel file
        sentinel.unlink(missing_ok=True)

        logger.info("Daemon stopped")
