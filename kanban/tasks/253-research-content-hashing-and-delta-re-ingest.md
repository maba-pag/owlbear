---
id: 253
title: 'Research: Content hashing and delta re-ingest strategy'
status: archived
priority: needed
created: 2026-02-28T12:40:06.3543806+01:00
updated: 2026-03-01T00:02:50.0211096+01:00
started: 2026-02-28T22:54:20.7714469+01:00
completed: 2026-03-01T00:02:50.0211096+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
class: standard
---

## Context
Currently, re-ingesting the same URL creates duplicate content. We need content hashing (SHA256) to detect changes and delta re-ingest to update only what changed.

## Research Checklist
- [ ] Theoretical validity: Is content hashing the right approach for change detection?
- [ ] Prior art: How do other knowledge pipelines handle updates? (LlamaIndex, LangChain, Haystack docstores)
- [ ] Technical feasibility: Where to store hashes? document_status table? Separate table?
- [ ] Architecture fit: How does delete-then-re-ingest work with Qdrant payloads + SQLite FK cascades?
- [ ] Implementation approach: Full re-ingest on change? Or chunk-level diffing?

## Questions to Answer
- Hash the raw content or the normalized/stripped content?
- Chunk-level hashing vs document-level? (chunk boundaries shift when content changes nearby)
- How to handle partial document changes? (only 1 paragraph updated in a 50-page doc)
- What about metadata changes (URL moved, title updated) without content change?
- HTTP ETag / Last-Modified for URL sources — should we use them?

## Acceptance Criteria
- [ ] Research doc in docs/
- [ ] Follow-up implementation tasks created
- [ ] Comparison of approaches (full re-ingest vs chunk-level diff vs hybrid)
