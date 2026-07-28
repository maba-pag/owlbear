"""Cockpit FastAPI dependency callables."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING

from fastapi import Depends

from owlbear_kanban import (
    ChangeLoadResult,
    ChangeRevision,
    DispatchRuntime,
    GitRepositoryHistory,
    NativeRuntime,
    NativeWorkspace,
    ProofCheckoutManager,
    load_change,
)

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_memory.engine import MemoryEngine


@dataclass(frozen=True, slots=True)
class NativeChangeContext:
    """Bind one admitted revision to its Cockpit runtime adapters."""

    revision: ChangeRevision
    runtime: NativeRuntime
    dispatch: DispatchRuntime


class NativeContextCache:
    """Cache native contexts while their loaded revision identity is current."""

    def __init__(self) -> None:
        self._contexts: dict[tuple[Path, str], NativeChangeContext] = {}
        self._lock = RLock()

    def load(self, changes_dir: Path, change_id: str) -> ChangeLoadResult:
        """Load current authority without constructing runtime stores."""
        return load_change(changes_dir, change_id)

    def get(
        self,
        *,
        workspace: NativeWorkspace,
        revision: ChangeRevision,
    ) -> NativeChangeContext:
        """Reuse a context only when its complete revision identity still matches."""
        key = (workspace.changes_dir.resolve(), revision.change_id)
        with self._lock:
            cached = self._contexts.get(key)
            if cached is not None and (
                cached.revision.delivery_digest == revision.delivery_digest
                and cached.revision.source_identity == revision.source_identity
            ):
                return cached

            proof_checkouts = ProofCheckoutManager(
                workspace.workspace_root,
                workspace.proof_root,
                workspace.changes_dir,
            )
            runtime = NativeRuntime(
                revision,
                workspace.work_root,
                GitRepositoryHistory(workspace.workspace_root),
                workspace.claim_expiry,
                proof_checkouts,
            )
            context = NativeChangeContext(
                revision=revision,
                runtime=runtime,
                dispatch=DispatchRuntime(runtime, workspace.work_root, proof_checkouts),
            )
            self._contexts[key] = context
            return context


_native_context_cache = NativeContextCache()


def get_workspace() -> NativeWorkspace:
    """Return the native workspace for the current request."""
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.workspace


def get_memory_engine() -> MemoryEngine:
    """Return the MemoryEngine for the current request.

    In production, resolved from ``app.state.memory_engine`` via a lifespan
    handler in ``main.run``. In tests, replaced via
    ``app.dependency_overrides[get_memory_engine]``.
    """
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.memory_engine


def get_native_context_cache() -> NativeContextCache:
    """Return the process-local native context cache."""
    return _native_context_cache


def get_ideas_path(workspace=Depends(get_workspace)) -> Path:  # noqa: ANN001, B008
    """Return the shared ideas markdown path adjacent to the kanban directory."""
    return workspace.ops_root / "ideas.md"
