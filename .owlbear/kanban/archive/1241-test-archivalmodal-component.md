---
id: 1241
title: 'Test: ArchivalModal component'
status: archived
priority: medium
created: 2026-05-01T03:07:55.116658+00:00
updated: 2026-05-01T14:26:52.784232+00:00
tags:
- scope:frontend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `ARCHIVAL_REASONS` constant is exported with order: `completed → dropped → wontfix → deprecated → duplicate`
- `ArchivalModal` renders with `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the visible title element's id
- Focus is placed on the reason `<select>` dropdown when the modal opens
- `completed` option is hidden in the dropdown when `taskStatus !== "done"`; shown when `taskStatus === "done"`
- Refs `<input>` is visible when reason is `"deprecated"` or `"duplicate"`; hidden for all other reasons
- When reason changes from a refs-requiring reason to any non-refs-requiring reason, refs state clears to `""`
- Submit button is disabled when no reason is selected
- Submit button is disabled when reason requires refs and refs field is empty
- Submit button is disabled while `isSubmitting === true`
- When the refs field is visible, a hint text is displayed below it: "Required — enter at least one task ID"
- Non-numeric token in the refs field produces a client-side inline error; no HTTP request is fired
- On 422 response: modal stays open; `error.detail` is displayed verbatim
- On 409 response: modal stays open; a modal-local stale-snapshot error message is shown
- On success: modal closes and board refresh is triggered
- Tab and Shift+Tab cycle within the modal only (focus trap active)
- Escape key closes the modal without firing a move request

## In Scope

- `ArchivalModal` component unit and interaction tests
- `ARCHIVAL_REASONS` constant assertion

## Out of Scope

- `handleTransitionClick` integration (F3 task #1242)
- Backend validation (B3 task #1240)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F1, F2
[[2026-05-01]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`
- Classes: `TestFromAC_ArchivalModal`
- Tests per category: happy ~15, edge ~10, error ~11, boundary ~5
- Total: 41 tests, all FAIL (module resolution error — `../components/ArchivalModal` does not exist; frontend equivalent of ImportError)
- ruff: N/A (TSX file); no TypeScript syntax errors in test file itself

### AC Coverage

| AC | Tests | Description |
|---|---|---|
| ARCHIVAL_REASONS constant | 3 | Order exact match, first=completed, last=duplicate |
| role/aria-modal/aria-labelledby | 3 | Each attribute verified independently |
| Focus on select at open | 1 | `document.activeElement === select` after mount |
| completed option visibility | 3 | non-done, done=show, todo (boundary) |
| Refs input visibility | 6 | deprecated, duplicate, completed, dropped, wontfix, initial |
| Refs clear on reason switch | 2 | deprecated→dropped, duplicate→wontfix |
| Submit disabled (no reason) | 1 | Initial state |
| Submit disabled (refs empty) | 4 | deprecated empty, duplicate empty, deprecated filled, dropped enabled |
| Submit disabled (isSubmitting) | 1 | In-flight request gates button |
| Hint text | 4 | deprecated, duplicate show; dropped, initial don't |
| Non-numeric refs error | 3 | alpha-only, mixed, valid (boundary) |
| 422 error verbatim | 1 | error.detail shown exactly; onClose not called |
| 409 stale error | 2 | Modal stays open; stale keyword present |
| Success: close + refresh | 3 | onClose, onRefresh, full payload assertion |
| Focus trap Tab/Shift+Tab | 2 | Last→first, first→last wrapping |
| Escape closes without fetch | 2 | No reason selected, reason selected |
[[2026-05-01]]
## Builder Notes
- Implementation files: `serve/cockpit/web/src/components/ArchivalModal.tsx` (new), `serve/cockpit/web/vitest.setup.ts` (setup matcher import for task test runtime).
- Behavior implemented: exported `ARCHIVAL_REASONS`; modal a11y attributes; initial focus on reason select; completed-option gating by `taskStatus`; refs visibility + clearing rules; submit disabled gates; refs hint text; client numeric refs validation; 422/409/success response handling; focus trap (Tab/Shift+Tab); Escape close without move request.
- RED verification: quality-runner initially failed with import resolution for missing `../components/ArchivalModal`.
- GREEN verification: quality-runner scoped run -> 41 passed, 0 failed, 0 skipped for `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- Lint: clean (no violations on scoped paths).
- Coverage: 93.68% for `ArchivalModal` in scoped quality-runner report.
- Commit: `434a9a73` with message `feat: implement archival modal component (#1241, builder)`.

## Post-task Reflection
- Problems faced: test runtime lacked jest-dom matcher registration, causing `toBeDisabled` assertion failure unrelated to component behavior.
- Workaround applied: added the minimal shared Vitest setup import (`@testing-library/jest-dom/vitest`) instead of changing tests.
- Pattern discovered: frontend AC tests can require bootstrap-level matcher support even when feature code is correct.
- Quality gap: coverage report is module-level only in this scoped run; branch-level detail remains limited.
- Time sink: diagnosing the single failing assertion required distinguishing app behavior failures from test-environment failures.
[[2026-05-01]]
## Review Evidence
### Source Scope
- Builder commit exists: `.git/logs/HEAD:1297` and `.git/logs/refs/heads/dev:1174` record `434a9a73` / `feat: implement archival modal component (#1241, builder)`.
- Changed files reconstructed from builder notes plus current tree: `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/vitest.setup.ts`. Current reviewer toolset did not expose a direct commit diff, so this incurred a small confidence deduction.

### Test Results
- quality-runner scoped run: 41 passed, 0 failed, 0 skipped for `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- Non-blocking runtime noise: React `act(...)` warning was logged during the scoped run.

### Lint
- ESLint scoped to `src/components/ArchivalModal.tsx`, `vitest.setup.ts`, and `src/__tests__/ArchivalModal_1241.test.tsx`: clean.

### Coverage
- quality-runner coverage for `ArchivalModal.tsx`: statements 93.68%, branches 88.33%, functions 100%, lines 93.68%.
- Uncovered lines reported by quality-runner: 83, 101, 106, 140, 182-184.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| `ARCHIVAL_REASONS` order export | `ArchivalModal_1241.test.tsx:96-112` | Yes; exact array / first / last assertions would fail | COVERED |
| dialog role + aria attrs | `ArchivalModal_1241.test.tsx:118-138` | Yes; role / `aria-modal` / `aria-labelledby` are asserted directly | COVERED |
| initial focus on reason select | `ArchivalModal_1241.test.tsx:145-148` | Yes; `document.activeElement === select` | COVERED |
| `completed` hidden unless `taskStatus === "done"` | `ArchivalModal_1241.test.tsx:154-176` | Yes; done vs non-done cases are checked directly | COVERED |
| refs input visible only for `deprecated` / `duplicate` | `ArchivalModal_1241.test.tsx:183-217` | Yes; positive and negative visibility cases are asserted | COVERED |
| refs clear when leaving refs-required reason | `ArchivalModal_1241.test.tsx:224-243` | Yes; value is checked after switching away and back | COVERED |
| submit disabled when no reason selected | `ArchivalModal_1241.test.tsx:250-253` | Yes; direct disabled check | COVERED |
| submit disabled when refs required and empty | `ArchivalModal_1241.test.tsx:260-282` | Yes; empty/filled and no-refs-required branches are checked | COVERED |
| submit disabled while submitting | `ArchivalModal_1241.test.tsx:289-302` | Yes; `toBeDisabled()` after click on pending request | COVERED |
| refs hint text when refs field visible | `ArchivalModal_1241.test.tsx:313-333` | Yes; visible and hidden states are asserted | COVERED |
| non-numeric refs => inline error, no request | `ArchivalModal_1241.test.tsx:340-372` | Yes; invalid input blocks fetch | COVERED |
| 422 => modal stays open and `detail` verbatim | `ArchivalModal_1241.test.tsx:395-418` | Yes; exact detail text is asserted and `onClose` must not fire | COVERED |
| 409 => modal stays open and stale message shown | `ArchivalModal_1241.test.tsx:425-477` | Yes; open state and stale/conflict wording are asserted | COVERED |
| success => modal closes and refreshes | `ArchivalModal_1241.test.tsx:482-537` | Yes; `onClose`, `onRefresh`, and request payload are asserted | COVERED |
| focus trap on Tab / Shift+Tab | `ArchivalModal_1241.test.tsx:545-580` | Yes; last->first and first->last focus wrapping are asserted | COVERED |
| Escape closes without move request | `ArchivalModal_1241.test.tsx:587-609` | Yes; `onClose` fires and fetch stays untouched | COVERED |

#### Security Review
- No security findings in scoped code. The component posts JSON to a fixed local route and does not introduce secret handling, shell execution, path construction, or unsafe deserialization.

#### Test Integrity
- No evidence that builder weakened or removed `TestFromAC_ArchivalModal` assertions. The builder notes and reconstructed changed-file scope point to source/setup files only.

#### Test Quality
- Explicit task-body AC tests are generally strong and assertion-specific.
- However, the task body binds Brief F1/F2, and the suite does not prove all of F2's submit/error branches.

#### Data Safety
- No blocking data-safety issues found in scoped code.

#### Implementation-Aware Gap Analysis
- FAIL: Brief F2 requires refs parsing via `refs.split(/[ ,\s]+/).filter(Boolean).map(Number)` semantics; see `.owlbear/briefs/draft-archival-ux/brief.md:148`. The implementation instead uses comma-only splitting in `serve/cockpit/web/src/components/ArchivalModal.tsx:23-30`, specifically `.split(',')` at line 25, and then raises a comma-only validation error at line 145. Whitespace-separated valid refs such as `"1230 1229"` would be rejected even though the bound brief requires them to be accepted.
- FAIL: The task-owned suite would not catch that drift. Its only valid refs success cases are comma-separated inputs at `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:375-386` and `:522-537`; there is no whitespace-separated success case.
- Additional gap: Brief F2 also requires modal-local generic handling for 404/network errors at `.owlbear/briefs/draft-archival-ux/brief.md:154`. No `404` / network-error test exists in `ArchivalModal_1241.test.tsx`, and quality-runner reported the generic error branch at `serve/cockpit/web/src/components/ArchivalModal.tsx:182-184` as uncovered.

#### Necessity Check
- Not applicable; no new dependency or external integration was added.

#### Builder Process Quality
- CLEAN: one builder cycle, no retry loop evidence.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `ARCHIVAL_REASONS` export/order | `ArchivalModal.tsx:3-8`; tests `:96-112` | `AC1` block | PASS |
| dialog role / modal attrs / labelled title | `ArchivalModal.tsx:191-192`; tests `:118-138` | `AC2` block | PASS |
| focus on select at open | `ArchivalModal.tsx:77`, `:197-200`; tests `:145-148` | `AC3` | PASS |
| `completed` hidden unless done | `ArchivalModal.tsx:204-205`; tests `:154-176` | `AC4` | PASS |
| refs input visibility rules | `ArchivalModal.tsx:60`, `:218-230`; tests `:183-217` | `AC5` | PASS |
| refs cleared when leaving refs-required reason | `ArchivalModal.tsx:125-134`; tests `:224-243` | `AC6` | PASS |
| submit disabled with no reason | `ArchivalModal.tsx:65-73`, `:235`; tests `:250-253` | `AC7` | PASS |
| submit disabled when refs required and empty | `ArchivalModal.tsx:60-73`, `:235`; tests `:260-282` | `AC8` | PASS |
| submit disabled while `isSubmitting` true | `ArchivalModal.tsx:65-73`, `:149-150`; tests `:289-302` | `AC9` | PASS |
| refs hint text displayed | `ArchivalModal.tsx:218-229`; tests `:313-333` | `AC10` | PASS |
| non-numeric token -> inline error / no HTTP | `ArchivalModal.tsx:143-146`; tests `:340-372` | `AC11` | PASS |
| 422 -> modal open + verbatim detail | `ArchivalModal.tsx:174-179`, `:246`; tests `:395-418` | `AC12` | PASS |
| 409 -> modal open + stale message | `ArchivalModal.tsx:170-171`, `:246`; tests `:425-477` | `AC13` | PASS |
| success -> close + refresh | `ArchivalModal.tsx:153-166`; tests `:482-537` | `AC14` | PASS |
| focus trap active | `ArchivalModal.tsx:80-117`; tests `:545-580` | `AC15` | PASS |
| Escape closes with no move request | `ArchivalModal.tsx:94-97`; tests `:587-609` | `AC16` | PASS |

### Deductions
- `-0.14` implementation violates the bound brief's whitespace-separated refs parsing contract.
- `-0.06` task-owned suite misses the whitespace-valid refs path and the brief-required 404/network generic error branch.
- `-0.02` changed-file scope reconstructed from builder notes / commit-log presence rather than direct diff output.

### Verdict
- FAIL, confidence 0.78.

### Required Follow-up
- Change refs parsing to brief-specified comma-or-whitespace tokenization.
- Preserve existing `TestFromAC_ArchivalModal` assertions and add proof for whitespace-separated valid refs.
- Add task-owned proof for the generic 404/network modal-local error branch required by Brief F2.

### Action
- Reject to `in-progress` because there is a concrete implementation defect plus accompanying proof gaps in the current task-owned suite.
[[2026-05-01]]
## Builder Notes
- Implementation: updated [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx) to tokenize refs using comma-or-whitespace splitting (`/[,\s]+/` semantics) and keep empty-token filtering.
- Behavior fix: whitespace-separated refs such as `"1230 1229"` now parse to numeric refs instead of triggering client-side invalid-token handling.
- Validation message: generalized inline error text to `Refs must contain only numeric task IDs.` to match multi-separator parsing behavior.
- Tests: quality-runner scoped run for [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx) -> 41 passed, 0 failed, 0 skipped.
- Coverage: `ArchivalModal` 93.61% statements / 88.33% branches / 100% functions / 93.61% lines.
- Lint: clean on [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx), [serve/cockpit/web/vitest.setup.ts](serve/cockpit/web/vitest.setup.ts).
- Commit: `6fc654ec` — `fix: align archival refs tokenization (#1241, builder)`.

## Post-task Reflection
- Problem faced: reviewer-flagged mismatch between brief tokenization semantics and current parser behavior despite AC suite passing.
- Workaround applied: scoped, minimal parser change rather than broader modal refactor.
- Pattern discovered: frontend task-owned suites can pass while brief-bound behavioral nuance still drifts.
- Quality gap: current task-owned tests still do not directly assert whitespace-separated refs success or generic non-409/422 error rendering path.
[[2026-05-01]]
## Review Evidence
### Source Scope
- Builder retry commit 6fc654ec changed only serve/cockpit/web/src/components/ArchivalModal.tsx.
- Retry commit did not change serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx or serve/cockpit/web/vitest.setup.ts.
- The live task file already contained one prior Review Evidence section at .owlbear/kanban/tasks/1241-test-archivalmodal-component.md:96, so this rejection is a second review FAIL and triggers the reviewer loop-breaker route.

### Test Results
- quality-runner scoped run: 41 passed, 0 failed, 0 skipped for serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx.
- Non-blocking runtime noise: one React act() warning during the scoped run.

### Lint
- ESLint clean on serve/cockpit/web/src/components/ArchivalModal.tsx, serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx, and serve/cockpit/web/vitest.setup.ts.

### Coverage
- ArchivalModal.tsx: 93.61% statements, 88.33% branches, 100% functions, 93.61% lines.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| ARCHIVAL_REASONS order export | ArchivalModal_1241.test.tsx:96 | Yes; exact array/position assertions | COVERED |
| dialog role + aria attrs | ArchivalModal_1241.test.tsx:118 | Yes; attributes asserted directly | COVERED |
| focus on reason select at open | ArchivalModal_1241.test.tsx:144 | Yes; activeElement check | COVERED |
| completed hidden unless taskStatus=done | ArchivalModal_1241.test.tsx:154 | Yes; done/non-done branches asserted | COVERED |
| refs input visible only for deprecated/duplicate | ArchivalModal_1241.test.tsx:184 | Yes; positive and negative visibility cases asserted | COVERED |
| refs clear when leaving refs-required reason | ArchivalModal_1241.test.tsx:223 | Yes; cleared value checked after switching away/back | COVERED |
| submit disabled with no reason | ArchivalModal_1241.test.tsx:249 | Yes; direct disabled assertion | COVERED |
| submit disabled when refs required and empty | ArchivalModal_1241.test.tsx:259 | Yes; empty/filled branches asserted | COVERED |
| submit disabled while isSubmitting | ArchivalModal_1241.test.tsx:288 | Yes; pending request disables button | COVERED |
| refs hint text displayed | ArchivalModal_1241.test.tsx:312 | Yes; visible and hidden states asserted | COVERED |
| non-numeric refs => inline error / no HTTP | ArchivalModal_1241.test.tsx:339 | Yes; invalid input blocks fetch | COVERED |
| 422 => modal stays open + detail verbatim | ArchivalModal_1241.test.tsx:394 | Yes; exact detail text asserted and onClose must not fire | COVERED |
| 409 => modal stays open + stale message | ArchivalModal_1241.test.tsx:424 | Yes; modal-local stale wording asserted | COVERED |
| success => close + refresh | ArchivalModal_1241.test.tsx:481 | Yes; onClose/onRefresh and payload asserted | COVERED |
| focus trap active | ArchivalModal_1241.test.tsx:544 | Yes; Tab and Shift+Tab wrap assertions | COVERED |
| Escape closes without move request | ArchivalModal_1241.test.tsx:586 | Yes; onClose fires and fetch remains untouched | COVERED |

#### Security Review
- No security findings in scoped code. No secret handling, shell execution, path construction, unsafe deserialization, or boundary validation regression was introduced.

#### Test Integrity
- No evidence that the retry commit weakened or removed TestFromAC_ArchivalModal assertions. Retry scope was implementation-only.

#### Test Quality
- Checklist AC coverage is strong and assertion-specific.
- However, the task body binds Brief F1/F2, and the current task-owned suite still does not prove all F2 submit/error branches.

#### Data Safety
- No blocking data-safety issues found in scoped code.

#### Implementation-Aware Gap Analysis
- FAIL: the prior implementation defect is fixed. Brief F2 requires refs parsing semantics at .owlbear/briefs/draft-archival-ux/brief.md:148, and the component now matches that with split(/[\s,]+/) at serve/cockpit/web/src/components/ArchivalModal.tsx:26.
- FAIL: the task-owned suite still proves only comma-separated valid refs inputs at serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:383 and :530. There is no whitespace-separated success proof, so the fixed behavior remains unverified.
- FAIL: Brief F2 also requires a generic modal-local error branch for any other error (404/network) at .owlbear/briefs/draft-archival-ux/brief.md:154. The component still contains those branches at serve/cockpit/web/src/components/ArchivalModal.tsx:182 and :184, but the task-owned suite only exercises 422/409 responses at serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:402, :431, and :456. No 404 or network-error proof exists.
- Supporting evidence: the builder's own post-task reflection at .owlbear/kanban/tasks/1241-test-archivalmodal-component.md:206 acknowledges that the task-owned tests still do not directly assert whitespace-separated refs success or generic non-409/422 error rendering.

#### Necessity Check
- Not applicable; no new dependency or external integration was added.

#### Builder Process Quality
- CLEAN. The builder addressed the code defect with a minimal implementation-only retry. The routing change here comes from repeat review failure count, not builder thrash.

### AC Compliance Table
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | ArchivalModal_1241.test.tsx:96; quality-runner 41/41 pass | PASS |
| AC2 | ArchivalModal_1241.test.tsx:118; quality-runner 41/41 pass | PASS |
| AC3 | ArchivalModal_1241.test.tsx:144; quality-runner 41/41 pass | PASS |
| AC4 | ArchivalModal_1241.test.tsx:154; quality-runner 41/41 pass | PASS |
| AC5 | ArchivalModal_1241.test.tsx:184; quality-runner 41/41 pass | PASS |
| AC6 | ArchivalModal_1241.test.tsx:223; quality-runner 41/41 pass | PASS |
| AC7 | ArchivalModal_1241.test.tsx:249; quality-runner 41/41 pass | PASS |
| AC8 | ArchivalModal_1241.test.tsx:259; quality-runner 41/41 pass | PASS |
| AC9 | ArchivalModal_1241.test.tsx:288; quality-runner 41/41 pass | PASS |
| AC10 | ArchivalModal_1241.test.tsx:312; quality-runner 41/41 pass | PASS |
| AC11 | ArchivalModal_1241.test.tsx:339; quality-runner 41/41 pass | PASS |
| AC12 | ArchivalModal_1241.test.tsx:394; quality-runner 41/41 pass | PASS |
| AC13 | ArchivalModal_1241.test.tsx:424; quality-runner 41/41 pass | PASS |
| AC14 | ArchivalModal_1241.test.tsx:481; quality-runner 41/41 pass | PASS |
| AC15 | ArchivalModal_1241.test.tsx:544; quality-runner 41/41 pass | PASS |
| AC16 | ArchivalModal_1241.test.tsx:586; quality-runner 41/41 pass | PASS |

### Deductions
- -0.10 task-owned suite does not prove whitespace-separated valid refs success required by bound Brief F2.
- -0.08 task-owned suite does not prove the brief-bound generic 404/network error branch.

### Verdict
- FAIL, confidence 0.82.

### Required Follow-up
- Preserve existing TestFromAC_ArchivalModal assertions.
- Add task-owned proof for whitespace-separated valid refs success.
- Add task-owned proof for the generic non-409/non-422 modal-local error path (404 and/or network failure).
- Re-submit after the loop-breaker handoff; no additional builder source change is required by current evidence.

### Action
- Reject to backlog because this is the second review failure on task 1241 and the remaining delta is a structural proof gap in bound Brief F2 behavior.
[[2026-05-01]]

## AC Addendum (Architecture Review — loop-breaker return)

The following AC lines are added to close brief-bound test gaps identified by the reviewer.
Existing 16 AC lines remain binding and already have passing test proof (41 tests).

- Comma-and-whitespace refs tokenization: whitespace-only separators (e.g., `"1230 1229"`), mixed comma-and-whitespace (e.g., `"1230, 1229"`), and consecutive separators producing empty tokens are all accepted and parsed to numeric values per Brief F2 `refs.split(/[,\s]+/).filter(Boolean).map(Number)` (td:2)
- On non-422/non-409 HTTP error (e.g., 404): modal stays open, `isSubmitting` resets to false, generic error message is displayed (td:1)
- On network failure (fetch throws): modal stays open, `isSubmitting` resets to false, generic error message is displayed (td:1)

### Test-depth annotations (existing AC)

| AC Line | td |
|---------|-----|
| ARCHIVAL_REASONS constant | td:1 |
| role/aria-modal/aria-labelledby | td:1 |
| Focus on reason select | td:1 |
| completed option hidden unless done | td:1 |
| Refs input visibility | td:2 |
| Refs cleared on reason change | td:1 |
| Submit disabled no reason | td:1 |
| Submit disabled refs empty | td:2 |
| Submit disabled isSubmitting | td:1 |
| Refs hint text | td:1 |
| Non-numeric token error | td:1 |
| 422 error verbatim | td:1 |
| 409 stale error | td:1 |
| Success close+refresh | td:1 |
| Focus trap Tab/Shift+Tab | td:2 |
| Escape closes without move | td:1 |

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | ArchivalModal tests + component, single UI concern |
| Interface clarity | PASS | After REFINE — 3 new AC lines close brief-bound gaps with precise test targets |
| Dependency correctness | PASS | No deps; parent #1238 is a closeout task tracking all children |
| Module layering | PASS | Frontend component, no upward imports, fetch to fixed local route |
| TDD compliance | PASS | This IS the test task; test-writer will add tests for 3 new AC lines |
| KISS/YAGNI | PASS | Minimal additions — only what the brief requires and the reviewer flagged |
| Premise challenge | PASS | Component serves a clear purpose in the archival UX flow |
| Pattern consistency | PASS | Follows existing Vitest/RTL patterns in the test suite |
| Security surface | PASS | No new security boundaries; JSON POST to fixed local route |
| Single domain | PASS | Frontend only (scope:frontend tag) |

### Failure Mode Map

Not applicable — no new codepaths introduced. Test additions only.

### Design Diverge

Skipped — single clear approach (add test proofs for already-implemented behavior).

### Challenge Results

- Challenger: reconsider (confidence 0.64)
- Issues raised: (1) error AC too coarse — collapses HTTP-status and network-failure into one td:1 line; (2) whitespace-only refs AC too narrow — doesn't cover mixed separators
- Architect response: ACCEPTED. Split error AC into two lines (HTTP status vs network failure). Broadened refs AC to cover whitespace, mixed, and empty-token cases at td:2. Challenger concerns fully addressed.

### Test Depth

- Max depth: td:2
- Test-writer: PROCEED (3 new AC lines need test proof)

### Verdict: APPROVE (after REFINE)

### Action Taken

Added 3 AC lines to close reviewer-identified brief-bound test gaps:
1. Comma-and-whitespace refs tokenization (td:2) — covers whitespace, mixed, empty-token
2. Non-422/409 HTTP error display (td:1) — distinct from network failure
3. Network failure error display (td:1) — catch branch

Implementation already handles all 3 correctly. Test-writer adds proofs; builder confirms pass. No source changes expected.

[[2026-05-01]]
REFINE → APPROVE. Loop-breaker return from reviewer (2× FAIL, confidence 0.78/0.82). Reviewer correctly identified 2 brief-bound test gaps: (1) no whitespace-separated refs proof, (2) no 404/network error proof. Implementation handles both correctly — gaps are test-only. Added 3 new AC lines after challenger reconsider (split error into HTTP-status + network-failure, broadened refs to cover mixed separators). Test-writer adds proofs; builder confirms pass.
[[2026-05-01]]
## Test-Writer Notes
- Retry: added 5 tests for reviewer/addendum gaps. All 46 tests pass against current impl.
- Builder skip: test-only retry, all tests green.

### New tests added (serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx)

| AC Addendum | Tests | Description |
|---|---|---|
| Whitespace/mixed refs tokenization (td:2) | 3 | whitespace-only ("1230 1229"), mixed comma+space ("1230, 1229"), consecutive separators ("1230  1229") |
| Non-422/409 HTTP error (td:1) | 1 | 404 → modal stays open, generic error shown, isSubmitting resets |
| Network failure (td:1) | 1 | fetch throws → modal stays open, generic error shown, isSubmitting resets |

### Results
- Total: 46 tests (41 existing preserved + 5 new), all PASS
- ESLint: clean
- Implementation handles all 3 addendum AC lines correctly; proof gaps closed.
[[2026-05-01]]
## Builder Notes
- Non-implementation builder pass-through on retry: Test-Writer added 5 addendum proofs and reported all tests passing; no source changes required in this builder cycle.
- Quality-runner verification (scoped) on current snapshot:
  - Tests: 46 passed, 0 failed, 0 skipped (`serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`)
  - Lint: clean on `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`, `serve/cockpit/web/vitest.setup.ts`
  - Coverage (`serve/cockpit/web/src/components/ArchivalModal.tsx`): statements 95.74%, branches 90.00%, functions 100%, lines 95.74%
- Evidence summary: addendum AC proofs are now present and passing (whitespace/mixed refs tokenization + non-409/422 HTTP generic error + network-failure generic error).
- Commit: none in this builder cycle (test-only retry pass-through).

## Post-task Reflection
- Problem faced: task state included prior builder/reviewer loops; needed to confirm whether new implementation work was still required.
- Workaround applied: treated this as a strict verification-only builder pass-through and re-ran quality-runner evidence instead of making speculative code edits.
- Pattern discovered: loop-breaker returns can convert builder responsibility from implementation to verification gatekeeping when retries are test-only.
- Quality gap: one non-blocking React `act(...)` warning remains in the scoped run; assertions still pass and lint remains clean.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped run: 46 passed, 0 failed, 0 skipped for [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx).
- Current snapshot is green, but green alone is not sufficient for reviewer pass when AC-mapped assertions are too weak to distinguish regressions.

### Lint
- quality-runner `ruff` output is not a TSX lint signal here; it only reports Python parse failures on `.ts`/`.tsx`, which is expected for cockpit frontend files per the documented quality-runner limitation.
- VS Code diagnostics are clean for [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx), and [serve/cockpit/web/vitest.setup.ts](serve/cockpit/web/vitest.setup.ts).

### Coverage
- quality-runner does not emit TSX coverage details in this path. For this frontend task, gate evidence is the 46/46 Vitest pass plus code review of the AC-mapped assertions.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---|---|---|
| AC1, AC3-AC11, AC14-AC17 | Current tests directly pin the required behavior and would fail on contract drift. | COVERED |
| AC2: `aria-labelledby` must point to the visible title element id | The test only checks that some referenced element exists and has non-empty text at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L136](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L136) and [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L138](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L138). That would still pass if `aria-labelledby` pointed to a different non-empty element instead of the visible title required by the AC, even though the implementation currently wires the real title at [serve/cockpit/web/src/components/ArchivalModal.tsx#L191](serve/cockpit/web/src/components/ArchivalModal.tsx#L191). | LAX |
| AC12: `error.detail` displayed verbatim on 422 | The test uses substring matching at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L415](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L415), so a transformed value like `Validation failed: {detail}` would still pass. The implementation currently sets the exact detail string at [serve/cockpit/web/src/components/ArchivalModal.tsx#L178](serve/cockpit/web/src/components/ArchivalModal.tsx#L178). | LAX |
| AC13: stale-snapshot local message on 409 | The test only requires non-empty text plus broad keyword matching at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L444](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L444), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L469](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L469), and [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L474](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L474). That would allow generic conflict wording instead of the concrete stale-snapshot message implemented at [serve/cockpit/web/src/components/ArchivalModal.tsx#L170](serve/cockpit/web/src/components/ArchivalModal.tsx#L170). | LAX |
| AC18: generic modal-local message on non-422/non-409 HTTP error | The new 404 test only asserts non-empty text at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L693](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L693), not the required generic message content. The implementation currently sets a concrete fallback string at [serve/cockpit/web/src/components/ArchivalModal.tsx#L182](serve/cockpit/web/src/components/ArchivalModal.tsx#L182). | LAX |
| AC19: generic modal-local message on network failure | The new network-failure test only asserts non-empty text at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L718](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L718), not the required generic message content. The implementation currently sets a concrete fallback string at [serve/cockpit/web/src/components/ArchivalModal.tsx#L184](serve/cockpit/web/src/components/ArchivalModal.tsx#L184). | LAX |

#### Security Review
- No security findings in scoped code. Input is constrained to digit-only refs before request construction, the POST target is fixed same-origin, and no secrets, dynamic execution, or filesystem access were introduced.

#### Test Integrity
- No evidence that the current cycle weakened or removed `TestFromAC_ArchivalModal` assertions. The problem is insufficient assertion specificity in several AC-mapped branches, not removed coverage.

#### Test Quality
- FAIL: assertion specificity is WEAK.
- Evidence: AC2 uses only existence/non-empty checks at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L136](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L136) and [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L138](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L138); AC12 uses substring matching at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L415](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L415); AC13 and AC18-19 accept broad non-empty or keyword-only error text at [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L444](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L444), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L469](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L469), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L474](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L474), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L693](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L693), and [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L718](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L718).
- Reviewer standard: if an assertion would stay green after a wrong or transformed value, it is not acceptable proof for an AC-mapped branch.

#### Data Safety
- No blocking data-safety issues found.

#### Implementation-Aware Gap Analysis
- The implementation itself matches the current task body and addendum on the reviewed branches.
- The remaining defect is proof quality: several tests do not pin the exact user-visible contract they claim to cover.

#### Necessity Check
- Not applicable; no new dependency or external integration was added.

#### Builder Process Quality
- CLEAN on process. The remaining problem is not builder thrash; it is structural test weakness.

### AC Compliance Table
| AC Line | Evidence | Status |
|---|---|---|
| AC1, AC3-AC11, AC14-AC17 | 46/46 task-owned tests pass and the mapped assertions are discriminating. | PASS |
| AC2 | Test is lax against the visible-title requirement; see [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L136](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L136) and [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L138](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L138). | FAIL |
| AC12 | Test is lax against verbatim detail handling; see [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L415](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L415). | FAIL |
| AC13 | Test is lax against the concrete stale-snapshot message; see [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L444](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L444), [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L469](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L469), and [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L474](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L474). | FAIL |
| AC18 | Test is lax against the required generic 404 fallback content; see [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L693](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L693). | FAIL |
| AC19 | Test is lax against the required generic network-failure content; see [serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L718](serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx#L718). | FAIL |

### Deductions
- `-0.12` AC2 proof does not distinguish the visible title contract from any other non-empty labelled element.
- `-0.10` AC12 proof does not pin verbatim detail rendering.
- `-0.10` AC13 proof does not pin the concrete stale-snapshot message.
- `-0.12` AC18-AC19 proofs do not pin the required generic fallback strings.

### Verdict
- FAIL, confidence 0.56.

### Required Follow-up
- Tighten AC2 to assert that `aria-labelledby` equals the actual visible title element id, not just any referenced non-empty element.
- Tighten AC12 to assert exact equality for the rendered 422 detail string.
- Tighten AC13 to assert the actual stale-snapshot message content, not generic conflict keywords.
- Tighten AC18 and AC19 to assert the concrete generic fallback messages shown to the user on 404 and thrown-fetch branches.
- Preserve existing `TestFromAC_ArchivalModal` coverage; this is a strengthening pass, not a rewrite.

### Action
- Reject to `backlog`.
- Reason: this task already has prior review failures at [ .owlbear/kanban/tasks/1241-test-archivalmodal-component.md](.owlbear/kanban/tasks/1241-test-archivalmodal-component.md#L96) and [ .owlbear/kanban/tasks/1241-test-archivalmodal-component.md](.owlbear/kanban/tasks/1241-test-archivalmodal-component.md#L208), so under the reviewer loop-breaker rule any further FAIL stays at backlog. The remaining delta is test-strengthening, not implementation rework.
[[2026-05-01]]
## AC Addendum (Architecture Review — assertion-specificity refinement)

Reviewer's 3rd FAIL (confidence 0.56) identified 5 AC lines where test assertions are too weak to distinguish correct from incorrect behavior. The implementation is correct on all branches. The following amendments specify required assertion methods — no new AC lines, no implementation changes.

### Assertion-Method Amendments

**AC2 (aria-labelledby):** The test must assert that the `aria-labelledby` attribute value exactly equals the `id` of the `<h3>` heading element that serves as the visible title. Checking that _some_ referenced element exists with non-empty text is not sufficient — the assertion must prove the label points to the title specifically. (td:1)

**AC12 (422 detail verbatim):** The test must assert the error element's `textContent` equals the 422 response `detail` value by exact equality (`.toBe()` semantics). Substring matching (`.toContain()`) is not sufficient — "verbatim" per Brief F2 means the full rendered text reproduces the detail string with no additions or transformations. (td:1)

**AC13 (409 stale-snapshot):** The test must assert the error element's `textContent` by exact equality against the component's rendered stale-snapshot message. Broad keyword matching (`stale`/`conflict`/`changed`) is not sufficient — the assertion must pin the full rendered output so any message change is caught. Brief authority is behavioral ("modal-local stale-snapshot error"); the test pins the actual output as regression proof. (td:1)

**AC18 (non-422/409 HTTP error):** The test must assert the error element's `textContent` by exact equality against the component's rendered fallback message for the specific HTTP status used in the test. Non-empty checks are not sufficient. Brief authority is behavioral ("generic modal-local error"); the test pins the actual output as regression proof. (td:1)

**AC19 (network failure):** The test must assert the error element's `textContent` by exact equality against the component's rendered network-failure message. Non-empty checks are not sufficient. Brief authority is behavioral ("generic modal-local error"); the test pins the actual output as regression proof. (td:1)

### Challenger Response

Challenger returned `reconsider` (0.43). Concerns addressed:
- **Brief authority:** Amendments require exact-equality _assertion method_ without pinning implementation strings in AC. Test-writer reads the implementation to determine expected values.
- **Refinement written before approval:** This addendum IS the written refinement.
- **AC18 pattern ambiguity:** Resolved — requires exact equality, not pattern matching.
- **Superseded chronology:** This is a fresh architect review after the 3rd reviewer FAIL, not a re-use of the prior approval.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | ArchivalModal tests + component, single UI concern |
| Interface clarity | PASS | After refinement — 5 AC lines now have explicit assertion-method requirements |
| Dependency correctness | PASS | No deps; parent #1238 is a closeout tracker |
| Module layering | PASS | Frontend component, no upward imports |
| TDD compliance | PASS | This IS the test task; test-writer strengthens 5 existing assertions |
| KISS/YAGNI | PASS | Minimal amendments — assertion method only, no new behavior |
| Premise challenge | PASS | Component serves clear archival UX purpose |
| Pattern consistency | PASS | Follows existing Vitest/RTL patterns |
| Security surface | PASS | No new security boundaries |
| Single domain | PASS | Frontend only (scope:frontend tag) |

### Failure Mode Map

Not applicable — no new codepaths. Assertion strengthening only.

### Design Diverge

Skipped — single clear approach (strengthen 5 test assertions to exact equality).

### Challenge Results

- Challenger: reconsider (confidence 0.43)
- Issues raised: (1) brief-authority drift for exact strings; (2) refinement not yet in repo; (3) AC18 pattern ambiguity; (4) superseded chronology unclear
- Architect response: All addressed. Refinements require assertion METHOD (exact equality) without pinning implementation strings. Addendum written to task body before approval. AC18 resolved to exact equality. Fresh review clearly scoped.

### Test Depth

- Max depth: td:2 (on existing AC lines 5, 8, 15, and addendum whitespace-refs line)
- Amended lines: all td:1 (single assertion change per line)
- Test-writer: PROCEED (strengthen 5 assertions in existing tests)

### Verdict: APPROVE (after REFINE)

REFINE → APPROVE. Loop-breaker return from reviewer (3× FAIL, 0.78/0.82/0.56). Implementation is correct on all 5 flagged branches. Reviewer correctly identified weak assertion methods. Added assertion-specificity amendments requiring exact-equality testing on AC2/12/13/18/19. Test-writer strengthens 5 existing assertions; no implementation changes expected.
[[2026-05-01]]
REFINE → APPROVE. Loop-breaker return (3× reviewer FAIL). Implementation correct on all branches. Added assertion-specificity amendments for AC2/12/13/18/19 requiring exact-equality testing method. No implementation changes needed — test-writer strengthens 5 existing assertions.
[[2026-05-01]]
## Test-Writer Notes
- Retry: strengthened 5 existing assertions to exact equality per AC addendum (assertion-specificity amendments). All 46 tests pass against current implementation.
- Builder skip: test-only retry, all tests green.

### Assertions tightened (serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx)

| AC | Change | Expected value |
|---|---|---|
| AC2 (aria-labelledby) | `toBeGreaterThan(0)` → `toBe(titleH3?.id)` — asserts labelledby equals h3.id exactly | `useId()` value on `<h3>` |
| AC12 (422 verbatim) | `.toContain(errorDetail)` → `.toBe(errorDetail)` — exact equality | exact detail string |
| AC13 test 1 (stale msg) | `toBeGreaterThan(0)` → `.toBe('Task snapshot is stale; refresh and try again.')` | implementation line 171 |
| AC13 test 2 (stale msg) | keyword multi-contains → `.toBe('Task snapshot is stale; refresh and try again.')` | implementation line 171 |
| AC18 (404 error) | `toBeGreaterThan(0)` → `.toBe('Archival failed (404).')` | implementation line 182 |
| AC19 (network error) | `toBeGreaterThan(0)` → `.toBe('Archival failed due to network error.')` | implementation line 184 |

### Results
- Total: 46 tests, all PASS
- ESLint: clean
- Commit: `488f62bf` — `test: strengthen AC2/12/13/18/19 assertions to exact equality (#1241, test-writer)`
[[2026-05-01]]
## Builder Notes
- Non-implementation builder pass-through on retry: no source changes were required in this cycle.
- Verification (quality-runner, scoped): 46 passed, 0 failed, 0 skipped for `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- Coverage (`serve/cockpit/web/src/components/ArchivalModal.tsx`): statements 95.74%, branches 90.00%, functions 100%, lines 95.74%.
- Lint signal: quality-runner `ruff` reports expected TypeScript parse failures (tool limitation); VS Code diagnostics show no errors in `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`, and `serve/cockpit/web/vitest.setup.ts`.
- Evidence summary: addendum proof set remains green with strengthened assertion-specific tests passing on current implementation.
- Commit: none in this builder cycle (test-only retry / verification pass-through).

## Post-task Reflection
- Problem faced: quality-runner lint output is not directly usable for TSX gate decisions because it runs Python `ruff`.
- Workaround applied: used frontend-appropriate gate evidence (Vitest pass + coverage + diagnostics clean) without changing code.
- Pattern discovered: loop-breaker retries often shift builder work from implementation to verification-only handoff.
- Quality gap: a non-blocking React `act(...)` warning still appears in scoped tests, though behavior and assertions are passing.
[[2026-05-01]]
## Review Evidence
### Source Scope
- Git log confirms task-linked commits for this task: `434a9a73` (`feat: implement archival modal component (#1241, builder)`), `6fc654ec` (`fix: align archival refs tokenization (#1241, builder)`), and `488f62bf` (`test: strengthen AC2/12/13/18/19 assertions to exact equality (#1241, test-writer)`).
- Current review scope: `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`, and `serve/cockpit/web/vitest.setup.ts`.
- Latest cycle is a test-strengthening / verification pass-through on top of an already-correct implementation snapshot.

### Test Results
- quality-runner scoped run: `46 passed, 0 failed, 0 skipped` for `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- Non-blocking runtime noise: one React `act(...)` warning during the async submit-state test.

### Lint
- quality-runner lint is not authoritative for TSX in this repo because it runs Python `ruff`; no TSX lint violation is available from that path.
- VS Code diagnostics are clean for `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`, and `serve/cockpit/web/vitest.setup.ts`.

### Coverage
- quality-runner scoped coverage for `serve/cockpit/web/src/components/ArchivalModal.tsx`: statements `95.74%`, branches `90.00%`, functions `100%`, lines `95.74%`.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC | Evidence | Verdict |
|---|---|---|
| AC1 `ARCHIVAL_REASONS` order export | `ArchivalModal_1241.test.tsx#L96-L112`; `ArchivalModal.tsx#L3-L8` | COVERED |
| AC2 dialog role / aria attrs / labelled title | `ArchivalModal_1241.test.tsx#L118-L138`; `ArchivalModal.tsx#L191-L192` | COVERED |
| AC3 focus on reason select at open | `ArchivalModal_1241.test.tsx#L144-L149`; `ArchivalModal.tsx#L67-L69` | COVERED |
| AC4 `completed` hidden unless done | `ArchivalModal_1241.test.tsx#L154-L180`; `ArchivalModal.tsx#L205-L214` | COVERED |
| AC5 refs input visibility rules | `ArchivalModal_1241.test.tsx#L184-L220`; `ArchivalModal.tsx#L60-L61`, `#L218-L230` | COVERED |
| AC6 refs cleared on reason change | `ArchivalModal_1241.test.tsx#L223-L246`; `ArchivalModal.tsx#L109-L120` | COVERED |
| AC7 submit disabled with no reason | `ArchivalModal_1241.test.tsx#L249-L254`; `ArchivalModal.tsx#L54-L64` | COVERED |
| AC8 submit disabled when refs required and empty | `ArchivalModal_1241.test.tsx#L259-L283`; `ArchivalModal.tsx#L54-L64` | COVERED |
| AC9 submit disabled while `isSubmitting` | `ArchivalModal_1241.test.tsx#L288-L307`; `ArchivalModal.tsx#L52-L64`, `#L148-L186` | COVERED |
| AC10 refs hint text displayed | `ArchivalModal_1241.test.tsx#L312-L336`; `ArchivalModal.tsx#L218-L229` | COVERED |
| AC11 invalid refs => inline error / no request | `ArchivalModal_1241.test.tsx#L339-L390`; `ArchivalModal.tsx#L23-L34`, `#L143-L146` | COVERED |
| AC12 422 keeps modal open and shows detail verbatim | `ArchivalModal_1241.test.tsx#L394-L420`; `ArchivalModal.tsx#L174-L179` | COVERED |
| AC13 409 keeps modal open and shows stale message | `ArchivalModal_1241.test.tsx#L424-L474`; `ArchivalModal.tsx#L170-L171` | COVERED |
| AC14 success closes modal and refreshes board | `ArchivalModal_1241.test.tsx#L476-L537`; `ArchivalModal.tsx#L153-L166` | COVERED |
| AC15 Tab / Shift+Tab cycle inside modal | `ArchivalModal_1241.test.tsx#L539-L579`; `ArchivalModal.tsx#L80-L121` | COVERED |
| AC16 Escape closes without move request | `ArchivalModal_1241.test.tsx#L581-L604`; `ArchivalModal.tsx#L94-L97` | COVERED |
| AC17 comma-and-whitespace refs tokenization | `ArchivalModal_1241.test.tsx#L611-L665`; `ArchivalModal.tsx#L23-L34` | COVERED |
| AC18 generic non-409/422 HTTP error branch | `ArchivalModal_1241.test.tsx#L669-L695`; `ArchivalModal.tsx#L182` | COVERED |
| AC19 network-failure error branch | `ArchivalModal_1241.test.tsx#L700-L720`; `ArchivalModal.tsx#L184` | COVERED |

#### Security Review
- No security findings in scoped code. Input is digit-validated before request construction, the POST target is fixed same-origin JSON, and there is no shell / path / secret / deserialization surface in scope.

#### Test Integrity
- No evidence that `TestFromAC_ArchivalModal` assertions were weakened or removed in the final cycle.
- The task-linked retry commit `488f62bf` strengthened the previously flagged AC2 / AC12 / AC13 / AC18 / AC19 assertions to exact-value proofs, and the current snapshot retains those stronger assertions.

#### Test Quality
- PASS: assertion specificity is strong for the binding task body plus architect addenda. The prior weak branches now use exact-equality proofs where the review history required them.
- I reviewed the code-reader's remaining concerns and treated them as non-blocking at current scope:
  - AC2 now matches the architect's explicit refinement: the test asserts `aria-labelledby === h3.id`, which is the binding proof method added in the task body.
  - AC15 uses td:2 component-level behavioral proofs for both wrap directions. Requiring explicit `preventDefault()` evidence would overfit the current implementation rather than the AC contract.
  - AC16 is td:1 and the paired tests adequately prove the two contract effects: Escape closes the modal, and Escape does not fire a move request even after a reason has been selected.

#### Data Safety
- No blocking data-safety issues found. Submit gating, refs clearing, and submit-state reset are all local and deterministic in `ArchivalModal.tsx`.

#### Implementation-Aware Gap Analysis
- No blocking implementation/test gap remains in the current snapshot.
- `parseRefsInput()` now accepts comma-and-whitespace tokenization via `/[\s,]+/` semantics.
- The component sets exact modal-local fallback strings for 409, generic HTTP, and network-failure branches, and the task-owned tests now pin those outputs directly.

#### Necessity Check
- Not applicable; no new dependency or external integration was introduced.

#### Builder Process Quality
- CLEAN. Earlier implementation and proof gaps were resolved across prior cycles; the final cycle is a test-only strengthening pass with no builder thrash.

### AC Compliance Table
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | `ArchivalModal_1241.test.tsx#L96-L112` exact array-order assertions | PASS |
| AC2 | `ArchivalModal_1241.test.tsx#L131-L138` exact `aria-labelledby === h3.id` assertion | PASS |
| AC3 | `ArchivalModal_1241.test.tsx#L144-L149` activeElement check on mount | PASS |
| AC4 | `ArchivalModal_1241.test.tsx#L154-L180` done vs non-done option checks | PASS |
| AC5 | `ArchivalModal_1241.test.tsx#L184-L220` positive and negative refs visibility checks | PASS |
| AC6 | `ArchivalModal_1241.test.tsx#L223-L246` clear-on-transition checks | PASS |
| AC7 | `ArchivalModal_1241.test.tsx#L249-L254` initial submit disabled | PASS |
| AC8 | `ArchivalModal_1241.test.tsx#L259-L283` refs-required disabled/enabled branches | PASS |
| AC9 | `ArchivalModal_1241.test.tsx#L288-L307` disabled while request pending | PASS |
| AC10 | `ArchivalModal_1241.test.tsx#L312-L336` hint visible/hidden assertions | PASS |
| AC11 | `ArchivalModal_1241.test.tsx#L339-L390` invalid-token client-side block and no fetch | PASS |
| AC12 | `ArchivalModal_1241.test.tsx#L394-L420` exact 422 detail equality | PASS |
| AC13 | `ArchivalModal_1241.test.tsx#L424-L474` exact stale-snapshot message equality | PASS |
| AC14 | `ArchivalModal_1241.test.tsx#L476-L537` close/refresh and payload assertions | PASS |
| AC15 | `ArchivalModal_1241.test.tsx#L539-L579` wrap-around focus assertions in both directions | PASS |
| AC16 | `ArchivalModal_1241.test.tsx#L581-L604` close + no-request escape behavior | PASS |
| AC17 | `ArchivalModal_1241.test.tsx#L611-L665` whitespace / mixed / consecutive separator refs parsing | PASS |
| AC18 | `ArchivalModal_1241.test.tsx#L669-L695` exact generic 404 fallback + re-enable | PASS |
| AC19 | `ArchivalModal_1241.test.tsx#L700-L720` exact network-failure fallback + re-enable | PASS |

### Deductions
- `-0.03` frontend lint gate depends on Vitest + editor diagnostics because quality-runner's lint path is Python-only for TSX.
- `-0.02` non-blocking React `act(...)` warning remains in the scoped run.
- `-0.02` focus-trap proof is component/unit-level rather than browser E2E; acceptable for the current AC/test-depth contract.

### Verdict
- PASS, confidence `0.93`.

### Action
- Advance to `docs`.

### Post-task Reflection
- Problems faced: the task body contained multiple review/addendum loops, so the latest binding AC had to be reconstructed from the live task body rather than any single earlier note.
- Workaround applied: re-ran quality-runner on the current snapshot and treated the latest architect addendum as the authority for the formerly weak AC2 / AC12 / AC13 / AC18 / AC19 proof methods.
- Pattern discovered: frontend review in this repo needs Vitest + diagnostics together because quality-runner lint is not authoritative for TSX.
- Quality gap: a non-blocking React `act(...)` warning remains in the scoped run; browser-level keyboard-trap proof could still be strengthened in a future non-blocking test-curation pass.
[[2026-05-01]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope README or guide references ArchivalModal component — new frontend-only component with no CLI/API/config change |
| 2 | Module docstrings | No | N/A | No Python modules modified — only `.tsx`/`.ts` files |
| 3 | External attribution | No | N/A | No external patterns used; implementation is entirely brief-derived |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches `ArchivalModal.tsx`. Footer updated to `Last verified: 2026-05-01 (9325fb5a)`. Committed as `9e61e30d`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files — only new/modified frontend files |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/components/ArchivalModal.tsx` | OUT (app source) | Diagram footer updated (Item 5) |
| `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx` | OUT (test file) | N/A |
| `serve/cockpit/web/vitest.setup.ts` | OUT (config/setup) | N/A |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `Last verified: 2026-05-01 (9325fb5a)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1241-*` scratch files found)
[[2026-05-01]]
## Audit

### AC Verification (spot-check; reviewer 4th-cycle detailed map trusted)
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1-AC16 (original) | Reviewer final review mapped all with file:line refs; 46/46 Vitest pass | PASS |
| AC17 whitespace refs | ArchivalModal_1241.test.tsx:611-665; /[\s,]+/ split in ArchivalModal.tsx:26 | PASS |
| AC18 generic 404 error | ArchivalModal_1241.test.tsx:693 exact equality .toBe('Archival failed (404).') | PASS |
| AC19 network failure | ArchivalModal_1241.test.tsx:718 exact equality .toBe('Archival failed due to network error.') | PASS |
| AC2 aria-labelledby (strengthened) | ArchivalModal_1241.test.tsx:136 exact .toBe(titleH3?.id) | PASS |
| AC12 422 verbatim (strengthened) | ArchivalModal_1241.test.tsx:415 exact .toBe(errorDetail) | PASS |

### Test Results
- Vitest (frontend): 678 passed, 2 failed (ResolveModal_plugins_1194 unrelated to #1241)
- pytest (Python): 3485 passed, 105 failed (all in unrelated packages: knowledge, orchestrator, mcp-memory)
- Task-scoped: 46/46 pass
- Lint (ruff): 4 violations, none in task scope

### Commits Verified
- 434a9a73 feat: implement archival modal component (#1241, builder)
- 6fc654ec fix: align archival refs tokenization (#1241, builder)
- def442a8 test: add whitespace-refs + 404/network proof (#1241, test-writer)
- 488f62bf test: strengthen AC2/12/13/18/19 assertions (#1241, test-writer)

### Architect Quality: 3/5
Original AC missed brief-bound whitespace-refs parsing and 404/network error branches, requiring 2 architect addenda and 5 pipeline cycles. Final AC is complete and precise with assertion-method amendments.

### Deduction Breakdown
- -0.03 AC quality score = 3

### Confidence: 0.97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2f539fc9 | chore | .owlbear/kanban/tasks/1241-*.md | #1241 |