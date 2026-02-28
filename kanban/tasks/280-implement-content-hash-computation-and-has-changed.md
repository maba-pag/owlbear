---
id: 280
title: Implement content hash computation and has_changed() check
status: in-progress
priority: needed
created: 2026-02-28T22:56:44.3022124+01:00
updated: 2026-03-01T00:10:54.3193749+01:00
started: 2026-02-28T23:12:15.564346+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 279
class: standard
---

Pure logic for content change detection.

AC:
- [ ] compute_content_hash(content: str) -> str: SHA-256 of content.strip(), hex digest
- [ ] check_content_changed(source: str, content: str, scope: str) -> tuple[bool, str | None]: computes hash, calls find_status_by_source(), returns (changed, existing_document_id)
- [ ] When source not previously ingested: returns (True, None) — signals new document
- [ ] When hash matches stored: returns (False, existing_document_id) — skip
- [ ] When hash differs: returns (True, existing_document_id) — re-ingest needed
- [ ] Tests: identical content -> (False, id), changed content -> (True, id), new content -> (True, None)

Depends on #279 (find_status_by_source query).
See docs/content-hashing-research.md
