---
id: 97
title: 'Test: Knowledge engine foundation layer'
status: archived
priority: medium
created: 2026-03-28 03:43:11.357637+01:00
updated: 2026-03-30 15:36:00.849490+02:00
started: 2026-03-30 15:18:48.042985+02:00
completed: 2026-03-30 15:18:48.042985+02:00
tags:
- phase-1
- scope:knowledge
- test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-29]] Sun 12:44
## Architecture Review
**Verdict:** BLOCK (duplicate)

### AC Assessment
All 11 AC lines in #97 are identical to (or a subset of) the 31 AC lines in #107, which was merged from #97 and archived at .97 confidence.

### Architecture Notes
Task #107 body explicitly states: "Merged from #97 (duplicate test task)." The test file tests/test_knowledge_foundation.py (69 tests) was written and verified through the #107 pipeline. All GraphStore, KnowledgeSourceStore, model validation, and protocol type tests are passing. No remaining work exists for #97.

### Changes Made
- Blocked to ideation as stale duplicate
- Released claim

### Dependencies
- #107 (archived) completed all work from #97

## Audit (manual archival 2026-03-30) Duplicate of #107 (archived). 69 tests in test_knowledge_foundation.py. Confidence 1.0.
