---
id: 1900
title: 'Knowledge: Remove legacy AppContext fields and dual-paths (Phase B2a — pure
  cleanup)'
status: archived
priority: medium
created: 2026-05-27T17:56:21.002017+02:00
updated: 2026-05-28T01:24:56.005866+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on: []
ac:
  - AppContext contains only v2 store fields (no query_service, graph_store, 
    ingest_pipeline, intra_doc_builder, structured_extractor)
  - knowledge_search has no legacy fallback path (no query_service branch, no 
    _serialize_legacy_search_results)
  - EnrichmentStore and IngestCoordinator wired with graph_store_v2 (not old 
    GraphStore)
  - list_entities, _legacy_graph_stats, _knowledge_stats_bridge (removes MCP 
    resource knowledge://stats), knowledge_stats_resource deleted
  - init_db() wrapper removed; lifespan uses plain sqlite3.connect() + 
    ensure_tables()
  - No imports from legacy knowledge modules (graph_store, query_service, 
    ingest, document_store, retrieval, schema.init_db, graph_builder, extractor,
    embeddings, models.EntityType) remain in mcp-knowledge package (server.py 
    and _helpers.py)
  - pytest tests/ -k 'knowledge or enrichment or search_provenance or 
    ingest_document or get_next_batch' 
    --ignore=tests/test_mcp_knowledge_lifespan_1888.py 
    --ignore=tests/test_mcp_knowledge_read_tools_1881.py 
    --ignore=tests/test_search_provenance.py 
    --ignore=tests/test_persistence_source_wiring.py 
    --ignore=tests/test_knowledge_tool_rename_1895.py 
    --ignore=tests/test_mcp_kanban_newline_norm_1531.py passes (0 failures, 0 
    errors)
  - 'source_store, refresh_orchestrator retained in AppContext (migrated separately
    in #1904)'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Remove all legacy components from the MCP server AppContext. Wire tools exclusively to v2 store APIs.

## Changes required
- Remove AppContext fields: query_service, graph_store, ingest_pipeline, intra_doc_builder, structured_extractor
- Remove dual-path in `search_knowledge` (delete query_service fallback + `_serialize_legacy_search_results()`)
- Replace `knowledge_stats` legacy helpers (`_legacy_graph_stats`, `_knowledge_stats_bridge`, `knowledge_stats_resource`) — tool already uses v2
- Delete `list_entities` function (deferred/unexposed, uses legacy APIs)
- Remove `init_db()` wrapper that calls `_schema_init_db()`; use plain `sqlite3.connect()` + individual `ensure_tables()` calls in lifespan
- Remove dead legacy imports from server.py (DocumentStore, GraphStore, IngestPipeline, KnowledgeSourceStore, KnowledgeQueryService, GraphAugmentedRetriever, BgeM3EmbeddingProvider, EntityExtractor, EntityType from models, TextChunker, schema.init_db)
- Remove dead code in _helpers.py: `_extract_entity_type()`, `_extract_relation()`, `_validate_enrichment_edge_payload()`, `_stable_edge_id()` and their imports (Edge, EntityType, RelationType from owlbear_knowledge.models)
- Wire `EnrichmentStore(db=conn, graph=graph_store_v2)` instead of old GraphStore — also fixes latent bug (old GraphStore lacks invalidate_evidence_by_chunks)
- Wire `IngestCoordinator(... graph=graph_store_v2)` instead of old GraphStore
- Remove `@mcp.resource(\"knowledge://stats\")` registration (replaced by knowledge_stats tool)
- Remove lifespan construction of: gs (GraphStore), emb (BgeM3EmbeddingProvider), extractor, intra_doc_builder, gar (GraphAugmentedRetriever), qs (KnowledgeQueryService), doc_store (DocumentStore), pipeline (IngestPipeline)

## Retained (B2b scope — #1904)
- source_store (KnowledgeSourceStore) — needed by refresh_orchestrator
- refresh_orchestrator (RefreshOrchestrator) — needs SourceFetcher adapter first
- select_content_fetcher import in _helpers.py — used by refresh_orchestrator construction

## Verification
- pytest tests/ -k 'knowledge or enrichment or search_provenance or ingest_document or get_next_batch' passes
- search_knowledge works without query_service fallback
- Stats function works via v2 stores (IngestCoordinator.stats() + EnrichmentStore.stats())
- No imports from legacy knowledge modules remain in mcp-knowledge package

## Research
See .owlbear/research/mcp-knowledge-v2-migration.md §3.1, §3.2
See .owlbear/research/mcp-knowledge-legacy-removal-b2.md (validates scope split B2a/B2b)

[[2026-05-27T23:34:27+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure deletion/cleanup of legacy code from one module |
| Interface clarity | PASS | ACs specify exact fields removed, functions deleted, wiring targets |
| Dependency correctness | PASS | No depends_on needed; #1904 depends on this task (correct ordering) |
| Module layering | PASS | All changes within mcp-knowledge; graph_store_v2 is same-layer |
| TDD compliance | PASS | Test-writer will write verification tests; existing suite covers regression |
| KISS/YAGNI | PASS | Pure deletion + minimal rewiring; no new abstractions |
| Premise challenge | PASS | Research validates legacy code is dead after v2 stores landed |
| Pattern consistency | PASS | Follows existing v2 wiring patterns already in codebase |
| Security surface | PASS | No new boundaries; removal only |
| Single domain | PASS | knowledge domain exclusively |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| EnrichmentStore wired with graph_store_v2 | invalidate_evidence_by_chunks now works (fixes latent bug) | N/A | Yes | Fixes silent cascade failure on re-ingest |
| knowledge://stats resource removed | Clients querying the MCP resource get 404 | ResourceNotFound | No (intentional removal) | Agents use knowledge_stats tool instead |

### Design Diverge
- Trigger: skipped — single valid approach (deletion/rewiring), no competing designs

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Key findings: (1) body contradicted AC on source_store/refresh_orchestrator scope, (2) AC7 used naked \"All\" quantifier, (3) _helpers.py dead code in scope but unmentioned, (4) knowledge://stats resource removal implicit
- Architect response: accepted all four concerns — refined body to resolve contradiction, tightened AC7 to runnable pytest filter, expanded AC6 to name _helpers.py explicitly, made resource removal explicit in AC4

### Proof-Bundle Validation
- Planner assignment: null (not set)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC and body to resolve scope contradiction and quality issues raised by challenger, then advanced to todo.

[[2026-05-27T23:45:40+02:00]]
## Test-Writer Notes
- Test file: tests/test_mcp_knowledge_legacy_removal_1900.py
- Classes: TestFromAC_AppContextFields, TestFromAC_SearchKnowledgeV2Only, TestFromAC_StorageWiring, TestFromAC_DeletedFunctions, TestFromAC_InitDbRemoved, TestFromAC_NoLegacyImportsServer, TestFromAC_NoLegacyImportsHelpers, TestFromAC_V2RegressionGuard
- Tests per category: happy 0, edge 6, error 4, boundary 34
- Total: 44 tests, all FAIL
- ruff: clean

| AC | Tests |
|----|-------|
| AC1 — AppContext no legacy fields | test_no_query_service_field, test_no_graph_store_field, test_no_ingest_pipeline_field, test_no_intra_doc_builder_field, test_no_structured_extractor_field, test_source_store_retained_and_legacy_absent, test_refresh_orchestrator_retained_and_legacy_absent |
| AC2 — search_knowledge no legacy fallback | test_serialize_legacy_search_results_removed, test_search_knowledge_source_has_no_query_service_branch, test_search_knowledge_source_has_no_legacy_fallback_call |
| AC3 — EnrichmentStore/IngestCoordinator wired with graph_store_v2 | test_enrichment_store_not_wired_with_old_graph_store, test_ingest_coordinator_not_wired_with_old_graph_store, test_enrichment_store_uses_graph_store_v2_keyword |
| AC4 — Deleted functions + MCP resource | test_list_entities_removed, test_legacy_graph_stats_removed, test_knowledge_stats_bridge_removed, test_knowledge_stats_resource_removed, test_knowledge_stats_mcp_resource_not_registered |
| AC5 — init_db wrapper removed | test_init_db_wrapper_removed, test_schema_init_db_not_in_server, test_lifespan_uses_sqlite_connect_not_init_db |
| AC6 server.py | test_no_graph_store_import, test_no_document_store_import, test_no_ingest_pipeline_import, test_no_knowledge_query_service_import, test_no_knowledge_query_error_import, test_no_graph_augmented_retriever_import, test_no_bge_embedding_provider_import, test_no_entity_extractor_import, test_no_text_chunker_import, test_no_models_entity_type_import, test_no_schema_init_db_import, test_no_intra_doc_graph_builder_import |
| AC6 _helpers.py | test_helpers_no_edge_import, test_helpers_no_models_entity_type_import, test_helpers_no_relation_type_import, test_helpers_no_extract_entity_type_function, test_helpers_no_extract_relation_function, test_helpers_no_validate_enrichment_edge_payload, test_helpers_no_stable_edge_id |
| AC7 — V2 regression guard | test_knowledge_search_source_uses_only_v2_error_type, test_appcontext_has_no_required_legacy_positional_args, test_lifespan_does_not_construct_legacy_objects |
| AC8 — source_store/refresh_orchestrator retained | test_source_store_retained_and_legacy_absent, test_refresh_orchestrator_retained_and_legacy_absent, test_appcontext_v2_only_instantiation |

[[2026-05-28T00:04:34+02:00]]
## Builder Notes
- Implementation:
  - Updated `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` to remove legacy AppContext fields (`query_service`, `graph_store`, `ingest_pipeline`, `structured_extractor`, `intra_doc_builder`) and legacy server imports.
  - Removed legacy server paths/functions: `_serialize_legacy_search_results`, `list_entities`, `_legacy_graph_stats`, `_knowledge_stats_bridge`, `knowledge_stats_resource`, and `init_db` wrapper.
  - Rewired lifespan to v2 stores only (`SqliteSourceStore`, `SqliteGraphStore`, `ContentStore`, `EnrichmentStore`, `IngestCoordinator`) with `sqlite3.connect()` and `ensure_tables()` calls.
  - Rewired `knowledge_search` to QueryFacade-only path (no `query_service` fallback).
  - Updated `knowledge_enrichment_retry` to delegate to `EnrichmentStore.reset_failed()` (v2 store API path).
  - Updated `knowledge_stats` claimable-chunk query to v2 table set (`enrich_queue`, `content_chunks`, `content_documents`, `source_registry`).
  - Updated `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py` to remove dead legacy imports/functions: `Edge/EntityType/RelationType` imports, `_extract_entity_type`, `_extract_relation`, `_validate_enrichment_edge_payload`, `_stable_edge_id`.
- Tests:
  - `tests/test_mcp_knowledge_legacy_removal_1900.py`: 44 passed, 0 failed.
  - Focused regression set (`tests/test_mcp_knowledge_legacy_removal_1900.py`, `tests/test_enrichment_tools_registry_1901.py`, `tests/test_get_next_batch_1891.py`, `tests/test_store_enrichment_phase1_1892.py`, `tests/test_ingest_document_coordinator_1893.py`): 150 passed, 0 failed, 3 setup errors.
- Lint:
  - Ruff clean on changed files.
- Coverage (focused regression run):
  - `owlbear_mcp_knowledge.server`: 53%
  - `owlbear_mcp_knowledge._helpers`: 24%

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update ingest-document coordinator fixtures to stop patching removed legacy symbol `BgeM3EmbeddingProvider`; align fixture strategy with #1900 AC6 legacy-import removal. | tests/test_ingest_document_coordinator_1893.py | quality-runner setup errors: `AttributeError: <module 'owlbear_mcp_knowledge.server'> does not have the attribute 'BgeM3EmbeddingProvider'` on 3 tests |
| 2 | test-writer | Reconcile cross-task regression proof for AC7 by removing contradictory legacy-symbol assumptions in ingest-document tests vs #1900 removal assertions. | tests/test_ingest_document_coordinator_1893.py, tests/test_mcp_knowledge_legacy_removal_1900.py | Contradiction observed: #1900 asserts legacy symbol must be absent; ingest-document fixture currently requires patchable presence |

- Reflection:
  - The main blocker was a cross-task test contradiction, not implementation correctness in #1900.
  - v2-only server cleanup is implementable and task-scoped tests are green.
  - Regression setup failures surfaced from fixture assumptions tied to removed legacy module attributes.
  - A test-writer pass is needed before AC7-style broad proof can be satisfied.

[[2026-05-28T00:08:20+02:00]]
## Test-Writer Notes
- Retry: removed stale `patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider")` from `_lifespan_heavy_mocks` fixture in `tests/test_ingest_document_coordinator_1893.py`.
- Root cause: builder (AC6) deleted `BgeM3EmbeddingProvider` from server.py; fixture was patching a now-absent symbol → 3 setup errors.
- Fix: removed dead patch line; `QdrantVectorStore` patch retained (still present); `_ZeroEmbeddingProvider` is internal and needs no patching.
- Outcome: 79 passed, 0 failed, 0 errors — all lifespan proof tests green.
- Ruff: clean.
- Builder skip: test-only retry, all tests green against current impl.

[[2026-05-28T00:22:09+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: backlog
- Summary: AC1, AC2, AC3, AC4, AC5, AC6, and AC8 map to the current v2-only cleanup, but AC7 is still red on independent verification. The failing proof surface is dominated by transition-era durable suites that still assert legacy symbols and old paths removed by this task, so the blocker is proof-plan and AC quality rather than a newly observed source-code defect.
- Challenger: reconsider, confidence 0.66. Accepted on routing: backlog is more accurate than todo because the failing selector mixes superseded transitional contracts with the current cleanup contract.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC7 | The exact required regression selector does not pass after the retry. Independent quality-runner verification reported 323 passed, 101 failed, 25 errors, so the task lacks the executable proof required for PASS. Builder evidence covered the task-local suite and a smaller focused subset, but not the full AC7 selector. | quality-runner verification for task 1900; task body Builder Notes and Test-Writer retry notes | backlog |
| 2 | AC7 | The failing selector is structurally inconsistent with the v2-only cleanup contract. Representative failures still assert removed legacy surfaces: tests/test_mcp_knowledge_lifespan_1888.py:39-48 and 81-130 construct AppContext with removed query_service, graph_store, and ingest_pipeline; tests/test_mcp_knowledge_read_tools_1881.py:102 and 218 import removed init_db and require legacy graph_store coexistence; tests/test_search_provenance.py:36-39 and 112-172 build a query_service-only context and call qs.query; tests/test_persistence_source_wiring.py:152-210 still assert pipeline.ingest_text; tests/test_knowledge_tool_rename_1895.py:142-156 requires _legacy_graph_stats to exist. Those expectations conflict with the current cleanup in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:367-379, 422-459, and 568-592. | cited files and line ranges | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC7 so the required regression proof is aligned with the v2-only cleanup contract, and split stale transition-era durable-suite updates into explicit follow-up task(s) before redispatch. | .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md, tests/test_mcp_knowledge_lifespan_1888.py, tests/test_mcp_knowledge_read_tools_1881.py, tests/test_search_provenance.py, tests/test_persistence_source_wiring.py, tests/test_knowledge_tool_rename_1895.py | Findings 1 and 2 |
| 2 | architect | Create follow-up task(s) for the stale durable suites that still assert query_service, graph_store, ingest_pipeline, pipeline.ingest_text, init_db, or _legacy_graph_stats so test-writing can update or retire them under the current v2-only direction. | tests/test_mcp_knowledge_lifespan_1888.py, tests/test_mcp_knowledge_read_tools_1881.py, tests/test_search_provenance.py, tests/test_persistence_source_wiring.py, tests/test_knowledge_tool_rename_1895.py | Finding 2 |

## Observations
- AC1 and AC8 map in the current AppContext shape: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:367-379 removes query_service, graph_store, ingest_pipeline, intra_doc_builder, and structured_extractor while retaining source_store and refresh_orchestrator.
- AC3, AC4, and AC5 map in app_lifespan: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:422-459 uses sqlite3.connect, QueryFacade, SqliteGraphStore, EnrichmentStore with graph_store_v2, IngestCoordinator with graph_store_v2, and ensure_tables calls; the legacy init_db wrapper and legacy stats helpers are absent.
- AC2 maps in knowledge_search: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:568-592 uses query_facade only and no query_service fallback.
- AC6 appears satisfied on direct inspection: package-level symbol searches found no remaining legacy graph_store, query_service, ingest_pipeline, document_store, retrieval, schema.init_db, graph_builder, extractor, embedding-provider, or models.EntityType imports in the mcp-knowledge package, and serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py no longer contains the removed Edge, EntityType, RelationType, or dead extraction helpers.
- This rejection does not ask the builder to restore removed legacy symbols. The blocker is the review gate and proof boundary, not the cleanup implementation itself.

[[2026-05-28T00:34:00+02:00]]
## Planning
### Decomposition: Retire/update stale transition-era knowledge test suites
- Tasks created: 4
- Dependency layers: 1 (all depend on #1900, independent of each other)
- Scope: knowledge test cleanup

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1905 | P1-01: Delete stale task-scoped knowledge test files (1888, 1881, 1895) | needed | 1900 | knowledge, cleanup, test |
| 1906 | P1-02: Update test_search_provenance.py to v2 QueryFacade interface | needed | 1900 | knowledge, cleanup, test |
| 1907 | P1-03: Update test_persistence_source_wiring.py to v2 ingest interface | needed | 1900 | knowledge, cleanup, test |
| 1908 | P1-04: Update test_server.py knowledge sections to remove legacy symbol patches | needed | 1900 | knowledge, cleanup, test |

### Dependency Graph
```mermaid
graph LR
  1900[\"#1900 Legacy removal\"] --> 1905[\"#1905 Delete task-scoped\"]
  1900 --> 1906[\"#1906 search_provenance\"]
  1900 --> 1907[\"#1907 persistence_wiring\"]
  1900 --> 1908[\"#1908 test_server.py\"]
```

### AC7 Resolution Strategy
AC7 retains the --ignore flags until these 4 follow-up tasks land. Once all four are complete, the knowledge selector runs without --ignore flags (verified by #1905 AC4).

[[2026-05-28T00:35:01+02:00]]
## Architecture Review (Re-review)
### Context
Returned from review with AC7 regression selector too broad — captured stale transition-era tests asserting removed legacy symbols. Reviewer required: (1) refine AC7, (2) create follow-up tasks for stale suites before redispatch.

### Actions Taken
1. Refined AC7: added --ignore flags for 5 stale test files (test_mcp_knowledge_lifespan_1888, test_mcp_knowledge_read_tools_1881, test_search_provenance, test_persistence_source_wiring, test_knowledge_tool_rename_1895) that assert legacy surfaces removed by this task.
2. Created follow-up tasks #1905–#1908 (depend on #1900) covering: deletion of task-scoped stale tests, v2 update of durable suites (search_provenance, persistence_source_wiring), and test_server.py legacy patch cleanup.

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Key findings: (1) AC7 must be edited in artifact before approval, (2) follow-up tasks required before redispatch, (3) --ignore exhaustiveness should be verified by builder/reviewer
- Architect response: accepted all — edited AC7 in artifact, created follow-up tasks, preserved regression breadth via --ignore approach rather than narrowing to explicit file list

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral (unchanged from first review)
- Test-writer: PROCEED (re-verify AC7 with refined selector)

### Evaluation
All original Step 2 criteria PASS (unchanged from first review). No new architecture concerns — this is a proof-plan refinement only.

### Verdict: APPROVE
### Action Taken: Refined AC7 selector with --ignore for stale suites, created follow-up tasks #1905–#1908, advanced to todo for re-verification of refined AC7 command.

[[2026-05-28T00:37:39+02:00]]
## Test-Writer Notes
- Retry: re-verified refined AC7 selector (architect added --ignore flags for 5 stale test files and created follow-up tasks #1905–#1908 before redispatch).
- AC7 refined selector result: 304 passed, 0 failed, 1 pre-existing collection error.
  - Error: `tests/test_mcp_kanban_newline_norm_1531.py` — `ImportError: cannot import name 'create_dr' from 'owlbear_mcp_kanban.server'`. Pre-existing; unrelated to knowledge cleanup. Not introduced by #1900.
  - All knowledge/enrichment/ingest/get_next_batch tests pass.
- All 44 tests in `tests/test_mcp_knowledge_legacy_removal_1900.py` pass (AC1–AC6, AC8 coverage confirmed in prior rounds).
- No new tests needed — reviewer Required Follow-up was for architect (refine AC7 + create follow-up tasks), both resolved.
- Builder skip: test-only retry, all tests green against current impl.

[[2026-05-28T00:47:05+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: backlog
- Summary: AC1, AC2, AC3, AC4, AC5, AC6, and AC8 map to the current v2-only cleanup in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py. AC7 remains unsatisfied: the latest refined proof reports 304 passed, 0 failed, 1 collection error, and direct inspection confirms the remaining error is an unrelated create_dr import in tests/test_mcp_kanban_newline_norm_1531.py against a server module that exposes create_request only.
- Challenger: reconsider, confidence 0.58. Accepted on nuance: the blocker is proof-surface contamination, not a newly observed #1900 implementation defect. Rejected on verdict: AC7 still requires 0 failures and 0 errors, and that contract is not met.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC7 | The authoritative proof command still does not complete with 0 failures and 0 errors. The latest retry reports 1 collection error outside the knowledge slice, so the executable proof required for PASS is still missing. | Task body Test-Writer Notes dated 2026-05-28T00:37:39+02:00; tests/test_mcp_kanban_newline_norm_1531.py:18 imports create_dr; serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:54-61 exports create_request and serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:423-454 defines create_request with no create_dr symbol | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Replace or refine AC7 so the required regression proof is path-scoped to the knowledge slice or otherwise insulated from unrelated collection-time failures, then redispatch after the exact command can achieve 0 failures and 0 errors. | .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md | Finding 1 |

## Observations
- AC1 and AC8 map in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:366-379: AppContext drops query_service, graph_store, ingest_pipeline, intra_doc_builder, and structured_extractor while retaining source_store and refresh_orchestrator.
- AC3 and AC5 map in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:421-467: app_lifespan uses sqlite3.connect(), ensure_tables(), QueryFacade, SqliteGraphStore, EnrichmentStore(graph=graph_store_v2), and IngestCoordinator(graph=graph_store_v2), with no legacy GraphStore or init_db wrapper.
- AC2 maps in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:567-592: knowledge_search uses query_facade only and contains no query_service branch or legacy serializer call.
- AC4 maps in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:814-870 plus direct symbol absence checks: knowledge_stats is tool-backed and no knowledge://stats resource helper remains.
- AC6 maps in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:20-60 and serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:1-188; no legacy graph_store/query_service/document_store/retrieval/schema.init_db helpers were found in the mcp-knowledge package, and _helpers.py no longer exposes the removed Edge/EntityType/RelationType extraction helpers.
- tests/test_mcp_knowledge_legacy_removal_1900.py remains a reasonably targeted task-local proof surface for deletion/rewiring checks: AC classes begin at lines 30, 107, 136, 178, 219, 247, 329, and 380.
- The task artifact still has a stale body Verification section at .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md:68-71 that advertises the broader root-level selector and the old search_knowledge spelling, while the authoritative AC7 and current code now use a narrower ignored-selector plan and the tool name knowledge_search. This did not change the verdict, but it is worth aligning on the next architect pass.

[[2026-05-28T00:56:24+02:00]]
## Architecture Review (Re-review #2)
### Context
Returned from review with AC7 still reporting 1 collection error. Root cause: tests/test_mcp_kanban_newline_norm_1531.py imports renamed symbol `create_dr` (now `create_request`) from owlbear_mcp_kanban.server — a pre-existing cross-domain issue unrelated to the knowledge cleanup.

### Actions Taken
1. Added `--ignore=tests/test_mcp_kanban_newline_norm_1531.py` to AC7 selector — the kanban test file's broken import is tracked by task #1862 (which asserts create_dr removal) and is outside knowledge domain scope.
2. Fixed AC2 naming: `search_knowledge` → `knowledge_search` to match live tool name in server.py:568.

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Key findings: (1) exact 6-ignore command not yet run in artifact, (2) kanban ignore lacks explicit follow-up task, (3) AC2 naming drift, (4) test_server.py #1908 scope question
- Architect response: (1) Mechanical deduction — prior run was 304/0/1 with only the kanban file erroring; adding its ignore yields 304/0/0; builder/test-writer will verify during normal pipeline flow. (2) Pre-existing cross-domain issue tracked by #1862; not #1900 scope. (3) Accepted and fixed. (4) Prior run showed test_server.py knowledge tests passing; #1908 handles proactive cleanup.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral (unchanged)
- Test-writer: PROCEED (verify refined AC7 command)

### Verdict: APPROVE
### Action Taken: Added kanban ignore to AC7, fixed AC2 naming, advanced to todo for builder re-verification of refined AC7 command.

[[2026-05-28T00:58:46+02:00]]
## Test-Writer Notes
- Retry 3: verified refined AC7 selector (architect added --ignore=tests/test_mcp_kanban_newline_norm_1531.py to eliminate pre-existing cross-domain collection error).
- AC7 result: 304 passed, 0 failed, 0 errors — clean pass.
- No new tests written. All 44 tests in tests/test_mcp_knowledge_legacy_removal_1900.py continue to pass.
- Reviewer's Required Follow-up was architect-only (refine AC7 proof surface); architect completed it (Architecture Review #2, 2026-05-28T00:56:24).
- Builder skip: test-only retry, all tests green against current impl.

[[2026-05-28T01:08:44+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1900 to docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: Builder notes report the task-local proof suite at tests/test_mcp_knowledge_legacy_removal_1900.py passed 44 tests with ruff clean, and the latest authoritative AC7 proof in .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md:315 reports 304 passed, 0 failed, 0 errors.
- AC1 and AC8 map to serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:367-379: AppContext no longer includes query_service, graph_store, ingest_pipeline, intra_doc_builder, or structured_extractor, and it still retains source_store plus refresh_orchestrator. Task-local proof anchors: tests/test_mcp_knowledge_legacy_removal_1900.py:30-99.
- AC2 maps to serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:568-592: knowledge_search uses query_facade only and contains no legacy query_service fallback path. Task-local proof anchors: tests/test_mcp_knowledge_legacy_removal_1900.py:107-127.
- AC3 and AC5 map to serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:422-459: app_lifespan uses sqlite3.connect(), QueryFacade, EnrichmentStore(graph=graph_store_v2), IngestCoordinator(graph=graph_store_v2), and ensure_tables() with no init_db wrapper. Task-local proof anchors: tests/test_mcp_knowledge_legacy_removal_1900.py:136-176 and tests/test_mcp_knowledge_legacy_removal_1900.py:219-246.
- AC4 maps to serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:815-846 and direct symbol absence in the server module: list_entities, _legacy_graph_stats, _knowledge_stats_bridge, knowledge_stats_resource, and the knowledge://stats resource registration are gone. Task-local proof anchors: tests/test_mcp_knowledge_legacy_removal_1900.py:178-218.
- AC6 maps to serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1-60 and serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:1-188: no legacy graph_store/query_service/ingest/document_store/retrieval/schema.init_db imports remain in the mcp-knowledge package, and _helpers.py no longer exposes the removed Edge/EntityType/RelationType helpers. Task-local proof anchors: tests/test_mcp_knowledge_legacy_removal_1900.py:247-379.
- AC7 is satisfied by the authoritative task-body proof surface: .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md:315 records 304 passed, 0 failed, 0 errors for the refined selector, and .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md:316 records that the 44 task-local tests still pass.
- Challenger result: proceed, confidence 0.82. No code-backed contradiction or proof-sufficiency defect was identified that would justify rejection.
- Blocking findings: none.

## Observations
- The task-local proof is mostly structural for the deletion and absence ACs. That is acceptable for this cleanup contract because the active ACs are removal and rewiring claims, and no adjacent runtime mismatch was found in the reviewed source.
- The task artifact still has stale Verification wording at .owlbear/kanban/tasks/1900-knowledge-remove-legacy-appcontext-fields-and-dual-paths-phase-b2.md:69-71, including the old search_knowledge spelling. Non-blocking, but worth aligning on a later doc or architect pass.

[[2026-05-28T01:12:02+02:00]]
## Docs Gate

### Checklist

**Item 1 — README Verification**
Target: `serve/mcp-knowledge/README.md`
- Layer 1 (structural): No removed symbols (`list_entities`, `knowledge://stats` resource, legacy functions) appear in the package README. Tool table is accurate. `knowledge_stats` described correctly as a tool.
- Layer 2 (editorial): Package description and tools table match the current v2-only server state. No task-caused contradictions.
- Result: No updates needed to `serve/mcp-knowledge/README.md`.

**Item 2 — External Attribution**
N/A — pure internal cleanup task (no external sources used).

**Item 3 — Research Doc**
Research docs referenced from task body:
- `.owlbear/research/mcp-knowledge-v2-migration.md` §3.1, §3.2 — linked
- `.owlbear/research/mcp-knowledge-legacy-removal-b2.md` — linked
Both linked in the task body `## Research` section. Verified.

**Item 4 — Deletion Detection**
Grep across `*.md` docs for removed symbols surfaced two task-caused issues:
1. `share/skills/h-knowledge-ops/SKILL.md` — referenced `knowledge://stats` MCP resource (removed by this task) in two places: under `knowledge_stats` description and in the decision-tree table.
   → **Fixed inline**: removed the Resource stanza and updated the decision-tree Notes cell.
2. `setup/setup-guide.md` — `KNOWLEDGE_TOOLS_EXCLUDE` example included `list_entities` which was never an MCP tool (task body: "deferred/unexposed") and is now fully deleted.
   → **Fixed inline**: removed `list_entities` from the example value; `knowledge_ingest` retained as the sole example tool to exclude.

### Files Updated
- `share/skills/h-knowledge-ops/SKILL.md` — removed 2× `knowledge://stats` resource references
- `setup/setup-guide.md` — removed `list_entities` from KNOWLEDGE_TOOLS_EXCLUDE example

### Scratch Cleanup
Removed: `1900-ac7-pytest.txt`, `1900-ac7-retry3.txt`, `1900-pytest-output.txt`, `1900-ruff-output.json`, `1900-ruff-output.txt` — clean.

[[2026-05-28T01:24:56+02:00]]
## Audit
### Regression Detection
- AC7 proof command: 304 passed, 0 failed, 0 errors (verified independently)
- Full suite minus known stale files (7 ignores + test_server.py): 4035 passed, 108 failed, 5 errors
- None of the 108 failures are attributable to #1900: test_server.py regressions tracked by #1908; other failures are pre-existing (test_register_source_1890 from #1895 rename, test_dead_code_sweep stale orchestrator refs, test_cockpit_view missing file, etc.)
- Lint: ruff clean on changed files
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (all changes within knowledge domain: server.py, _helpers.py; docs updates for removed symbols: h-knowledge-ops/SKILL.md, setup-guide.md)
- Purpose match: PASS (legacy AppContext fields removed, dual-paths eliminated, v2-only wiring confirmed)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
ACs specific, testable, and implementation-mapped cleanly. Minor gap: AC7 proof selector required two architect iterations to isolate from stale test contamination. Challenger accepted all four architect refinements.

### Commit Integrity
- Upstream commit presence: FAIL
  - Builder deliverables (server.py, _helpers.py) uncommitted; exist only in working tree
  - Doc-writer deliverables (h-knowledge-ops/SKILL.md, setup-guide.md) also uncommitted
  - No builder commit exists with #1900 attribution in git log
  - Process concern: builder and doc-writer failed to commit before advancing
- Kanban commit packaging: pending (this archival)

### Deduction Breakdown
- Evidence integrity concern (uncommitted source deliverables): -.05

### Confidence: .95
### Action: archive

### Process Note
Builder and doc-writer agents failed to commit their deliverables for this task. Implementation is functionally correct (tests pass, reviewer PASS verdict confirmed). Follow-up tasks #1905-#1908 track stale test cleanup.
