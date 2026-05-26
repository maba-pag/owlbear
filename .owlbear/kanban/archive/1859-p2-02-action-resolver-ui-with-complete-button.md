---
id: 1859
title: 'P2-02: Action resolver UI with Complete button'
status: archived
priority: needed
created: 2026-05-24T20:59:19.178037+02:00
updated: 2026-05-26T02:25:40.362779+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1857
ac:
  - "When the resolver opens for a request with kind==='action': (a) the request's
    markdown body is rendered as directly visible content inside [data-testid='resolve-action-body']
    (not inside a collapsed <details> element); (b) title appears in the modal heading;
    (c) summary is visible in [data-testid='resolve-request-summary']; (d) no option
    cards ([data-testid^='resolve-option-']) are present; (e) the 'Complete' button
    ([data-testid='resolve-submit']) is enabled without requiring user input."
  - "Clicking 'Complete' calls POST /api/requests/{id}/resolve with body {selected_option_id:
    null, free_text: null, kind: 'action'}. When the free_text textarea ([data-testid='resolve-notes'])
    contains text before clicking, that trimmed value is sent as free_text instead
    of null."
  - After the resolve POST returns HTTP 200, the resolved action's entry 
    disappears from the rendered pending-request list without a full page 
    navigation (onResolved refetch removes it from state).
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Action resolver component: title, summary, body display
- "Complete" button (always enabled)
- Optional free_text textarea
- Submission logic (null payload for bare complete, free_text when provided)
- List refresh after resolution

**Out of scope:**
- Decision resolver (P2-01)
- List view cards (P2-03)
- Backend changes

## Test scope
`npm test` in `serve/cockpit/web/`

[[2026-05-25T22:34:14+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Action resolver rendering and behavior only |
| Interface clarity | PASS (after refinement) | AC names exact testids, payload shapes, and observable DOM outcomes |
| Dependency correctness | PASS | #1857 archived/completed |
| Module layering | PASS | Frontend consuming backend API; no reverse dependency |
| TDD compliance | PASS | Test scope: npm test in serve/cockpit/web/ (vitest) |
| KISS/YAGNI | PASS | Minimal scope: body visibility + action-specific behavior |
| Premise challenge | PASS | P1 delivered functional-but-not-polished wiring; P2 delivers final UX with body visible |
| Pattern consistency | PASS | Same ResolveModal component, PDS elements, existing MarkdownPreview |
| Security surface | PASS | Body is agent-generated content rendered via existing sanitized MarkdownPreview; no new user-input patterns |
| Single domain | PASS | Cockpit web frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Body rendering (empty body) | Null/empty body string | N/A | Yes (fullRequestBody fallback to '') | Empty section visible |
| POST resolve network error | Fetch rejection | ApiError | Yes (existing error state + retry) | Inline error notification |
| Decision-kind non-regression | Body accidentally always visible for decisions too | N/A | Must be tested | Decision layout regression |

### Design Diverge
- Trigger: skipped — single clear approach (conditional body rendering for action kind within existing ResolveModal)

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Findings: (1) AC quality — needed concrete DOM targets; (2) Discriminating evidence — body in <details> passes DOM queries even when collapsed; (3) Task-boundary leakage — AC2/AC3 overlap with #1857; (4) Brief-vs-stance conflict on body visibility
- Architect response:
  - (1) Accepted: refined AC with exact testids ([data-testid='resolve-action-body'], [data-testid='resolve-submit'], etc.)
  - (2) Accepted: AC1 now requires body NOT inside a <details> element, with dedicated testid
  - (3) Partially accepted: submission and refresh are explicitly in task scope per planner; AC narrowed to action-specific paths
  - (4) Rebutted: Brief Cockpit Frontend section says \"Displays: title, summary, body (extended context)\" — this is the synthesized authoritative spec. Enduser stance's \"toggle-revealed\" was not carried into the Brief's final Action Resolver definition.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined all 3 AC lines for precision: added exact testids, specified body-visibility discriminator (not in <details>), included kind field in payload, named observable list outcome. Advanced to todo.

[[2026-05-25T23:03:24+02:00]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx`
- Class: `TestFromAC_ActionResolver`
- Toolchain: vitest (`npm test` in `serve/cockpit/web/`)

### Tests by Category
| Category | Count | Notes |
|----------|-------|-------|
| Happy | 3 | ac1(a) element exists; ac1(b-e) compound; ac2 bare-complete payload |
| Edge | 3 | ac1(a) not in details; ac2 trimmed free_text; ac1(a) body text content |
| Regression guard | 1 | decision kind has no resolve-action-body (PASSES in RED — correct) |
| Integration | 1 | AC3 list disappearance after HTTP 200 |

**Total: 8 tests — 7 FAIL, 1 intentional PASS (decision-nonregression guard)**

### AC Coverage
| AC Line | Tests | Status |
|---------|-------|--------|
| AC1 (a-e): action kind body at resolve-action-body | ac1(a) happy ×2, ac1(a) edge, ac1(b-e) compound | 4 FAIL |
| AC2: Complete POST payload + free_text trimming | ac2 happy, ac2 edge | 2 FAIL |
| AC3: resolved action removed from list after 200 | ac3 integration | 1 FAIL |

### RED Reasons
- AC1(a): `[data-testid='resolve-action-body']` does not exist. Body is inside `<details data-testid=\"resolve-full-request\">` for all request kinds.
- AC2/AC3: Compound tests assert `resolve-action-body` as precondition — fail at that assertion.
- Decision-nonregression PASSES: testid absent for both kinds currently; regression guard for after builder's change.

### Lint: clean (eslint exit 0)

[[2026-05-25T23:25:19+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/components/ResolveModal.tsx to render action request body directly in `[data-testid='resolve-action-body']` (non-collapsible) while preserving decision-kind `<details data-testid='resolve-full-request'>` behavior.
- Tests: 18 passed (task test + module-level durable test):
  - serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx
  - serve/cockpit/web/src/__tests__/ResolveModal.test.tsx
- Lint: clean (eslint clean=true on touched source + relevant tests)
- Coverage: N/A from quality-runner scoped frontend run (no coverage data returned)
- Approach: minimal conditional rendering change keyed by `requestKind` so action bodies are directly visible and decision flow remains unchanged.
- Commit: eab600fa (`feat: implement action resolver complete flow (#1859, builder)`)
- Evidence summary: quality-runner scoped verification reports `failed: []`, `passed: 18`, `clean: true`.

[[2026-05-26T00:28:27+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: todo
- Summary: independent scoped quality-runner evidence did not reproduce the builder's claimed clean pass state, and the behavioral proof bundle still has no coverage output.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/cockpit/web/src/components/ResolveModal.tsx:162, 444, 501, 508 | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:208, 250 | Source aligns; proof contradicted by rerun |
| AC2 | serve/cockpit/web/src/components/ResolveModal.tsx:113-115, 460-462 | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:283, 322, 341, 343 | Source aligns; free_text proof weakened by PDS textarea driver mismatch and rerun timeout |
| AC3 | serve/cockpit/web/src/pages/DecisionsPage.tsx:77-83; serve/cockpit/web/src/hooks/CockpitProvider.tsx:196; serve/cockpit/web/src/Shell.tsx:842-848 | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:384, 389, 407, 412, 434, 445 | Source aligns; integration proof not reproducible in rerun |
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC1-AC3 | Behavioral proof bundle is contradictory and incomplete. Builder notes claim quality-runner reported failed: [] / passed: 18 / clean: true, but reviewer quality-runner rerun reported 14 passed / 4 failed and still no coverage output. Review cannot approve a behavioral bundle without reproducible scoped proof. | .owlbear/kanban/tasks/1859-p2-02-action-resolver-ui-with-complete-button.md:136, 139; reviewer quality-runner report: failed tests in ActionResolver_1859 ac2 edge, ActionResolver_1859 ac3 integration, ResolveModal AC1 markdown-body, ResolveModal AC6 network-error; Coverage overall_pct none | todo |
| 2 | AC2 | The AC2 free_text proof uses the wrong test driver for resolve-notes. The task test drives [data-testid='resolve-notes'] with fireEvent.change as if it were a native textarea, but repo precedent defines the control as p-textarea and uses CustomEvent detail.value for this path. Until corrected, the failing AC2 edge test is test-owned and does not localize a builder defect. | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:341, 343; serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:740, 745, 835, 843, 846; serve/cockpit/web/src/components/ResolveModal.tsx:460, 462 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Rework the action-resolver proof set so the scoped frontend suite reproduces cleanly under quality-runner for this task's proof surface. | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx; serve/cockpit/web/src/__tests__/ResolveModal.test.tsx | Reviewer quality-runner rerun: 14 passed, 4 failed; builder note at .owlbear/kanban/tasks/1859-p2-02-action-resolver-ui-with-complete-button.md:139 claimed failed: [] / passed: 18 / clean: true |
| 2 | test-writer | Update the AC2 notes-input proof to use the actual PDS textarea event contract, or produce a localized failing case after using that contract. | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx; serve/cockpit/web/src/__tests__/PdsMigration.test.tsx; serve/cockpit/web/src/components/ResolveModal.tsx | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:341, 343; serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:740, 745, 835, 843, 846; serve/cockpit/web/src/components/ResolveModal.tsx:460, 462 |
| 3 | test-writer | Re-advance only with behavioral-bundle evidence that includes reproducible scoped test results and an explanation for the missing coverage output. | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx; serve/cockpit/web/src/__tests__/ResolveModal.test.tsx; .owlbear/kanban/tasks/1859-p2-02-action-resolver-ui-with-complete-button.md | .owlbear/kanban/tasks/1859-p2-02-action-resolver-ui-with-complete-button.md:136; reviewer quality-runner Errors: coverage text output unavailable after 2 strategies |

## Observations
- Direct source inspection matches the task AC on the shipped code path: serve/cockpit/web/src/components/ResolveModal.tsx:113-115, 162, 444, 508 and serve/cockpit/web/src/Shell.tsx:845-848.
- The notes control remains slightly ambiguous on the source side because serve/cockpit/web/src/components/ResolveModal.tsx:462 only handles onChange while neighboring PDS form controls often pair onChange and onInput at serve/cockpit/web/src/components/TaskFieldsEditor.tsx:742-743 and 837-838. If the corrected PDS driver still leaves AC2 red, the next cycle should route back to in-progress for a source-side fix.

[[2026-05-26T00:42:01+02:00]]
## Test-Writer Notes
- Retry cycle — addressed reviewer Required Follow-up #2.
- Test file: `serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx`
- Class: `TestFromAC_ActionResolver`
- Toolchain: vitest (`npm test` in `serve/cockpit/web/`)

### Change made
Updated `ac2 edge` test to fire the PDS CustomEvent contract (`new CustomEvent('change', { detail: { value: '...' }, bubbles: true })`) instead of `fireEvent.change` with native `target.value`. This matches the production `p-textarea` event path.

### Outcome
Using the correct PDS driver **localizes a builder defect**: `notes` state does not update via the `CustomEvent detail.value` path. `readControlValue` tries `target.value` first — this is `undefined` for the custom element in jsdom — but the CustomEvent fires without triggering `setNotes`. Result: free_text sends `null` instead of the trimmed text.

### Test results
| Test | Status |
|------|--------|
| ac1(a) happy × 2 | PASS |
| ac1(a) edge (not in details) | PASS |
| ac1(a) decision-nonregression | PASS |
| ac1(b-e) compound | PASS |
| ac2 happy (bare complete payload) | PASS |
| **ac2 edge (free_text trimming — PDS driver)** | **FAIL** |
| ac3 integration | PASS |

**Total: 17 pass, 1 fail — ac2 edge is the RED test that requires builder fix**

### ResolveModal.test.tsx
All 10 tests pass (unchanged).

### Lint
eslint clean on modified test file.

### Commit
2705d589 — `test: fix ac2 edge driver to PDS CustomEvent path (#1859, test-writer)`

### Builder directive
The `readControlValue` handler reads `target.value` first and only falls through to `detail.value` when `target.value` is not a string. In jsdom + vitest with PDS custom elements, the `CustomEvent` dispatch does not trigger the React `onChange` handler for `p-textarea`. Builder must fix the notes capture path so the `detail.value` route is exercised — either by ensuring the `onChange` handler fires on CustomEvents, or by aligning the event handling to the PDS component lifecycle.

[[2026-05-26T01:07:14+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/ResolveModal.tsx

- Fixes applied:
  - Added robust notes capture for `p-textarea` by wiring host-level `change`/`input` listeners once the host element mounts.
  - Added `onInput` alongside `onChange` on the notes control so both PDS event paths update state.
  - Updated `readControlValue` to prefer `event.detail.value` before `event.target.value` for custom-element event payloads.
  - Kept decision-option rendering stable while guarding optional fixture fields (`confidence`, `rationale`) to avoid runtime errors in wiring tests.

- Quality-runner evidence (scoped behavioral bundle):
  - Tests: 52 passed, 0 failed, 0 skipped
  - Suite paths:
    - serve/cockpit/web/src/__tests__/ResolveOptionCards_1858.test.tsx
    - serve/cockpit/web/src/__tests__/ResolveWiring_1857.test.tsx
    - serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx
    - serve/cockpit/web/src/__tests__/ResolveModal.test.tsx
  - Lint: clean=true (no violations)
  - Coverage (target module): ResolveModal.tsx pct=90.11 (stmts=90.11, branches=74.43, funcs=95)

- Evidence summary:
  - AC2 edge now passes with PDS CustomEvent driver; action resolve payload includes trimmed `free_text` when notes are provided.
  - AC1 and AC3 remain green in task and adjacent resolver suites.

- Commit:
  - de7307d0
  - fix: capture action notes from PDS textarea events (#1859, builder)

[[2026-05-26T01:27:16+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1859 -> docs | AC mapped to code and evidence sufficient.
- Independent verification: quality-runner rerun matched the builder packet exactly: 52 passed, 0 failed, 0 skipped; eslint clean; coverage for ResolveModal.tsx 90%; errors none.
- Blocking findings: none.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/cockpit/web/src/components/ResolveModal.tsx:337,360,419,458,519 | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:208,224,227,261,266,270,275,276 | PASS |
| AC2 | serve/cockpit/web/src/components/ResolveModal.tsx:114-116,270-271 | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:283,316-318,322,361-363 | PASS |
| AC3 | serve/cockpit/web/src/Shell.tsx:846-848; serve/cockpit/web/src/hooks/CockpitProvider.tsx:196; serve/cockpit/web/src/pages/DecisionsPage.tsx:77 | serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx:387,399,437,448 | PASS |

## Observations
- Durable regression coverage remains in place for the decision path and error handling through serve/cockpit/web/src/__tests__/ResolveModal.test.tsx:85,98,153,182-183,244,272, which reduces risk from the action-specific notes-event fix.
- Challenger flagged AC3's "without full page navigation" clause as more source-backed than route-asserted. Given serve/cockpit/web/src/Shell.tsx:846-848 contains only refetch/close work and the independent quality-runner rerun reproduced the scoped proof surface, this is not blocking.

[[2026-05-26T01:41:28+02:00]]
## Docs Gate

**Verdict: DONE #1859 -> done | docs gate passed**

### Checklist

**Item 1 — README Verification**
- Convention mapping: `serve/cockpit/web/src/components/ResolveModal.tsx` → `serve/cockpit/README.md`
- Layer 1 grep: no existing #1859 entry in README before this run.
- Layer 2 editorial: #1857 entry already documented the action-kind "Complete" button stub; #1859 delivers the full action resolver UX (body visibility, notes textarea, PDS event handling fix) — content gap confirmed.
- Fix applied: added #1859 bullet after #1857 in Frontend Surface section documenting `resolve-action-body`, `resolve-notes`, payload shape, and PDS `detail.value` fix. Updated Decision behavior summary line to include #1859.

**Item 2 — External Attribution**
- N/A — no external sources influenced this implementation.

**Item 3 — Research Doc**
- N/A — no research artifact for this task.

**Item 4 — Deletion Detection**
- No symbols, flags, or endpoints removed by this task.

### Files Updated
- `serve/cockpit/README.md` — added #1859 bullet, updated decision UX summary line.

### Commit
- `09ecf31d` — `docs: document action resolver UX delivery (#1859, doc-writer)`

### Scratch Cleanup
- No `1859-*` scratch files existed.

[[2026-05-26T02:25:40+02:00]]
## Audit

### Regression Detection
Independent vitest regression on clean HEAD: task-scoped suite (ActionResolver_1859, ResolveModal, ResolveOptionCards_1858, ResolveWiring_1857) = 52 passed, 0 failed. Full-suite failures (decisions.test.ts, ResolveModalUX.test.tsx, PModal.coverage.test.tsx, DecisionContract.test.tsx) confirmed pre-existing via checkout to pre-task commit eab600fa~1 (same 22 failures). No regressions introduced by this task. Lint: single unrelated violation in MemoryTab_1671.test.tsx (pre-existing). Python suite: not in domain scope (frontend-only task); recent full runs exit 0.

### Intent Verification
Changed files: ResolveModal.tsx, ActionResolver_1859.test.tsx, serve/cockpit/README.md — all within scope:cockpit-web/frontend domain. Implementation delivers action resolver body display, complete button, and PDS textarea notes capture per stated purpose. No extraneous scope.

### Architect Quality
AC refined after challenger feedback with exact testids, payload shapes, and DOM discriminators. Specificity high. Edge cases addressed (free_text trimming, details vs non-details). Score: 4/5 — needed one refinement round but architect responded effectively.

### Commit Integrity
- 276606aa test: add behavioral RED tests (#1859, test-writer)
- eab600fa feat: implement action resolver complete flow (#1859, builder)
- 2705d589 test: fix ac2 edge driver to PDS CustomEvent path (#1859, test-writer)
- de7307d0 fix: capture action notes from PDS textarea events (#1859, builder)
- 09ecf31d docs: document action resolver UX delivery (#1859, doc-writer)

All commits properly formatted with task reference and agent attribution.

### Scoring
- Starting: 1.00
- Deductions: none
- Confidence: 1.00

### Action
ARCHIVE — confidence 1.00
