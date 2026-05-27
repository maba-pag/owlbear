---
id: 1892
title: 'Knowledge: MCP wire store_enrichment phase-1 to submit_extractions'
status: todo
priority: needed
created: 2026-05-27T01:00:59.321864+02:00
updated: 2026-05-27T09:59:24.595903+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - Phase-1 path (chunk_id provided) calls EnrichmentStore.submit_extractions() 
    — removes direct SQL and BEGIN/COMMIT transaction management for this path
  - "Input entity dicts parsed into ExtractedEntity: dict key 'id' → local_ref, 'name'
    → name, 'entity_type' validated against protocols.common.EntityType (12-value
    enum, default CONCEPT), 'description' → description (default ''), 'confidence'
    → confidence (default 1.0)"
  - "Input edge dicts parsed into ExtractedRelation: 'source_id' → source_ref, 'target_id'
    → target_ref, 'relation'/'relationship' validated against protocols.common.RelationType
    (13-value enum), 'weight' → weight (default 1.0)"
  - Phase-2 path (candidate_id provided) remains on _persist_phase2_enrichment 
    helper (unchanged)
  - LookupError from submit_extractions raised as ToolError
  - 'On parsing failure (invalid enum value, missing required field): call enrichment_store.mark_failed(chunk_id,
    error_str) then raise ToolError'
  - 'ValueError from submit_extractions (unresolved relation source_ref/target_ref
    not matching entity local_refs): call enrichment_store.mark_failed(chunk_id, error_str)
    then raise as ToolError'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace _persist_phase1_enrichment() in `store_enrichment` with EnrichmentStore.submit_extractions(). Parse input entity/edge dicts into ExtractedEntity and ExtractedRelation models. Keep phase-2 (candidate_id) path on old helper.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`

[[2026-05-27T03:15:58+02:00]]
## Research
- Research doc: .owlbear/research/store-enrichment-phase1-wiring.md
- Sources: 7 studied, all codebase-internal (high relevance)
- Recommendation: straightforward wiring (confidence: .85)
- Key findings:
  - Dict→model parsing is mechanical: entity `id`→`local_ref`, edge `source_id`→`source_ref`
  - CRITICAL: Protocol EntityType (12 values) differs from legacy models.EntityType (19 values) — existing `_extract_entity_type()` helper validates wrong enum; needs new validation against `protocols.common.EntityType`
  - Same concern for RelationType — `_extract_relation()` validates legacy enum
  - submit_extractions is internally transactional — no explicit BEGIN/commit needed
  - LookupError (chunk not in enrich_queue) → ToolError per AC5; graceful during transition before #1891 wires get_next_batch
  - On parsing failure: call enrichment_store.mark_failed() before raising ToolError
  - claim_token becomes unused for phase-1 path (kept in signature for phase-2)
- Tier: T1 (autonomous — code-level wiring, no new capability)
- No additional follow-ups needed — AC is complete and validated

[[2026-05-27T03:26:26+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One wiring change: phase-1 path → submit_extractions |
| Interface clarity | PASS | AC specifies exact field mappings, enum sources, defaults |
| Dependency correctness | PASS | #1888 (AppContext enrichment_store) is archived/done |
| Module layering | PASS | MCP server → knowledge store; no upward imports |
| TDD compliance | PASS | Test-writer proceeds normally (behavioral bundle) |
| KISS/YAGNI | PASS | Removes ~100 lines of direct SQL, replaces with single store call |
| Premise challenge | PASS | EnrichmentStore.submit_extractions exists and does exactly what's needed |
| Pattern consistency | PASS | Follows same AppContext → store pattern used by other tools |
| Security surface | PASS | No new system boundaries; input validation via Pydantic models |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| submit_extractions | chunk not in enrich_queue | LookupError | AC5: wrapped as ToolError | Agent gets clear error |
| dict→model parsing | invalid entity_type/relation_type | ValueError/KeyError | AC6: mark_failed + ToolError | Chunk retried or failed |
| submit_extractions | graph upsert failure | RuntimeError | Propagates as ToolError | Agent retries |

### Design Diverge
- Trigger: skipped — single valid approach (direct delegation to store method)

### Challenge Results
- Challenger: FALLBACK — subagent returned no response
- Architect response: self-assessed; refined AC2/AC3 enum specificity and added AC6 for failure path

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### AC Refinements Applied
- AC2: specified protocols.common.EntityType (12-value), field mapping id→local_ref, defaults
- AC3: specified protocols.common.RelationType (13-value), field mapping source_id→source_ref
- AC6 (new): parsing failure → mark_failed + ToolError (missing from original)

### Verdict: APPROVE
### Action Taken: Refined AC for enum specificity and failure-path coverage, advanced backlog → todo

[[2026-05-27T03:58:00+02:00]]
## Test-Writer Notes
- Test file: tests/test_store_enrichment_phase1_1892.py
- Classes: TestFromAC_Phase1UsesSubmitExtractions, TestFromAC_EntityDictParsing, TestFromAC_EdgeDictParsing, TestFromAC_LookupErrorAsToolError, TestFromAC_ParsingFailureMarksFailed
- Tests per category: happy 3, edge 10, error 9, boundary 2
- Total: 24 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 — phase-1 calls submit_extractions | test_phase1_calls_submit_extractions, test_phase1_passes_chunk_id_to_submit_extractions, test_phase1_no_direct_sql_begin_in_phase1_path |
| AC2 — entity dict → ExtractedEntity mapping | 8 tests in TestFromAC_EntityDictParsing |
| AC3 — edge dict → ExtractedRelation mapping | 7 tests in TestFromAC_EdgeDictParsing |
| AC4 — phase-2 unchanged | Dropped: tests for unchanged behavior trivially pass with current impl; builder won't touch phase-2 branch |
| AC5 — LookupError → ToolError | test_lookup_error_from_submit_extractions_raised_as_tool_error (asserts submit_extractions was called, confirming error origin) |
| AC6 — parsing failure → mark_failed + ToolError | 5 tests: entity/relation invalid type → mark_failed called with chunk_id + error string |

[[2026-05-27T04:15:53+02:00]]
builder crashed once (no response); releasing claim before retry

[[2026-05-27T04:22:02+02:00]]
## Builder Notes
- Implementation: replaced phase-1 branch in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py to delegate to enrichment_store.submit_extractions(chunk_id, entities, relations); kept phase-2 candidate_id path on _persist_phase2_enrichment unchanged.
- Parsing/mapping added for phase-1 payloads:
  - entity dict -> ExtractedEntity (id->local_ref, name->name, entity_type validated against protocols.common.EntityType with default CONCEPT, description default "", confidence default 1.0)
  - edge dict -> ExtractedRelation (source_id->source_ref, target_id->target_ref, relation/relationship validated against protocols.common.RelationType, weight default 1.0)
- Error handling:
  - LookupError from submit_extractions converted to ToolError.
  - Parse/validation failures call enrichment_store.mark_failed(chunk_id, error_str) then raise ToolError.
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Tests: 24/24 passed in tests/test_store_enrichment_phase1_1892.py (all TestFromAC classes green)
- Lint: ruff clean for scoped paths (server.py + task test)
- Coverage: quality-runner reported 37% for module owlbear_mcp_knowledge.server under scoped run (monolithic module denominator); task-scoped AC tests all passing.
- Module-level durable test file: no separate test_store_enrichment durable module found; skipped.
- Commit: d6416f22 (feat: wire phase-1 enrichment submit_extractions (#1892, builder))

[[2026-05-27T04:40:20+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1892 -> todo | AC2/AC3/AC6 proof is insufficient; the green suite can still false-green key parser behaviors.
- Builder evidence reviewed: task-local suite reported green, lint clean, coverage note reviewed.
- Independent verification:
  - quality-runner: tests/test_store_enrichment_phase1_1892.py -> 24 passed, 0 failed; lint clean.
  - quality-runner: tests/test_enrichment_persistence_1557.py::TestFromAC_StoreEnrichmentPhase2Edges -> 9 passed, 0 failed; lint clean.
- AC checks with sufficient evidence:
  - AC1: PASS — phase-1 delegates to submit_extractions at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:264, covered by tests/test_store_enrichment_phase1_1892.py:84.
  - AC4: PASS for this review — candidate_id branch still delegates to _persist_phase2_enrichment at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:233, and the adjacent phase-2 regression class at tests/test_enrichment_persistence_1557.py:803 passed 9/9.
  - AC5: PASS — LookupError -> ToolError covered by tests/test_store_enrichment_phase1_1892.py:291.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | Task-local tests only assert omitted description/confidence defaults. They do not prove non-default values are passed through, so a parser that hardcodes protocol defaults would still pass. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:296-297; serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py:64-65; tests/test_store_enrichment_phase1_1892.py:152,161 | todo |
| 2 | AC3 | Task-local tests only assert omitted weight defaults. They do not prove a non-default weight is forwarded, so a parser that always emits 1.0 would still pass. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:342; serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py:80; tests/test_store_enrichment_phase1_1892.py:253 | todo |
| 3 | AC6 | AC requires missing required fields to call mark_failed(chunk_id, error_str) then raise ToolError, but the task-local suite only exercises invalid enum values. Missing id, name, source_id, target_id, and missing relation/relationship guards are unexecuted. | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:273,278,324,329,355; tests/test_store_enrichment_phase1_1892.py:314,350 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add task-local tests that pass explicit description and confidence values and assert they survive parsing into ExtractedEntity. | tests/test_store_enrichment_phase1_1892.py | Blocking finding #1 |
| 2 | test-writer | Add task-local tests that pass explicit non-default weight values and assert they survive parsing into ExtractedRelation. | tests/test_store_enrichment_phase1_1892.py | Blocking finding #2 |
| 3 | test-writer | Add task-local tests for missing required id, name, source_id, target_id, and missing relation/relationship, asserting both mark_failed(chunk_id, error_str) and ToolError. | tests/test_store_enrichment_phase1_1892.py | Blocking finding #3 |

## Observations
- The broader tests/test_enrichment_persistence_1557.py file is not a clean phase-1 proof surface after the enrichment-store refactor; reviewer limited independent verification to the phase-2 class so stale unrelated failures would not dominate this task.
- Challenger cross-check requested narrower wording. Final verdict is based on insufficient proof, not on a confirmed implementation defect.

[[2026-05-27T04:48:36+02:00]]
## Test-Writer Notes
- Retry: added 13 tests for reviewer gaps. All 37 tests pass against current impl.
- Builder skip: test-only retry, all tests green.
- Commit: b9abf645

**Gap-fill summary:**
| Reviewer Gap | Tests Added | Class |
|---|---|---|
| AC2: explicit description/confidence not proved | `test_entity_explicit_description_passes_through`, `test_entity_explicit_confidence_passes_through` | `TestFromAC_ExplicitFieldPassthrough` |
| AC3: explicit weight not proved | `test_edge_explicit_weight_passes_through` | `TestFromAC_ExplicitFieldPassthrough` |
| AC6: missing id/name/source_id/target_id/relation paths | 10 tests (ToolError + mark_failed for each) | `TestFromAC_ParsingFailureMarksFailed` |

All tests prove implementation correctly forwards non-default values and calls mark_failed for every missing-required-field path.

[[2026-05-27T05:09:37+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1892 -> backlog | repeated review cycle; phase-1 wiring still leaks a post-parse `ValueError` from `submit_extractions`, and the retry test file is not lint-clean.
- Upstream evidence reviewed: builder note for the `server.py` wiring change, prior review note, and the test-writer retry note for the gap-fill tests.
- Independent verification:
  - `quality-runner`: requested scopes passed (`tests/test_store_enrichment_phase1_1892.py`; `tests/test_enrichment_persistence_1557.py::TestFromAC_StoreEnrichmentPhase2Edges`), so the prior AC2/AC3/AC6 proof gaps are closed and the adjacent phase-2 behavior still holds.
  - `quality-runner`: `ruff check serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_store_enrichment_phase1_1892.py` failed with 10 violations in `tests/test_store_enrichment_phase1_1892.py`; `server.py` is clean.
  - `challenger`: `block` — highlighted an uncaught post-parse `ValueError` path from `submit_extractions`.
- AC checks with sufficient evidence:
  - AC1: PASS — phase-1 still delegates to `submit_extractions`, and the task-local suite proves the chunk path and no phase-1 `BEGIN` call.
  - AC2/AC3: PASS for the previously missing proof holes — explicit non-default `description`, `confidence`, and `weight` are now asserted in `tests/test_store_enrichment_phase1_1892.py:502`, `tests/test_store_enrichment_phase1_1892.py:516`, and `tests/test_store_enrichment_phase1_1892.py:530`.
  - AC4: PASS — `candidate_id` still dispatches through `_persist_phase2_enrichment` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:233`, and the adjacent phase-2 class at `tests/test_enrichment_persistence_1557.py:803` remained green under scoped verification.
  - AC5: PASS — `LookupError` from `submit_extractions` is still wrapped as `ToolError`, covered by `tests/test_store_enrichment_phase1_1892.py:291`.
  - AC6: PASS only for the originally reviewed enum/missing-field cases — the retry added direct `mark_failed` proof at `tests/test_store_enrichment_phase1_1892.py:380`, `tests/test_store_enrichment_phase1_1892.py:403`, `tests/test_store_enrichment_phase1_1892.py:427`, `tests/test_store_enrichment_phase1_1892.py:452`, and `tests/test_store_enrichment_phase1_1892.py:477`.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC6 | Phase-1 invalid relation refs can still escape as raw `ValueError` after parsing succeeds. The MCP wiring only calls `mark_failed(...)` / raises `ToolError` inside the parser catch and only wraps `LookupError` from `submit_extractions`; unresolved `source_ref` / `target_ref` in the store raise `ValueError` instead. This leaves failure handling incomplete for invalid phase-1 input in the changed path. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:255-266`; `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:345-351`; `tests/test_enrichment_store_1876.py:460-515` | backlog |
| 2 | Evidence gate | The retry task-local proof file is not lint-clean. Independent scoped lint failed with 10 Ruff violations in the modified test file, so the current review evidence packet is not clean even though the production file is. | `tests/test_store_enrichment_phase1_1892.py:374,392,397,415,420,440,445,465,470,490`; quality-runner scoped lint report | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-open the task contract and re-dispatch a retry that wraps post-parse `submit_extractions` relation-ref `ValueError` as MCP `ToolError`, calls `mark_failed(chunk_id, error_str)` for that invalid phase-1 path, and adds task-local proof for the mismatch-local_ref case. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_store_enrichment_phase1_1892.py` | Blocking finding #1 |
| 2 | architect | Re-dispatch the retry with a lint-clean requirement for the task-local proof file, including removal of the current Ruff violations in the added tests. | `tests/test_store_enrichment_phase1_1892.py` | Blocking finding #2 |

## Observations
- The retry did close the prior review's explicit passthrough and missing-required-field proof gaps.
- The older phase-1 durable surface in `tests/test_enrichment_persistence_1557.py` still uses legacy payload keys (`type`, `target_name`). That looks stale relative to the new contract and should be explicitly reconciled on the next architecture pass rather than silently treated as active proof.

[[2026-05-27T09:59:24+02:00]]
## Architecture Review (Re-review after reviewer rejection)
### Context
Task returned from review with two blocking findings: (1) uncaught ValueError from submit_extractions for unresolved relation refs, (2) lint violations in task-local test file.

### Findings Disposition
| # | Reviewer Finding | Status | Action |
|---|---|---|---|
| 1 | ValueError from submit_extractions escapes uncaught | CONFIRMED | Added AC7 to task contract |
| 2 | 10 Ruff violations in test file | RESOLVED | File is currently lint-clean (verified via IDE diagnostics) |

### AC7 Rationale
`submit_extractions()` raises ValueError at `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:349` when relation `source_ref`/`target_ref` don't match any submitted entity `local_ref`. The MCP handler at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:264` only catches `LookupError`. Fix: add `except ValueError` alongside `LookupError`, call `mark_failed(chunk_id, error_str)` before raising `ToolError`.

### Failure-Mode Map Correction
The original review listed RuntimeError from graph upsert as \"Propagates as ToolError\" — this was speculative. In practice, sqlite operational errors in the store would be infrastructure failures that should propagate naturally rather than be masked as ToolError. AC7 covers the demonstrated ValueError path only.

### Evaluation (delta only — prior full evaluation at 03:26 still holds)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC7 specifies exact exception, source, side-effect, and wrapped type |
| Security surface | PASS | No new boundaries |

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- Key concerns: (a) AC7 not yet in artifact, (b) behavioral bundle requires proof for new AC, (c) RuntimeError row inconsistency
- Architect response: (a) AC7 now written to task, (b) test-writer will write AC7 proof on next pass through todo, (c) corrected — RuntimeError row was speculative; omitted from AC contract

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (must write AC7 tests for the new ValueError path)

### Verdict: APPROVE
### Action Taken: Added AC7 (ValueError from submit_extractions → mark_failed + ToolError), corrected failure-mode map, advanced backlog → todo
