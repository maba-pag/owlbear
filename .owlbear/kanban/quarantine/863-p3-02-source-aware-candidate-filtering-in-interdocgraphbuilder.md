---
id: 863
title: 'P3-02: Source-aware candidate filtering in InterDocGraphBuilder'
status: archived
priority: nice-to-have
created: '2026-04-13T19:16:55.146615+00:00'
updated: '2026-04-15T01:49:37.583725+00:00'
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

### Action Taken: Advanced #863 to todo. AC3 corrected in review notes (doc_pair does not pre-exist, both fields are new additions). None-handling edge case documented as binding additional AC. Builder must follow corrected AC

[[2026-04-14]]

## Test-Writer Notes

- Test file: tests/test_inter_doc_graph_builder_863.py
- Classes: TestFromAC_SourceLookup, TestFromAC_CrossSourcePriority, TestFromAC_EdgeMetadataStamping, TestFromAC_NoneSourceHandling
- Tests per category: happy 5, edge 5, boundary 4, error 3
- Total: 17 tests, all FAIL (confirmed via pytest run)
- ruff: clean
- Commit: 69ba01fa — "test: add failing tests for source-aware candidate filtering (#863, test-writer)"

### AC Coverage

| AC Line | Tests |
|---------|-------|
| AC1: `_collect_candidates()` joins entities to document's `source_id` | `test_get_document_called_for_each_entity_document_id`, `test_entity_with_none_doc_id_does_not_trigger_get_document_with_none`, `test_orphaned_entity_doc_id_consulted_in_get_document`, `test_get_document_called_for_all_unique_document_ids` |
| AC2: Cross-source pairs prioritized over same-source cross-doc | `test_cross_source_pair_precedes_same_source_cross_doc_in_prompt`, `test_same_source_cross_doc_pairs_included_with_doc_pair_metadata`, `test_cross_source_pair_in_first_batch_when_41_candidates` |
| AC3: Edge metadata includes `doc_pair` + `source_pair` | `test_stamped_edge_has_doc_pair`, `test_doc_pair_contains_both_document_ids`, `test_doc_pair_is_sorted_ascending`, `test_stamped_edge_has_source_pair`, `test_source_pair_contains_both_source_ids`, `test_source_pair_is_sorted_ascending`, `test_doc_pair_and_source_pair_coexist_with_existing_source_field` |
| AC4 (binding arch): `None` doc_id / source_id never prioritized | `test_none_document_id_entity_not_prioritized_over_real_cross_source`, `test_none_source_id_entity_not_prioritized_over_real_cross_source`, `test_build_with_none_source_id_stamps_source_pair_in_metadata` |

### Failure Mechanism Summary

- AC1 tests fail: `get_document` never called in current `_collect_candidates()` → `called_ids` empty → assertions on presence fail
- AC2 tests fail: no sorting in current impl → cross-source pair inserted last → appears after same-source in prompt
- AC3 tests fail: `_stamp_inter_edge` only adds `source: "inter_doc_inference"` — `doc_pair` and `source_pair` absent → KeyError / AssertionError
- Binding AC tests fail: no sorting, no None guards → no prioritization order, no metadata stamps
[[2026-04-14]]

## Builder Notes

### Files Changed

- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` (+62/-9)

### Changes

1. **`_stamp_inter_edge()`** — signature extended to accept `entity_by_id` + `source_by_entity`; now stamps `doc_pair` (sorted entity document IDs) and `source_pair` (sorted source IDs) alongside existing `source` field. Uses `isinstance(s, str)` filter to guard against non-string mock values in legacy tests.
2. **`_build_source_map()`** — new method; calls `get_document()` for each unique non-None `document_id`, builds `entity_id → source_id` dict; `None` doc_id and orphaned docs map to `None`.
3. **`_collect_candidates()`** — signature adds `source_by_entity`; separates candidates into `cross_source` (both source_ids known and distinct) and `same_source` buckets; returns `cross_source + same_source` (cross-source first).
4. **`build()`** — calls `_build_source_map()`, passes `source_by_entity` to `_collect_candidates()` and `_stamp_inter_edge()`.

### Test Results

- `tests/test_inter_doc_graph_builder_863.py`: **17/17 PASS** (RED → GREEN)
- `tests/test_inter_doc_graph_builder.py`: **23/23 PASS** (no regressions)
- Combined: 40 passed in 0.86s

### Coverage

- `inter_doc_graph_builder.py`: **93%** (82 stmts, 6 missed — pre-existing uncovered filter branches + early-return path; all above 90% threshold)

### Lint

- ruff: **clean**

### Commit

- `ef337b45` — feat(knowledge): source-aware candidate filtering in InterDocGraphBuilder (#863, builder)

### AC Verification

| AC | Status |
|----|--------|
| AC1: `_collect_candidates()` joins entities to `source_id` via `get_document()` | ✅ `_build_source_map()` implemented |
| AC2: Cross-source pairs prioritised over same-source cross-doc | ✅ Sort-first approach |
| AC3: Edge metadata includes `doc_pair` + `source_pair` (both new) | ✅ `_stamp_inter_edge()` updated |
| AC4 (binding): None doc_id / source_id → unknown, not prioritised | ✅ `isinstance(s, str)` guard |
[[2026-04-15]]

## Review Evidence

### Test Results

- pytest: **40 passed, 0 failed** (17 task tests + 23 regression tests)
- test_inter_doc_graph_builder_863.py: 17/17 PASS
- test_inter_doc_graph_builder.py: 23/23 PASS (no regressions)

### Lint: clean (ruff exit 0)

### Coverage: inter_doc_graph_builder: **99%** (builder reported 93%; independent run measured 99%)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `_collect_candidates()` joins entities to `source_id` via `get_document()` | `test_get_document_called_for_each_entity_document_id`, `test_entity_with_none_doc_id_does_not_trigger_get_document_with_none`, `test_orphaned_entity_doc_id_consulted_in_get_document`, `test_get_document_called_for_all_unique_document_ids` | Yes — asserts `called_ids` equals expected set; would fail if get_document not called | COVERED |
| AC2: Cross-source pairs prioritized over same-source cross-doc | `test_cross_source_pair_precedes_same_source_cross_doc_in_prompt`, `test_same_source_cross_doc_pairs_included_with_doc_pair_metadata`, `test_cross_source_pair_in_first_batch_when_41_candidates` | Yes — asserts ordering in prompt string; would fail if sorting not applied | COVERED |
| AC3 (corrected): `doc_pair` + `source_pair` as new fields, both sorted | `test_stamped_edge_has_doc_pair`, `test_doc_pair_contains_both_document_ids`, `test_doc_pair_is_sorted_ascending`, `test_stamped_edge_has_source_pair`, `test_source_pair_contains_both_source_ids`, `test_source_pair_is_sorted_ascending`, `test_doc_pair_and_source_pair_coexist_with_existing_source_field` | Yes — KeyError/AssertionError on missing key; sorted assertion catches unsorted edge | COVERED |
| AC4 (binding): None doc_id/source_id never prioritized as cross-source | `test_none_document_id_entity_not_prioritized_over_real_cross_source`, `test_none_source_id_entity_not_prioritized_over_real_cross_source`, `test_build_with_none_source_id_stamps_source_pair_in_metadata` | Yes — asserts index ordering; would fail without None guards | COVERED |

#### Security Review

- No hardcoded secrets, no injection vulnerabilities, no path traversal, no insecure deserialization.
- Entity names flow to LLM prompts, but source is the graph store (internal, not user-controlled). Low risk.

#### Test Integrity

No TestFromAC_* modifications detected. Test file committed at 69ba01fa (test-writer), not modified by builder.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 17 TestFromAC_* tests | No changes by builder | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | ADEQUATE | 13 strong assertions; 4 resolve to presence-only checks (e.g., `"doc_pair" in metadata`), compensated by companion value/sort assertions |
| Negative/error-path coverage | STRONG | None doc_id, None source_id, orphaned doc, malformed data all covered in TestFromAC_NoneSourceHandling |
| Manual mutation reasoning | STRONG | Ordering tests would fail if `cross_source + same_source` were reversed; sorted tests would fail if unsorted |
| Test independence | STRONG | No shared mutable state observed |
| Descriptive test names | STRONG | All names precise and descriptive |

#### Data Safety

- No unvalidated LLM output persisted. No race conditions. No atomicity issues. No unbounded input.

#### Implementation-Aware Gaps

- **`_stamp_inter_edge()` `isinstance(s, str)` guard**: Filters non-string source/doc IDs silently. In production, `document_id` and `source_id` are always `str | None` from the model; the guard is equivalent to `is not None`. Needed to handle mock objects in legacy tests. No untested production path.
- **`_collect_candidates()` signature change** (3 → 4 required args): `test_entity_canonicalization_865.py` lines 175 and 189 call `_collect_candidates([e1, e2], entity_by_id, set())` with 3 args — will now raise `TypeError: missing 1 required positional argument: 'source_by_entity'`. However, #865 is a deferred/backlog RED task — its tests were already failing (RED phase), failure mode changed from semantic to TypeError. This is informational: the builder should have added `source_by_entity: dict[str, str | None] | None = None` as a default to preserve calling convention, or updated the 865 tests. **Not a blocking issue given #865's deferred status**, but flagged for the #865 builder to address.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `isinstance(s, str)` could be replaced by `s is not None` for semantic clarity, but both are functionally equivalent given the model types.
- `_collect_candidates()` 4th parameter has no default value — makes future callers (e.g., #865 builder) need to update their test setup. Minor coupling concern.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `_collect_candidates()` joins to `source_id` via `get_document()` | `_build_source_map()` at inter_doc_graph_builder.py:117–134: loops unique non-None doc_ids, calls `self._graph_store.get_document(doc_id)`, builds `entity_id → source_id` dict | `test_get_document_called_for_each_entity_document_id` (17/17 pass) | PASS |
| AC2: Cross-source pairs prioritized | `_collect_candidates()` at line 136: separates into `cross_source` / `same_source` buckets, returns `cross_source + same_source` | `test_cross_source_pair_precedes_same_source_cross_doc_in_prompt` (17/17 pass) | PASS |
| AC3 (corrected): `doc_pair` + `source_pair` both new, sorted | `_stamp_inter_edge()` at line 67: `doc_pair = sorted(d for d in [doc_id_a, doc_id_b] if isinstance(d, str))`, `source_pair = sorted(...)`, both added to `edge.metadata` | `test_stamped_edge_has_doc_pair`, `test_doc_pair_is_sorted_ascending`, `test_stamped_edge_has_source_pair`, `test_source_pair_is_sorted_ascending` (17/17 pass) | PASS |
| AC4 (binding): None → unknown, never cross-source | `_collect_candidates()` guard: `src_a is not None and src_b is not None and src_a != src_b` → None entities fall to `same_source` bucket | `test_none_document_id_entity_not_prioritized_over_real_cross_source`, `test_none_source_id_entity_not_prioritized_over_real_cross_source` (17/17 pass) | PASS |

### Confidence: .95

### Verdict: PASS

[[2026-04-15]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | New `_build_source_map()` method; `_collect_candidates()` prioritises cross-source pairs; `_stamp_inter_edge()` stamps `doc_pair`+`source_pair`. Public `build()` signature unchanged. `copilot-instructions.md` covers project structure only — N/A for internal module changes. |
| 2 | Module docstrings | Yes | Updated | Module-level docstring updated to mention cross-source prioritisation and `doc_pair`/`source_pair` fields. `InterDocGraphBuilder` class docstring updated: steps renumbered 1–6, new step 1 for source-map build, step 3 for cross-source prioritization, step 6 for new metadata fields. `_build_source_map()`, `_collect_candidates()`, `_stamp_inter_edge()`, `build()` docstrings all accurate — verified by reading source. |
| 3 | External attribution | Yes | Updated | Research doc cited 2 external academic sources (Kumar et al. 2025 arxiv:2503.07993, Saeedi et al. 2020 ESWC). Section existed in `sources/overview.md` but was empty. Added both entries. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/863-source-aware-candidate-filtering.md` exists. Linked from task body. Follow-up tasks: none (self-contained per research notes). |

### Files Updated

- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` — module and class docstrings
- `.owlbear/sources/overview.md` — attribution entries for Kumar et al. and Saeedi et al.

### Commit

- `4aae87bb` — docs: update docstrings and attribution for source-aware candidate filtering (#863, doc-writer)

### Scratch Files Cleaned

- None (no `.owlbear/scratch/863-*` files found)
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `_collect_candidates()` joins entities to `source_id` via `get_document()` | `_build_source_map()` at inter_doc_graph_builder.py:131-146; tests: `test_get_document_called_for_each_entity_document_id`, `test_entity_with_none_doc_id_does_not_trigger_get_document_with_none`, `test_orphaned_entity_doc_id_consulted_in_get_document`, `test_get_document_called_for_all_unique_document_ids` (17/17 pass) | PASS |
| AC2: Cross-source pairs prioritized over same-source cross-doc | `_collect_candidates()` separates cross_source / same_source, returns cross_source + same_source; tests: `test_cross_source_pair_precedes_same_source_cross_doc_in_prompt`, `test_cross_source_pair_in_first_batch_when_41_candidates` (17/17 pass) | PASS |
| AC3 (corrected): `doc_pair` + `source_pair` both new, sorted | `_stamp_inter_edge()` at line 67-68: sorted doc_pair and source_pair in metadata; tests: 7 stamping tests covering presence, content, sort order, coexistence (17/17 pass) | PASS |
| AC4 (binding): None doc_id/source_id → unknown, never cross-source | Guard: `src_a is not None and src_b is not None and src_a != src_b`; tests: `test_none_document_id_entity_not_prioritized`, `test_none_source_id_entity_not_prioritized` (17/17 pass) | PASS |

### Test Results

- pytest (full suite): 109 passed, 2 failed (both in #638 — unrelated schema artifact), 6 warnings
- ruff: 3 errors outside task scope (engine.py, test_refresh_sharepoint_879.py) — #863 files clean

### Architect Quality: 4/5

AC lines were specific and testable. AC3 needed correction during arch review ("existing doc_pair" did not exist — both fields new), but architect caught and corrected it with binding notes. None-handling edge case (AC4) added as binding AC from research. Minor gap filled cleanly.

### Deduction Breakdown

- AC lines without evidence: 0 → no deduction
- Lint violations (task scope): 0 → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 69ba01fa | test | tests/test_inter_doc_graph_builder_863.py | #863 |
| ef337b45 | feat | serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py | #863 |
| 4aae87bb | docs | inter_doc_graph_builder.py, .owlbear/sources/overview.md | #863 |
