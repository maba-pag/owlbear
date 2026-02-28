---
id: 260
title: 'Data migration: re-embed with bge-m3 into Qdrant'
status: archived
priority: important
created: 2026-02-28T12:42:07.1909055+01:00
updated: 2026-02-28T23:54:28.1984661+01:00
started: 2026-02-28T12:55:54.2800562+01:00
completed: 2026-02-28T23:54:28.1984661+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
depends_on:
    - 250
class: standard
---

## Context
If any content exists in the old sqlite-vec store, re-embed all chunks with bge-m3 and populate Qdrant. Also re-embed entity descriptions. Script should be idempotent and resumable.

## Research Needed
- How much existing data is there? (user said 'havent used sqlite-vec at all until now')
- If zero data: this task might be trivial (just delete old tables)
- If data exists: read chunks from SQLite, embed with bge-m3, upsert to Qdrant
- Re-embedding 10K chunks at ~35ms/chunk = ~6 minutes on CPU

## Acceptance Criteria
- [ ] Migration script reads all chunks from SQLite
- [ ] Embeds with BgeM3EmbeddingProvider (dense+sparse+ColBERT)
- [ ] Upserts to QdrantVectorStore with correct payloads
- [ ] Resumable: skips already-migrated chunks
- [ ] idempotent: safe to run multiple times
- [ ] CLI command: bearclaw knowledge migrate
- [ ] TDD

[[2026-02-28]] Sat 12:55
Closed as redundant — no data to migrate (user confirmed sqlite-vec never used). Useful AC merged into #251.
