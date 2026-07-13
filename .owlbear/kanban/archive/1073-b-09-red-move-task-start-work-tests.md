---
id: 1073
title: 'B-09: RED — move_task + start_work tests'
status: archived
priority: medium
created: 2026-04-21T10:49:15.724135+00:00
updated: 2026-04-25T12:31:32.543833+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1072
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.6, §1.7, §3.1, §3.2, §3.4, §4
Module: `serve/kanban/tests/test_engine_move_claim.py`

Test AgentView.move_task and AgentView.start_work. Covers status transitions, archival validation matrix, predicate on destination, claim semantics (lazy-release on expired, blocked/archived not claimable), skip-transition guidance.

## Acceptance Criteria

- [ ] AC4: `move_task(id, "archived")` without `archival_reason` → ValidationError(ERR_ARCHIVAL_REASON_REQUIRED)
- [ ] AC5: `move_task(id, "archived", "completed")` from non-terminal → ValidationError(ERR_COMPLETED_REQUIRES_DONE)
- [ ] AC7: `move_task(id, "archived", "deprecated")` empty refs → ValidationError(ERR_ARCHIVAL_REFS_REQUIRED)
- [ ] AC8: `move_task(id, "archived", "dropped", refs=[42])` → ValidationError(ERR_ARCHIVAL_REFS_FORBIDDEN)
- [ ] AC9: Invalid `archival_reason` enum → ValidationError(ERR_ARCHIVAL_REASON_INVALID)
- [ ] AC26: `move_task(..., archival_refs=[99999])` → ValidationError(ERR_ARCHIVAL_REF_MISSING)
- [ ] AC-NEW-5: Move skipping >1 status position emits skip-warning in guidance
- [ ] AC-NEW-16: move_task/start_work on missing id → NotFoundError(ERR_NOT_FOUND)
- [ ] Invalid `status` enum → ValidationError(ERR_INVALID_STATUS) (D49 — no transition-forbidden code)
- [ ] start_work on already-claimed task → ConcurrencyError(ERR_ALREADY_CLAIMED)
- [ ] start_work on archived task → ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE)
- [ ] start_work on blocked task → ValidationError(ERR_BLOCKED_NOT_CLAIMABLE)
- [ ] start_work on expired claim → lazy-release + re-claim (D18+D36)
- [ ] D15: write-time predicate on destination status fires; failure → ERR_PREDICATE_FAILED, transition NOT applied (D41)
- [ ] Archive clears claim atomically (D17)
- [ ] `archival_reason` set when `status != "archived"` → ERR_ARCHIVAL_FIELDS_FORBIDDEN
- [ ] All tests fail (RED phase)
[[2026-04-25]]
## Test-Writer Notes

**Test file:** `serve/kanban/tests/test_engine_move_claim.py`

**Classes:**
- `TestFromAC_MoveTask` — 10 tests (archival validation, predicate-on-destination, claim-clearing)
- `TestFromAC_StartWork` — 2 tests (blocked/archived claim guards)

**Categories:**
| Category | Count |
|----------|-------|
| Error paths (wrong/missing validation) | 9 |
| Behavioral contract (atomicity, no-move on failure) | 3 |
| **Total** | **12** |

**Pytest result:** `12 failed, 0 passed` ✓ (RED)

**AC coverage table:**

| AC | Test | Testable as RED? |
|----|------|-----------------|
| AC4 | `test_archive_without_reason_raises_archival_reason_required` | ✓ FAIL |
| AC5 | `test_archive_completed_from_non_terminal_raises_completed_requires_done` | ✓ FAIL |
| AC7 | `test_archive_deprecated_without_refs_raises_archival_refs_required` | ✓ FAIL |
| AC8 | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` | ✓ FAIL |
| AC9 | `test_archive_invalid_reason_raises_archival_reason_invalid` | ✓ FAIL |
| AC26 | `test_archive_with_missing_ref_raises_archival_ref_missing` | ✓ FAIL |
| ERR_ARCHIVAL_FIELDS_FORBIDDEN | `test_archival_reason_on_active_status_raises_fields_forbidden` | ✓ FAIL |
| D15 | `test_predicate_on_destination_fails_raises_predicate_failed` | ✓ FAIL |
| D41 | `test_predicate_on_destination_fails_task_not_moved` | ✓ FAIL |
| D17 | `test_archive_claimed_task_clears_claim` | ✓ FAIL |
| ERR_BLOCKED_NOT_CLAIMABLE | `test_blocked_task_raises_blocked_not_claimable` | ✓ FAIL |
| ERR_ARCHIVED_NOT_CLAIMABLE | `test_archived_task_raises_archived_not_claimable` | ✓ FAIL |
| AC-NEW-5 (skip warning) | — | Not testable as RED: `_skip_transition_guidance` already fires for delta > 1 |
| AC-NEW-16 (missing id) | — | Not testable as RED: FileNotFoundError → NotFoundError already implemented |
| Invalid status enum | — | Not testable as RED: engine ValueError → ERR_INVALID_STATUS already implemented |
| ERR_ALREADY_CLAIMED | — | Not testable as RED: "already claimed" substr check already fires |
| D18+D36 (expired claim re-claim) | — | Not testable as RED: engine.claim_task expiry logic already implemented |

**Why tests fail (root causes):**
- `move_task` stubs archival fields: `_ = (archival_reason, archival_refs)` — no validation
- `move_task` performs no predicate check on destination status
- `engine.move_task` does not clear `claimed_at` on archive (D17 gap)
- `start_work` maps blocked ValueError to `ERR_INVALID_STATUS` (not `ERR_BLOCKED_NOT_CLAIMABLE`)
- `start_work` maps archived FileNotFoundError to `NotFoundError(ERR_NOT_FOUND)` (not `ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE)`)
[[2026-04-25]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py)
- Fixes applied:
  - Added archive-time claim clearing in engine `move_task` (clears `claimed_at` and `claimed_by` before archive write/move).
  - Implemented `AgentView.move_task` archival validation matrix (`ERR_ARCHIVAL_REASON_REQUIRED`, `ERR_COMPLETED_REQUIRES_DONE`, `ERR_ARCHIVAL_REFS_REQUIRED`, `ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_ARCHIVAL_REASON_INVALID`, `ERR_ARCHIVAL_REF_MISSING`, `ERR_ARCHIVAL_FIELDS_FORBIDDEN`).
  - Added destination-status predicate enforcement for `move_task` (`ERR_PREDICATE_FAILED`) before transition write.
  - Updated `AgentView.start_work` mappings: archived task -> `ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE)` and blocked claim -> `ValidationError(ERR_BLOCKED_NOT_CLAIMABLE)` while preserving existing already-claimed -> `ConcurrencyError(ERR_ALREADY_CLAIMED)`.
- Tests: 12 TestFromAC tests passed in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py)
- Coverage: quality-runner scoped report for `owlbear_kanban.engine` = 31%
- Ruff: clean on touched source + task test file
- Evidence summary: RED verified first (12/12 failing), then GREEN verified (12/12 passing, 0 failures), lint clean.
- Commit: `33cb8c3a` (`feat: implement move/start_work guards for task #1073 (builder)`)
- Reflection:
  - Main sink was matching strict archival error-code mapping without regressing existing move behavior.
  - Extracting helper validators was necessary to satisfy ruff complexity gates after adding required validations.
  - Destination-predicate enforcement was added pre-write to preserve D41 (no transition on predicate failure).
  - Engine-level archive claim clearing was kept minimal to avoid side effects beyond D17.
[[2026-04-25]]
## Review Evidence
### Test Results
- pytest: 12 passed, 0 failed in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py)

### Lint
- clean

### Coverage
- `owlbear_kanban.engine`: 29% module coverage (32% overall) from an independent scoped quality-runner run; below the 90% review gate.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC-NEW-5 | No task-owned test. The file explicitly omits it at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L36); implementation exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1591-L1611) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2505-L2509). | MISSING |
| AC-NEW-16 | No task-owned test. Not-found wrapping exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1613-L1617), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2472-L2503), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2512-L2536). | MISSING |
| Invalid `status` enum | No task-owned test. Implementation exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1044-L1057) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2502-L2503). | MISSING |
| start_work on already-claimed task | No task-owned test. Implementation exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1097-L1127) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2525-L2529). | MISSING |
| start_work on expired claim | No task-owned test. Re-claim path exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1097-L1134). | MISSING |
| D17 | The only success-path archive assertion is [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L340-L355); it checks returned `claimed_at` only and does not prove persisted archive state or failure-path atomicity. | LAX |
| All tests fail (RED phase) | Present only as prior task-body prose from the test-writer; not independently replayable after GREEN. | MISSING |

#### Security Review
- No hardcoded secrets, injection, path traversal, unsafe deserialization, or new dependency risk found in the scoped move/claim changes at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1697-L1779) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2472-L2536).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Covered `TestFromAC_*` assertions in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L417) | No weakened/removed assertions were provable from the current file; the failure mode is omitted literal AC coverage in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L36). | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most covered tests assert exact error codes, but D41 suppresses every exception at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L322-L338) and D17 checks only the returned field at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L340-L355). |
| Negative/error-path coverage | WEAK | Five literal AC paths are omitted at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L36). |
| Manual mutation reasoning | WEAK | Removing skip guidance at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2505-L2509) or the already-claimed mapping at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2525-L2529) would not fail this suite. |
| Test independence | STRONG | Each test builds an isolated board/task set at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L121-L170). |
| Descriptive names | STRONG | The test names state the contract directly across [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L417). |

#### Data Safety
- FAIL: `AgentView.move_task` validates `archival_reason` and `archival_refs` at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2479-L2489) but then drops them by calling `self.engine.move_task(str(task_id), status)` at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2499). `write_task` persists those canonical fields at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L355-L411), and downstream archive filters/dep-status readers consume them at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1783-L1900) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1934-L2014). Successful archives can therefore lose validated metadata.
- FAIL: archive move is not atomic on `_move_file` failure. `engine.move_task` writes the cleared-claim record before moving the file at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1068-L1077), but rollback only wraps later `_emit_event` failures at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1086-L1092).

#### Implementation-Aware Gaps
- No task-owned test proves that a successful archive persists `archival_reason` or `archival_refs`; the only success-path archive assertion is [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L340-L355).
- No task-owned tests cover AC-NEW-5, AC-NEW-16, invalid status, already-claimed, or expired-claim paths.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The task-owned test module still describes itself as RED and narrates old broken behavior at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L1-L39). That is not the main failure, but it is stale review context.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC4 | Exact `ERR_ARCHIVAL_REASON_REQUIRED` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L207); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1708-L1712). | `test_archive_without_reason_raises_archival_reason_required` | PASS |
| AC5 | Exact `ERR_COMPLETED_REQUIRES_DONE` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L209-L223); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1737-L1741). | `test_archive_completed_from_non_terminal_raises_completed_requires_done` | PASS |
| AC7 | Exact `ERR_ARCHIVAL_REFS_REQUIRED` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L225-L239); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1721-L1727). | `test_archive_deprecated_without_refs_raises_archival_refs_required` | PASS |
| AC8 | Exact `ERR_ARCHIVAL_REFS_FORBIDDEN` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L241-L255); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1729-L1735). | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` | PASS |
| AC9 | Exact `ERR_ARCHIVAL_REASON_INVALID` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L257-L271); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1713-L1719). | `test_archive_invalid_reason_raises_archival_reason_invalid` | PASS |
| AC26 | Exact `ERR_ARCHIVAL_REF_MISSING` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L273-L288); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1742-L1747). | `test_archive_with_missing_ref_raises_archival_ref_missing` | PASS |
| AC-NEW-5 | Skip guidance is implemented at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1591-L1611) and returned at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2505-L2509), but the task file omits it at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L36). | none | FAIL |
| AC-NEW-16 | Not-found wrapping exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1613-L1617), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2472-L2503), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2512-L2536), but the task file omits it. | none | FAIL |
| Invalid `status` enum | Error wrapping exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1044-L1057) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2502-L2503), but the task file omits it. | none | FAIL |
| start_work on already-claimed task | Live-claim rejection exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1097-L1127) and is mapped at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2525-L2529), but the task file omits it. | none | FAIL |
| start_work on archived task | Exact `ERR_ARCHIVED_NOT_CLAIMABLE` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L398-L417); guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2513-L2520). | `test_archived_task_raises_archived_not_claimable` | PASS |
| start_work on blocked task | Exact `ERR_BLOCKED_NOT_CLAIMABLE` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L378-L396); mapping at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2530-L2534). | `test_blocked_task_raises_blocked_not_claimable` | PASS |
| start_work on expired claim | Expiry/re-claim path exists at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1116-L1134), but the task file omits it. | none | FAIL |
| D15 | Exact `ERR_PREDICATE_FAILED` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L306-L320); predicate validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1757-L1779). | `test_predicate_on_destination_fails_raises_predicate_failed` | PASS |
| D41 | Status remains `in-progress` at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L322-L338); pre-write validation happens before `engine.move_task` call at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2491-L2499). | `test_predicate_on_destination_fails_task_not_moved` | PASS |
| Archive clears claim atomically (D17) | Success path clears claim before archive write at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1068-L1077), but `archival_reason`/`archival_refs` are dropped at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2499) and `_move_file` failure is not rolled back at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1086-L1092). | `test_archive_claimed_task_clears_claim` | FAIL |
| `archival_reason` set when `status != "archived"` | Exact `ERR_ARCHIVAL_FIELDS_FORBIDDEN` assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L290-L304); validator at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1750-L1755). | `test_archival_reason_on_active_status_raises_fields_forbidden` | PASS |
| All tests fail (RED phase) | Only prior task-body prose exists; no independently replayable evidence remains after GREEN. | none | FAIL |

### Deductions
- Implementation defect: successful archive drops validated archival metadata.
- D17 atomicity is not satisfied on `_move_file` failure.
- Five literal AC branches remain untested in the task-owned suite.
- Touched module coverage is 29%.
- RED-phase evidence is prose-only at review time.

### Confidence: 0.37
### Verdict: FAIL
### Action: reject to `in-progress` because this is both an implementation issue and a test-proof gap.
[[2026-04-25]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py.
- Fixes applied:
  - Extended `KanbanEngine.move_task` to accept/pass archive metadata (`archival_reason`, `archival_refs`) and persist it when archiving.
  - Updated `AgentView.move_task` to forward `archival_reason` and `archival_refs` into engine transition instead of dropping validated values.
  - Added archive file-move rollback guard in `KanbanEngine.move_task`: if `_move_file` fails after write, restore original task record before re-raising.
- Tests: 52 passed, 0 failed
  - serve/kanban/tests/test_engine_move_claim.py
  - serve/kanban/tests/test_engine_atomicity_1104.py
  - serve/kanban/tests/test_engine_archived_edit_1120.py
- Coverage: `owlbear_kanban.engine` 49% in scoped quality-runner verification.
- Ruff: clean on touched source + task-owned test path.
- Evidence summary: quality-runner scoped run reported pytest exit=0 and ruff exit=0 after fix.
- Commit: 9b4fcc0a (`fix: persist archive metadata and rollback archive move (#1073, builder)`).
- Reflection:
  - The key risk was archive metadata validation being detached from persistence due to dropped kwargs at the engine boundary.
  - The critical safety gap was non-atomic behavior on archive move I/O failure; rollback now covers this failure point.
  - Keeping the change in a single file avoided side effects and preserved existing API call sites.
  - Coverage remains module-wide constrained because `owlbear_kanban.engine` is large; targeted behavioral suites were run for regression confidence.
[[2026-04-25]]
## Review Evidence
### Test Results
- Independent quality-runner run on [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py), [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py), and [serve/kanban/tests/test_engine_archived_edit_1120.py](serve/kanban/tests/test_engine_archived_edit_1120.py): 52 passed, 0 failed.

### Lint
- Clean on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) plus the three scoped test files.

### Coverage
- quality-runner reported 49 percent coverage for owlbear_kanban.engine. That is below the 90 percent review gate for the touched module.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would fail if AC violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC4 archive without reason | [AC4 test](serve/kanban/tests/test_engine_move_claim.py#L195-L207) | Yes | COVERED |
| AC5 completed archive from non-terminal | [AC5 test](serve/kanban/tests/test_engine_move_claim.py#L209-L223) | Yes | COVERED |
| AC7 deprecated archive without refs | [AC7 test](serve/kanban/tests/test_engine_move_claim.py#L225-L239) | Yes | COVERED |
| AC8 dropped archive with refs | [AC8 test](serve/kanban/tests/test_engine_move_claim.py#L241-L255) | Yes | COVERED |
| AC9 invalid archival reason enum | [AC9 test](serve/kanban/tests/test_engine_move_claim.py#L257-L271) | Yes | COVERED |
| AC26 archival ref missing | [AC26 test](serve/kanban/tests/test_engine_move_claim.py#L273-L288) | Yes | COVERED |
| AC-NEW-5 multi-column skip guidance | None in the task-owned suite. Broader coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2191-L2197), but this task file explicitly omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | No | MISSING |
| AC-NEW-16 missing id returns ERR_NOT_FOUND | None in the task-owned suite. Broader coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2199-L2202) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2230-L2232), but this task file explicitly omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | No | MISSING |
| Invalid status enum returns ERR_INVALID_STATUS | None in the task-owned suite. Broader coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2205-L2209), but this task file explicitly omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | No | MISSING |
| start_work already claimed returns ERR_ALREADY_CLAIMED | None in the task-owned suite. Broader coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2235-L2244), but this task file explicitly omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | No | MISSING |
| start_work archived returns ERR_ARCHIVED_NOT_CLAIMABLE | [archived start_work test](serve/kanban/tests/test_engine_move_claim.py#L398-L417) | Yes | COVERED |
| start_work blocked returns ERR_BLOCKED_NOT_CLAIMABLE | [blocked start_work test](serve/kanban/tests/test_engine_move_claim.py#L378-L396) | Yes | COVERED |
| start_work expired claim re-claims lazily | None in the task-owned suite. Broader engine-level coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L1158-L1163), but this task file explicitly omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | No | MISSING |
| D15 destination predicate failure returns ERR_PREDICATE_FAILED | [predicate failure code test](serve/kanban/tests/test_engine_move_claim.py#L306-L320) | Yes | COVERED |
| D41 destination predicate failure does not move the task | [predicate no-move test](serve/kanban/tests/test_engine_move_claim.py#L322-L338) | Yes | COVERED |
| D17 archive clears claim atomically | [D17 task-owned test](serve/kanban/tests/test_engine_move_claim.py#L340-L355) | No for the full AC. The task-owned test stops at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L355), while the archive implementation persists and moves the file in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1080-L1094). | LAX |
| archival fields forbidden on active status | [archival-fields-forbidden test](serve/kanban/tests/test_engine_move_claim.py#L290-L304) | Yes | COVERED |
| All tests fail in RED phase | No executable artifact in the current snapshot. The current independent run is green, and the only current evidence is prose in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | No | MISSING |

#### Security Review
- No scoped security issues found in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1080-L1094) or [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2515-L2556).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned TestFromAC assertions in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L417) | No weakened or removed assertions are visible in the current snapshot. The failure is omitted AC coverage in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact error-code assertions exist in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L320), but D17 only checks returned claimed_at at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L355). |
| Negative and error-path coverage | WEAK | The task-owned suite explicitly omits skip guidance, missing-id, invalid-status, already-claimed, and expired-claim paths in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). |
| Manual mutation reasoning | WEAK | Removing the guidance emission in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2526), changing the already-claimed translation in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2546-L2556), or relying only on the broader claim-expiry proof in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L1158-L1163) would not fail any task-owned TestFromAC case. |
| Test independence | STRONG | The scoped suites build isolated tmp_path boards and fixtures rather than sharing mutable state. |
| Descriptive names | STRONG | The task-owned test names in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L417) state the contract directly. |

#### Data Safety
- No live data-safety defect remains in the scoped move/start_work implementation. The wrapper now forwards archival metadata in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2515-L2519), the engine persists it and clears both claim fields in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1080-L1088), and the move helper is rename-based in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L348-L371).

#### Implementation-Aware Gaps
- No task-owned test proves multi-column guidance, missing-id mapping, invalid-status mapping, already-claimed mapping, or expired-claim re-claim. The only coverage I found for those paths is in broader suites at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2191-L2244) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L1158-L1163).
- D17 is only partially proven. The task-owned D17 test stops at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L355), while the archive implementation performs a write then move in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1080-L1094).
- The only separate archive rollback regression I found is [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py#L213-L236). That covers later emit failure, not task-owned archive-file persistence.
- Touched-module coverage is 49 percent, below gate.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- The task-owned test file still states that several literal AC lines are not testable as RED in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). That conflicts with the current task body, which still assigns those lines to this task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC4 archive without reason | Exact ERR_ARCHIVAL_REASON_REQUIRED assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L207). | [AC4 test](serve/kanban/tests/test_engine_move_claim.py#L195-L207) | PASS |
| AC5 completed archive from non-terminal | Exact ERR_COMPLETED_REQUIRES_DONE assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L209-L223). | [AC5 test](serve/kanban/tests/test_engine_move_claim.py#L209-L223) | PASS |
| AC7 deprecated archive without refs | Exact ERR_ARCHIVAL_REFS_REQUIRED assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L225-L239). | [AC7 test](serve/kanban/tests/test_engine_move_claim.py#L225-L239) | PASS |
| AC8 dropped archive with refs | Exact ERR_ARCHIVAL_REFS_FORBIDDEN assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L241-L255). | [AC8 test](serve/kanban/tests/test_engine_move_claim.py#L241-L255) | PASS |
| AC9 invalid archival reason enum | Exact ERR_ARCHIVAL_REASON_INVALID assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L257-L271). | [AC9 test](serve/kanban/tests/test_engine_move_claim.py#L257-L271) | PASS |
| AC26 archival ref missing | Exact ERR_ARCHIVAL_REF_MISSING assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L273-L288). | [AC26 test](serve/kanban/tests/test_engine_move_claim.py#L273-L288) | PASS |
| AC-NEW-5 multi-column skip guidance | Broader repo coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2191-L2197), but the task-owned suite omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | none | FAIL |
| AC-NEW-16 missing id returns ERR_NOT_FOUND | Broader repo coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2199-L2202) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2230-L2232), but the task-owned suite omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | none | FAIL |
| Invalid status enum returns ERR_INVALID_STATUS | Broader repo coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2205-L2209), but the task-owned suite omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | none | FAIL |
| start_work already claimed returns ERR_ALREADY_CLAIMED | Broader repo coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2235-L2244), but the task-owned suite omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | none | FAIL |
| start_work archived returns ERR_ARCHIVED_NOT_CLAIMABLE | Exact ValidationError code assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L398-L417). | [archived start_work test](serve/kanban/tests/test_engine_move_claim.py#L398-L417) | PASS |
| start_work blocked returns ERR_BLOCKED_NOT_CLAIMABLE | Exact ValidationError code assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L378-L396). | [blocked start_work test](serve/kanban/tests/test_engine_move_claim.py#L378-L396) | PASS |
| start_work expired claim re-claims lazily | Broader engine-level coverage exists in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L1158-L1163), but the task-owned suite omits it in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | none | FAIL |
| D15 destination predicate failure returns ERR_PREDICATE_FAILED | Exact code assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L306-L320). | [predicate failure code test](serve/kanban/tests/test_engine_move_claim.py#L306-L320) | PASS |
| D41 destination predicate failure does not move the task | Exact unchanged-status assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L322-L338). | [predicate no-move test](serve/kanban/tests/test_engine_move_claim.py#L322-L338) | PASS |
| D17 archive clears claim atomically | The implementation now clears claim fields before write and move in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1080-L1094), but the task-owned proof only checks returned claimed_at at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L355). | [D17 task-owned test](serve/kanban/tests/test_engine_move_claim.py#L340-L355) | FAIL |
| archival fields forbidden on active status | Exact ERR_ARCHIVAL_FIELDS_FORBIDDEN assertion in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L290-L304). | [archival-fields-forbidden test](serve/kanban/tests/test_engine_move_claim.py#L290-L304) | PASS |
| All tests fail in RED phase | The current independent run is green. No executable RED artifact remains in the current snapshot beyond prose in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L27-L35). | none | FAIL |

### Deductions
- Six literal AC lines remain missing from the task-owned TestFromAC coverage even though broader suites cover some of them elsewhere.
- D17 is only partially proven in the task-owned suite.
- owlbear_kanban.engine coverage is 49 percent.

### Confidence: 0.56
### Verdict: FAIL
### Action: reject to todo because the implementation now appears live-correct, but the task still fails on task-owned AC proof and coverage rather than a current code defect.
[[2026-04-25]]
## Test-Writer Notes

**Test file:** `serve/kanban/tests/test_engine_move_claim.py`

**Retry cycle:** Reviewer cited 5 missing AC lines and 1 LAX test (D17). Added 7 new tests to existing `TestFromAC_` classes.

**Classes:**
- `TestFromAC_MoveTask` — 14 tests (10 original + 4 new)
- `TestFromAC_StartWork` — 5 tests (2 original + 3 new)

**New tests added (covering previously-missing AC lines):**
| AC | New Test | Verdict |
|----|----------|---------|
| D17 (stronger) | `test_archive_cleared_claim_persisted_in_archive_file` | Re-reads from fresh engine — proves disk persistence |
| AC-NEW-5 | `test_move_skipping_two_columns_emits_skip_guidance` | Asserts non-empty guidance with "skip" string |
| AC-NEW-16 (move) | `test_move_missing_task_raises_not_found` | NotFoundError(ERR_NOT_FOUND) |
| Invalid status | `test_move_invalid_status_raises_invalid_status` | ValidationError(ERR_INVALID_STATUS) |
| AC-NEW-16 (start) | `test_start_work_missing_task_raises_not_found` | NotFoundError(ERR_NOT_FOUND) |
| ERR_ALREADY_CLAIMED | `test_start_work_already_claimed_raises_already_claimed` | ConcurrencyError(ERR_ALREADY_CLAIMED) |
| D18+D36 | `test_start_work_expired_claim_allows_reclaim` | claimed_at is not None after re-claim |

**Total:** 19 tests, all PASS (implementation is live-correct; retry adds task-owned proof)
**ruff:** clean
**Commit:** `a830bf38`
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes in this builder pass.
- Files changed: none.
- Tests: 86 passed, 0 failed (scoped regression sweep)
  - serve/kanban/tests/test_engine_move_claim.py
  - serve/kanban/tests/test_engine_atomicity_1104.py
  - serve/kanban/tests/test_engine_archived_edit_1120.py
- Lint: ruff clean on touched scope (`serve/kanban/src/owlbear_kanban/engine.py` + scoped tests).
- Coverage: `owlbear_kanban.engine` = 51% (613/1206) from independent quality-runner verification.
- Evidence summary:
  - quality-runner scoped task run: 19 passed, lint clean, engine coverage 32%.
  - quality-runner targeted regression run: 86 passed, lint clean, engine coverage 51%.
- Fixes applied: none (current implementation already satisfies task-owned behavior tests).
- Rejection reason: pipeline GREEN gate requires >=90% coverage on touched module(s); current module coverage remains below gate without additional test expansion.
- Test-writer request:
  - Add/expand task-owned coverage proving remaining move/start_work branches needed to raise module coverage for this task gate, or
  - split coverage obligation into a dedicated test-curation task if 90% on `owlbear_kanban.engine` is not intended for this scoped task.
[[2026-04-25]]
## Test-Writer Notes

**Retry cycle — coverage gate pass-through**

All AC lines now have task-owned tests (added in previous retry). This retry pass addresses the remaining issue cited by the builder: 90% coverage gate on `owlbear_kanban.engine`.

**Assessment:** The 90% gate on a 1,206-statement module is a module-wide structural concern. This task covers `move_task` and `start_work` only. The 19 task-owned tests reach 32% engine coverage in isolation and ~51% in the full suite. Reaching 90% would require covering ~470 additional statements across unrelated engine methods — beyond this task's AC scope.

**Action:** Pass through per retry-cycle protocol (quality/coverage concern, not missing AC tests). Created follow-up task #1123 (TEST-CURATION: raise owlbear_kanban.engine coverage to 90%) to track the remaining coverage obligation.

**Test file:** `serve/kanban/tests/test_engine_move_claim.py`

**Classes:**
- `TestFromAC_MoveTask` — 14 tests
- `TestFromAC_StartWork` — 5 tests

**Total:** 19 tests, all PASS (implementation live-correct; all AC lines covered)

**AC coverage:** Complete — all 17 AC lines mapped to task-owned tests

**Coverage:** 32% engine coverage from task-scoped tests alone; 51% with full engine suite. Gap to 90% tracked in #1123.

**ruff:** clean
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes in this builder pass.
- Files changed: none.
- Tests:
  - `serve/kanban/tests/test_engine_move_claim.py`: 19 passed, 0 failed
  - `serve/kanban/tests/test_engine_atomicity_1104.py` + `serve/kanban/tests/test_engine_archived_edit_1120.py`: 67 passed, 0 failed
- Ruff:
  - `serve/kanban/src/owlbear_kanban/engine.py`: clean
  - `serve/kanban/tests/test_engine_move_claim.py`: clean
  - `serve/kanban/tests/test_engine_atomicity_1104.py`: clean
  - `serve/kanban/tests/test_engine_archived_edit_1120.py`: clean
- Coverage (`owlbear_kanban.engine`):
  - Task test scoped run: 32%
  - Regression pair scoped run: 42%
- Evidence summary: current implementation satisfies task-owned behavior tests and lint, but verification remains below builder GREEN gate (`>=90%` coverage on touched module).
- Fixes applied: none (no implementation defect surfaced in this pass).
- Rejection rationale: this is an AC/gate-scope mismatch for a large shared module, not a source-code bug. Achieving 90% here requires broad test expansion beyond this task’s move/start_work implementation scope.
- AC suggestion: either (1) define scoped coverage acceptance for task-owned surfaces, or (2) make this task depend on dedicated coverage-curation work (e.g., #1123) before re-entry.
- Reflection:
  - Quality-runner verification remains stable across multiple runs; failure mode is gate threshold, not correctness.
  - The surgical builder boundary is respected: no test authoring and no unrelated source changes.
  - Task-owned AC behavior appears complete; remaining risk is governance mismatch on module-wide coverage policy.
[[2026-04-25]]
## Architecture Review

### AC Refinement

**STRUCK:** "All tests fail (RED phase)" — this AC line is a process artifact from the RED phase. It is inherently unverifiable after GREEN (you cannot have failing tests and passing tests simultaneously). It caused two reviewer deductions across review cycles despite being tautologically unfulfillable post-implementation. The test-writer's RED-phase evidence is recorded in the task body prose and commit history. This line is not an acceptance criterion for the delivered work.

**COVERAGE GATE NOTE:** The 90% pipeline coverage gate applies to *module-wide* measurement of touched modules, not task-scoped-only measurement. Task #1123 research confirmed `owlbear_kanban.engine` is at 96% module-wide coverage. The builder's 32-51% figures were task-scoped measurements only. Downstream reviewers: measure module-wide via `--cov=owlbear_kanban.engine` across the full test suite, not only from `test_engine_move_claim.py`.

**D18+D36 SCOPE NOTE:** The AC specifies behavioral "lazy-release + re-claim," not compare-and-set (CAS) semantics. The `write_task_if_unchanged` CAS mechanism referenced in Brief B §1.7 is a storage-layer concern scoped to Brief C. The task-owned test proves the behavioral contract as specified.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | move_task + start_work guards in one module; tightly coupled operations |
| Interface clarity | PASS | 16 verifiable AC lines with exact error codes, conditions, and behaviors |
| Dependency correctness | PASS | #1072 is done (archived) |
| Module layering | PASS | AgentView wraps KanbanEngine; correct direction |
| TDD compliance | PASS | Task is itself the RED phase (tdd:red tag); GREEN paired naturally |
| KISS/YAGNI | PASS | Minimal scope — validation guards, error mappings, no speculative features |
| Premise challenge | PASS | Archival validation matrix and claim guards are needed engine contracts |
| Pattern consistency | PASS | Error taxonomy (ValidationError, ConcurrencyError, NotFoundError) follows established patterns in engine.py |
| Security surface | PASS | Task IS input validation — validates archival_reason enum, archival_refs existence, predicate enforcement |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: reconsider (0.58)
- Architect response: accepted RED-phase AC strike and coverage clarification; rebutted D18+D36 CAS scope (behavioral AC, not CAS) and D41 crash atomicity (Brief C scope). Revised approach: REFINE (strike unverifiable AC, add gate notes) then APPROVE.

### Verdict: APPROVE (after REFINE)
### Action Taken: Struck "All tests fail (RED phase)" AC line as unverifiable post-GREEN. Added coverage gate scope note and D18+D36 scope clarification. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes

**Retry cycle — architecture review pass-through**

Architecture review approved and struck the "All tests fail (RED phase)" AC as unverifiable post-GREEN. All remaining 16 AC lines have task-owned tests. Implementation is live-correct; no new tests needed.

**Test file:** `serve/kanban/tests/test_engine_move_claim.py`

**Classes:**
- `TestFromAC_MoveTask` — 14 tests
- `TestFromAC_StartWork` — 5 tests

**Categories:**
| Category | Count |
|----------|-------|
| Error paths (archival validation, claim guards) | 11 |
| Behavioral contract (atomicity, predicate enforcement, guidance) | 6 |
| Boundary (skip warning, persistence proof, expiry re-claim) | 2 |
| **Total** | **19** |

**Pytest result:** `19 passed, 0 failed` (implementation live-correct; all AC lines proven)

**AC coverage (post-architect strike):**
| AC | Test | Status |
|----|------|--------|
| AC4 | `test_archive_without_reason_raises_archival_reason_required` | COVERED |
| AC5 | `test_archive_completed_from_non_terminal_raises_completed_requires_done` | COVERED |
| AC7 | `test_archive_deprecated_without_refs_raises_archival_refs_required` | COVERED |
| AC8 | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` | COVERED |
| AC9 | `test_archive_invalid_reason_raises_archival_reason_invalid` | COVERED |
| AC26 | `test_archive_with_missing_ref_raises_archival_ref_missing` | COVERED |
| ERR_ARCHIVAL_FIELDS_FORBIDDEN | `test_archival_reason_on_active_status_raises_fields_forbidden` | COVERED |
| D15 | `test_predicate_on_destination_fails_raises_predicate_failed` | COVERED |
| D41 | `test_predicate_on_destination_fails_task_not_moved` | COVERED |
| D17 (return value) | `test_archive_claimed_task_clears_claim` | COVERED |
| D17 (persistence proof) | `test_archive_cleared_claim_persisted_in_archive_file` | COVERED |
| AC-NEW-5 | `test_move_skipping_two_columns_emits_skip_guidance` | COVERED |
| AC-NEW-16 (move) | `test_move_missing_task_raises_not_found` | COVERED |
| Invalid status enum | `test_move_invalid_status_raises_invalid_status` | COVERED |
| ERR_BLOCKED_NOT_CLAIMABLE | `test_blocked_task_raises_blocked_not_claimable` | COVERED |
| ERR_ARCHIVED_NOT_CLAIMABLE | `test_archived_task_raises_archived_not_claimable` | COVERED |
| AC-NEW-16 (start_work) | `test_start_work_missing_task_raises_not_found` | COVERED |
| ERR_ALREADY_CLAIMED | `test_start_work_already_claimed_raises_already_claimed` | COVERED |
| D18+D36 | `test_start_work_expired_claim_allows_reclaim` | COVERED |
| "All tests fail (RED phase)" | STRUCK by architect — unverifiable post-GREEN |

**ruff:** clean (verified in prior cycles)
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes in this builder pass.
- Files changed: none.
- Fixes applied: none (existing implementation already satisfies task-owned contracts).
- Tests:
  - `serve/kanban/tests/test_engine_move_claim.py` + `serve/kanban/tests/test_engine_atomicity_1104.py` + `serve/kanban/tests/test_engine_archived_edit_1120.py`: 86 passed, 0 failed (`-p no:timeout` used due plugin interruption on first attempt).
- Coverage:
  - `owlbear_kanban.engine`: 96% module coverage (from quality-runner filtered summary on `tests/` + `serve/` non-api run).
- Lint:
  - Ruff clean on `serve/kanban/src/owlbear_kanban/engine.py` and scoped task/regression tests.
- Evidence summary:
  - Task-owned + regression scope is GREEN.
  - Touched module coverage meets >=90% gate.
  - Full cross-repo non-api run reports unrelated background failures/errors outside #1073 scope; task-owned verification remains clean and reproducible.
- Reflection:
  - Independent rerun confirms prior cycle findings: implementation is stable; remaining noise is global-suite debt not specific to move/start_work behavior in this task.
[[2026-04-25]]
## Review Evidence
### Test Results
- Independent scoped quality-runner run on serve/kanban/tests/test_engine_move_claim.py, serve/kanban/tests/test_engine_atomicity_1104.py, and serve/kanban/tests/test_engine_archived_edit_1120.py: 59 passed, 0 failed, 0 skipped.
- Independent broad quality-runner run for module coverage: 2058 passed, 166 failed, 209 errors, 4 skipped. Failures were dominated by unrelated constructor/fixture issues outside this task’s move/start_work scope, so I used this run for module-level coverage context only.

### Lint
- Ruff clean on serve/kanban/src/owlbear_kanban/engine.py plus the three scoped test files.

### Coverage
- Scoped run: owlbear_kanban.engine 50%.
- Broad run: owlbear_kanban.engine 96% (1207 statements, 48 missed).
- Per the architect refinement already recorded in the task body, the module-wide gate is satisfied; coverage is not the blocker in this review.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC4 archive without reason | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L207) | PASS |
| AC5 completed archive from non-terminal | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L209-L223) | PASS |
| AC7 deprecated archive without refs | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L225-L239) | PASS |
| AC8 dropped archive with refs | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L241-L255) | PASS |
| AC9 invalid archival reason | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L257-L271) | PASS |
| AC26 missing archival ref | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L273-L288) | PASS |
| archival fields forbidden off archived status | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L290-L304) | PASS |
| D15 predicate failure returns ERR_PREDICATE_FAILED | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L306-L320) | PASS |
| D41 predicate failure does not move task | Task-owned unchanged-status assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L322-L338) | PASS |
| D17 archive clears claim atomically | Success-path assertions exist at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L340-L375) and rollback assertions exist at [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py#L213-L239) plus [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py#L628-L651), but the success-path reread goes through [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L799-L845), which searches tasks before archive, and the rollback proofs use unclaimed fixtures only. | LAX |
| AC-NEW-5 skip guidance | Task-owned guidance assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L377-L388) | PASS |
| AC-NEW-16 move missing id | Task-owned NotFoundError assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L390-L399) | PASS |
| Invalid status enum | Task-owned ValidationError assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L401-L412) | PASS |
| start_work blocked task | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L435-L453) | PASS |
| start_work archived task | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L455-L474) | PASS |
| AC-NEW-16 start_work missing id | Task-owned NotFoundError assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L476-L485) | PASS |
| start_work already claimed | Task-owned exact-code assertion at [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L487-L504) | PASS |
| D18+D36 expired claim lazy-release + re-claim | The only task-owned proof is [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L506-L521), which asserts only that claimed_at is not null even though the fixture already starts with a non-null stale timestamp. A no-op implementation that returned the stale claim unchanged would still pass. | LAX |

#### Security Review
- No scoped security issue found in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1044-L1108), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1723-L1792), or [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2518-L2586).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned TestFromAC assertions in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L195-L521) | No weakened or removed assertions were demonstrated in the current snapshot. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most assertions are exact exception/code checks, but D17 and D18 rely on broader field-presence checks rather than discriminating mutations. |
| Negative/error-path coverage | ADEQUATE | All live AC lines now have task-owned coverage. |
| Manual mutation reasoning | WEAK | [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L506-L521) would stay green if start_work simply returned the stale expired claim unchanged, and [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L357-L375) would stay green if a cleared-claim copy remained in tasks because [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L799-L845) checks tasks before archive. |
| Test independence | STRONG | The scoped tests build isolated temp boards and fixtures. |
| Descriptive names | STRONG | The task-owned test names state the contract directly. |

#### Data Safety
- No live implementation defect demonstrated in the scoped code. The remaining failures are proof-strength gaps, not a reproduced runtime bug.

#### Implementation-Aware Gaps
- No task-owned test proves that the expired claim was actually replaced rather than merely returned unchanged; see [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L506-L521).
- No claimed-task rollback proof exists for archive failure. The rollback suite covers archive failure with unclaimed fixtures only; see [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py#L213-L239) and [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py#L628-L651).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior Review Evidence sections already in task body | 2 |
| Current review failure number | 3 |
| Assessment | LOOP-BREAKER ROUTE APPLIES |

### Pass 2 - INFORMATIONAL
- The top-level module docstring and several test docstrings in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py#L1-L39) still describe earlier RED-phase omissions. That is stale commentary, but not the gating failure because architecture already struck the RED-only AC.

### Deductions
- AC D18+D36 is only weakly proven: the task-owned test accepts any non-null claim timestamp, including the stale fixture value.
- AC D17 is still only partially proven: the current success-path reread does not prove archive-path persistence and the rollback suite does not cover claimed-task rollback.
- Scoped correctness, lint, and module-wide coverage are otherwise acceptable; the blocker is task-owned proof quality.
- This is the third review rejection on the same task, so the pipeline loop-breaker route is mandatory.

### Confidence: 0.85
### Verdict: FAIL
### Action: reject to backlog. Implementation appears live-correct, but task-owned proof remains too weak on D17 and D18+D36, and this is the third review failure.

### Reflection
- Broad coverage had to be separated from task correctness because the shared engine module pulls in unrelated suite noise.
- The remaining gap is mutation resistance in TestFromAC assertions, not a reproduced source-code defect.
- Fresh-engine rereads are not enough by themselves when the lookup path checks tasks before archive.
- Non-null assertions are not sufficient proof for reclaim semantics when the fixture already starts non-null.
[[2026-04-25]]
## Architecture Review (loop-breaker re-entry)

### AC Refinement

**STRUCK (prior cycle, retained):** "All tests fail (RED phase)" — unverifiable post-GREEN; process artifact.

**TIGHTENED — D17:** "Archive clears claim atomically" → the task-owned persistence test (`test_archive_cleared_claim_persisted_in_archive_file`) must additionally assert the task file exists in `archive/` and does NOT exist in `tasks/`. This eliminates the reviewer's concern about `show_task` reading from `tasks/` first. NOTE: `claimed_by` has `exclude=True` on the Task model (models.py L263) and is popped by `_coerce_claimed` (models.py L315) — it is not observable in projections or persisted state. Only `claimed_at` is a testable claim-clearing contract at the AgentView level.

**TIGHTENED — D18+D36:** "start_work on expired claim → lazy-release + re-claim" → the task-owned test (`test_start_work_expired_claim_allows_reclaim`) must assert `result.claimed_at != stale_fixture_timestamp` (not just `is not None`). The fixture uses `"2026-01-01T00:00:00+00:00"` — the assertion must prove the timestamp changed, not merely that it exists.

**COVERAGE GATE NOTE (retained):** Module-wide `owlbear_kanban.engine` coverage is 96%. The pipeline gate measures module-wide via `--cov=owlbear_kanban.engine` across the full test suite, not task-scoped-only. Confirmed by #1123 research. Downstream reviewers: do not gate on task-scoped coverage figures.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | move_task + start_work guards — tightly coupled operations in one module |
| Interface clarity | PASS | 16 live AC lines with exact error codes, conditions, behaviors; D17 and D18+D36 now tightened with specific assertion requirements |
| Dependency correctness | PASS | #1072 done (archived) |
| Module layering | PASS | AgentView wraps KanbanEngine; correct direction |
| TDD compliance | PASS | Task is the RED phase (tdd:red tag); GREEN paired in-task |
| KISS/YAGNI | PASS | Minimal scope — validation guards, error mappings, no speculative features |
| Premise challenge | PASS | Archival validation matrix and claim guards are required engine contracts per Brief B |
| Pattern consistency | PASS | Error taxonomy (ValidationError, ConcurrencyError, NotFoundError) follows established engine.py patterns |
| Security surface | PASS | Task IS input validation — validates archival_reason enum, archival_refs existence, predicate enforcement |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: reconsider (0.46)
- Key challenger points accepted: (1) prior REFINE+APPROVE was overturned — same approach won't hold; (2) D18+D36 proof gap is genuine; (3) for a RED task, test proof IS the deliverable
- Key challenger points rebutted: (1) D17 claimed_by concern is moot — `claimed_by` has `exclude=True` and is not persisted (models.py L263); (2) the D17 persistence test reads from archive via fresh engine glob path (engine.py L839-843 globs tasks/ first, finds nothing, then L845-847 globs archive/ — correct path after move_task)
- Architect response: accepted the need for concrete AC changes (not just notes); tightened D17 to require file-location assertion and D18+D36 to require timestamp-discrimination assertion. This differs from the prior approval which only added notes.

### Difference from prior cycle
The prior architect REFINE+APPROVE (struck RED AC, added scope notes) was overturned because the reviewer still found proof gaps. This time:
1. D17 AC now requires file-location assertion (archive/ exists, tasks/ does not) — directly addresses reviewer concern
2. D18+D36 AC now requires timestamp-discrimination assertion — closes the false-green proof gap
3. Both are single-line assertion changes with unambiguous targets for the test-writer

### Verdict: APPROVE (after REFINE)
### Action Taken: Tightened D17 and D18+D36 AC lines with specific assertion requirements. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes

**Retry cycle — tightened AC assertions (architect loop-breaker refinement)**

**Test file:** `serve/kanban/tests/test_engine_move_claim.py`

**Classes:**
- `TestFromAC_MoveTask` — 14 tests
- `TestFromAC_StartWork` — 5 tests

**Changes (2 tests strengthened per architect AC refinement):**

| AC | Test | Change |
|----|------|--------|
| D17 (persistence) | `test_archive_cleared_claim_persisted_in_archive_file` | Added file-location assertions: `archive/1-*.md` exists AND `tasks/1-*.md` does NOT exist after archive. Directly closes reviewer concern that `show_task` reads `tasks/` before `archive/`. |
| D18+D36 | `test_start_work_expired_claim_allows_reclaim` | Added `result.claimed_at != stale` assertion (stale=`"2026-01-01T00:00:00+00:00"`). Closes false-green gap where a no-op returning the unchanged stale timestamp would still pass the `is not None` check. |

**Total:** 19 tests, all PASS (implementation live-correct; all AC lines covered with strengthened proof)

**Pytest result:** `19 passed, 0 failed` ✓

**ruff:** clean

**AC coverage (post-architect tightening):**

| AC | Test | Proof strength |
|----|------|---------------|
| D17 (return value) | `test_archive_claimed_task_clears_claim` | claimed_at is None in response |
| D17 (persistence + location) | `test_archive_cleared_claim_persisted_in_archive_file` | file in archive/, not in tasks/; fresh engine claimed_at is None |
| D18+D36 | `test_start_work_expired_claim_allows_reclaim` | claimed_at is not None AND != stale timestamp |
| All other AC lines | (unchanged from prior cycle) | COVERED |
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes in this builder pass.
- Files changed by builder: none.
- Fixes applied: none (current implementation remained GREEN under task-owned assertions).
- Tests:
  - `serve/kanban/tests/test_engine_move_claim.py`
  - `serve/kanban/tests/test_engine_atomicity_1104.py`
  - `serve/kanban/tests/test_engine_archived_edit_1120.py`
  - Result: 59 passed, 0 failed, 0 skipped.
- Lint:
  - Ruff clean on `serve/kanban/src/owlbear_kanban/engine.py` and the three scoped test files.
- Coverage:
  - Scoped run reported `owlbear_kanban.engine` 51%.
  - Prior task history already records module-wide evidence at 96% for `owlbear_kanban.engine` after broader non-api run.
- Evidence summary:
  - Task-owned strengthened tests for D17 and D18+D36 are present and passing.
  - No implementation regression was found in move/start_work behavior in this pass.
- Reflection:
  - This cycle was verification-only; the implementation matched the tightened AC contracts without additional surgery.
  - Scoped quality checks are stable and reproducible.
  - Remaining risk is global-suite debt outside #1073 scope, not move/start_work behavior.
[[2026-04-25]]
## Review Evidence
### Test Results
- Independent scoped quality-runner run on [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py), [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py), and [serve/kanban/tests/test_engine_archived_edit_1120.py](serve/kanban/tests/test_engine_archived_edit_1120.py): 59 passed, 0 failed, 0 skipped.
- Independent broad quality-runner run for module coverage context: 2059 passed, 6 failed, 4 skipped. The listed failures were outside this task’s move_task/start_work scope, so I used that run only for module-wide coverage context.

### Lint
- Scoped lint is clean on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py), [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py), and [serve/kanban/tests/test_engine_archived_edit_1120.py](serve/kanban/tests/test_engine_archived_edit_1120.py).
- Broad lint found unrelated repo debt outside this task’s scope, so it is not the gating issue for #1073.

### Coverage
- Scoped run: owlbear_kanban.engine 51 percent.
- Broad run: owlbear_kanban.engine 96 percent.
- The latest architecture refinement in [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L595-L603](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L595-L603) makes module-wide coverage the binding gate, so coverage is satisfied.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would fail if AC violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC4 archive without reason | test_archive_without_reason_raises_archival_reason_required | Yes | COVERED |
| AC5 completed archive from non-terminal | test_archive_completed_from_non_terminal_raises_completed_requires_done | Yes | COVERED |
| AC7 deprecated archive without refs | test_archive_deprecated_without_refs_raises_archival_refs_required | Yes | COVERED |
| AC8 dropped archive with refs | test_archive_dropped_with_refs_raises_archival_refs_forbidden | Yes | COVERED |
| AC9 invalid archival reason enum | test_archive_invalid_reason_raises_archival_reason_invalid | Yes | COVERED |
| AC26 archival ref missing | test_archive_with_missing_ref_raises_archival_ref_missing | Yes | COVERED |
| AC-NEW-5 skip guidance | test_move_skipping_two_columns_emits_skip_guidance | Yes | COVERED |
| AC-NEW-16 missing id on move_task and start_work | test_move_missing_task_raises_not_found and test_start_work_missing_task_raises_not_found | Yes | COVERED |
| Invalid status enum | test_move_invalid_status_raises_invalid_status | Yes | COVERED |
| start_work already claimed | test_start_work_already_claimed_raises_already_claimed | Yes | COVERED |
| start_work archived not claimable | test_archived_task_raises_archived_not_claimable | Yes | COVERED |
| start_work blocked not claimable | test_blocked_task_raises_blocked_not_claimable | Yes | COVERED |
| D18 plus D36 expired claim re-claim | test_start_work_expired_claim_allows_reclaim | Yes under the latest architect tightening at [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L601-L603](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L601-L603) | COVERED |
| D15 plus D41 predicate failure and no move | test_predicate_on_destination_fails_raises_predicate_failed and test_predicate_on_destination_fails_task_not_moved | Yes | COVERED |
| D17 archive clears claim atomically | test_archive_claimed_task_clears_claim and test_archive_cleared_claim_persisted_in_archive_file | Yes under the latest architect tightening at [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L598-L600](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L598-L600) | COVERED |
| Archival fields forbidden on active status | test_archival_reason_on_active_status_raises_fields_forbidden | Yes | COVERED |

#### Security Review
- No scoped security issue found in the validation, archive, or error-mapping paths at [serve/kanban/src/owlbear_kanban/engine.py#L1044](serve/kanban/src/owlbear_kanban/engine.py#L1044), [serve/kanban/src/owlbear_kanban/engine.py#L1713](serve/kanban/src/owlbear_kanban/engine.py#L1713), and [serve/kanban/src/owlbear_kanban/engine.py#L2504](serve/kanban/src/owlbear_kanban/engine.py#L2504).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned TestFromAC assertions in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py) | Latest cycle only strengthened D17 and D18 plus D36 per [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L647-L651](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L647-L651); I found no weakened or removed assertion in the current snapshot. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact exception-code assertions cover the live AC surface at [serve/kanban/tests/test_engine_move_claim.py#L195](serve/kanban/tests/test_engine_move_claim.py#L195) through [serve/kanban/tests/test_engine_move_claim.py#L530](serve/kanban/tests/test_engine_move_claim.py#L530). |
| Negative and error-path coverage | ADEQUATE | The task-owned file now covers all live AC lines, including tightened D17 at [serve/kanban/tests/test_engine_move_claim.py#L357](serve/kanban/tests/test_engine_move_claim.py#L357) and tightened D18 plus D36 at [serve/kanban/tests/test_engine_move_claim.py#L513](serve/kanban/tests/test_engine_move_claim.py#L513). |
| Manual mutation reasoning | ADEQUATE | The latest architect-raised false-green issues are closed by the file-location assertions at [serve/kanban/tests/test_engine_move_claim.py#L371-L382](serve/kanban/tests/test_engine_move_claim.py#L371-L382) and the changed-timestamp assertion at [serve/kanban/tests/test_engine_move_claim.py#L526-L530](serve/kanban/tests/test_engine_move_claim.py#L526-L530). |
| Test independence | STRONG | The file builds isolated boards and tasks through local helpers at [serve/kanban/tests/test_engine_move_claim.py#L121](serve/kanban/tests/test_engine_move_claim.py#L121) and [serve/kanban/tests/test_engine_move_claim.py#L169](serve/kanban/tests/test_engine_move_claim.py#L169). |
| Descriptive names | STRONG | Test names state the contract directly throughout [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py). |

#### Data Safety
- No reproduced live data-safety defect remains in the current move_task/start_work behavior. The current blocker is missing proof for one changed rollback branch, not a reproduced runtime bug.

#### Implementation-Aware Gaps
- FAIL: the new archive file-move rollback branch at [serve/kanban/src/owlbear_kanban/engine.py#L1089-L1092](serve/kanban/src/owlbear_kanban/engine.py#L1089-L1092) is still unexercised. The only archive-failure proofs I found are [serve/kanban/tests/test_engine_atomicity_1104.py#L213](serve/kanban/tests/test_engine_atomicity_1104.py#L213) and [serve/kanban/tests/test_engine_atomicity_1104.py#L628](serve/kanban/tests/test_engine_atomicity_1104.py#L628), and both patch emit failure after the move. I found no engine test that forces _move_file or its underlying replace path to raise. Because move_task writes the archived record before the file move at [serve/kanban/src/owlbear_kanban/engine.py#L1084-L1088](serve/kanban/src/owlbear_kanban/engine.py#L1084-L1088), this untested recovery path is significant.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior Review Evidence sections in task body | 3 at [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L113](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L113), [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L223](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L223), and [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L509](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L509) |
| Current review failure number | 4 |
| Assessment | LOOP-BREAKER ROUTE APPLIES |

### Pass 2 - INFORMATIONAL
- The header commentary in [serve/kanban/tests/test_engine_move_claim.py#L1-L39](serve/kanban/tests/test_engine_move_claim.py#L1-L39) still describes the file as RED-phase and lists paths as not testable as RED even though the same file now contains those tests. That is stale context, not the gating issue.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC4 archive without reason | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L195](serve/kanban/tests/test_engine_move_claim.py#L195) | test_archive_without_reason_raises_archival_reason_required | PASS |
| AC5 completed archive from non-terminal | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L209](serve/kanban/tests/test_engine_move_claim.py#L209) | test_archive_completed_from_non_terminal_raises_completed_requires_done | PASS |
| AC7 deprecated archive without refs | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L225](serve/kanban/tests/test_engine_move_claim.py#L225) | test_archive_deprecated_without_refs_raises_archival_refs_required | PASS |
| AC8 dropped archive with refs | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L241](serve/kanban/tests/test_engine_move_claim.py#L241) | test_archive_dropped_with_refs_raises_archival_refs_forbidden | PASS |
| AC9 invalid archival reason enum | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L257](serve/kanban/tests/test_engine_move_claim.py#L257) | test_archive_invalid_reason_raises_archival_reason_invalid | PASS |
| AC26 archival ref missing | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L273](serve/kanban/tests/test_engine_move_claim.py#L273) | test_archive_with_missing_ref_raises_archival_ref_missing | PASS |
| AC-NEW-5 skip guidance | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L384](serve/kanban/tests/test_engine_move_claim.py#L384) | test_move_skipping_two_columns_emits_skip_guidance | PASS |
| AC-NEW-16 missing id on move_task and start_work | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L397](serve/kanban/tests/test_engine_move_claim.py#L397) and [serve/kanban/tests/test_engine_move_claim.py#L483](serve/kanban/tests/test_engine_move_claim.py#L483) | test_move_missing_task_raises_not_found and test_start_work_missing_task_raises_not_found | PASS |
| Invalid status enum | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L408](serve/kanban/tests/test_engine_move_claim.py#L408) | test_move_invalid_status_raises_invalid_status | PASS |
| start_work already claimed | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L494](serve/kanban/tests/test_engine_move_claim.py#L494) | test_start_work_already_claimed_raises_already_claimed | PASS |
| start_work archived not claimable | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L462](serve/kanban/tests/test_engine_move_claim.py#L462) | test_archived_task_raises_archived_not_claimable | PASS |
| start_work blocked not claimable | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L442](serve/kanban/tests/test_engine_move_claim.py#L442) | test_blocked_task_raises_blocked_not_claimable | PASS |
| D18 plus D36 expired claim re-claim | Scoped run green; tightened assertion present at [serve/kanban/tests/test_engine_move_claim.py#L513](serve/kanban/tests/test_engine_move_claim.py#L513) and [serve/kanban/tests/test_engine_move_claim.py#L526-L530](serve/kanban/tests/test_engine_move_claim.py#L526-L530) | test_start_work_expired_claim_allows_reclaim | PASS |
| D15 plus D41 predicate failure and no move | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L306](serve/kanban/tests/test_engine_move_claim.py#L306) and [serve/kanban/tests/test_engine_move_claim.py#L322](serve/kanban/tests/test_engine_move_claim.py#L322) | test_predicate_on_destination_fails_raises_predicate_failed and test_predicate_on_destination_fails_task_not_moved | PASS |
| D17 archive clears claim atomically | Scoped run green; tightened persistence proof at [serve/kanban/tests/test_engine_move_claim.py#L357](serve/kanban/tests/test_engine_move_claim.py#L357) through [serve/kanban/tests/test_engine_move_claim.py#L382](serve/kanban/tests/test_engine_move_claim.py#L382) | test_archive_claimed_task_clears_claim and test_archive_cleared_claim_persisted_in_archive_file | PASS |
| Archival fields forbidden on active status | Scoped run green; [serve/kanban/tests/test_engine_move_claim.py#L290](serve/kanban/tests/test_engine_move_claim.py#L290) | test_archival_reason_on_active_status_raises_fields_forbidden | PASS |

### Deductions
- All live AC lines are now task-owned and passing under the latest architect refinement.
- Module-wide coverage is independently confirmed at 96 percent, so coverage is not the blocker.
- One significant changed error-recovery branch remains untested: the archive file-move rollback branch at [serve/kanban/src/owlbear_kanban/engine.py#L1089-L1092](serve/kanban/src/owlbear_kanban/engine.py#L1089-L1092).
- This is the fourth review failure on the same task, so the loop-breaker route is mandatory.

### Confidence: 0.88
### Verdict: FAIL
### Action: reject to backlog because the implementation appears live-correct on the refined AC, but the changed archive rollback branch still lacks direct proof and the loop-breaker rule now applies.

### Reflection
- Scoped and broad quality runs had to be separated to distinguish task correctness from unrelated suite debt while still validating module-wide coverage.
- The latest Architecture Review refinement was the binding AC authority; the stale top-level checklist would have produced a wrong gate.
- The remaining issue is proof strength on changed error recovery, not a reproduced move_task/start_work behavior defect.
[[2026-04-25]]
## Architecture Review (2nd loop-breaker re-entry)

### AC Refinement

**RETAINED from prior cycles:** "All tests fail (RED phase)" remains struck (unverifiable post-GREEN).

**RETAINED from prior cycles:** Coverage gate note (module-wide 96%, not task-scoped), D18+D36 scope note (behavioral, not CAS).

**ADDED — D17 rollback proof:** The `_move_file` failure rollback branch at `serve/kanban/src/owlbear_kanban/engine.py` L1089-1092 was introduced by the builder within this task (commit `9b4fcc0a`). It is part of D17's "atomically" guarantee — if `_move_file` fails after `write_task` has written the archived record, the original task record must be restored. This branch is currently unexercised by any test suite (the atomicity tests at `test_engine_atomicity_1104.py` L213 and L628 mock `_emit_event`, not `_move_file`). The test-writer must add one task-owned test:

**New AC line:** `_move_file` OSError during archive must restore the pre-archive task record (original status, original `claimed_at`) in `tasks/` — mock `owlbear_kanban.engine._move_file` to raise `OSError`, call `AgentView.move_task(id, "archived", archival_reason=...)`, verify the task record on disk matches the pre-mutation state.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | move_task + start_work guards — tightly coupled operations in one module |
| Interface clarity | PASS | 16 prior AC lines verified + 1 new rollback AC added with specific mock target and assertion |
| Dependency correctness | PASS | #1072 done (archived) |
| Module layering | PASS | AgentView wraps KanbanEngine; correct direction |
| TDD compliance | PASS | tdd:red tag; GREEN paired in-task |
| KISS/YAGNI | PASS | Minimal scope — validation guards, error mappings, rollback proof |
| Premise challenge | PASS | Required engine contracts per Brief B |
| Pattern consistency | PASS | Error taxonomy follows established engine.py patterns |
| Security surface | PASS | Task IS input validation |
| Single domain | PASS | Kanban engine only |

### Challenge Results
- Challenger: reconsider (0.64)
- Key points accepted: (1) rollback branch was introduced in this task's builder commits — its proof is this task's responsibility; (2) D17 "atomically" covers failure recovery, not just success path; (3) atomicity suite mocks emit failure not move failure, so it cannot serve as alternate proof; (4) no new executable evidence since last rejection
- Key points rebutted: none — challenger's analysis is correct
- Architect response: accepted in full. Added rollback proof AC line instead of approving without it. This differs from prior cycle (which tried to classify the branch as out-of-scope).

### Difference from prior cycles
Prior architect approvals tried to classify the `_move_file` rollback branch as out-of-scope (atomicity concern for #1104). The challenger correctly identified that this branch was introduced within #1073's builder commits and that D17 "atomically" covers failure paths. This cycle adds a specific, mechanically derivable AC line for the rollback proof rather than deferring it.

### Verdict: APPROVE (after REFINE)
### Action Taken: Added _move_file rollback proof AC line. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes

**Test file:** `serve/kanban/tests/test_engine_move_claim.py`

**Retry cycle — 2nd loop-breaker architect refinement (D17 rollback proof)**

Architecture review (2nd loop-breaker re-entry) added one new AC line:
> `_move_file` OSError during archive must restore the pre-archive task record in `tasks/`.

**Change made (1 new test):**

| AC | Test | Proof |
|----|------|-------|
| D17 rollback | `test_archive_move_failure_restores_original_task_record` | Mocks `owlbear_kanban.engine._move_file` to raise `OSError`; asserts task file exists in `tasks/` (not `archive/`), `status == "todo"`, and `claimed_at is not None` via fresh engine re-read |

**Classes:**
- `TestFromAC_MoveTask` — 15 tests (14 original + 1 new)
- `TestFromAC_StartWork` — 5 tests (unchanged)

**Total:** 20 tests, all PASS (implementation live-correct; rollback branch introduced in builder commit `9b4fcc0a` satisfies the new AC)

**Pytest result:** `20 passed, 0 failed` ✓
**ruff:** clean

**AC coverage (complete — all 17 live AC lines + new rollback AC):**

| AC | Test | Status |
|----|------|--------|
| AC4 | `test_archive_without_reason_raises_archival_reason_required` | COVERED |
| AC5 | `test_archive_completed_from_non_terminal_raises_completed_requires_done` | COVERED |
| AC7 | `test_archive_deprecated_without_refs_raises_archival_refs_required` | COVERED |
| AC8 | `test_archive_dropped_with_refs_raises_archival_refs_forbidden` | COVERED |
| AC9 | `test_archive_invalid_reason_raises_archival_reason_invalid` | COVERED |
| AC26 | `test_archive_with_missing_ref_raises_archival_ref_missing` | COVERED |
| ERR_ARCHIVAL_FIELDS_FORBIDDEN | `test_archival_reason_on_active_status_raises_fields_forbidden` | COVERED |
| D15 | `test_predicate_on_destination_fails_raises_predicate_failed` | COVERED |
| D41 | `test_predicate_on_destination_fails_task_not_moved` | COVERED |
| D17 (return value) | `test_archive_claimed_task_clears_claim` | COVERED |
| D17 (persistence + location) | `test_archive_cleared_claim_persisted_in_archive_file` | COVERED |
| D17 (rollback) | `test_archive_move_failure_restores_original_task_record` | COVERED ← NEW |
| AC-NEW-5 | `test_move_skipping_two_columns_emits_skip_guidance` | COVERED |
| AC-NEW-16 (move) | `test_move_missing_task_raises_not_found` | COVERED |
| Invalid status enum | `test_move_invalid_status_raises_invalid_status` | COVERED |
| ERR_BLOCKED_NOT_CLAIMABLE | `test_blocked_task_raises_blocked_not_claimable` | COVERED |
| ERR_ARCHIVED_NOT_CLAIMABLE | `test_archived_task_raises_archived_not_claimable` | COVERED |
| AC-NEW-16 (start_work) | `test_start_work_missing_task_raises_not_found` | COVERED |
| ERR_ALREADY_CLAIMED | `test_start_work_already_claimed_raises_already_claimed` | COVERED |
| D18+D36 | `test_start_work_expired_claim_allows_reclaim` | COVERED |
| "All tests fail (RED phase)" | STRUCK by architect — unverifiable post-GREEN |
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes in this builder pass.
- Files changed by builder: none.
- Fixes applied: none (current implementation remained GREEN under the latest task-owned assertions, including rollback proof coverage added by test-writer).
- Tests:
  - `serve/kanban/tests/test_engine_move_claim.py`
  - `serve/kanban/tests/test_engine_atomicity_1104.py`
  - `serve/kanban/tests/test_engine_archived_edit_1120.py`
  - Result: 96 passed, 0 failed.
- Lint:
  - Ruff clean on `serve/kanban/src/owlbear_kanban/engine.py` and the three scoped test files.
- Coverage:
  - Module-wide evidence already recorded in task history: `owlbear_kanban.engine` 96% (binding gate per architect refinement).
- Evidence summary:
  - Current scoped verification is fully green.
  - No implementation regression found in move/start_work behavior.
- Reflection:
  - This cycle was verification-only; the latest test-writer changes closed prior proof gaps without requiring additional code surgery.
  - Scoped quality checks remain stable and reproducible.
  - Existing workspace contains unrelated dirty changes outside this task scope; no unrelated files were modified by this builder pass.
[[2026-04-25]]
## Review Evidence
### Test Results
- Independent quality-runner scoped run on [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py), [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py), and [serve/kanban/tests/test_engine_archived_edit_1120.py](serve/kanban/tests/test_engine_archived_edit_1120.py): 96 passed, 0 failed, 0 skipped.
- Independent broad quality-runner run for module-wide coverage context: 2099 passed, 165 failed, 4 skipped. The broad failures were dominated by unrelated `KanbanEngine.__init__(agent_name=...)` fixture/caller mismatches outside #1073 scope, so I used that run for module-wide coverage context only.

### Lint
- Scoped lint is clean on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py), [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py), and [serve/kanban/tests/test_engine_archived_edit_1120.py](serve/kanban/tests/test_engine_archived_edit_1120.py).
- Broad lint found unrelated repo debt in other packages; those paths were not touched by #1073 and are not the gating issue for this review.

### Coverage
- Scoped run: `owlbear_kanban.engine` 52 percent.
- Broad run: `owlbear_kanban.engine` 96 percent (1197 statements, 42 missed).
- The latest architecture refinement makes module-wide coverage the binding gate at [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L595-L603](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L595-L603); that gate is satisfied.

### Pass 1 - CRITICAL
#### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC4 archive without reason | [serve/kanban/tests/test_engine_move_claim.py#L185-L197](serve/kanban/tests/test_engine_move_claim.py#L185-L197) against [serve/kanban/src/owlbear_kanban/engine.py#L1713-L1721](serve/kanban/src/owlbear_kanban/engine.py#L1713-L1721) | PASS |
| AC5 completed archive from non-terminal | [serve/kanban/tests/test_engine_move_claim.py#L199-L214](serve/kanban/tests/test_engine_move_claim.py#L199-L214) against [serve/kanban/src/owlbear_kanban/engine.py#L1742-L1746](serve/kanban/src/owlbear_kanban/engine.py#L1742-L1746) | PASS |
| AC7 deprecated archive without refs | [serve/kanban/tests/test_engine_move_claim.py#L216-L231](serve/kanban/tests/test_engine_move_claim.py#L216-L231) against [serve/kanban/src/owlbear_kanban/engine.py#L1729-L1735](serve/kanban/src/owlbear_kanban/engine.py#L1729-L1735) | PASS |
| AC8 dropped archive with refs | [serve/kanban/tests/test_engine_move_claim.py#L233-L248](serve/kanban/tests/test_engine_move_claim.py#L233-L248) against [serve/kanban/src/owlbear_kanban/engine.py#L1737-L1741](serve/kanban/src/owlbear_kanban/engine.py#L1737-L1741) | PASS |
| AC9 invalid archival reason enum | [serve/kanban/tests/test_engine_move_claim.py#L250-L264](serve/kanban/tests/test_engine_move_claim.py#L250-L264) against [serve/kanban/src/owlbear_kanban/engine.py#L1722-L1728](serve/kanban/src/owlbear_kanban/engine.py#L1722-L1728) | PASS |
| AC26 archival ref missing | [serve/kanban/tests/test_engine_move_claim.py#L266-L282](serve/kanban/tests/test_engine_move_claim.py#L266-L282) against [serve/kanban/src/owlbear_kanban/engine.py#L1747-L1752](serve/kanban/src/owlbear_kanban/engine.py#L1747-L1752) | PASS |
| archival fields forbidden on active status | [serve/kanban/tests/test_engine_move_claim.py#L284-L298](serve/kanban/tests/test_engine_move_claim.py#L284-L298) against [serve/kanban/src/owlbear_kanban/engine.py#L1755-L1760](serve/kanban/src/owlbear_kanban/engine.py#L1755-L1760) | PASS |
| D15 predicate failure returns ERR_PREDICATE_FAILED | [serve/kanban/tests/test_engine_move_claim.py#L300-L315](serve/kanban/tests/test_engine_move_claim.py#L300-L315) against [serve/kanban/src/owlbear_kanban/engine.py#L1772-L1796](serve/kanban/src/owlbear_kanban/engine.py#L1772-L1796) | PASS |
| D41 predicate failure does not move task | [serve/kanban/tests/test_engine_move_claim.py#L317-L333](serve/kanban/tests/test_engine_move_claim.py#L317-L333) with pre-write validation at [serve/kanban/src/owlbear_kanban/engine.py#L2518-L2536](serve/kanban/src/owlbear_kanban/engine.py#L2518-L2536) | PASS |
| D17 archive clears claim and persists in archive location | [serve/kanban/tests/test_engine_move_claim.py#L335-L382](serve/kanban/tests/test_engine_move_claim.py#L335-L382) against [serve/kanban/src/owlbear_kanban/engine.py#L1080-L1095](serve/kanban/src/owlbear_kanban/engine.py#L1080-L1095) | PASS |
| D17 rollback on `_move_file` failure restores original task record | [serve/kanban/tests/test_engine_move_claim.py#L422-L452](serve/kanban/tests/test_engine_move_claim.py#L422-L452) directly patches `_move_file` at [serve/kanban/src/owlbear_kanban/engine.py#L1087-L1092](serve/kanban/src/owlbear_kanban/engine.py#L1087-L1092) | PASS |
| AC-NEW-5 skip guidance | [serve/kanban/tests/test_engine_move_claim.py#L385-L396](serve/kanban/tests/test_engine_move_claim.py#L385-L396) against [serve/kanban/src/owlbear_kanban/engine.py#L2538-L2542](serve/kanban/src/owlbear_kanban/engine.py#L2538-L2542) | PASS |
| AC-NEW-16 move missing id | [serve/kanban/tests/test_engine_move_claim.py#L398-L406](serve/kanban/tests/test_engine_move_claim.py#L398-L406) against [serve/kanban/src/owlbear_kanban/engine.py#L2528-L2533](serve/kanban/src/owlbear_kanban/engine.py#L2528-L2533) | PASS |
| Invalid status enum | [serve/kanban/tests/test_engine_move_claim.py#L408-L420](serve/kanban/tests/test_engine_move_claim.py#L408-L420) against [serve/kanban/src/owlbear_kanban/engine.py#L1044-L1051](serve/kanban/src/owlbear_kanban/engine.py#L1044-L1051) and [serve/kanban/src/owlbear_kanban/engine.py#L2534-L2535](serve/kanban/src/owlbear_kanban/engine.py#L2534-L2535) | PASS |
| start_work blocked not claimable | [serve/kanban/tests/test_engine_move_claim.py#L475-L493](serve/kanban/tests/test_engine_move_claim.py#L475-L493) against [serve/kanban/src/owlbear_kanban/engine.py#L1129-L1132](serve/kanban/src/owlbear_kanban/engine.py#L1129-L1132) and [serve/kanban/src/owlbear_kanban/engine.py#L2567-L2573](serve/kanban/src/owlbear_kanban/engine.py#L2567-L2573) | PASS |
| start_work archived not claimable | [serve/kanban/tests/test_engine_move_claim.py#L495-L514](serve/kanban/tests/test_engine_move_claim.py#L495-L514) against [serve/kanban/src/owlbear_kanban/engine.py#L2556-L2561](serve/kanban/src/owlbear_kanban/engine.py#L2556-L2561) | PASS |
| AC-NEW-16 start_work missing id | [serve/kanban/tests/test_engine_move_claim.py#L516-L524](serve/kanban/tests/test_engine_move_claim.py#L516-L524) against [serve/kanban/src/owlbear_kanban/engine.py#L2554-L2564](serve/kanban/src/owlbear_kanban/engine.py#L2554-L2564) | PASS |
| start_work already claimed | [serve/kanban/tests/test_engine_move_claim.py#L526-L544](serve/kanban/tests/test_engine_move_claim.py#L526-L544) against [serve/kanban/src/owlbear_kanban/engine.py#L1140-L1145](serve/kanban/src/owlbear_kanban/engine.py#L1140-L1145) and [serve/kanban/src/owlbear_kanban/engine.py#L2564-L2568](serve/kanban/src/owlbear_kanban/engine.py#L2564-L2568) | PASS |
| D18+D36 expired claim lazy-release + re-claim | The latest binding architecture refinement requires timestamp discrimination on the returned reclaim at [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L601-L603](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L601-L603); [serve/kanban/tests/test_engine_move_claim.py#L546-L563](serve/kanban/tests/test_engine_move_claim.py#L546-L563) asserts `claimed_at is not None` and `claimed_at != stale`. | PASS |

#### Security Review
- No scoped security issue found in the validation, archive, or claim paths at [serve/kanban/src/owlbear_kanban/engine.py#L1044-L1161](serve/kanban/src/owlbear_kanban/engine.py#L1044-L1161), [serve/kanban/src/owlbear_kanban/engine.py#L1713-L1796](serve/kanban/src/owlbear_kanban/engine.py#L1713-L1796), and [serve/kanban/src/owlbear_kanban/engine.py#L2508-L2577](serve/kanban/src/owlbear_kanban/engine.py#L2508-L2577).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned `TestFromAC_*` assertions in [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py) | Latest cycles strengthened D17 with archive-location and rollback proof at [serve/kanban/tests/test_engine_move_claim.py#L357-L452](serve/kanban/tests/test_engine_move_claim.py#L357-L452) and strengthened D18 with explicit stale-timestamp discrimination at [serve/kanban/tests/test_engine_move_claim.py#L546-L563](serve/kanban/tests/test_engine_move_claim.py#L546-L563). | PRESERVED / STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact exception-code assertions cover the live AC surface in [serve/kanban/tests/test_engine_move_claim.py#L185-L563](serve/kanban/tests/test_engine_move_claim.py#L185-L563). |
| Negative and error-path coverage | STRONG | All live AC lines now have task-owned proofs, including D17 rollback at [serve/kanban/tests/test_engine_move_claim.py#L422-L452](serve/kanban/tests/test_engine_move_claim.py#L422-L452). |
| Manual mutation reasoning | ADEQUATE | The prior false-green concerns are closed by the archive-location/rollback assertions at [serve/kanban/tests/test_engine_move_claim.py#L357-L452](serve/kanban/tests/test_engine_move_claim.py#L357-L452) and the non-stale reclaim assertion required by [.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L601-L603](.owlbear/kanban/tasks/1073-b-09-red-move-task-start-work-tests.md#L601-L603) and implemented at [serve/kanban/tests/test_engine_move_claim.py#L560-L563](serve/kanban/tests/test_engine_move_claim.py#L560-L563). |
| Test independence | STRONG | The task-owned suites build isolated temp boards and tasks through local helpers in [serve/kanban/tests/test_engine_move_claim.py#L109-L167](serve/kanban/tests/test_engine_move_claim.py#L109-L167). |
| Descriptive names | STRONG | The test names state the contract directly throughout [serve/kanban/tests/test_engine_move_claim.py](serve/kanban/tests/test_engine_move_claim.py). |

#### Data Safety
- No reproduced live data-safety defect remains in the current move_task/start_work behavior. `_move_file` failure rollback is directly exercised by [serve/kanban/tests/test_engine_move_claim.py#L422-L452](serve/kanban/tests/test_engine_move_claim.py#L422-L452), and emit-failure rollback remains covered by [serve/kanban/tests/test_engine_atomicity_1104.py#L213-L236](serve/kanban/tests/test_engine_atomicity_1104.py#L213-L236) and [serve/kanban/tests/test_engine_atomicity_1104.py#L628-L648](serve/kanban/tests/test_engine_atomicity_1104.py#L628-L648).

#### Implementation-Aware Gaps
- No significant changed branch remains untested in #1073 scope.
- I separately checked downstream impact of the `move_task` signature expansion. Current production callers remain compatible: [serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L83-L99](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L83-L99) still calls `engine.move_task(task_id, status)` positionally, and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L265-L294](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L265-L294) passes `archival_reason` and `archival_refs` by keyword.
- A code-reader subagent argued for an extra persisted reread on D18, but the latest binding refinement narrows that AC to timestamp discrimination on the returned reclaim rather than a second on-disk assertion; per the latest architect authority, [serve/kanban/tests/test_engine_move_claim.py#L546-L563](serve/kanban/tests/test_engine_move_claim.py#L546-L563) satisfies the current contract.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior `## Review Evidence` sections already in task body | 4 |
| Current review cycle | 5 |
| Assessment | RESOLVED AFTER LOOP-BREAKER REFINEMENT |

### Pass 2 - INFORMATIONAL
- The header commentary in [serve/kanban/tests/test_engine_move_claim.py#L1-L39](serve/kanban/tests/test_engine_move_claim.py#L1-L39) still says several cases were "NOT TESTABLE AS RED" even though the same file now contains those tests. That is stale context, but it is not a gating defect.

### Deductions
- 0 gating deductions.
- Residual repo risk: the broad non-api run still shows unrelated failures and lint debt outside #1073 scope; those should not be attributed to this task.

### Confidence: 0.93
### Verdict: PASS
### Action: advance to docs.

### Reflection
- Module-wide coverage had to be verified with a broad run because the scoped run under-measures a large shared module.
- The latest Architecture Review refinement, not earlier stale fail notes, was the binding authority for D17 and D18 proof.
- The prior rollback gap is now directly exercised; remaining broad-run failures belong to unrelated constructor and fixture debt outside this task.
[[2026-04-25]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` method table entry for `move_task` was stale — showed `(task_id, status)` but builder added `archival_reason` and `archival_refs` keyword params (commit `9b4fcc0a`). Updated to `move_task(task_id, status, *, archival_reason=None, archival_refs=None)` with revised description. |
| 2 | Module docstrings | Yes | N/A | `KanbanEngine.move_task` docstring (engine.py L1044) already documents `archival_reason` and `archival_refs` accurately. `AgentView.move_task` and `AgentView.start_work` have no docstrings (consistent with existing AgentView pattern). No update needed. |
| 3 | External attribution | No | N/A | No external sources used. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` file produced or referenced. |
| 5 | Diagram maintenance | No | N/A | Doc-index has no `describes` entries for diagrams matching `serve/kanban/src/owlbear_kanban/engine.py`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified accurate — no edit needed |
| `serve/kanban/tests/test_engine_move_claim.py` | IN (docstrings) | Test file — no public API docstrings; N/A |
| `serve/kanban/README.md` | IN (package README) | Updated `move_task` method table entry |

### Files Updated
- `serve/kanban/README.md` — commit `392bd0c3`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None
[[2026-04-25]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC4 archive without reason | test_engine_move_claim.py L195-207, exact ERR_ARCHIVAL_REASON_REQUIRED assertion | PASS |
| AC5 completed archive from non-terminal | test_engine_move_claim.py L209-223, exact ERR_COMPLETED_REQUIRES_DONE | PASS |
| AC7 deprecated archive without refs | test_engine_move_claim.py L225-239, exact ERR_ARCHIVAL_REFS_REQUIRED | PASS |
| AC8 dropped archive with refs | test_engine_move_claim.py L241-255, exact ERR_ARCHIVAL_REFS_FORBIDDEN | PASS |
| AC9 invalid archival reason enum | test_engine_move_claim.py L257-271, exact ERR_ARCHIVAL_REASON_INVALID | PASS |
| AC26 archival ref missing | test_engine_move_claim.py L273-288, exact ERR_ARCHIVAL_REF_MISSING | PASS |
| archival fields forbidden on active status | test_engine_move_claim.py L290-304, exact ERR_ARCHIVAL_FIELDS_FORBIDDEN | PASS |
| D15 predicate failure | test_engine_move_claim.py L306-320, exact ERR_PREDICATE_FAILED | PASS |
| D41 predicate failure no move | test_engine_move_claim.py L322-338, unchanged-status assertion | PASS |
| D17 archive clears claim (return) | test_engine_move_claim.py L340-355, claimed_at is None | PASS |
| D17 archive clears claim (persistence + location) | test_engine_move_claim.py L357-382, file in archive/ not tasks/, fresh engine reread | PASS |
| D17 rollback on _move_file failure | test_engine_move_claim.py L422-452, patches _move_file, asserts tasks/ restored, status/claimed_at preserved | PASS |
| AC-NEW-5 skip guidance | test_engine_move_claim.py L385-396, non-empty guidance with "skip" | PASS |
| AC-NEW-16 move missing id | test_engine_move_claim.py L398-406, NotFoundError(ERR_NOT_FOUND) | PASS |
| Invalid status enum | test_engine_move_claim.py L408-420, ValidationError(ERR_INVALID_STATUS) | PASS |
| start_work blocked | test_engine_move_claim.py L475-493, exact ERR_BLOCKED_NOT_CLAIMABLE | PASS |
| start_work archived | test_engine_move_claim.py L495-514, exact ERR_ARCHIVED_NOT_CLAIMABLE | PASS |
| AC-NEW-16 start_work missing id | test_engine_move_claim.py L516-524, NotFoundError(ERR_NOT_FOUND) | PASS |
| start_work already claimed | test_engine_move_claim.py L526-544, ConcurrencyError(ERR_ALREADY_CLAIMED) | PASS |
| D18+D36 expired claim re-claim | test_engine_move_claim.py L548-563, claimed_at != stale timestamp | PASS |

### Test Results
- pytest (full suite): 2099 passed, 165 failed, 209 errors, 4 skipped
- Task-scoped tests: all 20 passed, 0 failed
- Broad failures: ConfigError agent_map validation + KanbanEngine.__init__ agent_name signature mismatch — all unrelated to #1073 move/start_work scope
- ruff: clean on engine.py + test_engine_move_claim.py; 8 violations in other packages (knowledge, mcp-knowledge, mcp-memory, orchestrator) — not #1073 scope

### Architect Quality: 4/5
Initial AC included unverifiable RED-phase line and ambiguous coverage scope, causing unnecessary review cycles. Architect was responsive through 3 refinement rounds: struck RED AC, clarified coverage gate, tightened D17 (file-location) and D18+D36 (timestamp-discrimination), added _move_file rollback proof AC. Final AC state is strong.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 20 live AC lines have task-owned passing tests)
- Lint violations in task scope: 0
- AC quality score 4 > 3: no deduction
- Missing reviewer evidence: 0 (5th reviewer section present, detailed, PASS at 0.93)
- Full-suite failures in task scope: 0

### Confidence: .98
### Action: archive