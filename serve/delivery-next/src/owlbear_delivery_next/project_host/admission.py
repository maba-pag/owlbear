"""Admission of a launch the owner starts (a shaping chat, an Impeccable update) against OwlBear's stop (TD-288).

It runs under the host's ``launching`` lock, which a stop when idle takes once as its barrier: a launch admitted before
the intent is running and counted from then on, and one after it is refused.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from fastapi import HTTPException

from owlbear_delivery_next.project_host.host import ENDING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from owlbear_delivery_next.project_host.host import Host

STOPPING = "OwlBear is stopping"


@contextlib.contextmanager
def admitted(host: Host) -> Iterator[None]:
    """Hold the launch lock while the launch starts; refused while OwlBear or the project stops or before a stop."""
    with host.launching:
        if host.closed():
            raise HTTPException(503, STOPPING)
        if said := host.updating():
            raise HTTPException(503, said)
        if host.draining():
            raise HTTPException(409, ENDING)
        yield
