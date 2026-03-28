---
id: 97
title: 'Test: Knowledge engine foundation layer'
status: backlog
priority: needed
created: 2026-03-28T03:43:11.3576373+01:00
updated: 2026-03-28T03:43:18.0811771+01:00
tags:
    - phase-1
    - scope:knowledge
    - test
depends_on:
    - 7
class: standard
---

## Objective
Write failing tests (TDD RED) for the knowledge engine foundation layer extracted in #15.

## Acceptance Criteria
- [ ] tests/test_knowledge_foundation.py created
- [ ] Tests for init_db: creates all expected tables; idempotent (calling twice does not error); schema_version = 8
- [ ] Tests for GraphStore entity CRUD: insert_entity, get_entity, list_entities (type/scope filters), delete_entity (cascades edges), list_entities_for_document
- [ ] Tests for GraphStore edge CRUD: insert_edge, get_edge, list_edges (source/target/scope filters), delete_edge
- [ ] Tests for GraphStore document CRUD: insert_document, get_document, list_documents (scope filter), delete_document
- [ ] Tests for GraphStore.merge_entities: merges duplicates, redirects edges, deletes duplicates
- [ ] Tests for GraphStore.get_neighbors: BFS traversal respects max_depth and max_nodes
- [ ] Tests for KnowledgeSourceStore CRUD: create, get_by_id, list (scope/type filters), update, delete
- [ ] Tests for model validation: Entity with valid/invalid EntityType, Edge with valid RelationType, frozen model rejects mutation
- [ ] Tests for protocol types: SparseVector, HybridEmbedding instantiation, Embedding alias
- [ ] All tests import from owlbear_knowledge package (not v1 paths)
- [ ] All tests fail (RED) before builder implements #15
