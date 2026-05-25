"""Contract tests for manual knowledge enrichment persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Edge, EntityType, RelationType
from owlbear_knowledge.schema import init_db
from owlbear_mcp_knowledge.server import (
    _MAX_ENRICHMENT_BATCH_SIZE,
    get_consolidation_candidates,
    get_next_batch,
    get_stats,
    retry_failed_enrichment,
    store_enrichment,
)


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    return connection


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


_CLAIM_TOKEN = "claim-token"


def _ctx(conn: sqlite3.Connection) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.conn = conn
    ctx.request_context.lifespan_context.graph_store = GraphStore(conn)
    return ctx


def _insert_source(conn: sqlite3.Connection, name: str, *, scope: str = "global") -> str:
    source_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO knowledge_sources
        (id, name, source_type, fetch_method, enrich, config, scope, enabled, priority, created_at, updated_at)
        VALUES (?, ?, 'url_list', 'http', 1, '{}', ?, 1, 0, ?, ?)
        """,
        (source_id, name, scope, now, now),
    )
    conn.commit()
    return source_id


def _insert_document(conn: sqlite3.Connection, source_id: str, *, scope: str = "global") -> str:
    document_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)
        VALUES (?, 'Doc', 'content', '{}', ?, ?, ?)
        """,
        (document_id, now, scope, source_id),
    )
    conn.commit()
    return document_id


def _insert_chunk(
    conn: sqlite3.Connection,
    document_id: str,
    *,
    state: str = "claimed",
    index: int = 0,
    scope: str = "global",
) -> str:
    chunk_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state, claim_token)
        VALUES (?, ?, ?, 'chunk text', '{}', ?, ?, ?, ?)
        """,
        (chunk_id, document_id, index, now, scope, state, _CLAIM_TOKEN if state == "claimed" else None),
    )
    conn.commit()
    return chunk_id


def _insert_entity(
    conn: sqlite3.Connection,
    document_id: str,
    name: str,
    *,
    chunk_id: str | None = None,
    scope: str = "global",
) -> str:
    entity_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id, importance)
        VALUES (?, ?, 'concept', 'desc', '{}', ?, ?, ?, ?, 0.5)
        """,
        (entity_id, name, now, scope, document_id, chunk_id),
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
        claim_token=_CLAIM_TOKEN,
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
async def test_phase2_ignores_payload_edge_id_collision(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    entity_a = _insert_entity(conn, doc_a, "Shared Concept")
    entity_b = _insert_entity(conn, doc_b, "Shared Concept")
    conn.execute(
        """
        INSERT INTO edges (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
        VALUES ('collision', ?, ?, 'related_to', ?, 1.0, '{}', ?, 'global')
        """,
        (entity_a, entity_a, doc_a, _now()),
    )
    conn.commit()
    candidate_id = (await get_consolidation_candidates(_ctx(conn), limit=20))[0]["candidate_id"]

    await store_enrichment(
        _ctx(conn),
        candidate_id=candidate_id,
        edges=[{"id": "collision", "source_id": entity_a, "target_id": entity_b, "relation": "same_as"}],
    )

    same_as_row = conn.execute(
        "SELECT source_id, target_id, relation FROM edges WHERE source_id = ? AND target_id = ? AND relation = 'same_as'",
        (entity_a, entity_b),
    ).fetchone()
    assert same_as_row == (entity_a, entity_b, "same_as")
    assert conn.execute("SELECT COUNT(*) FROM reviewed_pairs").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_consolidation_candidates_exclude_cross_scope_entities(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A", scope="alpha")
    source_b = _insert_source(conn, "Source B", scope="beta")
    doc_a = _insert_document(conn, source_a, scope="alpha")
    doc_b = _insert_document(conn, source_b, scope="beta")
    chunk_a = _insert_chunk(conn, doc_a, scope="alpha")
    chunk_b = _insert_chunk(conn, doc_b, scope="beta")
    _insert_entity(conn, doc_a, "Shared Concept", chunk_id=chunk_a, scope="alpha")
    _insert_entity(conn, doc_b, "Shared Concept", chunk_id=chunk_b, scope="beta")

    candidates = await get_consolidation_candidates(_ctx(conn), limit=20)

    assert candidates == []


@pytest.mark.asyncio
@pytest.mark.parametrize("inactive_column", ["enabled", "enrich"])
async def test_consolidation_candidates_exclude_inactive_sources(
    conn: sqlite3.Connection,
    inactive_column: str,
) -> None:
    source_a = _insert_source(conn, "Source A", scope="team-a")
    source_b = _insert_source(conn, "Source B", scope="team-a")
    if inactive_column == "enabled":
        conn.execute("UPDATE knowledge_sources SET enabled = 0 WHERE id = ?", (source_b,))
    else:
        conn.execute("UPDATE knowledge_sources SET enrich = 0 WHERE id = ?", (source_b,))
    doc_a = _insert_document(conn, source_a, scope="team-a")
    doc_b = _insert_document(conn, source_b, scope="team-a")
    _insert_entity(conn, doc_a, "Shared Concept", scope="team-a")
    _insert_entity(conn, doc_b, "Shared Concept", scope="team-a")

    candidates = await get_consolidation_candidates(_ctx(conn), limit=20)

    assert candidates == []


@pytest.mark.asyncio
async def test_consolidation_candidates_ignore_non_consolidation_edges(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    entity_a = _insert_entity(conn, doc_a, "Shared Concept")
    entity_b = _insert_entity(conn, doc_b, "Shared Concept")
    graph = GraphStore(conn)

    graph.insert_edge(Edge(source_id=entity_a, target_id=entity_b, relation=RelationType.RELATED_TO), document_id=doc_a)
    related_candidates = await get_consolidation_candidates(_ctx(conn), limit=20)

    assert len(related_candidates) == 1

    graph.insert_edge(Edge(source_id=entity_a, target_id=entity_b, relation=RelationType.SAME_AS), document_id=doc_a)
    same_as_candidates = await get_consolidation_candidates(_ctx(conn), limit=20)

    assert same_as_candidates == []


@pytest.mark.asyncio
async def test_consolidation_candidates_reject_non_positive_limits(conn: sqlite3.Connection) -> None:
    for limit in (0, -1):
        with pytest.raises(ToolError):
            await get_consolidation_candidates(_ctx(conn), limit=limit)


@pytest.mark.asyncio
async def test_consolidation_candidates_accept_null_limit_as_unlimited(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    _insert_entity(conn, doc_a, "Shared Concept")
    _insert_entity(conn, doc_b, "Shared Concept")

    candidates = await get_consolidation_candidates(_ctx(conn), limit=None)

    assert len(candidates) == 1


@pytest.mark.asyncio
async def test_phase2_rejects_cross_scope_candidate_id(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A", scope="alpha")
    source_b = _insert_source(conn, "Source B", scope="beta")
    doc_a = _insert_document(conn, source_a, scope="alpha")
    doc_b = _insert_document(conn, source_b, scope="beta")
    chunk_a = _insert_chunk(conn, doc_a, scope="alpha")
    chunk_b = _insert_chunk(conn, doc_b, scope="beta")
    entity_a = _insert_entity(conn, doc_a, "Shared Concept", chunk_id=chunk_a, scope="alpha")
    entity_b = _insert_entity(conn, doc_b, "Shared Concept", chunk_id=chunk_b, scope="beta")
    candidate_id = json.dumps(["Shared Concept", source_a, source_b, entity_a, entity_b])

    with pytest.raises(ToolError):
        await store_enrichment(_ctx(conn), candidate_id=candidate_id, edges=[])

    reviewed_count = conn.execute("SELECT COUNT(*) FROM reviewed_pairs").fetchone()[0]
    assert reviewed_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("inactive_column", ["enabled", "enrich"])
async def test_phase2_rejects_inactive_source_candidate_id(
    conn: sqlite3.Connection,
    inactive_column: str,
) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    entity_a = _insert_entity(conn, doc_a, "Shared Concept")
    entity_b = _insert_entity(conn, doc_b, "Shared Concept")
    candidate_id = (await get_consolidation_candidates(_ctx(conn), limit=20))[0]["candidate_id"]
    if inactive_column == "enabled":
        conn.execute("UPDATE knowledge_sources SET enabled = 0 WHERE id = ?", (source_b,))
    else:
        conn.execute("UPDATE knowledge_sources SET enrich = 0 WHERE id = ?", (source_b,))
    conn.commit()

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            candidate_id=candidate_id,
            edges=[{"source_id": entity_a, "target_id": entity_b, "relation": "same_as"}],
        )

    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM reviewed_pairs").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_phase2_invalid_edge_weight_fails_before_review(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    entity_a = _insert_entity(conn, doc_a, "Shared Concept")
    entity_b = _insert_entity(conn, doc_b, "Shared Concept")
    candidate_id = (await get_consolidation_candidates(_ctx(conn), limit=20))[0]["candidate_id"]

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            candidate_id=candidate_id,
            edges=[{"source_id": entity_a, "target_id": entity_b, "relation": "same_as", "weight": -1}],
        )

    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM reviewed_pairs").fetchone()[0] == 0
    assert GraphStore(conn).list_edges() == []


@pytest.mark.asyncio
async def test_phase1_unknown_relation_fails_without_enriching_chunk(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[],
            edges=[{"source_name": "A", "target_name": "B", "relation": "not_a_relation"}],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "failed"


@pytest.mark.asyncio
async def test_phase1_rejects_chunks_when_source_enrichment_is_disabled(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    conn.execute("UPDATE knowledge_sources SET enrich = 0 WHERE id = ?", (source_id,))
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="pending")

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[{"name": "Alpha", "entity_type": "concept"}],
            edges=[],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "pending"
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_phase1_rejects_chunks_when_source_is_disabled(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    conn.execute("UPDATE knowledge_sources SET enabled = 0 WHERE id = ?", (source_id,))
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="pending")

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[{"name": "Alpha", "entity_type": "concept"}],
            edges=[],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "pending"
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_phase1_rejects_failed_chunks_without_persistence(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="failed")

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[{"name": "Alpha", "entity_type": "concept"}],
            edges=[],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "failed"
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_store_enrichment_rejects_ambiguous_mode_without_persistence(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="pending")

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            candidate_id="not-a-real-candidate",
            entities=[],
            edges=[],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "pending"


@pytest.mark.asyncio
async def test_phase1_invalid_entity_optional_fields_fail_before_persistence(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[{"name": "Bad Entity", "entity_type": "concept", "metadata": [], "importance": 5}],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "failed"
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0
    assert GraphStore(conn).list_entities() == []


@pytest.mark.asyncio
async def test_phase1_invalid_edge_weight_fails_before_persistence(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[
                {"id": "entity-a", "name": "A", "entity_type": "concept"},
                {"id": "entity-b", "name": "B", "entity_type": "concept"},
            ],
            edges=[{"source_id": "entity-a", "target_id": "entity-b", "relation": "related_to", "weight": -1}],
        )

    state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert state == "failed"
    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0
    assert GraphStore(conn).list_edges() == []


@pytest.mark.asyncio
async def test_phase1_non_object_edge_payload_rolls_back_and_releases_claim(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[{"id": "entity-a", "name": "A", "entity_type": "concept"}],
            edges=["not-an-object"],  # type: ignore[list-item]
        )

    assert not conn.in_transaction
    state = conn.execute("SELECT enrichment_state, claimed_at FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    assert state == ("failed", None)
    assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_phase1_failure_records_error_and_attempt_count(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=_CLAIM_TOKEN,
            entities=[{"name": "Bad Entity", "entity_type": "not_real"}],
        )

    row = conn.execute(
        """
        SELECT enrichment_state, claimed_at, claim_token, enrichment_attempts, enrichment_error,
               last_enrichment_error_at
        FROM chunks WHERE id = ?
        """,
        (chunk_id,),
    ).fetchone()
    assert row[0:4] == ("failed", None, None, 1)
    assert "unsupported entity_type" in row[4]
    assert row[5] is not None


@pytest.mark.asyncio
async def test_phase1_rejects_missing_claim_token_without_marking_failed(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError, match="claim_token is required"):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            entities=[{"name": "Alpha", "entity_type": "concept"}],
        )

    row = conn.execute(
        "SELECT enrichment_state, claim_token, enrichment_attempts, enrichment_error FROM chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    assert row == ("claimed", _CLAIM_TOKEN, 0, None)


@pytest.mark.asyncio
async def test_phase1_rejects_stale_claim_token_without_marking_failed(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)

    with pytest.raises(ToolError, match="claim_token does not match"):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token="stale-token",
            entities=[{"name": "Alpha", "entity_type": "concept"}],
        )

    row = conn.execute(
        "SELECT enrichment_state, claim_token, enrichment_attempts, enrichment_error FROM chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    assert row == ("claimed", _CLAIM_TOKEN, 0, None)


@pytest.mark.asyncio
async def test_get_stats_exposes_enrichment_queue_state_counts(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    _insert_chunk(conn, document_id, state="pending", index=0)
    _insert_chunk(conn, document_id, state="claimed", index=1)
    _insert_chunk(conn, document_id, state="failed", index=2)
    _insert_chunk(conn, document_id, state="enriched", index=3)

    stats = await get_stats(_ctx(conn))

    assert stats["chunks_pending"] == 1
    assert stats["chunks_claimed"] == 1
    assert stats["chunks_failed"] == 1
    assert stats["chunks_enriched"] == 1
    assert stats["chunks_claimable"] == 1


@pytest.mark.asyncio
async def test_retry_failed_enrichment_resets_failed_chunks_to_pending(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    failed_chunk = _insert_chunk(conn, document_id, state="failed")
    _insert_chunk(conn, document_id, state="enriched")
    conn.execute(
        """
        UPDATE chunks
        SET enrichment_error='bad payload', enrichment_attempts=2, last_enrichment_error_at=?
        WHERE id = ?
        """,
        (_now(), failed_chunk),
    )
    conn.commit()

    result = await retry_failed_enrichment(_ctx(conn), chunk_ids=[failed_chunk])

    assert result == {"reset": 1, "remaining_failed": 0}
    row = conn.execute(
        "SELECT enrichment_state, enrichment_error, enrichment_attempts, last_enrichment_error_at FROM chunks WHERE id = ?",
        (failed_chunk,),
    ).fetchone()
    assert row == ("pending", None, 2, None)


@pytest.mark.asyncio
async def test_phase2_non_object_edge_payload_rolls_back_without_review(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A")
    source_b = _insert_source(conn, "Source B")
    doc_a = _insert_document(conn, source_a)
    doc_b = _insert_document(conn, source_b)
    _insert_entity(conn, doc_a, "Shared Concept")
    _insert_entity(conn, doc_b, "Shared Concept")
    candidate_id = (await get_consolidation_candidates(_ctx(conn), limit=20))[0]["candidate_id"]

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            candidate_id=candidate_id,
            edges=["not-an-object"],  # type: ignore[list-item]
        )

    assert not conn.in_transaction
    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM reviewed_pairs").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_phase1_rejects_entity_id_from_another_chunk(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    doc_a = _insert_document(conn, source_id)
    doc_b = _insert_document(conn, source_id)
    chunk_a = _insert_chunk(conn, doc_a)
    chunk_b = _insert_chunk(conn, doc_b)
    existing_entity_id = _insert_entity(conn, doc_a, "Original", chunk_id=chunk_a)

    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_b,
            claim_token=_CLAIM_TOKEN,
            entities=[{"id": existing_entity_id, "name": "Moved", "entity_type": "concept"}],
        )

    entity_row = conn.execute(
        "SELECT document_id, chunk_id, name FROM entities WHERE id = ?",
        (existing_entity_id,),
    ).fetchone()
    assert entity_row == (doc_a, chunk_a, "Original")
    chunk_b_state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_b,)).fetchone()[0]
    assert chunk_b_state == "failed"


@pytest.mark.asyncio
async def test_phase1_allows_same_scope_cross_document_edge_endpoint_id(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source", scope="team-a")
    doc_a = _insert_document(conn, source_id, scope="team-a")
    doc_b = _insert_document(conn, source_id, scope="team-a")
    chunk_a = _insert_chunk(conn, doc_a, scope="team-a")
    chunk_b = _insert_chunk(conn, doc_b, scope="team-a")
    existing_entity_id = _insert_entity(conn, doc_a, "Existing", chunk_id=chunk_a, scope="team-a")

    await store_enrichment(
        _ctx(conn),
        chunk_id=chunk_b,
        claim_token=_CLAIM_TOKEN,
        entities=[{"id": "local-entity", "name": "Local", "entity_type": "concept"}],
        edges=[{"source_id": existing_entity_id, "target_id": "local-entity", "relation": "related_to"}],
    )

    edge_row = conn.execute(
        "SELECT source_id, target_id, relation, document_id, scope FROM edges WHERE source_id = ?",
        (existing_entity_id,),
    ).fetchone()
    assert edge_row == (existing_entity_id, "local-entity", "related_to", doc_b, "team-a")
    chunk_b_state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_b,)).fetchone()[0]
    assert chunk_b_state == "enriched"


@pytest.mark.asyncio
async def test_phase1_allows_same_chunk_entity_id_retry(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id)
    existing_entity_id = _insert_entity(conn, document_id, "Original", chunk_id=chunk_id)

    await store_enrichment(
        _ctx(conn),
        chunk_id=chunk_id,
        claim_token=_CLAIM_TOKEN,
        entities=[{"id": existing_entity_id, "name": "Original", "entity_type": "concept", "description": "retry"}],
    )

    entity_row = conn.execute(
        "SELECT document_id, chunk_id, description FROM entities WHERE id = ?",
        (existing_entity_id,),
    ).fetchone()
    assert entity_row == (document_id, chunk_id, "retry")
    chunk_state = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()[0]
    assert chunk_state == "enriched"


@pytest.mark.asyncio
async def test_get_next_batch_rejects_non_positive_limits_without_claiming(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    _insert_chunk(conn, document_id, state="pending")

    for limit in (0, -1):
        with pytest.raises(ToolError):
            await get_next_batch(_ctx(conn), limit=limit)

    state = conn.execute("SELECT enrichment_state FROM chunks").fetchone()[0]
    assert state == "pending"


@pytest.mark.asyncio
async def test_get_next_batch_normalizes_nullable_string_fields(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = uuid.uuid4().hex
    chunk_id = uuid.uuid4().hex
    now = _now()
    conn.execute(
        """
        INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)
        VALUES (?, NULL, 'content', '{}', ?, NULL, ?)
        """,
        (document_id, now, source_id),
    )
    conn.execute(
        """
        INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state)
        VALUES (?, ?, 0, 'chunk text', '{}', ?, NULL, 'pending')
        """,
        (chunk_id, document_id, now),
    )
    conn.commit()

    batch = await get_next_batch(_ctx(conn), limit=10)

    assert len(batch) == 1
    assert batch[0] == {
        "chunk_id": chunk_id,
        "text": "chunk text",
        "doc_title": "",
        "section_path": None,
        "source_name": "Source",
        "document_id": document_id,
        "source_id": source_id,
        "scope": "global",
        "claim_token": batch[0]["claim_token"],
        "claimed_at": batch[0]["claimed_at"],
    }
    assert batch[0]["claim_token"]
    assert batch[0]["claimed_at"]


@pytest.mark.asyncio
async def test_get_next_batch_skips_disabled_sources(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    conn.execute("UPDATE knowledge_sources SET enabled = 0 WHERE id = ?", (source_id,))
    document_id = _insert_document(conn, source_id)
    _insert_chunk(conn, document_id, state="pending")

    batch = await get_next_batch(_ctx(conn), limit=10)

    assert batch == []
    state = conn.execute("SELECT enrichment_state FROM chunks").fetchone()[0]
    assert state == "pending"


@pytest.mark.asyncio
async def test_get_next_batch_caps_excessive_limits(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    for index in range(_MAX_ENRICHMENT_BATCH_SIZE + 1):
        _insert_chunk(conn, document_id, state="pending", index=index)

    batch = await get_next_batch(_ctx(conn), limit=_MAX_ENRICHMENT_BATCH_SIZE + 50)

    assert len(batch) == _MAX_ENRICHMENT_BATCH_SIZE
    claimed = conn.execute("SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'claimed'").fetchone()[0]
    assert claimed == _MAX_ENRICHMENT_BATCH_SIZE


@pytest.mark.asyncio
async def test_phase1_claim_token_required_for_token_bearing_claim(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="pending")

    batch = await get_next_batch(_ctx(conn), limit=1)
    assert batch[0]["chunk_id"] == chunk_id
    assert batch[0]["claim_token"]

    with pytest.raises(ToolError, match="claim_token is required"):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            entities=[{"name": "Alpha", "entity_type": "concept"}],
            edges=[],
        )

    state, token = conn.execute(
        "SELECT enrichment_state, claim_token FROM chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    assert state == "claimed"
    assert token == batch[0]["claim_token"]


@pytest.mark.asyncio
async def test_phase1_store_with_matching_claim_token_clears_lease(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="pending")

    batch = await get_next_batch(_ctx(conn), limit=1)
    await store_enrichment(
        _ctx(conn),
        chunk_id=chunk_id,
        claim_token=batch[0]["claim_token"],
        entities=[{"name": "Alpha", "entity_type": "concept"}],
        edges=[],
    )

    state, token, error = conn.execute(
        "SELECT enrichment_state, claim_token, enrichment_error FROM chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    assert (state, token, error) == ("enriched", None, None)


@pytest.mark.asyncio
async def test_phase1_failed_matching_claim_records_diagnostics(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="pending")

    batch = await get_next_batch(_ctx(conn), limit=1)
    with pytest.raises(ToolError):
        await store_enrichment(
            _ctx(conn),
            chunk_id=chunk_id,
            claim_token=batch[0]["claim_token"],
            entities=[{"name": "Bad", "entity_type": "not_an_entity_type"}],
            edges=[],
        )

    state, token, error, attempts = conn.execute(
        """
        SELECT enrichment_state, claim_token, enrichment_error, enrichment_attempts
        FROM chunks WHERE id = ?
        """,
        (chunk_id,),
    ).fetchone()
    assert state == "failed"
    assert token is None
    assert error
    assert attempts == 1


@pytest.mark.asyncio
async def test_retry_failed_enrichment_resets_failed_chunks(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_id = _insert_chunk(conn, document_id, state="failed")
    conn.execute(
        "UPDATE chunks SET enrichment_error = 'bad payload', enrichment_attempts = 2 WHERE id = ?",
        (chunk_id,),
    )
    conn.commit()

    result = await retry_failed_enrichment(_ctx(conn), chunk_ids=[chunk_id])

    assert result == {"reset": 1, "remaining_failed": 0}
    state, error = conn.execute(
        "SELECT enrichment_state, enrichment_error FROM chunks WHERE id = ?",
        (chunk_id,),
    ).fetchone()
    assert (state, error) == ("pending", None)


@pytest.mark.asyncio
async def test_retry_failed_enrichment_resets_scoped_failed_chunks(conn: sqlite3.Connection) -> None:
    source_a = _insert_source(conn, "Source A", scope="team-a")
    source_b = _insert_source(conn, "Source B", scope="team-b")
    document_a = _insert_document(conn, source_a, scope="team-a")
    document_b = _insert_document(conn, source_b, scope="team-b")
    chunk_a = _insert_chunk(conn, document_a, state="failed", scope="team-a")
    chunk_b = _insert_chunk(conn, document_b, state="failed", scope="team-b")
    conn.execute(
        "UPDATE chunks SET enrichment_error = 'bad payload' WHERE id IN (?, ?)",
        (chunk_a, chunk_b),
    )
    conn.commit()

    result = await retry_failed_enrichment(_ctx(conn), scopes=["team-a"], limit=10)

    assert result == {"reset": 1, "remaining_failed": 1}
    rows = conn.execute(
        "SELECT id, enrichment_state FROM chunks WHERE id IN (?, ?)",
        (chunk_a, chunk_b),
    ).fetchall()
    states = {row[0]: row[1] for row in rows}
    assert states[chunk_a] == "pending"
    assert states[chunk_b] == "failed"


@pytest.mark.asyncio
async def test_retry_failed_enrichment_limit_without_scope_resets_only_limited_rows(
    conn: sqlite3.Connection,
) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    chunk_a = _insert_chunk(conn, document_id, state="failed", index=0)
    chunk_b = _insert_chunk(conn, document_id, state="failed", index=1)
    conn.execute(
        "UPDATE chunks SET enrichment_error = 'bad payload' WHERE id IN (?, ?)",
        (chunk_a, chunk_b),
    )
    conn.commit()

    result = await retry_failed_enrichment(_ctx(conn), limit=1)

    assert result == {"reset": 1, "remaining_failed": 1}
    pending_count = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'pending'",
    ).fetchone()[0]
    failed_count = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE enrichment_state = 'failed'",
    ).fetchone()[0]
    assert pending_count == 1
    assert failed_count == 1


@pytest.mark.asyncio
async def test_retry_failed_enrichment_rolls_back_when_update_raises() -> None:
    conn = MagicMock()

    def _execute(sql: str, params: object = ()) -> MagicMock:  # noqa: ARG001
        if sql in {"PRAGMA busy_timeout = 5000", "BEGIN IMMEDIATE"}:
            return MagicMock()
        msg = "forced retry failure"
        raise sqlite3.OperationalError(msg)

    conn.execute.side_effect = _execute
    ctx = MagicMock()
    ctx.request_context.lifespan_context.conn = conn

    with pytest.raises(sqlite3.OperationalError, match="forced retry failure"):
        await retry_failed_enrichment(ctx, chunk_ids=["chunk-1"])

    conn.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_stats_exposes_enrichment_queue_state_counts(conn: sqlite3.Connection) -> None:
    source_id = _insert_source(conn, "Source")
    document_id = _insert_document(conn, source_id)
    _insert_chunk(conn, document_id, state="pending")
    _insert_chunk(conn, document_id, state="claimed")
    _insert_chunk(conn, document_id, state="failed")
    _insert_chunk(conn, document_id, state="enriched")
    ctx = _ctx(conn)
    ctx.request_context.lifespan_context.graph_store = GraphStore(conn)

    stats = await get_stats(ctx)

    assert stats["chunks_pending"] == 1
    assert stats["chunks_claimed"] == 1
    assert stats["chunks_failed"] == 1
    assert stats["chunks_enriched"] == 1
    assert stats["chunks_claimable"] == 1
