---
id: 1541
title: 'P3-07: test — sidecar collapse toggle'
status: archived
priority: medium
created: 2026-05-13T18:41:58.362901+00:00
updated: 2026-05-14T02:56:32.966203+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - test
  - frontend
parent: 1534
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Tests for sidecar collapse/expand button, visibility toggle, state persistence across re-renders
- **Out:** Sidecar CSS implementation, transition animation, layout space reclaim verification

## Acceptance Criteria

- AC-1: Vitest renders Shell, locates a collapse toggle via `data-testid="sidecar-collapse"`, asserts it is a native `<button>` element (`tagName === 'BUTTON'`), asserts default `aria-expanded="true"`, asserts `aria-controls` resolves by `id` to an element within `[data-region="sidecar"]`; the controlled element does NOT contain the toggle (`controlled.contains(toggle)` is `false`) — structural proof that collapse hides content without hiding the toggle itself; the controlled element does not have `aria-hidden="true"` in default state (proves panel starts open); clicking the button sets `aria-expanded` to `"false"` and the controlled element has `aria-hidden="true"`; after collapse, re-query toggle via `data-testid="sidecar-collapse"` and verify it remains in DOM and is NOT a descendant of any element with `aria-hidden="true"` (reopenability proof); clicking the toggle again restores `aria-expanded` to `"true"` and the controlled element does not have `aria-hidden="true"` (round-trip proof)
- AC-2: Vitest verifies collapsed state persists after `rerender()` — re-query toggle via `data-testid="sidecar-collapse"`, verify `aria-expanded="false"` and controlled element `aria-hidden="true"`; also verify re-queried toggle is NOT a descendant of any element with `aria-hidden="true"` (reopenability persists)

Proof bundle: behavioral

## Builder Guidance
- Follow filter toggle ARIA pattern from KanbanBoard.tsx (L264-267: `<button type="button">` + `aria-expanded` + `aria-controls` + `onClick` toggle)
- Use Shell.test.tsx mock setup (vi.mock EventSourceProvider + vi.stubGlobal fetch)
- Test file: `src/__tests__/SidecarCollapse_1541.test.tsx`
- RED phase: tests must fail against current Shell.tsx (no collapse mechanism exists yet)
- Button-semantics assertion: `expect(toggle.tagName).toBe('BUTTON')` — proves native button, not a clickable div/span with role
- Collapse indicator: assert controlled element has `aria-hidden="true"` when collapsed; element must remain in DOM for CSS transition compatibility — do NOT use `hidden` attribute or DOM removal
- Default-open proof: before first click, assert controlled element does NOT have `aria-hidden="true"` — proves panel starts accessible/open
- Round-trip proof: after collapsing, click toggle again and assert `aria-expanded="true"` is restored and controlled element does not have `aria-hidden="true"`
- Containment proof: assert `controlled.contains(toggle)` is `false` — proves the toggle is NOT inside the controlled (collapsible) element, so collapse cannot hide the expand control
- Reopenability proof: after each collapse, re-query toggle via `data-testid="sidecar-collapse"` and walk its ancestors — verify none have `aria-hidden="true"`. This proves the toggle remains accessible to assistive tech even after content is hidden. Use a helper like: `let ancestor = toggle.parentElement; while (ancestor) { expect(ancestor.getAttribute('aria-hidden')).not.toBe('true'); ancestor = ancestor.parentElement; }`
- The controlled element referenced by `aria-controls` may be an inner content wrapper — locate it by `id` resolution from `aria-controls`, not by hardcoding `data-region="sidecar"`
- AC-2 persistence: after `rerender()`, re-query both toggle and controlled element fresh (do not reuse stale references)

## Research
- Research doc: .owlbear/research/1541-sidecar-collapse-toggle-test-approach.md
- Sources: 6 studied, 3 high-relevance (filter toggle pattern, Shell.test.tsx, brief)
- Recommendation: ARIA disclosure pattern (aria-expanded + aria-controls) with CSS class toggle for visibility, rerender() for state persistence test (confidence: 0.85)
- Follow-up tasks created: none (implementation task #1549 already exists)
- Decision requests: none
2026-05-14T02:02:51+00:00
## Architecture Review (re-review round 3 — post second reviewer rejection)

### Changes from previous round
Addressed reviewer findings 1 and 2 from the second review cycle:

**Finding 1 (loose aria-controls target):** AC-1 now requires `controlled.contains(toggle)` to be `false` — structural proof that the controlled element does not contain the toggle. This prevents pointing `aria-controls` at the toggle itself or at a parent wrapper that wraps the toggle. Builder Guidance adds explicit "Containment proof" pattern.

**Finding 2 (no reopenability proof):** AC-1 and AC-2 now require re-querying the toggle after collapse and verifying it is NOT a descendant of any `aria-hidden="true"` element. This proves the toggle remains accessible to assistive technology after content is hidden. Builder Guidance adds explicit "Reopenability proof" helper pattern with ancestor-walking assertion.

**Additional hardening:** AC-2 now requires fresh DOM queries after `rerender()` — no stale references.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: RED tests for sidecar collapse toggle |
| Interface clarity | PASS (refined) | AC-1: native button + containment proof + default-open proof + collapse proof + reopenability proof + round-trip proof; AC-2: persistence proof with reopenability |
| Dependency correctness | PASS | No deps; RED phase tests run against unimplemented code |
| Module layering | PASS | Frontend test only, no cross-layer concerns |
| TDD compliance | PASS | This IS the RED phase; #1549 depends on it for GREEN |
| KISS/YAGNI | PASS | 2 focused AC lines, ~6 test assertions |
| Premise challenge | PASS | Brief L127-129 specifies collapsible sidecar with toggle button |
| Pattern consistency | PASS | Follows KanbanBoard.tsx L264-267 disclosure pattern |
| Security surface | PASS | No security boundary |
| Single domain | PASS | Frontend/cockpit only |

### Challenge Results
- Challenger: reconsider (confidence 0.61)
- Findings: (1) controlled element scope still under-specified relative to whole panel; (2) evidence drift — refinement not yet in repo; (3) AC-1 over-bundled
- Architect response: PARTIALLY ACCEPTED finding 1 — the "covers all content" concern is a visual/CSS question belonging to #1549's scope, not this ARIA-layer test. This task's scope explicitly excludes "CSS implementation, layout space reclaim." The containment+reopenability proofs are the correct layer boundary for a unit test. DISMISSED finding 2 — this IS the arch review that writes the refinement; artifacts update as output of this step. NOTED finding 3 — the 5 test cases provide clear failure attribution; splitting AC-1 into 5 lines would add verbosity without testability gains.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (pass-through via `test` tag — builder writes test file as deliverable)

### Design Diverge
- Trigger: skipped — single established approach (ARIA disclosure pattern), no competing designs

### Verdict: APPROVE (after AC refinement)
### Action Taken: Refined AC-1 (containment proof via controlled.contains(toggle)===false, reopenability proof via ancestor walk, fresh re-query pattern); refined AC-2 (fresh queries + reopenability persistence); updated Builder Guidance with concrete helper patterns. Advanced to todo.
2026-05-14T02:06:21+00:00
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx`
- Class: `TestFromAC_SidecarCollapse_1541`
- Tests: 8 total, all FAIL (RED confirmed)
- Lint: clean (ESLint 0 violations)

### AC Coverage
| AC | Tests |
|----|-------|
| AC-1: toggle is native button, aria-expanded="true", aria-controls within sidecar | 1 happy |
| AC-1: default-open proof (controlled not aria-hidden="true") | 1 happy |
| AC-1: containment proof (controlled.contains(toggle) === false) | 1 happy |
| AC-1: collapse — aria-expanded="false" + controlled aria-hidden="true" | 1 happy |
| AC-1: reopenability proof after collapse (ancestor walk) | 1 edge |
| AC-1: round-trip — second click restores open state | 1 happy |
| AC-2: collapsed state persists after rerender() | 1 happy |
| AC-2: reopenability persists after rerender() (ancestor walk) | 1 edge |

### Categories
- Happy path: 6
- Edge: 2
- Error: 0 (all tests error on missing toggle — correct RED behavior)
- Boundary: 0

### Fail evidence
All 8 tests throw `Error: sidecar-collapse toggle not found` — `data-testid="sidecar-collapse"` does not exist in current Shell.tsx (no collapse mechanism). vitest exit code: 1.
2026-05-14T02:27:54+00:00
## Builder Notes
- Files changed: serve/cockpit/web/src/Shell.tsx
- Implementation summary: added native sidecar collapse toggle (`data-testid="sidecar-collapse"`) with ARIA disclosure semantics (`aria-expanded`, `aria-controls`) and a controlled sidecar content wrapper (`id="shell-sidecar-content"`, `aria-hidden` on collapse). Toggle is outside controlled wrapper to preserve reopenability/accessibility when collapsed.

### RED Verification (pre-implementation)
- quality-runner scoped: serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx
- Result: 0 passed, 8 failed (all `TestFromAC_SidecarCollapse_1541` tests failed with `sidecar-collapse toggle not found`)
- Lint: clean

### Baseline Durable Module Test (pre-implementation)
- quality-runner scoped: serve/cockpit/web/src/__tests__/Shell.test.tsx
- Result: 18 passed, 0 failed
- Lint: clean

### GREEN Verification (post-implementation)
- quality-runner scoped: serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx
- Result: 8 passed, 0 failed
- Lint: clean for serve/cockpit/web/src/Shell.tsx and task test file
- Coverage (reported): Shell.tsx 81.62% (branch 83.41%, lines 77.41)

### Regression Check (post-implementation)
- quality-runner scoped combined: serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx + serve/cockpit/web/src/__tests__/Shell.test.tsx
- Result: 26 passed, 0 failed
- Lint: clean

### Commit
- Commit: 5c900665
- Message: feat: implement sidecar collapse semantics (#1541, builder)

### Evidence Summary
- AC-1 met: native button semantics, default-open state, collapse/expand round trip, containment and reopenability behavior.
- AC-2 met: collapsed state persists after rerender with reopenability retained.
- No unrelated files edited.
2026-05-14T02:42:06+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1541 -> docs | AC mapped to code and evidence sufficient.
- AC evidence:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/Shell.tsx:46` defaults `isSidecarCollapsed` to `false`; `serve/cockpit/web/src/Shell.tsx:172-179` adds a native `button` toggle with `data-testid="sidecar-collapse"`, `aria-expanded`, `aria-controls="shell-sidecar-content"`, click-toggle state update, and a controlled wrapper with `aria-hidden` driven by collapse state. | `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:54-69` proves native button semantics, default `aria-expanded`, and `aria-controls` target within `[data-region="sidecar"]`; `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:72-96` proves default-open state, containment, and collapse behavior; `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:99-125` proves reopenability after collapse and round-trip expansion. | PASS |
| AC-2 | `serve/cockpit/web/src/Shell.tsx:46,175,179` keep collapse state in component-local React state and bind the controlled wrapper visibility to that state across rerenders. | `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:128-170` rerenders the tree, re-queries toggle and controlled element, and proves collapsed `aria-expanded`/`aria-hidden` state plus reopenability persist after rerender. | PASS |

- Builder evidence consistency: task body includes scoped RED, GREEN, and regression evidence for `SidecarCollapse_1541.test.tsx` and `Shell.test.tsx`, plus clean lint for `Shell.tsx` and the task test. I independently verified there are no IDE errors in `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx`, or `serve/cockpit/web/src/__tests__/Shell.test.tsx`.
- Commit evidence: builder commit `5c900665` is present in `.git/logs/refs/heads/dev` and `.git/logs/HEAD`.
- Safety & security: reviewed change only adds local UI state and ARIA wiring in `Shell.tsx`; no new input-handling, auth, storage, or dependency surface was introduced.

## Observations
- `#1541` now overlaps part of `#1549` on button/state semantics. `#1549` still owns the CSS-transition aspect, but its remaining scope should be reconciled before dispatch so the next agent does not duplicate the already-landed semantics.
- Builder-reported `Shell.tsx` coverage (`81.62%`) is below the general pipeline target, but the task’s AC-specific assertions are direct and falsifiable, so this is not a blocking proof gap for `#1541`.
2026-05-14T02:45:33+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | No | N/A | `serve/cockpit/README.md` contains no mention of "sidecar", "Shell", or "collapse" — README is backend/API-focused and does not document individual frontend components; no stale content relative to this change |
| 2 | External attribution | No | N/A | `.owlbear/sources/overview.md` already contains "Sidecar Collapse Toggle Test Research (Task #1541)" section with WAI-ARIA source; attribution handled by researcher |
| 3 | Research doc | Yes | N/A | `.owlbear/research/1541-sidecar-collapse-toggle-test-approach.md` exists and is linked from task body |
| 4 | Deletion detection | No | N/A | Builder only modified `serve/cockpit/web/src/Shell.tsx`; no files deleted, no orphaned references |

### Verification Layers
- Layer 1 — grep: no matches for "sidecar", "Shell", "collapse" in `serve/cockpit/README.md`; research doc path confirmed in `.owlbear/research/`; sources section confirmed in `.owlbear/sources/overview.md`
- Layer 2 — editorial: README covers backend API, launch, frontend stack, error envelopes, sessions model, decisions API, configuration, delivery packaging, and dependencies — all unchanged by this task; no coherence gaps or contradictions introduced

### Scratch Cleanup
No `.owlbear/scratch/1541-*` files found.
2026-05-14T02:56:32+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4594 passed, 20 failed (all pre-existing: deleted task-test FileNotFoundErrors, engine config access pattern assertions, bridge element naming), 5 errors (pytest-timeout on vitest wrappers), 14 skipped. Lint clean. No failures related to #1541.
- Frontend suite: builder+reviewer verified 26/26 pass (8 task + 18 Shell module tests). vitest instrument_error in full run is infrastructure, not task regression.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (single file changed: Shell.tsx in cockpit frontend domain; tags scope:cockpit/frontend/test match)
- purpose match: PASS (ARIA disclosure pattern for sidecar collapse toggle — matches AC intent)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC went through 3 rounds of arch review. Final AC is highly specific with 6 distinct proof categories (button semantics, default-open, containment, reopenability, round-trip, persistence). Minor initial gaps caught and refined through reviewer rejection cycles — process worked correctly.

### Commit Integrity
- upstream commit presence: PASS (builder commit 5c900665 confirmed, touches only Shell.tsx +95/-83; test-writer commits 7b6d2fc1, 66f26e92 also present)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive