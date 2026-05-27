---
id: 1889
title: 'Knowledge: MCP wire remove_source to IngestCoordinator.delete_source'
status: archived
priority: needed
created: 2026-05-27T01:00:59.181782+02:00
updated: 2026-05-27T04:56:16.665481+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - remove_source tool delegates to IngestCoordinator.delete_source(source_id) 
    instead of manual SQL/vector operations
  - 'On PurgeStatus.COMPLETE: response dict contains status, completed_steps, and
    summary fields from source/content/enrichment/graph sub-results'
  - 'On PurgeStatus.PARTIAL: response dict contains status, completed_steps, failed_step,
    error; does not raise ToolError'
  - Source not found (via source_store_v2.get_source) raises ToolError before 
    delegation
  - Old manual SQL queries and vector_store.delete_embedding loop removed from 
    remove_source
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Replace manual vector deletion + delete_cascade in the `remove_source` tool with delegation to IngestCoordinator.delete_source(). Return PurgeResult summary to caller. Handle partial failures per PurgeStatus.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`



## Research
- Research doc: .owlbear/research/mcp-knowledge-write-ops-wiring.md (section 3.4, item 2)
- Sources: 6 codebase files studied, all high-relevance
- Recommendation: Direct delegation to IngestCoordinator.delete_source() (confidence: .88)

### Implementation Notes
- `app_ctx.ingest_coordinator` available (dep 1888 complete); import on line 28 of server.py
- `delete_source(source_id, *, reason=None)` → `PurgeResult(status, completed_steps, failed_step, error, source, content, enrichment, graph)`
- Pre-validate source existence via `app_ctx.source_store_v2.get_source(source_id)` → raise ToolError if None (preserves current not-found behavior)
- PurgeStatus.PARTIAL → return structured dict, do NOT raise ToolError (AC3)
- PurgeStatus.COMPLETE → return dict with status + completed_steps + sub-result summaries (AC2)
- ~85 LOC of manual SQL/vector deletion replaced by ~20 LOC delegation + result formatting
- Risk: old-table sources (ingested pre-migration) won't be purged until re-ingested via new path. Accepted per phased approach.

### Testing Strategy
- Mock `IngestCoordinator.delete_source()` at MCP tool level
- Verify complete → structured response dict
- Verify partial → structured error (no ToolError)
- Verify source-not-found → ToolError
- Existing coordinator tests: tests/test_ingest_coordinator_1878.py (12 ACs)

[[2026-05-27T03:06:10+02:00]]
## Research
Validation pass against existing research doc (.owlbear/research/mcp-knowledge-write-ops-wiring.md). All findings confirmed:
- IngestCoordinator.delete_source() in AppContext (dep 1888 complete)
- Clean 1:1 replacement: ~85 LOC manual SQL/vector → ~20 LOC delegation
- PurgeResult protocol already defines all AC-required fields
- No existing MCP-level tests; builder needs new test file
- Risk: old-table orphan data accepted per phased migration
Confidence: .88. T1 autonomous — no follow-up tasks needed (task is already scoped).

[[2026-05-27T03:21:28+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure delegation refactor — replaces manual SQL with coordinator call |
| Interface clarity | PASS | AC specifies exact methods, return shapes, and error behavior |
| Dependency correctness | PASS | #1888 archived; ingest_coordinator wired in AppContext lifespan |
| Module layering | PASS | mcp-knowledge → knowledge (correct downward dependency) |
| TDD compliance | PASS | No existing MCP-level tests; new test file needed per testing strategy |
| KISS/YAGNI | PASS | ~85 LOC → ~20 LOC; no new abstractions |
| Premise challenge | PASS | IngestCoordinator.delete_source is the designed orchestration point |
| Pattern consistency | PASS | Follows existing MCP tool patterns (ToolError for not-found, structured dicts) |
| Security surface | PASS | No new system boundary; source_id from MCP params (already validated) |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| ingest_coordinator is None | AppContext not fully initialized | AttributeError | Needs null-guard (follows existing pattern) | Tool unavailable |
| delete_source partial failure | Cascade step fails mid-way | Caught internally | Yes (AC3 — returns structured dict) | Partial deletion reported |
| source_store_v2 not found | Source ID invalid | ToolError | Yes (AC4 — pre-validation) | Clear error message |

### Design Diverge
- Skipped: single valid approach (direct delegation to existing coordinator method)

### Challenge Results
- Challenger: FALLBACK — no response returned from subagent
- Architect response: self-validated AC quality issues and refined

### AC Refinements Applied
- AC2 clarified: expanded vague "sub-results" to name specific PurgeResult fields (source/content/enrichment/graph)
- AC4 added: source-not-found → ToolError preservation (was in Testing Strategy but missing from AC)
- AC5 refined: specified what "old code" means (SQL queries + vector_store.delete_embedding loop)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC for precision (5 lines), advanced backlog → todo

[[2026-05-27T03:35:43+02:00]]
## Test-Writer Notes
- Test file: `tests/test_remove_source_1889.py`
- Class: `TestFromAC_RemoveSourceDelegation`
- Proof bundle: behavioral — full TDD category coverage

**Tests by category:**
- Happy path (AC1, AC2): 8 tests — delegation call, source_id forwarding, COMPLETE response keys (status, completed_steps, source, content, enrichment, graph)
- Error paths (AC3, AC4): 7 tests — PARTIAL returns dict not ToolError, PARTIAL response fields (status/failed_step/error/completed_steps), source-not-found ToolError, coordinator not called when not found
- Regression guards (AC4, AC5): 3 tests — source_store_v2.get_source consulted, conn.execute not called, vector_store.delete_embedding not called

**Total: 18 tests, all FAIL** (quality-runner confirmed: 0 passed, 18 failed, lint clean)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1 — delegates to IngestCoordinator.delete_source | test_delegates_*, test_passes_exact_source_id_* |
| AC2 — COMPLETE response shape (status, completed_steps, source, content, enrichment, graph) | 6 tests |
| AC3 — PARTIAL returns dict, not ToolError; has status/failed_step/error/completed_steps | 5 tests |
| AC4 — source_store_v2.get_source None → ToolError before delegation | 3 tests |
| AC5 — conn.execute and delete_embedding loop removed | 2 tests |

**Mock strategy:** `_make_ctx()` configures conn.execute.fetchall to return real rows so the old SQL+vector path would call delete_embedding (4 times) — ensuring AC5 regression guards correctly fail against the current implementation.

[[2026-05-27T04:02:31+02:00]]
## Builder Notes
- Implementation: replaced manual SQL/vector deletion path in `remove_source` with delegation to `app_ctx.ingest_coordinator.delete_source(source_id)` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`.
- Behavior: `remove_source` now pre-validates with `source_store_v2.get_source(source_id)` and raises `ToolError` when missing, then returns structured purge summary dict with `status`, `completed_steps`, `failed_step`, `error`, and `source`/`content`/`enrichment`/`graph` sub-results.
- Regression guard: removed dependency on old `conn.execute(...)` query path and `vector_store.delete_embedding(...)` loop in this tool.
- Tests: `tests/test_remove_source_1889.py` via quality-runner -> 18 passed, 0 failed.
- Lint: clean (ruff).
- Coverage: quality-runner reported module coverage for `owlbear_mcp_knowledge.server` at 28% from scoped task tests.
- Module-level durable test file: no module-level `remove_source` durable test file present (`serve/*/tests/test_remove_source.py` or `tests/test_remove_source.py`) -> skipped per workflow.
- Commit: `dbe04d6af7c156eea2a77dd18d06e3f8b80e2221` (file: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`).

[[2026-05-27T04:28:12+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1889 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: `.owlbear/kanban/tasks/1889-knowledge-mcp-wire-remove-source-to-ingestcoordinator-delete-source.md:142-144` reports scoped tests passed (18/18), ruff clean, and coverage recorded for `owlbear_mcp_knowledge.server`.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1105-1115` pre-validates the source and delegates to `ingest_coordinator.delete_source(source_id)` | `tests/test_remove_source_1889.py:157-172` asserts delegation and exact `source_id` forwarding | PASS |
| AC2 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1117-1124` returns `status`, `completed_steps`, and serialized `source`/`content`/`enrichment`/`graph` payloads; `serve/knowledge/src/owlbear_knowledge/protocols/ingest.py:102-109` defines those typed purge-result fields | `tests/test_remove_source_1889.py:179-218` proves the MCP COMPLETE response surface, and `tests/test_ingest_coordinator_1878.py:243-296` proves the coordinator sub-results carry real payload data | PASS |
| AC3 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1117-1124` returns `failed_step` and `error` from the purge result; `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:162-210` defines PARTIAL purge results rather than raising | `tests/test_remove_source_1889.py:225-259` asserts PARTIAL returns a dict with `status`, `completed_steps`, `failed_step`, and `error` | PASS |
| AC4 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1100-1108` checks `source_store_v2.get_source(source_id)` and raises `ToolError` before delegation when missing | `tests/test_remove_source_1889.py:266-287` asserts `ToolError`, verifies no coordinator call, and confirms the lookup path used | PASS |
| AC5 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:1097-1124` contains no manual SQL or vector-delete path in `remove_source` | `tests/test_remove_source_1889.py:294-307` asserts `conn.execute` and `vector_store.delete_embedding` are not called | PASS |

- Blocking findings: none.
- Diagnostic check: `get_errors` reported no current diagnostics in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` or `tests/test_remove_source_1889.py`.

## Observations
- Challenger cross-check did not surface a stronger blocker. The only arguable gap was deeper MCP-layer payload assertions for AC2, but the adjacent durable coordinator suite already proves the nested purge payload contents, so the current task tests are sufficient for this wiring layer.
- Optional future hardening: add one MCP-boundary assertion around JSON normalization of nested datetime/tuple fields if serialization regressions become a recurring risk.

[[2026-05-27T04:42:01+02:00]]
## Docs Gate

**Verdict: DONE**

### Item 1: README Verification
- Convention mapping: `serve/mcp-knowledge/src/**` → `serve/mcp-knowledge/README.md`
- Stale entry found and fixed: `remove_source` row described the old manual SQL/vector path ("vectors are deleted first — any Qdrant failure aborts before SQLite changes"), which was removed by AC5.
- Updated to reflect coordinator-delegated purge with structured PurgeResult response (status, completed_steps, failed_step, error, source/content/enrichment/graph sub-results).
- Layer 1: old text absent, new text present — confirmed via grep.
- Layer 2: full editorial read — README is coherent, no contradictions, all other tool descriptions unaffected.

### Item 2: External Attribution
N/A — no external sources; implementation was a codebase-internal refactor delegating to an existing coordinator method.

### Item 3: Research Doc
Linked in task body: `.owlbear/research/mcp-knowledge-write-ops-wiring.md` (section 3.4, item 2). File confirmed present.

### Item 4: Deletion Detection
Old SQL/vector code removed from `remove_source` in `server.py` — no public-facing deletions of tools, commands, or flags. No orphaned references.

### Scratch Cleanup
No `.owlbear/scratch/1889-*` files existed.

[[2026-05-27T04:56:16+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 244 passed, 18 failed, 1 collection error.
- 18 failures: all in `tests/test_enrichment_persistence_1557.py` — pre-existing (test file had ImportError from `_helpers._extract_section_path` before builder commit; different tools at server.py:157/247, unrelated to `remove_source` at :1097-1124).
- 1 collection error: `test_mcp_kanban_newline_norm_1531.py` — ImportError in unrelated package.
- Lint: clean.
- Task-scoped tests (`test_remove_source_1889.py`): 18/18 passed per builder evidence.
- Verdict: No regressions from task 1889.

### Intent Verification
- Changed files: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (single file)
- Domain: knowledge MCP — correct for task scope
- Purpose alignment: implementation delegates `remove_source` to coordinator per stated intent
- Extraneous scope: none

### Architect Quality
- Score: 4/5
- AC lines are specific and testable after architect refinement (AC2 expanded, AC4 added, AC5 specified)
- Challenger returned FALLBACK; architect self-validated — minor process gap, no quality impact

### Commit Integrity
- Builder: `dbe04d6a` ✓
- Test-writer: `38429c34` ✓
- Doc-writer: README update present in working tree with correct content but NOT committed — process concern flagged (do not silently commit per protocol)

### Deduction Breakdown
| Criterion | Deduction |
|---|---|
| Regression failures | 0 (pre-existing, not task-caused) |
| Intent mismatch | 0 |
| Evidence integrity | 0 |
| Lint violations | 0 |
| AC quality ≤ 3 | 0 (score: 4) |
| Missing reviewer evidence | 0 (detailed PASS with AC mapping) |

### Confidence: 1.00
### Action: ARCHIVE
