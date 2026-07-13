---
id: 15
title: Extract knowledge engine from v1
status: archived
priority: medium
created: 2026-03-26 17:21:09.612643+01:00
updated: 2026-03-29 16:05:02.303883+02:00
started: 2026-03-29 16:04:25.804447+02:00
completed: 2026-03-29 16:04:25.804447+02:00
tags:
- phase-1
- scope:knowledge
- type:build
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Extract the knowledge engine foundation layer from v1 src/owlbear/memory/knowledge/ into v2 packages/knowledge/src/owlbear_knowledge/ as a standalone package.

## Acceptance Criteria

### Foundation modules extracted
- [ ] models.py: Entity, Edge, Document, KnowledgeSource, EntityType, RelationType, SourceType -- frozen Pydantic models with ConfigDict(frozen=True)
- [ ] schema.py: init_db() creates all tables (documents, entities, edges, chunks, document_status, knowledge_sources, bookmarks, consolidations, schema_version), idempotent, schema_version == 8
- [ ] graph_store.py: GraphStore class -- entity/edge/document CRUD, merge_entities (redirect edges + delete duplicates), get_neighbors (BFS with max_depth/max_nodes)
- [ ] protocol.py: VectorStoreProtocol (runtime_checkable Protocol), SparseVector, HybridEmbedding, Embedding alias
- [ ] source_store.py: KnowledgeSourceStore -- CRUD (create, get_by_id, list with scope/type filter, update, delete) over knowledge_sources table
- [ ] status_store.py: StatusStore (set_status, find_status_by_source, check_content_changed, update_content_hash), DocumentStatus model, compute_content_hash -- split from v1 document_store.py per research recommendation
- [ ] bookmark_store.py: BookmarkStore (sqlite CRUD for bookmarks with scope/tag filtering) + Bookmark model

### Package configuration
- [ ] pyproject.toml name=owlbear-knowledge, requires-python>=3.12, dependency pydantic>=2.10.0; optional-dependencies qdrant=[qdrant-client>=1.9.0] embedding=[FlagEmbedding>=1.2.0]
- [ ] __init__.py re-exports: GraphStore, KnowledgeSourceStore, StatusStore, DocumentStatus, compute_content_hash, init_db, Bookmark, BookmarkStore
- [ ] src-layout: packages/knowledge/src/owlbear_knowledge/

### Import path migration
- [ ] All internal imports use owlbear_knowledge.* (zero references to owlbear.memory.knowledge.*)
- [ ] Zero PydanticAI, daemon, or hook imports in any foundation module

### Verification
- [ ] tests/test_knowledge_foundation.py passes (69 tests covering all foundation store CRUD, model validation, protocol types, init_db, public exports)
- [ ] Package installable: uv pip install -e packages/knowledge/ succeeds
- [ ] ruff check packages/knowledge/src/owlbear_knowledge/ passes

## TDD Compliance
Test task #107 (archived, .97 confidence) provided RED-phase tests for all foundation modules. 69 tests written and verified. No additional test task needed.

## Context
Depends on #7 (monorepo skeleton, archived). Downstream: #32 (vector store + embedding), #33 (entity extraction + graph builders), #34 (integration + hybrid search) depend on this task.

Note: Additional extraction modules (qdrant.py, embeddings.py, extractor.py, graph_builder.py, query_service.py, chunker.py) were extracted ahead of schedule under #15 commits. Their full verification, testing, and integration are owned by #32/#33/#34 respectively. See docs/research/extract-knowledge-engine-v1.md.

[[2026-03-29]] Sun 15:03
## Test-Writer Notes
- Pre-existing test file: tests/test_knowledge_foundation.py (written under task #107, archived .97 confidence)
- 72 tests, all PASS (implementation already complete)
- ruff: clean
- AC explicitly states: No additional test task needed
- Pass-through: advancing to in-progress for builder verification.

[[2026-03-29]] Sun 15:31
## Builder Notes
- Files changed: packages/knowledge/pyproject.toml, src/owlbear_knowledge/{bookmark_store,chunker,embeddings,extractor,graph_builder,qdrant,query_service}.py, tests/test_bookmark_store.py
- Tests: 72 passed (test_knowledge_foundation.py), 55 passed (test_bookmark_store.py), 127 combined
- Coverage: models/schema/protocol/status_store 100%, bookmark_store 99%, graph_store 94%, source_store 93%
- Lint: ruff clean
- Package installable: uv pip install -e packages/knowledge/ OK
- Commit: 260895f

[[2026-03-29]] Sun 16:04
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| models.py frozen Pydantic models | ConfigDict(frozen=True) on Entity, Edge, Document, KnowledgeSource; StrEnums for types | PASS |
| schema.py init_db, schema_version 8 | _SCHEMA_VERSION=8 at L19, init_db exported | PASS |
| graph_store.py GraphStore, merge_entities, get_neighbors | Class L25, merge L276, neighbors L306 | PASS |
| protocol.py VectorStoreProtocol, SparseVector, HybridEmbedding, Embedding | All present, runtime_checkable | PASS |
| source_store.py CRUD | create L67, get L90 (named get not get_by_id), list_all L100, update L113, delete L143 | PASS |
| status_store.py StatusStore, DocumentStatus, compute_content_hash | All methods present: set_status, find_status_by_source, check_content_changed, update_content_hash | PASS |
| bookmark_store.py BookmarkStore + Bookmark | Present, exported from __init__ | PASS |
| pyproject.toml config | name=owlbear-knowledge, python>=3.12, pydantic>=2.10.0, qdrant/embedding optionals | PASS |
| __init__.py re-exports | All 9 symbols exported | PASS |
| src-layout | packages/knowledge/src/owlbear_knowledge/ | PASS |
| Zero old imports | grep owlbear.memory.knowledge: 0 hits | PASS |
| Zero PydanticAI/daemon/hook imports | Only .daemon attr on Timer, not an import | PASS |
| Tests pass | 127 passed (72 foundation + 55 bookmark) in 0.36s | PASS |
| Package installable | uv pip install -e OK | PASS |
| Ruff clean | ruff check passed | PASS |

### Test Results
- pytest: 127 passed, 0 failed (task-scoped); 129 passed full suite (4 collection errors unrelated)
- ruff: clean

### AC Quality Score: 4/5
AC was specific and complete. Minor gap: AC said get_by_id but impl uses get (functionally equivalent). AC said 69 tests but 72+55=127 exist and pass.

### Quality Gaps
- No Review Evidence section in task body (reviewer pipeline gap)
- No Docs Gate section in task body (writer pipeline gap)
- source_store.get vs AC get_by_id (cosmetic only)

### Confidence: .95
### Action: archived

[[2026-03-29]] Sun 16:05
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 02ce42e | chore | kanban/tasks/015-*.md | #15 |
