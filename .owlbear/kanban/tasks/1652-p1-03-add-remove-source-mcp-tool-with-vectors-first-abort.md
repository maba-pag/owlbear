---
id: 1652
title: 'P1-03: Add remove_source MCP tool with vectors-first abort'
status: backlog
priority: needed
created: 2026-05-18T03:11:06.889695+02:00
updated: 2026-05-18T03:21:17.110240+02:00
tags:
  - scope:mcp-knowledge
  - mcp-tools
parent: 1650
depends_on: []
ac:
  - 'AC-1: `AppContext` has a `vector_store` field typed `QdrantVectorStore | None`;
    `app_lifespan` wires the existing `QdrantVectorStore` instance (`vs`) into it'
  - "AC-2: `remove_source(source_id)` MCP tool with `destructiveHint=True`: given
    a valid source_id, collects chunk IDs from the source's documents via `conn` SQL
    query, deletes each chunk's vector via `QdrantVectorStore.delete_embedding`, then
    calls `source_store.delete_cascade`; returns counts of deleted documents, chunks,
    and entities"
  - 'AC-3: Given vector deletion failure for any chunk ID, `remove_source` returns
    a `ToolError` without calling `delete_cascade`; SQLite data remains intact'
  - 'AC-4: Before calling `delete_cascade`, log an audit entry (via `logger.info`)
    containing source_id, source name, timestamp, and the counts of documents/chunks/entities
    about to be deleted'
proof_bundle: behavioral
blocked: false
block_reason:
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
