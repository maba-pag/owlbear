---
id: 1880
title: 'Knowledge: QueryFacade — entity lookup & render'
status: docs
priority: needed
created: 2026-05-25T19:05:09.183316+02:00
updated: 2026-05-27T10:09:11.351357+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1879
  - 1874
  - 1887
ac:
  - lookup_entity resolves entity by ID (direct get_entity) or name 
    (find_entities canonical lookup + optional entity_type filter); empty-string
    fields are treated as absent (name-path selected when entity_id is empty 
    string); raises LookupError when entity not found
  - 'EntityLookupResult populates: entity record, neighbourhood (traverse within expand_hops;
    None when expand_hops=0), related_chunks (chunk_ids_for_entity → get_chunk, empty
    tuple when no evidence)'
  - render_context formats provided QueryResult and/or EntityLookupResult as 
    structured text within max_chars; raises ValueError when neither result 
    provided in request
  - Render sets RenderedContext.truncated=True when budget exceeded; truncation 
    drops incomplete lines (no partial segments emitted); includes source 
    attribution when include_provenance=True; populates char_count, chunk_count,
    entity_count counting only fully included entries
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Entity-first query (find entity by id/name/type, expand neighbourhood) and context rendering for LLM consumption. Completes the QueryFacade protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/query.py`
- Depends on: QueryFacade search (#1879) for base infrastructure; GraphStore (#1873, #1874) for entity operations
- Target file: `serve/knowledge/src/owlbear_knowledge/query_facade.py` (extends same module)

## Implementation Notes

- lookup_entity: resolve by entity_id (direct get_entity) or entity_name (find_entities with canonical lookup)
- When entity_name used without entity_type, and multiple entities match, selection strategy is implementation-defined
- Neighbourhood expansion: Graph.traverse from resolved entity, expand_hops → max_hops
- related_chunks: find chunks that provide evidence for the entity (via Graph.claims → chunk lookups)
- render_context: format QueryResult or EntityLookupResult into structured text for LLM prompt insertion
- Rendering respects max_chars budget; truncates with flag; includes source attribution when include_provenance=True

[[2026-05-27T00:36:34+02:00]]
## Research

Completed research for QueryFacade entity lookup & render.

**Key findings:**
- `lookup_entity`: straightforward composition of `get_entity`/`find_entities` + `traverse`, EXCEPT `related_chunks` requires a new `chunk_ids_for_entity` protocol method on GraphStore (created as #1887)
- `render_context`: structured markdown-like sections (Entity, Relationships, Sources) with char budget tracking; truncation sets flag, prioritises entity desc > neighbours > chunks
- Both methods are synchronous, matching protocol signatures
- XOR validation on request handled by model_validator (already in protocol)
- Error contract: LookupError for missing entities, ValueError for empty render request

**Trade-off matrix:** See `.owlbear/research/1880-queryfacade-entity-render.md` §3
**Confidence:** 0.85
**Tier:** T1 (autonomous) — composition of existing protocol modules + one trivial protocol addition
**Follow-ups:** #1887 (chunk_ids_for_entity prerequisite)

[[2026-05-27T00:36:40+02:00]]
## Research

Key findings: lookup_entity is composition of get_entity/find_entities + traverse; render_context uses structured markdown sections with char budget. Protocol gap identified: need `chunk_ids_for_entity` on GraphStore (created #1887 as prerequisite). Confidence: 0.85. Tier: T1.

Doc: .owlbear/research/1880-queryfacade-entity-render.md
Follow-up: #1887 (GraphStore chunk_ids_for_entity)

[[2026-05-27T01:53:19+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two closely related read-only methods on existing QueryFacade |
| Interface clarity | PASS (after refinement) | AC rewritten to name exact methods, return fields, and error contracts |
| Dependency correctness | PASS | #1879 (search infra), #1874 (graph ops), #1887 (chunk_ids_for_entity) — all archived |
| Module layering | PASS | QueryFacade reads from Content + Graph, no upward imports |
| TDD compliance | PASS | Proceeds through test-writer |
| KISS/YAGNI | PASS | Direct composition of existing primitives per protocol |
| Premise challenge | PASS | Protocol already defines these methods; this implements them |
| Pattern consistency | PASS | Follows existing QueryFacade.search() pattern (sync, read-only, same error taxonomy) |
| Security surface | PASS | Internal read-only facade, no new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| lookup_entity by ID | get_entity returns None | LookupError | Yes (AC) | Clear error |
| lookup_entity by name | find_entities returns empty | LookupError | Yes (AC) | Clear error |
| traverse on resolved entity | Entity deleted between lookup and traverse | LookupError from traverse | Propagates | Acceptable race |
| chunk_ids_for_entity | Never raises | N/A | N/A | Empty related_chunks |
| get_chunk for related | Returns None for stale chunk | Skip | Impl-defined | Graceful degradation |
| render_context neither input | Neither field populated | ValueError | Yes (AC) | Clear error |

### Design Diverge
- Trigger: skipped — single clear approach (composition of existing primitives per protocol)

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Findings: AC1 trivially true (model_validator in protocol), related_chunks missing from AC, error contracts implicit, dual-input render ambiguity
- Architect response: accepted — refined all 4 AC lines to address gaps. Removed trivial XOR AC (protocol handles it). Added explicit error contracts, related_chunks requirement, and RenderedContext metadata fields.

### Proof-Bundle Validation
- Planner assignment: null (not set)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC (4 lines covering error contracts, related_chunks, render metadata), set proof_bundle=behavioral, advanced to todo.

[[2026-05-27T02:01:09+02:00]]
## Test-Writer Notes

- **Test file:** `tests/test_query_facade_1880.py`
- **Class:** `TestFromAC_LookupEntity`, `TestFromAC_RenderContext`
- **Total:** 24 tests — all FAIL (RED phase confirmed by quality-runner)
- **Lint:** ruff clean

### Tests per category

| Category | Count |
|----------|-------|
| Happy path | 12 |
| Edge cases | 4 |
| Error paths | 4 |
| Boundary | 4 |

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — lookup by ID (get_entity), by name (find_entities + entity_type), LookupError on miss | 6 |
| AC2 — EntityLookupResult: entity, neighbourhood (expand_hops boundary), related_chunks (chunk_ids_for_entity), None-skip | 7 |
| AC3 — render_context: QueryResult/EntityLookupResult/both, ValueError on neither, max_chars respected | 5 |
| AC4 — truncated flag, char_count == len(text), include_provenance diff, entity_count ≥ 1, chunk_count ≥ 1 | 6 |

[[2026-05-27T02:07:55+02:00]]
## Builder Notes
- Implementation: added `lookup_entity` and `render_context` plus focused private helpers in `serve/knowledge/src/owlbear_knowledge/query_facade.py`
- Files changed: `serve/knowledge/src/owlbear_knowledge/query_facade.py`
- Tests (RED verification): `tests/test_query_facade_1880.py` initially failed (21 failing TestFromAC cases due missing methods)
- Tests (GREEN verification): 55 passed, 0 failed across `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py`
- Coverage: 93% on `owlbear_knowledge.query_facade`
- Lint: ruff clean (no violations)
- Evidence summary:
  - lookup by ID/name now resolves via `get_entity` / `find_entities(EntityQuery(...))`, raising `LookupError` on miss
  - neighbourhood expansion uses `TraversalQuery(max_hops=expand_hops)` and is skipped when `expand_hops=0`
  - related chunks are resolved via `chunk_ids_for_entity` -> `get_chunk`, skipping stale `None` chunks
  - context rendering supports query/entity/both, enforces max_chars with truncation flag, includes optional provenance, and reports `char_count`, `chunk_count`, `entity_count`
- Fixes applied during verification:
  - refactored `render_context` into helper methods to satisfy complexity lint rules
  - adjusted related chunk loading to comprehension style for perf lint rule compliance
- Commit: `084dab6f`

[[2026-05-27T02:26:29+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: task body reports 55 passed / 0 failed across `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py`, 93% coverage on `owlbear_knowledge.query_facade`, and ruff clean.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | `render_context` returns `entity_count` / `chunk_count` gathered before truncation, so metadata can describe content no longer present in the returned text. | `serve/knowledge/src/owlbear_knowledge/query_facade.py:99-123` (counts accumulated at `:99-109`, text truncated at `:115-117`, pre-truncation totals returned at `:122-123`) | in-progress |
| 2 | AC3 | Success-path render tests only prove non-crash/basic shape; they do not prove structured sections are emitted or that both inputs are rendered together. | `tests/test_query_facade_1880.py:329-360` | in-progress |
| 3 | AC4 | Provenance/count proof is too weak: provenance only checks whole-string inequality, and multi-entity / multi-chunk fixtures assert only `>= 1`, so broken attribution or under/over-counting would still pass. | `tests/test_query_facade_1880.py:418-463` (fixtures at `:441` and `:455`; assertions at `:435`, `:449`, `:463`) | in-progress |
| 4 | AC1 | Positive name-path lookup is not asserted beyond call shape; no test would fail if `lookup_entity` returned the wrong entity after `find_entities`. | `tests/test_query_facade_1880.py:212-228` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make `render_context` metadata consistent with the returned truncated text and keep the contract explicit in task-scoped tests. | `serve/knowledge/src/owlbear_knowledge/query_facade.py`, `tests/test_query_facade_1880.py` | Finding #1 |
| 2 | builder | Strengthen `render_context` tests to assert actual section content, combined query+entity rendering, query provenance output, and exact entity/chunk counts from the rendered result. | `tests/test_query_facade_1880.py` | Findings #2-#3 |
| 3 | builder | Add a positive name-path assertion proving `lookup_entity` returns the resolved entity from `find_entities`, not just that the query object was constructed correctly. | `tests/test_query_facade_1880.py` | Finding #4 |

## Observations
- AC1/AC2 code mapping is otherwise solid: ID vs name lookup, `expand_hops=0` skip, traversal wiring, and stale/empty related chunk handling all align with `serve/knowledge/src/owlbear_knowledge/query_facade.py:53-81` and `tests/test_query_facade_1880.py:184-315`.
- I did not independently rerun quality-runner because the builder packet was complete and the blocking issues are AC/code/test-quality defects, not missing execution evidence.

[[2026-05-27T02:34:40+02:00]]
## Builder Notes
- Implementation: updated render metadata accounting in `serve/knowledge/src/owlbear_knowledge/query_facade.py` so `entity_count` and `chunk_count` are derived from fully rendered lines that survive truncation.
- Fix applied for review finding #1: `render_context` now builds output incrementally against `max_chars` and only credits entity/chunk metadata for included (non-partial) segments.
- Approach: replaced aggregate pre-truncation counting with line-entry metadata + `_build_rendered_output(...)` truncation-aware assembly.
- Tests (task-scoped): `tests/test_query_facade_1880.py` -> 24 passed, 0 failed.
- Tests (query facade scope): `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py` -> 55 passed, 0 failed.
- Coverage: 93% on `owlbear_knowledge.query_facade` (scoped run with 1879+1880 suites).
- Lint: ruff clean for `serve/knowledge/src/owlbear_knowledge/query_facade.py`, `tests/test_query_facade_1879.py`, `tests/test_query_facade_1880.py`.
- Module-level durable test file: none present for query_facade (package-local/root), so durable-file check skipped.
- Commit: `ecd2e8d6`

[[2026-05-27T02:43:00+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: latest builder note reports `tests/test_query_facade_1880.py` 24 passed / 0 failed, `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py` 55 passed / 0 failed, 93% coverage on `owlbear_knowledge.query_facade`, and ruff clean from commit `ecd2e8d6`.
- Routing: backlog. This is the second review cycle on the task, and blocking proof gaps remain.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | Positive name-path success proof is still missing. The suite verifies `find_entities(...)` call shape and `entity_type` wiring, but does not assert that `lookup_entity(...)` returns the entity chosen from the name lookup, so returning the wrong match would still pass. | `tests/test_query_facade_1880.py:212-228`; `serve/knowledge/src/owlbear_knowledge/query_facade.py:124-134` | backlog |
| 2 | AC3 | Success-path render tests still prove only type/basic shape for query-only, entity-only, and dual-input calls. They do not prove the returned text actually contains content from the provided query/entity inputs, so a regression that drops one or both inputs would still pass. | `tests/test_query_facade_1880.py:329-360` | backlog |
| 3 | AC4 | Proof for provenance/count rendering remains too weak. The query-result provenance branch is implemented but unexercised, entity provenance is only checked via whole-string inequality, and count assertions remain `>= 1` instead of exact counts from the rendered output. Broken attribution or under/over-counting would still false-green. | `serve/knowledge/src/owlbear_knowledge/query_facade.py:168-176`; `tests/test_query_facade_1880.py:418-463` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-open the proof plan for AC1 and require a retry that asserts the positive name-lookup path returns the entity selected by `find_entities(...)`, not just the query object shape. | `tests/test_query_facade_1880.py` | Finding #1 |
| 2 | architect | Re-scope AC3 proof so the retry must assert rendered output includes the provided query/entity content for query-only, entity-only, and dual-input cases. | `tests/test_query_facade_1880.py` | Finding #2 |
| 3 | architect | Re-scope AC4 proof so the retry must exercise query provenance rendering and assert exact rendered `entity_count` / `chunk_count`, not non-zero lower bounds. | `tests/test_query_facade_1880.py`; `serve/knowledge/src/owlbear_knowledge/query_facade.py` | Finding #3 |

## Observations
- The prior AC4 implementation defect appears fixed: render metadata is now accumulated only for fully included segments before `RenderedContext` is returned. The earlier mismatch between truncated text and metadata is no longer the blocker. Evidence: `serve/knowledge/src/owlbear_knowledge/query_facade.py:116-121`, `serve/knowledge/src/owlbear_knowledge/query_facade.py:213-243`.
- AC2 still maps cleanly: ID vs name lookup, `expand_hops=0` skip, traversal wiring, and stale/empty related chunk handling remain aligned with the task contract.
- I did not independently rerun quality-runner because the builder packet was complete and the blocking issues are remaining proof-quality defects, not missing execution evidence.

[[2026-05-27]]
## Architecture Review (cycle 2)

### Context
Second review cycle. Code implementation is correct — reviewer rejection is purely about test proof quality. The builder wrote tests that verify call shapes and types rather than asserting returned values. Three specific gaps remain after two build cycles.

### Builder Guidance — Required Proof Strengthenings

These are mandatory before the task can pass review. Each maps to a reviewer finding:

**1. AC1 — positive name-path value assertion:**
The test `test_lookup_by_name_calls_find_entities` must set a specific entity as the `find_entities` return value, call `lookup_entity`, and assert `result.entity is <that entity>`. Currently it only verifies the query object shape.

**2. AC3 — rendered content assertions:**
Success-path render tests (query-only, entity-only, dual-input) must assert that `result.text` contains identifiable content from the input fixture (e.g., entity names, chunk text). A no-op render that returns empty/generic text would currently pass. Additionally, the dual-input test must assert content from BOTH inputs appears in the output.

**3. AC4 — exact provenance/count assertions:**
- `entity_count` and `chunk_count` must assert exact values matching the fixture (e.g., 3 entities in fixture with large budget → `entity_count == 3`, not `>= 1`)
- Provenance test must assert specific attribution content appears in text (e.g., `source_id` string present), not just string inequality
- Query-result provenance branch must be exercised (currently only entity provenance is tested)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same scope as prior review |
| Interface clarity | PASS | AC precise, reviewer confirmed code maps cleanly |
| Dependency correctness | PASS | All deps archived |
| Module layering | PASS | No changes |
| TDD compliance | PASS | Test file exists, gaps are assertion strength not coverage |
| KISS/YAGNI | PASS | No changes |
| Premise challenge | PASS | Protocol requires these methods |
| Pattern consistency | PASS | No changes |
| Security surface | PASS | No changes |
| Single domain | PASS | Knowledge only |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (test file exists, builder strengthens assertions)

### Challenge Results
- Challenger: SKIPPED — re-approval of previously challenged and approved task with no AC changes, only proof-quality guidance added

### Verdict: APPROVE
### Action Taken: Added explicit proof-quality guidance for 3 reviewer findings. Re-advanced to todo for builder retry.

[[2026-05-27T02:52:36+02:00]]
## Architecture Review (cycle 2)
Re-approval after reviewer rejection for test proof-quality gaps. AC unchanged — implementation is correct. Added explicit builder guidance for 3 specific proof strengthening requirements: (1) positive name-path value assertion, (2) rendered content assertions proving input appears in output, (3) exact count/provenance assertions instead of lower-bound checks. Challenger skipped — no AC or design changes from prior approved review.

[[2026-05-27T02:57:52+02:00]]
## Test-Writer Notes
- Retry: surgical gap-fill for 3 reviewer findings. All new tests PASS against current impl.
- Builder skip: test-only retry per Step 1b.1 — all 8 new tests are green.
- Test file: tests/test_query_facade_1880.py
- Classes: TestFromAC_LookupEntity, TestFromAC_RenderContext
- Tests per category (new only): happy 4, edge 0, error 0, boundary 4
- Total (all): 32 tests, all PASS (24 original + 8 new)
- ruff: clean

### Gap coverage (new tests only)
| Reviewer Finding | New Test(s) |
|-----------------|-------------|
| AC1 — name-path returns wrong entity without value assertion | test_lookup_by_name_returns_resolved_entity |
| AC3 — query-only render drops chunk text | test_render_context_query_text_contains_chunk_content |
| AC3 — entity-only render drops entity name | test_render_context_entity_text_contains_entity_name |
| AC3 — dual-input drops one or both inputs | test_render_context_dual_input_text_contains_both_sources |
| AC4 — entity_count >= 1 not exact | test_render_context_entity_count_exact |
| AC4 — chunk_count >= 1 not exact | test_render_context_chunk_count_exact |
| AC4 — query provenance branch unexercised | test_render_context_query_provenance_includes_source_id |
| AC4 — entity provenance checks string inequality only | test_render_context_entity_provenance_includes_source_id |

[[2026-05-27T03:10:15+02:00]]
## Review Evidence
- Verdict: FAIL
- Evidence reviewed first: latest retry notes report 32 passed, 0 failed in tests/test_query_facade_1880.py, ruff clean, and builder-skip on a test-only retry; prior builder evidence on the unchanged implementation reports 55 passed, 0 failed across tests/test_query_facade_1879.py and tests/test_query_facade_1880.py with 93% coverage on owlbear_knowledge.query_facade and ruff clean.
- Routing: backlog. This is a repeated review cycle, so the new blocking finding routes back to architect.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | On the truncation path, render_context appends a partial final segment but only increments entity_count and chunk_count for fully included lines. That means RenderedContext can under-report entity or chunk content that is visibly present in the returned text. The task-scoped suite does not combine truncation with exact count assertions, so this defect false-greens. | serve/knowledge/src/owlbear_knowledge/query_facade.py:225, serve/knowledge/src/owlbear_knowledge/query_facade.py:233, serve/knowledge/src/owlbear_knowledge/query_facade.py:234, serve/knowledge/src/owlbear_knowledge/query_facade.py:239, serve/knowledge/src/owlbear_knowledge/query_facade.py:155, serve/knowledge/src/owlbear_knowledge/query_facade.py:164, serve/knowledge/src/owlbear_knowledge/query_facade.py:191, serve/knowledge/src/owlbear_knowledge/query_facade.py:197, serve/knowledge/src/owlbear_knowledge/query_facade.py:206, serve/knowledge/src/owlbear_knowledge/query_facade.py:209, tests/test_query_facade_1880.py:405, tests/test_query_facade_1880.py:540, tests/test_query_facade_1880.py:558 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-open AC4 truncation-count semantics for partially rendered entity and chunk lines, then require a retry that makes metadata consistent with truncated returned text and proves it with task-scoped tests that assert exact entity_count and chunk_count on truncated output. | serve/knowledge/src/owlbear_knowledge/query_facade.py, tests/test_query_facade_1880.py | Finding #1 |

## Observations
- The earlier proof gaps are otherwise closed: name-path success now asserts the resolved entity, dual-input render asserts content from both inputs, and query/entity provenance checks now assert concrete source IDs.
- I did not independently rerun quality-runner because the upstream execution evidence was sufficient for review and the blocker is a concrete AC4 code-plus-proof defect visible from the current source and tests.

[[2026-05-27T03:21:35+02:00]]
## Architecture Review (cycle 3)

### Context
Third review cycle. Code implementation is correct for AC1-AC3. Single remaining defect: on the truncation path, `_build_rendered_output` appends a partial final segment but only counts fully-included lines in metadata. Reviewer finding is accurate — metadata can under-report content visible in the returned text.

### AC4 Refinement
Clarified truncation semantics: "truncation drops incomplete lines (no partial segments emitted)" and "counting only fully included entries." This eliminates the ambiguity that allowed the defect.

### Builder Guidance — Required Fix

**Code change (surgical):** In `serve/knowledge/src/owlbear_knowledge/query_facade.py`, method `_build_rendered_output`, remove the partial-append branch. When `next_len > max_chars`, do NOT append `segment[:remaining]`. Just set `truncated = True` and `break`. The rendered output should contain only complete lines.

Current code (approx lines 235-240):
```python
remaining = max_chars - current_len
if remaining > 0:
    rendered_parts.append(segment[:remaining])
truncated = True
break
```

Fix:
```python
truncated = True
break
```

**Test requirement:** Add a test that:
1. Provides fixtures with multiple entity/chunk entries
2. Sets `max_chars` to a value that allows some entries fully but not the next one
3. Asserts `truncated == True`
4. Asserts `entity_count` exactly matches the number of entity IDs from fully-included lines
5. Asserts `chunk_count` exactly matches chunk entries from fully-included lines
6. Asserts the partial line does NOT appear in `result.text`

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same scope |
| Interface clarity | PASS | AC4 now unambiguous on truncation semantics |
| Dependency correctness | PASS | All deps (#1879, #1874, #1887) archived |
| Module layering | PASS | No change |
| TDD compliance | PASS | Existing test file, builder adds boundary test |
| KISS/YAGNI | PASS | Fix removes code (partial-append branch) |
| Premise challenge | PASS | Protocol requires these methods |
| Pattern consistency | PASS | Line-boundary truncation is simpler and more predictable |
| Security surface | PASS | Internal read-only facade |
| Single domain | PASS | Knowledge only |

### Failure Mode Map
Unchanged from cycle 1 — no new failure modes introduced.

### Design Diverge
- Trigger: skipped — single clear fix (remove partial-append branch)

### Challenge Results
- Challenger: block (confidence 0.22)
- Findings: (1) repo still contains defect code, (2) tests don't prove new truncation semantics, (3) AC was ambiguous
- Architect response: rebutted — challenger misreads pipeline flow. Approval with refined AC is what triggers the builder fix cycle. The AC refinement (point 3) is applied in this review. Points 1 and 2 are precisely what the builder will address in the next cycle. The architect does not write code.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (test file exists, builder adds truncation-boundary test)

### Verdict: APPROVE
### Action Taken: Refined AC4 to specify line-boundary truncation semantics. Added explicit builder guidance for the 2-line code fix and required boundary test. Advanced to todo.

[[2026-05-27T03:35:55+02:00]]
test-writer crashed once (no response); releasing claim before retry

[[2026-05-27T03:41:04+02:00]]
## Test-Writer Notes
- Retry (cycle 3): surgical gap-fill for architect cycle-3 truncation-semantics finding.
- **Test file:** `tests/test_query_facade_1880.py`
- **Class:** `TestFromAC_RenderContext`
- **New test:** `test_render_context_truncation_no_partial_line_appended` (1 test)
- **Total:** 33 tests — 32 pass, 1 FAIL (RED phase confirmed by quality-runner)
- **Lint:** ruff clean

### Tests per category (new only)
| Category | Count |
|----------|-------|
| Boundary | 1 |

### AC Coverage (new test)
| AC | Tests |
|----|-------|
| AC4 — truncation drops incomplete lines; partial segments must not appear in output | `test_render_context_truncation_no_partial_line_appended` |

### Failure evidence
```
FAILED tests/test_query_facade_1880.py::TestFromAC_RenderContext::test_render_context_truncation_no_partial_line_appended
AssertionError: assert 'GammaLinePartial' not in result.text
```
Mechanism: current `_build_rendered_output` appends `segment[:remaining]` when remaining > 0; with remaining=50, the partial GammaLine prefix (containing "GammaLinePartial") bleeds into the output. The builder must remove the partial-append branch (set `truncated = True; break` without the append).

[[2026-05-27T04:00:51+02:00]]
## Builder Notes
- Implementation: updated truncation behavior in `serve/knowledge/src/owlbear_knowledge/query_facade.py` (`_build_rendered_output`) to stop at line boundaries when budget is exceeded.
- Files changed: `serve/knowledge/src/owlbear_knowledge/query_facade.py`
- Approach: removed partial-segment append path so incomplete lines are never emitted; now truncation sets `truncated=True` and exits without adding partial text.
- Tests (RED verification): quality-runner on `tests/test_query_facade_1880.py` reported 1 expected failure (`test_render_context_truncation_no_partial_line_appended`).
- Tests (GREEN verification): quality-runner on `tests/test_query_facade_1880.py` reported 33 passed, 0 failed.
- Verification suite: quality-runner on `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py` reported 64 passed, 0 failed.
- Coverage: 96% on `owlbear_knowledge.query_facade`.
- Lint: ruff clean for `serve/knowledge/src/owlbear_knowledge/query_facade.py`, `tests/test_query_facade_1879.py`, `tests/test_query_facade_1880.py`.
- Module-level durable test file: none present for query_facade (package-local/root), skipped.
- Commit: `46ad205a`
- Evidence summary: AC4 truncation semantics now align with refined requirement: no partial segments emitted and counts continue to represent fully included entries only.

[[2026-05-27T04:29:27+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: latest builder note reports 33 passed / 0 failed in `tests/test_query_facade_1880.py`, 64 passed / 0 failed in `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py`, 96% coverage on `owlbear_knowledge.query_facade`, and ruff clean from commit `46ad205a`.
- Behavioral-bundle challenger cross-check returned `reconsider` (0.74) and exposed one remaining blocking boundary defect, which I then confirmed directly in the current source.
- Routing: `backlog`. This is a repeated review cycle and the blocking issue crosses request-boundary semantics and implementation behavior.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | `EntityLookupRequest` accepts a mixed request like `entity_id=""` + `entity_name="Alice"` because the validator uses truthiness, but `QueryFacade._resolve_entity` treats that same request as an ID lookup because it branches on `is not None`; `lookup_entity` then reports the miss as a name lookup. The task suite only covers non-empty ID/name inputs, so this accepted boundary case false-greens. | `serve/knowledge/src/owlbear_knowledge/protocols/query.py:61-72`; `serve/knowledge/src/owlbear_knowledge/query_facade.py:60-64`; `serve/knowledge/src/owlbear_knowledge/query_facade.py:124-133`; `tests/test_query_facade_1880.py:184-250` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-open AC1/request-boundary semantics for empty-string lookup fields, then require a retry that makes `EntityLookupRequest` validation and `QueryFacade.lookup_entity` branch selection consistent and adds a task-scoped test for the accepted or rejected boundary case. | `serve/knowledge/src/owlbear_knowledge/protocols/query.py`, `serve/knowledge/src/owlbear_knowledge/query_facade.py`, `tests/test_query_facade_1880.py` | Finding #1 |

## Observations
- The latest builder fix for AC4 appears correct: `_build_rendered_output` now stops at line boundaries without appending partial segments, and the new boundary test asserts `truncated=True`, exact truncated counts, and absence of the partial line. Evidence: `serve/knowledge/src/owlbear_knowledge/query_facade.py:213-239`; `tests/test_query_facade_1880.py:632-678`.
- AC2-AC4 otherwise map cleanly in the current source/tests: neighbourhood skip at `expand_hops=0`, related chunk loading, dual-input rendering, provenance inclusion, exact count assertions, and no-partial-line truncation proof are all present.
- I did not dispatch `quality-runner` because the builder evidence packet was complete and internally consistent; the blocker is a concrete boundary defect/proof gap visible from the current source and tests.

[[2026-05-27T04:46:06+02:00]]
## Architecture Review (cycle 4)

### Context
Fourth review cycle. Single remaining defect: `_resolve_entity` uses `is not None` for branching while the validator and error reporting use truthiness. This causes `entity_id=""` + `entity_name="Alice"` to take the ID branch (returning None) then report a name miss.

### AC1 Refinement
Added explicit boundary semantics: "empty-string fields are treated as absent (name-path selected when entity_id is empty string)." This is independently verifiable without referencing internal validator behavior.

### Builder Guidance — Required Fix

**Code change (1 line):** In `serve/knowledge/src/owlbear_knowledge/query_facade.py`, method `_resolve_entity`, change:
```python
if request.entity_id is not None:
```
to:
```python
if request.entity_id:
```

This makes branching consistent with the validator's truthiness-based acceptance and the error-reporting truthiness check.

**Test requirement:** Add a boundary test that:
1. Creates an `EntityLookupRequest(entity_id="", entity_name="Alice")`
2. Mocks `find_entities` to return a known entity
3. Calls `lookup_entity`
4. Asserts the returned `result.entity` is the entity from `find_entities` (proving name-path was taken, not ID-path)
5. Asserts `get_entity` was NOT called (proving ID-path was not taken)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same scope |
| Interface clarity | PASS | AC1 now explicitly defines empty-string boundary behavior |
| Dependency correctness | PASS | All deps archived |
| Module layering | PASS | No change |
| TDD compliance | PASS | Existing test file, builder adds boundary test |
| KISS/YAGNI | PASS | Fix removes a distinction (simplifies) |
| Premise challenge | PASS | Protocol requires these methods |
| Pattern consistency | PASS | Truthiness-based branching matches validator and error reporting |
| Security surface | PASS | Internal read-only facade |
| Single domain | PASS | Knowledge only |

### Design Diverge
- Trigger: skipped — single clear fix (truthiness alignment)
- Alternative considered: reject empty strings at validator level. Rejected because modifying the protocol contract is out of scope for this task.

### Challenge Results
- Challenger: reconsider (confidence 0.63)
- Findings: (1) contract ambiguity between reject-at-validator vs accept-and-branch, (2) AC wording referenced validator internals, (3) proof plan too narrow
- Architect response: accepted findings 2 and 3 — rewrote AC1 to explicitly state boundary behavior without referencing validator internals, expanded test requirement to prove both positive path AND negative exclusion. Rebutted finding 1: modifying the protocol validator is out of scope for this task (protocol established by prior tasks).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (test file exists, builder adds boundary test)

### Verdict: APPROVE
### Action Taken: Refined AC1 with explicit empty-string boundary semantics. Added surgical builder guidance (1-line fix + boundary test with both positive and negative assertions). Advanced to todo.

[[2026-05-27T04:55:04+02:00]]
## Test-Writer Notes
- Retry (cycle 4): surgical gap-fill for architect cycle-4 boundary finding.
- **Test file:** `tests/test_query_facade_1880.py`
- **Class:** `TestFromAC_LookupEntity`
- **New test:** `test_lookup_empty_entity_id_treats_as_absent_takes_name_path` (1 test)
- **Total:** 34 tests — 33 pass, 1 FAIL (RED phase confirmed by quality-runner)
- **Lint:** ruff clean

### Tests per category (new only)
| Category | Count |
|----------|-------|
| Boundary | 1 |

### AC Coverage (new test)
| AC | Tests |
|----|-------|
| AC1 — empty-string entity_id treated as absent; name-path selected | `test_lookup_empty_entity_id_treats_as_absent_takes_name_path` |

### Failure evidence
```
FAILED tests/test_query_facade_1880.py::TestFromAC_LookupEntity::test_lookup_empty_entity_id_treats_as_absent_takes_name_path
AssertionError: assert EntityRecord(id='ent-1'...) is EntityRecord(id='ent-alice'...)
```
Mechanism: `_resolve_entity` branches on `is not None`; `entity_id=""` is not None so `get_entity("")` is called (returns mock default ent-1) instead of `find_entities`. Builder must change `if request.entity_id is not None:` → `if request.entity_id:` in `_resolve_entity`.

[[2026-05-27T09:47:00+02:00]]
## Builder Notes
- Implementation: updated `_resolve_entity` in `serve/knowledge/src/owlbear_knowledge/query_facade.py` to treat empty `entity_id` as absent by changing the ID-branch guard from truthy-agnostic to truthy-only (`if request.entity_id:`).
- Files changed: `serve/knowledge/src/owlbear_knowledge/query_facade.py`
- Approach: surgical one-line fix to align `lookup_entity` branch selection with AC1 boundary semantics and existing truthiness-based error-path behavior.
- Tests (RED verification): `tests/test_query_facade_1880.py` -> 33 passed, 1 failed (`TestFromAC_LookupEntity::test_lookup_empty_entity_id_treats_as_absent_takes_name_path`).
- Tests (GREEN verification): `tests/test_query_facade_1879.py` + `tests/test_query_facade_1880.py` -> 65 passed, 0 failed.
- Coverage: 96% on `owlbear_knowledge.query_facade`.
- Lint: ruff clean for `serve/knowledge/src/owlbear_knowledge/query_facade.py`, `tests/test_query_facade_1879.py`, `tests/test_query_facade_1880.py`.
- Module-level durable test file: none present for `query_facade` (package-local or root `test_query_facade.py`), so durable-file check skipped.
- Commit: `4a375bbc76eabc6a1d50da5aec8fde8a1bf857a7`
- Evidence summary: empty-string `entity_id` requests now follow name-path lookup as required; new boundary `TestFromAC` failure is resolved and task-scoped suites are green.

[[2026-05-27T10:09:11+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1880 to docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: latest builder note reports 65 passed / 0 failed across tests/test_query_facade_1879.py and tests/test_query_facade_1880.py, 96% coverage on owlbear_knowledge.query_facade, and ruff clean from commit 4a375bbc76eabc6a1d50da5aec8fde8a1bf857a7.
- Independent slice check: current editor diagnostics report no errors in serve/knowledge/src/owlbear_knowledge/query_facade.py, serve/knowledge/src/owlbear_knowledge/protocols/query.py, and tests/test_query_facade_1880.py.
- Challenger cross-check: proceed with confidence 0.84; no concrete blocking AC, implementation, or proof defect surfaced.
- AC evidence map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/knowledge/src/owlbear_knowledge/query_facade.py:56-80, serve/knowledge/src/owlbear_knowledge/query_facade.py:124-132, serve/knowledge/src/owlbear_knowledge/protocols/query.py:53-72 | tests/test_query_facade_1880.py:184-291 | PASS |
| AC2 | serve/knowledge/src/owlbear_knowledge/query_facade.py:67-80, serve/knowledge/src/owlbear_knowledge/query_facade.py:130-141 | tests/test_query_facade_1880.py:297-363 | PASS |
| AC3 | serve/knowledge/src/owlbear_knowledge/query_facade.py:83-122, serve/knowledge/src/owlbear_knowledge/query_facade.py:143-210 | tests/test_query_facade_1880.py:375-426, tests/test_query_facade_1880.py:513-562 | PASS |
| AC4 | serve/knowledge/src/owlbear_knowledge/query_facade.py:94-122, serve/knowledge/src/owlbear_knowledge/query_facade.py:151-209, serve/knowledge/src/owlbear_knowledge/query_facade.py:213-236, serve/knowledge/src/owlbear_knowledge/protocols/query.py:78-139 | tests/test_query_facade_1880.py:427-505, tests/test_query_facade_1880.py:571-709 | PASS |

## Observations
- The prior AC1 blocker is closed: _resolve_entity now treats empty entity_id as absent on the lookup branch, matching the request-boundary semantics, and the task test proves both positive name-path resolution and negative ID-path exclusion.
- The prior AC4 blocker is closed: _build_rendered_output now truncates on full-line boundaries only, and the task test proves truncated output, exact truncated counts, and absence of partial-line bleed.
- Non-blocking: query-result graph-context rendering at serve/knowledge/src/owlbear_knowledge/query_facade.py:159-166 is code-inspected rather than isolated by a dedicated task-scoped assertion. Current AC3 proof remains sufficient because query content, dual-input inclusion, provenance, and budget handling are directly asserted.
