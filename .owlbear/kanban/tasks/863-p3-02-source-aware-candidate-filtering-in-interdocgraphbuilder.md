---
id: 863
title: 'P3-02: Source-aware candidate filtering in InterDocGraphBuilder'
status: todo
priority: nice-to-have
created: '2026-04-13T19:16:55.146615+00:00'
updated: '2026-04-14T15:25:36.290354+00:00'
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

[[2026-04-14]]
## Research
- Research doc: .owlbear/research/863-source-aware-candidate-filtering.md
- Sources: 6 studied, 4 high-relevance (codebase + 772 research doc)
- Recommendation: Option A — direct document lookup via `graph_store.get_document()` with sort-first cross-source prioritization. ~30 LOC, zero interface changes. (confidence: .82)
- Follow-up tasks created: none — #863 AC is self-contained
- Decision requests: none (T1 — incremental enhancement to existing builder)

## Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Confidence in original: .82
- Key challenges: N/A
- Researcher response: N/A

## Key Findings
1. Data model supports the change: `Entity.document_id` → `Document.source_id` via `GraphStore.get_document()` (PK lookup, ~μs)
2. **AC discrepancy**: AC3 says "alongside existing `doc_pair`" but no `doc_pair` exists anywhere in codebase — both `doc_pair` and `source_pair` must be added fresh
3. #862 (prompt fix) is blocked due to LLMExtractor removal — but #863 is independent (filtering happens before LLM calls)
4. Sort-first prioritization (cross-source pairs returned before same-source) is simplest approach; weight-boost rejected (conflates semantics)
5. Edge cases: `document_id=None` or `source_id=None` entities should be treated as "unknown source", never prioritized as cross-source
[[2026-04-14]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: source-aware candidate filtering in InterDocGraphBuilder |
| Interface clarity | PASS/FLAG | AC3 references "existing `doc_pair`" which does not exist — see corrected AC below. All other AC lines are testable. |
| Dependency correctness | PASS | No dependencies. #863 is independent of #862 (prompt fix). Confirmed in research. |
| Module layering | PASS | Changes scoped to `inter_doc_graph_builder.py`. Uses already-injected `self._graph_store`. No cross-package imports. |
| TDD compliance | PASS | AC4 explicitly requires tests. |
| KISS/YAGNI | PASS | Option A: direct `get_document()` lookup, ~30 LOC, zero interface/schema changes. |
| Premise challenge | PASS | Verified: `_collect_candidates()` filters by `document_id` only (line 107). No source awareness. Gap is real. |
| Pattern consistency | PASS | Uses existing DI patterns — `graph_store` already injected, `get_document()` is an existing method. |
| Security surface | PASS | No new system boundaries. Internal graph processing only. |
| Single domain | PASS | `scope:knowledge` only. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `get_document(doc_id)` | Returns None for orphaned doc_id | None | Must handle | Entities treated as "unknown source" |
| `Document.source_id` | None for docs without source | None | Must handle | Pairs treated as same-source, never prioritized |

### AC Correction (binding for downstream)

AC3 as written: "Edge metadata includes `source_pair: [source_a_id, source_b_id]` alongside existing `doc_pair`"

**Corrected AC3:** Edge metadata includes both `doc_pair: [doc_a_id, doc_b_id]` and `source_pair: [source_a_id, source_b_id]` as new fields (neither exists today). Both sorted for stable comparison.

**Additional AC (implicit from research finding #5):** Entities with `document_id=None` or resolved `source_id=None` are treated as "unknown source" and never prioritized as cross-source pairs.

### Codebase Evidence

- `_collect_candidates()`: `inter_doc_graph_builder.py:99-120` — filters `entity.document_id == other.document_id`, no source awareness
- `_stamp_inter_edge()`: `inter_doc_graph_builder.py:54-56` — only adds `source: "inter_doc_inference"` to metadata, no `doc_pair`
- `Entity.document_id`: `models.py:93` — `str | None`
- `Document.source_id`: `models.py:144` — `str | None`
- `GraphStore.get_document()`: `graph_store.py:377` — PK lookup, returns `Document | None`

### Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge; high confidence based on codebase verification (.88)

### Verdict: APPROVE
### Action Taken: Advanced #863 to todo. AC3 corrected in review notes (doc_pair does not pre-exist, both fields are new additions). None-handling edge case documented as binding additional AC. Builder must follow corrected AC.