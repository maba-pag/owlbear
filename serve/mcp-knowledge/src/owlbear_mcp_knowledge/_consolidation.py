"""Phase-2 consolidation: cross-source candidate queries and persistence."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp.exceptions import ToolError

from ._helpers import _extract_relation, _stable_edge_id, _validate_enrichment_edge_payload
from ._types import _CANDIDATE_ID_BASE_PARTS, _CANDIDATE_ID_EXTENDED_PARTS, _CANDIDATE_SOURCE_COUNT

if TYPE_CHECKING:
    import sqlite3


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
            JOIN knowledge_sources AS ks1 ON ks1.id = d1.source_id
            JOIN knowledge_sources AS ks2 ON ks2.id = d2.source_id
            LEFT JOIN chunks AS c1 ON c1.id = e1.chunk_id
            LEFT JOIN chunks AS c2 ON c2.id = e2.chunk_id
            WHERE d1.source_id IS NOT NULL
              AND d2.source_id IS NOT NULL
              AND d1.source_id != d2.source_id
                            AND ks1.enabled = 1
                            AND ks2.enabled = 1
                            AND ks1.enrich = 1
                            AND ks2.enrich = 1
                            AND COALESCE(e1.scope, 'global') = COALESCE(e2.scope, 'global')
                            AND COALESCE(d1.scope, 'global') = COALESCE(d2.scope, 'global')
              AND NOT EXISTS (
                  SELECT 1
                  FROM edges AS ed
                        WHERE (
                                (ed.source_id = e1.id AND ed.target_id = e2.id)
                            OR (ed.source_id = e2.id AND ed.target_id = e1.id)
                        )
                          AND ed.relation = 'same_as'
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


def _count_consolidation_candidates(conn: sqlite3.Connection) -> int:
    """Count unresolved consolidation candidates without materializing rows."""
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
                END AS source_b
            FROM entities AS e1
            JOIN entities AS e2 ON e1.name = e2.name AND e1.id < e2.id
            JOIN documents AS d1 ON d1.id = e1.document_id
            JOIN documents AS d2 ON d2.id = e2.document_id
            JOIN knowledge_sources AS ks1 ON ks1.id = d1.source_id
            JOIN knowledge_sources AS ks2 ON ks2.id = d2.source_id
            WHERE d1.source_id IS NOT NULL
              AND d2.source_id IS NOT NULL
              AND d1.source_id != d2.source_id
              AND ks1.enabled = 1
              AND ks2.enabled = 1
              AND ks1.enrich = 1
              AND ks2.enrich = 1
              AND COALESCE(e1.scope, 'global') = COALESCE(e2.scope, 'global')
              AND COALESCE(d1.scope, 'global') = COALESCE(d2.scope, 'global')
              AND NOT EXISTS (
                  SELECT 1
                  FROM edges AS ed
                  WHERE (
                      (ed.source_id = e1.id AND ed.target_id = e2.id)
                      OR (ed.source_id = e2.id AND ed.target_id = e1.id)
                  )
                  AND ed.relation = 'same_as'
              )
        ),
        deduplicated AS (
            SELECT pc.entity_name, pc.entity_id_a, pc.entity_id_b, pc.source_a, pc.source_b
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
        )
        SELECT COUNT(*) FROM deduplicated
    """
    return conn.execute(sql).fetchone()[0]


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
                    AND COALESCE(e1.scope, 'global') = COALESCE(e2.scope, 'global')
                    AND COALESCE(d1.scope, 'global') = COALESCE(d2.scope, 'global')
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


def _validate_active_candidate_sources(conn: sqlite3.Connection, *, source_a: str, source_b: str) -> None:
    """Ensure candidate source endpoints are still active for phase-2 writes."""
    active_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM knowledge_sources
        WHERE id IN (?, ?)
          AND enabled = 1
          AND enrich = 1
        """,
        (source_a, source_b),
    ).fetchone()
    if active_count is None or active_count[0] != _CANDIDATE_SOURCE_COUNT:
        msg = "candidate_id does not resolve to active source endpoints"
        raise ToolError(msg)


def _resolve_candidate_identity(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
) -> tuple[str, str, str, str, str]:
    """Resolve candidate identity to a durable row pair and source pair."""
    entity_name, source_a, source_b, id_a, id_b = _decode_candidate_id(candidate_id)
    _validate_active_candidate_sources(conn, source_a=source_a, source_b=source_b)
    if id_a is not None and id_b is not None:
        row = conn.execute(
            """
            SELECT
                e1.id,
                e2.id,
                d1.source_id,
                d2.source_id,
                e1.name,
                e2.name,
                e1.scope,
                e2.scope,
                d1.scope,
                d2.scope
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
            or (row[6] or "global") != (row[7] or "global")
            or (row[8] or "global") != (row[9] or "global")
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


def _load_phase2_edge_provenance(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    target_id: str,
) -> tuple[str, str, dict[str, list[str] | str]]:
    """Derive edge document/scope metadata from candidate endpoints."""
    row = conn.execute(
        """
        SELECT
            source_entity.document_id,
            source_entity.scope,
            source_doc.source_id,
            target_entity.document_id,
            target_entity.scope,
            target_doc.source_id
        FROM entities AS source_entity
        JOIN entities AS target_entity ON target_entity.id = ?
        LEFT JOIN documents AS source_doc ON source_doc.id = source_entity.document_id
        LEFT JOIN documents AS target_doc ON target_doc.id = target_entity.document_id
        WHERE source_entity.id = ?
        """,
        (target_id, source_id),
    ).fetchone()
    if row is None or not isinstance(row[0], str) or not isinstance(row[3], str):
        msg = "edge endpoints must resolve to persisted documents"
        raise ToolError(msg)

    source_scope = row[1] if isinstance(row[1], str) and row[1] else "global"
    target_scope = row[4] if isinstance(row[4], str) and row[4] else source_scope
    if target_scope != source_scope:
        msg = "edge endpoints must be in the same scope"
        raise ToolError(msg)

    source_ids = [value for value in (row[2], row[5]) if isinstance(value, str)]
    return (
        row[0],
        source_scope,
        {
            "phase": "phase2",
            "document_ids": [row[0], row[3]],
            "source_ids": source_ids,
        },
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
            edge_document_id, edge_scope, provenance_metadata = _load_phase2_edge_provenance(
                conn,
                source_id=resolved_source_id,
                target_id=resolved_target_id,
            )
            edge_metadata = {**edge_metadata, **provenance_metadata}
            edge_id = _stable_edge_id(
                "phase2",
                candidate_id,
                resolved_source_id,
                resolved_target_id,
                relation,
            )
            validated_edge = _validate_enrichment_edge_payload(
                {
                    "id": edge_id,
                    "source_id": resolved_source_id,
                    "target_id": resolved_target_id,
                    "relation": relation,
                    "weight": edge.get("weight", 1.0),
                    "metadata": edge_metadata,
                    "scope": edge_scope,
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
                    edge_document_id,
                    validated_edge.weight,
                    json.dumps(validated_edge.metadata),
                    now_iso,
                    validated_edge.scope,
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
