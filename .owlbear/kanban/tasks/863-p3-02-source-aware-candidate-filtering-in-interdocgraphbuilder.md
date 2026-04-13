---
id: 863
title: 'P3-02: Source-aware candidate filtering in InterDocGraphBuilder'
status: research
priority: nice-to-have
created: '2026-04-13T19:16:55.146615+00:00'
updated: '2026-04-13T19:16:55.146615+00:00'
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

InterDocGraphBuilder filters candidates by `document_id` but not by `source_id`. Brief Outcome 4 requires cross-*source* linking (e.g., SharePoint security policy → Confluence implementation guide). The builder should prioritize cross-source pairs and include source metadata in edge stamps.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gap G3)

## Acceptance Criteria

- [ ] `_collect_candidates()` joins entities to their document's `source_id`
- [ ] Cross-source pairs are prioritized over same-source cross-document pairs
- [ ] Edge metadata includes `source_pair: [source_a_id, source_b_id]` alongside existing `doc_pair`
- [ ] Tests verify cross-source filtering and metadata stamping

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py`

## Dependency

Deferred until Phase 1 entity model is proven via real corporate ingestion.
