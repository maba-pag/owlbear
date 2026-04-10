---
id: 757
title: 'P1-02: Impl — Schema extensions'
status: backlog
priority: critical
created: '2026-04-10T10:55:57.126815+00:00'
updated: '2026-04-10T11:53:24.580975+00:00'
tags:
- phase-1
- scope:knowledge
- schema
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. Implement all schema elements from P1-01 (#754):
- AUTHENTICATED_WEB SourceType
- Corporate EntityType/RelationType values
- SourcePage model + table
- source_id FK on documents
- Cascade delete

All P1-01 tests pass.

Parent: #751. Depends on: #754

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/757-schema-extensions.md
- Sources: 9 studied (all internal), 7 high-relevance
- Recommendation: Proceed with implementation as specified (confidence: .88)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none (T1 — additive changes following established patterns)

### Key Findings
1. All enum additions are safely additive — llm_extractor.py dynamically iterates members, MCP server validates dynamically. No consumer breaks.
2. **Test conflict**: `test_remove_crawl_stubs_703.py::test_source_type_valid_values_only` (L38) hardcodes `expected = {"url_list", "file_glob"}` — will fail after AUTHENTICATED_WEB is added. Builder must relax this guard test.
3. Schema v8 to v9 migration follows established pattern (see v5-v8 chain). CREATE TABLE source_pages + ALTER TABLE documents ADD COLUMN source_id.
4. Cascade delete: reuse existing `delete_document_data()` per-document, add `delete_source_cascade(source_id)` orchestrating source-level teardown.
5. source_id FK is logically enforced (application-level cascade), consistent with existing codebase pattern.
6. 6 files to modify, ~115 LOC estimated. No architecture change.

### Implementation files
- models.py: enum additions + PageStatus StrEnum + SourcePage model + Document.source_id
- schema.py: source_pages DDL + v9 migration + indexes
- __init__.py: SourcePage export
- document_store.py: delete_source_cascade + source_id in insert path
- graph_store.py: source_id in document CRUD
- test_remove_crawl_stubs_703.py: relax SourceType guard

## Challenge Results
- Challenger: FALLBACK — subagent not available
- Confidence in original: .88
- Key challenges: self-challenged DB-level CASCADE vs app-level cascade. Rejected — codebase uses app-level exclusively.
- Researcher response: accepted — consistency with existing patterns