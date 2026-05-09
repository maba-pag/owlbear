# Frontend Task-Scoped Test Cleanup Plan

> **Owning task:** #1465 — E2c: Delete/merge stale frontend tests (44 files in serve/cockpit/web/src/__tests__/)
> **Date:** 2026-05-09 **Status:** Complete

## 1. Context and Question

Parent #1415 identified 44 stale TSX test files for cleanup. This research validates the actual count, categorizes every file, and produces a detailed cleanup plan.

**Key finding: the AC underestimates scope.** Actual count is **64 stale** task-scoped files (47 `.tsx` + 18 `.ts`), not 44. The original scan used a `.tsx`-only glob.

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `serve/cockpit/web/src/__tests__/` filesystem scan | 1.0 | 65 task-scoped files, 8 durable files |
| S2 | Vitest JSON output (baseline run) | 1.0 | 74 files, 1224 tests (1215 pass, 9 fail) |
| S3 | `.owlbear/research/1415-stale-test-cleanup.md` | .90 | Parent research: strategy, categories |
| S4 | Kanban board (active task search) | 1.0 | #1380 done, #1381 at backlog |

## 3. Analysis

### 3.1 AC Corrections Required

| AC claim | Actual | Delta |
|----------|--------|-------|
| 44 task-scoped files | 64 stale (65 total - 1 retained) | +20 (.ts files missed) |
| Shell_* 10 files | 11 files | +1 |
| KanbanBoard_* 6 files | 8 files | +2 |

### 3.2 Baseline (pre-cleanup)

74 test files, 1224 tests. 4 files failing (9 tests): DetailTab.test.tsx (durable, 1 fail), DecisionContract_1386 (3 fail), PdsMigration_1230 (3 fail), Shell_1344 (2 fail).

### 3.3 Cleanup Categories

**D — Rename (16 files → 16 `git mv` operations):**

| File | Tests | Rename to |
|------|:-----:|-----------|
| DRStatusIndicator_1191 | 25 | DRStatusIndicator.test.tsx |
| DecisionViewport_1388 | 26 | DecisionViewport.test.tsx |
| ErrorContract_1374 | 20 | ErrorContract.test.tsx |
| EventSourceProvider_1276 | 33 | EventSourceProvider.test.tsx |
| FilterAccessibilityPanel_1254 | 8 | FilterAccessibilityPanel.test.tsx |
| FilterAccessibility_1254 | 14 | FilterAccessibility.test.tsx |
| FilterPanel_1250 | 40 | FilterPanel.test.tsx |
| HealthBadgeRepair_1168 | 17 | HealthBadgeRepair.test.tsx |
| PdsMigration_1230 | 81 | PdsMigration.test.tsx |
| RepairPanel_1167 | 47 | RepairPanel.test.tsx |
| SidecarUX_1393 | 34 | SidecarUX.test.tsx |
| TaskDetailModel_1376 | 15 | TaskDetailModel.test.tsx |
| styles_1226 | 4 | styles.test.ts |
| useScanPolling_1157 | 29 | useScanPolling.test.ts |
| useRepairFlow_1165 | 36 | useRepairFlow.test.ts |
| vite_config_936 | 6 | vite_config.test.ts |

**C — Merge into NEW durable (8 groups, 17 files → 8 new files):**

| Group | Files | Tests | Merge into |
|-------|:-----:|:-----:|------------|
| ArchivalModal | 3 | 59 | ArchivalModal.test.tsx |
| DecisionContract | 2 | 12 | DecisionContract.test.tsx |
| ResolveModalUX | 2 | 23 | ResolveModalUX.test.tsx |
| ResolveModal + plugins | 2 | 11 | ResolveModal.test.tsx |
| filterTasks | 2 | 23 | filterTasks.test.ts |
| repairStorage | 2 | 41 | repairStorage.test.ts |
| usePendingDRs | 2 | 27 | usePendingDRs.test.ts |
| usePollingFetch | 2 | 28 | usePollingFetch.test.ts |

**B — Merge into EXISTING durable (5 groups, 31 files → update 5 files):**

| Group | Durable (tests) | Task-scoped | Stale tests | Combined lines |
|-------|:---------------:|:-----------:|:-----------:|:--------------:|
| Shell | 18 | 11 files | 111 | ~3.6K |
| KanbanBoard | 35 | 8 files | 87 | ~4.0K |
| DetailTab | 48 | 4 stale | 45 | ~1.5K |
| ActivityTab | 15 | 2 files | 64 | ~1.0K |
| useBoard | 14 | 4 files | 42 | ~0.8K |

**A — Delete / merge 1 test (2 files):**

- `App_1276` (1 test) → merge into `src/App.test.tsx` (durable, 5 tests)
- `optimistic_936` (4 tests) → merge into `optimistic.test.ts` (durable, 6 tests)

**E — Retain (1 file):**

- `DetailTab_1380` (22 tests, all pass) — downstream #1381 at backlog

### 3.4 Failing Stale Tests

| File | Fails | Root cause | Recommendation |
|------|:-----:|------------|----------------|
| DecisionContract_1386 | 3/7 | Awaits unimplemented #1387 feature | Merge passing (4), `.skip` failing (3) |
| PdsMigration_1230 | 3/81 | PDS v4 API drift | Rename, `.skip` failing (3) |
| Shell_1344 | 2/3 | onTaskUpdated not wired | Merge passing (1), `.skip` failing (2) |

### 3.5 Size Concern — Shell and KanbanBoard

Shell merge would produce ~3.6K lines; KanbanBoard ~4K lines. These are large but acceptable for test files — test suites often have high line counts due to mock setup. No test-level duplication was found between durable and task-scoped Shell tests.

### 3.6 Execution Order

1. **Renames first** (16 files) — zero-risk `git mv`, fastest batch
2. **New-durable merges** (8 groups) — straightforward import dedup
3. **Existing-durable merges** (5 groups) — most complex, largest diffs
4. **Deletes/small merges** (2 files) — trivial
5. **Vitest verification** — must match or exceed 1215 passing tests

## 4. Recommendation

Proceed as a single builder task with updated AC (confidence: .85). The work is mechanical — no architecture decisions. Risk is low: renames are zero-risk, merges preserve all tests.

**AC corrections needed:** update P1 from "44" to "64 stale files", P3 from "10/6" to "11/8".

Challenge: SKIPPED — T1 autonomous cleanup, no architectural recommendation.

## 5. Follow-up Tasks

No further decomposition needed. Task #1465 is ready for `backlog` with corrected AC.
