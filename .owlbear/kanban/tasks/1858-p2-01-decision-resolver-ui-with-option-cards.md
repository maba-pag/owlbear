---
id: 1858
title: 'P2-01: Decision resolver UI with option cards'
status: review
priority: needed
created: 2026-05-24T20:59:10.619728+02:00
updated: 2026-05-26T00:32:47.104919+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1857
ac:
  - 'ResolveModal renders one card per decision option ([data-testid="resolve-option-{option_id}"]):
    label text, confidence bar ([data-testid="option-confidence-{option_id}"], width
    proportional to confidence 0→0% 1→100%), rationale text (omitted if empty), Recommended
    badge ([data-testid="option-recommended-{option_id}"], DOM-present only when recommended===true).'
  - 'Clicking an option card sets aria-selected="true" on it and aria-selected="false"
    on siblings; selected option_id becomes selected_option_id in the resolve payload.
    Clicking a different card moves selection. Submitting with no selection sends
    selected_option_id: null.'
  - 'For decision-kind: submit button ([data-testid="resolve-submit"]) disabled when
    no option selected AND textarea empty (trimmed); enabled when option selected
    OR textarea has non-whitespace text. Does not alter action-kind submit behavior
    (P2-02 scope).'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Option card component: label, confidence bar, rationale, recommended badge
- Card selection state management
- free_text textarea as alternative input
- Submit button enabled/disabled logic
- Integration with existing resolve submission flow (POST /api/requests/{id}/resolve)

**Out of scope:**
- Action resolver (P2-02)
- List view (P2-03)
- Backend changes (already complete in P1-06)

## Test scope
`npm test` in `serve/cockpit/web/`

[[2026-05-25T22:34:38+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single component enhancement — option card visuals + selection + submit logic for decision-kind |
| Interface clarity | PASS | After refinement: exact testids, width assertion, aria-selected contract, trimmed-empty boundary |
| Dependency correctness | PASS | #1857 archived/completed; PendingDROption type already carries confidence, recommended, rationale |
| Module layering | PASS | Frontend component rendering existing data — no reverse deps |
| TDD compliance | PASS | Test scope: npm test in serve/cockpit/web/ (vitest); existing test infra for ResolveModal |
| KISS/YAGNI | PASS | Implements brief promise — option cards with metadata. No over-engineering |
| Premise challenge | PASS | Brief explicitly promises option cards with confidence/recommended/rationale; this task delivers |
| Pattern consistency | PASS | Extends existing data-testid="resolve-option-{id}" pattern; aria-selected is standard listbox pattern |
| Security surface | PASS | Renders engine-validated data; no new user inputs beyond existing textarea |
| Single domain | PASS | Cockpit web frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Empty rationale render | rationale="" from engine | N/A (conditional render) | Yes — AC specifies "omitted if empty" | No visual artifact |
| Confidence at boundary | 0.0 or 1.0 values | N/A (CSS width 0%/100%) | Yes — proportional width handles range | Correct visual |

### Design Diverge
- Trigger: skipped — single clear approach (enhance existing option buttons in ResolveModal with card structure; reuse existing state management)

### Challenge Results
- Challenger: reconsider (confidence 0.44)
- Findings: (1) source-of-truth mismatch — refined AC not yet in artifact; (2) h-ac-quality B1 — vague target; (3) AC3 action-flow regression — shared modal submit logic; (4) boundary conditions — whitespace, empty rationale; (5) aria-selected not local precedent
- Architect response: Accepted findings 1-4. (1) Wrote refined AC to task artifact before approval. (2) Named ResolveModal as concrete target in AC1. (3) Scoped AC3 explicitly to decision-kind with "does not alter action-kind" clause. (4) Added "trimmed" qualifier and "omitted if empty" for rationale. (5) Rebutted: aria-selected is the correct ARIA listbox-option pattern for selection from a set — local Card uses data-selected for a different interaction model (board cards with context menus).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined all 3 AC lines addressing challenger findings — exact DOM selectors, decision-kind scoping, trimmed boundary, conditional rendering rules. Advanced to todo.

[[2026-05-25T22:59:56+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ResolveOptionCards_1858.test.tsx
- Classes: TestFromAC_OptionCards, TestFromAC_OptionSelection
- Tests per category: happy 3, edge 3, boundary 2, error 3
- Total: 11 tests, all FAIL
- lint: clean (eslint 0 violations)

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1: confidence bar per option with proportional width | 4 tests (element present, 80% for 0.8, 0% boundary, 100% boundary) |
| AC1: rationale text omitted if empty | 1 test (non-empty rationale in card textContent) |
| AC1: recommended badge DOM-present only when true | 1 test (combined: alpha badge present, beta badge absent) |
| AC2: aria-selected on click + siblings | 3 tests (click → true, sibling → false, transfer on re-click) |
| AC2: initial state aria-selected="false" | 1 test |
| AC2+AC3: no option + textarea text → POST with selected_option_id: null | 1 test |

RED failure modes:
- AC1: no confidence bar / rationale / badge elements in current implementation
- AC2: no aria-selected attribute on option buttons
- AC2+AC3: handleSubmit returns early when selectedOptionId===null regardless of textarea content

[[2026-05-25T23:45:02+02:00]]
## Builder Notes
### Files Changed
- serve/cockpit/web/src/components/ResolveModal.tsx

### Implementation Summary
- Implemented decision option-card rendering in ResolveModal with:
  - confidence bar per option (`data-testid="option-confidence-{option_id}"`) and proportional width mapping with clamp 0..1
  - conditional rationale text rendering (omitted when empty/non-string)
  - conditional Recommended badge (`data-testid="option-recommended-{option_id}"`) only when `recommended===true`
- Added option selection accessibility/state contract:
  - `aria-selected="true"` for selected option card
  - `aria-selected="false"` for non-selected sibling cards and initial state
- Updated decision submit gating:
  - decision-kind submit enabled when option selected OR textarea has non-whitespace text
  - decision-kind submit blocked only when no selected option AND trimmed notes empty
  - preserves action-kind submit behavior
- Preserved resolve payload contract:
  - selected option goes to `selected_option_id`
  - no selection submits `selected_option_id: null`
  - `free_text` is trimmed and null when empty

### Quality-Runner Evidence
- RED verification (task test):
  - `serve/cockpit/web/src/__tests__/ResolveOptionCards_1858.test.tsx`
  - result: 0 passed / 11 failed (all `TestFromAC_*`) — RED confirmed
- GREEN verification (task test):
  - `serve/cockpit/web/src/__tests__/ResolveOptionCards_1858.test.tsx`
  - result: 11 passed / 0 failed
- Durable/module regression checks (all pass in isolation):
  - `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx` -> 10 passed / 0 failed
  - `serve/cockpit/web/src/__tests__/ResolveWiring_1857.test.tsx` -> 6 passed / 0 failed
  - `serve/cockpit/web/src/__tests__/ActionResolver_1859.test.tsx` -> 8 passed / 0 failed
- Lint:
  - ESLint clean for touched source and scoped test paths

### Coverage Gate
- Scoped coverage run on passing Resolve suites:
  - tests: ResolveOptionCards_1858 + ResolveWiring_1857 + ResolveModal + ActionResolver_1859
  - module: `serve/cockpit/web/src/components/ResolveModal.tsx`
  - result: **74.05%** (below required 90% builder gate)

### Why Rejected
- Builder implementation is complete and task AC behavior is green.
- Coverage gate for touched module remains below threshold, and builder does not author tests.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add/adjust `TestFromAC_*` coverage for ResolveModal branches impacted by decision submit enablement and error/retry flows to raise touched-module coverage to >=90% without conflicting with AC3 trimmed-empty decision behavior. | serve/cockpit/web/src/__tests__/ResolveOptionCards_1858.test.tsx; serve/cockpit/web/src/components/ResolveModal.tsx | quality-runner coverage: ResolveModal.tsx 74.05% with all scoped suites passing |
| 2 | test-writer | Ensure coverage-oriented tests align with AC3 decision constraint (`no option + empty trimmed notes => disabled`) while still exercising error/retry branches via valid submit preconditions (selected option OR non-whitespace notes). | serve/cockpit/web/src/components/ResolveModal.tsx; relevant ResolveModal coverage tests | failing compatibility observations from broader coverage suites and current AC3 contract |

### Confidence
- 0.89 that implementation satisfies AC behavior and regressions checked above.
- 0.95 that current block is strictly a test-coverage gate issue.

[[2026-05-26T00:32:47+02:00]]
## Test-Writer Notes
- Retry: added 16 tests (27 total from 11 original) for reviewer coverage gaps.
- Test file: `serve/cockpit/web/src/__tests__/ResolveOptionCards_1858.test.tsx`
- Classes added: `TestFromAC_DecisionSubmitGate`, `TestFromAC_ErrorRetryFlow`, `TestFromAC_ActionKind`, `TestFromAC_ModalInteractions`
- Tests per category (retry additions): submit-gate boundary 3, error/retry flow 5, action-kind path 3, modal interactions 5
- All 27 tests PASS against current implementation (Step 1b.1 direct-to-review)
- Builder skip: test-only retry, all tests green.

Coverage gate (all 4 scoped suites):
| Suite | Tests | Status |
|-------|-------|--------|
| ResolveOptionCards_1858.test.tsx | 27 | ✓ all pass |
| ResolveModal.test.tsx | 10 | ✓ all pass |
| ResolveWiring_1857.test.tsx | 6 | ✓ all pass |
| ActionResolver_1859.test.tsx | 8 | ✓ all pass |
| **Total** | **51** | **✓ all pass** |

Coverage (v8) for `ResolveModal.tsx` with all 4 suites:
- Stmts: 90% | Branch: 72.93% | Funcs: 97.14% | **Lines: 90.5%** ✓ (gate: ≥90%)

AC coverage (retry gaps filled):
| Gap | Tests added |
|-----|-------------|
| AC3 submit disabled (no option + empty notes) | TestFromAC_DecisionSubmitGate × 3 |
| AC3 whitespace-only trimmed boundary | TestFromAC_DecisionSubmitGate |
| ApiError 4xx non-retryable branch | TestFromAC_ErrorRetryFlow |
| ApiError with custom server message body | TestFromAC_ErrorRetryFlow |
| Non-Error/non-ApiError catch fallback | TestFromAC_ErrorRetryFlow |
| dismissError (removes notification) | TestFromAC_ErrorRetryFlow |
| retryResolve (second fetch call) | TestFromAC_ErrorRetryFlow |
| Action-kind submit path (kind: action) | TestFromAC_ActionKind × 3 |
| openTaskDetail (resolve-open-task click) | TestFromAC_ModalInteractions |
| openTaskDetail (resolve-metadata-open-task click) | TestFromAC_ModalInteractions |
| handleModalKeyDown Tab branch | TestFromAC_ModalInteractions × 2 |
| handleModalKeyDown Escape branch | TestFromAC_ModalInteractions |

Lint: ESLint 0 violations on test file.
Commit: eee98e8c
