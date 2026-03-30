---
id: 203
title: 'Test: Entity extraction and graph builders'
status: backlog
priority: needed
created: 2026-03-30T08:11:19.8857429+02:00
updated: 2026-03-30T08:11:24.6685937+02:00
started: 2026-03-30T08:11:24.6685937+02:00
tags:
    - phase-1
    - ' scope:knowledge'
    - ' test'
depends_on:
    - 32
class: standard
---

## Objective

Write failing tests (TDD RED) for the entity extraction pipeline and graph builders before implementation in #33.

## Acceptance Criteria

- [ ] `tests/test_extractor.py` — test `EntityExtractor` with mock `StructuredExtractor`:
  - empty/whitespace input returns empty `ExtractionResult`
  - non-empty input delegates to injected extractor and returns its result
  - optional `metadata` dict is prefixed to the prompt string sent to the extractor
- [ ] `tests/test_graph_builder.py` — test `IntraDocGraphBuilder` with mock `StructuredExtractor`:
  - fewer than 2 entities returns empty `GraphBuildResult`
  - <=80 entities: single LLM call
  - >80 entities: batched by `entity_type`, one call per type
  - all returned edges stamped with `weight=0.5` and `metadata["source"]=="intra_doc_inference"`
  - `scope` and `document_id` forwarded correctly
- [ ] `tests/test_inter_doc_graph_builder.py` — test `InterDocGraphBuilder` with mock `StructuredExtractor` + mock `VectorStoreProtocol` + mock `GraphStore`:
  - fewer than 2 entities returns empty `GraphBuildResult`
  - vector pre-filtering calls `get_embedding` and `search_similar` per entity
  - cross-doc filter: same `document_id` pairs skipped
  - existing inter-doc edges skipped (dedup via `list_edges`)
  - pairs batched in groups of 40
  - all returned edges stamped with `weight=0.4` and `metadata["source"]=="inter_doc_inference"`
- [ ] `tests/test_structured_extractor_protocol.py` — test `StructuredExtractor` protocol is `@runtime_checkable` and validates duck-type conformance
- [ ] All tests fail (RED phase) before #33 implementation
- [ ] ruff clean on all test files

## Context

TDD RED pair for #33. Depends on #32 (shared protocol.py types). Tests target the v2 module signatures defined in #33 AC.
