---
id: 1365
title: 'P1-02: Fix Cockpit PDS v4 build compatibility'
status: review
priority: critical
created: 2026-05-06T00:58:31.995607+00:00
updated: 2026-05-06T08:53:55.988372+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:build
- frontend
- design-system
- build
parent: 1363
depends_on:
- 1364
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Resolve Cockpit frontend PDS v4 build and type compatibility blockers.

## Problem Evidence
- serve/cockpit/web npm run build currently fails.
- Observed failures include PDS v4 API/type mismatches for component variants, select/input/textarea events and props, JSX namespace typing, and PendingDR/ResolveModal body typing.
- sync-to-main cannot stage a fresh Cockpit dist until the SPA builds cleanly.

## Acceptance Criteria
- npm run build in serve/cockpit/web passes cleanly.
- PDS v4 component usage and type errors are resolved without test hacks, broad type suppression, or hiding errors from TypeScript.
- PendingDR/ResolveModal body typing is corrected if still failing in this foundation path.
- Changes stay scoped to build and design-system compatibility; the dashboard layout and cache/SSE behavior are not redesigned here.
- The tests and quality gates from #1364 pass.

## Scope
- In scope: Cockpit web TypeScript/build compatibility with the installed PDS version.
- Out of scope: CSP-compatible runtime loading, visual dashboard redesign, and cache/SSE invalidation already completed by #1346.

## Test Dependency
Satisfies #1364.

[[2026-05-06]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All fixes target `tsc -b` build errors in one package (serve/cockpit/web) |
| Interface clarity | PASS | Build exit code + typed component APIs are clear contracts |
| Dependency correctness | PASS | #1364 archived (RED tests exist at tests/test_cockpit_pds_build_compat_1364.py) |
| Module layering | PASS | Changes scoped within cockpit-web; no upward imports |
| TDD compliance | PASS | RED test file from #1364 provides precise failure assertions |
| KISS/YAGNI | PASS | No new abstractions — pure type/API alignment with installed PDS v4 |
| Premise challenge | PASS | Build must pass for sync-to-main; legitimate blocking issue |
| Pattern consistency | PASS | Uses existing PDS component patterns (readControlValue helpers, ref-based attrs) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (confidence 0.63)
- Key concerns: scope breadth (PDS + JSX namespace + data-shape), downstream vitest suites asserting old API, AC4 not machine-testable
- Architect response: REBUTTED — all errors surface from one `tsc -b` run on one package; splitting by error category creates artificial deps on overlapping files. Vitest suite concern accepted and addressed via AC refinement. AC4 is scope-constraint (td:0, reviewer-verified).

### Test Depth
- AC1: npm run build passes cleanly (td:1)
- AC2: PDS v4 type errors resolved without broad suppression (td:2)
- AC3: PendingDR/ResolveModal body typing corrected (td:1)
- AC4: Changes stay scoped to build compat (td:0)
- AC5: Tests from #1364 pass (td:1)
- AC6: Existing vitest suites pass after v4 alignment (td:1)
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC to add explicit vitest suite gate (AC6). Annotated test depths. Approved to `todo`.

[[2026-05-06]]
Architecture review complete. All criteria pass. Dependency #1364 satisfied (archived). Challenger raised scope-breadth concern (0.63 confidence) — rebutted: all errors from one `tsc -b` in one package. Vitest suite gate (AC6) added per challenger's valid downstream-test blind spot. Task approved to todo.
[[2026-05-06]]
## Test-Writer Notes

**Test file:** `tests/test_cockpit_pds_build_compat_1365.py`
**Commit:** `6fd7a816`

### Coverage

| AC | Test | Category |
|----|------|----------|
| AC6 | `test_vitest_suite_exits_zero` | happy/gate |
| AC6 | `test_pds_migration_suite_passes` | error — PDS v4 tertiary-variant runtime |
| AC6 | `test_shell_966_suite_passes` | error — EventSourceProvider context |
| AC6 | `test_shell_1227_suite_passes` | error — EventSourceProvider context |
| AC6 | `test_activity_tab_1156_suite_passes` | error — ActivityTab render |

AC1/AC2/AC3/AC5 already covered by `test_cockpit_pds_build_compat_1364.py` (satisfies #1364).
AC4 is `td:0` — no test needed.

### Class: `TestFromAC_ExistingVitestSuites`
- 5 tests, all FAIL ✓ (14.64s)

### Fail verification
- `vitest_result.returncode` = 1 (20 failures, 4 files)
- `vitest_failing_files` = `{"PdsMigration_1230.test", "Shell_966.test", "Shell_1227.test", "ActivityTab_1156.test"}` 
- All 5 tests confirmed FAIL against current broken state.

### Implementation notes for builder
- ANSI codes stripped via `_ANSI_RE` before parsing FAIL lines.
- Module-scoped `vitest_result` fixture runs `npm test -- --run` once (~14s).
- PdsMigration_1230 failures: `getVariantColors('tertiary')` TypeError — PDS v4 removed `tertiary` variant. Builder must replace `variant="tertiary"` across all components and update PdsMigration assertions accordingly.
- Shell_966/Shell_1227 failures: `useSSEEvent must be used within an EventSourceProvider` — Shell.tsx uses EventSourceProvider hooks; tests must provide the context wrapper after alignment.
- ActivityTab_1156: 1 failure, details in test output.
[[2026-05-06]]
## Builder Notes
- No source files changed.
- RED verified via quality-runner on tests/test_cockpit_pds_build_compat_1365.py: 5/5 TestFromAC tests failing as expected.
- Blocking mismatch found in downstream vitest suite assumptions:
  - ActivityTab_1156 reports runtime invalid prop: p-button variant='tertiary' is rejected by PDS v4 (valid variants: primary, secondary).
  - PdsMigration_1230 assertions still require variant='tertiary' for several actions (DetailTab and conflict actions), which conflicts with PDS v4 API and AC2 intent.
- This creates an infeasible gate for builder-only source changes under current test assumptions.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update legacy vitest assertions from tertiary to PDS v4-compatible variant expectations (or equivalent v4 contract assertions) in migration suites | serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx | quality-runner failure excerpt: Expected tertiary vs Received secondary on DetailTab actions; AC2 requires PDS v4 compatibility |
| 2 | test-writer | Reconcile ActivityTab expectations with PDS v4 button variant contract to eliminate invalid tertiary runtime path | serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx | quality-runner failure excerpt: Invalid property 'variant' with value 'tertiary' supplied to p-button |
| 3 | test-writer | Confirm Shell suite context setup contract for SSE-dependent renders after v4 alignment and ensure failing assertions represent intended production contract | serve/cockpit/web/src/__tests__/Shell_966.test.tsx, serve/cockpit/web/src/__tests__/Shell_1227.test.tsx | quality-runner failure excerpt: useSSEEvent must be used within an EventSourceProvider |

- Lint status from quality-runner scoped run: clean.
- Coverage: not applicable for this wrapper-style Python test (external vitest invocation).
[[2026-05-06]]
## Test-Writer Notes

**Retry cycle** — addressed builder's Required Follow-up (3 items).

**Commit:** `679221f2`

**Changed files:**
- `serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx`
- `serve/cockpit/web/src/__tests__/Shell_966.test.tsx`
- `serve/cockpit/web/src/__tests__/Shell_1227.test.tsx`
- `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx`

### Changes by Required Follow-up item

**Item 1 — PdsMigration_1230: tertiary→secondary**
All 15 variant assertions updated: `'tertiary'` → `'secondary'` across ConfirmDialog, ArchivalModal, ActivityTab filter buttons (5), DetailTab action buttons (7), ResolveModal, Shell nav rail. These tests remain FAIL because source still uses `variant="tertiary"` — PDS v4 returns undefined from `getVariantColors('tertiary')` → TypeError, causing assertions to fail correctly.

**Item 2 — ActivityTab_1156: block_reason assertion fix**
Test was checking `getAttribute('defaultvalue')` but source uses controlled `value={blockReason}` state. PDS v4 PInputText exposes the value as the `.value` JS property (not a DOM attribute). Updated to `(inputEl as HTMLElement & { value?: string }).value`. Now passes — implementation was already correct, test had wrong assertion.

**Item 3 — Shell_966, Shell_1227: EventSourceProvider mock**
Shell renders `<ActivityTab>` which calls `useSSEEvent()` from EventSourceProvider. Both test files lacked the mock, causing `useSSEEvent must be used within an EventSourceProvider` errors. Added `vi.mock('../hooks/EventSourceProvider', () => ({ useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })) }))` to both files. These tests now PASS (Shell implementation already correct).

### Verification (pytest gate)

| Test | Status |
|------|--------|
| test_vitest_suite_exits_zero | **FAIL** ✓ (vitest exits 1 — PdsMigration still failing) |
| test_pds_migration_suite_passes | **FAIL** ✓ (source still uses tertiary → TypeError) |
| test_shell_966_suite_passes | PASS ✓ (EventSourceProvider mock fixed) |
| test_shell_1227_suite_passes | PASS ✓ (EventSourceProvider mock fixed) |
| test_activity_tab_1156_suite_passes | PASS ✓ (block_reason .value assertion fixed) |

### Remaining work for builder
Builder must change `variant="tertiary"` → `variant="secondary"` in all affected source components: ConfirmDialog, ArchivalModal, ActivityTab, DetailTab, ResolveModal, Shell. This will resolve the 2 remaining Python gate failures and the 10 vitest failures in PdsMigration_1230.
[[2026-05-06]]
## Builder Notes
- Implementation: Updated PDS button variant usage from `tertiary` to `secondary` across cockpit web source, and fixed remaining TS/PDS v4 compatibility issues in `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/hooks/EventSourceProvider.tsx`, `serve/cockpit/web/src/components/ActivityTab.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ConfirmDialog.tsx`, `serve/cockpit/web/src/components/DRStatusIndicator.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`, `serve/cockpit/web/src/components/HealthBadge.tsx`, `serve/cockpit/web/src/components/RepairPanel.tsx`, and `serve/cockpit/web/src/components/ResolveModal.tsx`.
- Tests: `tests/test_cockpit_pds_build_compat_1365.py` passed (5/5). `tests/test_cockpit_pds_build_compat_1364.py` passed (11/11), including `npm run build` gate.
- Coverage: N/A for these integration wrappers (subprocess-driven frontend gates); no actionable Python coverage signal.
- Lint: clean on scoped changed files (`eslint` and `ruff` both exit 0).
- Evidence summary: Initial RED showed remaining PDS v4 incompatibilities (unsupported `onInput` on select wrappers, missing required `name` props, JSX namespace typing, and PendingDR/ResolveModal body contract mismatch). GREEN verified after targeted source alignment and type-safe event parsing updates.
- Fixes applied:
  - Removed unsupported PDS wrapper `onInput` usages where v4 does not expose that prop.
  - Added required `name` props for PDS form controls (`PSelect`, `PMultiSelect`, `PInputText`, `PTextarea`) where demanded by v4 typings.
  - Reworked control-value readers to safely parse both custom-event detail payloads and target values without unsafe assumptions.
  - Replaced React 19-incompatible `JSX.Element` annotations with `ReactElement` typing.
  - Tightened SSE mtime record typing in EventSourceProvider and kept dynamic event-key access type-safe.
  - Relaxed ResolveModal pending DR body typing to optional with safe render fallback (`dr.body ?? ''`) to resolve build contract mismatch.

## Post-task Reflection
- Problem faced: #1365 gate passed while #1364 dependency gate still failed due hidden TS/PDS incompatibilities beyond button variants.
- Workaround applied: Pulled raw `npm run build` diagnostics into `.owlbear/scratch/1365-build.txt` to patch exact compiler failures instead of broad guessing.
- Pattern discovered: PDS v4 wrapper typings require stricter control props (`name`) and event signatures than legacy usage patterns in this code.
- Time sink: A small syntax regression during typed state-update refactor caused one intermediate red run; fixed by explicit callback return typing.
- Quality gap observed: Global eslint config still has unrelated baseline debt, so scoped lint-on-changed-files evidence remains necessary for builder gate clarity.