---
id: 865
title: 'P3-04: Entity name canonicalization for cross-source matching'
status: research
priority: someday
created: '2026-04-13T19:16:55.238306+00:00'
updated: '2026-04-13T19:16:55.238306+00:00'
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

InterDocGraphBuilder relies on embedding cosine similarity (0.70 threshold) for candidate discovery. No name normalization exists. "Data Classification" and "data classification" from different sources become separate entities. Conservative canonical_name pre-filtering would improve match quality.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gap G4)
See: .owlbear/briefs/draft-browser-knowledge-extraction/voices/data-person.md (Gap 3)

## Acceptance Criteria

- [ ] `canonical_name` derived field: lowercase, collapse whitespace, strip leading/trailing articles and punctuation
- [ ] `_collect_candidates()` uses canonical_name for pre-filtering alongside vector similarity
- [ ] Conservative normalization only — "Data Classification Framework" must remain distinct from "data classification"
- [ ] Tests verify canonicalization and pre-filter behavior

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/models.py` (Entity model)
- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py`

## Dependency

Deferred until real corporate ingestion shows entity name drift is a measurable problem.
