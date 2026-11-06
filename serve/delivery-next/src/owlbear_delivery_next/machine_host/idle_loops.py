"""Idle inspections and their current failures, retained for the existing machine pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.machine_host.auto_update import IDLE_FOR

if TYPE_CHECKING:
    from owlbear_delivery_next.machine_host.machine import Machine


def curate(machine: Machine, every: float) -> None:
    """Look for idle curation work until the machine stops."""
    while not machine.stopping.wait(every):
        try:
            idle = machine.auto.mono() - machine.auto.last_use >= IDLE_FOR
            if idle and not (machine.updating or machine.ending or machine.busy()):
                machine.curation.nudge(None, "idle")
                machine.uncurated = ""
        except Exception as exc:  # noqa: BLE001 - a failed inspection does not end the loop
            why = failure(exc)
            if why != machine.uncurated:
                machine.say(f"looking whether to curate memory failed: {why}")
            machine.uncurated = why


def stop(machine: Machine, every: float) -> None:
    """Look whether the requested stop can finish, never inferring idle from an unreadable inspection."""
    while not machine.stopping.wait(every):
        try:
            machine.idle_stop()
        except Exception as exc:  # noqa: BLE001 - a failed inspection does not end the loop
            why = failure(exc)
            if why != machine.unstopped:
                machine.say(f"looking whether OwlBear may stop failed: {why}")
            machine.unstopped = why
