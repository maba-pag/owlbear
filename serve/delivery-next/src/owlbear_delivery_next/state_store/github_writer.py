"""The account a project's GitHub writes are made by (TD-402): its ``github_account`` setting, read at first use."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.github.account import REPOSITORY_OWNER, Writer

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store


def of(store: Store, repo: Path, *, detecting: bool = False) -> Writer:
    """The writer of *repo*'s project: its setting, ``SettingsUnset`` at the first launch while no layer sets it.

    *detecting* (setup's, the CLI's and the profile's detection, which may run before the settings are filled in) uses
    TD-402's rule while the setting is unset.
    """

    def setting() -> str:
        settings = store.settings()
        if settings.github_account is None and detecting:
            return REPOSITORY_OWNER
        settings.need("github_account")
        return str(settings.github_account)

    return Writer(setting, repo)
