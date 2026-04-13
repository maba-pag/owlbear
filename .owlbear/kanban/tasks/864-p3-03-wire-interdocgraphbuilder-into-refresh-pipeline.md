---
id: 864
title: 'P3-03: Wire InterDocGraphBuilder into refresh pipeline'
status: research
priority: nice-to-have
created: '2026-04-13T19:16:55.201306+00:00'
updated: '2026-04-13T19:16:55.201306+00:00'
tags:
- phase-3
- scope:knowledge
- deferred
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

InterDocGraphBuilder is a standalone class — neither refresh.py nor ingest.py calls it. For cross-source linking to work, the builder must be triggered after intra-doc graph building completes for a newly ingested document.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gap G6)

## Acceptance Criteria

- [ ] After document ingestion + intra-doc build, trigger inter-doc build for new doc's entities
- [ ] Inter-doc build is async (non-blocking to ingestion flow)
- [ ] Skip inter-doc build if fewer than 2 documents exist in scope
- [ ] Config toggle to enable/disable inter-doc building (default: disabled until Phase 3 launch)
- [ ] Integration test: ingest 2 docs from different sources, verify cross-doc edges created

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/refresh.py` or `ingest.py`

## Dependency

Depends on P3-01 (prompt fix) and P3-02 (source-aware filtering).
