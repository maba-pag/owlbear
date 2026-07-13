---
id: 1907
title: 'P1-03: Update test_persistence_source_wiring.py to v2 ingest interface'
status: archived
priority: medium
created: 2026-05-28T00:34:20.741704+02:00
updated: 2026-05-28T04:09:22.064461+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - test_persistence_source_wiring.py no longer patches GraphStore, init_db, 
    KnowledgeQueryService, GraphAugmentedRetriever, or BgeM3EmbeddingProvider in
    owlbear_mcp_knowledge.server
  - test_persistence_source_wiring.py tests Qdrant persistence path and 
    source-identity wiring against v2 lifespan (SqliteSourceStore, 
    IngestCoordinator, QdrantVectorStore) OR is deleted with a supersession note
    citing specific test functions in existing v2 suites that cover the same 
    contracts (Qdrant location arg, source_id flow)
  - pytest tests/test_persistence_source_wiring.py passes (0 failures, 0 errors)
    — or file is absent if retired
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Update the durable module-level `tests/test_persistence_source_wiring.py` (~9 tests) to test against the v2 ingest interface, or retire if superseded.

## Current State
- Patches `GraphStore`, `init_db`, `KnowledgeQueryService`, `GraphAugmentedRetriever`, `BgeM3EmbeddingProvider` in `owlbear_mcp_knowledge.server`
- Tests AC1 (Qdrant filesystem persistence), AC4 (source_url parameter), AC6 (source identity by URL)
- Uses `pipeline.ingest_text()` calls which reference removed `IngestPipeline`

## Direction
- Evaluate whether the Qdrant persistence contract and source-identity wiring are now tested by v2-era suites (e.g., `test_ingest_document_coordinator_1893.py` or `serve/mcp-knowledge/tests/`)
- If covered: delete with supersession evidence note
- If not covered: rewrite fixtures to patch v2 lifespan symbols (`SqliteGraphStore`, `QdrantVectorStore`, `IngestCoordinator`) and test the same contracts against `knowledge_ingest` tool

## Scope
- In-scope: rewrite or retire `tests/test_persistence_source_wiring.py`
- Out-of-scope: other test files, server.py changes

[[2026-05-28T01:50:58+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file update/retire |
| Interface clarity | PASS | AC names concrete file, symbols, and verification method |
| Dependency correctness | PASS | #1900 (remove legacy AppContext) is archived |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | Tagged `test` — pass-through |
| KISS/YAGNI | PASS | Minimal scope: evaluate and act on one file |
| Premise challenge | PASS | File patches symbols that no longer exist in server.py |
| Pattern consistency | PASS | Follows cleanup task patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Codebase Evidence
- `server.py` app_lifespan now uses: QdrantVectorStore(location=qdrant_path), SqliteSourceStore, SqliteGraphStore, ContentStore, IngestCoordinator
- No GraphStore/init_db/KnowledgeQueryService/GraphAugmentedRetriever/BgeM3EmbeddingProvider remain
- `test_ingest_document_coordinator_1893.py` covers source_url forwarding, inline source resolution, IngestCoordinator wiring
- `test_mcp_knowledge_lifespan_1888.py` covers v2 store instantiation but NOT Qdrant location assertion
- Minor coverage gap: no v2 test asserts QdrantVectorStore location= argument value

### AC Refinement
- AC2 corrected: SqliteGraphStore → SqliteSourceStore (source identity flows through source_store_v2, not graph store)
- AC2 tightened: retire path now requires citing specific test functions as supersession evidence

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Findings: AC2 symbol inaccuracy (SqliteGraphStore), vague retire-path evidence, Qdrant path gap
- Architect response: accepted symbol fix and evidence tightening; proof bundle kept at smoke (test cleanup, not new production code)

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Test-writer: PROCEED (pass-through — tagged `test`)

### Verdict: APPROVE
### Action Taken: Refined AC2, advanced backlog → todo

[[2026-05-28T02:03:06+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Passing through to builder.

[[2026-05-28T02:41:37+02:00]]
## Builder Notes
- Files changed: tests/test_persistence_source_wiring.py
- Commit: cbb00af8
- Scope outcome: rewrote legacy durability test file to v2 interface coverage; removed all legacy symbol patching (GraphStore/init_db/KnowledgeQueryService/GraphAugmentedRetriever/BgeM3EmbeddingProvider).

- Implemented contracts:
  - Qdrant persistence path wiring verified through app_lifespan with QdrantVectorStore(location=...) default and OWLBEAR_QDRANT_PATH override assertions.
  - Source identity wiring verified through knowledge_ingest v2 path (source_store_v2 + ingest_coordinator): request.source_id comes from resolved inline source and from register_source fallback.

- Quality-runner evidence (scoped):
  - Tests: passed 4, failed 0, skipped 0
  - Lint: clean true (ruff exit 0)
  - Coverage: overall 36% (smoke/test-only cleanup task; no production source edited)
  - Commands executed via quality-runner on tests/test_persistence_source_wiring.py

- Fixes applied during build:
  - Replaced hardcoded /tmp path with pytest tmp_path fixture to satisfy S108 lint rule.

- AC mapping summary:
  - AC1 satisfied: test file no longer patches legacy removed symbols.
  - AC2 satisfied (rewrite path): file now asserts v2 Qdrant path wiring and source_id flow via v2 ingest wiring.
  - AC3 satisfied: pytest tests/test_persistence_source_wiring.py passes with zero failures/errors.

[[2026-05-28T02:55:07+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | The rewritten source-identity tests do not exercise v2 lifespan wiring. They inject `source_store_v2` and `ingest_coordinator` mocks directly into a `SimpleNamespace` context instead of proving the contract through `app_lifespan` / real v2 lifespan components required by the AC. | AC2 requires source-identity wiring against v2 lifespan in `.owlbear/kanban/tasks/1907-p1-03-update-test-persistence-source-wiring-py-to-v2-ingest-interface.md:20`; rewrite direction says to patch v2 lifespan symbols in `.owlbear/kanban/tasks/1907-p1-03-update-test-persistence-source-wiring-py-to-v2-ingest-interface.md:44`. Current file uses `app_lifespan` only for Qdrant path assertions at `tests/test_persistence_source_wiring.py:31-32` and `tests/test_persistence_source_wiring.py:51-52`, but the source-id cases bypass lifespan via mock-only context wiring at `tests/test_persistence_source_wiring.py:74-75` and `tests/test_persistence_source_wiring.py:106-107` before asserting `request.source_id` at `tests/test_persistence_source_wiring.py:88` and `tests/test_persistence_source_wiring.py:120`. Stronger adjacent runtime proof already exists in `tests/test_ingest_document_coordinator_1893.py:698` and `tests/test_ingest_document_coordinator_1893.py:733`, with source-id flow assertions in `tests/test_ingest_document_coordinator_1893.py:373` and `tests/test_ingest_document_coordinator_1893.py:389`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen `tests/test_persistence_source_wiring.py` so the source-identity coverage runs through `app_lifespan` with real v2 lifespan components, or retire the file with a supersession note citing the existing v2 tests that already cover source-id flow and real-store lifecycle wiring. | `tests/test_persistence_source_wiring.py`, `tests/test_ingest_document_coordinator_1893.py`, `.owlbear/kanban/tasks/1907-p1-03-update-test-persistence-source-wiring-py-to-v2-ingest-interface.md` | AC2 at task line 20, rewrite direction at task line 44, and mock-only context wiring at `tests/test_persistence_source_wiring.py:74-75` and `tests/test_persistence_source_wiring.py:106-107` |

## Observations
- AC1 appears satisfied: the rewritten file no longer patches the removed legacy server symbols; the only patching present is `QdrantVectorStore` for the path assertions (`tests/test_persistence_source_wiring.py:31-32`, `tests/test_persistence_source_wiring.py:51-52`).
- AC3 evidence is sufficient for this review cycle: the builder supplied scoped pass/lint evidence, and `get_errors` reports no syntax/type diagnostics for `tests/test_persistence_source_wiring.py`.
- I did not dispatch `quality-runner`; the blocking issue is proof scope against AC2, not missing execution evidence.

[[2026-05-28T03:17:11+02:00]]
## Test-Writer Notes
- Retry: rewrote `TestKnowledgeIngestSourceIdentityWiring` (2 tests) to exercise `app_lifespan` with real `SqliteSourceStore` instead of `SimpleNamespace` context injection.
- Pattern follows `TestFromAC_IngestDocumentLifespanProof` in `tests/test_ingest_document_coordinator_1893.py` — only `QdrantVectorStore` is patched, SQLite runs in-memory.
- `test_ingest_source_id_comes_from_existing_inline_source`: pre-registers source via real store, asserts `request.source_id == pre_registered.id`.
- `test_ingest_source_id_comes_from_newly_registered_inline_source`: no pre-registration, asserts `request.source_id == inline[0].id` from real store after ingest.
- `TestQdrantPersistencePathWiring` (2 tests): unchanged — already used `app_lifespan`.
- Quality-runner: 4 passed, 0 failed, ruff clean.
- Commit: 8b789f5b
- Builder skip: test-only retry, all 4 tests green against current impl.

[[2026-05-28T03:38:41+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1907 to docs | AC mapped to code and evidence sufficient.
- Builder and test-writer evidence reviewed first: the retry note reports quality-runner 4 passed, 0 failed, ruff clean at .owlbear/kanban/tasks/1907-p1-03-update-test-persistence-source-wiring-py-to-v2-ingest-interface.md:145, with builder skip recorded at .owlbear/kanban/tasks/1907-p1-03-update-test-persistence-source-wiring-py-to-v2-ingest-interface.md:147.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | tests/test_persistence_source_wiring.py:19 imports only `_DEFAULT_QDRANT_PATH`, `app_lifespan`, and `knowledge_ingest`; the only remaining patch sites are QdrantVectorStore at tests/test_persistence_source_wiring.py:37, tests/test_persistence_source_wiring.py:57, tests/test_persistence_source_wiring.py:78, and tests/test_persistence_source_wiring.py:126. No GraphStore, init_db, KnowledgeQueryService, GraphAugmentedRetriever, or BgeM3EmbeddingProvider references remain in the file. | Direct file inspection of tests/test_persistence_source_wiring.py. | PASS |
| AC2 | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:428 wires QdrantVectorStore(location=qdrant_path), serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:429 wires SqliteSourceStore(conn), and serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:439 wires IngestCoordinator(...). knowledge_ingest resolves or registers the inline source at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:765-777, builds IngestRequest with source_id=source.id at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:790-791, and calls coordinator.ingest at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:802. | tests/test_persistence_source_wiring.py:41 and tests/test_persistence_source_wiring.py:61 assert the exact QdrantVectorStore location argument. tests/test_persistence_source_wiring.py:79-80 and tests/test_persistence_source_wiring.py:127-128 run through app_lifespan and confirm a real SqliteSourceStore. tests/test_persistence_source_wiring.py:82 pre-registers the existing source, tests/test_persistence_source_wiring.py:142 reads real-store sources after ingest, tests/test_persistence_source_wiring.py:147 enforces single inline-source creation on the create branch, and tests/test_persistence_source_wiring.py:111 plus tests/test_persistence_source_wiring.py:155 assert exact request.source_id propagation. | PASS |
| AC3 | Current retry evidence in the task body at .owlbear/kanban/tasks/1907-p1-03-update-test-persistence-source-wiring-py-to-v2-ingest-interface.md:145-147 records 4 passed, 0 failed, ruff clean for tests/test_persistence_source_wiring.py. | get_errors reports no diagnostics for tests/test_persistence_source_wiring.py. | PASS |
- Blocking findings: none.

## Observations
- Adjacent v2 coverage in tests/test_ingest_document_coordinator_1893.py:373-403 and tests/test_ingest_document_coordinator_1893.py:698-758 is consistent with the task-scoped suite and strengthens confidence in the same source-id and lifespan contracts.
- I did not dispatch quality-runner because the supplied retry evidence was sufficient and internally consistent for a smoke-bundle review.
- Non-blocking: the existing-source branch in tests/test_persistence_source_wiring.py does not itself assert post-call source cardinality, but duplicate-suppression is already proved by tests/test_ingest_document_coordinator_1893.py:733-758, so this is not a blocker for task 1907.

[[2026-05-28T03:57:56+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | `tests/test_persistence_source_wiring.py` is in workspace-root `tests/`; no `serve/{pkg}` convention mapping applies; no public interface changed |
| 2. External Attribution | N/A — no external attribution needed | Test rewrite against existing v2 lifespan interface; no external sources cited |
| 3. Research Doc | N/A — no research doc linkage needed | No `.owlbear/research/` artifact for this task |
| 4. Deletion Detection | N/A — no deletion impact | File rewritten in-place; no orphaned references |

### Files Updated
None — no docs impact.

### Scratch Cleanup
No `.owlbear/scratch/1907-*` files found.

[[2026-05-28T04:09:22+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 304 passed, 0 failed. Pytest exit code 1 due to pre-existing collection error in `tests/test_mcp_kanban_newline_norm_1531.py` (ImportError: `create_dr` — last touched by task #1531, unrelated). Lint violations in `serve/knowledge/src/owlbear_knowledge/protocols/query.py` and `refresh.py` are pre-existing (files not changed by this task). No regressions attributable to #1907.

### Intent Verification
Changed file: `tests/test_persistence_source_wiring.py` — stays within knowledge domain test scope. Implementation rewrites legacy test fixtures to v2 interface as stated in task purpose. No extraneous files or scope.

### Architect Quality
AC quality score: 4/5. AC lines are specific (names exact symbols for AC1, exact v2 components and alternatives for AC2, concrete pass gate for AC3). Architect accepted challenger feedback and corrected symbol inaccuracy (SqliteGraphStore → SqliteSourceStore). Proof bundle appropriately set to `smoke` for test cleanup. Minor gap: AC2 rewrite direction could have specified real-store vs mock boundary more explicitly, but builder/reviewer resolved without ambiguity.

### Commit Integrity
- `cbb00af8` — test: rewrite persistence source wiring for v2 ingest (#1907, builder)
- `8b789f5b` — test: strengthen source-identity tests through app_lifespan (#1907, test-writer)
Both commits present and properly attributed.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| Regression failures | 0 (none attributable) |
| Intent mismatch | 0 |
| Evidence integrity | 0 |
| Lint violations | 0 (pre-existing, not in changed files) |
| AC quality ≤ 3 | 0 (score=4) |
| Missing reviewer evidence | 0 (detailed PASS with AC map) |

### Confidence: 1.00
### Action: Archive
