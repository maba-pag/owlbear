---
id: 1884
title: 'Knowledge: SourceStore protocol — add last_refreshed_at write path'
status: review
priority: needed
created: 2026-05-26T06:08:59.357802+02:00
updated: 2026-05-26T08:41:11.457143+02:00
tags:
  - knowledge
  - layer-2
parent: 1877
depends_on: []
ac:
  - 'Add `last_refreshed_at: datetime | None = None` field to `SourceUpdate` model
    in `protocols/sources.py`'
  - In `SqliteSourceStore.update_source`, when `update.last_refreshed_at` is not
    None, persist it as ISO string via `.isoformat()` (same serialization as 
    `record_health` uses for `checked_at`)
  - 'Test: calling `update_source(id, SourceUpdate(last_refreshed_at=now))` persists
    the timestamp and returns updated record with matching value'
  - 'Test: calling `update_source(id, SourceUpdate(state=SourceState.ACTIVE))` preserves
    existing `last_refreshed_at` value (no clobber)'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Extend SourceStore protocol to support refresh watermark updates. Currently `SourceUpdate` has no `last_refreshed_at` field and `record_health` only sets `last_checked_at`. IngestCoordinator.refresh() needs a way to persist the refresh timestamp through the protocol boundary.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/sources.py`
- Gap identified in: `.owlbear/research/1877-ingest-coordinator.md`
- Options: Add field to SourceUpdate, or add a dedicated `mark_refreshed(source_id, timestamp)` method
- See also: legacy `refresh.py` L446 which uses direct store mutation

[[2026-05-26T06:26:53+02:00]]
## Research
- Research doc: .owlbear/research/1884-sourcestore-refresh-write-path.md
- Sources: 7 studied (all internal codebase), 4 high-relevance
- Recommendation: Add `last_refreshed_at: datetime | None = None` to `SourceUpdate` model (confidence: .82)
- Challenge: reconsider (.47) — accepted "smallest unblocker" argument, revised from dedicated method to field addition
- Trade-off: Option A (field) wins on KISS/YAGNI over Option B (dedicated method) — can upgrade later if #1886 reveals need
- AC written: 4 concrete acceptance criteria (2 impl + 2 test)

[[2026-05-26T06:50:11+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One field addition + one if-check, single concern |
| Interface clarity | PASS | Field type, location, and serialization format explicit in AC |
| Dependency correctness | PASS | No dependencies; downstream #1886 depends on this correctly |
| Module layering | PASS | Changes within owlbear_knowledge only (protocol + store impl) |
| TDD compliance | PASS | AC3-4 are behavioral test specs for test-writer |
| KISS/YAGNI | PASS | Minimal field addition; research validated over dedicated method |
| Premise challenge | PASS | Gap is real: _SourceRecordBase has read field, SQL passes column, but SourceUpdate has no write path |
| Pattern consistency | PASS | Follows record_health .isoformat() pattern for timestamps; follows if-check pattern for SourceUpdate fields |
| Security surface | PASS | No new system boundary; datetime via existing protocol method |
| Single domain | PASS | Pure knowledge/sources domain |

### Challenge Results
- Challenger: reconsider (0.67)
- Findings: (1) AC1-2 are implementation instructions not behaviors, (2) timestamp serialization unstated, (3) consolidation-test gap, (4) interface drift in sibling #1885
- Architect response: ACCEPTED in part — refined AC2 to explicitly state .isoformat() serialization. Rebutted: AC1-2 guide builder location (necessary), AC3-4 are the behavioral proofs. Consolidation gap addressed by #1886 serving as integration point. Interface drift in #1885/#1886 is that task's concern, not this one's.

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC2 to specify .isoformat() serialization pattern. Set proof_bundle=behavioral. Advanced to todo.

[[2026-05-26T07:18:46+02:00]]
## Test-Writer Notes
- Test file: `tests/test_source_store_1884.py`
- Classes: `TestFromAC_SourceUpdateField`, `TestFromAC_UpdateSourceRefreshTimestamp`, `TestFromAC_NoRefreshClobber`
- Tests per category:
  - Happy path: 5 (field accepts datetime, defaults to None, persists value, round-trips via get_source, returns datetime type)
  - Edge: 2 (None explicit no-clobber, scope update preserves timestamp)
  - Boundary: 2 (microsecond precision preserved, overwrites previous value)
  - Error path: 1 (explicit None treated as no-change)
- Total: 12 tests — all FAIL (RED confirmed by quality-runner)
- Lint: clean (ruff exit 0)
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1: SourceUpdate.last_refreshed_at field | test_source_update_accepts_last_refreshed_at, test_source_update_last_refreshed_at_defaults_to_none, test_source_update_accepts_none_explicitly |
  | AC2: persist as ISO string | test_update_source_returns_datetime_not_string, test_last_refreshed_at_microsecond_precision_preserved |
  | AC3: update_source persists and returns matching value | test_update_source_persists_last_refreshed_at, test_get_source_reflects_last_refreshed_at_after_update, test_last_refreshed_at_overwrites_previous_value |
  | AC4: no clobber on unrelated update | test_state_update_preserves_last_refreshed_at, test_priority_update_preserves_last_refreshed_at, test_scope_update_preserves_last_refreshed_at, test_none_last_refreshed_at_does_not_clobber_existing |

[[2026-05-26T07:44:18+02:00]]
## Builder Notes
- Files changed:
  - serve/knowledge/src/owlbear_knowledge/protocols/sources.py
  - serve/knowledge/src/owlbear_knowledge/stores/sources.py
- Implementation summary:
  - Added `last_refreshed_at: datetime | None = None` to `SourceUpdate` protocol model.
  - Updated `SqliteSourceStore.update_source` to persist `update.last_refreshed_at` when non-None using `.isoformat()`.
  - Preserved existing semantics: explicit `None` remains no-op (no clobber of stored watermark).
- RED verification (quality-runner):
  - `tests/test_source_store_1884.py`: 0 passed, 12 failed (all `TestFromAC_*` expected failures confirmed)
  - lint on task test file: clean
- GREEN verification (quality-runner, final):
  - `tests/test_source_store_1884.py` + `tests/test_source_store_1870.py`: 81 passed, 0 failed
  - lint: clean (`protocols/sources.py`, `stores/sources.py`, task + durable tests)
  - coverage: `owlbear_knowledge.stores.sources` = 91%
- Fixes applied during verification:
  - Resolved one lint issue (`I001`) in `protocols/sources.py` by organizing imports.
- Commit:
  - `a5dfbc2b` — `feat: add source refresh watermark update path (#1884, builder)`

[[2026-05-26T08:08:14+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1884 -> todo | AC4 is not proved by the current test evidence.
- Builder evidence reviewed first: GREEN report says `tests/test_source_store_1884.py` + `tests/test_source_store_1870.py` passed 81/81, lint was clean for touched source and test files, and coverage for `owlbear_knowledge.stores.sources` was 91%.
- AC mapping summary:
  - AC1 maps to `serve/knowledge/src/owlbear_knowledge/protocols/sources.py:157` and is directly exercised by `tests/test_source_store_1884.py:67-84`.
  - AC2 maps to `serve/knowledge/src/owlbear_knowledge/stores/sources.py:211-212`, matching the existing `.isoformat()` pattern in `serve/knowledge/src/owlbear_knowledge/stores/sources.py:276-291`.
  - AC3 is directly proved by `tests/test_source_store_1884.py:93-113`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | The task AC requires `update_source(id, SourceUpdate(state=SourceState.ACTIVE))` to preserve an existing `last_refreshed_at`, but the task-specific no-clobber test exercises `SourceState.INACTIVE` instead. The only durable `ACTIVE` update test asserts only state transition, not watermark preservation. Because `update_source` branches when `update.state != next_state`, the tested `INACTIVE` transition does not prove the same-state `ACTIVE` path named by the AC. | Task AC in `.owlbear/kanban/tasks/1884-knowledge-sourcestore-protocol-add-last-refreshed-at-write-path.md:21-22`; current task test in `tests/test_source_store_1884.py:153-163`; durable transition test in `tests/test_source_store_1870.py:370-373`; state-branch logic in `serve/knowledge/src/owlbear_knowledge/stores/sources.py:197-203` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a task-scoped test that seeds `last_refreshed_at`, calls `update_source(id, SourceUpdate(state=SourceState.ACTIVE))`, and asserts the timestamp is preserved through the same-state `ACTIVE` path. | `tests/test_source_store_1884.py` | AC4 in `.owlbear/kanban/tasks/1884-knowledge-sourcestore-protocol-add-last-refreshed-at-write-path.md:21-22`; current mismatch in `tests/test_source_store_1884.py:153-163`; same-state branch in `serve/knowledge/src/owlbear_knowledge/stores/sources.py:197-203` |

## Observations
- I did not find an implementation defect in the touched source files. The rejection is for missing proof, so `todo` is the correct route.
- The task's Architecture Review explicitly framed AC3-AC4 as the behavioral proof obligations, which is why AC2's raw storage format was treated as code evidence rather than a separate blocking test requirement in this cycle (`.owlbear/kanban/tasks/1884-knowledge-sourcestore-protocol-add-last-refreshed-at-write-path.md:69`).
- Challenger cross-check agreed the PASS case should be reconsidered because proof exactness falls short on AC4.
- No new safety or security issue was found in the touched slice.

[[2026-05-26T08:18:39+02:00]]
## Test-Writer Notes
- Retry: added 1 test for reviewer's AC4 gap. All 13 tests pass against current impl.
- Builder skip: test-only retry, all tests green.
- File: `tests/test_source_store_1884.py`
- New test: `TestFromAC_NoRefreshClobber::test_same_state_active_update_preserves_last_refreshed_at`
- Coverage: seeds `last_refreshed_at`, calls `update_source(id, SourceUpdate(state=SourceState.ACTIVE))` on an already-ACTIVE source (same-state path, skips state-transition branch), asserts timestamp preserved.
- Rationale: implementation already handles this path correctly (the `if update.last_refreshed_at is not None` guard is independent of the state branch). New test passes green — direct-to-review advance per Step 1b.1.
- Lint: clean (ruff exit 0)
- Commit: `96c3b2b4` — test: add same-state ACTIVE no-clobber proof for AC4 (#1884, test-writer)
