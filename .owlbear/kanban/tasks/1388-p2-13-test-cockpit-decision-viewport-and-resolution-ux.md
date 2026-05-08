---
id: 1388
title: 'P2-13: Test Cockpit decision viewport and resolution UX'
status: backlog
priority: needed
created: 2026-05-06T01:04:50.731483+00:00
updated: 2026-05-08T19:27:18.726656+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- decisions
- ux
parent: 1363
depends_on:
- 1387
blocked: false
block_reason:
claimed_at: 2026-05-08T19:27:18.726656+00:00
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for a central Cockpit decision viewport and safer resolution UX.

## Problem Evidence
- DRStatusIndicator is a tiny decision count popover rather than a central decision viewport.
- ResolveModal defaults to approved, has terse lower-case choices, and lacks a visible consequence summary.
- Pending decisions need clear task context, body preview, and loading/error/empty states.

## Acceptance Criteria
- AC1: Tests prove a `DecisionViewport` component renders each pending decision with: clickable task-id reference (button or link element displaying the numeric task ID, firing `onItemClick` callback on click), agent name, request_type, human-readable relative age derived from `created` timestamp (proven by rendering items with distinct timestamps under fake timers and asserting different age strings), and body_preview text (proven with fixtures where body_preview is NOT a verbatim substring of body to ensure the component renders the preview field, not the full body). Viewport renders distinct loading, error, and empty-state indicators identified by `data-testid` attributes. (td:2)
- AC2: Tests prove each resolution choice (approved, rejected, needs-info) renders a structurally separate description element (`p-text` or equivalent) adjacent to the radio input, containing explanatory text about the consequence of that choice. Tests verify: (a) a description element exists per option that is NOT the radio label itself, (b) description text contains at least one action-oriented word beyond the bare status token. (td:2)
- AC3: Tests prove no resolution choice is pre-selected on initial render (all radios `checked === false`); submit button has `disabled` attribute until explicit user radio selection. Sequence test proves: disabled → user clicks radio → enabled. (td:2)
- AC4: Tests prove submit and cancel action labels each contain ≥2 words. Response selector contains ≥3 `p-text` elements (one per option description). (td:1)
- AC5: Tests prove: initial focus lands inside the modal container and not on the submit button; Escape key calls `onClose` (tested on both modal element and document); modal element has `aria-modal="true"`. Decision list items have focusable semantics (button or link tag/role, no `tabindex="-1"`). Logical Tab traversal order deferred to E2E tests (covered by #1395/#1396 accessibility gate). (td:2)
- AC6: Tests prove viewport-level error indicator has ARIA role `alert` or `status` and surfaces error message content via `textContent`. ResolveModal error contract already covered by #1375 is not duplicated. (td:1)
- AC7: The RED-phase delta is proven: all ResolveModal UX tests fail against current defects (`useState('approved')` pre-selects, bare labels, no focus management); DecisionViewport tests fail via import error (component does not exist). Already-green contracts from #1375/#1387 are excluded. Shell-level popover replacement is not tested here — that integration is #1389's implementation scope. (td:1)

## Scope
- In scope: Cockpit frontend decision viewport and resolution-modal UX tests.
- Out of scope: backend decision lifecycle from #1385, data/refetch plumbing from #1387, task detail workflows, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1389.

[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task for decision viewport and resolution UX — single domain concern |
| Interface clarity | PASS (after refinement) | AC lines refined per challenger feedback: task-link clarified as clickable task-id reference, keyboard model specified, RED-phase delta narrowed |
| Dependency correctness | PASS | #1387 (archived), #1375 (archived) — both dependencies satisfied |
| Module layering | N/A | Test task, no production module layering |
| TDD compliance | PASS | This IS the RED phase task; counterpart #1389 depends on it |
| KISS/YAGNI | PASS | Scope explicitly excludes backend lifecycle, data plumbing, global a11y audit |
| Premise challenge | PASS | Audit evidence confirms real UX defects: default-approved, bare labels, tiny popover |
| Pattern consistency | PASS | Follows TDD-paired pattern (test/impl) consistent with #1386/#1387, #1374/#1375 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Findings accepted: (1) source-of-truth mismatch — persisted refined AC into task body; (2) RED-phase overstatement — narrowed AC7 to exclude already-green #1375/#1387 behavior; (3) task navigation unspecified — AC1 now says "clickable task-id reference"; (4) accessibility semantics — AC5 now specifies initial focus, Escape close, tab order, button/focus semantics; (5) existing overlap — AC6 now excludes ResolveModal error contract already covered by #1375
- Architect response: all 5 findings accepted and incorporated into refined AC

### Test Depth
- Max depth: 2 (AC1, AC2, AC3, AC5 are td:2)
- Test-writer: SKIP (type:test tag — builder writes tests as deliverable)

### Verdict: APPROVE
### Action Taken: Refined all 7 AC lines with td annotations, narrowed RED-phase delta, specified interaction model for keyboard/focus, excluded already-green behavior. Task advanced to todo.
[[2026-05-08]]
## Test-Writer Notes

**Test files:**
- `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` — imports non-existent `DecisionViewport` component; 19 tests collected, all fail via import error (valid RED evidence for new-file tasks)
- `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx` — 17 tests against current `ResolveModal`; all 17 fail

**RED verification:** 0 passed / 17 failed (vitest) + 0 lint violations (eslint)

**AC Coverage:**

| AC | td | Tests | Class | Fail reason |
|----|-----|-------|-------|-------------|
| AC1 — viewport renders items (task-id, agent, request_type, age, body_preview), loading/error/empty states | td:2 | 19 | `TestFromAC_DecisionViewport` | Import error — component doesn't exist |
| AC2 — resolution choices have consequence descriptions (not bare labels) | td:2 | 6 | `TestFromAC_ResolveModalUX` | Current labels are bare "approved"/"rejected"/"needs-info" |
| AC3 — no pre-selected choice; submit disabled until selection | td:2 | 4 | `TestFromAC_ResolveModalUX` | `useState('approved')` pre-selects; submit never disabled |
| AC4 — multi-word action labels; PDS p-text in option descriptions | td:1 | 3 | `TestFromAC_ResolveModalUX` | "Submit"/"Cancel" are single words; no p-text in selector |
| AC5 — keyboard/focus: initial focus, Escape, aria-modal; viewport items keyboard-reachable | td:2 | 4+viewport | `TestFromAC_ResolveModalUX` + viewport | No focus management, no Escape handler, no aria-modal |
| AC6 — viewport-level errors surface user-visible indicator | td:1 | 3 | `TestFromAC_DecisionViewport` | Import error — component doesn't exist |
| AC7 — proof fails against current tiny-popover and default-approved | td:1 | — | evidence | Proven by RED run |

**Total: 36 tests (19 DecisionViewport + 17 ResolveModalUX), all FAIL**
[[2026-05-08]]
## Builder Notes
- Scope: test-only deliverable for #1388 (no production implementation changes in this task).
- Files under scope:
  - serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx
  - serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx
- Commit evidence:
  - HEAD includes `61244801` with message: `test: add RED-phase tests for decision viewport and resolve modal UX (#1388, test-writer)`
  - Both scoped files are clean in working tree (`git status --porcelain -- <files>` showed no changes).
- RED verification (quality-runner, scoped):
  - DecisionViewport suite: import failure for missing `../components/DecisionViewport` (expected RED for new component task).
  - ResolveModalUX suite: 17/17 tests failing against current ResolveModal behavior (expected RED for AC2/AC3/AC4/AC5 deltas).
  - Aggregate: 0 passed, 17 failed (plus viewport import failure).
- Lint status:
  - eslint clean for both task-scoped test files (0 violations).
- Coverage note:
  - Not applicable for RED-phase test-only task closure; counterpart implementation task #1389 owns GREEN and coverage gates.
- Evidence summary:
  - AC deltas are now concretely encoded in failing tests and are ready for builder counterpart implementation in #1389.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped run succeeded on the Cockpit frontend toolchain.
- DecisionViewport suite: import fails because [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L18) imports a non-existent component. This is valid RED evidence for a new-file task, but it does not by itself prove the viewport assertions are discriminating.
- ResolveModalUX suite: 17 tests collected, 17 failed. Failures line up with current implementation defects, including default-approved state at [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L29), missing aria-modal on the dialog opened at [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L87), and single-word action buttons at [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L135) and [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L142).
- Current UI still uses the tiny status-bar popover via [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L136), [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L162), and [serve/cockpit/web/src/components/DRStatusIndicator.tsx](serve/cockpit/web/src/components/DRStatusIndicator.tsx#L37).

### Lint Results
- eslint: clean for both scoped test files.

### Coverage Data
- Not run. This is a RED-phase test-only task; the review gate here is proof quality, not GREEN coverage.

### Scope Reconstruction
- Commit 61244801 exists in the repository logs and matches the task-scoped test-only change set.
- Review scope reconstructed from the task body and commit note: [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx) and [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx).
- Small confidence deduction applied because this review tool surface did not provide a direct commit diff or dirty-tree check for full TestFromAC immutability verification.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: central decision viewport replaces tiny popover and renders task-id, agent/request type, age, body preview, loading/error/empty states | The task contract requires replacement of the tiny popover at [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L37), but the viewport suite only mounts a standalone component via [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L46). Age proof is lax at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L180) and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L193). Preview proof is lax because the fixture body and body_preview are identical at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L29) and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L30), while the assertion is only substring containment at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L204). | TestFromAC_DecisionViewport | FAIL |
| AC2: visible consequence descriptions explain the effect of approved/rejected/needs-info | The tests only require multi-word labels or extra text beyond the status token at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L81), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L93), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L105), and [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L118). Meaningless filler would still pass. | TestFromAC_ResolveModalUX | FAIL |
| AC3: no default-approved selection; explicit user selection required before submit is enabled | Strong proof exists at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L145), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L163), and [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L177), and those failures map directly to the current implementation default at [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L29). | TestFromAC_ResolveModalUX | PASS |
| AC4: descriptive multi-word action labels and modal/viewport structure uses PDS components | Label proof is reduced to word count at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L191). PDS proof is reduced to tag counting at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L213), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L218), and a broad p-* selector at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L233) and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L235). That does not prove the modal or viewport structure itself uses PDS components in a contract-level way. | TestFromAC_DecisionViewport, TestFromAC_ResolveModalUX | FAIL |
| AC5: initial focus on non-destructive element, Escape closes, tab order logical, decision items keyboard-reachable | Focus and Escape are partially covered at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L226), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L235), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L240), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L249), and [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L256), but there is no actual Tab traversal proof. Viewport keyboard proof only checks tag/role/tabindex semantics at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L242) and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L255), not real keyboard interaction. | TestFromAC_DecisionViewport, TestFromAC_ResolveModalUX | FAIL |
| AC6: viewport-level decision errors surface user-visible error indicators; ResolveModal error contract not duplicated | The viewport suite does cover visible error-state presence and accessible role at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L105) and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L263), and it does not duplicate ResolveModal error handling. One assertion is over-specific because it requires verbatim message content at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L108), but the required user-visible-indicator contract is still present. | TestFromAC_DecisionViewport | PASS |
| AC7: proof fails against current tiny-popover structure and default-approved selection; excludes already-green contracts | Default-approved is directly proven by AC3 tests and current code at [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L29). But the current tiny-popover structure is only present in the live shell at [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L136), [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L162), and [serve/cockpit/web/src/components/DRStatusIndicator.tsx](serve/cockpit/web/src/components/DRStatusIndicator.tsx#L37); the new viewport suite never proves replacement because it stays isolated at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L46). | TestFromAC_DecisionViewport, TestFromAC_ResolveModalUX | FAIL |

### Deductions
- Assertion specificity is WEAK. Several core checks reduce to word counts, non-empty text, substring containment, or broad tag counting rather than discriminating contract proof.
- AC1 and AC7 are only partially encoded. The suite does not prove the central viewport actually replaces the existing status-bar popover in Shell.
- AC5 is incomplete. Logical Tab order is part of the AC at [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L41), but no test exercises Tab traversal.
- Small confidence deduction for lack of direct diff/dirty-tree evidence in this review surface.

### Verdict
- FAIL -> backlog
- Confidence: 0.57
- Reason: the RED state is real, but the test contract is structurally weak and partially misaligned with the AC. Handing this directly to the implementation task would create both false-green and false-red risk.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC and test contract so the viewport work proves replacement of the live status-bar popover in Shell, not just a standalone component render | .owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md, serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx, serve/cockpit/web/src/Shell.tsx, serve/cockpit/web/src/components/DRStatusIndicator.tsx | AC1 and AC7 at [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L37) and [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L43); isolated render at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L46); live popover at [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L136), [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L162), and [serve/cockpit/web/src/components/DRStatusIndicator.tsx](serve/cockpit/web/src/components/DRStatusIndicator.tsx#L37) |
| 2 | architect | Tighten the expected proof for consequence descriptions, descriptive labels, and PDS structure so the task requires discriminating behavior assertions instead of word-count or generic tag-count heuristics | .owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md, serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx, serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx | AC2 and AC4 at [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L38) and [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L40); weak assertions at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L81), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L118), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L191), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L218), [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L204), and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L235) |
| 3 | architect | Specify interaction-level proof for task-id activation and logical Tab order; current task wording is stronger than the tests actually encode | .owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md, serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx, serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx | AC1 and AC5 at [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L37) and [.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md](.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md#L41); task-id semantics only at [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L138), [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L150), and [serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx](serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx#L223); missing Tab traversal with only focus/Escape checks at [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L226), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L240), [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L249), and [serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx#L256) |

### Action Taken
- Rejected task 1388 to backlog for AC/test-contract refinement before another RED-phase retry.
[[2026-05-08]]


## Architecture Review (Pass 2 — Reviewer Remediation)

### Context
Reviewer rejected #1388 from `review` back to `backlog` (confidence 0.57) with three follow-ups:
1. Standalone viewport render doesn't prove Shell popover replacement (AC1/AC7).
2. Word-count and tag-count assertions are too weak to discriminate — consequence descriptions, labels, PDS structure need structural proof (AC2/AC4).
3. Tab traversal claimed in AC5 but not tested; task-id activation proof incomplete (AC5/AC1).

### AC Refinements Applied
| AC | Change | Rationale |
|----|--------|-----------|
| AC1 | Removed "replacing the tiny status-bar popover." Added fixture discrimination (body_preview ≠ substring of body), onItemClick callback proof, fake-timer age proof. | Shell integration is #1389's scope. Standalone component tests prove the component contract. Fixture discrimination prevents false-green from body rendering. |
| AC2 | Changed from "visible consequence descriptions" to "structurally separate description element (p-text) adjacent to radio input." | Prevents word-count-only assertions from satisfying the AC. Tests must check DOM structure, not label text length. |
| AC4 | Specified ≥3 p-text elements in response selector (one per option description). | Replaces generic "PDS components" with structural check. |
| AC5 | Explicitly deferred Tab traversal to E2E tests (covered by #1395/#1396 accessibility gate). Kept focus/Escape/aria-modal. | jsdom doesn't support real focus model — Tab traversal proof requires browser context. |
| AC7 | Removed "fails against current tiny-popover structure." Added explicit scope note: Shell replacement is #1389. | Aligns AC7 with what standalone component tests can actually prove. |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task for decision viewport and resolution UX — single domain |
| Interface clarity | PASS | All AC lines specify DOM structure, ARIA attributes, data-testid selectors, and callback contracts |
| Dependency correctness | PASS | #1387 archived (done). No other deps. |
| Module layering | N/A | Test task |
| TDD compliance | PASS | This IS the RED phase task; #1389 depends on it |
| KISS/YAGNI | PASS | Scope excludes backend lifecycle, data plumbing, global a11y audit, Shell integration |
| Premise challenge | PASS | Audit evidence confirms real UX defects in current ResolveModal |
| Pattern consistency | PASS | TDD-paired pattern consistent with #1386/#1387, #1374/#1375 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: block (confidence 0.24)
- Findings: (1) source-of-truth mismatch — old AC still in task body. (2) test artifacts don't match refined AC. (3) #1389 AC not yet aligned. (4) Tab deferral target tasks #1395/#1396 exist but not explicitly linked.
- Architect response: (1) ACCEPTED — refined AC now persisted to task body (this edit). (2) EXPECTED — tests will be updated by test-writer on next pipeline pass; that's how TDD refinement works. (3) NOTED — #1389 will get its own arch review when dispatched; its AC aligns to #1388's test contract at review time, not before. (4) ACCEPTED — deferral target now explicit in AC5 text.

### Test Depth
- Max depth: 2 (AC1, AC2, AC3, AC5)
- Test-writer: processes task normally (existing tests need updating to match refined AC)

### Note on existing tests
The test-writer must update both test files to match the refined AC:
- DecisionViewport_1388.test.tsx: update fixtures so body_preview ≠ substring of body; verify onItemClick fires from task-id reference element specifically.
- ResolveModalUX_1388.test.tsx: replace word-count label assertions with structural description-element checks (p-text adjacent to radio, separate from label).

### Verdict: APPROVE
### Action Taken: Refined all 7 AC lines addressing reviewer's three follow-ups. Persisted refined AC to canonical task body. Advanced to todo.
[[2026-05-08]]
Architecture review pass 2 — refined AC addressing reviewer rejection. Key changes: (1) AC1 removed Shell replacement language — component contract only, Shell wiring is #1389. (2) AC2 requires structurally separate p-text description elements, not word-count checks. (3) AC5 defers Tab traversal to E2E (#1395/#1396). (4) AC7 scopes out Shell integration. (5) AC1 requires discriminating fixtures (body_preview ≠ substring of body). Test-writer must update both test files to match refined AC on next pass.
[[2026-05-08]]
## Test-Writer Notes

**Retry pass — architectural refinements from Pass 2 applied.**

**Test files:**
- `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` — 19 tests, all FAIL via import error (component does not exist)
- `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx` — 17 tests, all FAIL against current defects

**Changes from previous RED pass (addressing reviewer gaps via arch Pass 2):**
1. **AC1 fixtures (DecisionViewport):** `body_preview` updated to NOT be a substring of `body` in both DR_A and DR_B — prevents false-green if component renders full body instead of preview field.
2. **AC1 onItemClick (DecisionViewport):** Test now fires `fireEvent.click` on `[data-testid="decision-task-ref-*"]` specifically (not the generic item container) — proves `onItemClick` fires from the task-id reference element.
3. **AC2 structural tests (ResolveModalUX):** Replaced 6 word-count label assertions with 6 structural `p-text` DOM checks. For each option (approved/rejected/needs-info): (a) verifies a `p-text` exists in the option container that is NOT inside the radio's `<label>`, (b) verifies the `p-text` content has action-oriented text beyond the bare status token (>4 chars after stripping the token).

**RED verification (vitest scoped):**
- DecisionViewport: import fails — component does not exist (valid RED for new-component task)
- ResolveModalUX: 17/17 FAIL — no `p-text` in fieldset, `useState('approved')` pre-selects, submit never disabled, single-word labels, no focus management, no Escape handler, no `aria-modal`

**Lint:** eslint clean (0 violations) for both files.

**AC Coverage:**

| AC | td | Tests | Class | Status |
|----|-----|-------|-------|--------|
| AC1 — viewport renders task-id ref (fires onItemClick), agent, request_type, age (fake timers), body_preview (discriminating fixture), loading/error/empty states | td:2 | 19 | `TestFromAC_DecisionViewport` | FAIL (import error) |
| AC2 — each option has p-text description element structurally separate from radio label; content has action-oriented words | td:2 | 6 | `TestFromAC_ResolveModalUX` | FAIL (no p-text in fieldset) |
| AC3 — no pre-selected choice; submit disabled until selection | td:2 | 4 | `TestFromAC_ResolveModalUX` | FAIL (useState('approved')) |
| AC4 — multi-word action labels; ≥3 p-text in response selector | td:1 | 3 | `TestFromAC_ResolveModalUX` | FAIL |
| AC5 — initial focus inside modal (not submit), Escape closes, aria-modal | td:2 | 4 | `TestFromAC_ResolveModalUX` | FAIL |
| AC6 — viewport error has role=alert/status; surfaces message | td:1 | 3 | `TestFromAC_DecisionViewport` | FAIL (import error) |
| AC7 — proof fails against current defects | td:1 | evidence | — | Proven by RED run |

**Total: 36 tests (19 DecisionViewport + 17 ResolveModalUX), all FAIL**
**Commit: 69f82181**
[[2026-05-08]]
## Builder Notes
- Non-implementation task (test-only RED artifact handoff).
- No source-code changes applied by builder.
- Files in scope:
  - serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx
  - serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx
- quality-runner (scoped) evidence:
  - Tests: 0 passed, 17 failed (expected RED)
  - DecisionViewport suite failure confirms missing `DecisionViewport` import/implementation (expected for counterpart implementation task #1389).
  - ResolveModalUX failures confirm unresolved UX defects (selection default/labels/focus/Escape/aria-modal and related assertions) as intended RED baseline.
  - Lint: eslint clean (0 violations) on both scoped test files.
- Coverage: N/A for this RED test-only gate.
- Outcome: Builder pass-through to review with verified RED evidence; no file edits, no commit required.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run succeeded for the Cockpit web package.
- `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` still fails at import time because it imports `../components/DecisionViewport` at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:18`, and no matching component file exists under `serve/cockpit/web/src/components/`.
- `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx` collected 17 tests and all 17 failed, matching the current defects in `serve/cockpit/web/src/components/ResolveModal.tsx`: default-approved state at `:29`, missing `aria-modal` on the modal opened at `:87`, and single-word action buttons at `:135` and `:142`.

### Lint Results
- eslint clean on both scoped files: `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` and `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`.

### Coverage Data
- Not run. This is a RED-phase test-only review; the gate here is proof quality, not GREEN coverage.

### Scope Reconstruction
- Review scope reconstructed as `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` and `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`.
- Commit `69f82181` is present in repository logs and matches the retry noted in the task body.
- The task file already contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md:122`, so this is a second-cycle review. On FAIL, the loop-breaker route is `backlog`.
- Direct `git diff` / `git status` evidence was not available in this tool surface, so I applied a small confidence deduction for scope/immutability verification.
- Review anchored to the latest refined AC at `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md:37` through `:43`, not the stale first-pass review findings that were superseded by Architecture Review Pass 2.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | The retry correctly strengthened the `body_preview` fixture discrimination at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:31`, `:43`, `:203`, and `:206`, and it correctly proves `onItemClick` fires from the task-id reference at `:227` and `:233`. But the required age proof is still non-discriminating: the suite only asserts non-empty row text at `:182` and compares full row text at `:192`, `:193`, and `:195`, so other row fields can make the assertion pass even if the age field is wrong or constant. | `TestFromAC_DecisionViewport` | FAIL |
| AC2 | The suite now targets structural description elements, but each per-option lookup walks from the radio label to `parentElement` and then grabs the first `p-text` descendant at `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:83` through `:85`, `:97` through `:101`, `:111` through `:113`, `:124` through `:128`, `:138` through `:140`, and `:151` through `:155`. In the current markup, all labels are siblings in the same fieldset at `serve/cockpit/web/src/components/ResolveModal.tsx:91`, so one shared description node could satisfy every assertion without being adjacent to a specific option. The consequence-copy proof is also weak because it reduces to `text.length > 4` after stripping the status token at `:101`, `:128`, and `:155`. | `TestFromAC_ResolveModalUX` | FAIL |
| AC3 | Strong proof exists for the no-default-selection and disabled-until-selection contract at `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:177`, `:187`, `:194`, `:197`, and `:201`, and those failures map directly to the current implementation default at `serve/cockpit/web/src/components/ResolveModal.tsx:29`. | `TestFromAC_ResolveModalUX` | PASS |
| AC4 | The refined AC is directly encoded by the multi-word label assertions at `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:216` and `:227`, plus the `>= 3` description-element assertion at `:235`. | `TestFromAC_ResolveModalUX` | PASS |
| AC5 | The modal half of the contract is well targeted: initial focus inside the modal and not on submit at `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:252` and `:254`, Escape on modal/document at `:262` and `:269`, and `aria-modal="true"` at `:278`. The remaining gap is viewport item focusability: the suite checks button/link semantics on `decision-item` elements at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:255` and `:256`, but the no-`tabindex=-1` assertion is only applied to the task-id reference at `:263`. That splits the focusability proof across two different elements, so a non-tabbable `decision-item` could still pass. Logical Tab traversal was correctly treated as out of scope per the refined AC. | `TestFromAC_DecisionViewport`, `TestFromAC_ResolveModalUX` | FAIL |
| AC6 | The viewport error-state contract is covered by the visible error assertions at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:101`, `:107`, and `:268`, and the suite does not duplicate ResolveModal error handling already covered by #1375. | `TestFromAC_DecisionViewport` | PASS |
| AC7 | The RED delta is proven. `DecisionViewport` import remains unresolved at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:18`, and the scoped quality-runner pass confirmed `ResolveModalUX_1388` still fails 17/17 against the current defects rooted in `serve/cockpit/web/src/components/ResolveModal.tsx:29` and `:87`. The latest AC explicitly scopes Shell-level popover replacement out of this task. | `TestFromAC_DecisionViewport`, `TestFromAC_ResolveModalUX` | PASS |

### Deductions
- Test quality is still **WEAK** for a td:2 artifact. The remaining failures are proof-quality failures, not RED-execution failures.
- No `TestFromAC_*` weakening or removal detected in scope.
- No security or data-safety issues found in the scoped files.
- Non-blocking overreach remains in `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx`: default-export smoke test at `:71` and generic PDS-presence test at `:238` are not traceable to the refined AC.

### Verdict
- FAIL -> backlog
- Confidence: 0.84
- Reason: second-cycle review. RED evidence is valid, but the td:2 proof is still non-discriminating on AC1, AC2, and AC5.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rework the AC1 RED contract so the age assertion targets an isolated age field or age-specific string derived from `created`, not whole-row text, then send the task back through test-writing | `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md`, `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` | AC1 at `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md:37`; weak age assertions at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:182`, `:192`, `:193`, `:195` |
| 2 | architect | Rework the AC2 RED contract so each radio option must own its own adjacent description element and the consequence-copy proof is stricter than `text.length > 4`, then re-dispatch test-writing | `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md`, `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx` | AC2 at `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md:38`; broad fieldset-rooted queries at `serve/cockpit/web/src/__tests__/ResolveModalUX_1388.test.tsx:83` through `:85`, `:97` through `:101`, `:111` through `:113`, `:124` through `:128`, `:138` through `:140`, `:151` through `:155`; current sibling-label structure at `serve/cockpit/web/src/components/ResolveModal.tsx:91` |
| 3 | architect | Clarify AC5 so the same viewport element carries both the button/link semantics and the no-`tabindex=-1` requirement, then re-dispatch test-writing with that single focus target | `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md`, `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx` | AC5 at `.owlbear/kanban/tasks/1388-p2-13-test-cockpit-decision-viewport-and-resolution-ux.md:41`; split proof at `serve/cockpit/web/src/__tests__/DecisionViewport_1388.test.tsx:255`, `:256`, `:263` |

### Action Taken
- Rejected task 1388 to `backlog` under the reviewer loop-breaker rule for architect-mediated contract tightening before another RED-phase retry.