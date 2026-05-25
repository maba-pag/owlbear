"""SQLite-backed GraphStore implementation for entity and edge operations."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from owlbear_knowledge.protocols.common import EntityType, RelationType, canonicalize_name
from owlbear_knowledge.protocols.graph import (
    AdjacencyQuery,
    ChunkClaims,
    EdgeInput,
    EdgeRecord,
    EntityAliasInput,
    EntityAliasRecord,
    EntityInput,
    EntityQuery,
    EntityRecord,
    EvidenceInput,
    EvidenceInvalidationResult,
    EvidenceRecord,
    GraphStats,
    GraphStore,
    TraversalDirection,
    TraversalQuery,
    TraversalResult,
)


class SqliteGraphStore(GraphStore):
    """SQLite-backed GraphStore for graph_entities and graph_edges."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def ensure_tables(self) -> None:
        """Create Graph-owned tables if they do not yet exist."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(canonical_name, entity_type)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_edges (
                id TEXT PRIMARY KEY,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id),
                FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id),
                UNIQUE(source_entity_id, target_entity_id, relation_type)
            )
            """
        )
        self._conn.commit()

    def upsert_entity(self, entity: EntityInput) -> EntityRecord:
        """Create or update an entity by canonical identity."""
        canonical_name = canonicalize_name(entity.name)
        if not canonical_name:
            msg = "entity name is empty after canonicalization"
            raise ValueError(msg)

        now_iso = self._now_iso()
        entity_id = self._entity_identity_id(canonical_name, entity.entity_type.value)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                """
                SELECT id, created_at, metadata_json
                FROM graph_entities
                WHERE canonical_name = ? AND entity_type = ?
                """,
                (canonical_name, entity.entity_type.value),
            ).fetchone()

            if row is None:
                self._conn.execute(
                    """
                    INSERT INTO graph_entities (
                        id, name, canonical_name, entity_type, description,
                        metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        entity.name,
                        canonical_name,
                        entity.entity_type.value,
                        entity.description,
                        json.dumps(entity.metadata),
                        now_iso,
                        now_iso,
                    ),
                )
            else:
                merged = {**self._load_json_dict(row["metadata_json"]), **entity.metadata}
                entity_id = str(row["id"])
                self._conn.execute(
                    """
                    UPDATE graph_entities
                    SET name = ?, description = ?, metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        entity.name,
                        entity.description,
                        json.dumps(merged),
                        now_iso,
                        entity_id,
                    ),
                )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        record = self.get_entity(entity_id)
        if record is None:  # pragma: no cover
            msg = f"entity {entity_id!r} not found after upsert"
            raise LookupError(msg)
        return record

    def upsert_edge(self, edge: EdgeInput) -> EdgeRecord:
        """Create or update an edge by endpoint and relation identity."""
        relation_value = str(edge.relation_type)
        if relation_value == "same_as":
            msg = "SAME_AS relation is invalid for edges; use aliases"
            raise ValueError(msg)

        if not self._entity_exists(edge.source_entity_id):
            msg = f"source entity {edge.source_entity_id!r} does not exist"
            raise ValueError(msg)
        if not self._entity_exists(edge.target_entity_id):
            msg = f"target entity {edge.target_entity_id!r} does not exist"
            raise ValueError(msg)

        now_iso = self._now_iso()
        edge_id = self._edge_identity_id(
            edge.source_entity_id,
            edge.target_entity_id,
            relation_value,
        )
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                """
                SELECT id, created_at, metadata_json
                FROM graph_edges
                WHERE source_entity_id = ? AND target_entity_id = ? AND relation_type = ?
                """,
                (
                    edge.source_entity_id,
                    edge.target_entity_id,
                    relation_value,
                ),
            ).fetchone()

            if row is None:
                self._conn.execute(
                    """
                    INSERT INTO graph_edges (
                        id, source_entity_id, target_entity_id, relation_type,
                        weight, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge_id,
                        edge.source_entity_id,
                        edge.target_entity_id,
                        relation_value,
                        edge.weight,
                        json.dumps(edge.metadata),
                        now_iso,
                        now_iso,
                    ),
                )
            else:
                edge_id = str(row["id"])
                self._conn.execute(
                    """
                    UPDATE graph_edges
                    SET weight = ?, metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        edge.weight,
                        json.dumps(edge.metadata),
                        now_iso,
                        edge_id,
                    ),
                )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        return self._require_edge(edge_id)

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        """Return one entity record by ID, or None when unknown."""
        row = self._conn.execute(
            "SELECT * FROM graph_entities WHERE id = ?",
            (entity_id,),
        ).fetchone()
        if row is None:
            return None

        alias_names = self._alias_names_for(entity_id)
        return self._row_to_entity(row, alias_names)

    def find_entities(self, query: EntityQuery) -> tuple[EntityRecord, ...]:
        """Find entity records by canonical name and/or entity type."""
        where: list[str] = []
        params: list[object] = []

        if query.name:
            canonical = canonicalize_name(query.name)
            if self._has_aliases_table():
                where.append(
                    "(e.canonical_name = ? OR e.id IN ("
                    "SELECT a.entity_id FROM graph_aliases a WHERE a.canonical_alias = ?))"
                )
                params.extend([canonical, canonical])
            else:
                where.append("e.canonical_name = ?")
                params.append(canonical)

        if query.entity_type is not None:
            where.append("e.entity_type = ?")
            params.append(query.entity_type.value)

        sql = "SELECT DISTINCT e.* FROM graph_entities e"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.canonical_name, e.id LIMIT ?"
        params.append(query.limit)

        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return tuple(self._row_to_entity(row, self._alias_names_for(str(row["id"]))) for row in rows)

    def get_adjacent(self, query: AdjacencyQuery) -> tuple[EdgeRecord, ...]:
        """Return adjacent edges filtered by direction and relation type."""
        where: list[str] = []
        params: list[object] = []

        if query.direction == TraversalDirection.OUTGOING:
            where.append("source_entity_id = ?")
            params.append(query.entity_id)
        elif query.direction == TraversalDirection.INCOMING:
            where.append("target_entity_id = ?")
            params.append(query.entity_id)
        else:
            where.append("(source_entity_id = ? OR target_entity_id = ?)")
            params.extend([query.entity_id, query.entity_id])

        if query.relation_types:
            placeholders = ", ".join("?" for _ in query.relation_types)
            where.append(f"relation_type IN ({placeholders})")
            params.extend(relation.value for relation in query.relation_types)

        sql = "SELECT * FROM graph_edges"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id LIMIT ?"
        params.append(query.limit)

        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return tuple(self._row_to_edge(row) for row in rows)

    def traverse(self, query: TraversalQuery) -> TraversalResult:
        """Not yet implemented in this task's scope."""
        raise NotImplementedError  # pragma: no cover

    def add_evidence(self, evidence: EvidenceInput) -> EvidenceRecord:
        """Not yet implemented in this task's scope."""
        raise NotImplementedError  # pragma: no cover

    def claims_for_chunk(self, chunk_id: str) -> ChunkClaims:
        """Not yet implemented in this task's scope."""
        raise NotImplementedError  # pragma: no cover

    def invalidate_evidence_by_chunks(
        self,
        chunk_ids: tuple[str, ...],
    ) -> EvidenceInvalidationResult:
        """Not yet implemented in this task's scope."""
        raise NotImplementedError  # pragma: no cover

    def add_alias(self, alias: EntityAliasInput) -> EntityAliasRecord:
        """Not yet implemented in this task's scope."""
        raise NotImplementedError  # pragma: no cover

    def stats(self) -> GraphStats:
        """Not yet implemented in this task's scope."""
        raise NotImplementedError  # pragma: no cover

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=UTC).isoformat()

    @staticmethod
    def _entity_identity_id(canonical_name: str, entity_type: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"entity:{entity_type}:{canonical_name}"))

    @staticmethod
    def _edge_identity_id(source_id: str, target_id: str, relation_type: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"edge:{source_id}:{target_id}:{relation_type}"))

    def _entity_exists(self, entity_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM graph_entities WHERE id = ?",
            (entity_id,),
        ).fetchone()
        return row is not None

    def _alias_names_for(self, entity_id: str) -> tuple[str, ...]:
        if not self._has_aliases_table():
            return ()
        rows = self._conn.execute(
            "SELECT alias_name FROM graph_aliases WHERE entity_id = ? ORDER BY alias_name",
            (entity_id,),
        ).fetchall()
        return tuple(str(row["alias_name"]) for row in rows)

    def _has_aliases_table(self) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'graph_aliases'",
        ).fetchone()
        return row is not None

    def _require_edge(self, edge_id: str) -> EdgeRecord:
        row = self._conn.execute(
            "SELECT * FROM graph_edges WHERE id = ?",
            (edge_id,),
        ).fetchone()
        if row is None:  # pragma: no cover
            msg = f"edge {edge_id!r} not found after upsert"
            raise LookupError(msg)
        return self._row_to_edge(row)

    def _row_to_entity(
        self,
        row: sqlite3.Row,
        alias_names: tuple[str, ...],
    ) -> EntityRecord:
        return EntityRecord(
            id=str(row["id"]),
            name=str(row["name"]),
            canonical_name=str(row["canonical_name"]),
            entity_type=EntityType(str(row["entity_type"])),
            description=str(row["description"]),
            alias_names=alias_names,
            metadata=self._load_json_dict(str(row["metadata_json"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def _row_to_edge(self, row: sqlite3.Row) -> EdgeRecord:
        return EdgeRecord(
            id=str(row["id"]),
            source_entity_id=str(row["source_entity_id"]),
            target_entity_id=str(row["target_entity_id"]),
            relation_type=RelationType(str(row["relation_type"])),
            weight=float(row["weight"]),
            metadata=self._load_json_dict(str(row["metadata_json"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @staticmethod
    def _load_json_dict(raw: str) -> dict[str, object]:
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            return loaded
        return {}
