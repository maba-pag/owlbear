"""Retro's runs a host's predecessor left open (#715): taken up again on the job's first pass, or ended."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.machine_host.retro_inputs import Running, settle_open

if TYPE_CHECKING:
    from collections.abc import Callable


def restored(ended: Callable[[Running, str], None]) -> list[Running]:
    """The open runs to take up, each waiting; those whose spend is not known or whose limit is spent are *ended*."""
    waiting, live = [], set()
    for snap in store.run_states().values():
        if snap["state"] == "ended":
            continue
        ctx = Running.of(snap)
        if snap["unsettled"] or not snap["known"]:
            ctx.known = False
            ended(ctx, "stopped: unknown spend after an interruption")
        elif ctx.provenance == "synthetic" or ctx.uid.startswith("syn:"):
            ended(ctx, f"refused: {store.SYNTHETIC_RETIRED}")
        elif ctx.limit - ctx.spent <= 0:
            ended(ctx, "stopped: its credit limit is spent")
        else:
            ctx.why = "OwlBear restarted"
            store.run_event(ctx.id, "waiting", why=ctx.why)
            waiting.append(ctx)
            live.add((ctx.uid, ctx.rev))
    settle_open(live)
    return waiting
