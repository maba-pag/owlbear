"""Cockpit FastAPI dependency callables."""

from __future__ import annotations

import weakref
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING

from fastapi import Depends

from owlbear_cockpit.cache import MtimeScanCache
from owlbear_cockpit.view import CockpitView
from owlbear_kanban import (
    ChangeLoadResult,
    ChangeRevision,
    DispatchRuntime,
    GitRepositoryHistory,
    NativeRuntime,
    ProofCheckoutManager,
    load_change,
)

if TYPE_CHECKING:
    from datetime import timedelta

    from owlbear_memory.engine import MemoryEngine

    from owlbear_kanban import KanbanEngine

# WeakKeyDictionary: cache is discarded when the engine instance is GC'd (end of test).
_engine_caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_native_context_caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


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
        changes_dir: Path,
        work_root: Path,
        workspace_root: Path,
        revision: ChangeRevision,
        claim_expiry: timedelta,
    ) -> NativeChangeContext:
        """Reuse a context only when its complete revision identity still matches."""
        key = (changes_dir.resolve(), revision.change_id)
        with self._lock:
            cached = self._contexts.get(key)
            if cached is not None and (
                cached.revision.delivery_digest == revision.delivery_digest
                and cached.revision.source_identity == revision.source_identity
            ):
                return cached

            proof_checkouts = ProofCheckoutManager(workspace_root, work_root.parent / "scratch" / "proof")
            runtime = NativeRuntime(
                revision,
                work_root,
                GitRepositoryHistory(workspace_root),
                claim_expiry,
                proof_checkouts,
            )
            context = NativeChangeContext(
                revision=revision,
                runtime=runtime,
                dispatch=DispatchRuntime(runtime, work_root, proof_checkouts),
            )
            self._contexts[key] = context
            return context


def get_engine() -> KanbanEngine:
    """Return the KanbanEngine for the current request.

    In production, resolved from ``app.state.engine`` via a lifespan handler.
    In tests, replaced via ``app.dependency_overrides[get_engine]``.

    The import of ``owlbear_cockpit.main`` is deferred to call time to avoid
    a circular import (main → routes.read → deps → main at module load time).
    """
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.engine


def get_memory_engine() -> MemoryEngine:
    """Return the MemoryEngine for the current request.

    In production, resolved from ``app.state.memory_engine`` via a lifespan
    handler in ``main.run``. In tests, replaced via
    ``app.dependency_overrides[get_memory_engine]``.
    """
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.memory_engine


def get_cache(engine=Depends(get_engine)) -> MtimeScanCache:  # noqa: ANN001, B008
    """Return the per-engine MtimeScanCache instance.

    Creates one lazily on first access and reuses it for all subsequent requests
    using the same engine instance.  Keyed by engine identity via a
    WeakKeyDictionary so the cache is automatically released when the engine is
    garbage-collected (e.g., at end of each test).
    """
    if engine not in _engine_caches:
        _engine_caches[engine] = MtimeScanCache(engine.tasks_dir)
    return _engine_caches[engine]


def get_native_context_cache(engine=Depends(get_engine)) -> NativeContextCache:  # noqa: ANN001, B008
    """Return the native context cache scoped to the request engine."""
    if engine not in _native_context_caches:
        _native_context_caches[engine] = NativeContextCache()
    return _native_context_caches[engine]


def get_view(engine=Depends(get_engine)) -> CockpitView:  # noqa: ANN001, B008
    """Return a CockpitView facade bound to the request engine."""
    return CockpitView(engine)


def get_decisions_dir(engine=Depends(get_engine)) -> Path:  # noqa: ANN001, B008
    """Return the decisions directory under the engine's public kanban_dir."""
    return Path(engine.kanban_dir) / "decisions"


def get_ideas_path(engine=Depends(get_engine)) -> Path:  # noqa: ANN001, B008
    """Return the shared ideas markdown path adjacent to the kanban directory."""
    return Path(engine.kanban_dir).parent / "ideas.md"
