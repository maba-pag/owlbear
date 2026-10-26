"""The pending project config intents of every clone: this clone's record and the one on the shared remote."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.data_repo import DataRepoError

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store

CONFIG_PENDING = "config.pending"  # the digest of a project config change that has not reached the shared repository


def pending_file(store: Store) -> Path:
    """This clone's pending record file in the shared checkout."""
    return store.shared.root / store.name / CONFIG_PENDING


def shared_pending(store: Store) -> str:
    """The digest of this clone's project config change that has not reached the shared repository; else ``""``."""
    if not store.shared:
        return ""
    try:
        return pending_file(store).read_text().strip()
    except FileNotFoundError:
        return ""


def remote_pending(store: Store) -> str:
    """The pending record on the shared remote, read after a fetch that leaves the checkout alone; else ``""``."""
    fetched = store.shared.git("fetch", "-q")
    if fetched.returncode:
        msg = f"the shared repository could not be fetched to read the pending settings: {fetched.stderr.strip()[:200]}"
        raise DataRepoError(msg)
    rel = f"{store.name}/{CONFIG_PENDING}"
    if store.shared.git("cat-file", "-e", f"@{{upstream}}:{rel}").returncode:
        return ""  # no record on the remote
    shown = store.shared.git("show", f"@{{upstream}}:{rel}")
    if shown.returncode:
        msg = f"the pending settings on the shared remote could not be read: {shown.stderr.strip()[:200]}"
        raise DataRepoError(msg)
    return shown.stdout.strip()


def unpublished_pending(store: Store) -> str:
    """This clone's pending record, only while it has not reached the shared remote; else ``""``.

    A checkout copies the remote's record when it is cloned or pulled, so that copy is not a new intent of this clone.
    """
    local = shared_pending(store)
    if not local:
        return ""
    rel = f"{store.name}/{CONFIG_PENDING}"
    status = store.shared.git("status", "--porcelain", "--", rel)
    ahead = store.shared.git("log", "--format=%H", "@{upstream}..HEAD", "--", rel)
    if status.returncode or ahead.returncode or status.stdout.strip() or ahead.stdout.strip():
        return local  # unknown or unpublished: this clone's intent still holds
    return ""


def pending_intents(store: Store) -> set[str]:
    """Every pending project config intent that has not been published, by this clone or any other."""
    if not store.shared:
        return set()
    return {digest for digest in (unpublished_pending(store), remote_pending(store)) if digest}
