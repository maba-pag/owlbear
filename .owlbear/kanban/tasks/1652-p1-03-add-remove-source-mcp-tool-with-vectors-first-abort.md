---
id: 1652
title: 'P1-03: Add remove_source MCP tool with vectors-first abort'
status: in-progress
priority: needed
created: 2026-05-18T03:11:06.889695+02:00
updated: 2026-05-18T04:12:03.804103+02:00
tags:
  - scope:mcp-knowledge
  - mcp-tools
parent: 1650
depends_on: []
ac:
  - 'AC-1: `AppContext` has a `vector_store` field typed `QdrantVectorStore | None`;
    `app_lifespan` wires the existing `QdrantVectorStore` instance (`vs`) into it'
  - "AC-2: `remove_source(source_id: str)` MCP tool registered with `destructiveHint=True`:
    given a source_id present in `knowledge_sources`, collects chunk IDs via SQL join
    (`chunks.document_id` → `documents.source_id`), deletes each chunk's vector via
    `QdrantVectorStore.delete_embedding`, then calls `source_store.delete_cascade(source_id)`;
    returns a dict with counts of deleted documents, chunks, and entities"
  - 'AC-3: Given a `QdrantVectorStore.delete_embedding` call that raises an exception
    for any chunk ID, `remove_source` raises `ToolError` without calling `delete_cascade`;
    SQLite data remains intact — `delete_embedding` returning `False` (missing vector)
    is not an abort condition'
  - 'AC-4: Before calling `delete_cascade`, `remove_source` logs an audit entry via
    `logger.info` containing source_id, source name, and the counts of documents,
    chunks, and entities about to be deleted'
  - 'AC-5: Given a source_id not present in `knowledge_sources`, `remove_source` raises
    `ToolError`; no vector deletions or SQL changes occur'
proof_bundle: behavioral
blocked: true
block_reason: 'builder crashed twice: pre-existing uncommitted changes in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
  prevent safe commit isolation'
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Extend `AppContext` with `vector_store` field; wire new `remove_source` MCP tool; implement vectors-first abort semantics.

**Out-of-scope:** Dry-run mode (excluded per brief D6). Refresh logic (O2). Health exposure (O1). Config field exposure.

## Context

Execution order per brief:
1. Collect chunk IDs from source's documents (SQL: chunks.document_id → documents.source_id)
2. Delete vectors from Qdrant for those chunk IDs (`QdrantVectorStore.delete_embedding`)
3. If any vector deletion fails → abort, return `ToolError`, source stays intact
4. Run `source_store.delete_cascade` (SQLite transaction)
5. Return deletion counts

`AppContext` currently has `source_store` and `conn` but no `vector_store`. Lifespan builds `vs = QdrantVectorStore(location=qdrant_path)` — wire it into `AppContext`.

`document_store.delete_chunk_embeddings` uses best-effort (catches exceptions). This tool needs strict abort — implement strict deletion loop directly in the tool handler.

[[2026-05-18T03:19:32+02:00]]
## Research
- Research doc: .owlbear/research/1652-remove-source-mcp-tool.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: proceed as specified in brief (confidence: 0.92)
- Key findings: AppContext needs `vector_store` field; SQL join for chunk IDs; strict abort via try/except on `delete_embedding`; count queries before cascade

[[2026-05-18T03:19:49+02:00]]
## Research
- Research doc: .owlbear/research/1652-remove-source-mcp-tool.md
- Sources: 6 studied (4 codebase, 1 external SDK, 1 schema), 4 high-relevance
- Recommendation: proceed as specified in brief (confidence: 0.92)
- Key findings:
  - AppContext needs `vector_store: QdrantVectorStore | None = None` field; lifespan wires existing `vs`
  - SQL join `chunks c JOIN documents d ON c.document_id = d.id WHERE d.source_id = ?` for chunk IDs
  - Strict abort via try/except on `delete_embedding` (NOT best-effort like `delete_chunk_embeddings`)
  - Count queries (docs, chunks, entities) must run BEFORE `delete_cascade`
  - `delete_embedding` returns False for missing vectors (ok), raises on Qdrant errors (abort trigger)
- Challenge: skipped — implementation follows pre-approved brief with no design alternatives
- Follow-up tasks: none needed — #1652 is the implementation task
- Attribution: MCP Python SDK added to sources/overview.md

[[2026-05-18T03:39:32+02:00]]
## Architecture Review

**Verdict:** APPROVED (after AC refinement)
**Proof bundle:** behavioral (confirmed — contained new tool + one DI field, consolidation test #1655 gates integration)

### AC Assessment

| AC | Assessment | Action |
|-----|-----------|--------|
| AC-1 | Clean. Single structural change: field + wiring. `app_lifespan` at server.py L1296 builds `vs` but doesn't pass it to AppContext — AC addresses this gap. | No change |
| AC-2 | Refined. Removed B3-banned word \"valid\"; replaced with \"present in knowledge_sources\". Clarified SQL join path and return type (dict). | Rewritten |
| AC-3 | Refined. Clarified False vs exception semantics: `delete_embedding` returning False (missing vector) is not abort; only raised exceptions trigger abort + ToolError. | Rewritten |
| AC-4 | Clean. `remove_source` named as explicit subject. Removed \"timestamp\" (logger provides this automatically). | Minor edit |
| AC-5 | Added. Nonexistent source_id → ToolError. Follows `refresh_source` pattern at server.py L1547 (`store.get()` → None → ToolError). | New |

### Architecture Notes

- **Module layering:** MCP server layer → knowledge domain layer. Correct direction.
- **AppContext field:** Direct `vector_store` field preferred over reaching through `query_service.vector_store` (Law of Demeter). Existing AppContext pattern exposes services directly.
- **Vectors-first design:** Brief D8 decision. Tradeoff: missing vectors + surviving SQLite (recoverable via re-ingest) preferred over orphaned vectors (unrecoverable). Post-vector SQL failure is low risk — `delete_cascade` is a single SQLite transaction.
- **Strict abort vs best-effort:** `delete_chunk_embeddings` in document_store.py L278 is best-effort (catches all exceptions). This tool's AC-3 explicitly requires strict abort — different pattern, justified by destructive semantics.
- **`__all__` export:** Builder should add `remove_source` to `__all__` at server.py L1339 following existing pattern.

### Dependency Analysis

- No upstream dependencies (parallel with O2/O1).
- Downstream: consolidation test #1655 depends on this task.
- Sibling tasks verified under parent #1650.

### Challenger Results

Challenger recommended `block` (confidence 0.41). Override rationale:
1. Post-vector SQL failure: Design intent per brief D8, not an AC gap.
2. AC quality: Addressed — AC-2 rewritten (B3 fix), AC-3 clarified, AC-5 added.
3. Proof bundle: `behavioral` appropriate — contained new feature, #1655 consolidation test exists.
4. AppContext necessity: LoD justifies direct field over reaching through query_service.
5. Audit scope: docs/chunks/entities are primary data objects; edges/source_pages are derived artifacts.

[[2026-05-18T03:53:37+02:00]]
## Test-Writer Notes
- Test file: `tests/test_server_1652.py`
- Classes: `TestFromAC_AppContextVectorStore`, `TestFromAC_RemoveSourceTool`, `TestFromAC_VectorsFirstAbort`, `TestFromAC_AuditLog`, `TestFromAC_SourceNotFound`
- Tests per category:
  - Happy path: 5 (lifespan wiring, returns dict, delete_embedding called per chunk, cascade called, correct counts)
  - Edge/boundary: 3 (False not abort, second chunk fails, empty chunk list tolerance)
  - Error paths: 6 (exception → ToolError, no cascade on failure, source not found → ToolError ×3, no SQL mutation)
  - Structural: 4 (vector_store field exists, accepts None, destructiveHint=True, __all__ export)
  - Audit log: 6 (info called, contains source_id, name, doc count, chunk count, entity count)
- Total: 24 tests — all FAIL (ImportError: cannot import name 'remove_source' from 'owlbear_mcp_knowledge.server')
- Lint: clean (ruff 0)
- Commit: 540783e9

## AC Coverage
| AC | Tests |
|----|-------|
| AC-1 (AppContext.vector_store + lifespan wiring) | test_app_context_has_vector_store_field, test_app_context_vector_store_accepts_none, test_app_lifespan_wires_vector_store_to_app_context |
| AC-2 (tool registered destructiveHint=True, happy path) | test_remove_source_registered_with_destructive_hint, test_remove_source_returns_dict_with_expected_keys, test_remove_source_dict_values_are_integers, test_remove_source_calls_delete_embedding_for_each_chunk, test_remove_source_calls_delete_cascade_with_source_id, test_remove_source_returns_correct_counts |
| AC-3 (exception → ToolError, no cascade; False → continue) | test_remove_source_raises_tool_error_on_delete_embedding_exception, test_remove_source_does_not_call_delete_cascade_when_vector_deletion_fails, test_remove_source_false_from_delete_embedding_is_not_abort, test_remove_source_aborts_on_second_chunk_failure, test_remove_source_sqlite_intact_after_vector_failure |
| AC-4 (logger.info audit with source_id, name, counts) | test_remove_source_calls_logger_info_before_delete_cascade, test_remove_source_log_contains_source_id, test_remove_source_log_contains_source_name, test_remove_source_log_contains_doc_count, test_remove_source_log_contains_chunk_count, test_remove_source_log_contains_entity_count |
| AC-5 (source not found → ToolError, no mutations) | test_remove_source_raises_tool_error_when_source_not_found, test_remove_source_no_delete_embedding_when_source_not_found, test_remove_source_no_delete_cascade_when_source_not_found, test_remove_source_no_sql_mutation_when_source_not_found, test_remove_source_in_all_export |

[[2026-05-18T04:08:17+02:00]]
builder crashed once: stopped due to pre-existing uncommitted changes in server.py; releasing claim before retry

[[2026-05-18T04:12:03+02:00]]
builder crashed twice: pre-existing uncommitted changes in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py prevent safe commit isolation. Tests pass (25/25) but implementation cannot be committed without resolving working tree conflicts. User action needed: clean/split unrelated edits from server.py first.
