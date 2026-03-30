"""Knowledge consolidation service — no-op stub implementation.

Provides the ConsolidationInsight schema and a stub ConsolidationService
that returns zero without making LLM calls. Real LLM wiring happens at
the application layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    import sqlite3


class ConsolidationInsight(BaseModel):
    """A single insight produced by consolidating multiple knowledge chunks."""

    model_config = ConfigDict(frozen=True)

    id: str
    source_ids: list[str]
    insight: str
    created_at: str


class ConsolidationService:
    """Stub consolidation service with no LLM dependency.

    Returns 0 (no chunks consolidated) for all inputs. Wire up a real
    LLM backend at the application layer if consolidation is needed.

    Args:
        conn: SQLite connection to the knowledge database.
        graph_store: Optional graph store for entity relationships.
        model: Ignored — kept for API compatibility.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        graph_store: object | None = None,
        model: str | object | None = None,
    ) -> None:
        self._conn = conn
        self._graph_store = graph_store
        self._model = model

    async def consolidate(self, batch_size: int = 50) -> int:  # noqa: ARG002
        """Return 0 — no chunks consolidated (no-op stub)."""
        return 0
