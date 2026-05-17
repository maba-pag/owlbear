"""Contract tests for manual knowledge enrichment persistence."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import EntityType, RelationType
from owlbear_knowledge.schema import init_db
from owlbear_mcp_knowledge.server import get_consolidation_candidates, store_enrichment


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    return connection


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _ctx(conn: sqlite3.Connection) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.conn = conn
    return ctx


def _insert_source(conn: sqlite3.Connection, name: str) -> str:
    source_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO knowledge_sources
        (id, name, source_type, fetch_method, enrich, config, scope, enabled, priority, created_at, updated_at)
        VALUES (?, ?, 'url_list', 'http', 1, '{}', 'global', 1, 0, ?, ?)
        """,
        (source_id, name, now, now),
    )
    conn.commit()
    return source_id


def _insert_document(conn: sqlite3.Connection, source_id: str) -> str:
    document_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)
        VALUES (?, 'Doc', 'content', '{}', ?, 'global', ?)
        """,
        (document_id, now, source_id),
    )
    conn.commit()
    return document_id


def _insert_chunk(conn: sqlite3.Connection, document_id: str) -> str:
    chunk_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state)
        VALUES (?, ?, 0, 'chunk text', '{}', ?, 'global', 'claimed')
        """,
        (chunk_id, document_id, now),
    )
    conn.commit()
    return chunk_id


def _insert_entity(conn: sqlite3.Connection, document_id: str, name: str) -> str:
    entity_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id, importance)
        VALUES (?, ?, 'concept', 'desc', '{}', ?, 'global', ?, NULL, 0.5)
        """,
        (entity_id, name, now, document_id),
    )
    conn.commit()
    return entity_id


@pytest.mark.asyncio
async def test_phase1_name_only_edges_create_readable_default_entities(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    await store_enrichment(
        _ctx(conn),
        chunk_id=chunk_id,
        entities=[],
        edges=[{"source_name": "Azure DevOps", "target_name": "CI/CD Pipeline", "relation": "hosts"}],
    )

    graph = GraphStore(conn)
    entities = graph.list_entities()
    edges = graph.list_edges()

    assert {entity.entity_type for entity in entities} == {EntityType.CONCEPT}
    assert [edge.relation for edge in edges] == [RelationType.HOSTS]


@pytest.mark.asyncio
async def test_phase2_edge_without_document_id_persists_readable_edge(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    entity_a = _insert_entity(conn, doc_a, "Shared Concept")
    entity_b = _insert_entity(conn, doc_b, "Shared Concept")

    candidates = await get_consolidation_candidates(_ctx(conn), limit=20)
    candidate_id = candidates[0]["candidate_id"]

    await store_enrichment(
        _ctx(conn),
        candidate_id=candidate_id,
        edges=[{"source_id": entity_a, "target_id": entity_b, "relation": "same_as"}],
    )

    row = conn.execute("SELECT document_id, scope FROM edges WHERE relation = 'same_as'").fetchone()
    assert row == (doc_a, "global")
    assert GraphStore(conn).list_edges()[0].relation == RelationType.SAME_AS


@pytest.mark.asyncio
async def test_phase1_unknown_relation_fails_without_enriching_chunk(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            entities=[],
            edges=[{"source_name": "A", "target_name": "B", "relation": "not_a_relation"}],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "failed"
