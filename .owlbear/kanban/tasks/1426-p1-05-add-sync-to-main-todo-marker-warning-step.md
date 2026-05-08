---
id: 1426
title: 'P1-05: Add sync-to-main TODO marker warning step'
status: research
priority: important
created: 2026-05-08T00:41:08.358257+00:00
updated: 2026-05-08T00:41:22.511439+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on:
- 1423
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Acceptance Criteria

Add a pre-sync warning step to the sync-to-main GitHub Actions workflow (`.github/workflows/sync-to-main.yml`):

1. Before syncing, grep all `serve/*/README.md`, `README.md`, `README-consumer.md` for `> **TODO:**` markers
2. If markers found: print a summary (count + file list) as a workflow warning annotation
3. Do NOT fail the workflow — warning only, not a hard gate
4. Summary format: "⚠️ {n} unresolved TODO markers in {m} files: {list}"

**In scope:** CI workflow step only.
**Out of scope:** Resolving the markers (doc-audit), marker format definition (#1423).

Brief: see parent #1421