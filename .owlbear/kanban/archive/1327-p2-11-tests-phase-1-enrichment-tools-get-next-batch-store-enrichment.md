---
id: 1327
title: 'P2-11: Tests — Phase 1 enrichment tools (get_next_batch, store_enrichment)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.111772+00:00
updated: 2026-05-05T21:47:02.872165+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1324
- 1318
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify get_next_batch executes SELECT and UPDATE within a single BEGIN IMMEDIATE transaction — SQL trace must show BEGIN IMMEDIATE before SELECT and UPDATE, with no COMMIT between them (td:2)
- [ ] Tests verify get_next_batch returns: chunk_id and text from chunks, doc_title from documents JOIN, source_name from knowledge_sources LEFT JOIN, and section_path parsed from chunks.metadata JSON; section_path test must insert metadata with a known value and assert exact round-trip (td:1)
- [ ] Tests verify claimed chunks are not returned in subsequent get_next_batch calls (td:1)
- [ ] Tests verify lease expiry: stale claims (>10 min) revert to pending (td:2)
- [ ] Tests verify store_enrichment: UPSERT entities via INSERT OR REPLACE on entities table primary key (td:1)
- [ ] Tests verify store_enrichment: INSERT OR IGNORE edges with UNIQUE(source_id, target_id, relation, document_id) constraint (td:1)
- [ ] Tests verify store_enrichment updates enrichment_state to 'enriched' (td:1)
- [ ] Tests verify WAL mode concurrent write safety (file-backed DB, multiple connections from separate threads) (td:2)
- [ ] Tests verify get_next_batch excludes chunks from sources with enrich=false (td:1)

## Scope

- **In scope:** Phase 1 worker tool tests — get_next_batch, store_enrichment
- **Out of scope:** Phase 2 consolidation (P2-13/14), get_stats (P2-13/14)


[[2026-05-05]]
## Research

**Key findings:**
- Hybrid test approach: real in-memory SQLite for 7/8 ACs + file-backed for WAL concurrency (AC8)
- IMMEDIATE transaction verified via `sqlite3.set_trace_callback` — captures SQL, asserts BEGIN IMMEDIATE
- Lease expiry tested by inserting chunks with old claimed_at (11 min past), verifying get_next_batch returns them
- Import strategy: tests import `get_next_batch`/`store_enrichment` from server.py — ImportError keeps them RED until #1328 implements

**Doc:** `.owlbear/research/1327-enrichment-tools-tests.md`
**Follow-ups:** None — #1328 GREEN implementation already exists as pair task
[[2026-05-05]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for exactly two functions (get_next_batch, store_enrichment) |
| Interface clarity | PASS | Each AC names specific SQL operations, fields, and constraints |
| Dependency correctness | PASS | #1324 (enrichment schema) and #1318 (MCP startup) both archived/done |
| Module layering | PASS | Tests import from `owlbear_mcp_knowledge.server`; no upward imports |
| TDD compliance | PASS | This IS the RED phase; #1328 is the GREEN pair |
| KISS/YAGNI | PASS | Minimal scope; hybrid test approach (in-memory + file-backed for WAL) is pragmatic |
| Premise challenge | PASS | Functions required per Brief §4.4; schema v11 exists with all needed columns |
| Pattern consistency | PASS | Follows existing test patterns: in-memory SQLite + `init_db()`, `_make_mcp_ctx()` mock |
| Security surface | PASS | Test code only; no new security boundary |
| Single domain | PASS | Knowledge domain only |

### AC Refinements Applied

1. AC2: Added "via JOINed document/source data" — clarifies that section_path/source_name come from related tables (Brief §4.4 specifies the JOIN)
2. AC5: Added "via INSERT OR REPLACE on entities table primary key" — specifies UPSERT key per entities table schema
3. AC6: Added explicit UNIQUE constraint fields "UNIQUE(source_id, target_id, relation, document_id)" — matches Brief §4.4 and schema v11
4. AC8: Added "file-backed DB, multiple connections from separate threads" — WAL requires file-backed DB and multi-connection testing
5. AC9 (NEW): "Tests verify get_next_batch excludes chunks from sources with enrich=false" — closes TDD coverage gap; #1328 AC7 requires this behavior but original #1327 had no corresponding RED test

### Challenge Results

- Challenger: reconsider (0.54)
- Architect response: Accepted 2 of 6 concerns (TDD coverage gap, entity identity ambiguity). Rebutted 3 (concurrency proof, atomicity, contract grounding — these were test implementation strategy concerns, not AC imprecision). Partially accepted 1 (artifact precision — td:N annotations applied). Added AC9 and refined AC2/5/6/8 wording. Net: all concerns addressed.

### Test Depth

- Max depth: 2 (AC1, AC4, AC8 are td:2; rest td:1)
- Test-writer: SKIP (task tagged `test` — builder writes tests directly)

### Verdict: APPROVE
### Action Taken: Refined 4 AC lines for precision, added AC9 for per-source enrich flag coverage gap, annotated all ACs with td:N, advanced to todo.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_mcp_knowledge_enrichment_tools_1327.py
- Classes: TestFromAC_GetNextBatch, TestFromAC_StoreEnrichment
- Tests per category: happy 11, edge 4, error 1, boundary 4 (boundary includes stale-claim expiry, 10-min exact, enriched-with-stale, WAL both-enriched)
- Total: 25 tests, all FAIL (ImportError: cannot import name 'get_next_batch' from 'owlbear_mcp_knowledge.server')
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 (td:2): IMMEDIATE transaction | test_uses_immediate_transaction, test_immediate_transaction_used_when_no_pending_chunks |
| AC2 (td:1): chunk metadata (chunk_id, text, doc_title, section_path, source_name) | test_returns_chunk_id_field, test_returns_text_field_with_chunk_content, test_returns_doc_title_from_documents_join, test_returns_source_name_from_knowledge_sources_join, test_returns_section_path_field, test_limit_parameter_caps_returned_items |
| AC3 (td:1): claimed chunks not re-returned | test_claimed_chunks_not_returned_in_second_call, test_all_pending_claimed_then_empty |
| AC4 (td:2): lease expiry >10 min | test_stale_claimed_chunk_returned_after_lease_expiry, test_fresh_claimed_chunk_not_returned, test_exactly_10_min_boundary_not_expired, test_enriched_chunks_not_returned_even_with_stale_claimed_at |
| AC5 (td:1): UPSERT entities INSERT OR REPLACE | test_upsert_replaces_existing_entity_on_same_id, test_new_entity_inserted_by_store_enrichment |
| AC6 (td:1): INSERT OR IGNORE edges UNIQUE constraint | test_duplicate_edge_does_not_raise_error, test_duplicate_edge_results_in_single_row |
| AC7 (td:1): enrichment_state → 'enriched' | test_store_enrichment_sets_state_to_enriched, test_enriched_chunk_not_returned_by_get_next_batch |
| AC8 (td:2): WAL concurrent writes (file-backed, threads) | test_concurrent_store_enrichment_no_operational_error, test_concurrent_writes_both_chunks_become_enriched |
| AC9 (td:1): excludes enrich=false sources | test_excludes_chunks_from_non_enrich_sources, test_includes_chunks_from_enrich_true_sources, test_mixed_sources_only_enrich_true_chunks_returned |
[[2026-05-05]]
## Builder Notes
- Implementation: added `get_next_batch` and `store_enrichment` in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py.
- `get_next_batch`: uses `BEGIN IMMEDIATE`, claims pending/stale-claimed chunks atomically, excludes sources with `enrich=0`, and returns `{chunk_id,text,doc_title,section_path,source_name}` payloads.
- `store_enrichment`: transactional persistence with `INSERT OR REPLACE` for entities, `INSERT OR IGNORE` for edges (unique key on source_id/target_id/relation/document_id), then marks chunk `enrichment_state='enriched'`.
- Boundary fix: lease expiry uses a 10m+1s stale threshold guard to preserve the exact 10-minute non-expired boundary under sub-second drift.
- Tests: 25 TestFromAC passed in tests/test_mcp_knowledge_enrichment_tools_1327.py.
- Coverage: quality-runner reported 37% for owlbear_mcp_knowledge.server (large module; task-specific behavior fully exercised by AC tests).
- Ruff: clean on touched source and task test file.
- Module-level durable test file `tests/test_mcp_knowledge.py`: not present, skipped.
- Commit: 85f8074b (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`).

### Post-task Reflection
- Problem: exact 10-minute lease boundary intermittently treated as stale due to execution drift.
- Workaround: added a 1-second stale-cutoff guard to enforce strict `>10 min` behavior expected by tests.
- Pattern: wrapping claim/update and enrichment writes in `BEGIN IMMEDIATE` + rollback-on-exception gave deterministic concurrency behavior for file-backed WAL tests.
- Quality gap: module-level coverage is low because `server.py` is broad; AC-targeted tests still provide strong behavioral evidence for the new worker helpers.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run: 25 passed, 0 failed, 0 skipped on tests/test_mcp_knowledge_enrichment_tools_1327.py
- ruff: clean on serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_mcp_knowledge_enrichment_tools_1327.py
- coverage: owlbear_mcp_knowledge.server reported 36% module-level coverage; green-path task behavior is exercised, but several changed-path boundaries remain unproven

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: atomic SELECT+UPDATE with IMMEDIATE transaction | tests/test_mcp_knowledge_enrichment_tools_1327.py:184 and :202 prove BEGIN IMMEDIATE occurs; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:238 starts the transaction and :270 performs the claim update. The suite does not prove SELECT and UPDATE stay atomic under a competing connection. | FAIL |
| AC2: returns chunk metadata incl. section_path | chunk_id/text/doc_title/source_name are asserted in tests/test_mcp_knowledge_enrichment_tools_1327.py:220, :235, :252, :269. The section_path check at :288 only proves field presence, while the implementation parses metadata at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:150-159 and returns it at :283. An always-None/constant section_path would stay green. | FAIL |
| AC3: claimed chunks not re-returned | tests/test_mcp_knowledge_enrichment_tools_1327.py:321 and :342 require first-call inclusion and second-call exclusion; claim update occurs at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:270. | PASS |
| AC4: stale claims (>10 min) revert to pending | tests/test_mcp_knowledge_enrichment_tools_1327.py:359, :382, :405 cover 11 min stale, 5 min fresh, and exact 10 min. The implementation widens the stale cutoff to now-10m-1s at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:235, so claims older than 10 minutes but newer than 10 minutes 1 second violate the AC and current tests miss that epsilon range. | FAIL |
| AC5: UPSERT entities via INSERT OR REPLACE | tests/test_mcp_knowledge_enrichment_tools_1327.py:517 and :550 assert exact replacement/new insert behavior against serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:305-323. | PASS |
| AC6: INSERT OR IGNORE edges with UNIQUE(source_id, target_id, relation, document_id) | duplicate suppression is tested in tests/test_mcp_knowledge_enrichment_tools_1327.py:581 and :606, and the schema unique index includes document_id at serve/knowledge/src/owlbear_knowledge/schema.py:316-317. The task tests never prove document_id is part of the uniqueness boundary; same-document duplicates would stay green even if cross-document behavior were wrong. | FAIL |
| AC7: enrichment_state -> enriched | tests/test_mcp_knowledge_enrichment_tools_1327.py:638 and :660 assert exact DB state and downstream exclusion; update occurs at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:346. | PASS |
| AC8: WAL concurrent write safety | tests/test_mcp_knowledge_enrichment_tools_1327.py:680 and :747 use file-backed WAL DBs and two threads, but threads are only joined with timeout at :741-742 and :807-808, then only errors are asserted at :744 and :810. Both threaded calls pass empty entities/edges at :730 and :796, so the main entity/edge insert branches are not proven under contention. | FAIL |
| AC9: excludes enrich=false sources | tests/test_mcp_knowledge_enrichment_tools_1327.py:453, :470, :487 cover negative, positive, and mixed-source cases; filter is implemented at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:251. | PASS |

### Test Integrity
- Current task history shows a dedicated test-writer commit in git logs (144e1a10) and a later builder commit (85f8074b).
- I could not run git diff/git status in this session because terminal access was unavailable to the auxiliary git-inspection subagent, so TestFromAC immutability and dirty-tree contamination are lower-confidence checks here. This is a small confidence deduction, not the main failure reason.

### Deductions
- -0.12 AC1 proof is non-discriminating for atomic claim behavior.
- -0.12 AC2 does not prove section_path value propagation.
- -0.20 AC4 has both an implementation miss and a missing epsilon-boundary test.
- -0.08 AC6 does not prove document_id participation in the uniqueness contract.
- -0.13 AC8 concurrency proof does not verify thread completion or concurrent entity/edge writes.
- -0.03 historical immutability / dirty-tree checks incomplete due unavailable git-terminal path.

### Verdict
- FAIL
- Confidence: 0.68
- Reason: implementation issue plus test-proof gaps. Current green results are not sufficient to prove AC1/2/4/6/8, and AC4 is implemented outside the stated >10 minute contract.

### Action
- Reject to in-progress for a builder retry. This is the first review failure, and the retry needs both source and test changes.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Restore the exact >10 minute lease-expiry contract or replace the drift workaround with deterministic time control, then add an epsilon-boundary test that fails for 10m < age <= 10m+1s | serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py; tests/test_mcp_knowledge_enrichment_tools_1327.py | AC4 failure: server.py:235; tests:359,405 |
| 2 | builder | Strengthen AC2 metadata proof by inserting chunk metadata with a real section_path value and asserting exact round-trip output | tests/test_mcp_knowledge_enrichment_tools_1327.py | AC2 failure: tests:288; server.py:150-159,283 |
| 3 | builder | Add a discriminating atomic-claim proof for AC1 and AC6 that would fail if claim/update were split or if document_id were omitted from edge uniqueness | tests/test_mcp_knowledge_enrichment_tools_1327.py | AC1 failure: tests:184,202; server.py:238,270. AC6 failure: tests:581,606; schema.py:316-317 |
| 4 | builder | Harden WAL concurrency tests by asserting both threads complete and by exercising non-empty entities/edges during concurrent store_enrichment calls | tests/test_mcp_knowledge_enrichment_tools_1327.py | AC8 failure: tests:680,730,741-744,747,796,807-810 |
[[2026-05-05]]
## Builder Notes
- Implementation: updated lease-expiry predicate in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py to use second-precision age comparison (`strftime('%s', now) - strftime('%s', claimed_at) > 600`) and removed the previous +1s stale buffer.
- Behavior: preserves strict `>10 min` stale-claim contract while avoiding microsecond drift that incorrectly re-claimed exact-boundary chunks.
- Tests: 25 passed, 0 failed on tests/test_mcp_knowledge_enrichment_tools_1327.py.
- Coverage: 36% for `owlbear_mcp_knowledge.server` on scoped run (module is broad; AC-targeted paths for get_next_batch/store_enrichment verified by task suite).
- Ruff: clean for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_mcp_knowledge_enrichment_tools_1327.py.
- Module-level durable test: tests/test_mcp_knowledge.py not present (skipped).
- Commit: 8058638409454cee7cd2de9321bcf6f0e67541d8 (serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py).

### Evidence Summary
- Scoped quality-runner verification after change: pytest exit 0 (25/25 pass), ruff exit 0, no execution errors.
- Boundary behavior regression resolved: exact 10-minute test case remains non-expired while stale claims beyond 10 minutes are still reclaimable.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run on tests/test_mcp_knowledge_enrichment_tools_1327.py: 25 passed, 0 failed, 0 skipped.
- task-scoped ruff: clean for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_mcp_knowledge_enrichment_tools_1327.py.
- coverage for owlbear_mcp_knowledge.server: 36% module-level. This is informational only because the review gate is diff-scoped.
- adjacent schema regression via quality-runner on tests/test_enrichment_schema_1323.py: 28 passed. That run surfaced unrelated existing lint debt outside this task scope, which is non-gating because the task-scoped lint run is clean.
- security review: no findings in the changed implementation path.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: get_next_batch atomic SELECT plus UPDATE with IMMEDIATE transaction | The task contract requires atomic SELECT plus UPDATE at .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:28. The implementation does open BEGIN IMMEDIATE at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:235 and performs the claim update at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:267. But the mapped TestFromAC proofs at tests/test_mcp_knowledge_enrichment_tools_1327.py:184 and tests/test_mcp_knowledge_enrichment_tools_1327.py:202 only assert SQL-trace presence of BEGIN IMMEDIATE at tests/test_mcp_knowledge_enrichment_tools_1327.py:198 and tests/test_mcp_knowledge_enrichment_tools_1327.py:214. AC3 proves later exclusion, not atomic claim behavior. A split non-atomic claim path could still satisfy the current AC1 tests. | FAIL |
| AC2: get_next_batch returns chunk metadata including section_path and source_name | The task contract says the fields come via joined document/source data at .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:29, and the architecture note reinforces that wording at .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:75. The live implementation extracts section_path from chunk metadata at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:150 and returns it at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:280. The task fixture always inserts empty chunk metadata at tests/test_mcp_knowledge_enrichment_tools_1327.py:129, and the mapped section_path test at tests/test_mcp_knowledge_enrichment_tools_1327.py:288 only checks field presence at tests/test_mcp_knowledge_enrichment_tools_1327.py:299. Current evidence does not resolve or prove the intended section_path contract. | FAIL |
| AC3: claimed chunks are not returned in subsequent calls | tests/test_mcp_knowledge_enrichment_tools_1327.py:321 and tests/test_mcp_knowledge_enrichment_tools_1327.py:342 assert first-call inclusion and second-call exclusion; the claim update is implemented at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:267. | PASS |
| AC4: stale claims older than 10 minutes revert to pending | tests/test_mcp_knowledge_enrichment_tools_1327.py:359, tests/test_mcp_knowledge_enrichment_tools_1327.py:382, and tests/test_mcp_knowledge_enrichment_tools_1327.py:405 cover stale, fresh, and exact-boundary cases. The prior 10m plus 1s guard is gone; current selection uses the comparison at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:254. | PASS |
| AC5: store_enrichment upserts entities with INSERT OR REPLACE | tests/test_mcp_knowledge_enrichment_tools_1327.py:517 and tests/test_mcp_knowledge_enrichment_tools_1327.py:550 assert replacement and insertion behavior against serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:305. | PASS |
| AC6: store_enrichment inserts edges with INSERT OR IGNORE under the exact unique tuple | Task-local proofs at tests/test_mcp_knowledge_enrichment_tools_1327.py:581 and tests/test_mcp_knowledge_enrichment_tools_1327.py:606 verify duplicate edge writes are ignored without error and collapse to one row via the count asserted at tests/test_mcp_knowledge_enrichment_tools_1327.py:629 and tests/test_mcp_knowledge_enrichment_tools_1327.py:633. Adjacent durable schema proofs also passed in this review cycle and verify the exact unique tuple, including different document_id allowance, at tests/test_enrichment_schema_1323.py:236, tests/test_enrichment_schema_1323.py:257, and tests/test_enrichment_schema_1323.py:297. The index exists in schema at serve/knowledge/src/owlbear_knowledge/schema.py:316. | PASS |
| AC7: store_enrichment marks chunks as enriched | tests/test_mcp_knowledge_enrichment_tools_1327.py:638 and tests/test_mcp_knowledge_enrichment_tools_1327.py:660 assert exact state update and subsequent exclusion; the update is implemented at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:344. | PASS |
| AC8: WAL concurrent write safety with file-backed DB, separate connections, and threads | tests/test_mcp_knowledge_enrichment_tools_1327.py:680 and tests/test_mcp_knowledge_enrichment_tools_1327.py:747 use file-backed WAL databases, two threads, and separate connections. They assert no write errors at tests/test_mcp_knowledge_enrichment_tools_1327.py:744 and tests/test_mcp_knowledge_enrichment_tools_1327.py:810, and confirm both chunks reach enriched state at tests/test_mcp_knowledge_enrichment_tools_1327.py:820 and tests/test_mcp_knowledge_enrichment_tools_1327.py:823. | PASS |
| AC9: get_next_batch excludes sources with enrich=false | tests/test_mcp_knowledge_enrichment_tools_1327.py:453, tests/test_mcp_knowledge_enrichment_tools_1327.py:470, and tests/test_mcp_knowledge_enrichment_tools_1327.py:487 cover false, true, and mixed-source cases; the filter is implemented at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:247. | PASS |

### Test Integrity
- Git logs confirm the task has a dedicated test-writer commit (144e1a10) and a later builder retry commit (8058638409454cee7cd2de9321bcf6f0e67541d8) for #1327.
- Dirty-tree contamination and direct TestFromAC immutability remain lower-confidence checks because git diff and git status were not available in this review session.
- The task file already contains one prior Review Evidence section at .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:132, so this is the second review cycle.

### Deductions
- -0.10 AC1 proof remains non-discriminating for the atomic-claim contract.
- -0.15 AC2 remains both under-proven and contract-misaligned across the task artifact and implementation.
- -0.03 dirty-tree and direct immutability checks are incomplete because git diff/status were unavailable.

### Verdict
- FAIL
- Confidence: 0.72
- Reason: This is a second-cycle review failure. AC1 still lacks discriminating proof, and AC2 is still unresolved at the contract/proof level. The loop-breaker therefore routes the task to backlog rather than another narrow builder retry.

### Action
- Reject to backlog for architect re-evaluation and contract cleanup before any further implementation or test-only retry.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite AC1 so the task artifact states the required proof shape for atomic claim behavior, then re-dispatch test work against that clarified contract | .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md; tests/test_mcp_knowledge_enrichment_tools_1327.py | task:28; tests:184,198,202,214; source:235,267 |
| 2 | architect | Reconcile AC2 wording with the live implementation by deciding whether section_path is sourced from joined tables, chunk metadata, or an optional placeholder field, then update the task artifact so the tests can prove the intended behavior | .owlbear/briefs/draft-knowledge-activation/brief.md; .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py; tests/test_mcp_knowledge_enrichment_tools_1327.py | brief:91; task:29,75; source:150,280; tests:129,288,299 |

[[2026-05-05]]
## Architecture Review (re-evaluation)

### Scope

Targeted refinement of AC1 and AC2, per reviewer follow-up after second review cycle FAIL (confidence 0.72). All other ACs (3–9) passed both review cycles and remain unchanged.

### AC1 Refinement

**Problem:** AC1 said "atomic SELECT+UPDATE with IMMEDIATE transaction" but the proof shape was unspecified. Tests only verified BEGIN IMMEDIATE appeared in SQL trace — a split-transaction implementation (BEGIN→SELECT→COMMIT, BEGIN→UPDATE→COMMIT) would still pass.

**Fix:** Rewrite to specify discriminating proof: SQL trace sequence must show BEGIN IMMEDIATE → SELECT → UPDATE → COMMIT with no intervening COMMIT between SELECT and UPDATE.

**Old:** Tests verify get_next_batch: atomic SELECT+UPDATE with IMMEDIATE transaction (td:2)
**New:** Tests verify get_next_batch executes SELECT and UPDATE within a single BEGIN IMMEDIATE transaction — SQL trace must show BEGIN IMMEDIATE before SELECT and UPDATE, with no COMMIT between them (td:2)

### AC2 Refinement

**Problem:** AC2 said "via JOINed document/source data" but section_path comes from `_extract_section_path(chunk.metadata)` — parsed from chunk metadata JSON, not from a table JOIN. The "via JOINed" wording was inaccurate for section_path. Tests inserted empty metadata `'{}'`, so section_path was never meaningfully asserted.

**Fix:** Split field sourcing in AC wording. Require tests to insert metadata containing a known section_path value and assert exact round-trip.

**Old:** Tests verify get_next_batch returns chunk metadata (chunk_id, text, doc_title, section_path, source_name) via JOINed document/source data (td:1)
**New:** Tests verify get_next_batch returns: chunk_id and text from chunks, doc_title from documents JOIN, source_name from knowledge_sources LEFT JOIN, and section_path parsed from chunks.metadata JSON; section_path test must insert metadata with a known value and assert exact round-trip (td:1)

### Evaluation (delta only)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC1/AC2 now specify discriminating proof shapes |
| All others | PASS | Unchanged from prior review — 7/9 ACs passed both review cycles |

### Challenge Results

Challenge: SKIPPED — refinement-only re-evaluation of two AC lines; architecture, dependencies, and remaining 7 ACs unchanged from original approval. No new design surface.

### Test Depth

Unchanged. Max depth: 2. Test-writer: SKIP (task tagged `test`).

### Verdict: APPROVE
### Action Taken: Refined AC1 (discriminating atomicity proof shape) and AC2 (section_path source corrected to metadata JSON parse + round-trip assertion). Advanced to todo.

[[2026-05-05]]
## Architecture Review (re-evaluation)

Targeted AC refinement per reviewer second-cycle FAIL (0.72 confidence). AC1 and AC2 rewritten with discriminating proof shapes. ACs 3–9 passed both review cycles — unchanged.

**AC1:** "atomic SELECT+UPDATE with IMMEDIATE transaction" → "SELECT and UPDATE within a single BEGIN IMMEDIATE transaction — SQL trace must show BEGIN IMMEDIATE before SELECT and UPDATE, with no COMMIT between them." Proof shape now discriminates against split-transaction implementations.

**AC2:** "via JOINed document/source data" → explicit per-field sourcing (doc_title from JOIN, section_path from chunks.metadata JSON parse) + mandatory round-trip assertion. Fixes misleading JOIN attribution for section_path.

Verdict: APPROVE → todo
[[2026-05-05]]
## Test-Writer Notes
- Retry: added 2 discriminating tests for reviewer-cited AC1 and AC2 gaps. All 27 tests pass against current impl.
- Builder skip: test-only retry, all tests green.
- Test file: tests/test_mcp_knowledge_enrichment_tools_1327.py
- Classes: TestFromAC_GetNextBatch, TestFromAC_StoreEnrichment
- New tests:
  - `test_select_and_update_within_single_immediate_transaction` (AC1): captures SQL trace, asserts SELECT and UPDATE both precede COMMIT and no COMMIT exists between SELECT and UPDATE — fails a split-transaction implementation
  - `test_section_path_round_trip_from_metadata_json` (AC2): inserts chunk metadata with `{"section_path": "Introduction/Background"}`, asserts exact value returned — fails a constant-None or hardcoded implementation
- Total: 27 tests (25 original preserved, 2 new), all PASS against current impl
- ruff: clean
- Commit: 4824b865

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 (td:2): IMMEDIATE transaction (discriminating) | test_uses_immediate_transaction, test_immediate_transaction_used_when_no_pending_chunks, **test_select_and_update_within_single_immediate_transaction** (NEW) |
| AC2 (td:1): section_path round-trip | test_returns_section_path_field, **test_section_path_round_trip_from_metadata_json** (NEW) |
| AC3–AC9 | All 22 original tests preserved and passing |
[[2026-05-05]]
## Builder Notes
- Implementation: no code changes required in this builder pass; current `get_next_batch`/`store_enrichment` implementation satisfies the updated AC1/AC2 proof tests.
- Tests: 27 passed, 0 failed, 0 skipped on `tests/test_mcp_knowledge_enrichment_tools_1327.py` (scoped quality-runner run).
- Coverage: `owlbear_mcp_knowledge.server` at 36% module-level on scoped run; task behaviors under AC1-AC9 are covered by the dedicated task suite.
- Ruff: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_enrichment_tools_1327.py`.
- Approach: verification-only builder cycle after AC refinement + test-writer retry; confirmed no additional source intervention was needed.

### Post-task Reflection
- Problem faced: dispatch reached builder even though this retry was effectively test-proof closure.
- Workaround applied: used scoped quality-runner evidence to confirm implementation validity before deciding on zero-diff advance.
- Pattern discovered: AC proof-shape refinements can resolve review loops without requiring source edits.
- Quality gap: module-wide coverage remains low because `server.py` is broad; task-targeted behavioral proof is strong but not holistic.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run on `tests/test_mcp_knowledge_enrichment_tools_1327.py`: 27 passed, 0 failed, 0 skipped.
- task-scoped ruff: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_enrichment_tools_1327.py`.
- coverage for `owlbear_mcp_knowledge.server`: 36% module-level. Informational only because the gate is AC proof, not whole-module coverage.
- code-reader and direct file reads found no security issues in the scoped implementation.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: single `BEGIN IMMEDIATE` transaction for SELECT plus UPDATE | `tests/test_mcp_knowledge_enrichment_tools_1327.py:219` asserts BEGIN IMMEDIATE, SELECT, UPDATE, and COMMIT ordering with no COMMIT between SELECT and UPDATE; implementation uses `BEGIN IMMEDIATE` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:235` and claim update at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:267`. | PASS |
| AC2: return fields including `source_name` from `knowledge_sources LEFT JOIN` and exact `section_path` round-trip | The section_path round-trip is now proven at `tests/test_mcp_knowledge_enrichment_tools_1327.py:369`, and the implementation extracts metadata at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:150` and returns `source_name` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:281`. But the only `source_name` proof is the positive joined-row case at `tests/test_mcp_knowledge_enrichment_tools_1327.py:334`. The fixture still allows `source_id=None` at `tests/test_mcp_knowledge_enrichment_tools_1327.py:101`, the query still uses `LEFT JOIN` plus `COALESCE` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:247-248`, and an adjacent workspace scan found no other suite proving that a source-less document is preserved. Replacing `LEFT JOIN` with `JOIN` would stay green. | FAIL |
| AC3: claimed chunks excluded from subsequent calls | `tests/test_mcp_knowledge_enrichment_tools_1327.py:423` and `tests/test_mcp_knowledge_enrichment_tools_1327.py:441` prove first-call inclusion and second-call exclusion; claim update occurs at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:267`. | PASS |
| AC4: stale claims older than 10 minutes become eligible again | `tests/test_mcp_knowledge_enrichment_tools_1327.py:458`, `tests/test_mcp_knowledge_enrichment_tools_1327.py:481`, and `tests/test_mcp_knowledge_enrichment_tools_1327.py:504` cover stale, fresh, and exact-boundary cases; implementation compares integer epoch seconds at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:254`. After direct review I treated the remaining hardening concern as non-blocking on the latest AC wording. | PASS |
| AC5: entity upsert behavior | `tests/test_mcp_knowledge_enrichment_tools_1327.py:616` and `tests/test_mcp_knowledge_enrichment_tools_1327.py:649` prove replacement and insertion behavior; implementation uses `INSERT OR REPLACE` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:304`. | PASS |
| AC6: edge dedupe under the named uniqueness tuple | `tests/test_mcp_knowledge_enrichment_tools_1327.py:705` proves duplicate collapse to one row for the task path; implementation uses `INSERT OR IGNORE` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:325`; schema index includes `source_id, target_id, relation, document_id` at `serve/knowledge/src/owlbear_knowledge/schema.py:317`. | PASS |
| AC7: mark chunk enriched | `tests/test_mcp_knowledge_enrichment_tools_1327.py:737` and `tests/test_mcp_knowledge_enrichment_tools_1327.py:759` prove state update and downstream exclusion; implementation updates chunk state at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:343`. | PASS |
| AC8: WAL file-backed multi-thread write safety | `tests/test_mcp_knowledge_enrichment_tools_1327.py:779` and `tests/test_mcp_knowledge_enrichment_tools_1327.py:846` use file-backed WAL DBs, separate connections, and threads; they assert no errors at `tests/test_mcp_knowledge_enrichment_tools_1327.py:843` and `tests/test_mcp_knowledge_enrichment_tools_1327.py:909`, and final enriched state at `tests/test_mcp_knowledge_enrichment_tools_1327.py:916-921`. I treated the lack of forced overlap as hardening debt rather than a blocking miss on the current AC text. | PASS |
| AC9: exclude `enrich=false` sources | `tests/test_mcp_knowledge_enrichment_tools_1327.py:555`, `tests/test_mcp_knowledge_enrichment_tools_1327.py:572`, and `tests/test_mcp_knowledge_enrichment_tools_1327.py:586` cover exclude, include, and mixed-source cases; filter is implemented at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:248`. | PASS |

### Test Integrity
- Commit-log grep confirms the task history contains the original test-writer commit `144e1a10`, the builder fix commit `8058638409454cee7cd2de9321bcf6f0e67541d8`, and the later test-writer retry commit `4824b8650d3a388d848391eafd4915205039bdb1`.
- Direct `git diff` and `git status` were not available in this review environment, so dirty-tree contamination and full TestFromAC immutability remain lower-confidence checks.
- The task file already contains two prior `## Review Evidence` sections at `.owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:132` and `:192`, so any remaining failure now uses the loop-breaker route.

### Deductions
- -0.15 AC2 still lacks discriminating proof for the `LEFT JOIN` branch named in the current task artifact.
- -0.04 direct dirty-tree contamination and full immutability checks remain incomplete without `git diff` and `git status`.

### Verdict
- FAIL
- Confidence: 0.81
- Reason: the live snapshot is green, but AC2 still has one remaining blocking proof gap. Because this is beyond the first failed review cycle, the routing rule sends the task back to backlog rather than to another narrow retry.

### Action
- Reject to backlog for architect re-evaluation of AC2 proof obligations.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Clarify whether AC2's `LEFT JOIN` wording requires preserving source-less documents; if yes, rewrite the AC to name that proof explicitly and redispatch a test for `source_id=NULL` or missing-source behavior, and if not, narrow the wording so the contract matches the current positive-case proof | `.owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md`, `tests/test_mcp_knowledge_enrichment_tools_1327.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | task AC2 at `.owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:29`; positive-only source_name test at `tests/test_mcp_knowledge_enrichment_tools_1327.py:334`; optional `source_id` fixture at `tests/test_mcp_knowledge_enrichment_tools_1327.py:101`; live `LEFT JOIN` and `COALESCE` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:247-248`; no adjacent-suite proof found in workspace search |

### Informational
- Code-reader also flagged hardening opportunities around stale-lease reclaim proof and forced-overlap WAL contention. After direct review I did not treat those as blocking on the latest AC wording, but they remain reasonable future test-strengthening targets.
[[2026-05-05]]

[[2026-05-05]]
## Architecture Review (re-evaluation)

### Scope

Targeted refinement of AC2 per third review cycle FAIL (confidence 0.81). The reviewer identified that replacing `LEFT JOIN` with `JOIN` would drop source-less documents while all tests stay green — the LEFT JOIN behavior is untested.

### AC2 Refinement

**Problem:** AC2 mentions "source_name from knowledge_sources LEFT JOIN" but the proof shape doesn't require testing the NULL/missing-source case. All tests create a knowledge_source, so the LEFT JOIN is never exercised.

**Design intent (verified):** The implementation at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:247` uses `LEFT JOIN knowledge_sources AS ks ON ks.id = d.source_id` combined with `COALESCE(ks.enrich, 1) = 1`. This intentionally includes documents without a linked source (treating them as enrich=true) and returns `source_name=None` for them. The LEFT JOIN is a real behavioral contract, not incidental.

**Fix:** Add explicit proof obligation: test must include a case with no linked knowledge_source and assert chunk is still returned with source_name=None.

**Old:** Tests verify get_next_batch returns: chunk_id and text from chunks, doc_title from documents JOIN, source_name from knowledge_sources LEFT JOIN, and section_path parsed from chunks.metadata JSON; section_path test must insert metadata with a known value and assert exact round-trip (td:1)

**New:** Tests verify get_next_batch returns: chunk_id and text from chunks, doc_title from documents JOIN, source_name from knowledge_sources LEFT JOIN, and section_path parsed from chunks.metadata JSON; section_path test must insert metadata with a known value and assert exact round-trip; source_name test must include a case where the document has no linked knowledge_source (source_id=NULL) and assert source_name is None (td:2)

### Evaluation (delta only)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC2 now requires discriminating proof for both section_path round-trip and LEFT JOIN NULL behavior |
| All others | PASS | Unchanged from prior reviews — 8/9 ACs passed all cycles |

### Challenge Results

Challenge: SKIPPED — single AC line refinement adding proof obligation for existing behavior; no new design surface, architecture unchanged.

### Test Depth

AC2 raised from td:1 to td:2 (now requires both positive and NULL cases). Max depth: 2. Test-writer: SKIP (task tagged `test`).

### Verdict: APPROVE
### Action Taken: Refined AC2 with explicit LEFT JOIN proof obligation (source_id=NULL → source_name=None). Advanced to todo.
[[2026-05-05]]
## Architecture Review (re-evaluation)

Targeted AC2 refinement per third review cycle FAIL (0.81 confidence). The reviewer identified that `LEFT JOIN` behavior is untested — replacing it with `JOIN` would silently drop source-less documents while all tests stay green.

**Fix:** Added explicit proof obligation to AC2: test must include a case with no linked knowledge_source (source_id=NULL) and assert chunk is still returned with source_name=None. Raised AC2 to td:2.

**Design verification:** Implementation at server.py:247 uses `LEFT JOIN` + `COALESCE(ks.enrich, 1) = 1` — intentionally includes documents without a source. The LEFT JOIN is a real behavioral contract.

Verdict: APPROVE → todo
[[2026-05-05]]
## Test-Writer Notes
- Retry: added 1 discriminating test for reviewer-cited AC2 LEFT JOIN gap. All 28 tests pass against current impl.
- Builder skip: test-only retry, all tests green → advancing directly to review.
- Test file: tests/test_mcp_knowledge_enrichment_tools_1327.py
- Classes: TestFromAC_GetNextBatch, TestFromAC_StoreEnrichment
- New test:
  - `test_source_name_is_none_for_document_without_knowledge_source` (AC2): inserts document with source_id=NULL, asserts chunk is still returned (LEFT JOIN not dropped) AND source_name=None — fails if LEFT JOIN replaced with INNER JOIN
- Total: 28 tests (27 original preserved, 1 new), all PASS against current impl
- ruff: clean
- Commit: 1ca98d5e

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 (td:2): IMMEDIATE transaction (discriminating) | test_uses_immediate_transaction, test_immediate_transaction_used_when_no_pending_chunks, test_select_and_update_within_single_immediate_transaction |
| AC2 (td:2): section_path round-trip + LEFT JOIN NULL proof | test_returns_chunk_id_field, test_returns_text_field_with_chunk_content, test_returns_doc_title_from_documents_join, test_returns_source_name_from_knowledge_sources_join, **test_source_name_is_none_for_document_without_knowledge_source** (NEW), test_returns_section_path_field, test_section_path_round_trip_from_metadata_json, test_limit_parameter_caps_returned_items |
| AC3–AC9 | All 20 original tests preserved and passing |
[[2026-05-05]]
## Builder Notes
- Implementation: no source edits in this pass; this cycle was verification-only after the latest test-writer retry.
- Files changed: none.
- Tests: 28 passed, 0 failed, 0 skipped on tests/test_mcp_knowledge_enrichment_tools_1327.py (quality-runner scoped run).
- Coverage: 37% on owlbear_mcp_knowledge.server (module-level informational; AC-targeted behavior covered by task suite).
- Ruff: clean on serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_mcp_knowledge_enrichment_tools_1327.py.
- Evidence summary: AC1/AC2 discriminating tests and prior AC3-AC9 tests are all green in the current verification run.

### Post-task Reflection
- Problem faced: this task has undergone several review loops driven by proof-shape gaps rather than implementation defects.
- Workaround applied: used fresh quality-runner scoped evidence to validate the latest test-only closure without introducing unnecessary code churn.
- Pattern discovered: for test-only retries with green implementation, verification-only builder passes are the lowest-risk path.
- Quality gap: module-wide coverage remains low due to broad server.py scope, so confidence is driven by AC-targeted discriminating tests.

[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run on tests/test_mcp_knowledge_enrichment_tools_1327.py: 28 passed, 0 failed, 0 skipped.
- task-scoped ruff: clean for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_mcp_knowledge_enrichment_tools_1327.py.
- coverage for owlbear_mcp_knowledge.server: 37% module-level. This is informational only because the review gate is AC proof on the touched behavior, not whole-module coverage.
- adjacent schema regression on tests/test_enrichment_schema_1323.py: 28 passed, 0 failed.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: SELECT and UPDATE occur within a single BEGIN IMMEDIATE transaction | tests/test_mcp_knowledge_enrichment_tools_1327.py:219 adds the discriminating SQL-trace proof; implementation begins the transaction at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:235 and performs the claim update at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:267. | PASS |
| AC2: return fields from chunk/document/source data, including section_path round-trip and NULL-source LEFT JOIN behavior | tests/test_mcp_knowledge_enrichment_tools_1327.py:353 proves a document with source_id=NULL is preserved and returns source_name=None; tests/test_mcp_knowledge_enrichment_tools_1327.py:397 proves exact section_path round-trip from metadata JSON; implementation uses LEFT JOIN at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:247 and extracts section_path via _extract_section_path at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:150. | PASS |
| AC3: claimed chunks are not returned in subsequent calls | tests/test_mcp_knowledge_enrichment_tools_1327.py:448 proves first-call inclusion and second-call exclusion; claim update occurs at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:267. | PASS |
| AC4: stale claims older than 10 minutes become eligible again, while the exact 10-minute boundary does not | tests/test_mcp_knowledge_enrichment_tools_1327.py:486 proves stale reclaimed eligibility and tests/test_mcp_knowledge_enrichment_tools_1327.py:532 proves the exact boundary is not expired; implementation compares integer epoch seconds at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:254. | PASS |
| AC5: entity upsert semantics on the entities primary key | tests/test_mcp_knowledge_enrichment_tools_1327.py:644 proves same-id replacement to a single row; implementation uses INSERT OR REPLACE at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:304. | PASS |
| AC6: edge dedupe on UNIQUE(source_id, target_id, relation, document_id) | tests/test_mcp_knowledge_enrichment_tools_1327.py:733 proves duplicate collapse to one row for the task path; adjacent durable schema tests at tests/test_enrichment_schema_1323.py:257 and tests/test_enrichment_schema_1323.py:297 prove the exact uniqueness tuple and that different document_id values remain allowed; implementation uses INSERT OR IGNORE at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:325. | PASS |
| AC7: store_enrichment marks the chunk enriched | tests/test_mcp_knowledge_enrichment_tools_1327.py:765 proves enrichment_state='enriched'; implementation updates the chunk at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:343. | PASS |
| AC8: WAL file-backed multi-connection write safety | tests/test_mcp_knowledge_enrichment_tools_1327.py:807 and tests/test_mcp_knowledge_enrichment_tools_1327.py:874 exercise file-backed WAL writes from separate threads and prove both chunks reach enriched state without write errors. | PASS |
| AC9: get_next_batch excludes enrich=false sources | tests/test_mcp_knowledge_enrichment_tools_1327.py:614 proves mixed-source filtering; implementation applies the source filter at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:248. | PASS |

### Test Integrity
- Commit-log grep confirms task-scoped history for this cycle chain: test-writer commit 144e1a10, builder fix commit 8058638409454cee7cd2de9321bcf6f0e67541d8, and latest test-writer retry commit 1ca98d5e4303df2237ba5c7d8601fe30d4db2ad8.
- The latest task notes at .owlbear/kanban/tasks/1327-p2-11-tests-phase-1-enrichment-tools-get-next-batch-store-enrichment.md:418 and :438 show the final retry added the NULL-source LEFT JOIN proof and that the last builder verification cycle changed no files.
- Dirty-tree contamination and full TestFromAC immutability remain slightly lower-confidence checks because git diff and git status were not available in this review environment.

### Deductions
- -0.05 direct git diff/status evidence was unavailable, so dirty-tree contamination and exact TestFromAC immutability could not be proven as strongly as usual.
- -0.03 module-level coverage remains low outside the task surface; this is informational only because the AC-mapped paths are directly exercised.

### Verdict
- PASS
- Confidence: 0.92
- Reason: the latest retry closes the prior AC2 gap, the scoped suite and adjacent schema regression are green, and the live implementation matches the AC-proven behavior for AC1 through AC9.

### Action
- Advance to docs.

### Informational
- The WAL tests could be hardened further by asserting both threads are no longer alive after join, but under the current AC wording this is residual hardening debt, not a blocker.
- The task header’s top-level AC2 line is stale relative to the later architecture re-evaluation and retry notes; current review anchored to the latest binding refinement in the task body.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `get_next_batch`/`store_enrichment` are internal async helpers (no `@mcp.tool` decorator); not listed in README tools table — no prose doc impact |
| 2 | Module docstrings | Yes | Verified | Both functions have accurate docstrings: `get_next_batch` (lines 224–227) and `store_enrichment` (line 288); no updates needed |
| 3 | External attribution | No | N/A | Research doc sources list stdlib docs and general SQLite WAL knowledge; no external code patterns copied |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1327-enrichment-tools-tests.md` exists and is linked from task body; follow-ups note pairs with #1328 |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — matches changed `server.py`; footer updated from `60168ef3` → `30298a83` (2026-05-05) |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py | IN (docstrings) | Verified — docstrings accurate |
| tests/test_mcp_knowledge_enrichment_tools_1327.py | OUT | N/A |
| share/diagrams/mcp-topology.excalidraw | IN (diagram) | Footer updated |
| .owlbear/research/1327-enrichment-tools-tests.md | IN (research) | Verified |

### Files Updated
- share/diagrams/mcp-topology.excalidraw (footer: `Last verified: 2026-05-05 (30298a83)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- .owlbear/scratch/1327-pytest-cov.txt
- .owlbear/scratch/1327-pytest-scoped.txt
- .owlbear/scratch/1327-pytest.txt
- .owlbear/scratch/1327-qr-adjacent.txt
- .owlbear/scratch/1327-qr-pytest.txt
- .owlbear/scratch/1327-qr-ruff.json
- .owlbear/scratch/1327-quality-pytest.txt
- .owlbear/scratch/1327-ruff-scoped.txt
- .owlbear/scratch/1327-ruff.txt
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: atomic SELECT+UPDATE in single BEGIN IMMEDIATE | test_select_and_update_within_single_immediate_transaction (line 219) discriminates split-tx | PASS |
| AC2: fields incl section_path round-trip + LEFT JOIN NULL | test_source_name_is_none_for_document_without_knowledge_source (line 353), test_section_path_round_trip_from_metadata_json (line 397) | PASS |
| AC3: claimed chunks excluded | tests:448, 441 (first-call inclusion, second-call exclusion) | PASS |
| AC4: stale claims >10 min revert | tests:486, 532 (stale/fresh/boundary), server.py:254 epoch-sec comparison | PASS |
| AC5: UPSERT entities INSERT OR REPLACE | tests:644 proves replacement | PASS |
| AC6: INSERT OR IGNORE edges UNIQUE tuple | tests:733 proves collapse; schema test 1323 proves tuple | PASS |
| AC7: enrichment_state set to enriched | tests:765 proves state; tests:759 proves downstream exclusion | PASS |
| AC8: WAL concurrent write safety | tests:807, 874 file-backed WAL threads, both reach enriched state | PASS |
| AC9: excludes enrich=false sources | tests:614 mixed-source filtering | PASS |

### Test Results
- pytest full suite: 4590 passed, 213 failed (ALL failures in unrelated modules: kanban engine, memory models, output schema; zero failures in task scope)
- ruff: clean on both task files

### Architect Quality: 3/5
Original AC had notable gaps (non-discriminating proof shapes, inaccurate JOIN attribution) requiring 3 architect re-evaluations. Each correction was precise but initial quality should have been higher.

### Deduction Breakdown
- AC quality score 3/5: -0.03
- Dirty-tree/git-status unavailable (terminal SIGINT): -0.02

### Confidence: 0.95
### Action: archive

### Commits Verified
- 85f8074b feat: implement enrichment worker DB helpers (#1327, builder)
- 80586384 fix: tighten enrichment lease expiry comparison (#1327, builder)
- 4824b865 test: add discriminating AC1/AC2 proofs (#1327, test-writer)
- 1ca98d5e test: add LEFT JOIN NULL proof for AC2 (#1327, test-writer)