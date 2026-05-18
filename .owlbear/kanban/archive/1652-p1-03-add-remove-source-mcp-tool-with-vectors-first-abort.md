---
id: 1652
title: 'P1-03: Add remove_source MCP tool with vectors-first abort'
status: archived
priority: needed
created: 2026-05-18T03:11:06.889695+02:00
updated: 2026-05-18T14:36:24.296799+02:00
tags:
  - scope:mcp-knowledge
  - mcp-tools
parent: 1650
depends_on: []
ac:
  - 'AC-1: `AppContext` has a `vector_store` field typed `QdrantVectorStore | None`;
    `app_lifespan` wires the existing `QdrantVectorStore` instance (`vs`) into it'
  - "AC-2: `remove_source(source_id: str)` MCP tool registered with `destructiveHint=True`:
    given a source_id present in `knowledge_sources`, collects chunk IDs via SQL join
    (`chunks.document_id` → `documents.source_id`), deletes each chunk's vector via
    `QdrantVectorStore.delete_embedding`, then calls `source_store.delete_cascade(source_id)`;
    returns a dict with counts of deleted documents, chunks, and entities"
  - 'AC-3: Given a `QdrantVectorStore.delete_embedding` call that raises an exception
    for any chunk ID, `remove_source` raises `ToolError` without calling `delete_cascade`;
    SQLite data remains intact — `delete_embedding` returning `False` (missing vector)
    is not an abort condition'
  - 'AC-4: `remove_source` calls `logger.info` (containing source_id, source name,
    and counts of documents, chunks, and entities about to be deleted) strictly before
    calling `delete_cascade`; test proof must include a call-order assertion that
    fails if logging is reordered after cascade deletion (e.g. via side-effect call
    sequence tracking)'
  - 'AC-5: Given a source_id not present in `knowledge_sources`, `remove_source` raises
    `ToolError`; no vector deletions or SQL changes occur'
proof_bundle: behavioral
blocked: false
block_reason: 'builder crashed twice: pre-existing uncommitted changes in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
  prevent safe commit isolation'
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Extend `AppContext` with `vector_store` field; wire new `remove_source` MCP tool; implement vectors-first abort semantics.

**Out-of-scope:** Dry-run mode (excluded per brief D6). Refresh logic (O2). Health exposure (O1). Config field exposure.

## Context

Execution order per brief:
1. Collect chunk IDs from source's documents (SQL: chunks.document_id → documents.source_id)
2. Delete vectors from Qdrant for those chunk IDs (`QdrantVectorStore.delete_embedding`)
3. If any vector deletion fails → abort, return `ToolError`, source stays intact
4. Run `source_store.delete_cascade` (SQLite transaction)
5. Return deletion counts

`AppContext` currently has `source_store` and `conn` but no `vector_store`. Lifespan builds `vs = QdrantVectorStore(location=qdrant_path)` — wire it into `AppContext`.

`document_store.delete_chunk_embeddings` uses best-effort (catches exceptions). This tool needs strict abort — implement strict deletion loop directly in the tool handler.

[[2026-05-18T03:19:32+02:00]]
## Research
- Research doc: .owlbear/research/1652-remove-source-mcp-tool.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: proceed as specified in brief (confidence: 0.92)
- Key findings: AppContext needs `vector_store` field; SQL join for chunk IDs; strict abort via try/except on `delete_embedding`; count queries before cascade

[[2026-05-18T03:19:49+02:00]]
## Research
- Research doc: .owlbear/research/1652-remove-source-mcp-tool.md
- Sources: 6 studied (4 codebase, 1 external SDK, 1 schema), 4 high-relevance
- Recommendation: proceed as specified in brief (confidence: 0.92)
- Key findings:
  - AppContext needs `vector_store: QdrantVectorStore | None = None` field; lifespan wires existing `vs`
  - SQL join `chunks c JOIN documents d ON c.document_id = d.id WHERE d.source_id = ?` for chunk IDs
  - Strict abort via try/except on `delete_embedding` (NOT best-effort like `delete_chunk_embeddings`)
  - Count queries (docs, chunks, entities) must run BEFORE `delete_cascade`
  - `delete_embedding` returns False for missing vectors (ok), raises on Qdrant errors (abort trigger)
- Challenge: skipped — implementation follows pre-approved brief with no design alternatives
- Follow-up tasks: none needed — #1652 is the implementation task
- Attribution: MCP Python SDK added to sources/overview.md

[[2026-05-18T03:39:32+02:00]]
## Architecture Review

**Verdict:** APPROVED (after AC refinement)
**Proof bundle:** behavioral (confirmed — contained new tool + one DI field, consolidation test #1655 gates integration)

### AC Assessment

| AC | Assessment | Action |
|-----|-----------|--------|
| AC-1 | Clean. Single structural change: field + wiring. `app_lifespan` at server.py L1296 builds `vs` but doesn't pass it to AppContext — AC addresses this gap. | No change |
| AC-2 | Refined. Removed B3-banned word \"valid\"; replaced with \"present in knowledge_sources\". Clarified SQL join path and return type (dict). | Rewritten |
| AC-3 | Refined. Clarified False vs exception semantics: `delete_embedding` returning False (missing vector) is not abort; only raised exceptions trigger abort + ToolError. | Rewritten |
| AC-4 | Clean. `remove_source` named as explicit subject. Removed \"timestamp\" (logger provides this automatically). | Minor edit |
| AC-5 | Added. Nonexistent source_id → ToolError. Follows `refresh_source` pattern at server.py L1547 (`store.get()` → None → ToolError). | New |

### Architecture Notes

- **Module layering:** MCP server layer → knowledge domain layer. Correct direction.
- **AppContext field:** Direct `vector_store` field preferred over reaching through `query_service.vector_store` (Law of Demeter). Existing AppContext pattern exposes services directly.
- **Vectors-first design:** Brief D8 decision. Tradeoff: missing vectors + surviving SQLite (recoverable via re-ingest) preferred over orphaned vectors (unrecoverable). Post-vector SQL failure is low risk — `delete_cascade` is a single SQLite transaction.
- **Strict abort vs best-effort:** `delete_chunk_embeddings` in document_store.py L278 is best-effort (catches all exceptions). This tool's AC-3 explicitly requires strict abort — different pattern, justified by destructive semantics.
- **`__all__` export:** Builder should add `remove_source` to `__all__` at server.py L1339 following existing pattern.

### Dependency Analysis

- No upstream dependencies (parallel with O2/O1).
- Downstream: consolidation test #1655 depends on this task.
- Sibling tasks verified under parent #1650.

### Challenger Results

Challenger recommended `block` (confidence 0.41). Override rationale:
1. Post-vector SQL failure: Design intent per brief D8, not an AC gap.
2. AC quality: Addressed — AC-2 rewritten (B3 fix), AC-3 clarified, AC-5 added.
3. Proof bundle: `behavioral` appropriate — contained new feature, #1655 consolidation test exists.
4. AppContext necessity: LoD justifies direct field over reaching through query_service.
5. Audit scope: docs/chunks/entities are primary data objects; edges/source_pages are derived artifacts.

[[2026-05-18T03:53:37+02:00]]
## Test-Writer Notes
- Test file: `tests/test_server_1652.py`
- Classes: `TestFromAC_AppContextVectorStore`, `TestFromAC_RemoveSourceTool`, `TestFromAC_VectorsFirstAbort`, `TestFromAC_AuditLog`, `TestFromAC_SourceNotFound`
- Tests per category:
  - Happy path: 5 (lifespan wiring, returns dict, delete_embedding called per chunk, cascade called, correct counts)
  - Edge/boundary: 3 (False not abort, second chunk fails, empty chunk list tolerance)
  - Error paths: 6 (exception → ToolError, no cascade on failure, source not found → ToolError ×3, no SQL mutation)
  - Structural: 4 (vector_store field exists, accepts None, destructiveHint=True, __all__ export)
  - Audit log: 6 (info called, contains source_id, name, doc count, chunk count, entity count)
- Total: 24 tests — all FAIL (ImportError: cannot import name 'remove_source' from 'owlbear_mcp_knowledge.server')
- Lint: clean (ruff 0)
- Commit: 540783e9

## AC Coverage
| AC | Tests |
|----|-------|
| AC-1 (AppContext.vector_store + lifespan wiring) | test_app_context_has_vector_store_field, test_app_context_vector_store_accepts_none, test_app_lifespan_wires_vector_store_to_app_context |
| AC-2 (tool registered destructiveHint=True, happy path) | test_remove_source_registered_with_destructive_hint, test_remove_source_returns_dict_with_expected_keys, test_remove_source_dict_values_are_integers, test_remove_source_calls_delete_embedding_for_each_chunk, test_remove_source_calls_delete_cascade_with_source_id, test_remove_source_returns_correct_counts |
| AC-3 (exception → ToolError, no cascade; False → continue) | test_remove_source_raises_tool_error_on_delete_embedding_exception, test_remove_source_does_not_call_delete_cascade_when_vector_deletion_fails, test_remove_source_false_from_delete_embedding_is_not_abort, test_remove_source_aborts_on_second_chunk_failure, test_remove_source_sqlite_intact_after_vector_failure |
| AC-4 (logger.info audit with source_id, name, counts) | test_remove_source_calls_logger_info_before_delete_cascade, test_remove_source_log_contains_source_id, test_remove_source_log_contains_source_name, test_remove_source_log_contains_doc_count, test_remove_source_log_contains_chunk_count, test_remove_source_log_contains_entity_count |
| AC-5 (source not found → ToolError, no mutations) | test_remove_source_raises_tool_error_when_source_not_found, test_remove_source_no_delete_embedding_when_source_not_found, test_remove_source_no_delete_cascade_when_source_not_found, test_remove_source_no_sql_mutation_when_source_not_found, test_remove_source_in_all_export |

[[2026-05-18T04:08:17+02:00]]
builder crashed once: stopped due to pre-existing uncommitted changes in server.py; releasing claim before retry

[[2026-05-18T04:12:03+02:00]]
builder crashed twice: pre-existing uncommitted changes in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py prevent safe commit isolation. Tests pass (25/25) but implementation cannot be committed without resolving working tree conflicts. User action needed: clean/split unrelated edits from server.py first.

[[2026-05-18T12:40:56+02:00]]
## Builder Notes
- Implementation: no additional source edits were required in this builder run; required behavior is present in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (`AppContext.vector_store`, lifespan wiring, `remove_source` registration/handler, `__all__` export).
- Tests: task-scoped proof passed via quality-runner (`tests/test_server_1652.py`): 26 passed, 0 failed.
- Module regression signal: durable server test file passed via quality-runner (`serve/mcp-knowledge/tests/test_server.py`): 10 passed, 0 failed.
- Coverage: quality-runner reported `owlbear_mcp_knowledge.server` at 35% in scoped run; implementation area for AC-1..AC-5 is exercised by the task-scoped suite.
- ruff: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_server_1652.py`.
- Approach: verified existing in-branch implementation against AC and test-writer contract, then validated with canonical quality-runner gates before advancing.

[[2026-05-18T12:59:07+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: `tests/test_server_1652.py` passed 26/26, `serve/mcp-knowledge/tests/test_server.py` passed 10/10, ruff clean, scoped coverage reported 35% for `owlbear_mcp_knowledge.server`.
- Independent verification was required because AC-1 changes a shared constructor surface and the builder proof did not cover the adjacent `AppContext` consumer in `serve/mcp-knowledge/tests/test_direct_ingest_delta.py`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | `AppContext` now requires `vector_store` at construction time, which regresses an existing mcp-knowledge consumer that still instantiates `AppContext` without that argument. The adjacent direct-ingest suite fails during fixture setup. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1231-1238`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1315-1325`, `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:40-47`, quality-runner on `serve/mcp-knowledge/tests/test_direct_ingest_delta.py`: 13 errors with `TypeError: AppContext.__init__() missing 1 required positional argument: 'vector_store'` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Preserve omitted-argument `AppContext` construction for existing mcp-knowledge callers, then rerun the adjacent direct-ingest suite together with the task proof before returning to review. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `serve/mcp-knowledge/tests/test_direct_ingest_delta.py` | Blocking finding #1; quality-runner fixture setup failure |

## Observations
- AC-2 through AC-5 map cleanly to the `remove_source` implementation in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1588-1672`, and the task suite in `tests/test_server_1652.py` covers the vectors-first abort, audit logging, and source-not-found paths.
- The AC-1 task tests prove explicit `vector_store=None` and lifespan wiring, but they do not protect the omitted-argument `AppContext` path that the adjacent direct-ingest suite still uses.
- No additional blocking issues were found in the `remove_source` handler from direct file review.

[[2026-05-18T13:07:11+02:00]]
## Builder Notes
- Implementation: updated AppContext constructor compatibility in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py by making `vector_store` optional with default `None` (while keeping lifespan wiring of the live `vs` instance).
- Regression fix: preserves omitted-argument AppContext call sites used by adjacent mcp-knowledge tests (notably direct-ingest fixture construction), resolving reviewer-reported TypeError.
- Commit: f30613c0
- Tests (quality-runner, scoped):
  - tests/test_server_1652.py: pass
  - serve/mcp-knowledge/tests/test_direct_ingest_delta.py: pass
  - serve/mcp-knowledge/tests/test_server.py: pass
  - Aggregate: 49 passed, 0 failed, 0 skipped
- Coverage (quality-runner, scoped): `owlbear_mcp_knowledge.server` 40% (overall scoped run 43%).
- Ruff: clean (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, task and adjacent test paths).
- Approach: minimal constructor-surface compatibility patch only; no changes to remove_source behavior or test files.

[[2026-05-18T13:18:00+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: task-scoped proof passed (`tests/test_server_1652.py` 26/26), adjacent direct-ingest proof passed (`serve/mcp-knowledge/tests/test_direct_ingest_delta.py`), durable server proof passed (`serve/mcp-knowledge/tests/test_server.py`), ruff clean, scoped coverage reported `owlbear_mcp_knowledge.server` at 40%.
- Current implementation satisfies the repaired constructor surface and the AC-4 ordering in direct code review: `AppContext` defaults `vector_store` to `None` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1239`, `app_lifespan` still injects the live `vs` instance at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1315`, and `remove_source` currently logs before cascading at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1659-1667`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | Test proof is insufficient for the required `logger.info`-before-`delete_cascade` ordering. The named ordering test only asserts that `logger.info` was called; it never compares that side effect against the cascade call, so the suite would false-green if the audit log moved after the destructive delete. Because this is the second review cycle on the task, route to backlog per reviewer loop-break policy. | `tests/test_server_1652.py:346-353` (`mock_logger.info.assert_called()` only), `tests/test_server_1652.py:238` (`store.delete_cascade.assert_called_once_with("src-1")` checked separately), `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1659-1667` (current code order is correct today but not regression-proof) | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC-4 proof so the task explicitly requires an ordering assertion that fails if `logger.info` is moved after `delete_cascade`, then re-dispatch through test coverage before the next review cycle. | `tests/test_server_1652.py` | Blocking finding #1; `tests/test_server_1652.py:238`, `tests/test_server_1652.py:346-353`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1659-1667` |

## Observations
- AC-1 constructor compatibility appears resolved: omitted-argument `AppContext` construction is preserved by the defaulted `vector_store` field in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1239`, which matches adjacent call sites in `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:40`, `tests/test_knowledge_ingest_source_identity_1556.py:136`, and `tests/test_enrichment_persistence_1557.py:45`.
- AC-2, AC-3, and AC-5 have adequate task-local behavioral proof in `tests/test_server_1652.py`, and direct file review did not uncover additional implementation defects in `remove_source`.
- Challenger cross-check: `proceed` with confidence 0.86; it agreed the missing ordering assertion is a true blocking proof gap under reviewer standards even though the current source order is correct today.

[[2026-05-18T13:33:35+02:00]]
## Architecture Review (Re-review cycle)

**Context:** Reviewer loop-break returned task to backlog with a single blocking finding: AC-4 ordering test proof insufficient (assert_called without call-order verification).

### AC-4 Refinement

Original: \"Before calling `delete_cascade`, `remove_source` logs an audit entry via `logger.info` containing source_id, source name, and the counts of documents, chunks, and entities about to be deleted\"

Refined: \"`remove_source` calls `logger.info` (containing source_id, source name, and counts of documents, chunks, and entities about to be deleted) strictly before calling `delete_cascade`; test proof must include a call-order assertion that fails if logging is reordered after cascade deletion (e.g. via side-effect call sequence tracking)\"

Rationale: The word \"Before\" was already present but the test-writer interpreted it as a documentation hint rather than a regression-testable constraint. The refined wording makes the ordering proof requirement unmistakable.

### Architecture Assessment

No architectural changes since prior approval. Implementation committed (f30613c0), all suites passing (task-scoped 26/26, direct-ingest 13/13, durable server 10/10). Only gap is the ordering proof quality.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral (confirmed — no change)
- Test-writer: PROCEED (must add ordering assertion to existing test file)

### Challenge Results
- Challenger: block (confidence 0.31)
- Architect response: OVERRIDE — challenger confused pipeline flow with current state. The task goes to `todo` where test-writer will write the ordering assertion per refined AC-4. Count fidelity and partial vector mutation are design decisions (Brief D8), not gaps.

### Verdict: APPROVE (REFINE AC-4, re-dispatch)
### Action Taken: Refined AC-4 to require explicit call-order assertion proof; re-approved to todo for test-writer to strengthen ordering test.

[[2026-05-18T13:48:24+02:00]]
## Test-Writer Notes
- Retry: added 1 ordering-assertion test for reviewer gap (AC-4 call-order proof).
- Test file: `tests/test_server_1652.py`
- New test: `TestFromAC_AuditLog::test_remove_source_logger_info_strictly_before_delete_cascade`
- Technique: side-effect call-sequence tracking (appends `"logger.info"` / `"delete_cascade"` to `call_order` list); asserts `index("logger.info") < index("delete_cascade")`. Fails if logging is reordered after cascade.
- All 27 tests PASS against current implementation (Step 1b.1: test-proof gap, implementation already correct).
- Lint: ruff clean.
- Commit: 7adebfb0
- Builder skip: test-only retry, all tests green.

## AC Coverage
| AC | Tests |
|----|-------|
| AC-4 (ordering: logger.info before delete_cascade) | `test_remove_source_calls_logger_info_before_delete_cascade` (existing — calls-only assert), `test_remove_source_logger_info_strictly_before_delete_cascade` (new — call-order regression guard) |

[[2026-05-18T14:13:22+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1652 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: prior builder quality-runner proof covered `tests/test_server_1652.py`, `serve/mcp-knowledge/tests/test_direct_ingest_delta.py`, and `serve/mcp-knowledge/tests/test_server.py` with aggregate 49 passed / 0 failed / 0 skipped, ruff clean, and scoped coverage `owlbear_mcp_knowledge.server` 40%. The current retry was test-only (`7adebfb0`) and added the AC-4 ordering regression guard with 27/27 passing and ruff clean; because implementation was unchanged, no independent rerun was required.
- No blocking findings after AC->code mapping, test->AC alignment, proof sufficiency, and safety/security review.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1231-1239` defines `AppContext.vector_store` as optional; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1315-1323` wires `vector_store=vs` in `app_lifespan` | `tests/test_server_1652.py:120`, `tests/test_server_1652.py:124`, `tests/test_server_1652.py:139`; adjacent omitted-argument callers remain valid at `serve/mcp-knowledge/tests/test_direct_ingest_delta.py:40`, `tests/test_knowledge_ingest_source_identity_1556.py:136`, `tests/test_enrichment_persistence_1557.py:45` | PASS |
| AC-2 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1588-1667` registers `remove_source` as destructive, gathers source-scoped IDs, deletes embeddings, cascades source deletion, and returns counts | `tests/test_server_1652.py:165`, `tests/test_server_1652.py:197`, `tests/test_server_1652.py:214`, `tests/test_server_1652.py:230`, `tests/test_server_1652.py:241` | PASS |
| AC-3 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1648-1657` aborts on vector deletion exceptions and skips cascade on failure | `tests/test_server_1652.py:264`, `tests/test_server_1652.py:275`, `tests/test_server_1652.py:289`, `tests/test_server_1652.py:303`, `tests/test_server_1652.py:321` | PASS |
| AC-4 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1659-1667` emits one audit log call before `delete_cascade` with source id, source name, and counts | `tests/test_server_1652.py:356`, `tests/test_server_1652.py:368`, `tests/test_server_1652.py:380`, `tests/test_server_1652.py:393`, `tests/test_server_1652.py:406`, `tests/test_server_1652.py:419` | PASS |
| AC-5 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1595-1600` raises `ToolError` for a missing source before vector deletion or SQL mutation work begins | `tests/test_server_1652.py:464`, `tests/test_server_1652.py:472`, `tests/test_server_1652.py:483`, `tests/test_server_1652.py:494` | PASS |

## Observations
- Safety/security check: `source_id` only flows into parameterized SQLite queries inside `remove_source` and no shell/path/template sink was introduced in this change surface.
- Challenger cross-check returned `reconsider` (0.46 confidence) on a hypothetical future split-log false-green, but that concern does not rise to a blocker here: AC-4's explicit strengthened proof requirement was call-order tracking, which is now implemented at `tests/test_server_1652.py:419`, and current code still uses a single pre-cascade audit call at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1659`.
- Residual non-blocking hardening opportunity: the AC-4 payload tests aggregate `mock_logger.info.call_args_list`; an exact single-call payload matcher would make future refactors harder to false-green, but the current code + proof packet are sufficient for PASS.

[[2026-05-18T14:15:39+02:00]]
## Docs Gate

**Verdict:** PASS

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1 — README Verification | FIXED | `serve/mcp-knowledge/README.md` Tools table was missing `remove_source`; added row with vectors-first abort description. Layer 1: grep confirms match at line 27. Layer 2: full-file editorial read — coherent, no contradictions, logical placement after `refresh_source`. Commit: c07f22ce |
| 2 — External Attribution | N/A (already done) | `sources/overview.md` line 9 contains MCP Python SDK entry with #1652 research doc reference — added by researcher during prior cycle |
| 3 — Research Doc | N/A | `.owlbear/research/1652-remove-source-mcp-tool.md` exists; linked from task body |
| 4 — Deletion Detection | N/A | No source files deleted; changed files: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (modified), `tests/test_server_1652.py` (new). No orphaned references. |

### Files Updated
- `serve/mcp-knowledge/README.md` — added `remove_source` row to Tools table

### Scratch Cleanup
- None created for #1652

[[2026-05-18T14:36:24+02:00]]
## Audit

### Regression Detection
Quality-runner full-suite: 4801 passed. Domain-scoped run (`tests/test_server_1652.py` + `serve/mcp-knowledge/tests/`): 186 passed, lint clean. 17 failures in `test_ingest_graph_tools.py` (10), `test_stats_resource.py` (6), `test_list_sources.py` (1) — all pre-existing background debt from commits `f208138c` and `f06a3339` (#1654), confirmed via `git log` attribution. No regressions caused by #1652.

### Intent Verification
Changed files: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (implementation), `tests/test_server_1652.py` (tests), `serve/mcp-knowledge/README.md` (docs). All within `scope:mcp-knowledge` domain, matching task purpose "Add remove_source MCP tool with vectors-first abort." No extraneous scope.

### Architect Quality
Score: 4/5. AC-1 through AC-5 are specific and testable. One refinement cycle needed: AC-4 initially used implicit "Before" which the test-writer under-proved; architect proactively refined to require explicit call-order assertion. Final AC set is clean and complete. Minor gap filled by reviewer feedback — standard iteration, not architect failure.

### Commit Integrity
4 pipeline commits properly attributed:
- `540783e9` test: initial RED (#1652, test-writer)
- `f30613c0` fix: AppContext compatibility (#1652, builder)
- `7adebfb0` test: ordering assertion (#1652, test-writer)
- `c07f22ce` docs: README update (#1652, doc-writer)

Process observation: primary `remove_source` implementation lives in bulk commit `c7207603` (unattributed) due to documented block scenario — builder crashed on pre-existing uncommitted changes, user resolved by committing alongside unrelated enrichment changes. Implementation verified against AC by builder and reviewer post-commit. Not a deduction — situation documented in block_reason and all verification was performed against committed code.

### Deduction Breakdown
- Regression failures: 0 (none task-caused)
- Intent mismatch: 0
- Lint violations: 0
- AC quality ≤3: 0 (scored 4)
- Missing reviewer evidence: 0 (detailed PASS with full AC→code mapping)
- Evidence integrity: 0

**Confidence: 1.00 — Archive**
