"""Consolidation service — periodic synthesis of cross-document insights.

Reads unconsolidated chunks from the knowledge graph database, generates
insights via an LLM call, stores the results in the ``consolidations``
table, and marks source chunks as consolidated.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai import Agent

if TYPE_CHECKING:
    import sqlite3

    from pydantic_ai.models import Model

    from owlbear.memory.knowledge.graph import GraphStore

logger = logging.getLogger(__name__)


class ConsolidationService:
    """Periodically consolidate unconsolidated chunks into insights.

    Parameters
    ----------
    conn:
        SQLite connection with the v8+ knowledge-graph schema.
    graph_store:
        Optional graph store (reserved for future enrichment).
    model:
        Model identifier passed to the LLM call.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore | None,
        model: str | Model,
    ) -> None:
        self._conn = conn
        self._graph_store = graph_store
        self._model = model
        self._agent: Agent[None, str] = Agent(
            model,
            system_prompt=(
                "Synthesize one concise cross-document insight from the provided chunks. "
                "Return plain text only."
            ),
        )

    # -- Public API ----------------------------------------------------------

    async def consolidate(self, batch_size: int = 50) -> int:
        """Read unconsolidated chunks, synthesise insights, and store them.

        Returns the number of insights created (0 when nothing to process
        or on LLM failure).
        """
        rows = self._conn.execute(
            "SELECT id, content FROM chunks WHERE consolidated = 0 ORDER BY rowid LIMIT ?",
            (batch_size,),
        ).fetchall()

        if not rows:
            return 0

        chunk_ids = [r[0] for r in rows]
        contents = [r[1] for r in rows]

        try:
            insight_text = await self._run_llm(contents)
        except Exception:  # noqa: BLE001
            logger.warning("LLM failure during consolidation; skipping batch")
            return 0

        insight_id = str(uuid.uuid4())
        now = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            "INSERT INTO consolidations (id, source_ids, insight, created_at) VALUES (?, ?, ?, ?)",
            (insight_id, json.dumps(chunk_ids), insight_text, now),
        )

        self._conn.executemany(
            "UPDATE chunks SET consolidated = 1 WHERE id = ?",
            [(cid,) for cid in chunk_ids],
        )
        self._conn.commit()
        return 1

    async def schedule_periodic(self, interval: int = 3600) -> None:
        """Run :meth:`consolidate` in a loop, sleeping *interval* seconds."""
        while True:
            try:
                await self.consolidate()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.warning("Consolidation loop error; will retry next cycle", exc_info=True)
            await asyncio.sleep(interval)

    # -- Internal ------------------------------------------------------------

    async def _run_llm(self, contents: list[str]) -> str:
        """Call the LLM to synthesise an insight from *contents*.

        This is a separate method so tests can patch it easily.
        """
        prompt = "\n\n".join(f"Chunk {idx + 1}: {content}" for idx, content in enumerate(contents))
        result = await self._agent.run(prompt)
        return result.output
