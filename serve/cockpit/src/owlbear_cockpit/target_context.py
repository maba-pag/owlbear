"""Receipt-authorized target context assembly for Cockpit."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_cockpit.routes.target_work import TargetCockpitBinding, TargetCockpitContext
from owlbear_kanban.attempts import AttemptStore
from owlbear_kanban.target_admission import TargetAuthorityRegistry
from owlbear_kanban.target_cutover import (
    TargetCutoverError,
    TargetCutoverRequest,
    authorize_target_mutation,
)
from owlbear_kanban.target_runtime import TargetRuntime

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_kanban.target_authority import TargetAuthority


def process_is_alive(process_id: str) -> bool:
    """Return whether one numeric local process identity is still alive."""
    try:
        process = int(process_id)
        if process <= 0:
            return False
        os.kill(process, 0)
    except ProcessLookupError, ValueError:
        return False
    except PermissionError:
        return True
    return True


class _TargetContextLoader:
    def __init__(self, target_root: Path) -> None:
        self._target_root = target_root
        self._registry = TargetAuthorityRegistry(target_root)
        self._changes: dict[str, TargetCockpitBinding] = {}
        self._runtime_roots: dict[str, Path] = {}

    def load(self) -> TargetCockpitContext:
        context = TargetCockpitContext(
            changes=self._changes,
            work_item_activity=self.activity,
            work_item_trace=self.trace,
            work_item_requests=self.requests,
            process_is_alive=process_is_alive,
            refresh=self.refresh,
        )
        self.refresh()
        return context

    def refresh(self) -> None:
        authorities = self._registry.list_authorities()
        admitted_ids = {authority.change_id for authority in authorities}
        for change_id in tuple(self._changes):
            if change_id not in admitted_ids:
                self._changes.pop(change_id)
                self._runtime_roots.pop(change_id, None)
        for authority in authorities:
            current = self._changes.get(authority.change_id)
            if current is not None and current.authority == authority:
                continue
            self._bind(authority)

    def _bind(self, authority: TargetAuthority) -> None:
        runtime_root = self._target_root / "changes" / authority.change_id
        runtime = TargetRuntime(authority, runtime_root)
        runtime.list_frontier()
        self._changes[authority.change_id] = TargetCockpitBinding(authority=authority, runtime=runtime)
        self._runtime_roots[authority.change_id] = runtime_root

    def activity(self, change_id: str, work_item_id: str) -> tuple[dict[str, object], ...]:
        root = self._runtime_roots.get(change_id)
        if root is None:
            return ()
        return tuple(
            event.model_dump(mode="json")
            for event in AttemptStore(root).list()
            if event.change_id == change_id and event.target_node_id == work_item_id
        )

    def trace(self, change_id: str, work_item_id: str) -> tuple[dict[str, object], ...]:
        binding = self._changes[change_id]
        attempts = (
            {"resource": "attempt", **attempt.model_dump(mode="json")}
            for attempt in binding.runtime.list_attempts(work_item_id)
        )
        receipts = (
            {"resource": "receipt", **receipt.model_dump(mode="json")}
            for receipt in binding.runtime.list_receipts(work_item_id)
        )
        return (*attempts, *receipts)

    def requests(self, change_id: str, work_item_id: str) -> tuple[dict[str, object], ...]:
        binding = self._changes[change_id]
        return tuple(item.model_dump(mode="json") for item in binding.runtime.list_requests(work_item_id))


def load_target_context(workspace_root: Path, request_path: Path) -> TargetCockpitContext:
    """Load and continuously refresh receipt-authorized target changes."""
    try:
        request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
        authorize_target_mutation(workspace_root, request)
    except (OSError, ValidationError, TargetCutoverError) as exc:
        message = "Cockpit startup requires a valid target cutover request and receipt"
        raise RuntimeError(message) from exc
    return _TargetContextLoader(workspace_root / request.target_path).load()


__all__ = ["load_target_context", "process_is_alive"]
