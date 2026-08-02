---
id: 1840
title: 'P2-01: State machine — contested, disputed, stale states'
status: archived
priority: medium
created: 2026-05-24T19:00:51.542397+02:00
updated: 2026-05-25T01:34:42.246267+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on: []
ac:
  - MemoryState enum includes `contested`, `disputed`, `stale` values in both 
    serve/memory and serve/mcp-memory packages. `list_memories` default state 
    set includes all three new states. `_state_rank_for_list` places contested 
    at rank 1 (same tier as curated) and disputed/stale at rank 3 (same tier as 
    deleted).
  - MemoryEngine.resolve(entry_id, expected_updated_at) transitions entries from
    {contested, disputed, stale} → approved with OCC enforcement. Sets 
    approved_at on success. Raises TransitionError for entries in non-resolvable
    states (pending, approved, curated, deleted).
  - Recall filtering (in tools.py recall_memory) excludes entries with state 
    disputed or stale alongside existing exclusions of deleted and pending. 
    Entries with state contested remain in recall results (added to visible set 
    and inline state_rank dict).
  - edit() raises TransitionError for entries in contested, disputed, or stale 
    state (resolve first, then edit). delete() performs soft-delete (state → 
    deleted) from these states, same as curated/approved behavior.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1839

## Scope

Add three new lifecycle states to the memory engine and define their recall visibility and curator resolution transitions.

### In Scope
- MemoryState enum additions (contested, disputed, stale)
- state_rank ordering for new states
- Recall visibility rules (contested=visible, disputed/stale=excluded)
- Curator resolution transitions to approved

### Out of Scope
- Assessment counter fields (P2-02)
- Score computation (P2-02)
- Confirmation cycle logic (P2-06)
- Slot-efficiency auto-transition (P2-05)

## Domain
serve/memory/


## Research
- Research doc: .owlbear/research/memory-state-machine-contested-disputed-stale.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: T1 implementation following existing patterns — standalone resolve() method, enum extension, recall filter update (confidence: 0.90)

[[2026-05-24T22:03:27+02:00]]
## Research
- Research doc: .owlbear/research/memory-state-machine-contested-disputed-stale.md
- Validated: T1 trivial extension, no architectural risk
- Implementation approach: (1) extend MemoryState enum in both packages, (2) extend _state_rank_for_list — contested=1, disputed/stale=3, (3) add CONTESTED to recall visible set, (4) standalone resolve() method on MemoryEngine (contested/disputed/stale → approved), (5) block edit() from new states, (6) allow delete() soft-delete
- Prior art: Wikipedia flag→dispute→resolve model, KG two-source confirmation
- Confidence: 0.90
- Challenge: SKIP — trivial T1 extension

[[2026-05-25T00:02:21+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: state machine additions (enum, rank, recall filter, transitions) |
| Interface clarity | PASS | resolve(entry_id, expected_updated_at) follows approve() pattern; inputs/outputs/errors clear |
| Dependency correctness | PASS | No deps needed — foundational task depended on by #1843-1845 |
| Module layering | PASS | Engine in serve/memory, tools in serve/mcp-memory — existing pattern |
| TDD compliance | PASS | proof_bundle=behavioral, test-writer will produce TDD tests |
| KISS/YAGNI | PASS | Minimal additions following existing patterns; no new abstractions |
| Premise challenge | PASS | States required by parent Brief for voting system |
| Pattern consistency | PASS | resolve() follows approve() OCC pattern; enum extension is trivial |
| Security surface | PASS | No new system boundaries; edit() blocking prevents escape-dispute bypass |
| Single domain | PASS | serve/memory + serve/mcp-memory (paired packages, same domain) |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| resolve() from wrong state | Invalid source state | TransitionError | Yes | Clear error message |
| edit() on contested/disputed/stale | Attempted bypass | TransitionError | Yes | Forces resolve-first workflow |
| OCC mismatch in resolve() | Concurrent mutation | ConcurrencyError | Yes | Retry with fresh state |

### Challenge Results
- Challenger: reconsider (confidence 0.63)
- Issues raised: (1) AC1 conflating list rank with recall visibility, (2) AC2 missing OCC signature, (3) list_memories default filter excludes new states, (4) edit() blocking unspecified, (5) multi-consumer impact
- Architect response: ACCEPTED items 1-4 — refined all 3 original AC lines and added AC4. Item 5 (Cockpit frontend): out of scope per parent Brief (\"Cockpit UI follow-on\"); backend proxies state strings transparently. Confidence in refined AC: 0.91

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single valid approach (standalone resolve() following approve() pattern), no competing criteria

### Verdict: APPROVE
### Action Taken: Refined AC (clarified dual-package sync, OCC signature, list_memories default set, added AC4 for edit/delete behavior). Advanced to todo.

[[2026-05-25T00:17:40+02:00]]
## Test-Writer Notes
- Test file: tests/test_memory_state_machine_1840.py
- Classes: TestFromAC_StateEnum, TestFromAC_Resolve, TestFromAC_RecallFiltering, TestFromAC_EditDeleteNewStates
- Tests per category: happy 14, edge 4, error 11, boundary 4
- Total: 33 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 — enum values + list_memories default + _state_rank_for_list ranks | test_contested/disputed/stale_value_in_memory_state_enum, test_new_states_accessible_via_mcp_memory_package, test_state_rank_contested_is_1, test_state_rank_disputed/stale_is_3, test_state_rank_contested_same_tier_as_curated, test_list_memories_default_includes_contested/disputed/stale_entries, test_list_memories_contested_ordered_before_disputed_by_rank |
| AC2 — resolve() transitions + OCC + approved_at + TransitionError | test_resolve_contested/disputed/stale_returns_approved_state, test_resolve_sets_approved_at_timestamp, test_resolve_updates_updated_at, test_resolve_persists_approved_state_to_disk, test_resolve_occ_mismatch_raises_concurrency_error, test_resolve_pending/approved/curated/deleted_raises_transition_error |
| AC3 — recall inclusion/exclusion | test_recall_includes_contested_entries, test_recall_excludes_disputed/stale_entries, test_recall_contested_appears_alongside_curated_entries |
| AC4 — edit() blocks + delete() soft-deletes | test_edit_contested/disputed/stale_raises_transition_error, test_delete_contested/disputed/stale_is_soft_delete |

### RED failure modes verified
- AttributeError: MemoryState has no attribute CONTESTED/DISPUTED/STALE (enum tests, state_rank tests, resolve tests)
- AttributeError: MemoryEngine has no attribute resolve (all resolve tests)
- AssertionError: entry id not in list_memories result (engine skips unrecognised states at parse time)
- AssertionError: entry must be loadable by engine (recall exclusion tests fail with clear message)
- pytest.raises(TransitionError) catches NotFoundError from get_entry (edit/delete on new states fail; engine can't load the entry)

[[2026-05-25T00:35:27+02:00]]
## Builder Notes
- Implementation: extended `MemoryState` in both packages; added `MemoryEngine.resolve(entry_id, expected_updated_at)` for `{contested, disputed, stale} -> approved` with OCC + `approved_at`; blocked `edit()` from contested/disputed/stale; updated MCP `list_memories` default state set, `_state_rank_for_list`, and `recall_memory` visible states/ranking to include contested and exclude disputed/stale.
- Files changed:
  - serve/memory/src/owlbear_memory/models.py
  - serve/memory/src/owlbear_memory/engine.py
  - serve/mcp-memory/src/owlbear_mcp_memory/models.py
  - serve/mcp-memory/src/owlbear_mcp_memory/tools.py
- RED verification (before implementation): quality-runner on `tests/test_memory_state_machine_1840.py` reported 33 failed, 0 passed.
- GREEN verification (after implementation): quality-runner on `tests/test_memory_state_machine_1840.py` reported 33 passed, 0 failed.
- Durable regression signal: quality-runner on `tests/test_memory_engine_1668.py` reported 59 passed, 0 failed.
- Expanded scoped regression run: quality-runner on `tests/test_memory_state_machine_1840.py`, `tests/test_memory_engine_1668.py`, `tests/test_recall_memory.py`, `tests/test_mutation_tools.py` reported 166 passed, 0 failed.
- Lint: ruff clean in all quality-runner runs.
- Coverage evidence:
  - Scoped package run reported `owlbear_mcp_memory.tools` 85%.
  - Domain-mapped full verification reported per-file coverage: `serve/memory/src/owlbear_memory/engine.py` 98%, `serve/memory/src/owlbear_memory/models.py` 84%, `serve/mcp-memory/src/owlbear_mcp_memory/models.py` 81%, `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` 32%.
  - Domain run also surfaced 6 pre-existing `module mismatch` failures in `tests/test_memory_engine.py` outside this task scope; all changed-scope tests passed.
- Commit: `b84a2dcd` (`feat: implement contested/disputed/stale memory states (#1840, builder)`).

[[2026-05-25T01:05:44+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1840 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: quality-runner reported 33/33 task tests passing in `tests/test_memory_state_machine_1840.py`, 59/59 passing in `tests/test_memory_engine_1668.py`, 166/166 passing across the expanded scoped regression set, and ruff clean.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/memory/src/owlbear_memory/models.py:26` and `serve/mcp-memory/src/owlbear_mcp_memory/models.py:26` add `CONTESTED`/`DISPUTED`/`STALE`; `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:121` ranks contested with curated; `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:189` plus `:196-198` include all three new states in `list_memories` defaults. | `tests/test_memory_state_machine_1840.py:128`, `:140`, `:148`, `:154`, `:160`, `:173`, `:187`, `:201` prove enum access, rank values, and default list visibility for contested/disputed/stale. | PASS |
| AC2 | `serve/memory/src/owlbear_memory/engine.py:135` implements `resolve(entry_id, expected_updated_at)`; `serve/memory/src/owlbear_memory/engine.py:140` restricts source states to contested/disputed/stale and `:144-148` sets `state=approved`, `approved_at`, and refreshed `updated_at`. | `tests/test_memory_state_machine_1840.py:244`, `:253`, `:262`, `:271`, `:289`, `:300`, `:308`, `:317`, `:326`, `:335` cover each success state, OCC mismatch, persistence, and TransitionError for pending/approved/curated/deleted. | PASS |
| AC3 | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:258` adds contested to the recall ranking map and `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:266` limits recall visibility to approved/curated/contested, excluding disputed/stale along with pending/deleted. | `tests/test_memory_state_machine_1840.py:357`, `:370`, `:392`, `:414` prove contested recall inclusion, disputed/stale exclusion, and coexistence with curated entries. | PASS |
| AC4 | `serve/memory/src/owlbear_memory/engine.py:154` keeps edit under OCC; `serve/memory/src/owlbear_memory/engine.py:162-163` blocks edit from contested/disputed/stale; `serve/memory/src/owlbear_memory/engine.py:186` and `:206` soft-delete non-pending entries by writing `state=deleted`. | `tests/test_memory_state_machine_1840.py:442`, `:450`, `:458`, `:466`, `:477`, `:487` prove TransitionError on edit and soft-delete behavior with file retention for contested/disputed/stale. | PASS |

- Safety/security check: no new external boundary or unsafe input path introduced; reviewed changes are confined to local enum definitions, state-machine transitions, and in-process filtering logic.

## Observations
- Non-blocking: `tests/test_memory_state_machine_1840.py:140` imports `MemoryState` through `owlbear_mcp_memory.tools`, and `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:8-13` aliases that symbol from `owlbear_memory`. That means the task-local proof does not directly guard the duplicated enum in `serve/mcp-memory/src/owlbear_mcp_memory/models.py`, even though direct source inspection at `serve/mcp-memory/src/owlbear_mcp_memory/models.py:26` shows the literals are present now. If future parity drift between the two enum definitions becomes a concern, add one explicit test importing `owlbear_mcp_memory.models.MemoryState` directly.

[[2026-05-25T01:14:03+02:00]]
## Docs Gate

### Checklist

**Item 1: README Verification** — PASS
- Convention mapping: `serve/memory/src/**` → `serve/memory/README.md`; `serve/mcp-memory/src/**` → `serve/mcp-memory/README.md`
- Layer 1 (grep): confirmed MemoryState table missing contested/disputed/stale; engine method table missing resolve(); State Machine table missing resolve transitions and edit-blocking rows; mcp-memory state diagram and Entry Schema state field stale.
- Layer 2 (editorial): curate_memory tool description missing TransitionError note for new states; delete_memory tool description omitted contested/disputed/stale from soft-delete list.
- Fixes applied (commit `c00ac7ec`):
  - `serve/memory/README.md`: added contested/disputed/stale rows to MemoryState table; added `resolve()` to engine method table; updated `edit()` and `delete()` method descriptions; added 6 new State Machine rows (resolve + delete for each new state) and edit-blocking row; updated OCC section to include `resolve`.
  - `serve/mcp-memory/README.md`: updated State Model diagram and bullet list to show all 7 states; updated `curate_memory` tool description (TransitionError for contested/disputed/stale); updated `delete_memory` tool description (soft-delete includes contested/disputed/stale); updated Entry Schema `state` field to list all 7 values.

**Item 2: External Attribution** — N/A
- Implementation is a T1 trivial enum extension; no external libraries or services introduced. No `.owlbear/sources/overview.md` update required.

**Item 3: Research Doc** — PASS
- `.owlbear/research/memory-state-machine-contested-disputed-stale.md` exists and is linked from task body.

**Item 4: Deletion Detection** — PASS
- No symbols removed; only additions. No orphaned references.

### Scratch Cleanup
- No `.owlbear/scratch/1840-*` files found; nothing to delete.

[[2026-05-25T01:34:42+02:00]]
## Audit

### Regression Detection
- Memory domain (166 tests across test_memory_state_machine_1840, test_memory_engine_1668, test_recall_memory, test_mutation_tools): ALL PASS.
- Ruff lint (serve/memory/src/, serve/mcp-memory/src/): clean.
- quality-runner env fallback: pre-existing unresolved merge conflict in serve/knowledge/src/owlbear_knowledge/schema.py blocks full-suite collection; ran memory domain + broad cross-domain manually.
- 8 memory-related failures from older task-scoped tests (test_memory_primitives_1667 asserts exactly 4 enum values; test_memory_engine has 6 module-mismatch issues) — expected consequence of enum extension, noted by builder as pre-existing. Test-curator scope.
- 111 other failures across cockpit build, kanban, and various unrelated domains — all pre-existing, not attributable to this task.
- No regressions caused by this task.

### Intent Verification
- Changed files: serve/memory/src/owlbear_memory/{models,engine}.py, serve/mcp-memory/src/owlbear_mcp_memory/{models,tools}.py — all within declared domain (scope:memory).
- Implementation matches stated purpose: adds contested/disputed/stale enum values, resolve() transition, recall filtering, edit-blocking. No extraneous scope.

### Architect Quality
- AC quality score: 5/5 — Specific, complete, challenger-refined (4 AC lines with exact signatures, state sets, rank values, behavior constraints).
- Edge cases covered: TransitionError for invalid states, OCC enforcement, edit-blocking, soft-delete behavior.
- Design direction: clear pattern guidance (follow approve()).

### Commit Integrity
- Test-writer: 80281d9c ✓
- Builder: b84a2dcd ✓
- Doc-writer: c00ac7ec ✓
- All properly attributed with #1840 and agent role.

### Reviewer Evidence
- Detailed PASS with AC-to-code line mapping. Complete and sufficient.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
