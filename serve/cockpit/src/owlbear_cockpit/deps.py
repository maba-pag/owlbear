"""Cockpit FastAPI dependency callables."""

from __future__ import annotations

import weakref
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Depends

from owlbear_cockpit.cache import MtimeScanCache
from owlbear_cockpit.view import CockpitView

if TYPE_CHECKING:
    from owlbear_memory.engine import MemoryEngine

    from owlbear_kanban import KanbanEngine

# WeakKeyDictionary: cache is discarded when the engine instance is GC'd (end of test).
_engine_caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


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


def get_view(engine=Depends(get_engine)) -> CockpitView:  # noqa: ANN001, B008
    """Return a CockpitView facade bound to the request engine."""
    return CockpitView(engine)


def get_decisions_dir(engine=Depends(get_engine)) -> Path:  # noqa: ANN001, B008
    """Return the decisions directory under the engine's public kanban_dir."""
    return Path(engine.kanban_dir) / "decisions"
