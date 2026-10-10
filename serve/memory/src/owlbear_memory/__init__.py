"""owlbear-memory package exports."""

from __future__ import annotations

from owlbear_memory.engine import MemoryEngine, check_slot_efficiency, compute_score, repair_duplicate_ids
from owlbear_memory.errors import (
    ConcurrencyError,
    DuplicateEntryError,
    LifecycleRecoveryError,
    LifecycleRollbackFailure,
    MemoryBusyError,
    NotFoundError,
    TransitionError,
    ValidationError,
)
from owlbear_memory.models import (
    AssessmentReceipt,
    AssessmentResult,
    MemoryCategory,
    MemoryEntry,
    MemoryHealth,
    MemoryState,
    validate_scope_agents,
)
from owlbear_memory.writer_lock import writer_lock

__all__ = [
    "AssessmentReceipt",
    "AssessmentResult",
    "ConcurrencyError",
    "DuplicateEntryError",
    "LifecycleRecoveryError",
    "LifecycleRollbackFailure",
    "MemoryBusyError",
    "MemoryCategory",
    "MemoryEngine",
    "MemoryEntry",
    "MemoryHealth",
    "MemoryState",
    "NotFoundError",
    "TransitionError",
    "ValidationError",
    "check_slot_efficiency",
    "compute_score",
    "repair_duplicate_ids",
    "validate_scope_agents",
    "writer_lock",
]
