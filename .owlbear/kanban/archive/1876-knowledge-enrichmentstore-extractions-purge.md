---
id: 1876
title: 'Knowledge: EnrichmentStore — extractions & purge'
status: archived
priority: needed
created: 2026-05-25T19:04:07.626934+02:00
updated: 2026-05-26T08:52:35.908668+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on:
  - 1875
  - 1873
ac:
  - 'submit_extractions(chunk_id, entities, relations) → ExtractionResult: resolves
    each ExtractedEntity via Graph.upsert_entity building local_ref→entity_id map;
    resolves each ExtractedRelation source_ref/target_ref via that map then calls
    Graph.upsert_edge; creates evidence via Graph.add_evidence for each entity (ENTITY
    claim) and edge (EDGE claim); transitions queue item to COMPLETED with completed_at;
    returns ExtractionResult with entity_ids, edge_ids, evidence_ids tuples populated'
  - submit_extractions raises LookupError if chunk_id is not in IN_PROGRESS 
    state in enrich_queue
  - submit_extractions raises ValueError if any relation source_ref or 
    target_ref does not match a local_ref in the submitted entities batch
  - "suggest_intra_doc_edges(document_id) → tuple[SuggestedEdge, ...]: queries content_chunks
    for document's chunk_ids, queries graph_evidence for entity claims per chunk,
    returns SuggestedEdge for each entity pair co-occurring across ≥2 distinct chunks
    with confidence = shared_chunks/total_chunks and relation_type RELATED_TO"
  - suggest_intra_doc_edges raises LookupError if document_id has no chunks in 
    content_chunks (unknown document)
  - 'purge_source(source_id) → EnrichmentPurgeResult: deletes from enrich_queue WHERE
    source_id (count → queue_items_removed), deletes from enrich_extractions WHERE
    source_id (count → extractions_removed); idempotent, never raises'
  - ensure_tables creates enrich_extractions table (id, chunk_id, source_id, 
    batch_id, entity_count, edge_count, submitted_at) with indexes on source_id 
    and chunk_id; idempotent alongside existing enrich_queue and enrich_batches
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Implement extraction submission with local_ref entity cross-referencing, intra-document edge suggestion, and source purge. Completes the EnrichmentStore protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py`
- Design decisions: CP20 (local_ref cross-referencing), D52/D64 (submit_extractions idempotency + non-guarantees)
- Depends on: EnrichmentStore queue (task #1875) for tables; GraphStore entities (task #1873) for upsert_entity
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` (extends same module)

## Implementation Notes

- submit_extractions is the bridge between Enrichment and Graph: it calls Graph.upsert_entity for each extracted entity
- local_ref: agent assigns temporary names to entities within a batch; resolution maps these to stable entity IDs after upsert
- Relations reference source/target entities by local_ref; resolved to actual IDs before calling Graph.upsert_edge
- Steps 1-3 of submit_extractions are idempotent; step 4 (state transition) only on success (D52)
- suggest_intra_doc_edges: heuristic for entities co-occurring across chunks of same document
- purge_source: removes queue entries + batch records for source (used in delete cascade)

[[2026-05-26T06:01:50+02:00]]
## Research
- Research doc: .owlbear/research/1876-enrichmentstore-extractions-purge.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Implement per protocol with GraphStore DI and enrich_extractions audit table (confidence: .90)
- Follow-up tasks created: none (task itself is the implementation unit)
- Decision requests: none (T1 — protocol already specified)

## Challenge Results
- Challenger: FALLBACK — trivial implementation of authoritative protocol
- Confidence in original: .90
- Key findings: (1) GraphStore injected via constructor for entity/edge ops, (2) enrich_extractions table needed for separate purge audit counts, (3) suggest_intra_doc_edges uses co-occurrence heuristic via cross-module reads

[[2026-05-26T06:25:05+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extraction submission + intra-doc edges + purge all serve the same enrichment lifecycle module |
| Interface clarity | PASS | After AC rewrite — all methods match protocol signatures with explicit I/O, error conditions, and evidence creation steps |
| Dependency correctness | PASS | #1875 (archived) provides queue tables; #1873 (archived) provides Graph.upsert_entity/upsert_edge/add_evidence |
| Module layering | PASS | stores/enrichment.py imports protocols and SqliteGraphStore via constructor DI; cross-reads content_chunks at impl layer (permitted per protocol header) |
| TDD compliance | PASS | Greenfield; test-writer handles RED phase |
| KISS/YAGNI | PASS | Three methods exactly matching protocol contract; no hypothetical features |
| Premise challenge | PASS | Required to complete EnrichmentStore protocol; no existing implementation of these methods |
| Pattern consistency | PASS | Follows existing store pattern (sqlite3.Connection, ensure_tables, DI for cross-store ops via constructor) |
| Security surface | PASS | Internal SQLite only; typed Pydantic inputs at boundary; parameterized SQL |
| Single domain | PASS | Knowledge domain exclusively |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| submit_extractions on non-IN_PROGRESS chunk | Invalid state | LookupError | AC-specified | Caller error |
| submit_extractions with unresolved local_ref | Relation references missing entity | ValueError | AC-specified | Caller error |
| suggest_intra_doc_edges unknown document | No chunks in content_chunks | LookupError | AC-specified | Caller error |
| purge_source unknown source | No records to delete | N/A | Idempotent (returns zeros) | None |

### Design Diverge
- Skipped: single clear approach — constructor DI for GraphStore, SQLite audit table, co-occurrence heuristic. No competing approaches.

### Challenge Results
- Challenger: block (confidence 0.34)
- Key findings: (1) AC missing evidence creation step, (2) missing ValueError for unresolved local_ref, (3) AC2 duplicates AC1, (4) missing LookupError for unknown document, (5) purge scope uses banned quantifier \"all\", (6) missing ensure_tables for enrich_extractions
- Architect response: accepted 6/7 findings — rewrote all AC lines to be protocol-exact with evidence steps, error conditions, enumerated purge tables, and table DDL requirement. Rebutted 1/7: dependency status confirmed via show_task (both archived/completed); old decision file is stale artifact.

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Rewrote all 5 AC lines into 7 protocol-exact lines covering submit_extractions full algorithm (entity resolution, relation resolution, evidence creation, state transition, result shape), error conditions (LookupError, ValueError), suggest_intra_doc_edges with error boundary, purge_source with enumerated table scope, and ensure_tables for new enrich_extractions table. Proof bundle set to behavioral. Advanced to todo.

[[2026-05-26T06:53:01+02:00]]
## Test-Writer Notes
- Test file: `tests/test_enrichment_store_1876.py`
- Classes: `TestFromAC_SubmitExtractions`, `TestFromAC_SuggestIntraDocEdges`, `TestFromAC_PurgeSource`, `TestFromAC_EnsureTables`
- Tests per category:
  - Happy path: 16 (entity/edge resolution, evidence creation, COMPLETED transition, confidence calc, purge counts, co-occurrence detection)
  - Edge/boundary: 7 (empty submissions, single-chunk co-occurrence threshold, unknown source, idempotency)
  - Error paths: 9 (LookupError × 4 for non-IN_PROGRESS states, ValueError × 3 for unresolved refs, LookupError × 2 for unknown document)
  - Structural: 10 (table/index existence, column set, idempotent ensure_tables, existing tables preserved)
- Total: 42 tests, all FAIL at fixture setup (`TypeError: EnrichmentStore.__init__() got an unexpected keyword argument 'graph'`)
- Lint: clean (ruff)

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 — submit_extractions happy path | test_returns_extraction_result_with_correct_chunk_id, test_entity_ids_populated_with_one_id_per_entity, test_upsert_entity_called_once_per_entity, test_edge_ids_populated_with_one_id_per_relation, test_upsert_edge_called_with_resolved_entity_ids, test_add_evidence_called_for_each_entity_as_entity_claim, test_add_evidence_called_for_each_edge_as_edge_claim, test_evidence_ids_populated_with_all_evidence_records, test_queue_item_transitions_to_completed_with_timestamp, test_submit_empty_entities_and_relations_completes_item, test_state_transition_step4_occurs_only_after_graph_steps |
| AC2 — LookupError non-IN_PROGRESS | test_raises_lookup_error_if_chunk_not_in_queue, test_raises_lookup_error_if_chunk_is_pending, test_raises_lookup_error_if_chunk_is_completed, test_raises_lookup_error_if_chunk_is_failed |
| AC3 — ValueError unresolved refs | test_raises_value_error_if_source_ref_not_in_entities, test_raises_value_error_if_target_ref_not_in_entities, test_raises_value_error_if_both_refs_unresolved, test_value_error_raised_before_graph_calls_for_unresolved_ref |
| AC4 — suggest_intra_doc_edges | test_returns_tuple_of_suggested_edges, test_entity_pair_co_occurring_in_two_chunks_produces_suggestion, test_suggested_edge_has_related_to_relation_type, test_confidence_equals_shared_chunks_over_total_chunks, test_entity_pair_co_occurring_in_only_one_chunk_not_suggested, test_no_suggestions_when_no_entity_evidence_in_document, test_suggest_does_not_write_to_graph |
| AC5 — LookupError unknown document | test_raises_lookup_error_for_document_with_no_chunks, test_raises_lookup_error_not_empty_tuple_for_unknown_document |
| AC6 — purge_source | test_returns_enrichment_purge_result, test_result_source_id_matches_input, test_purge_removes_enqueue_queue_items_for_source, test_purge_does_not_remove_other_source_queue_items, test_purge_removes_enrich_extractions_for_source, test_purge_returns_zero_counts_for_unknown_source, test_purge_is_idempotent |
| AC7 — ensure_tables | test_enrich_extractions_table_is_created, test_enrich_extractions_has_required_columns, test_index_on_source_id_exists, test_index_on_chunk_id_exists, test_ensure_tables_is_idempotent, test_enrich_queue_table_still_present_after_ensure_tables, test_enrich_batches_table_still_present_after_ensure_tables |

- Builder note: constructor must accept `graph: GraphStore` kwarg; `suggest_intra_doc_edges` reads `content_chunks` and `graph_evidence` tables directly from the shared `db` connection; `purge_source` requires `enrich_extractions` table created by updated `ensure_tables`

[[2026-05-26T07:23:30+02:00]]
## Builder Notes
- Implementation: added GraphStore DI support and completed EnrichmentStore protocol methods in serve/knowledge/src/owlbear_knowledge/stores/enrichment.py (`submit_extractions`, `suggest_intra_doc_edges`, `purge_source`), plus `enrich_extractions` table/index creation in `ensure_tables`.
- Tests: 86 passed (task-scoped suites: tests/test_enrichment_store_1876.py + tests/test_enrichment_store_1875.py).
- Coverage: 97% on `owlbear_knowledge.stores.enrichment`.
- ruff: clean.
- RED verification: quality-runner confirmed all 42 TaskFromAC tests initially failed at fixture setup (`TypeError: EnrichmentStore.__init__() got an unexpected keyword argument 'graph'`).
- Fixes applied:
  - Constructor now accepts optional `graph` dependency; extraction methods require graph and fail fast if absent.
  - `submit_extractions` now enforces IN_PROGRESS guard, resolves local_ref -> entity IDs, validates relation refs, upserts entities/edges, adds ENTITY/EDGE evidence, records extraction audit row, and transitions queue row to COMPLETED only after graph steps succeed.
  - `suggest_intra_doc_edges` now reads `content_chunks` + `graph_evidence`, computes co-occurrence pairs across document chunks, emits RELATED_TO suggestions for pairs shared in >=2 chunks with confidence `shared_chunks/total_chunks`, and raises `LookupError` for unknown documents.
  - `purge_source` now deletes source-owned rows from `enrich_queue` and `enrich_extractions` and returns itemized counts idempotently.
  - Lint hardening: removed dynamic SQL interpolation in suggestion query (`json_each` binding) and replaced threshold magic number with class constant.
- Durable module-level test check: no canonical non-task `test_enrichment_store.py` file exists yet (recorded as skip per workflow).

[[2026-05-26T07:49:51+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: todo
- Builder evidence reviewed first: task notes report 86 passing scoped tests, 97% coverage on `owlbear_knowledge.stores.enrichment`, and clean `ruff` status.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | Task tests do not prove `suggest_intra_doc_edges` is limited to the requested document's chunk set. Every AC4 fixture seeds only `doc-1`, so a regression that accidentally includes other documents' chunks/evidence would still false-green. The implementation currently scopes correctly, but the behavioral proof is missing. | AC4 in task body line 27; implementation scoping at `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:427` and `:441`; task tests only seed `doc-1` at `tests/test_enrichment_store_1876.py:543-629` | todo |
| 2 | AC7 | The index checks are name-based only. A miswired index with a matching name would still pass even though AC7 requires indexes on the `source_id` and `chunk_id` columns. | AC7 in task body line 36; DDL at `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:90` and `:94`; current assertions are `any("source_id" in name ...)` and `any("chunk_id" in name ...)` at `tests/test_enrichment_store_1876.py:775` and `:786` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add an AC4 adversarial test that seeds a second document and proves `suggest_intra_doc_edges` ignores out-of-document chunks/evidence when computing suggested pairs and confidence. | `tests/test_enrichment_store_1876.py` | Review finding #1; current AC4 fixtures only use `doc-1` at `tests/test_enrichment_store_1876.py:543-629` |
| 2 | test-writer | Strengthen AC7 index assertions to inspect indexed columns rather than index-name substrings. | `tests/test_enrichment_store_1876.py` | Review finding #2; current name-only checks at `tests/test_enrichment_store_1876.py:775` and `:786` |

## Observations
- The reviewed implementation path itself appears consistent with the authored AC on these slices; the rejection is for proof sufficiency, not a demonstrated source-code defect.
- Challenger review requested reconsideration because builder evidence and direct code inspection are otherwise consistent. I kept FAIL because `w-code-review` treats missing or lax AC proof as blocking.
- I did not independently rerun `quality-runner`: builder evidence was present and internally consistent, and the blocking findings came from direct AC-to-test proof review rather than contradictory execution output.

[[2026-05-26T08:04:53+02:00]]
## Test-Writer Notes
- Retry: added 4 tests for reviewer gaps. All pass against current impl.
- Builder skip: test-only retry, all tests green.

### New tests added to `tests/test_enrichment_store_1876.py`

**AC4 — adversarial doc-scoping (2 tests):**
- `TestFromAC_SuggestIntraDocEdges::test_suggest_scopes_confidence_to_requested_document_only` — seeds doc-1 (2 chunks, ent-A+B both present) AND doc-2 (2 more chunks, same entities); asserts confidence = 1.0 (2/2), not 0.5 (2/4). A regression omitting document scoping would produce 0.5.
- `TestFromAC_SuggestIntraDocEdges::test_suggest_does_not_include_entity_pairs_from_other_documents` — doc-1 has one solo entity (no pairs possible); doc-2 has ent-C and ent-D co-occurring in 2 chunks (meets threshold); asserts doc-1 result is empty tuple and the C-D pair is absent.

**AC7 — column-level index verification (2 tests):**
- `TestFromAC_EnsureTables::test_source_id_index_covers_source_id_column` — reads `sql` column from `sqlite_master` for each index on `enrich_extractions`; extracts the column list from the DDL (`ON enrich_extractions(...)`) and asserts `source_id` appears there.
- `TestFromAC_EnsureTables::test_chunk_id_index_covers_chunk_id_column` — same DDL-parsing approach for `chunk_id`.

Commit: 33491297

[[2026-05-26T08:25:04+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1876 to docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence reviewed first: builder notes reported scoped proof with 86 passing tests across `tests/test_enrichment_store_1876.py` and `tests/test_enrichment_store_1875.py`, 97% coverage on `owlbear_knowledge.stores.enrichment`, and clean `ruff`.
- Independent retry verification: quality-runner reran the updated `tests/test_enrichment_store_1876.py` suite and lint for that file; result was 46 passed, 0 failed, 0 skipped, with clean `ruff` and no tooling errors.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:306`, `:349`, `:394`, `:411` | `tests/test_enrichment_store_1876.py:241`, `:267`, `:296`, `:317`, `:333`, `:352`, `:368`, `:397` | PASS |
| AC2 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:317` | `tests/test_enrichment_store_1876.py:415`, `:423`, `:432`, `:445` | PASS |
| AC3 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:349` | `tests/test_enrichment_store_1876.py:460`, `:474`, `:502` | PASS |
| AC4 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:424`, `:427`, `:441`, `:466` | `tests/test_enrichment_store_1876.py:566`, `:580`, `:598`, `:614`, `:643`, `:670` | PASS |
| AC5 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:424`, `:427` | `tests/test_enrichment_store_1876.py:703` | PASS |
| AC6 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:475`, `:479`, `:483` | `tests/test_enrichment_store_1876.py:739`, `:752`, `:764`, `:785` | PASS |
| AC7 | `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:48`, `:90`, `:94` | `tests/test_enrichment_store_1876.py:809`, `:818`, `:849`, `:877`, `:902` | PASS |

## Observations
- The prior review blockers are closed: AC4 now has explicit cross-document scoping proof, and AC7 now checks index DDL rather than index names alone.
- AC7 proof is still slightly looser than the implementation because the new assertions accept any index DDL containing the target column names rather than proving two separate single-column indexes. Given the explicit DDL at `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:90` and `:94` and the lack of a demonstrated false-green path on this schema, I treated this as non-blocking.
- Challenger result: proceed, confidence 0.83.

[[2026-05-26T08:33:59+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | NO IMPACT | `EnrichmentStore` is not exported via `owlbear_knowledge.__init__.py` — internal store accessed only via `owlbear_knowledge.protocols` DI. `serve/knowledge/README.md` "Module groups" table lists public exports only (`DocumentStore`, `GraphStore`, `StatusStore`, `KnowledgeSourceStore`). No task-caused README drift. Layer 1 grep: no removed symbols referenced in README. Layer 2: README coherent with post-task package surface. |
| 2. External Attribution | VERIFIED | `.owlbear/sources/overview.md` contains task #1876 entry: `microsoft/graphrag` source linked to `1876-enrichmentstore-extractions-purge.md` (2026-05-26). |
| 3. Research Doc | VERIFIED | `.owlbear/research/1876-enrichmentstore-extractions-purge.md` exists. Linked from task body under `## Research`. |
| 4. Deletion Detection | CLEAN | `git diff HEAD~3 HEAD` shows no lines removed from `stores/enrichment.py` — only additions. No orphaned README references. |

### Files Updated
None — no-impact gate pass.

### Scratch Cleanup
- Removed: `.owlbear/scratch/1876-coverage.json`

[[2026-05-26T08:52:35+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: domain-scoped tests 46 passed, 0 failed, lint clean. Full-suite collection blocked by pre-existing ImportError in unrelated domain (tests/test_mcp_kanban_newline_norm_1531.py imports removed symbol from owlbear_mcp_kanban.server). Confirmed pre-existing via git log (last modified well before task 1876 commits). No task-introduced regressions.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all 3 task commits touch only serve/knowledge/src/owlbear_knowledge/stores/enrichment.py and tests/test_enrichment_store_1876.py — knowledge domain exclusively)
- purpose match: PASS (implements submit_extractions, suggest_intra_doc_edges, purge_source per EnrichmentStore protocol)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
Final AC is protocol-exact with method signatures, return types, error conditions, table DDL, and index requirements. Challenger-driven rewrite produced specific, complete, clean implementation path.

### Commit Integrity
- upstream commit presence: PASS (88033fa8 researcher, 2c7438ff test-writer RED, 6906f32b builder GREEN, 33491297 test-writer retry)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions. All criteria pass.

### Confidence: 1.00
### Action: archive
