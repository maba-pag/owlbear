"""Graph enrichment scheduling — background intra- and inter-doc graph building.

Provides :class:`GraphEnricher`, which owns background task scheduling and
concurrency control for graph enrichment after document ingestion.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from owlbear.memory.knowledge.cancellation import CancelSignal
    from owlbear.memory.knowledge.document_store import DocumentStore
    from owlbear.memory.knowledge.extractor import ExtractionResult
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.graph_builder import IntraDocGraphBuilder
    from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder
    from owlbear.memory.knowledge.models import Entity

logger = logging.getLogger(__name__)


class GraphEnricher:
    """Schedule and run background graph enrichment tasks.

    Owns the ``_background_tasks`` set and ``_bg_semaphore`` that bound
    concurrent enrichment work.

    Args:
        conn: SQLite connection for idempotency checks.
        graph_store: Graph store for inserting inferred edges.
        graph_builder: Optional intra-document graph builder.
        inter_doc_builder: Optional inter-document graph builder.
        document_store: Document store for status updates.
        pipeline_name: Label stamped into provenance metadata.
        bg_concurrency: Maximum concurrent background enrichment tasks.
    """

    def __init__(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        graph_builder: IntraDocGraphBuilder | None,
        inter_doc_builder: InterDocGraphBuilder | None,
        document_store: DocumentStore,
        pipeline_name: str,
        bg_concurrency: int = 5,
    ) -> None:
        self._conn = conn
        self._graph = graph_store
        self._graph_builder = graph_builder
        self._inter_doc_builder = inter_doc_builder
        self._store = document_store
        self._pipeline_name = pipeline_name
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._bg_semaphore = asyncio.Semaphore(bg_concurrency)
        self._shutdown = False

    # -- Public API ----------------------------------------------------------

    def schedule_graph_enrichment(
        self,
        document_id: str,
        extract_results: list[ExtractionResult],
        scope: str,
        *,
        cancel: CancelSignal | None = None,
    ) -> None:
        """Schedule non-blocking intra-document graph enrichment.

        No-op when ``_shutdown`` is ``True``, ``cancel.is_set()`` is ``True``,
        no graph builder is configured, or the document has no entities.
        """
        if self._shutdown:
            return
        if cancel is not None and cancel.is_set():
            return
        if self._graph_builder is None:
            return
        entities = [e for r in extract_results for e in r.entities]
        if not entities:
            return
        logger.info("Scheduling graph enrichment for document %s", document_id)
        task = asyncio.create_task(self._enrich_graph(document_id, entities, scope))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def schedule_inter_doc_enrichment(
        self,
        document_id: str,
        extract_results: list[ExtractionResult],
        scope: str,
        *,
        cancel: CancelSignal | None = None,
    ) -> None:
        """Schedule non-blocking inter-document graph enrichment.

        No-op when ``_shutdown`` is ``True``, ``cancel.is_set()`` is ``True``,
        no inter-doc builder is configured, there are no entities, or the scope
        contains fewer than two documents.
        """
        if self._shutdown:
            return
        if cancel is not None and cancel.is_set():
            return
        if self._inter_doc_builder is None:
            return
        entities = [e for r in extract_results for e in r.entities]
        if not entities:
            return

        doc_count = self._conn.execute(
            "SELECT COUNT(*) FROM document_status WHERE scope = ?",
            (scope,),
        ).fetchone()[0]
        _min_docs = 2
        if doc_count < _min_docs:
            return

        logger.info(
            "Scheduling inter-document graph enrichment for document %s",
            document_id,
        )
        task = asyncio.create_task(self._enrich_inter_doc_graph(document_id, entities, scope))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def drain(self) -> None:
        """Await all tracked tasks to completion and clear their tracking references."""
        self._shutdown = True
        tasks = list(self._background_tasks)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._background_tasks.difference_update(tasks)

    async def shutdown(self) -> None:
        """Set shutdown signal, cancel tracked tasks, and await cleanup."""
        self._shutdown = True
        tasks = list(self._background_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._background_tasks.difference_update(tasks)

    # -- Private helpers -----------------------------------------------------

    async def _enrich_graph(
        self,
        document_id: str,
        entities: list[Entity],
        scope: str,
    ) -> None:
        """Background task: run graph builder and update status on completion."""
        async with self._bg_semaphore:
            await self._enrich_graph_inner(document_id, entities, scope)

    async def _enrich_graph_inner(
        self,
        document_id: str,
        entities: list[Entity],
        scope: str,
    ) -> None:
        """Inner implementation of graph enrichment (runs under semaphore)."""
        try:
            row = self._conn.execute(
                "SELECT status FROM document_status WHERE document_id = ?",
                (document_id,),
            ).fetchone()
            if row and row[0] == "graph_enriched":
                logger.info("Document %s already graph-enriched, skipping", document_id)
                return

            result = await self._graph_builder.build(  # type: ignore[union-attr]
                entities, scope=scope, document_id=document_id
            )

            enrichment_provenance = {
                "source_pipeline": self._pipeline_name,
                "source_task": "graph_enrichment",
            }
            for edge in result.edges:
                stamped = edge.model_copy(
                    update={
                        "metadata": {**edge.metadata, **enrichment_provenance},
                    }
                )
                self._graph.insert_edge(stamped)

            self._store.set_status(document_id, "graph_enriched", scope=scope)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Graph enrichment failed for document %s",
                document_id,
                exc_info=True,
            )

    async def _enrich_inter_doc_graph(
        self,
        document_id: str,
        entities: list[Entity],
        scope: str,
    ) -> None:
        """Background task: run inter-doc graph builder and store inferred edges."""
        async with self._bg_semaphore:
            try:
                result = await self._inter_doc_builder.build(  # type: ignore[union-attr]
                    entities, scope=scope, document_id=document_id
                )

                for edge in result.edges:
                    self._graph.insert_edge(edge)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Inter-document graph enrichment failed for document %s",
                    document_id,
                    exc_info=True,
                )
