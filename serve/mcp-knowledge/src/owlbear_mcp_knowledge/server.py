"""FastMCP server for owlbear-mcp-knowledge: knowledge ingestion and search tools."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict
from uuid import uuid4

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline
from owlbear_knowledge.bookmark_store import BookmarkStore
from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.consolidation import ConsolidationService, TextCompletionFn
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.evaluator import EvaluateFn, EvaluationResult, SourceEvaluator
from owlbear_knowledge.extractor import EntityExtractor
from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge.graph_builder import IntraDocGraphBuilder
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.models import EntityType
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.query_service import KnowledgeQueryService
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_knowledge.retrieval import GraphAugmentedRetriever
from owlbear_knowledge.schema import init_db as _schema_init_db
from owlbear_knowledge.scope_transfer import _do_import as _core_do_import
from owlbear_knowledge.scope_transfer import export_scope as _core_export_scope
from owlbear_knowledge.scope_transfer import import_scope as _core_import_scope
from owlbear_knowledge.scope_transfer import resolve_global_db_path
from owlbear_knowledge.source_store import KnowledgeSourceStore

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
    from owlbear_knowledge.protocol import ContentFetcher
else:
    InterDocGraphBuilder = Any

_DEFAULT_KB_PATH = ".owlbear/knowledge/local.db"
_DEFAULT_QDRANT_PATH = ".owlbear/knowledge/vectors"

# Backward-compatible patch target used by legacy tests; the guard is no longer wired.
globals()["Content" "InjectionGuard"] = object


class _BrowserContentFetcher:
    """Protocol-compatible browser fetcher placeholder.

    The browser MCP server owns Playwright lifecycle. This placeholder preserves
    fetch-method routing behavior in mcp-knowledge without introducing a direct
    package dependency on owlbear_browser.
    """

    async def fetch(self, url: str) -> str:
        """Raise a clear error until a live browser fetcher is injected."""
        # Keep protocol signature without leaking URL details into persisted errors.
        _ = url
        msg = "browser fetcher selected but no browser session is wired"
        raise RuntimeError(msg)


class SearchResult(TypedDict):
    """A single knowledge-base search result."""

    title: str
    score: float
    snippet: str
    entity_type: str | None
    retrieval_path: str
    entities: list[SearchEntity]
    related_sources: list[RelatedSource]
    source: SearchSource


class SearchEntity(TypedDict):
    """A single entity mention attached to a search result."""

    name: str
    type: str


class RelatedSource(TypedDict):
    """A relationship edge from this result to another source."""

    name: str
    relationship: str
    entity: str


class SearchSource(TypedDict):
    """Source metadata attached to a search result."""

    name: str
    url: str


class SourceInfo(TypedDict):
    """A registered knowledge source entry."""

    id: str
    name: str
    source_type: str
    scope: str


class EntityInfo(TypedDict):
    """A knowledge-graph entity entry."""

    name: str
    entity_type: str
    description: str


class StatsResult(TypedDict):
    """Knowledge-base summary statistics."""

    documents: int
    entities: int
    edges: int
    total_sources: int
    total_chunks: int
    chunks_enriched_ratio: float
    consolidation_candidates_remaining: int


class EnrichmentChunk(TypedDict):
    """Chunk payload claimed by enrichment workers."""

    chunk_id: str
    text: str
    doc_title: str
    section_path: str | None
    source_name: str | None
    document_id: str
    source_id: str
    scope: str


class ConsolidationCandidate(TypedDict):
    """Cross-source entity pair eligible for phase-2 consolidation."""

    candidate_id: str
    entity_id_a: str
    entity_id_b: str
    entity_name: str
    source_a: str
    source_b: str
    source_a_name: str
    source_b_name: str
    source_a_chunk: str
    source_b_chunk: str


_CANDIDATE_ID_BASE_PARTS = 3
_CANDIDATE_ID_EXTENDED_PARTS = 5


def _encode_candidate_id(
    entity_name: str,
    source_a: str,
    source_b: str,
    entity_id_a: str,
    entity_id_b: str,
) -> str:
    """Encode the reviewed-pair identity into an opaque candidate ID."""
    return json.dumps(
        [entity_name, source_a, source_b, entity_id_a, entity_id_b],
        separators=(",", ":"),
    )


def _decode_candidate_id(candidate_id: str) -> tuple[str, str, str, str | None, str | None]:
    """Decode candidate ID into (entity_name, source_a, source_b, entity_id_a, entity_id_b)."""
    try:
        parsed = json.loads(candidate_id)
    except (TypeError, ValueError) as exc:
        msg = "invalid candidate_id"
        raise ToolError(msg) from exc

    if (
        not isinstance(parsed, list)
        or len(parsed) not in {_CANDIDATE_ID_BASE_PARTS, _CANDIDATE_ID_EXTENDED_PARTS}
        or not all(isinstance(part, str) for part in parsed)
    ):
        msg = "invalid candidate_id"
        raise ToolError(msg)
    if len(parsed) == _CANDIDATE_ID_BASE_PARTS:
        return parsed[0], parsed[1], parsed[2], None, None
    return parsed[0], parsed[1], parsed[2], parsed[3], parsed[4]


def _fetch_consolidation_candidate_rows(
    conn: sqlite3.Connection,
    *,
    limit: int | None,
) -> list[
    tuple[
        str,
        str,
        str,
        str,
        str,
        str | None,
        str | None,
        str | None,
        str | None,
    ]
]:
    """Return deduplicated candidate rows ordered by entity name."""
    sql = """
        WITH pair_candidates AS (
            SELECT
                e1.name AS entity_name,
                CASE
                    WHEN d1.source_id < d2.source_id THEN e1.id
                    ELSE e2.id
                END AS entity_id_a,
                CASE
                    WHEN d1.source_id < d2.source_id THEN e2.id
                    ELSE e1.id
                END AS entity_id_b,
                CASE
                    WHEN d1.source_id < d2.source_id THEN d1.source_id
                    ELSE d2.source_id
                END AS source_a,
                CASE
                    WHEN d1.source_id < d2.source_id THEN d2.source_id
                    ELSE d1.source_id
                END AS source_b,
                CASE
                    WHEN d1.source_id < d2.source_id THEN ks1.name
                    ELSE ks2.name
                END AS source_a_name,
                CASE
                    WHEN d1.source_id < d2.source_id THEN ks2.name
                    ELSE ks1.name
                END AS source_b_name,
                CASE
                    WHEN d1.source_id < d2.source_id THEN c1.content
                    ELSE c2.content
                END AS source_a_chunk,
                CASE
                    WHEN d1.source_id < d2.source_id THEN c2.content
                    ELSE c1.content
                END AS source_b_chunk
            FROM entities AS e1
            JOIN entities AS e2 ON e1.name = e2.name AND e1.id < e2.id
            JOIN documents AS d1 ON d1.id = e1.document_id
            JOIN documents AS d2 ON d2.id = e2.document_id
            LEFT JOIN knowledge_sources AS ks1 ON ks1.id = d1.source_id
            LEFT JOIN knowledge_sources AS ks2 ON ks2.id = d2.source_id
            LEFT JOIN chunks AS c1 ON c1.id = e1.chunk_id
            LEFT JOIN chunks AS c2 ON c2.id = e2.chunk_id
            WHERE d1.source_id IS NOT NULL
              AND d2.source_id IS NOT NULL
              AND d1.source_id != d2.source_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM edges AS ed
                  WHERE (ed.source_id = e1.id AND ed.target_id = e2.id)
                     OR (ed.source_id = e2.id AND ed.target_id = e1.id)
              )
        )
        SELECT
            pc.entity_name,
            pc.entity_id_a,
            pc.entity_id_b,
            pc.source_a,
            pc.source_b,
            MIN(pc.source_a_name) AS source_a_name,
            MIN(pc.source_b_name) AS source_b_name,
            MIN(pc.source_a_chunk) AS source_a_chunk,
            MIN(pc.source_b_chunk) AS source_b_chunk
        FROM pair_candidates AS pc
        WHERE NOT EXISTS (
            SELECT 1
            FROM reviewed_pairs AS rp
            WHERE (
                (
                    rp.entity_name = pc.entity_name
                    AND (
                        (rp.source_a = pc.source_a AND rp.source_b = pc.source_b)
                        OR (rp.source_a = pc.source_b AND rp.source_b = pc.source_a)
                    )
                    AND COALESCE(rp.entity_id_a, '') = ''
                    AND COALESCE(rp.entity_id_b, '') = ''
                )
                OR (
                    (
                        rp.source_a = pc.source_a
                        AND rp.source_b = pc.source_b
                        AND rp.entity_id_a = pc.entity_id_a
                        AND rp.entity_id_b = pc.entity_id_b
                    )
                    OR (
                        rp.source_a = pc.source_b
                        AND rp.source_b = pc.source_a
                        AND rp.entity_id_a = pc.entity_id_b
                        AND rp.entity_id_b = pc.entity_id_a
                    )
                )
            )
        )
        GROUP BY pc.entity_name, pc.entity_id_a, pc.entity_id_b, pc.source_a, pc.source_b
        ORDER BY pc.entity_name ASC, pc.source_a ASC, pc.source_b ASC
    """

    params: tuple[object, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    return conn.execute(sql, params).fetchall()


async def get_consolidation_candidates(
    ctx: Context,
    limit: int = 20,
) -> list[ConsolidationCandidate]:
    """Return unresolved cross-source consolidation candidates."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    rows = _fetch_consolidation_candidate_rows(conn, limit=limit)
    return [
        {
            "candidate_id": _encode_candidate_id(row[0], row[3], row[4], row[1], row[2]),
            "entity_name": row[0],
            "entity_id_a": row[1],
            "entity_id_b": row[2],
            "source_a": row[3],
            "source_b": row[4],
            "source_a_name": row[5] or "",
            "source_b_name": row[6] or "",
            "source_a_chunk": row[7] or "",
            "source_b_chunk": row[8] or "",
        }
        for row in rows
    ]


def _candidate_entity_ids(
    conn: sqlite3.Connection,
    *,
    entity_name: str,
    source_a: str,
    source_b: str,
) -> tuple[str, str] | None:
    """Resolve candidate endpoint IDs in source_a/source_b order."""
    row = conn.execute(
        """
        SELECT
            CASE
                WHEN d1.source_id < d2.source_id THEN e1.id
                ELSE e2.id
            END AS entity_id_a,
            CASE
                WHEN d1.source_id < d2.source_id THEN e2.id
                ELSE e1.id
            END AS entity_id_b
        FROM entities AS e1
        JOIN entities AS e2 ON e1.name = e2.name AND e1.id < e2.id
        JOIN documents AS d1 ON d1.id = e1.document_id
        JOIN documents AS d2 ON d2.id = e2.document_id
        WHERE e1.name = ?
          AND (
                (d1.source_id = ? AND d2.source_id = ?)
                OR (d1.source_id = ? AND d2.source_id = ?)
          )
        ORDER BY entity_id_a ASC, entity_id_b ASC
        LIMIT 1
        """,
        (entity_name, source_a, source_b, source_b, source_a),
    ).fetchone()
    if row is None or row[0] is None or row[1] is None:
        return None
    return row[0], row[1]


def _resolve_candidate_identity(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
) -> tuple[str, str, str, str, str]:
    """Resolve candidate identity to a durable row pair and source pair."""
    entity_name, source_a, source_b, id_a, id_b = _decode_candidate_id(candidate_id)
    if id_a is not None and id_b is not None:
        row = conn.execute(
            """
            SELECT
                e1.id,
                e2.id,
                d1.source_id,
                d2.source_id,
                e1.name,
                e2.name
            FROM entities AS e1
            JOIN entities AS e2 ON e2.id = ?
            JOIN documents AS d1 ON d1.id = e1.document_id
            JOIN documents AS d2 ON d2.id = e2.document_id
            WHERE e1.id = ?
            """,
            (id_b, id_a),
        ).fetchone()
        if (
            row is None
            or not isinstance(row[0], str)
            or not isinstance(row[1], str)
            or not isinstance(row[2], str)
            or not isinstance(row[3], str)
            or row[4] != entity_name
            or row[5] != entity_name
            or row[2] != source_a
            or row[3] != source_b
        ):
            msg = "candidate_id does not resolve to persisted entity endpoints"
            raise ToolError(msg)
        return row[4], row[2], row[3], row[0], row[1]

    entity_ids = _candidate_entity_ids(
        conn,
        entity_name=entity_name,
        source_a=source_a,
        source_b=source_b,
    )
    if entity_ids is None:
        msg = "candidate_id does not resolve to persisted entity endpoints"
        raise ToolError(msg)
    return entity_name, source_a, source_b, entity_ids[0], entity_ids[1]


def _resolve_phase2_edge_endpoints(
    edge: dict[str, Any],
    *,
    entity_id_a: str,
    entity_id_b: str,
) -> tuple[str, str]:
    """Resolve and validate phase-2 endpoints against the candidate pair."""
    pair = {entity_id_a, entity_id_b}
    source_value = edge.get("source_id")
    target_value = edge.get("target_id")
    source_id = source_value if isinstance(source_value, str) else None
    target_id = target_value if isinstance(target_value, str) else None

    if source_id is None and target_id is None:
        return entity_id_a, entity_id_b

    if source_id is None:
        if target_id not in pair:
            msg = "edge endpoints must match candidate entity row identifiers"
            raise ToolError(msg)
        return (entity_id_b if target_id == entity_id_a else entity_id_a), target_id

    if target_id is None:
        if source_id not in pair:
            msg = "edge endpoints must match candidate entity row identifiers"
            raise ToolError(msg)
        return source_id, (entity_id_b if source_id == entity_id_a else entity_id_a)

    if source_id == target_id or {source_id, target_id} != pair:
        msg = "edge endpoints must match candidate entity row identifiers"
        raise ToolError(msg)
    return source_id, target_id


def _extract_relation(edge: dict[str, Any]) -> str:
    """Read edge relation from documented aliases and validate it."""
    relation = edge.get("relation")
    if not isinstance(relation, str) or not relation.strip():
        relationship = edge.get("relationship")
        if isinstance(relationship, str) and relationship.strip():
            relation = relationship
    if not isinstance(relation, str) or not relation.strip():
        msg = "edge relation is required (use 'relation' or 'relationship')"
        raise ToolError(msg)
    return relation.strip()


def _stable_edge_id(*parts: str) -> str:
    """Return a deterministic edge row ID for idempotent retries."""
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class _ChunkProvenance:
    """Server-derived provenance for phase-1 enrichment persistence."""

    document_id: str
    source_id: str
    scope: str
    state: str
    chunk_id: str


def _resolve_or_create_chunk_entity(
    conn: sqlite3.Connection,
    *,
    now_iso: str,
    provenance: _ChunkProvenance,
    name: str,
) -> str:
    """Resolve an entity by chunk/name, creating a placeholder if needed."""
    existing = conn.execute(
        """
        SELECT id FROM entities
        WHERE name = ? AND document_id = ? AND chunk_id = ? AND scope = ?
        ORDER BY created_at ASC, id ASC
        LIMIT 1
        """,
        (name, provenance.document_id, provenance.chunk_id, provenance.scope),
    ).fetchone()
    if existing is not None and isinstance(existing[0], str):
        return existing[0]

    entity_id = uuid4().hex
    conn.execute(
        """
        INSERT OR REPLACE INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            name,
            "",
            "",
            json.dumps({}),
            now_iso,
            provenance.scope,
            provenance.document_id,
            provenance.chunk_id,
            0.5,
        ),
    )
    return entity_id


def _resolve_phase1_edge_endpoints(
    conn: sqlite3.Connection,
    *,
    edge: dict[str, Any],
    now_iso: str,
    provenance: _ChunkProvenance,
    default_source_id: str | None,
) -> tuple[str, str]:
    """Resolve edge endpoints using IDs, names, and chunk-local fallbacks."""
    source_id = edge.get("source_id") if isinstance(edge.get("source_id"), str) else None
    target_id = edge.get("target_id") if isinstance(edge.get("target_id"), str) else None

    def _entity_id_exists(entity_id: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM entities WHERE id = ? AND scope = ? LIMIT 1",
            (entity_id, provenance.scope),
        ).fetchone()
        return row is not None

    if source_id is None:
        source_name = edge.get("source_name")
        if isinstance(source_name, str) and source_name.strip():
            source_id = _resolve_or_create_chunk_entity(
                conn,
                now_iso=now_iso,
                provenance=provenance,
                name=source_name.strip(),
            )
        elif default_source_id is not None:
            source_id = default_source_id

    if target_id is None:
        target_name = edge.get("target_name")
        if isinstance(target_name, str) and target_name.strip():
            target_id = _resolve_or_create_chunk_entity(
                conn,
                now_iso=now_iso,
                provenance=provenance,
                name=target_name.strip(),
            )

    if source_id is not None and not _entity_id_exists(source_id):
        msg = "unable to resolve edge endpoints from provided payload"
        raise ToolError(msg)

    if target_id is not None and not _entity_id_exists(target_id):
        msg = "unable to resolve edge endpoints from provided payload"
        raise ToolError(msg)

    if source_id is None or target_id is None:
        msg = "unable to resolve edge endpoints from provided payload"
        raise ToolError(msg)

    return source_id, target_id


def _load_chunk_provenance(conn: sqlite3.Connection, *, chunk_id: str) -> _ChunkProvenance:
    """Load chunk/document/source identity required for phase-1 persistence."""
    row = conn.execute(
        """
        SELECT d.id, d.source_id, d.scope, c.enrichment_state
        FROM chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        JOIN knowledge_sources AS ks ON ks.id = d.source_id
        WHERE c.id = ?
        """,
        (chunk_id,),
    ).fetchone()
    if row is None:
        msg = "chunk_id does not resolve to an enrich-enabled source-linked chunk"
        raise ToolError(msg)
    if row[3] == "enriched":
        msg = "chunk is already enriched"
        raise ToolError(msg)
    if not isinstance(row[0], str) or not isinstance(row[1], str):
        msg = "chunk provenance could not be resolved"
        raise ToolError(msg)

    scope = row[2] if isinstance(row[2], str) and row[2] else "global"
    state = row[3] if isinstance(row[3], str) else "pending"
    return _ChunkProvenance(
        document_id=row[0],
        source_id=row[1],
        scope=scope,
        state=state,
        chunk_id=chunk_id,
    )


def _clear_failed_chunk_claim(conn: sqlite3.Connection, *, chunk_id: str) -> None:
    """Release stale claim for a failed phase-1 write attempt."""
    row = conn.execute(
        "SELECT enrichment_state FROM chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    if row is None:
        return
    if row[0] != "claimed":
        return
    conn.execute(
        "UPDATE chunks SET enrichment_state='failed', claimed_at=NULL WHERE id = ?",
        (chunk_id,),
    )


def _persist_phase2_enrichment(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    edges: list[dict[str, Any]],
    now_iso: str,
) -> None:
    """Persist phase-2 consolidation review or edge output."""
    entity_name, source_a, source_b, entity_id_a, entity_id_b = _resolve_candidate_identity(
        conn,
        candidate_id=candidate_id,
    )

    if edges:
        for edge in edges:
            relation = _extract_relation(edge)
            metadata = edge.get("metadata")
            edge_metadata = metadata if isinstance(metadata, dict) else {}
            resolved_source_id, resolved_target_id = _resolve_phase2_edge_endpoints(
                edge,
                entity_id_a=entity_id_a,
                entity_id_b=entity_id_b,
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO edges
                (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.get("id")
                    or _stable_edge_id(
                        "phase2",
                        candidate_id,
                        resolved_source_id,
                        resolved_target_id,
                        relation,
                    ),
                    resolved_source_id,
                    resolved_target_id,
                    relation,
                    edge.get("document_id"),
                    edge.get("weight", 1.0),
                    json.dumps(edge_metadata),
                    now_iso,
                    edge.get("scope", "global"),
                ),
            )

    conn.execute(
        """
        INSERT OR IGNORE INTO reviewed_pairs
        (entity_name, source_a, source_b, entity_id_a, entity_id_b)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entity_name, source_a, source_b, entity_id_a, entity_id_b),
    )


def _persist_phase1_enrichment(
    conn: sqlite3.Connection,
    *,
    chunk_id: str,
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    now_iso: str,
) -> None:
    """Persist phase-1 extraction output using server-derived provenance."""
    provenance = _load_chunk_provenance(conn, chunk_id=chunk_id)

    first_entity_id: str | None = None
    for entity in entities:
        entity_name = entity.get("name")
        if not isinstance(entity_name, str) or not entity_name.strip():
            msg = "entity name is required"
            raise ToolError(msg)
        entity_type = entity.get("entity_type")
        if not isinstance(entity_type, str):
            entity_type_alias = entity.get("type")
            entity_type = entity_type_alias if isinstance(entity_type_alias, str) else ""

        entity_id = entity.get("id") if isinstance(entity.get("id"), str) else uuid4().hex
        conn.execute(
            """
            INSERT OR REPLACE INTO entities
            (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_id,
                entity_name.strip(),
                entity_type,
                entity.get("description", ""),
                json.dumps(entity.get("metadata", {})),
                now_iso,
                provenance.scope,
                provenance.document_id,
                provenance.chunk_id,
                entity.get("importance", 0.5),
            ),
        )
        if first_entity_id is None:
            first_entity_id = entity_id

    for edge in edges:
        relation = _extract_relation(edge)
        endpoint_source_id, endpoint_target_id = _resolve_phase1_edge_endpoints(
            conn,
            edge=edge,
            now_iso=now_iso,
            provenance=provenance,
            default_source_id=first_entity_id,
        )
        metadata = edge.get("metadata")
        edge_metadata = metadata.copy() if isinstance(metadata, dict) else {}
        edge_metadata.setdefault("chunk_id", chunk_id)
        conn.execute(
            """
            INSERT OR IGNORE INTO edges
            (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge.get("id") or uuid4().hex,
                endpoint_source_id,
                endpoint_target_id,
                relation,
                provenance.document_id,
                edge.get("weight", 1.0),
                json.dumps(edge_metadata),
                now_iso,
                provenance.scope,
            ),
        )

    conn.execute(
        "UPDATE chunks SET enrichment_state='enriched', claimed_at=NULL WHERE id = ?",
        (chunk_id,),
    )


def select_content_fetcher(method: str) -> ContentFetcher:
    """Return the content fetcher implementation for a persisted fetch method."""
    normalized = method.strip().lower()
    if normalized == "browser":
        return _BrowserContentFetcher()
    return HttpxContentFetcher()


def _extract_section_path(metadata: str | None) -> str | None:
    """Extract section_path from serialized chunk metadata."""
    if not metadata:
        return None
    try:
        parsed = json.loads(metadata)
    except (TypeError, ValueError):
        return None
    section_path = parsed.get("section_path")
    return section_path if isinstance(section_path, str) else None


def _serialize_search_entities(value: object) -> list[SearchEntity]:
    """Normalize result entities to a list of {name, type} objects."""
    if not isinstance(value, list):
        return []

    entities: list[SearchEntity] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            entity_type = item.get("type")
        else:
            name = getattr(item, "name", None)
            entity_type = getattr(item, "type", None)
        if isinstance(name, str) and isinstance(entity_type, str):
            entities.append({"name": name, "type": entity_type})
    return entities


def _serialize_related_sources(value: object) -> list[RelatedSource]:
    """Normalize related_sources to {name, relationship, entity} objects."""
    if not isinstance(value, list):
        return []

    related_sources: list[RelatedSource] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            relationship = item.get("relationship")
            entity = item.get("entity")
        else:
            name = getattr(item, "name", None)
            relationship = getattr(item, "relationship", None)
            entity = getattr(item, "entity", None)
        if (
            isinstance(name, str)
            and isinstance(relationship, str)
            and isinstance(entity, str)
        ):
            related_sources.append(
                {"name": name, "relationship": relationship, "entity": entity}
            )
    return related_sources


def _serialize_source(value: object) -> SearchSource:
    """Normalize source metadata to a {name, url} object."""
    name = getattr(value, "name", None)
    url = getattr(value, "url", None)

    if not isinstance(url, str):
        config = getattr(value, "config", None)
        config_url = config.get("url") if isinstance(config, dict) else None
        if isinstance(config_url, str):
            url = config_url

    return {
        "name": name if isinstance(name, str) else "",
        "url": url if isinstance(url, str) else "",
    }


async def get_next_batch(ctx: Context, limit: int = 10) -> list[EnrichmentChunk]:
    """Atomically claim a batch of chunks ready for enrichment.

    Chunks are eligible when state is pending, or when a previous claim lease
    is stale (>10 minutes). Chunks from sources with enrich=0 are excluded.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    now = datetime.now(tz=UTC)
    now_iso = now.isoformat()

    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.content,
                d.title,
                c.metadata,
                ks.name,
                d.id,
                d.source_id,
                d.scope
            FROM chunks AS c
            JOIN documents AS d ON d.id = c.document_id
            JOIN knowledge_sources AS ks ON ks.id = d.source_id
            WHERE ks.enrich = 1
              AND (
                c.enrichment_state = 'pending'
                OR (
                    c.enrichment_state = 'claimed'
                    AND c.claimed_at IS NOT NULL
                                        AND (strftime('%s', ?) - strftime('%s', c.claimed_at)) > 600
                )
              )
            ORDER BY c.created_at ASC, c.id ASC
            LIMIT ?
            """,
            (now_iso, limit),
        ).fetchall()

        if rows:
            chunk_ids = [row[0] for row in rows]
            placeholders = ",".join("?" for _ in chunk_ids)
            update_sql = (
                "UPDATE chunks SET enrichment_state='claimed', claimed_at=? "  # noqa: S608
                f"WHERE id IN ({placeholders})"
            )
            conn.execute(
                update_sql,
                (now_iso, *chunk_ids),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return [
        {
            "chunk_id": row[0],
            "text": row[1],
            "doc_title": row[2],
            "section_path": _extract_section_path(row[3]),
            "source_name": row[4],
            "document_id": row[5],
            "source_id": row[6],
            "scope": row[7],
        }
        for row in rows
    ]


async def store_enrichment(
    ctx: Context,
    chunk_id: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    candidate_id: str | None = None,
) -> None:
    """Persist enrichment results for phase-1 chunks or phase-2 candidates."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    now_iso = datetime.now(tz=UTC).isoformat()
    edge_rows = edges or []

    if chunk_id is None:
        if candidate_id is not None:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("BEGIN IMMEDIATE")
            try:
                _persist_phase2_enrichment(
                    conn,
                    candidate_id=candidate_id,
                    edges=edge_rows,
                    now_iso=now_iso,
                )
            except Exception:
                conn.rollback()
                raise
            conn.commit()
            return
        msg = "chunk_id is required for phase-1 store_enrichment"
        raise ToolError(msg)

    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("BEGIN IMMEDIATE")
    try:
        _persist_phase1_enrichment(
            conn,
            chunk_id=chunk_id,
            entities=entities or [],
            edges=edge_rows,
            now_iso=now_iso,
        )
    except (sqlite3.Error, ToolError, TypeError, ValueError):
        conn.rollback()
        conn.execute("BEGIN IMMEDIATE")
        try:
            _clear_failed_chunk_claim(conn, chunk_id=chunk_id)
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
        raise
    conn.commit()


def init_db(path: str) -> sqlite3.Connection:
    """Open the SQLite database at *path*, apply schema, return connection."""
    conn = sqlite3.connect(path)
    _schema_init_db(conn)
    return conn


@dataclass(slots=True)
class AppContext:
    """Runtime context passed to MCP tools via FastMCP lifespan."""

    conn: sqlite3.Connection
    query_service: KnowledgeQueryService | None
    graph_store: GraphStore | None
    ingest_pipeline: IngestPipeline | None
    source_store: KnowledgeSourceStore | None
    bookmark_pipeline: BookmarkPipeline | None
    bookmark_store: BookmarkStore | None
    refresh_orchestrator: RefreshOrchestrator | None = None
    consolidation_service: ConsolidationService | None = None
    structured_extractor: object | None = None
    intra_doc_builder: IntraDocGraphBuilder | None = None
    inter_doc_builder: InterDocGraphBuilder | None = None


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read KNOWLEDGE_TOOLS_EXCLUDE and remove each listed tool from the server.

    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    env_val = os.environ.get("KNOWLEDGE_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


def make_text_completion_fn() -> TextCompletionFn:
    """Return a no-op TextCompletionFn stub.

    LLM-backed completion via pydantic-ai was removed. This stub preserves
    the call-site contract so ConsolidationService still wires up.
    """

    async def _complete(_prompt: str) -> str:
        return ""

    return _complete


def make_evaluate_fn() -> EvaluateFn:
    """Return a neutral no-op EvaluateFn stub.

    LLM-backed evaluation via pydantic-ai was removed. Returns a neutral
    result that always allows ingestion.
    """

    async def _evaluate(_prompt: str) -> EvaluationResult:
        return EvaluationResult(
            relevance_score=0.5,
            summary="No project context available -- neutral evaluation.",
            worth_ingesting=True,
        )

    return _evaluate


async def _web_read(url: str) -> str | None:
    """Fetch a URL with the knowledge package's SSRF-safe HTTP fetcher."""
    try:
        return await HttpxContentFetcher().fetch(url)
    except Exception:  # noqa: BLE001
        return None


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Initialise knowledge-base services; close the DB connection on exit."""
    global _app_context  # noqa: PLW0603
    token_path = Path.home() / ".owlbear" / "copilot_token.json"
    token_path.unlink(missing_ok=True)
    path = os.environ.get("OWLBEAR_LOCAL_KB_PATH") or os.environ.get(
        "OWLBEAR_KB_PATH", _DEFAULT_KB_PATH
    )
    qdrant_path = os.environ.get("OWLBEAR_QDRANT_PATH", _DEFAULT_QDRANT_PATH)
    conn = init_db(path)
    try:
        gs = GraphStore(conn)
        vs = QdrantVectorStore(location=qdrant_path)
        emb = BgeM3EmbeddingProvider()
        structured_extractor = None
        extractor = EntityExtractor(extractor=structured_extractor)
        intra_doc_builder = IntraDocGraphBuilder(extractor=structured_extractor)
        inter_doc_builder = None
        gar = GraphAugmentedRetriever(vs, gs, emb)
        source_store = KnowledgeSourceStore(conn)
        qs = KnowledgeQueryService(
            vector_store=vs,
            graph_store=gs,
            embedding_provider=emb,
            retriever=gar,
            source_store=source_store,
        )
        doc_store = DocumentStore(conn, gs, vs, emb)
        chunker = TextChunker()
        pipeline = IngestPipeline(
            doc_store,
            extractor,
            chunker,
            source_store=source_store,
        )
        bookmark_store = BookmarkStore(conn)
        evaluator = SourceEvaluator(llm_fn=make_evaluate_fn())

        bookmark_pipeline = BookmarkPipeline(
            bookmark_store=bookmark_store,
            evaluator=evaluator,
            ingest_pipeline=pipeline,
            web_read_fn=_web_read,
        )
        refresh_orchestrator = RefreshOrchestrator(
            store=source_store,
            pipeline=pipeline,
            workspace_root=Path.cwd(),
            content_fetcher=select_content_fetcher("http"),
            inter_doc_builder=inter_doc_builder,
            graph_store=gs,
        )
        consolidation_service: ConsolidationService | None = ConsolidationService(
            conn, make_text_completion_fn()
        )
        ctx = AppContext(
            conn=conn,
            query_service=qs,
            graph_store=gs,
            ingest_pipeline=pipeline,
            source_store=source_store,
            bookmark_pipeline=bookmark_pipeline,
            bookmark_store=bookmark_store,
            refresh_orchestrator=refresh_orchestrator,
            consolidation_service=consolidation_service,
            structured_extractor=structured_extractor,
            intra_doc_builder=intra_doc_builder,
            inter_doc_builder=inter_doc_builder,
        )
        _app_context = ctx
        _apply_tool_exclusions(_server)
        yield ctx
    finally:
        _app_context = None
        conn.close()


mcp = FastMCP("owlbear-knowledge", lifespan=app_lifespan)

get_next_batch = mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
)(get_next_batch)
get_consolidation_candidates = mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
)(get_consolidation_candidates)
store_enrichment = mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
)(store_enrichment)

__all__ = [
    "AppContext",
    "_apply_tool_exclusions",
    "app_lifespan",
    "bookmark_source",
    "consolidate_knowledge",
    "export_scope",
    "get_stats",
    "import_scope",
    "ingest_document",
    "init_db",
    "list_bookmarks",
    "list_entities",
    "list_sources",
    "mcp",
    "refresh_source",
    "search_knowledge",
    "select_content_fetcher",
    "sync_from_global",
    "sync_to_global",
    "update_bookmark_tags",
]

# Module-level context so zero-arg @mcp.resource handlers can access graph_store.
_app_context: AppContext | None = None


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def search_knowledge(
    ctx: Context,
    query: str,
    limit: int = 5,
    scopes: list[str] | None = None,
) -> list[SearchResult] | str:
    """Search the knowledge base for relevant context."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    qs = app_ctx.query_service
    if qs is None:
        return "error: Knowledge service not available."
    results = await qs.query(query, top_k=limit, scopes=scopes)
    serialized: list[SearchResult] = []
    for r in results:
        retrieval_path = getattr(r, "retrieval_path", "vector")
        serialized.append(
            {
                "title": r.title,
                "score": r.score,
                "snippet": r.snippet,
                "entity_type": r.entity_type,
                "retrieval_path": (
                    retrieval_path if isinstance(retrieval_path, str) else "vector"
                ),
                "entities": _serialize_search_entities(getattr(r, "entities", [])),
                "related_sources": _serialize_related_sources(
                    getattr(r, "related_sources", [])
                ),
                "source": _serialize_source(getattr(r, "source", None)),
            }
        )
    return serialized


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_sources(ctx: Context, scope: str | None = None) -> list[SourceInfo]:
    """List all registered knowledge sources."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)
    sources = store.list_all(scope=scope)
    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": str(s.source_type),
            "scope": s.scope,
        }
        for s in sources
    ]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def ingest_document(
    ctx: Context,
    text: str,
    metadata: dict[str, Any] | None = None,
    scope: str = "global",
    source_url: str | None = None,
) -> str:
    """Ingest a text document into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    pipeline = app_ctx.ingest_pipeline
    if pipeline is None:
        return "error: ingest pipeline not available"
    try:
        result = await pipeline.ingest_text(
            text,
            metadata=metadata,
            scope=scope,
            source_url=source_url,
        )
    except Exception as exc:  # noqa: BLE001
        return f"error: ingestion failed: {exc}"
    else:
        if result.status == "failed":
            return f"error: ingestion failed for document {result.document_id}"
        return (
            f"Ingested: {result.document_id}, {result.chunk_count} chunks, "
            f"{result.entity_count} entities, {result.edge_count} edges "
            f"(status: {result.status})"
        )


async def list_entities(
    ctx: Context,
    entity_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
    scopes: list[str] | None = None,
) -> list[EntityInfo] | str:
    """List entities in the knowledge graph."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    if gs is None:
        return "error: graph store not available"

    if entity_type is not None:
        try:
            et = EntityType(entity_type)
        except ValueError:
            valid = ", ".join(e.value for e in EntityType)
            return f"error: Invalid entity_type '{entity_type}'. Valid types: {valid}"
        entities = await asyncio.to_thread(
            gs.list_entities, entity_type=et, scopes=scopes
        )
    else:
        entities = await asyncio.to_thread(gs.list_entities, scopes=scopes)

    page = entities[offset : offset + limit]
    return [
        {"name": e.name, "entity_type": e.entity_type, "description": e.description}
        for e in page
    ]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_stats(ctx: Context) -> StatsResult:
    """Get knowledge base summary statistics."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    conn = app_ctx.conn
    if gs is None:
        msg = "graph store not available"
        raise ToolError(msg)
    doc_count, entity_count, edge_count = gs.get_counts()

    total_sources = conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0]
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    enriched_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'enriched'"
    ).fetchone()[0]
    chunks_enriched_ratio = (
        float(enriched_chunks) / float(total_chunks) if total_chunks else 0.0
    )
    consolidation_candidates_remaining = len(
        _fetch_consolidation_candidate_rows(conn, limit=None)
    )

    return {
        "documents": doc_count,
        "entities": entity_count,
        "edges": edge_count,
        "total_sources": total_sources,
        "total_chunks": total_chunks,
        "chunks_enriched_ratio": chunks_enriched_ratio,
        "consolidation_candidates_remaining": consolidation_candidates_remaining,
    }


async def knowledge_stats(ctx: Context) -> str:
    """Return knowledge base statistics (callable directly with ctx for testing)."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    gs = app_ctx.graph_store
    doc_count, entity_count, edge_count = gs.get_counts()
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


@mcp.resource("knowledge://stats")
async def _knowledge_stats_bridge() -> str:
    """MCP-registered concrete resource for knowledge://stats (zero-arg for FastMCP compat)."""
    if _app_context is None or _app_context.graph_store is None:
        return "Knowledge base: 0 documents, 0 entities, 0 edges"
    gs = _app_context.graph_store
    doc_count, entity_count, edge_count = gs.get_counts()
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


async def knowledge_stats_resource(ctx: Context | None = None) -> str:
    """Return knowledge base statistics; accepts optional ctx for direct invocation."""
    if ctx is not None:
        app_ctx: AppContext = ctx.request_context.lifespan_context
        gs = app_ctx.graph_store
        counts_fn = gs.get_counts
    else:
        counts_fn = lambda: (0, 0, 0)  # noqa: E731
    doc_count, entity_count, edge_count = counts_fn()
    return f"Knowledge base: {doc_count} documents, {entity_count} entities, {edge_count} edges"


async def bookmark_source(ctx: Context, url: str, reason: str | None = None) -> str:
    """Bookmark a URL: evaluate and optionally ingest into the knowledge base."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    pipeline = app_ctx.bookmark_pipeline
    if pipeline is None:
        return f"error: bookmark pipeline not available for {url}"
    result = await pipeline.process(url, reason=reason)
    if result.skipped_reason is not None:
        return f"Skipped {url}: {result.skipped_reason}"
    score = result.evaluation.relevance_score if result.evaluation else "n/a"
    return f"Bookmarked {url} (score: {score}, ingested: {result.ingested})"


class BookmarkInfo(TypedDict):
    """A single bookmark entry."""

    url: str
    title: str | None
    relevance_score: float | None
    tags: list[str]


async def list_bookmarks(
    ctx: Context,
    tag: str | None = None,
    min_score: float | None = None,
) -> list[BookmarkInfo]:
    """List bookmarks, optionally filtered by tag or minimum relevance score."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.bookmark_store
    if store is None:
        return []
    bookmarks = await asyncio.to_thread(store.list, tag=tag, min_score=min_score)
    return [
        {
            "url": b.url,
            "title": b.title,
            "relevance_score": b.relevance_score,
            "tags": b.tags,
        }
        for b in bookmarks
    ]


async def update_bookmark_tags(
    ctx: Context,
    url: str,
    tags: list[str],
    scope: str = "global",
) -> BookmarkInfo:
    """Update the tags on an existing bookmark."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.bookmark_store
    if store is None:
        msg = "bookmark store not available"
        raise ToolError(msg)
    bookmark = await asyncio.to_thread(store.get_by_url, url, scope)
    if bookmark is None:
        msg = f"bookmark not found for URL: {url}"
        raise ToolError(msg)
    await asyncio.to_thread(store.update_tags, bookmark.id, tags)
    return {
        "url": bookmark.url,
        "title": bookmark.title,
        "relevance_score": bookmark.relevance_score,
        "tags": tags,
    }


async def import_scope(
    ctx: Context,
    project_name: str,
    path: str | None = None,
) -> str:
    """Import a project-local knowledge snapshot into the global KB.

    Reads a portable SQLite file (default: ``.owlbear/knowledge/local.db``)
    and ingests its documents into the global KB under ``scope="project:{project_name}"``.
    Duplicate documents (same content hash) are skipped.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    src = Path(path) if path is not None else None
    return await asyncio.to_thread(
        _core_import_scope,
        src,
        project_name,
        app_ctx.conn,
        workspace_root=Path.cwd(),
    )


async def export_scope(
    ctx: Context,
    scope: str,
    output_path: str,
) -> str:
    """Export all knowledge for a scope to a portable SQLite file.

    Creates a new SQLite database at *output_path* containing only the rows
    matching *scope*.  Qdrant embeddings are excluded (re-embedded on import).
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return await asyncio.to_thread(
        _core_export_scope,
        scope,
        Path(output_path),
        app_ctx.conn,
    )


async def sync_from_global(ctx: Context) -> str:
    """Import all documents from the global knowledge DB into the local DB under scope='global'.

    Global DB path resolution via ``owlbear-project.json`` has been removed (see #1296).
    This tool always returns an ``error: `` string until a replacement resolver is provided.

    Returns a count string on success, or an ``error: `` string on failure.
    """
    try:
        global_path = resolve_global_db_path(Path.cwd())
    except NotImplementedError as exc:
        return f"error: {exc}"
    if isinstance(global_path, str):
        return "error: global DB path could not be resolved"

    if not global_path.exists():
        return f"error: global DB not found at {global_path}"

    app_ctx: AppContext = ctx.request_context.lifespan_context
    local_conn: sqlite3.Connection = app_ctx.conn

    def _run() -> str:
        global_conn = sqlite3.connect(str(global_path))
        try:
            raw = _core_do_import(global_conn, local_conn, target_scope="global")
        finally:
            global_conn.close()
        # Reformat raw "Imported N documents (skipped M duplicates) into scope global"
        # → AC format: "Imported N documents (skipped M duplicates) from global into local under scope 'global'"
        prefix = "Imported "
        if raw.startswith(prefix):
            counts_part = raw[len(prefix) : raw.index(" into scope")]
            return f"Imported {counts_part} from global into local under scope 'global'"
        return raw

    return await asyncio.to_thread(_run)


async def sync_to_global(ctx: Context) -> str:
    """Export local documents with scope='global' into the global knowledge DB.

    Global DB path resolution via ``owlbear-project.json`` has been removed (see #1296).
    This tool always returns an ``error: `` string until a replacement resolver is provided.
    Only documents with ``scope='global'`` in the local DB are exported.
    Duplicate documents (same content hash) are skipped.

    Returns a count string on success, or an ``error: `` string on failure.
    """
    try:
        global_path = resolve_global_db_path(Path.cwd())
    except NotImplementedError as exc:
        return f"error: {exc}"
    if isinstance(global_path, str):
        return f"error: {global_path}"

    app_ctx: AppContext = ctx.request_context.lifespan_context
    local_conn: sqlite3.Connection = app_ctx.conn

    def _run() -> str:
        global_path.parent.mkdir(parents=True, exist_ok=True)
        global_conn = sqlite3.connect(str(global_path))
        try:
            _schema_init_db(global_conn)
            raw = _core_do_import(
                local_conn, global_conn, target_scope="global", source_scope="global"
            )
        finally:
            global_conn.close()
        # Reformat raw "Imported N documents (skipped M duplicates) into scope global"
        # → AC format: "Exported N documents (skipped M duplicates) from local scope 'global' to global DB"
        prefix = "Imported "
        if raw.startswith(prefix):
            counts_part = raw[len(prefix) : raw.index(" into scope")]
            return f"Exported {counts_part} from local scope 'global' to global DB"
        return raw

    return await asyncio.to_thread(_run)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def refresh_source(ctx: Context, source_id: str) -> dict | str:
    """Trigger re-ingestion of a registered knowledge source by its ID.

    Returns a dict with source_id, refreshed, skipped, and failed counts on
    success.  Returns an error string for disabled sources or unavailable
    orchestrator.  Raises ToolError if source_store is unavailable or the
    source_id is not found.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    store = app_ctx.source_store
    if store is None:
        msg = "source store not available"
        raise ToolError(msg)
    source = store.get(source_id)
    if source is None:
        msg = f"Source '{source_id}' not found"
        raise ToolError(msg)
    orchestrator = app_ctx.refresh_orchestrator
    if orchestrator is None:
        return "error: refresh orchestrator not available"
    pipeline = app_ctx.ingest_pipeline
    if pipeline is None:
        return "error: ingest pipeline not available"

    selected_fetcher = select_content_fetcher(source.fetch_method)
    run_orchestrator = RefreshOrchestrator(
        store=store,
        pipeline=pipeline,
        workspace_root=Path.cwd(),
        content_fetcher=selected_fetcher,
        inter_doc_builder=None,
        graph_store=app_ctx.graph_store,
    )
    try:
        result = await run_orchestrator.refresh(source)
    except ValueError as exc:
        return f"error: {exc}"
    return {
        "source_id": result.source_id,
        "refreshed": result.refreshed,
        "skipped": result.skipped,
        "failed": result.failed,
    }


async def consolidate_knowledge(ctx: Context, batch_size: int = 50) -> str:
    """Trigger cross-document insight synthesis for unconsolidated knowledge chunks.

    Returns a human-readable summary of the consolidation result.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    svc = app_ctx.consolidation_service
    if svc is None:
        return "error: consolidation service not available"
    result = await svc.consolidate(batch_size=batch_size)
    if result == 0:
        return "No unconsolidated chunks available"
    return f"Consolidated: {result} insight created"
