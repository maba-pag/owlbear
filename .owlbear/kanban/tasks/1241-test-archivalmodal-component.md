---
id: 1241
title: 'Test: ArchivalModal component'
status: review
priority: needed
created: 2026-05-01T03:07:55.116658+00:00
updated: 2026-05-01T09:37:52.543058+00:00
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