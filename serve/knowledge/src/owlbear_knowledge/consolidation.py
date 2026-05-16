"""Knowledge consolidation service — LLM callable injection.

Provides the ConsolidationInsight schema and ConsolidationService that
batches unconsolidated chunks, calls an injected LLM function, and stores
the resulting insight.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3  # noqa: TC003
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

TextCompletionFn = Callable[[str], Awaitable[str]]


class ConsolidationInsight(BaseModel):
    """A single insight produced by consolidating multiple knowledge chunks."""

    model_config = ConfigDict(frozen=True)

    id: str
    source_ids: list[str]
    insight: str
    created_at: str


class ConsolidationService:
    """Consolidation service that batches chunks and calls an LLM function.

    Args:
        conn: SQLite connection to the knowledge database.
        llm_fn: Async callable that accepts a prompt string and returns
            a completion string.
    """

    def __init__(self, conn: sqlite3.Connection, llm_fn: TextCompletionFn) -> None:
        self._conn = conn
        self._llm_fn = llm_fn

    async def consolidate(self, batch_size: int = 50) -> int:
        """Consolidate a batch of unconsolidated chunks via the LLM function.

        Returns:
            1 on success, 0 when there are no chunks or the LLM call fails.
        """
        rows = self._conn.execute(
            "SELECT id, content FROM chunks WHERE consolidated = 0 ORDER BY rowid LIMIT ?",
            (batch_size,),
        ).fetchall()

        if not rows:
            return 0

        prompt = "\n\n".join(f"Chunk {idx + 1}: {content}" for idx, (_, content) in enumerate(rows))

        try:
            insight_text = await self._llm_fn(prompt)
        except Exception:  # noqa: BLE001
            logger.warning("LLM call failed during consolidation", exc_info=True)
            return 0

        consolidation_id = str(uuid4())
        source_ids = json.dumps([row[0] for row in rows])
        created_at = datetime.now(UTC).isoformat()

        self._conn.execute(
            "INSERT INTO consolidations (id, source_ids, insight, created_at) VALUES (?, ?, ?, ?)",
            (consolidation_id, source_ids, insight_text, created_at),
        )
        chunk_ids = [row[0] for row in rows]
        placeholders = ",".join("?" * len(chunk_ids))
        self._conn.execute(
            f"UPDATE chunks SET consolidated = 1 WHERE id IN ({placeholders})",  # noqa: S608
            chunk_ids,
        )
        self._conn.commit()
        return 1

    async def schedule_periodic(self, interval: int = 3600) -> None:
        """Run consolidate() in an infinite loop, sleeping between runs.

        Re-raises asyncio.CancelledError; logs and continues on other exceptions.
        """
        while True:
            try:
                await self.consolidate()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.warning("Error in consolidation cycle", exc_info=True)
            await asyncio.sleep(interval)
