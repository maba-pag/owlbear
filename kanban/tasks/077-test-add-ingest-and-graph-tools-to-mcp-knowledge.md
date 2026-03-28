---
id: 77
title: 'Test: Add ingest and graph tools to mcp-knowledge'
status: backlog
priority: important
created: 2026-03-26T21:02:00.1833273+01:00
updated: 2026-03-26T21:02:00.1833273+01:00
tags:
    - phase-2
    - scope:mcp
    - scope:knowledge
    - test
depends_on:
    - 54
class: standard
---

## Objective
Write failing tests (TDD RED) for ingest/graph tools before the builder implements #55.

## Acceptance Criteria
- [ ] Test file: packages/mcp-knowledge/tests/test_ingest_graph_tools.py with pytest tests
- [ ] Test: ingest_document with valid text returns summary string matching format 'Ingested: {id}, {n} chunks, {n} entities, {n} edges (status: {status})'
- [ ] Test: ingest_document passes metadata dict through to IngestPipeline.ingest_text
- [ ] Test: ingest_document returns error string (no traceback) when pipeline raises exception
- [ ] Test: list_entities with no filters returns formatted entity list including total_count
- [ ] Test: list_entities with entity_type filter forwards filter to GraphStore.list_entities
- [ ] Test: list_entities with offset=10, limit=5 returns correct slice of results
- [ ] Test: list_entities returns appropriate message when no entities exist
- [ ] Test: get_stats returns formatted string 'Knowledge base: {n} documents, {n} entities, {n} edges'
- [ ] Test: get_stats with empty database returns all zeros
- [ ] Test: GraphStore.get_counts() returns (doc_count, entity_count, edge_count) via SQL COUNT queries
- [ ] All tests use mocked IngestPipeline and GraphStore; no real DB, Qdrant, or network
- [ ] All tests FAIL at this point (RED phase)

## Context
Preceding test task for #55. See docs/research/ingest-graph-tools-mcp-knowledge.md section 3.6 for testing strategy.
Depends on #54 completing (real lifespan with DB connections must exist before extending with IngestPipeline).
