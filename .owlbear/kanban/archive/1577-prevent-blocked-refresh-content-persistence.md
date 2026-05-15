---
id: 1577
title: Prevent blocked refresh content persistence
status: archived
priority: critical
created: 2026-05-15T00:58:33.908483+00:00
updated: 2026-05-15T01:57:57.499858+00:00
tags:
  - scope:knowledge
  - type:build
  - bug
  - security
parent:
depends_on:
  - 1556
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1579
---
Context:
Knowledge module audit found that direct text ingest scans chunks before writing, but the refresh/intake ingest path writes the document and chunks before running the content-injection guard. When the guard blocks, the pipeline returns `status='blocked'` while the already-written document/chunks remain in the database.

Problem:
A source whose content is rejected by the guard can still leave persisted chunks behind. That makes the reported ingest outcome misleading and can expose blocked content to later retrieval or enrichment.

Scope:
- In scope: `IngestPipeline.ingest(...)`/refresh-intake ordering and cleanup when content guard returns `blocked`; relational rows, status rows, and vector embeddings created before a block; source lifecycle only where needed for cleanup consistency.
- Out of scope: redesigning the content guard, adding automatic LLM filtering, changing manual enrichment policy, and broad source lifecycle design.

Functional acceptance note:
Acceptance is based on persisted state after a blocked ingest. Passing or failing tests alone is not functional proof.

Acceptance Criteria:
AC-1: Given refresh/intake ingest processes content that the configured content guard blocks, the returned ingest result is `status='blocked'` and no newly created document, chunk, status, graph, or vector rows from that blocked attempt remain queryable or enrichable.
AC-2: Given refresh/intake ingest replaces an existing document and the replacement content is blocked, the implementation must either leave the previous accepted document intact or explicitly document and prove the intended rollback/delete behavior; it must not leave a half-written replacement document or chunks.
AC-3: Given direct text ingest uses the same guard path, the fix preserves the existing behavior that blocked direct text does not persist blocked chunks.
AC-4: Proof must include a default SQLite-backed store and a fake/deterministic content guard that blocks a chunk, then inspect persisted document/chunk/vector state after the blocked result.

Suggested implementation shape:
Prefer scanning chunks before any persistence in `IngestPipeline.ingest(...)`. If pre-scan is impractical for a specific path, use the same cleanup path as failed ingest and prove it also removes vector embeddings.
2026-05-15T01:46:36+00:00


Audit refinement — refresh wrappers must not convert `blocked` to `ok`:
`RefreshOrchestrator._handle_authenticated_web(...)` currently normalizes any ingest status outside `ok`, `skipped`, and `failed` to `ok`. Because the ingest pipeline can return `status='blocked'` when content is rejected by the content guard, authenticated refresh can count blocked content as successfully refreshed and schedule inter-document graph building.

Required follow-up before review:
- Treat `blocked` as an explicit non-success outcome in all refresh wrappers, including authenticated-web refresh.
- Do not schedule inter-document graph building for blocked content.
- Proof should cover an authenticated-web refresh whose pipeline returns `blocked` and show that it is not counted as refreshed/ok.