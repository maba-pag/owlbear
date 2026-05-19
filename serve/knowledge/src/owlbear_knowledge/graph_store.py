"""CRUD operations for the knowledge graph.

Provides :class:`GraphStore` — a thin data-access layer over the SQLite
tables created by :func:`owlbear_knowledge.schema.init_db`.
All queries are parameterized (no SQL injection).  Metadata dicts are
serialized to JSON strings on write and deserialized on read.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_knowledge.models import Document, Edge, Entity

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

    from owlbear_knowledge.models import EntityType


class GraphStore:
    """Synchronous CRUD facade for knowledge-graph entities, edges, and documents.

    Args:
        conn (sqlite3.Connection): An open :class:`sqlite3.Connection` where
            :func:`~owlbear_knowledge.schema.init_db` has already been called.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """ISO-8601 timestamp in UTC."""
        return datetime.now(tz=UTC).isoformat()

    @staticmethod
    def _dump_meta(meta: dict[str, object]) -> str:
        """Serialize a metadata dict to a JSON string."""
        return json.dumps(meta)

    @staticmethod
    def _load_meta(raw: str | None) -> dict[str, object]:
        """Deserialize a JSON string back to a metadata dict."""
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _entity_from_row(row: tuple[object, ...]) -> Entity:
        """Deserialize a 9-element entity row into an :class:`Entity`."""
        return Entity(
            id=row[0],
            name=row[1],
            entity_type=row[2],
            description=row[3],
            metadata=GraphStore._load_meta(row[4]),  # type: ignore[arg-type]
            scope=row[5],
            document_id=row[6],
            chunk_id=row[7],
            importance=row[8] if row[8] is not None else 0.5,
        )

    @staticmethod
    def _edge_from_row(row: tuple[object, ...]) -> Edge:
        """Deserialize a 7-element edge row into an :class:`Edge`."""
        return Edge(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            relation=row[3],
            weight=row[4],
            metadata=GraphStore._load_meta(row[5]),  # type: ignore[arg-type]
            scope=row[6],
        )

    # ── Entity operations ──────────────────────────────────────────────────

    def insert_entity(self, entity: Entity) -> None:
        """Insert *entity* into the ``entities`` table."""
        if not isinstance(entity.document_id, str) or not entity.document_id.strip():
            msg = "entity document_id is required"
            raise ValueError(msg)
        self._conn.execute(
            "INSERT INTO entities"
            " (id, name, entity_type, description, metadata,"
            "  created_at, scope, document_id, chunk_id, importance)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entity.id,
                entity.name,
                str(entity.entity_type),
                entity.description,
                self._dump_meta(entity.metadata),
                self._now(),
                entity.scope,
                entity.document_id,
                entity.chunk_id,
                entity.importance,
            ),
        )
        self._conn.commit()

    def get_entity(self, entity_id: str) -> Entity | None:
        """Return the :class:`Entity` with *entity_id*, or ``None``."""
        row = self._conn.execute(
            "SELECT id, name, entity_type, description, metadata,"
            " scope, document_id, chunk_id, importance"
            " FROM entities WHERE id = ?",
            (entity_id,),
        ).fetchone()
        if row is None:
            return None
        return self._entity_from_row(row)

    def list_entities(
        self,
        entity_type: EntityType | None = None,
        scopes: list[str] | None = None,
        pipeline_name: str | None = None,
    ) -> list[Entity]:
        """Return all entities, optionally filtered by type, scopes, and/or pipeline_name."""
        if scopes is not None and len(scopes) == 0:
            return []

        clauses: list[str] = []
        params: list[str] = []

        if entity_type is not None:
            clauses.append("entity_type = ?")
            params.append(str(entity_type))
        if scopes is not None:
            placeholders = ", ".join("?" for _ in scopes)
            clauses.append(f"scope IN ({placeholders})")
            params.extend(scopes)
        if pipeline_name is not None:
            clauses.append("CASE WHEN json_valid(metadata) THEN json_extract(metadata, '$.pipeline_name') END = ?")
            params.append(pipeline_name)

        sql = (
            "SELECT id, name, entity_type, description, metadata,"
            " scope, document_id, chunk_id, importance"
            " FROM entities"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._entity_from_row(r) for r in rows]

    def get_entities_by_chunk_ids(
        self,
        chunk_ids: set[str],
        scopes: list[str] | None = None,
    ) -> list[Entity]:
        """Return entities whose chunk_id is in *chunk_ids*."""
        if not chunk_ids:
            return []
        if scopes is not None and len(scopes) == 0:
            return []

        params: list[str] = list(chunk_ids)
        placeholders = ", ".join("?" for _ in chunk_ids)
        cols = "id, name, entity_type, description, metadata, scope, document_id, chunk_id, importance"
        sql = f"SELECT {cols} FROM entities WHERE chunk_id IN ({placeholders})"  # noqa: S608
        if scopes is not None:
            scope_placeholders = ", ".join("?" for _ in scopes)
            sql += f" AND scope IN ({scope_placeholders})"
            params.extend(scopes)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._entity_from_row(r) for r in rows]

    def list_entities_for_document(
        self,
        document_id: str,
        scopes: list[str] | None = None,
    ) -> list[Entity]:
        """Return all entities linked to *document_id*, optionally filtered by *scopes*."""
        if scopes is not None and len(scopes) == 0:
            return []

        clauses: list[str] = ["document_id = ?"]
        params: list[str] = [document_id]

        if scopes is not None:
            placeholders = ", ".join("?" for _ in scopes)
            clauses.append(f"scope IN ({placeholders})")
            params.extend(scopes)

        sql = (
            "SELECT id, name, entity_type, description, metadata,"  # noqa: S608
            " scope, document_id, chunk_id, importance"
            " FROM entities WHERE " + " AND ".join(clauses)
        )

        rows = self._conn.execute(sql, params).fetchall()
        return [self._entity_from_row(r) for r in rows]

    def delete_entity(self, entity_id: str) -> bool:
        """Delete the entity and cascade-remove its edges.

        Returns ``True`` if the entity existed, ``False`` otherwise.
        """
        self._conn.execute(
            "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
            (entity_id, entity_id),
        )
        cursor = self._conn.execute(
            "DELETE FROM entities WHERE id = ?",
            (entity_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── Edge operations ────────────────────────────────────────────────────

    def insert_edge(self, edge: Edge, *, document_id: str | None = None) -> bool:
        """Insert *edge* into the ``edges`` table."""
        resolved_document_id = self._resolve_edge_document_id(edge, document_id)
        cursor = self._conn.execute(
            "INSERT OR IGNORE INTO edges "
            "(id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                edge.id,
                edge.source_id,
                edge.target_id,
                str(edge.relation),
                resolved_document_id,
                edge.weight,
                self._dump_meta(edge.metadata),
                self._now(),
                edge.scope,
            ),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def _resolve_edge_document_id(self, edge: Edge, document_id: str | None) -> str:
        if isinstance(document_id, str) and document_id:
            return document_id

        meta_document_id = edge.metadata.get("document_id")
        if isinstance(meta_document_id, str) and meta_document_id:
            return meta_document_id

        for entity_id in (edge.source_id, edge.target_id):
            entity = self.get_entity(entity_id)
            entity_document_id = getattr(entity, "document_id", None)
            if isinstance(entity_document_id, str) and entity_document_id:
                return entity_document_id

        msg = "edge document_id is required when endpoint entities have no document provenance"
        raise ValueError(msg)

    def get_edge(self, edge_id: str) -> Edge | None:
        """Return the :class:`Edge` with *edge_id*, or ``None``."""
        row = self._conn.execute(
            "SELECT id, source_id, target_id, relation, weight, metadata, scope FROM edges WHERE id = ?",
            (edge_id,),
        ).fetchone()
        if row is None:
            return None
        return self._edge_from_row(row)

    def list_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        scopes: list[str] | None = None,
        pipeline_name: str | None = None,
    ) -> list[Edge]:
        """Return edges, optionally filtered by source/target, scopes, and/or pipeline_name."""
        if scopes is not None and len(scopes) == 0:
            return []

        clauses: list[str] = []
        params: list[str] = []
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(source_id)
        if target_id is not None:
            clauses.append("target_id = ?")
            params.append(target_id)
        if scopes is not None:
            placeholders = ", ".join("?" for _ in scopes)
            clauses.append(f"scope IN ({placeholders})")
            params.extend(scopes)
        if pipeline_name is not None:
            clauses.append("CASE WHEN json_valid(metadata) THEN json_extract(metadata, '$.pipeline_name') END = ?")
            params.append(pipeline_name)

        sql = "SELECT id, source_id, target_id, relation, weight, metadata, scope FROM edges"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._edge_from_row(r) for r in rows]

    def delete_edge(self, edge_id: str) -> bool:
        """Delete the edge with *edge_id*.

        Returns ``True`` if the edge existed, ``False`` otherwise.
        """
        cursor = self._conn.execute(
            "DELETE FROM edges WHERE id = ?",
            (edge_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── Merge operations ───────────────────────────────────────────────────

    def merge_entities(
        self,
        canonical_id: str,
        duplicate_ids: Sequence[str],
        merged_metadata: dict[str, object],
    ) -> int:
        """Merge *duplicate_ids* into *canonical_id*.

        Updates canonical metadata, redirects all edges, deletes duplicates.
        Returns the number of duplicates merged.
        """
        duplicate_id_list = list(duplicate_ids)
        self._conn.execute(
            "UPDATE entities SET metadata = ? WHERE id = ?",
            (self._dump_meta(merged_metadata), canonical_id),
        )
        self._dedupe_edges_for_entity_merge(canonical_id, duplicate_id_list)
        for dup_id in duplicate_id_list:
            self._conn.execute(
                "UPDATE edges SET source_id = ? WHERE source_id = ?",
                (canonical_id, dup_id),
            )
            self._conn.execute(
                "UPDATE edges SET target_id = ? WHERE target_id = ?",
                (canonical_id, dup_id),
            )
        if duplicate_id_list:
            placeholders = ", ".join("?" for _ in duplicate_id_list)
            self._conn.execute(
                f"DELETE FROM entities WHERE id IN ({placeholders})",  # noqa: S608
                duplicate_id_list,
            )
        self._conn.commit()
        return len(duplicate_id_list)

    def _dedupe_edges_for_entity_merge(self, canonical_id: str, duplicate_ids: Sequence[str]) -> None:
        if not duplicate_ids:
            return

        merge_ids = [canonical_id, *duplicate_ids]
        placeholders = ", ".join("?" for _ in merge_ids)
        rows = self._conn.execute(
            "SELECT id, source_id, target_id, relation, document_id FROM edges "  # noqa: S608
            f"WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
            (*merge_ids, *merge_ids),
        ).fetchall()

        duplicate_id_set = set(duplicate_ids)
        rows = sorted(
            rows,
            key=lambda row: (
                row[1] in duplicate_id_set or row[2] in duplicate_id_set,
                str(row[0]),
            ),
        )
        seen: set[tuple[object, object, object, object]] = set()
        edge_ids_to_delete: list[str] = []
        for edge_id, source_id, target_id, relation, row_document_id in rows:
            normalized_source_id = canonical_id if source_id in duplicate_id_set else source_id
            normalized_target_id = canonical_id if target_id in duplicate_id_set else target_id
            key = (normalized_source_id, normalized_target_id, relation, row_document_id)
            if key in seen:
                if isinstance(edge_id, str):
                    edge_ids_to_delete.append(edge_id)
                continue
            seen.add(key)

        if edge_ids_to_delete:
            delete_placeholders = ", ".join("?" for _ in edge_ids_to_delete)
            self._conn.execute(
                f"DELETE FROM edges WHERE id IN ({delete_placeholders})",  # noqa: S608
                edge_ids_to_delete,
            )

    # ── Traversal operations ───────────────────────────────────────────────

    def get_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        max_nodes: int = 20,
        scopes: list[str] | None = None,
    ) -> list[tuple[Entity, Edge]]:
        """BFS traversal returning neighbor entities with their connecting edges.

        Args:
            entity_id (str): Starting entity for the traversal.
            max_depth (int): Maximum number of hops (1 = direct neighbors only).
            max_nodes (int): Stop collecting once this many neighbors have been found.
            scopes (list[str] | None): Optional scope filter.

        Returns:
            list[tuple[Entity, Edge]]: Each tuple is ``(neighbor_entity, connecting_edge)``.
            Returns an empty list if *entity_id* does not exist.
        """
        if self.get_entity(entity_id) is None:
            return []

        visited: set[str] = {entity_id}
        result: list[tuple[Entity, Edge]] = []
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])

        while queue and len(result) < max_nodes:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            edges = self.list_edges(source_id=current_id, scopes=scopes)
            edges += self.list_edges(target_id=current_id, scopes=scopes)

            for edge in edges:
                neighbor_id = edge.target_id if edge.source_id == current_id else edge.source_id
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                neighbor = self.get_entity(neighbor_id)
                if neighbor is None:
                    continue  # pragma: no cover

                result.append((neighbor, edge))
                if len(result) >= max_nodes:
                    break

                queue.append((neighbor_id, depth + 1))

        return result

    # ── Document operations ────────────────────────────────────────────────

    def insert_document(self, doc: Document) -> None:
        """Insert *doc* into the ``documents`` table."""
        self._conn.execute(
            "INSERT INTO documents"
            " (id, title, content, metadata, created_at, scope, source_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                doc.id,
                doc.title,
                doc.content,
                self._dump_meta(doc.metadata),
                self._now(),
                doc.scope,
                doc.source_id,
            ),
        )
        self._conn.commit()

    def get_document(self, doc_id: str) -> Document | None:
        """Return the :class:`Document` with *doc_id*, or ``None``."""
        row = self._conn.execute(
            "SELECT id, title, content, metadata, scope, source_id FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if row is None:
            return None
        return Document(
            id=row[0],
            title=row[1],
            content=row[2],
            metadata=self._load_meta(row[3]),
            scope=row[4],
            source_id=row[5],
        )

    def list_documents(self, scopes: list[str] | None = None) -> list[Document]:
        """Return all documents, optionally filtered by *scopes*."""
        if scopes is not None and len(scopes) == 0:
            return []

        params: list[str] = []
        sql = "SELECT id, title, content, metadata, scope, source_id FROM documents"
        if scopes is not None:
            placeholders = ", ".join("?" for _ in scopes)
            sql += f" WHERE scope IN ({placeholders})"
            params.extend(scopes)

        rows = self._conn.execute(sql, params).fetchall()
        return [
            Document(
                id=r[0],
                title=r[1],
                content=r[2],
                metadata=self._load_meta(r[3]),
                scope=r[4],
                source_id=r[5],
            )
            for r in rows
        ]

    def delete_document(self, doc_id: str) -> bool:
        """Delete the document with *doc_id*.

        Returns ``True`` if the document existed, ``False`` otherwise.
        """
        cursor = self._conn.execute(
            "DELETE FROM documents WHERE id = ?",
            (doc_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── Chunk lookup ────────────────────────────────────────────────────────

    def get_document_id_for_chunk(self, chunk_id: str) -> str | None:
        """Return the document_id that owns *chunk_id*, or ``None`` if not found."""
        row = self._conn.execute(
            "SELECT document_id FROM chunks WHERE id = ?",
            (chunk_id,),
        ).fetchone()
        return row[0] if row else None

    def get_chunk(self, chunk_id: str) -> dict[str, object] | None:
        """Return chunk row as a dict, or ``None`` if not found."""
        row = self._conn.execute(
            "SELECT id, document_id, chunk_index, content FROM chunks WHERE id = ?",
            (chunk_id,),
        ).fetchone()
        if not row:
            return None
        return {"id": row[0], "document_id": row[1], "chunk_index": row[2], "content": row[3]}

    def count_chunks_for_document(self, document_id: str) -> int:
        """Return the number of chunks belonging to *document_id*."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        return row[0] if row else 0

    # ── Count operations ───────────────────────────────────────────────────

    def get_counts(self) -> tuple[int, int, int]:
        """Return (doc_count, entity_count, edge_count) via SQL COUNT — O(1).

        Returns:
            A three-tuple of (document count, entity count, edge count).
        """
        doc_count: int = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        entity_count: int = self._conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        edge_count: int = self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        return (doc_count, entity_count, edge_count)
