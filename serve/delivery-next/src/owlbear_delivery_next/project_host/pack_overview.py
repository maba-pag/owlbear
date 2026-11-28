"""Read a machine update and any old project updates that still wait for answers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.impeccable_runs import pack_progress
from owlbear_delivery_next.impeccable_runs.pack_state import running_for
from owlbear_delivery_next.state_store import pack_run_record, project_home, registry, update_home

if TYPE_CHECKING:
    from collections.abc import Callable


def pinned() -> dict[str, Any]:
    """The pack this OwlBear version pins, whether it is in place here, and the last look at upstream's releases."""
    pins, notice = pack_files.manifest(), pack_update.notice(refresh=False)
    return {
        "pack": pins["pack"], "upstream": pins["upstream"]["tag"], "identity": pack_files.identity(),
        "status": pack_files.status(),
        "notice": {"said": pack_update.said(notice), "behind": notice["behind"], "checked_at": notice["checked_at"]},
    }  # fmt: skip


def runs(
    reader: Callable[[Path], dict[str, Any] | None] = pack_run_record.read_only,
    actions: dict[str, str] = pack_progress.ACTIONS,
) -> dict[str, Any]:
    """The machine's last run, its lock holder and a list of old runs that cannot be continued."""
    holder = running_for()
    record, error = _read(update_home.root(), reader)
    old, unread = _old_waiting(reader)
    return {
        "holder": holder, "run": _shown(record, holder, actions), "error": "".join(error),
        "old_waiting": old, "errors": unread,
    }  # fmt: skip


def _old_waiting(reader: Callable[[Path], dict[str, Any] | None]) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        listed = registry.load().projects
    except registry.RegistryError as exc:
        return [], [f"the machine's registry cannot be read, so old waiting runs are not shown: {failure(exc)}"]
    waiting, errors = [], []
    for p in listed:
        name = Path(p.path).name
        record, unread = _read(project_home.home(p.id), reader)
        errors.extend(f"{name}: {text}" for text in unread)
        if record and record.get("state") == "waiting":
            pr = (record.get("context") or {}).get("publication") or record.get("published") or {}
            waiting.append({"name": name, "number": pr.get("number"), "url": pr.get("url")})
    return waiting, errors


def _read(root: Path, reader: Callable[[Path], dict[str, Any] | None]) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        return reader(root), []
    except (OSError, ValueError) as exc:
        return None, [f"the update record in {root} cannot be read: {failure(exc)}"]


def _shown(record: dict[str, Any] | None, holder: str | None, actions: dict[str, str]) -> dict[str, Any] | None:
    if not record or not record.get("started_at"):
        return None
    shown = {k: v for k, v in record.items() if k not in {"context", "stages"}}
    stopped = record["state"] == "running" and holder is None
    return shown | {"progress": pack_progress.progress(record, actions), "interrupted": stopped}
