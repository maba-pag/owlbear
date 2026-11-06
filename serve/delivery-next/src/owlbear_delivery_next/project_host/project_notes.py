"""Project notes, retaining readable diagnostics when the saved profile cannot be read."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.state_store.store import Store

_log = logging.getLogger(__name__)


def reader(store: Store, host: Host) -> Callable[[], dict[str, list[str]]]:
    """The project's notes route, logging only changed profile failures until a successful read."""
    profile_said = ""

    def project() -> dict[str, list[str]]:
        nonlocal profile_said
        failed = [f"The host's last pass failed: {host.failed}"] if host.failed else []
        try:
            notes = profile.notes(store.read_profile() or Profile())
        except StoreError as exc:
            why = failure(exc)
            notes = [f"The project profile could not be read: {why}"]
            if profile_said != why:
                _log.warning("%s: project profile could not be read: %s", store.name or store.root, why)
                profile_said = why
        else:
            profile_said = ""
        return {"notes": [*notes, *failed]}

    return project
