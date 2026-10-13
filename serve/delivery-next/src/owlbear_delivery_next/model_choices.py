"""The models this machine's Copilot runtime offers, with their efforts and context windows, for the settings page."""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from typing import TYPE_CHECKING, Any, get_args

from copilot import CopilotClient, RuntimeConnection

from owlbear_delivery_next.models import Effort
from owlbear_delivery_next.sdk_adapter import cli_path

if TYPE_CHECKING:
    from copilot.client import ModelInfo

FRESH = 3600.0  # seconds one successful read is reused
WAIT = 30.0  # seconds one read may take, the runtime's start included
AUTO = "auto"  # the runtime's own choice: Delivery pins each role's model and checks the usage names it
EFFORTS = frozenset(get_args(Effort.__value__))


class Offered:
    """The last read of the offered models, shared by the settings page's requests; a failure is never kept."""

    def __init__(self) -> None:
        self._lock, self._kept = threading.Lock(), None

    def __call__(self) -> dict[str, Any]:
        """The models with an empty error, or no models and why."""
        with self._lock:
            if self._kept and time.monotonic() - self._kept[0] < FRESH:
                return {"models": self._kept[1], "error": ""}
            try:
                models = [
                    shown(m) for m in _read() if m.id != AUTO and (m.policy is None or m.policy.state == "enabled")
                ]
            except Exception as exc:  # noqa: BLE001 - without the list the page keeps a typed model
                return {"models": [], "error": f"{type(exc).__name__}: {exc}"[:200]}
            self._kept = (time.monotonic(), models)
            return {"models": models, "error": ""}


def shown(m: ModelInfo) -> dict[str, Any]:
    """One model as the page offers it, with only the efforts a setting can hold."""
    return {
        "id": m.id,
        "name": m.name,
        "efforts": [e for e in m.supported_reasoning_efforts or [] if e in EFFORTS],
        "default_effort": m.default_reasoning_effort or "",
        "context": m.capabilities.limits.max_context_window_tokens,
    }


def _read() -> list[ModelInfo]:
    return asyncio.run(_listed())


async def _listed() -> list[ModelInfo]:
    """Start the runtime, list, and stop it, each step bounded: at most ``WAIT`` plus 10 seconds in all."""
    client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
    try:
        async with asyncio.timeout(WAIT):
            await client.start()
            return await client.list_models()
    finally:
        try:
            async with asyncio.timeout(5):
                await client.stop()
        except Exception:  # noqa: BLE001 - a runtime that will not stop is ended
            with contextlib.suppress(Exception):
                async with asyncio.timeout(5):
                    await client.force_stop()
