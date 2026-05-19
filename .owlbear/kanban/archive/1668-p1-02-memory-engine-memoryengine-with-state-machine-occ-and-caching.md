---
id: 1668
title: 'P1-02: Memory engine — MemoryEngine with state machine, OCC, and caching'
status: archived
priority: critical
created: 2026-05-18T17:43:08.887647+02:00
updated: 2026-05-19T04:26:52.371080+02:00
tags:
  - phase-1
  - scope:memory
  - backend
parent: 1659
depends_on:
  - 1667
ac:
  - MemoryEngine.approve(id, expected_updated_at) transitions curated→approved 
    (sets approved_at and updated_at), raises TransitionError for 
    pending/approved/deleted source states
  - MemoryEngine.edit(id, fields, expected_updated_at) transitions 
    pending→curated when scope_agents in fields is non-empty, approved→curated 
    (clears approved_at, sets updated_at); curated entries and pending entries 
    without scope_agents in fields stay in current state (field update only); 
    raises TransitionError when source state is deleted
  - MemoryEngine.delete(id, expected_updated_at) hard-deletes pending entries 
    (file removed from disk), soft-deletes curated/approved (state set to 
    deleted, updated_at set); raises TransitionError when source state is 
    already deleted
  - approve(), edit(), and delete() raise ConcurrencyError when 
    expected_updated_at does not match the on-disk entry updated_at value 
    (string comparison); save() does not accept expected_updated_at
  - MtimeScanCache.has_changed() returns True on first call (triggers initial 
    load) and when directory mtime_ns has changed; returns False when mtime_ns 
    is unchanged, enabling get_entries() to skip full reparse
  - MemoryEngine.save(title, content, categories, confidence, source_agent, 
    scope_agents) creates a new entry in pending state with generated UUIDv4 id 
    and ISO 8601 timestamps (created_at, updated_at) derived from wall-clock 
    time; task-local proof must assert timestamps fall within a before/after UTC
    bound captured around the save() call
  - get_entries() skips unparseable files and tracks parse_errors count as 
    instance attribute; when duplicate UUIDs are found across files, keeps the 
    entry with later updated_at and logs a warning
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Implement the MemoryEngine class in `serve/memory/` that orchestrates storage primitives with state machine enforcement, optimistic concurrency control, and mtime-based caching.

### In Scope
- MemoryEngine class: __init__(memory_dir), load(), get_entries(), get_entry(id), approve(), edit(), delete(), save()
- State machine enforcement per brief table (pending→curated via edit, curated→approved via approve, approved→curated via edit, pending→hard-delete, curated/approved→soft-delete)
- OCC: expected_updated_at parameter on all mutations
- MtimeScanCache: skip reparse when directory mtime unchanged
- Lenient read: skip unparseable files, report parse_errors count; handle duplicate UUIDs (keep later updated_at)
- Public API exports from `owlbear_memory.__init__`

### Out of Scope
- Models and storage primitives (P1-01, dependency)
- MCP tool wiring (P2-01)
- HTTP API (P2-02)

## Technical Context
- Existing MtimeScanCache pattern already in `serve/mcp-memory/src/owlbear_mcp_memory/engine.py`
- State machine transitions defined in brief § Engine Package
- Duplicate UUID handling: keep entry with later `updated_at`, log warning

Complexity waiver: 5 AC lines — all tightly coupled to a single class (MemoryEngine) operating on one state machine. Split would fragment the state machine verification across tasks, making correctness harder to validate.

[[2026-05-19T02:49:45+02:00]]
## Research

Key findings: all implementation patterns have direct codebase precedent.

- **MtimeScanCache:** Use simple `st_mtime_ns` directory check (matches mcp-memory engine pattern and brief wording)
- **State machine:** Frozen dict keyed by `(from_state, action)` → `to_state`; 6 valid transitions, everything else raises `TransitionError`
- **OCC:** String comparison of `expected_updated_at` vs on-disk `entry.updated_at` (matches kanban pattern)
- **Duplicate UUID:** Keep entry with later `updated_at`, log warning (per brief)
- **EditPayload:** TypedDict with `total=False` for type-safe optional fields
- **Lenient read:** Count `None` returns from `storage.read_entry()` as `parse_errors`

Confidence: 0.88. Tier: T1 (composition of proven patterns, no new capability).
Doc: `.owlbear/research/memory-engine-state-machine-occ.md`
No additional follow-up tasks needed — downstream tasks already planned in parent decomposition.

[[2026-05-19T02:59:26+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single class (MemoryEngine) orchestrating state machine, OCC, and caching over storage primitives |
| Interface clarity | PASS | After refinement: all methods have explicit signatures, state transitions enumerated per source state, OCC scope explicit |
| Dependency correctness | PASS | Only dependency #1667 is archived (completed). Storage primitives, models, errors all available |
| Module layering | PASS | MemoryEngine in serve/memory/ — same package as models/errors/storage. No upward imports. Downstream mcp-memory and cockpit will consume |
| TDD compliance | PASS | Proof bundle behavioral, test-writer proceeds |
| KISS/YAGNI | PASS | Composition of proven patterns (MtimeScanCache, OCC string comparison, transition table). No speculative features |
| Premise challenge | PASS | Engine extraction required for both mcp-memory rewire (#1669) and cockpit API (#1670) |
| Pattern consistency | PASS | MtimeScanCache pattern from mcp-memory engine, OCC from kanban, atomic writes from storage.py |
| Security surface | PASS | No new security boundary — delegates to storage.py primitives which already enforce containment, symlink rejection, size bounds |
| Single domain | PASS | Memory domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| approve/edit/delete | OCC mismatch | ConcurrencyError | Yes | Caller retries with fresh state |
| approve/edit/delete | Invalid transition | TransitionError | Yes | Caller shows error |
| approve/edit/delete | Entry not found | NotFoundError | Yes | Caller shows 404 |
| get_entries | Unparseable file | N/A (skipped) | Yes | Entry invisible, parse_errors incremented |
| get_entries | Duplicate UUID | N/A (dedup) | Yes | Later entry kept, warning logged |
| has_changed | Directory stat fails | OSError | No (propagates) | Load fails — acceptable, dir must exist |

### Design Diverge
- Trigger: SKIPPED — single clear approach (composition of mcp-memory MtimeScanCache + kanban OCC + brief state table), no competing designs

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Findings: (1) AC coverage gap for save/parse_errors/dedup, (2) state-machine contradiction between research \"raise for all unlisted\" and AC2 implicit curated-edit allowance, (3) AC4 banned quantifier \"All mutation methods\", (4) OCC string vs datetime precedent mismatch, (5) cache first-call semantics unspecified
- Architect response: ACCEPTED findings 1-3 and 5 — refined AC from 5 to 7 lines. REBUTTED finding 4: P1-01 model uses string timestamps by design; string comparison is correct since engine controls all writes in consistent ISO 8601 format.

### AC Refinements Applied
1. AC2: Added explicit curated→curated and pending-without-scope_agents behaviors (field update only, no state change)
2. AC4: Replaced \"All mutation methods\" with enumerated \"approve(), edit(), and delete()\"; clarified save() excluded from OCC
3. AC5: Added \"returns True on first call\" to specify initial-load trigger
4. AC6 (new): save() method — creates pending entry with generated id and timestamps
5. AC7 (new): parse_errors tracking and duplicate UUID dedup behavior

### Builder Guidance
- **State machine interpretation:** Research §3.2 says \"raise TransitionError for any (state, action) pair not in the table.\" This refers to STATE-CHANGING transitions only. The AC clarifies: edit on curated stays curated (field update, no transition), edit on pending without scope_agents stays pending. Add (CURATED, \"edit\") → CURATED and handle pending-without-scope as no-op state change in the transition logic.
- **OCC scope:** expected_updated_at applies to approve/edit/delete only. save() creates new entries (no existing state to compare).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC from 5 to 7 lines addressing challenger gaps (save method, parse_errors, state-machine clarity, enumerated OCC scope, cache first-call), advanced to todo

[[2026-05-19T03:00:06+02:00]]
Architecture review complete. Refined AC from 5 to 7 lines addressing challenger findings: added save() method AC, parse_errors/dedup AC, explicit curated→curated edit behavior, enumerated OCC scope (not save), cache first-call semantics. Proof bundle: behavioral (unchanged). Consolidation test #1673 exists.

[[2026-05-19T03:18:33+02:00]]
## Test-Writer Notes
- Test file: tests/test_memory_engine_1668.py
- Classes: TestFromAC_Approve, TestFromAC_Edit, TestFromAC_Delete, TestFromAC_OCC, TestFromAC_MtimeScanCache, TestFromAC_Save, TestFromAC_LenientRead
- Tests per category: happy 28, edge 10, error 15, boundary 3
- Total: 56 tests, all FAIL (collection error — ModuleNotFoundError: No module named 'owlbear_memory.engine')
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1: approve() curated→approved, TransitionError on pending/approved/deleted | test_approve_curated_to_approved_returns_approved_state, test_approve_sets_approved_at_timestamp, test_approve_updates_updated_at, test_approve_persists_to_disk, test_approve_pending_raises_transition_error, test_approve_already_approved_raises_transition_error, test_approve_deleted_raises_transition_error, test_approve_nonexistent_id_raises_not_found_error |
| AC2: edit() transitions and field-update rules | test_edit_pending_with_scope_agents_transitions_to_curated, test_edit_approved_to_curated_clears_approved_at, test_edit_approved_updates_updated_at, test_edit_curated_stays_curated, test_edit_curated_stays_curated_updates_field, test_edit_pending_without_scope_agents_stays_pending, test_edit_pending_without_scope_agents_updates_field, test_edit_deleted_raises_transition_error, test_edit_nonexistent_id_raises_not_found_error, test_edit_persists_field_change_to_disk |
| AC3: delete() hard/soft delete | test_delete_pending_removes_file_from_disk, test_delete_pending_not_in_get_entries_after_hard_delete, test_delete_curated_soft_deletes_state, test_delete_curated_file_still_exists, test_delete_approved_soft_deletes_state, test_delete_curated_updates_updated_at, test_delete_already_deleted_raises_transition_error, test_delete_nonexistent_id_raises_not_found_error, test_delete_soft_persists_to_disk |
| AC4: OCC string comparison, save() has no expected_updated_at | test_approve_wrong_expected_updated_at_raises_concurrency_error, test_edit_wrong_expected_updated_at_raises_concurrency_error, test_delete_wrong_expected_updated_at_raises_concurrency_error, test_occ_check_is_string_comparison, test_approve_correct_expected_updated_at_succeeds, test_edit_correct_expected_updated_at_succeeds, test_delete_correct_expected_updated_at_succeeds, test_save_has_no_expected_updated_at_parameter |
| AC5: MtimeScanCache.has_changed() semantics | test_has_changed_returns_true_on_first_call, test_has_changed_returns_false_on_second_call_same_mtime, test_has_changed_returns_true_after_directory_modified, test_has_changed_false_again_after_second_change_check, test_get_entries_skips_reparse_when_mtime_unchanged |
| AC6: save() pending entry, UUIDv4, ISO 8601 timestamps | test_save_returns_memory_entry, test_save_creates_pending_state, test_save_generates_uuidv4_id, test_save_creates_iso8601_created_at, test_save_created_at_equals_updated_at_on_creation, test_save_writes_file_to_disk, test_save_appears_in_get_entries, test_save_two_calls_produce_unique_ids, test_save_with_scope_agents_stores_them |
| AC7: lenient read, parse_errors, duplicate UUID dedup + warning | test_parse_errors_starts_at_zero, test_unparseable_file_is_skipped, test_unparseable_file_increments_parse_errors, test_valid_file_does_not_increment_parse_errors, test_duplicate_uuid_keeps_later_updated_at, test_duplicate_uuid_logs_warning, test_parse_errors_accumulate_across_reloads, test_mixed_valid_and_invalid_returns_only_valid |

[[2026-05-19T03:26:58+02:00]]
## Builder Notes
- Implementation: added `serve/memory/src/owlbear_memory/engine.py` and updated exports in `serve/memory/src/owlbear_memory/__init__.py`.
- Approach: implemented `MemoryEngine` orchestration over storage primitives with explicit state-machine behavior (`approve`, `edit`, `delete`), OCC checks via exact `updated_at` string match, UUIDv4+ISO timestamp `save`, and `MtimeScanCache`-gated reloads.
- Lenient read behavior: `get_entries()` skips unparseable files, tracks `parse_errors` per reload, and deduplicates duplicate UUIDs by later `updated_at` while logging warnings.
- Task tests (RED->GREEN proof): `tests/test_memory_engine_1668.py` -> 57 passed, 0 failed.
- Coverage: quality-runner reported 98% for `serve/memory/src/owlbear_memory/engine.py` (module target >=90% satisfied).
- Lint: ruff clean for `serve/memory/src/owlbear_memory/engine.py`, `serve/memory/src/owlbear_memory/__init__.py`, and `tests/test_memory_engine_1668.py`.
- Durable baseline check: `tests/test_memory_engine.py` currently fails (6 failures) in legacy `owlbear_mcp_memory` contract expectations unrelated to this task’s `owlbear_memory` package changes; recorded as non-blocking cross-domain pre-existing signal.
- Commit: `7bc7b1f3` (`feat(memory): implement MemoryEngine state machine and OCC (#1668, builder)`).

[[2026-05-19T03:40:10+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL routing: FAIL #1668 -> in-progress | AC7 duplicate resolution compares raw timestamp strings, so valid timezone-aware ISO 8601 timestamps can select the wrong winner.
- AC1-6 mapped cleanly: `MtimeScanCache`, `get_entries()`, `approve()`, `edit()`, `delete()`, and `save()` are implemented in `serve/memory/src/owlbear_memory/engine.py:28,91,105,124,153,176`, with task-local proof in `tests/test_memory_engine_1668.py:89,168,303,397,473,531`. No blocking findings found on those AC lines.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC7 | Duplicate-ID resolution uses raw lexical string ordering (`entry.updated_at > current.updated_at`) even though the memory contract accepts timezone-aware ISO 8601 timestamps and the brief defines `updated_at` as datetime. Two valid timestamps with different offsets can therefore pick the wrong "later" entry. | `serve/memory/src/owlbear_memory/engine.py:76`; `serve/memory/src/owlbear_memory/models.py:91-108`; `serve/memory/README.md:52-54`; `.owlbear/briefs/draft-cockpit-memory-tab/brief.md:95-105` | in-progress |
| 2 | AC7 | Task proof only covers duplicate resolution with same-format `_TS_EARLY` / `_TS_LATE` values, so the suite would false-green the mixed-offset chronology bug above. | `tests/test_memory_engine_1668.py:730-758` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Compare duplicate `updated_at` values chronologically after ISO 8601 parsing instead of raw lexical string order. | `serve/memory/src/owlbear_memory/engine.py` | AC7; `serve/memory/src/owlbear_memory/engine.py:76`; `.owlbear/briefs/draft-cockpit-memory-tab/brief.md:95-105` |
| 2 | builder | Add a task-local regression test proving duplicate-ID dedup keeps the later entry when valid timezone-aware timestamps use different offsets. | `tests/test_memory_engine_1668.py` | AC7; `tests/test_memory_engine_1668.py:730-758`; `serve/memory/src/owlbear_memory/models.py:91-108` |

## Observations
- Builder evidence was otherwise sufficient: scoped tests/lint/coverage were reported, and AC1-6 matched the current implementation and task-local proof surface.
- Challenger cross-check initially raised AC7 wording ambiguity, but the primary brief resolves that ambiguity by typing `updated_at` as `datetime` and restating duplicate handling as “keep the later `updated_at`,” which is stricter than raw lexical ordering.

[[2026-05-19T03:44:42+02:00]]
## Builder Notes
- Files changed: `serve/memory/src/owlbear_memory/engine.py`, `tests/test_memory_engine_1668.py`
- Fix applied: AC7 duplicate-ID dedup now compares `updated_at` values chronologically via ISO-8601 datetime parsing instead of raw lexical string ordering.
- Regression proof added: `test_duplicate_uuid_keeps_later_updated_at_with_timezone_offsets` in `tests/test_memory_engine_1668.py` verifies mixed-offset timestamps keep the true later instant.

Quality-runner evidence (scoped task proof):
- Tests: 58 passed, 0 failed, 0 skipped (`tests/test_memory_engine_1668.py`)
- Lint: clean (`serve/memory/src/owlbear_memory/engine.py`, `tests/test_memory_engine_1668.py`)
- Coverage: `owlbear_memory.engine` 98% (>= 90% gate)

Durable module-level baseline check:
- `tests/test_memory_engine.py`: 8 passed, 6 failed, lint clean.
- Failures are legacy contract/model-mismatch cases in old `TestFromAC_FileEngine` expectations (invalid enum `knowledge`, missing `source_agent` / `scope_agents`) and are unchanged from pre-fix baseline; no additional failures introduced by this AC7 patch.

Commit:
- `dff851cf` — `fix(memory): compare duplicate updated_at chronologically (#1668, builder)`

[[2026-05-19T04:03:15+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL routing: FAIL #1668 -> backlog | AC6 still lacks executable proof that `save()` timestamps are current, not just valid ISO strings.
- Builder evidence was otherwise sufficient and internally consistent: scoped task tests reported 58 passed / 0 failed / 0 skipped, lint clean, and coverage 98% for `owlbear_memory.engine`.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC6 | The task-local save() proof never asserts that `created_at` / `updated_at` are current. A broken implementation returning any fixed valid ISO 8601 timestamp would still pass because the suite only checks ISO parseability and `created_at == updated_at` on creation. | `tests/test_memory_engine_1668.py:582-614`; implementation currently uses `datetime.now(UTC)` in `serve/memory/src/owlbear_memory/engine.py:186-200` and `serve/memory/src/owlbear_memory/engine.py:224-225`, so this is a proof gap rather than a demonstrated code defect. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-queue AC6 with an explicit executable proof requirement that `save()` timestamps fall within a `before` / `after` wall-clock bound, then route the retry with task-local coverage for that clause. | `tests/test_memory_engine_1668.py` | AC6; `tests/test_memory_engine_1668.py:582-614`; second review-cycle loop-breaker |

## Observations
- AC7 is now closed: duplicate-ID dedup compares parsed datetimes chronologically at `serve/memory/src/owlbear_memory/engine.py:76-77` with helper parsing at `serve/memory/src/owlbear_memory/engine.py:227-228`, and the mixed-offset regression test at `tests/test_memory_engine_1668.py:747-765` would fail on the previous lexical-order bug.
- AC4 is PASS-supportable. The challenger’s stale-cache concern is non-blocking in the supported storage model because `get_entries()` reloads on directory mtime changes (`serve/memory/src/owlbear_memory/engine.py:35-43`, `serve/memory/src/owlbear_memory/engine.py:91-94`), and supported writes invalidate that cache path via same-directory temp-file creation plus replace in `serve/memory/src/owlbear_memory/storage.py:63-94`.
- No editor diagnostics were present in `serve/memory/src/owlbear_memory/engine.py`, `serve/memory/src/owlbear_memory/__init__.py`, or `tests/test_memory_engine_1668.py` during review.

[[2026-05-19T04:04:28+02:00]]
## Architecture Re-Review (Cycle 3)

### Context
Second review (cycle 2) returned task to backlog with a single finding: AC6 proof gap — task-local tests only check ISO parseability and `created_at == updated_at`, never asserting timestamps are current. The implementation is correct (`datetime.now(UTC)`) but the test suite would false-green a fixed-timestamp implementation.

### AC6 Refinement
- **Before:** \"...current ISO 8601 timestamps (created_at, updated_at), writes to disk, and returns the created MemoryEntry\"
- **After:** \"...ISO 8601 timestamps (created_at, updated_at) derived from wall-clock time; task-local proof must assert timestamps fall within a before/after UTC bound captured around the save() call\"

This makes the proof obligation explicit and mechanically testable: the test-writer/builder must capture `before = datetime.now(UTC)` / `after = datetime.now(UTC)` around the call and assert `before <= parsed_timestamp <= after`.

### Prior Review Results (unchanged)
All 10 criteria PASS. Failure mode map, proof-bundle (behavioral), and challenge results from cycle 1 remain valid — no architectural change, only proof-obligation tightening on one AC line.

### Verdict: APPROVE
### Action Taken: Refined AC6 to require explicit wall-clock bound assertion for save() timestamps (reviewer finding), advanced to todo

[[2026-05-19T04:07:19+02:00]]
## Test-Writer Notes
- Retry: added 1 test for AC6 reviewer gap (wall-clock bound assertion for save() timestamps).
- Test file: tests/test_memory_engine_1668.py
- New test: `TestFromAC_Save.test_save_timestamps_fall_within_wall_clock_bound` — captures `before`/`after` UTC bound around `save()` call and asserts both `created_at` and `updated_at` fall within that bound.
- All 59 tests PASS against current implementation (implementation uses `datetime.now(UTC)` — correct). No implementation gaps — test-only retry.
- Lint: clean. Commit: e3761e46.
- Builder skip: test-only retry, all tests green.

[[2026-05-19T04:16:38+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1668 hands off to docs | AC mapped to code and evidence sufficient.
- Evidence reviewed first: prior builder proof reported 58 task tests passing, lint clean, and 98% coverage for owlbear_memory.engine; current test-only retry added the AC6 wall-clock bound test, reported 59 task tests passing, and lint clean.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/memory/src/owlbear_memory/engine.py:105 and 117-119 | tests/test_memory_engine_1668.py:93, 132, 140, 148 | PASS |
| AC2 | serve/memory/src/owlbear_memory/engine.py:124, 137, 140 | tests/test_memory_engine_1668.py:172, 185, 238, 264 | PASS |
| AC3 | serve/memory/src/owlbear_memory/engine.py:153, 168, 173 | tests/test_memory_engine_1668.py:307, 328, 347, 365 | PASS |
| AC4 | serve/memory/src/owlbear_memory/engine.py:176, 202-203 | tests/test_memory_engine_1668.py:401, 425 | PASS |
| AC5 | serve/memory/src/owlbear_memory/engine.py:28, 35, 91-94 | tests/test_memory_engine_1668.py:477, 483, 490, 509 | PASS |
| AC6 | serve/memory/src/owlbear_memory/engine.py:176, 188, 193, 196-197, 224-225 | tests/test_memory_engine_1668.py:583, 601, 616, 687, 691, 700, 705-706 | PASS |
| AC7 | serve/memory/src/owlbear_memory/engine.py:58, 67, 76-77, 227 | tests/test_memory_engine_1668.py:732, 752, 769, 790 | PASS |
- Blocking findings: none.

## Observations
- Challenger verdict was reconsider (0.69) on cache freshness and AC6 persistence proof. Not blocking after review:
  - AC4/AC5: the brief couples OCC with directory-mtime caching, and supported writes use temp-file replace in serve/memory/src/owlbear_memory/storage.py:87 and 94, so the implementation matches the intended invalidation model rather than arbitrary in-place external edits.
  - AC6: the cycle-3 refinement required task-local proof that save() timestamps fall within a before/after UTC bound around the save() call. That gap is now closed by tests/test_memory_engine_1668.py:687, 691, 700, 705-706; write-to-disk remains covered by tests/test_memory_engine_1668.py:616 and trusted storage serialization in serve/memory/src/owlbear_memory/storage.py:63.
- Public API exports are present in serve/memory/src/owlbear_memory/__init__.py:5, 14, 17, 20.
- Safety review: engine mutations still route through path containment and symlink guards in serve/memory/src/owlbear_memory/storage.py:24, 32, 65-66, 103-104. No new dependency or credential or PII risk observed.
- No diagnostics were present in serve/memory/src/owlbear_memory/engine.py, serve/memory/src/owlbear_memory/__init__.py, or tests/test_memory_engine_1668.py during review.

[[2026-05-19T04:19:16+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | UPDATED | `serve/memory/README.md` — added `## Engine` section documenting `MemoryEngine` (method table, state machine, OCC, lenient read) and `MtimeScanCache`; updated Usage import example to include `MemoryEngine` |
| 2. External Attribution | N/A | No external sources used; implementation composed from internal patterns |
| 3. Research Doc | N/A | `.owlbear/research/memory-engine-state-machine-occ.md` already linked in task body |
| 4. Deletion Detection | N/A | No files deleted |

### Files Updated
- `serve/memory/README.md` — Engine section added (MemoryEngine + MtimeScanCache), usage example updated

### Commit
- `d5808172` — `docs(memory): document MemoryEngine and MtimeScanCache in README (#1668, doc-writer)`

### Scratch Cleanup
- No scratch files created for this task.

[[2026-05-19T04:26:52+02:00]]
## Audit

### Regression Detection
Quality-runner full suite: 4995 passed, 20 failed, 14 skipped, lint clean.
20 failures are pre-existing in unrelated domains:
- `tests/test_cockpit_view.py` (10): FileNotFoundError — cockpit domain, last touched at 31d0ad7b
- `tests/test_server.py` (7): TypeError NoneType — mcp-kanban domain, last touched at 31d0ad7b
- `tests/test_engine_accessor_migration.py` (3): AssertionError — kanban engine domain, last touched at 31d0ad7b

No memory-domain regressions. Task-scoped tests (58 passed + 1 wall-clock bound = 59) all green per builder/test-writer evidence.

### Intent Verification
Changed files: `serve/memory/src/owlbear_memory/engine.py`, `serve/memory/src/owlbear_memory/__init__.py`, `serve/memory/README.md`, `tests/test_memory_engine_1668.py`. All within memory domain. Implementation matches stated purpose (MemoryEngine orchestration with state machine, OCC, caching). No extraneous scope.

### Architect Quality
Score: 4/5. AC refined from 5→7 lines across 3 arch review cycles incorporating challenger and reviewer findings. Specific, testable, covers edge cases. Minor gap: initial AC missed save() and parse_errors (caught by challenger cycle 1), and lacked explicit proof obligation for timestamp currency (caught by reviewer cycle 2). Architect responded well to feedback in all cases.

### Commit Integrity
All upstream commits present and properly attributed:
- `f984edc6` — test-writer (failing tests)
- `7bc7b1f3` — builder (implementation)
- `dff851cf` — builder (fix for AC7 reviewer finding)
- `e3761e46` — test-writer (AC6 wall-clock bound test)
- `d5808172` — doc-writer (README update)

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| Regression failures | 0 (none caused by task) |
| Intent mismatch | 0 |
| Evidence integrity | 0 |
| Lint violations | 0 |
| AC quality ≤ 3 | 0 (score 4) |
| Missing reviewer evidence | 0 (detailed, 3 cycles) |

### Confidence: 1.00
### Action: ARCHIVE
