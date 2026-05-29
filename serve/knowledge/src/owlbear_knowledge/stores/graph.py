"""SQLite-backed GraphStore implementation for entity and edge operations."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from dataclasses import dataclass
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
    EvidenceClaimType,
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
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_evidence (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                claim_type TEXT NOT NULL,
                entity_id TEXT,
                edge_id TEXT,
                confidence REAL NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES graph_entities(id),
                FOREIGN KEY (edge_id) REFERENCES graph_edges(id),
                UNIQUE(chunk_id, claim_type, entity_id, edge_id)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_aliases (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                canonical_alias TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES graph_entities(id),
                UNIQUE(entity_id, canonical_alias)
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_evidence_chunk_id ON graph_evidence(chunk_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_evidence_entity_id ON graph_evidence(entity_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_evidence_edge_id ON graph_evidence(edge_id)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_aliases_canonical_alias ON graph_aliases(canonical_alias)"
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
                merged = {**self._load_json_dict(row["metadata_json"]), **edge.metadata}
                self._conn.execute(
                    """
                    UPDATE graph_edges
                    SET weight = ?, metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        edge.weight,
                        json.dumps(merged),
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
        """Traverse from a seed entity up to max_hops with deduped results."""
        if not self._entity_exists(query.entity_id):
            msg = f"seed entity {query.entity_id!r} does not exist"
            raise LookupError(msg)

        state = _TraversalState(
            seen_entities={query.entity_id},
            found_entities=[],
            found_edges=[],
            queue=deque([(query.entity_id, 0)]),
            limit=query.limit,
        )
        seen_edges: set[str] = set()

        while state.queue and (len(state.found_entities) + len(state.found_edges) < query.limit):
            current_id, hops = state.queue.popleft()
            if hops >= query.max_hops:
                continue

            adjacent = self.get_adjacent(
                AdjacencyQuery(
                    entity_id=current_id,
                    direction=TraversalDirection.BOTH,
                    relation_types=query.relation_types,
                    limit=query.limit,
                )
            )

            for edge in adjacent:
                if self._at_limit(state.found_entities, state.found_edges, query.limit):
                    break
                if edge.id not in seen_edges:
                    seen_edges.add(edge.id)
                    state.found_edges.append(edge)

                if self._collect_traversal_neighbors(edge, current_id, hops + 1, state):
                    break

        return TraversalResult(
            entities=tuple(state.found_entities),
            edges=tuple(state.found_edges),
        )

    def add_evidence(self, evidence: EvidenceInput) -> EvidenceRecord:
        """Create or update evidence by chunk/claim/target identity."""
        target_id = evidence.entity_id if evidence.claim_type == EvidenceClaimType.ENTITY else evidence.edge_id
        if target_id is None:  # pragma: no cover - guarded by model validation
            msg = "evidence target_id is missing"
            raise ValueError(msg)

        evidence_id = self._evidence_identity_id(
            evidence.chunk_id,
            evidence.claim_type.value,
            target_id,
        )
        now_iso = self._now_iso()

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                """
                SELECT id
                FROM graph_evidence
                WHERE chunk_id = ? AND claim_type = ?
                  AND ((entity_id IS NULL AND ? IS NULL) OR entity_id = ?)
                  AND ((edge_id IS NULL AND ? IS NULL) OR edge_id = ?)
                """,
                (
                    evidence.chunk_id,
                    evidence.claim_type.value,
                    evidence.entity_id,
                    evidence.entity_id,
                    evidence.edge_id,
                    evidence.edge_id,
                ),
            ).fetchone()

            if row is None:
                self._conn.execute(
                    """
                    INSERT INTO graph_evidence (
                        id, chunk_id, claim_type, entity_id, edge_id,
                        confidence, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        evidence.chunk_id,
                        evidence.claim_type.value,
                        evidence.entity_id,
                        evidence.edge_id,
                        evidence.confidence,
                        json.dumps(evidence.metadata),
                        now_iso,
                    ),
                )
            else:
                evidence_id = str(row["id"])
                self._conn.execute(
                    """
                    UPDATE graph_evidence
                    SET confidence = ?, metadata_json = ?
                    WHERE id = ?
                    """,
                    (evidence.confidence, json.dumps(evidence.metadata), evidence_id),
                )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        return self._require_evidence(evidence_id)

    def claims_for_chunk(self, chunk_id: str) -> ChunkClaims:
        """Return all entity, edge, and evidence IDs tied to one chunk."""
        rows = self._conn.execute(
            """
            SELECT id, entity_id, edge_id
            FROM graph_evidence
            WHERE chunk_id = ?
            ORDER BY id
            """,
            (chunk_id,),
        ).fetchall()

        entity_ids = tuple(sorted({str(row["entity_id"]) for row in rows if row["entity_id"] is not None}))
        edge_ids = tuple(sorted({str(row["edge_id"]) for row in rows if row["edge_id"] is not None}))
        evidence_ids = tuple(str(row["id"]) for row in rows)
        return ChunkClaims(
            chunk_id=chunk_id,
            entity_ids=entity_ids,
            edge_ids=edge_ids,
            evidence_ids=evidence_ids,
        )

    def chunk_ids_for_entity(self, entity_id: str) -> tuple[str, ...]:
        """Return distinct chunk IDs that reference one entity via evidence."""
        rows = self._conn.execute(
            """
            SELECT DISTINCT chunk_id
            FROM graph_evidence
            WHERE entity_id = ?
            """,
            (entity_id,),
        ).fetchall()
        return tuple(str(row["chunk_id"]) for row in rows)

    def invalidate_evidence_by_chunks(
        self,
        chunk_ids: tuple[str, ...],
    ) -> EvidenceInvalidationResult:
        """Delete evidence for chunks and cascade delete orphaned graph elements."""
        if not chunk_ids:
            return EvidenceInvalidationResult()

        chunk_ids_json = self._json_array(chunk_ids)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            deleted_rows = self._conn.execute(
                """
                SELECT id, entity_id, edge_id
                FROM graph_evidence
                WHERE chunk_id IN (SELECT value FROM json_each(?))
                """,
                (chunk_ids_json,),
            ).fetchall()

            if not deleted_rows:
                self._conn.commit()
                return EvidenceInvalidationResult()

            invalidated_evidence_ids = tuple(str(row["id"]) for row in deleted_rows)
            candidate_entity_ids = sorted(
                {str(row["entity_id"]) for row in deleted_rows if row["entity_id"] is not None}
            )
            candidate_edge_ids = sorted({str(row["edge_id"]) for row in deleted_rows if row["edge_id"] is not None})

            self._conn.execute(
                """
                DELETE FROM graph_evidence
                WHERE chunk_id IN (SELECT value FROM json_each(?))
                """,
                (chunk_ids_json,),
            )

            orphaned_entity_ids = tuple(self._find_orphan_entities(candidate_entity_ids))
            orphaned_edge_ids = set(self._find_orphan_edges(candidate_edge_ids))

            if orphaned_entity_ids:
                orphaned_entity_json = self._json_array(orphaned_entity_ids)
                rows = self._conn.execute(
                    """
                    SELECT id
                    FROM graph_edges
                    WHERE source_entity_id IN (SELECT value FROM json_each(?))
                       OR target_entity_id IN (SELECT value FROM json_each(?))
                    """,
                    (orphaned_entity_json, orphaned_entity_json),
                ).fetchall()
                orphaned_edge_ids.update(str(row["id"]) for row in rows)

                self._conn.execute(
                    """
                    DELETE FROM graph_aliases
                    WHERE entity_id IN (SELECT value FROM json_each(?))
                    """,
                    (orphaned_entity_json,),
                )

            orphaned_edge_id_tuple = tuple(sorted(orphaned_edge_ids))
            if orphaned_edge_id_tuple:
                orphaned_edge_json = self._json_array(orphaned_edge_id_tuple)
                self._conn.execute(
                    """
                    DELETE FROM graph_evidence
                    WHERE edge_id IN (SELECT value FROM json_each(?))
                    """,
                    (orphaned_edge_json,),
                )
                self._conn.execute(
                    """
                    DELETE FROM graph_edges
                    WHERE id IN (SELECT value FROM json_each(?))
                    """,
                    (orphaned_edge_json,),
                )

            if orphaned_entity_ids:
                orphaned_entity_json = self._json_array(orphaned_entity_ids)
                self._conn.execute(
                    """
                    DELETE FROM graph_evidence
                    WHERE entity_id IN (SELECT value FROM json_each(?))
                    """,
                    (orphaned_entity_json,),
                )
                self._conn.execute(
                    """
                    DELETE FROM graph_entities
                    WHERE id IN (SELECT value FROM json_each(?))
                    """,
                    (orphaned_entity_json,),
                )

            self._conn.commit()
            return EvidenceInvalidationResult(
                invalidated_evidence_ids=invalidated_evidence_ids,
                orphaned_entity_ids=orphaned_entity_ids,
                orphaned_edge_ids=orphaned_edge_id_tuple,
            )
        except Exception:
            self._conn.rollback()
            raise

    def add_alias(self, alias: EntityAliasInput) -> EntityAliasRecord:
        """Create or return existing alias record for an entity."""
        if not self._entity_exists(alias.entity_id):
            msg = f"entity {alias.entity_id!r} does not exist"
            raise LookupError(msg)

        canonical_alias = canonicalize_name(alias.alias_name)
        if not canonical_alias:
            msg = "alias name is empty after canonicalization"
            raise ValueError(msg)

        conflict = self._conn.execute(
            """
            SELECT id
            FROM graph_entities
            WHERE canonical_name = ? AND id != ?
            LIMIT 1
            """,
            (canonical_alias, alias.entity_id),
        ).fetchone()
        if conflict is not None:
            msg = "alias conflicts with another entity canonical_name"
            raise ValueError(msg)

        alias_id = self._alias_identity_id(alias.entity_id, canonical_alias)
        now_iso = self._now_iso()

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                """
                SELECT id
                FROM graph_aliases
                WHERE entity_id = ? AND canonical_alias = ?
                """,
                (alias.entity_id, canonical_alias),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    """
                    INSERT INTO graph_aliases (id, entity_id, alias_name, canonical_alias, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (alias_id, alias.entity_id, alias.alias_name, canonical_alias, now_iso),
                )
            else:
                alias_id = str(row["id"])

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        return self._require_alias(alias_id)

    def stats(self) -> GraphStats:
        """Return current graph table counts."""
        entities = self._count_rows("graph_entities")
        edges = self._count_rows("graph_edges")
        evidence_claims = self._count_rows("graph_evidence")
        aliases = self._count_rows("graph_aliases")
        return GraphStats(
            entities=entities,
            edges=edges,
            evidence_claims=evidence_claims,
            aliases=aliases,
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=UTC).isoformat()

    @staticmethod
    def _entity_identity_id(canonical_name: str, entity_type: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"entity:{entity_type}:{canonical_name}"))

    @staticmethod
    def _edge_identity_id(source_id: str, target_id: str, relation_type: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"edge:{source_id}:{target_id}:{relation_type}"))

    @staticmethod
    def _evidence_identity_id(chunk_id: str, claim_type: str, target_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"evidence:{chunk_id}:{claim_type}:{target_id}"))

    @staticmethod
    def _alias_identity_id(entity_id: str, canonical_alias: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"alias:{entity_id}:{canonical_alias}"))

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

    @staticmethod
    def _json_array(values: tuple[str, ...] | list[str]) -> str:
        return json.dumps(list(values))

    @staticmethod
    def _at_limit(found_entities: list[EntityRecord], found_edges: list[EdgeRecord], limit: int) -> bool:
        return len(found_entities) + len(found_edges) >= limit

    def _collect_traversal_neighbors(
        self,
        edge: EdgeRecord,
        current_id: str,
        next_hops: int,
        state: _TraversalState,
    ) -> bool:
        for neighbor_id in (edge.source_entity_id, edge.target_entity_id):
            if neighbor_id == current_id or neighbor_id in state.seen_entities:
                continue
            if self._at_limit(state.found_entities, state.found_edges, state.limit):
                return True
            state.seen_entities.add(neighbor_id)
            neighbor = self.get_entity(neighbor_id)
            if neighbor is None:
                continue
            state.found_entities.append(neighbor)
            state.queue.append((neighbor_id, next_hops))
        return False

    def _find_orphan_entities(self, candidate_entity_ids: list[str]) -> list[str]:
        if not candidate_entity_ids:
            return []
        candidate_json = self._json_array(candidate_entity_ids)
        rows = self._conn.execute(
            """
            SELECT e.id
            FROM graph_entities e
            LEFT JOIN graph_evidence ge ON ge.entity_id = e.id
            WHERE e.id IN (SELECT value FROM json_each(?))
            GROUP BY e.id
            HAVING COUNT(ge.id) = 0
            ORDER BY e.id
            """,
            (candidate_json,),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def _find_orphan_edges(self, candidate_edge_ids: list[str]) -> list[str]:
        if not candidate_edge_ids:
            return []
        candidate_json = self._json_array(candidate_edge_ids)
        rows = self._conn.execute(
            """
            SELECT e.id
            FROM graph_edges e
            LEFT JOIN graph_evidence ge ON ge.edge_id = e.id
            WHERE e.id IN (SELECT value FROM json_each(?))
            GROUP BY e.id
            HAVING COUNT(ge.id) = 0
            ORDER BY e.id
            """,
            (candidate_json,),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def _count_rows(self, table_name: str) -> int:
        queries = {
            "graph_entities": "SELECT COUNT(*) AS n FROM graph_entities",
            "graph_edges": "SELECT COUNT(*) AS n FROM graph_edges",
            "graph_evidence": "SELECT COUNT(*) AS n FROM graph_evidence",
            "graph_aliases": "SELECT COUNT(*) AS n FROM graph_aliases",
        }
        row = self._conn.execute(queries[table_name]).fetchone()
        return int(row["n"]) if row is not None else 0

    def _require_edge(self, edge_id: str) -> EdgeRecord:
        row = self._conn.execute(
            "SELECT * FROM graph_edges WHERE id = ?",
            (edge_id,),
        ).fetchone()
        if row is None:  # pragma: no cover
            msg = f"edge {edge_id!r} not found after upsert"
            raise LookupError(msg)
        return self._row_to_edge(row)

    def _require_evidence(self, evidence_id: str) -> EvidenceRecord:
        row = self._conn.execute(
            "SELECT * FROM graph_evidence WHERE id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:  # pragma: no cover
            msg = f"evidence {evidence_id!r} not found after upsert"
            raise LookupError(msg)
        return self._row_to_evidence(row)

    def _require_alias(self, alias_id: str) -> EntityAliasRecord:
        row = self._conn.execute(
            "SELECT * FROM graph_aliases WHERE id = ?",
            (alias_id,),
        ).fetchone()
        if row is None:  # pragma: no cover
            msg = f"alias {alias_id!r} not found after upsert"
            raise LookupError(msg)
        return self._row_to_alias(row)

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

    def _row_to_evidence(self, row: sqlite3.Row) -> EvidenceRecord:
        return EvidenceRecord(
            id=str(row["id"]),
            chunk_id=str(row["chunk_id"]),
            claim_type=EvidenceClaimType(str(row["claim_type"])),
            entity_id=str(row["entity_id"]) if row["entity_id"] is not None else None,
            edge_id=str(row["edge_id"]) if row["edge_id"] is not None else None,
            confidence=float(row["confidence"]),
            metadata=self._load_json_dict(str(row["metadata_json"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )

    def _row_to_alias(self, row: sqlite3.Row) -> EntityAliasRecord:
        return EntityAliasRecord(
            id=str(row["id"]),
            entity_id=str(row["entity_id"]),
            alias_name=str(row["alias_name"]),
            canonical_alias=str(row["canonical_alias"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )

    @staticmethod
    def _load_json_dict(raw: str) -> dict[str, object]:
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            return loaded
        return {}


@dataclass
class _TraversalState:
    seen_entities: set[str]
    found_entities: list[EntityRecord]
    found_edges: list[EdgeRecord]
    queue: deque[tuple[str, int]]
    limit: int
