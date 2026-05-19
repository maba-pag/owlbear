"""Phase-1 enrichment: batch claiming, entity/edge extraction persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.models import Entity, EntityType

from ._helpers import (
    _extract_entity_type,
    _extract_relation,
    _stable_edge_id,
    _validate_enrichment_edge_payload,
)

if TYPE_CHECKING:
    import sqlite3


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
            EntityType.CONCEPT.value,
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


def _validate_phase1_entity_id(
    conn: sqlite3.Connection,
    *,
    entity_id: str,
    provenance: _ChunkProvenance,
    allow_new: bool,
    allow_existing_in_scope: bool = False,
) -> str:
    """Return a phase-1 entity ID when it is new, chunk-local, or an allowed same-scope endpoint."""
    normalized_entity_id = entity_id.strip()
    if not normalized_entity_id:
        msg = "entity id must not be blank"
        raise ToolError(msg)

    row = conn.execute(
        """
        SELECT document_id, chunk_id, scope
        FROM entities
        WHERE id = ?
        LIMIT 1
        """,
        (normalized_entity_id,),
    ).fetchone()
    if row is None:
        if allow_new:
            return normalized_entity_id
        msg = "unable to resolve edge endpoints from provided payload"
        raise ToolError(msg)

    entity_scope = row[2] if isinstance(row[2], str) and row[2] else "global"
    if row[0] == provenance.document_id and row[1] == provenance.chunk_id and entity_scope == provenance.scope:
        return normalized_entity_id
    if allow_existing_in_scope and entity_scope == provenance.scope:
        return normalized_entity_id

    msg = "phase-1 entity IDs must belong to the target chunk"
    raise ToolError(msg)


def _validate_phase1_entity_payload(
    *,
    entity_id: str,
    entity_name: str,
    entity_type: str,
    entity: dict[str, Any],
    provenance: _ChunkProvenance,
) -> Entity:
    """Return a domain-validated Entity for a phase-1 payload."""
    try:
        return Entity(
            id=entity_id,
            name=entity_name,
            entity_type=entity_type,
            description=entity.get("description", ""),
            metadata=entity.get("metadata", {}),
            scope=provenance.scope,
            document_id=provenance.document_id,
            chunk_id=provenance.chunk_id,
            importance=entity.get("importance", 0.5),
        )
    except ValueError as exc:
        msg = "invalid entity payload"
        raise ToolError(msg) from exc


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

    if source_id is not None:
        source_id = _validate_phase1_entity_id(
            conn,
            entity_id=source_id,
            provenance=provenance,
            allow_new=False,
            allow_existing_in_scope=True,
        )

    if target_id is not None:
        target_id = _validate_phase1_entity_id(
            conn,
            entity_id=target_id,
            provenance=provenance,
            allow_new=False,
            allow_existing_in_scope=True,
        )

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
          AND ks.enrich = 1
          AND ks.enabled = 1
        """,
        (chunk_id,),
    ).fetchone()
    if row is None:
        msg = "chunk_id does not resolve to an enrich-enabled source-linked chunk"
        raise ToolError(msg)
    state = row[3] if isinstance(row[3], str) else "pending"
    if state == "enriched":
        msg = "chunk is already enriched"
        raise ToolError(msg)
    if state not in {"pending", "claimed"}:
        msg = "chunk is not pending or claimed"
        raise ToolError(msg)
    if not isinstance(row[0], str) or not isinstance(row[1], str):
        msg = "chunk provenance could not be resolved"
        raise ToolError(msg)

    scope = row[2] if isinstance(row[2], str) and row[2] else "global"
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
        entity_type = _extract_entity_type(entity)

        raw_entity_id = entity.get("id")
        entity_id = (
            _validate_phase1_entity_id(
                conn,
                entity_id=raw_entity_id,
                provenance=provenance,
                allow_new=True,
            )
            if isinstance(raw_entity_id, str) and raw_entity_id.strip()
            else uuid4().hex
        )
        validated_entity = _validate_phase1_entity_payload(
            entity_id=entity_id,
            entity_name=entity_name.strip(),
            entity_type=entity_type,
            entity=entity,
            provenance=provenance,
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO entities
            (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                validated_entity.id,
                validated_entity.name,
                validated_entity.entity_type.value,
                validated_entity.description,
                json.dumps(validated_entity.metadata),
                now_iso,
                validated_entity.scope,
                validated_entity.document_id,
                validated_entity.chunk_id,
                validated_entity.importance,
            ),
        )
        if first_entity_id is None:
            first_entity_id = validated_entity.id

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
        edge_id = _stable_edge_id(
            "phase1",
            chunk_id,
            endpoint_source_id,
            endpoint_target_id,
            relation,
        )
        validated_edge = _validate_enrichment_edge_payload(
            {
                "id": edge_id,
                "source_id": endpoint_source_id,
                "target_id": endpoint_target_id,
                "relation": relation,
                "weight": edge.get("weight", 1.0),
                "metadata": edge_metadata,
                "scope": provenance.scope,
            }
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO edges
            (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                validated_edge.id,
                validated_edge.source_id,
                validated_edge.target_id,
                validated_edge.relation.value,
                provenance.document_id,
                validated_edge.weight,
                json.dumps(validated_edge.metadata),
                now_iso,
                validated_edge.scope,
            ),
        )

    conn.execute(
        "UPDATE chunks SET enrichment_state='enriched', claimed_at=NULL WHERE id = ?",
        (chunk_id,),
    )
