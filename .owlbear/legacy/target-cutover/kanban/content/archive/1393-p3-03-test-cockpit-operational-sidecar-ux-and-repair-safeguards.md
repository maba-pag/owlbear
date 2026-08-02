---
id: 1393
title: 'P3-03: Test Cockpit operational sidecar UX and repair safeguards'
status: archived
priority: medium
created: 2026-05-06T01:09:38.127439+00:00
updated: 2026-05-08T12:05:03.641903+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:test
- frontend
- sidecar
- activity
- health
- repair
- interface-contract
parent: 1363
depends_on:
- 1367
- 1373
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests proving the operational sidecar has correct session types, usable activity navigation, and safe health repair safeguards.

## Problem Evidence
- ActivityTab rows are clickable divs with raw spans, no active filter state, and raw numeric durations.
- The frontend Session type assumes task_id is a number and agent is a string, while the backend SessionRecord allows null for both (serve/kanban/src/owlbear_kanban/models.py:547).
- ActivityTab passes subtab 'history' to onSelectTask, but Shell drops it (Shell.tsx line 238 uses only taskId).
- HistorySubtab is reachable from DetailTab's History button (DetailTab.tsx:229) but the subtab hint from ActivityTab never reaches it.
- RepairPanel confirmation dialog is generic ("repair N corrupted files"), omits affected file list, quarantine destination, and explicit consequences. RepairPanel only receives corruptionCount, not file details.

## Acceptance Criteria
- Tests prove frontend Session type and rendering accept null task_id and null agent values (matching backend SessionRecord nullability) without crashing, displaying literal "null" text, or NaN. (td:2)
- Tests prove activity filter buttons show observable active/inactive state (via aria attribute, data attribute, or variant change) and session rows display human-readable durations (not raw numeric seconds). (td:2)
- Tests prove ActivityTab renders empty state (no sessions matching filter) and error state, without duplicating existing coverage in ActivityTab_1156 or ActivityTab_1278 suites. (td:2)
- Tests prove session rows use semantic interactive roles (not bare div-with-onClick) for accessible click navigation. (td:1)
- Tests prove the `history` subtab hint from ActivityTab is either consumed by Shell to navigate to DetailTab's HistorySubtab, or the test exposes the current routing gap (Shell drops the hint at line 238) for #1394 to fix. (td:1)
- Tests prove repair confirmation dialog includes affected file details when available via props, categorizes outcomes (fixed/quarantined/failed), and states destructive or quarantine consequences explicitly. Must extend beyond existing RepairPanel_1167 coverage. (td:2)
- Tests prove repair retry and refetch use `getResponseErrorMessage` from `api/errorMessage.ts` (error contract from #1375). Dismiss is local state reset, not subject to the error contract. (td:2)
- All new proofs are RED-phase: expected to fail against current head. Failing proofs are suitable for #1394 to satisfy. (td:1)

## Scope
- In scope: Cockpit frontend Session type nullability tests, sidecar activity UX tests, subtab routing coherence tests, and health repair safeguard tests.
- Out of scope: dashboard visual layout from #1392, global accessibility gate from #1396, backend health false-OK implementation from #1373, cache/SSE invalidation from #1346.
- Existing coverage context: Shell_1372 tests cover scan loading/error/retry. RepairPanel_1167 tests cover basic dismiss and dialog flow. ActivityTab_1156 covers HistorySubtab row rendering and click-through. New tests must not duplicate these.

## Counterpart
Implementation task: #1394.

[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All AC lines concern the operational sidecar UX (Activity, Health, Repair) |
| Interface clarity | PASS | Each AC line specifies the exact contract to test, with module references |
| Dependency correctness | PASS | #1367, #1373, #1375 all archived (done) |
| Module layering | N/A | Test task — no production module changes |
| TDD compliance | PASS | This IS the RED-phase test task, paired with #1394 |
| KISS/YAGNI | PASS | AC scoped to audited defects only; no speculative requirements |
| Premise challenge | PASS | Session type mismatch, raw durations, weak repair confirmation all confirmed in live code |
| Pattern consistency | PASS | Follows existing Vitest component test patterns (ActivityTab_1156, RepairPanel_1167) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Codebase Evidence
- Backend SessionRecord (models.py:547): `task_id: int | None`, `agent: str | None = None`
- Frontend Session (HistorySubtab.tsx:3-9): `task_id: number`, `agent: string` — no null allowed
- Shell.tsx:238: `(taskId) => setSelectedTaskId(taskId)` drops subtab parameter
- ActivityTab.tsx:87: passes `onSelectTask?.(s.task_id, 'history')` — hint sent but Shell drops it
- HistorySubtab rendered in DetailTab.tsx:335 via showHistory toggle (line 229 History button) — NOT dead code
- RepairPanel.tsx:45-48: confirmation says "repair {requestedCount} corrupted files" — no file list, no quarantine path
- RepairPanel only receives corruptionCount prop (HealthBadge.tsx:54), not file details

### AC Refinements Applied
1. Removed ungrounded "formatted timestamps" claim (ActivityTab renders no timestamps)
2. Corrected HistorySubtab from "appears unused" to "reachable from DetailTab but subtab routing broken"
3. Separated dismiss (local state reset) from network error contract (retry/refetch)
4. Added existing coverage deduplication constraints (Shell_1372, RepairPanel_1167, ActivityTab_1156)
5. Specified observable signals for active filter state (aria/data attribute/variant change)
6. Added null rendering contract (no literal "null" text, no NaN, no crash)
7. Updated Problem Evidence with specific file:line references

### Challenge Results
- Challenger: reconsider (confidence: 0.62)
- Findings addressed: (1) ungrounded timestamp requirement removed, (2) existing test coverage overlap scoped via deduplication constraints, (3) error-contract dismiss carved out, (4) HistorySubtab routing corrected with code evidence, (5) repair file list prop gap acknowledged
- Architect response: accepted all findings, rewrote AC and Problem Evidence accordingly

### Test Depth
- Max depth: 2
- Test-writer: PROCEED
- td:2 lines: null type handling, filter active state, empty/error states, repair confirmation, error contract usage
- td:1 lines: semantic row roles, subtab routing, RED-phase validity

### Verdict: APPROVE
### Action Taken: Refined 7 original AC lines into 8 precise lines with codebase evidence, deduplication constraints, and challenger-driven corrections. `type:test` tag present for test-writer pass-through. Advancing to todo.
[[2026-05-08]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx`

**Classes and test distribution:**

| Class | AC | Count | Category |
|---|---|---|---|
| `TestFromAC_SessionNullability` | AC1 | 5 | edge/error/boundary |
| `TestFromAC_FilterActiveState` | AC2 | 4 | happy/edge/boundary |
| `TestFromAC_HumanReadableDuration` | AC2 | 4 | edge/boundary |
| `TestFromAC_ActivityEmptyAndError` | AC3 | 3 | edge/error |
| `TestFromAC_SessionRowSemanticRoles` | AC4 | 4 | happy/boundary |
| `TestFromAC_SubtabRoutingGap` | AC5 | 1 | error (integration) |
| `TestFromAC_RepairConfirmationDetails` | AC6 | 4 | edge/error |
| `TestFromAC_RepairErrorContract` | AC7 | 2 | error/boundary |

**Total: 27 tests — all FAIL (verified via `npx vitest run`)**

**AC coverage:**
| AC | Tests | Status |
|---|---|---|
| AC1: Session nullability (null task_id/agent) | 5 | RED |
| AC2: Filter active state + human-readable duration | 4+4 | RED |
| AC3: ActivityTab empty/error states | 3 | RED |
| AC4: Semantic interactive roles | 4 | RED |
| AC5: Subtab routing gap Shell→DetailTab | 1 | RED |
| AC6: Repair confirmation file details + consequences | 4 | RED |
| AC7: Repair retry mechanism (error contract) | 2 | RED |

**Key failure reasons (against current head):**
- AC1: React renders null as empty string `''` — fallback assertions fail; `onSelectTask(null, ...)` called directly
- AC2: No `aria-pressed` attribute on filter buttons; durations rendered as raw numbers
- AC3: No `[data-testid="activity-empty"]` or `[data-testid="activity-error"]` elements
- AC4: Session rows are bare `<div onClick>` — no `role="button"`, no `tabIndex`
- AC5: Shell.tsx:238 drops subtab hint — `history-view` never appears after ActivityTab click
- AC6: No `files` prop on `RepairPanel`; confirmation text lacks "irreversible"/"quarantine directory"
- AC7: No `[data-testid="repair-retry-btn"]` in error phase

**Deduplication:** No overlap with ActivityTab_1156, ActivityTab_1278, RepairPanel_1167, or Shell_1372 confirmed.

**ESLint:** CLEAN  
**Commit:** ce95a391
[[2026-05-08]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/components/HistorySubtab.tsx, serve/cockpit/web/src/components/ActivityTab.tsx, serve/cockpit/web/src/components/RepairPanel.tsx, serve/cockpit/web/src/components/HealthBadge.tsx, serve/cockpit/web/src/components/DetailTab.tsx, and serve/cockpit/web/src/Shell.tsx.
- Tests: 27/27 TestFromAC tests passed in serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx.
- Coverage: not collected in scoped frontend quality-runner mode (task suite fully green).
- ruff/eslint: eslint clean on all changed files.
- Approach: implemented null-safe session rendering and click guards, added observable filter active-state attributes, human-readable integer duration formatting, activity empty/error states, semantic interactive row roles, subtab hint propagation from Activity->Shell->DetailTab, and repair confirmation/retry safeguards with file detail visibility.
- Commit: 961c3f47 (`feat: implement sidecar UX safeguards (#1393, builder)`).

### Evidence Summary
- RED verified before implementation: 27 failed / 0 passed on SidecarUX_1393.
- GREEN verification after implementation: 27 passed / 0 failed on SidecarUX_1393.
- Neighbor regression context: ActivityTab_1156 and RepairPanel_1167 suites pass with these changes; Shell_1372 has one pre-existing expectation mismatch in scan-error message text unrelated to task 1393 acceptance criteria.

### Fixes Applied
- AC1: Session model now tolerates null `task_id`/`agent` and renders non-empty fallbacks; navigation is guarded from null task IDs.
- AC2: Filter buttons expose `aria-pressed`; durations are no longer raw integers in activity/history rows.
- AC3: Activity tab now renders explicit `activity-empty` and `activity-error` states.
- AC4: Session rows in activity/history now expose semantic interactive affordances (`role="button"`, `tabIndex=0`, keyboard activation).
- AC5: Activity subtab hint (`history`) is carried through Shell and consumed by DetailTab rendering path.
- AC6: Repair confirmation now includes explicit irreversible/quarantine consequences and optional affected-file listing via props.
- AC7: Repair error phase now exposes retry action (`repair-retry-btn`) wired to `confirmRepair`.

### Post-task Reflection
- A subtle routing test remained red after most ACs were green; making subtab hint consumption explicit at render-time removed state-order fragility.
- Neighbor-suite expectations around legacy duration formatting required preserving decimal display while still humanizing integer second values.
- Scoped quality-runner iterations were effective for quickly isolating a single failing integration assertion without broad-suite churn.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run on `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx`: 27 passed, 0 failed, 0 skipped
- eslint clean; VS Code diagnostics clean on changed files and the task test file

### Coverage
- Scoped frontend coverage: `Shell.tsx` 78.94, `ActivityTab.tsx` 87.12, `HistorySubtab.tsx` 70.58, `DetailTab.tsx` 50.86, `HealthBadge.tsx` 84.00, `RepairPanel.tsx` 35.48
- Coverage is not the gating issue here. The rejection is for proof quality, not an implementation coverage miss.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 nullability without literal `null`/`NaN` | Source fallbacks and guards exist in `serve/cockpit/web/src/components/ActivityTab.tsx:156-157`, `serve/cockpit/web/src/components/HistorySubtab.tsx:60`, `serve/cockpit/web/src/components/ActivityTab.tsx:86`, and `serve/cockpit/web/src/components/HistorySubtab.tsx:37`. Task tests at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:230`, `:241`, `:266`, `:291`, `:315` only assert non-empty text or no null callback, so they would still pass on literal `null` or `NaN` text. | FAIL |
| AC2 active state + human-readable duration | Filter-state proof is strong at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:331`, `:339`, `:347`, `:355` against `serve/cockpit/web/src/components/ActivityTab.tsx:97`, `:105`, `:113`, `:121`, `:129`. Duration proof is incomplete: `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:385` proves human-readable output for `HistorySubtab`, but `:417` only rejects raw `120` for `ActivityTab` while the formatter contract lives in `serve/cockpit/web/src/components/ActivityTab.tsx:14-29`. | FAIL |
| AC3 empty/error state without duplicating 1156/1278 | Task tests at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:462`, `:477`, `:498` cover empty/error rendering against `serve/cockpit/web/src/components/ActivityTab.tsx:136`, `:138`. Adjacent suites `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx:409-598` and `serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx:69-292` cover different concerns, so the non-duplication constraint is satisfied. | PASS |
| AC4 semantic interactive roles | Exact role/tabIndex assertions at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:534`, `:556`, `:563`, `:570` match `serve/cockpit/web/src/components/ActivityTab.tsx:145-146` and `serve/cockpit/web/src/components/HistorySubtab.tsx:49-50`. | PASS |
| AC5 history subtab hint consumed | Integration assertion at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:659` matches `serve/cockpit/web/src/Shell.tsx:219`, `:249` and `serve/cockpit/web/src/components/DetailTab.tsx:76`, `:80`, `:351-352`. | PASS |
| AC6 repair confirmation details + consequences | Task tests at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:682`, `:691`, `:709`, `:730-731` cover irreversible/quarantine wording and file-list extension against `serve/cockpit/web/src/components/RepairPanel.tsx:35`, `:41-42`. Existing `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx:231`, `:237`, `:243` already proves grouped fixed/quarantined/failed results, which is consistent with the AC's non-duplication constraint. | PASS |
| AC7 repair retry/refetch uses `getResponseErrorMessage` | The real helper path exists at `serve/cockpit/web/src/api/repair.ts:1`, `:15` and `serve/cockpit/web/src/hooks/useRepairFlow.ts:68`. The task suite mocks `useRepairFlow` at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:39-40`, `:147` and only asserts a mocked `confirmRepair` call at `:764`, so the named helper/refetch contract is not proven. | FAIL |
| AC8 RED-phase evidence | Historical evidence exists in `.owlbear/kanban/tasks/1393-p3-03-test-cockpit-operational-sidecar-ux-and-repair-safeguards.md:127`, and commit `ce95a391` exists in `.git/logs/HEAD:2245`. I could not independently replay the RED snapshot from this tool surface, so this is a confidence deduction rather than a routing reason. | PASS |

### Deductions
- `-0.08` AC1 proof gap: non-empty assertions do not exclude literal `null`/`NaN`
- `-0.05` AC2 proof gap: the `ActivityTab` duration assertion would accept non-human garbage output
- `-0.10` AC7 proof gap: the mocked repair hook bypasses the named error-helper contract
- `-0.03` TestFromAC immutability and dirty-tree contamination could not be fully verified without `git diff` / `git status`; commit existence only confirmed via `.git/logs/**`

### Verdict
- FAIL. Implementation paths are present and the task suite is green, but AC1, AC2, and AC7 are not actually proven by discriminating task-owned assertions.
- Confidence: `0.74`
- Action: reject to `todo` for test-writer strengthening. This is a first-cycle proof failure, not a builder source regression.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC1 nullability tests to reject literal `null`/`NaN` text and pin exact fallback behavior for `ActivityTab` and `HistorySubtab` | `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx` | `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:230`, `:266`, `:291` only assert non-empty text; source fallbacks are at `serve/cockpit/web/src/components/ActivityTab.tsx:156-157` and `serve/cockpit/web/src/components/HistorySubtab.tsx:60` |
| 2 | test-writer | Strengthen AC2 `ActivityTab` duration proof to assert a human-readable format, not only `!= "120"` | `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx` | `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:417` vs formatter contract in `serve/cockpit/web/src/components/ActivityTab.tsx:14-29` |
| 3 | test-writer | Add task-owned proof that the repair retry/error path exercises `getResponseErrorMessage` through `repairStorage` / `useRepairFlow`, while keeping dismiss as local-state-only behavior | `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx` | Task suite mocks `useRepairFlow` at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:39-40`, `:147` and only asserts a mocked `confirmRepair` call at `:764`; the real helper path is in `serve/cockpit/web/src/api/repair.ts:1`, `:15` and `serve/cockpit/web/src/hooks/useRepairFlow.ts:68` |
[[2026-05-08]]
## Test-Writer Notes

**Retry — surgical fill mode (Step 1b.1)**

Reviewer identified 3 proof gaps. All new tests PASS against current implementation (builder #1394 already done), so advancing directly to review.

**New tests added: 7** (34 total, 27 preserved)

| Gap | New Class | Tests | Resolution |
|---|---|---|---|
| AC1: non-empty ≠ not-"null" | `TestFromAC_SessionNullabilityStrong` | 3 | Added explicit `not.toBe('null')` + `not.toContain('NaN')` assertions for HistorySubtab agent, ActivityTab agent, and ActivityTab task_id spans |
| AC2: ActivityTab duration `!= "120"` too weak | `TestFromAC_ActivityDurationFormat` | 1 | Pinned exact `toBe('2m')` for 120s session in ActivityTab |
| AC7: useRepairFlow mock bypasses error contract | `TestFromAC_RepairErrorContractProof` | 3 | Direct `repairStorage()` calls with controlled fetch stubs: (1) JSON body message surfaces via `getResponseErrorMessage`, (2) fallback when no message field, (3) dismiss in done phase calls `dismissResults` without any network request |

**Verification:**
- 34/34 pass (`npx vitest run SidecarUX_1393.test.tsx`)
- ESLint: CLEAN
- Commit: af33e9bb

**AC coverage (retry):**
| AC | Status |
|---|---|
| AC1 nullability — no literal "null"/"NaN" | Strengthened |
| AC2 duration — exact "2m" for 120s | Strengthened |
| AC7 error contract — repairStorage uses getResponseErrorMessage | Proven via direct API test |
[[2026-05-08]]
## Builder Notes
- Implementation: no file changes in this builder retry cycle.
- Tests: 34/34 passed in serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx.
- Coverage: not requested in scoped frontend verification.
- eslint: clean.
- Approach: verification-only pass after test-writer retry. Reviewer findings were proof-quality gaps in tests; test-writer strengthened assertions and contract coverage, and the current implementation satisfies the revised task-owned proofs.

### Evidence Summary
- quality-runner scoped run: passed=34, failed=0, skipped=0 on SidecarUX_1393.
- quality-runner lint run: clean=true, violations=0 across task test + sidecar-related source files.
- No reproducible implementation defect remains for task 1393 in this cycle.

### Post-task Reflection
- This retry confirms the failure mode was proof strength, not source behavior; builder edits would have been churn.
- Scoped quality-runner evidence was sufficient to resolve the in-progress loop quickly.
- Keeping builder cycles surgical avoided accidental regressions in adjacent sidecar flows.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 145 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx`, `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx`, `serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx`, and `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`.
- Scoped eslint run was clean on `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ActivityTab.tsx`, `serve/cockpit/web/src/components/HistorySubtab.tsx`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/components/HealthBadge.tsx`, `serve/cockpit/web/src/components/RepairPanel.tsx`, and `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx`.
- VS Code diagnostics on the same scope: no errors.

### Coverage
- Current quality-runner frontend run could not emit scoped coverage because the frontend Vitest config in this session did not expose a coverage block. I treated that as a confidence deduction, not a failure: the task suite and adjacent regression suites are green, and the changed source paths were read directly.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: Session type/rendering accept null `task_id` and null `agent` without crash, literal `null`, or `NaN` | Source contract is nullable in `serve/cockpit/web/src/components/HistorySubtab.tsx:4` and `:6`; null navigation is guarded in `serve/cockpit/web/src/components/HistorySubtab.tsx:37`-`:38` and `serve/cockpit/web/src/components/ActivityTab.tsx:86`-`:87`; fallback rendering is in `serve/cockpit/web/src/components/HistorySubtab.tsx:60` and `serve/cockpit/web/src/components/ActivityTab.tsx:156`-`:157`. Task tests reject null navigation at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:242` and `:316`, and reject literal `null` / `NaN` text at `:785`-`:786`, `:810`-`:811`, and `:835`-`:836`. | PASS |
| AC2: Observable filter state and human-readable durations | Filter state is surfaced by `aria-pressed` in `serve/cockpit/web/src/components/ActivityTab.tsx:97`, `:105`, `:113`, `:121`, `:129`; tests assert those states at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:327`-`:358`. Human-readable duration formatting is implemented in `serve/cockpit/web/src/components/ActivityTab.tsx:14` and `:159` plus `serve/cockpit/web/src/components/HistorySubtab.tsx:17` and `:61`; tests reject raw values at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:378`, `:386`, `:418`, and pin `120s -> 2m` at `:871`. | PASS |
| AC3: Activity empty/error state without duplicating 1156/1278 | Empty and error states are rendered in `serve/cockpit/web/src/components/ActivityTab.tsx:136` and `:138`; task tests assert them at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:461`, `:478`, and `:499`. Adjacent suites remain scoped to other concerns at `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx:416` and `serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx:69`, and they are green in the current review run. | PASS |
| AC4: Semantic interactive roles for session rows | Semantic affordances exist in `serve/cockpit/web/src/components/ActivityTab.tsx:145`-`:146` and `serve/cockpit/web/src/components/HistorySubtab.tsx:49`-`:50`; task tests assert role/tabIndex at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:516`, `:557`, `:560`, and `:571`. | PASS |
| AC5: History subtab hint is consumed end-to-end | Shell threads the subtab via `serve/cockpit/web/src/Shell.tsx:216`, `:219`, and `:249`; DetailTab consumes it in `serve/cockpit/web/src/components/DetailTab.tsx:76`, `:80`, `:351`, and `:352`. The integration proof is `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:660`. | PASS |
| AC6: Repair confirmation details, outcome categorization, and explicit consequences | Confirmation dialog and consequence copy are in `serve/cockpit/web/src/components/RepairPanel.tsx:35`, `:41`, and `:42`; file-detail propagation is wired in `serve/cockpit/web/src/components/HealthBadge.tsx:54`. Task tests cover dialog copy and file details at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:678`, `:689`, `:707`, and `:728`. Existing grouped-outcome coverage remains present and green at `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx:231`, `:237`, and `:243`, satisfying the non-duplication constraint while preserving category proof. | PASS |
| AC7: Repair retry/refetch use `getResponseErrorMessage`; dismiss is local-only | The helper path is live in `serve/cockpit/web/src/api/repair.ts:15` and `serve/cockpit/web/src/hooks/useRepairFlow.ts:68`. Task tests assert retry affordance and retry-to-confirm flow at `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx:754`, `:757`, and `:765`; direct `repairStorage()` tests pin helper-driven body/fallback error behavior at `:886`, `:899`, and `:914`; dismiss-local-state behavior is pinned at `:926`. | PASS |
| AC8: RED-phase evidence suitable for #1394 | Historical task evidence records the RED snapshot and later strengthening at `.owlbear/kanban/tasks/1393-p3-03-test-cockpit-operational-sidecar-ux-and-repair-safeguards.md:163`, `:222`, `:235`, and `:248`. Commit chronology for the RED, builder, and retry commits is present in `.git/logs/HEAD:2245`, `:2248`, and `:2269`. I could not replay the pre-builder snapshot directly from this tool surface, so this remains a confidence deduction rather than a failure. | PASS |

### Security / Data Safety
- No security or data-safety issues found in the scoped frontend changes. The reviewed paths perform local UI state updates and fixed-route fetches; no new injection, secret, traversal, or unsafe-deserialization patterns were introduced.

### Informational
- `serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx` still contains some stale RED-phase commentary and a few `as unknown as Session` fixtures. Those weaken future compile-time regression sensitivity, but on this record they do not negate the current nullable source contract or the strengthened runtime assertions.

### Deductions
- `-0.03` Could not independently run commit-scoped dirty-tree / test-immutability diff checks from this tool surface; commit existence was confirmed via `.git/logs/HEAD` only.
- `-0.03` Current quality-runner frontend pass could not emit scoped coverage in this session.
- `-0.03` AC8 RED-phase evidence relied on task-body history and git-log chronology rather than a direct replay of the pre-builder snapshot.

### Verdict
- PASS. The strengthened task suite, adjacent green regressions, and direct source inspection collectively satisfy the acceptance criteria.
- Confidence: `0.91`
- Action: advance to docs.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope README/guide references ActivityTab, HistorySubtab, RepairPanel, Shell, DetailTab, or HealthBadge by name. serve/cockpit/README.md covers backend API surface, not frontend component internals. |
| 2 | Module docstrings | No | N/A | All changed files are TypeScript (.tsx) — Python docstring rule does not apply. |
| 3 | External attribution | No | N/A | No new external patterns cited in Builder Notes or Review Evidence. |
| 4 | Research doc | No | N/A | No .owlbear/research/ doc produced for this test task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | share/diagrams/cockpit.excalidraw describes: serve/cockpit/web/src/**. Changed files are under that glob. Footer updated to "Last verified: 2026-05-08 (3e98d0be)". Commit: 356a0ac0. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted in this task. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/HistorySubtab.tsx | OUT (app source .tsx) | N/A |
| serve/cockpit/web/src/components/ActivityTab.tsx | OUT (app source .tsx) | N/A |
| serve/cockpit/web/src/components/RepairPanel.tsx | OUT (app source .tsx) | N/A |
| serve/cockpit/web/src/components/HealthBadge.tsx | OUT (app source .tsx) | N/A |
| serve/cockpit/web/src/components/DetailTab.tsx | OUT (app source .tsx) | N/A |
| serve/cockpit/web/src/Shell.tsx | OUT (app source .tsx) | N/A |
| serve/cockpit/web/src/__tests__/SidecarUX_1393.test.tsx | OUT (test file) | N/A |
| share/diagrams/cockpit.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: 2026-05-08, 3e98d0be)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/1393-* files found)
[[2026-05-08]]
## Planning

Created 1 follow-up task:

| ID | Title | Status | Priority | Tags | Depends |
|----|-------|--------|----------|------|---------|
| #1436 | Fix HealthBadgeRepair_1168 assertion mismatch from #1393 RepairPanel changes | backlog | needed | cockpit, frontend, scope:cockpit-web | #1393 |

Single-task shortcut — test assertion string update only, no TDD pair needed (existing tests already cover the behavior, just need string alignment).[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Session null task_id/agent | Source guards at ActivityTab.tsx:86-87, HistorySubtab.tsx:37-38; fallbacks at ActivityTab.tsx:156-157, HistorySubtab.tsx:60; tests reject literal "null"/NaN at SidecarUX_1393:785-836 | PASS |
| AC2: Filter active state + human-readable duration | aria-pressed on 5 filter buttons (ActivityTab.tsx:97-129); formatDuration at ActivityTab.tsx:14,159 and HistorySubtab.tsx:17,61; pinned 120s→"2m" at SidecarUX_1393:871 | PASS |
| AC3: Empty/error state | activity-empty/activity-error in ActivityTab.tsx:136,138; tests at SidecarUX_1393:461-498; no overlap with 1156/1278 suites | PASS |
| AC4: Semantic interactive roles | role="button" + tabIndex=0 at ActivityTab.tsx:145-146, HistorySubtab.tsx:49-50; tests at SidecarUX_1393:534-571 | PASS |
| AC5: Subtab routing gap | Shell.tsx:219,249 threads subtab; DetailTab.tsx:76,80,351-352 consumes; integration test at SidecarUX_1393:660 | PASS |
| AC6: Repair confirmation details | RepairPanel.tsx:35,41-42 has irreversible/quarantine copy + file list; tests at SidecarUX_1393:678-731 | PASS |
| AC7: Repair error contract | repairStorage at repair.ts:15 + useRepairFlow.ts:68 proven via direct API tests at SidecarUX_1393:886-926; dismiss is local-only | PASS |
| AC8: RED-phase evidence | Commit chronology: ce95a391 (RED) → 961c3f47 (GREEN) → af33e9bb (strengthen) | PASS |

### Test Results
- vitest (full): 1105 passed, 2 failed (HealthBadgeRepair_1168 — assertion text mismatch from #1393 RepairPanel.tsx changes, follow-up #1436 created)
- pytest (full): 2949 passed, 188 failed, 6 errors — all failures unrelated (task is frontend-only, no Python changes)
- eslint: clean on all task-scope files
- ruff: violations in unrelated files only

### Architect Quality: 5/5
AC was specific, with codebase evidence at file:line, challenger-driven corrections (7 refinements), deduplication constraints, and test depth markers.

### Deduction Breakdown
- -.05 Full-suite regression: HealthBadgeRepair_1168 (2 tests) broken by #1393 RepairPanel confirmation text change. Follow-up #1436 created at backlog.

### Confidence: 0.95
### Action: archive

### Commits Verified
| Commit | Type | Agent |
|--------|------|-------|
| ce95a391 | test (RED) | test-writer |
| 961c3f47 | feat (GREEN) | builder |
| af33e9bb | test (strengthen) | test-writer |
| 356a0ac0 | docs (diagram) | doc-writer |
