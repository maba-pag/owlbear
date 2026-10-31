"""The models this machine's Copilot runtime offers, with efforts, context tiers and token rates, for the settings page.

Rates are the runtime's AI credits per batch of tokens, a batch being 1M tokens for every model listed so far.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from typing import TYPE_CHECKING, Any, get_args

from copilot import CopilotClient, RuntimeConnection
from copilot.generated.rpc import ModelsListRequest

from owlbear_delivery_next.change_contracts.models import Effort
from owlbear_delivery_next.runtimes.copilot_cli import cli_path
from owlbear_delivery_next.runtimes.sdk_teardown import call

if TYPE_CHECKING:
    from copilot.generated.rpc import Model, ModelBillingTokenPrices, ModelBillingTokenPricesLongContext

FRESH = 3600.0  # seconds one successful read is reused
WAIT = 30.0  # seconds one read may take, the runtime's start included
AUTO = "auto"  # the runtime's own choice: Delivery pins each role's model and checks the usage names it
EFFORTS = frozenset(get_args(Effort.__value__))


class Offered:
    """The last good read of the offered models, shared by the settings page's requests, and the last read's error.

    A failed read keeps the last good list beside its error; with no list kept, the next call reads again.
    """

    def __init__(self) -> None:
        self._lock, self._kept, self._error = threading.Lock(), None, ""

    def __call__(self) -> dict[str, Any]:
        """The models and the last read's error; read again when the kept list is older than ``FRESH`` or absent."""
        with self._lock:
            return self._last() if self._kept and time.monotonic() - self._kept[0] < FRESH else self._refresh()

    def refresh(self) -> dict[str, Any]:
        """Read now, whatever the kept list's age."""
        with self._lock:
            return self._refresh()

    def _last(self) -> dict[str, Any]:
        return {"models": self._kept[1] if self._kept else [], "error": self._error}

    def _refresh(self) -> dict[str, Any]:
        try:
            models = [
                shown(m) for m in _read() if m.id != AUTO and (m.policy is None or _value(m.policy.state) == "enabled")
            ]
        except Exception as exc:  # noqa: BLE001 - without a new list the page keeps the last one, or a typed model
            self._error = f"{type(exc).__name__}: {exc}"[:200]
            return self._last()
        self._kept, self._error = (time.monotonic(), models), ""
        return self._last()


async def takes_effort(client: CopilotClient, model: str) -> bool:
    """Whether the model takes a reasoning effort; a model missing from the list, or an unread list, is trusted to."""
    try:
        listed = await call(client.list_models(), "model list")
    except Exception:  # noqa: BLE001 - the session create then reports a refused effort itself
        return True
    found = next((m for m in listed if m.id == model), None)
    return found is None or bool(found.supported_reasoning_efforts)


def shown(m: Model) -> dict[str, Any]:
    """One model as the page offers it: efforts a setting can hold, and each context tier's size and rates."""
    prices = m.billing.token_prices if m.billing else None
    long = prices.long_context if prices else None
    return {
        "id": m.id,
        "name": m.name,
        "efforts": [e for e in m.supported_reasoning_efforts or [] if e in EFFORTS],
        "default_effort": m.default_reasoning_effort or "",
        "context": (prices.context_max if prices else None) or m.capabilities.limits.max_context_window_tokens,
        "rates": _rates(prices),
        "long": {"context": long.context_max, "rates": _rates(long)} if long and long.context_max else None,
    }


def _rates(p: ModelBillingTokenPrices | ModelBillingTokenPricesLongContext | None) -> dict[str, float | None] | None:
    """Input, output, cache read, cache write and one-hour cache write rates; one not stated stays ``None``."""
    if p is None or p.input_price is None or p.output_price is None:
        return None
    cache = p.cache_read_price if p.cache_read_price is not None else p.cache_price
    return {
        "input": p.input_price, "output": p.output_price, "cache": cache, "cache_write": p.cache_write_price,
        "cache_write_1h": p.cache_write1_h_price,
    }  # fmt: skip


def _value(state: object) -> object:
    return getattr(state, "value", state)


def _read() -> list[Model]:
    return asyncio.run(_listed())


async def _listed() -> list[Model]:
    """Start the runtime, list, and stop it, each step bounded: at most ``WAIT`` plus 10 seconds in all."""
    client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
    try:
        async with asyncio.timeout(WAIT):
            await client.start()
            return (await client.rpc.models.list(ModelsListRequest())).models
    finally:
        try:
            async with asyncio.timeout(5):
                await client.stop()
        except Exception:  # noqa: BLE001 - a runtime that will not stop is ended
            with contextlib.suppress(Exception):
                async with asyncio.timeout(5):
                    await client.force_stop()
