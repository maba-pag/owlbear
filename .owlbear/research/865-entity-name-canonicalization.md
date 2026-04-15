# Entity Name Canonicalization for Cross-Source Matching

> **Owning task:** #865 — P3-04: Entity name canonicalization for cross-source matching
> **Date:** 2026-04-14 **Status:** Complete

## 1. Context and Question

InterDocGraphBuilder uses embedding cosine similarity (0.70 threshold) for cross-document candidate discovery. No string normalization exists — "Data Classification" and "data classification" from different sources become separate entities. The question: what canonicalization approach balances robustness with conservative distinctness preservation?

## 2. Sources Studied

| # | Source | Type | Relevance | What |
|---|--------|------|-----------|------|
| S1 | `models.py` Entity class | Codebase | .95 | `frozen=True`, no derived fields, 9 stored fields |
| S2 | `inter_doc_graph_builder.py` `_collect_candidates()` | Codebase | .95 | Pure vector-similarity filtering, no string normalization |
| S3 | `graph_store.py` `merge_entities()` | Codebase | .80 | Post-hoc merge API exists but needs external detection logic |
| S4 | `schema.py` entities table | Codebase | .85 | No canonical_name column; would be schema v10 if stored |
| S5 | ScrapingAnt: Deduplication & Canonicalization in KGs (2025) | Web | .80 | Blocking + candidate generation pipeline; canonical_name as blocking key |
| S6 | SpotIntelligence: Entity Resolution Techniques (2024) | Web | .75 | Rule-based matching, string similarity measures, clustering approaches |
| S7 | 772-interdocgraphbuilder-corporate-types.md | Codebase | .90 | Gap G4 analysis; deferred canonicalization recommendation |

## 3. Analysis

### 3.1 Normalization Rules

The AC specifies: lowercase, collapse whitespace, strip leading/trailing articles and punctuation.

| Input | Canonical Output | Correctness |
|-------|-----------------|-------------|
| "Data Classification Framework" | "data classification framework" | Distinct from "data classification" ✓ |
| "data classification" | "data classification" | Preserved ✓ |
| "The Security Policy" | "security policy" | Article stripped ✓ |
| "  ISO   27001:  " | "iso 27001" | Whitespace collapsed, trailing punct stripped ✓ |
| "—Risk Assessment—" | "risk assessment" | Leading/trailing punct stripped ✓ |

Conservative operations only: no stemming, no token reordering, no fuzzy matching, no stopword removal from middle of string. This matches industry best practice for "blocking key" normalization (S5, S6).

### 3.2 Implementation Approach Comparison

| Criterion | A: `@computed_field` on Entity | B: Stored DB column | C: Free function only |
|-----------|-------------------------------|---------------------|-----------------------|
| Schema change | None | v10 migration | None |
| Persistence | Not stored | SQLite column | Not stored |
| SQL queryable | No | Yes (indexable) | No |
| Consistency | Always derived from name | Risk of stale sync | Caller's responsibility |
| Reusability | Travels with Entity model | Travels with DB row | Ad-hoc per call site |
| LOC estimate | ~20 (model) + ~15 (builder) | ~40 (schema+store+model) + ~15 (builder) | ~15 (function) + ~15 (builder) |
| KISS score | High | Low | Highest |
| Frozen model compat | Yes — computed fields are read-only | N/A — stored field | N/A |
| Future extensibility | Easy to evolve rule | DB column locked to one normalization | Easy to evolve rule |

### 3.3 Pre-Filter Integration Strategy

Current flow in `_collect_candidates()`:
1. For each entity → vector search → filter by cosine ≥ 0.70 → filter same-doc → dedup

Proposed addition (canonical-name blocking):
1. Build `canonical_name → [Entity]` index from all entities
2. For each canonical_name group with entities from different documents: add to candidate pairs
3. Merge with vector-similarity candidates (union, deduplicated)

This is a standard **blocking strategy** (S5): exact canonical_name match generates candidates independently of vector similarity, catching cases where embeddings miss lexically similar entities.

### 3.4 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Over-normalization merges distinct entities | Low | High | Conservative rules only; entity_type still checked downstream by LLM |
| canonical_name collision on unrelated entities | Low | Low | LLM validation step filters false positives |
| Performance overhead of canonical blocking | Very Low | Low | Dict lookup is O(1); entity count per doc is small |
| Pydantic `computed_field` import needed | Very Low | None | Standard pydantic v2 API |

## 4. Recommendation (confidence: .82)

**Approach A: `@computed_field` on Entity model + canonical-name blocking in `_collect_candidates()`.**

Rationale:
- AC explicitly says "derived field" — `@computed_field` is the idiomatic Pydantic v2 mechanism
- No schema migration needed; aligns with KISS/YAGNI
- Computed property is always consistent with `name` — no staleness risk
- `frozen=True` model is compatible with computed fields (read-only by design)
- The canonical-name blocking pattern is the standard industry approach for pre-filtering (S5, S6)
- ~35 LOC total — well within the "conservative extension" scope

Implementation sketch:
- `_canonicalize(name: str) -> str` — module-level function: lower, collapse whitespace, strip articles/punct
- `Entity.canonical_name` — `@computed_field` returning `_canonicalize(self.name)`
- `_collect_candidates()` — add canonical-name blocking as complementary candidate source

Challenge: FALLBACK — challenger subagent not available in agent list.

## 5. Follow-up Tasks

Task #865 itself becomes the implementation task. No additional follow-up tasks needed — AC is already concrete and implementation-ready. Task should advance to `backlog` with the `deferred` tag retained (dependency gate: real corporate ingestion must show entity name drift is a measurable problem).

### Tier Classification

**T1 — Autonomous.** Incremental extension to existing Entity model and InterDocGraphBuilder. No new capabilities, no architecture changes, no security implications. Conservative normalization function + computed property + pre-filter integration.
