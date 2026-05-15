---
id: 1565
title: 'P2-10 RED: Specify task card information density'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.493454+00:00
updated: 2026-05-15T03:56:11.406375+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - cards
  - visual-remediation
parent: 1559
depends_on:
  - 1560
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8. Cards currently communicate too little beyond title and rail color.

## Scope
In scope: task-card metadata, state cues, accessible naming, and overflow behavior.
Out of scope: column layout, sidecar detail rendering, filter workflow, and drag-and-drop behavior beyond preserving existing reachability.

## Acceptance Criteria
AC-1: Test-writer adds E2E rendering fixtures for task cards with id, title, priority tag, tag preview with overflow indicator, blocked cue, claimed cue, deps-unmet cue, and DR-pending cue; verify by quality-runner output for named tests.
AC-2: Test-writer adds an accessibility check that blocked, claimed, deps-unmet, and DR-pending states are perceivable without relying on rail color; verify by axe or locator assertions.
AC-3: Test-writer records current failing evidence that cards are title-only in the production board; verify by artifact inspection of Test Evidence.
AC-4: Test-writer adds card fixture coverage for compact update-recency metadata using the `updated` field available on the task list endpoint, such as relative age or stale-work indication, with accessible text that does not rely on color alone; verify by named test output.

Proof bundle: behavioral

## Evidence Expectations
Failing card-density proof and accessible-state evidence.


## Content Audit Amendment — Age / Recency Signal
The consolidated audit explicitly calls out that cards lack age information. The RED task must preserve that requirement so the GREEN implementation cannot stop at ID/status/tags alone.

AC-4 covers this requirement. The test-writer should use the `updated` timestamp from TaskSummary (available on `/api/tasks` list endpoint) rather than `created` (only available on the single-task detail endpoint) to avoid unfunded backend changes in the GREEN task.

Evidence expectation: failing current-card proof shows no age/update-recency signal on task cards.
2026-05-14T20:39:09+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 4 ACs focused on card information density test specification |
| Interface clarity | PASS | Each AC names agent, artifact, and verification method |
| Dependency correctness | PASS | #1560 (design policy gate) is archived as completed |
| Module layering | N/A | Test-only task, no production code |
| TDD compliance | PASS | This IS the RED task; GREEN is #1570 |
| KISS/YAGNI | PASS | 4 focused ACs, no hypothetical requirements |
| Premise challenge | PASS | Cards confirmed title-only in Card.tsx; computeSignal.ts provides signals unused in UI |
| Pattern consistency | PASS | Follows existing E2E test pattern in serve/cockpit/web/e2e/ |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signal C2 present (AC specifies expected test outcomes) |
| DR verification | N/A | References research doc, not research-tagged |

### AC Assessment (Post-Refinement)
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 | PASS — tightened "priority or status tag" to "priority tag" (status redundant with column); added deps-unmet cue | Refined |
| AC-2 | PASS — added deps-unmet to accessibility check (design policy rejects color-only signaling for all states) | Refined |
| AC-3 | PASS — baseline failing evidence, clear verification | No change |
| AC-4 | PASS — clarified `updated`-based recency from TaskSummary; prevents unfunded backend changes in GREEN | Refined |

### Architecture Notes
- Card.tsx renders only title; computeSignal.ts computes 5 states (dr-pending, blocked, claimed, deps-unmet, ready) but only rail color distinguishes them
- TaskSummary provides id, title, status, priority, updated, tags, blocked, claimed, dep_status — sufficient for all AC assertions
- `created` is NOT on TaskSummary (only on TaskFull detail endpoint); AC-4 scoped to `updated` to match available list data
- Existing E2E patterns: Playwright with page.route() API mocking, data-testid selectors
- Consolidation test #1573 exists under parent #1559 covering all implementation siblings

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Findings: (1) AC-1 status-tag ambiguity, (2) AC-2 missing deps-unmet, (3) AC-4 created/updated data split, (4) PDS component naming, (5) wrong claim about #1560 status
- Architect response: accepted findings 1-3 and refined AC lines; rebutted finding 4 (PDS component selection is GREEN concern, consolidation test verifies); rebutted finding 5 (#1560 IS archived per show_task)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single valid approach (E2E Playwright tests asserting card density elements)

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined 3 AC lines to close challenger-identified gaps, then advanced to todo
2026-05-14T21:25:22+00:00
## Test-Writer Notes

**Test file:** `serve/cockpit/web/e2e/card-density-1565.spec.ts`

**Framework:** Playwright E2E (matches existing pattern in `serve/cockpit/web/e2e/`)

**Test classes:**

| describe block | Category | Tests |
|---|---|---|
| AC-1 \| Card rendering fixtures — id, priority, tags, state cues | happy/cue | 8 |
| AC-2 \| Accessibility — blocked, claimed, deps-unmet, dr-pending without color | accessibility | 4 |
| AC-3 \| Baseline failing evidence — pre-remediation title-only baseline | baseline proof | 2 |
| AC-4 \| Update recency metadata using updated field from TaskSummary | edge/boundary | 4 |

**Total: 18 tests — ALL FAIL (quality-runner confirmed: passed=0, failed=18)**

**Fail mechanism:** Every test asserts presence of a `data-testid` element (e.g., `card-id`, `card-priority`, `card-blocked-cue`, `card-updated`) that does not exist in the current `Card.tsx` (which renders only `<span data-testid="card-title">`). Tests timeout with "locator expected to be visible" — clean, expected RED failures.

**AC coverage:**

| AC | Tests | Coverage |
|---|---|---|
| AC-1 | 8 tests — id, priority tag, tag preview, overflow indicator, blocked/claimed/deps-unmet/dr-pending cues | FULL |
| AC-2 | 4 tests — each cue element checked for visible text via locator assertions | FULL |
| AC-3 | Comment block (═══ violation catalogue) + 2 baseline-proof tests | FULL |
| AC-4 | 4 tests — recency element exists, non-empty text, stale task, relative (non-ISO) format | FULL |

**Fixtures:**
- 7 task variants: TASK_READY, TASK_BLOCKED, TASK_CLAIMED, TASK_DEPS_UNMET, TASK_DR_PENDING, TASK_MANY_TAGS (5 tags), TASK_STALE (updated 2026-01-01)
- PENDING_DR_FOR_TASK_5 stubs `/api/decisions/pending` → Shell.tsx builds `pendingDRIds = new Set([5])` → `computeSignal` returns `dr-pending` for task 5
- Route registration follows LIFO pattern (generic catch-all first, specific last)

**Lint:** ESLint clean (exit 0)
**Commit:** fcfa1f42 — `test: add failing E2E tests for card information density (#1565, test-writer)`
2026-05-14T22:22:49+00:00
## Builder Notes
- Implementation: serve/cockpit/web/src/components/Card.tsx, serve/cockpit/web/src/components/Card.css
- Approach: Expanded card rendering from title-only to explicit metadata rows with required `data-testid` hooks (`card-id`, `card-priority`, `card-tags`, `card-tag-overflow`, `card-*-cue`, `card-updated`), plus state cue text and compact updated-age formatting derived from `task.updated`.
- RED verification (quality-runner): 0 passed / 18 failed on `serve/cockpit/web/e2e/card-density-1565.spec.ts`; failures were all missing `card-*` elements (expected pre-implementation).
- GREEN verification (quality-runner): 18 passed / 0 failed on `serve/cockpit/web/e2e/card-density-1565.spec.ts`.
- Durable regression check (quality-runner): 61 passed / 0 failed on `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` and `serve/cockpit/web/src/__tests__/BoardVisualDesign.test.tsx`.
- Lint status (quality-runner): clean (`eslint` + `stylelint` exit 0 for scoped paths).
- Coverage: N/A for Playwright/Vitest scoped evidence in this run (no module coverage report emitted by quality-runner).
- Fixes applied:
  - Added visible/accessible text cues for blocked, claimed, deps-unmet, and dr-pending states (no color-only dependency).
  - Added tag preview with overflow indicator for >3 tags.
  - Added relative recency metadata text that avoids raw ISO timestamp output.
- Commit: 74c50eb5 (`feat: implement card information density cues (#1565, builder)`).
2026-05-14T22:37:25+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1565 -> todo | AC-4 recency proof can false-green, and independent scoped coverage for Card.tsx is only 38.88%.
- AC mapping summary:
  - AC-1: Implemented card metadata/cue surface is present in `Card.tsx` (`card-tags` at line 124, `card-tag-overflow` at line 128, state cues at lines 137/142/147/152).
  - AC-2: Cue text is rendered in `Card.tsx` (`Blocked`, `Claimed`, `Dependencies blocked`, `Decision pending` at lines 138/143/148/153) and the Playwright spec asserts readable text at lines 331/343/355/367.
  - AC-3: Baseline title-only evidence remains documented in the spec header and baseline tests at lines 372-396.
  - AC-4: The implementation derives recency from `task.updated` (`Card.tsx:51`) and renders `card-updated` (`Card.tsx:113`), but the proof surface is insufficient.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | The recency tests only prove visibility, non-empty text, stale-card element presence, and non-ISO formatting. They do not prove that output actually varies with `updated` or conveys stale/relative age, so a constant non-ISO label would still pass. | `serve/cockpit/web/e2e/card-density-1565.spec.ts:400-442`; concrete constant-label example exists at `serve/cockpit/web/src/components/Card.tsx:11` (`Updated recently`) | todo |
| 2 | AC-4 / Proof bundle: behavioral | Independent reviewer rerun produced scoped frontend coverage of only 38.88% for `Card.tsx`, so the changed executable surface still lacks sufficient behavioral proof. | quality-runner scoped rerun: Tests 33 passed / 0 failed; Lint clean; Coverage `overall_pct: 38.88`, module `Card.tsx: 38.88%`; exit codes `vitest=0`, `eslint=0`, `stylelint=0`, `playwright=0` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC-4 recency assertions so they fail if every card renders the same constant non-ISO label; compare distinct `updated` fixtures and assert meaningful relative/stale output. | `serve/cockpit/web/e2e/card-density-1565.spec.ts` | Finding #1 |
| 2 | test-writer | Add or extend instrumented frontend tests that raise `Card.tsx` behavioral coverage to the phase gate while preserving the existing E2E contract. | `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`, `serve/cockpit/web/src/__tests__/Card.css.test.ts`, `serve/cockpit/web/src/components/Card.tsx` | Finding #2 |

## Observations
- No implementation defect was proven in the reviewed UI surface. The current `Card.tsx` does render id/priority/updated chips, tag preview/overflow, and text cues for blocked/claimed/deps-unmet/dr-pending.
- Builder-provided notes left coverage as `N/A`, so reviewer had to obtain independent scoped evidence. That rerun was otherwise clean: Playwright, Vitest, ESLint, and Stylelint all passed.
2026-05-14T22:56:55+00:00
## Test-Writer Notes

**Retry cycle — direct-to-review advance (Step 1b.1)**

**Modified file:** `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`

**New describe blocks added:**

| Describe block | Category | Tests | Addresses |
|---|---|---|---|
| TestFromAC_CardDensityElements | happy | 3 | Finding #2 (coverage) |
| TestFromAC_UpdateRecencyBranches | boundary/edge | 5 | Finding #1 + #2 |
| TestFromAC_CardCueRendering | happy/edge | 11 | Finding #2 (coverage) |

**Total new tests: 19 — ALL PASS against current impl (74c50eb5)**

**Finding #1 resolution (AC-4 weak recency assertions):**
- Added exact-output tests for each formatUpdatedAge branch (minutes/hours/days/fallback) using `vi.useFakeTimers()` with fixed "now" = 2026-05-15T12:00:00Z
- Constant-label guard: "stale task (months old) renders different recency text than a recent task" — asserts stale (2026-01-01, ~134d) != recent (2026-05-15T11:50, 10m); fails any constant-label implementation
- Note: path guard blocked modification to `e2e/card-density-1565.spec.ts`; Vitest unit tests provide stronger (deterministic) proof than the E2E comparison

**Finding #2 resolution (Card.tsx coverage 38.88%):**
- 11 cue-rendering tests cover all conditional branches in Card.tsx render (blocked/claimed/deps-unmet/dr-pending cues, tags, overflow)
- 5 recency tests cover all `formatUpdatedAge` branches plus the stale-vs-recent guard
- 3 density-element tests cover id/priority/updated chip rendering

**Step 1b.1 qualification:**
- All reviewer Required Follow-up items target test gaps only (no implementation fixes needed)
- All 24 tests in file pass (5 pre-existing + 19 new) against current implementation
- Builder pass-through unnecessary

**Lint:** ESLint clean (exit 0)
**Commit:** e48fd533 — `test: add density/recency/cue coverage for Card.tsx retry (#1565, test-writer)`
2026-05-14T23:53:00+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1565 -> backlog | AC-1 still lacks the required task-local E2E title fixture, so the second review cycle escalates to backlog.
- AC mapping summary:
  - AC-1: The implementation does render title text in `Card.tsx` (`card-title` at `serve/cockpit/web/src/components/Card.tsx:118`), and adjacent durable proof exists in `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx:297` and `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx:305`, but the task contract explicitly requires E2E fixtures for title at `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:32`. The task-local Playwright AC-1 block starts at `serve/cockpit/web/e2e/card-density-1565.spec.ts:243` and omits title from its own scope line at `serve/cockpit/web/e2e/card-density-1565.spec.ts:243`; `card-title` appears only in comments at `serve/cockpit/web/e2e/card-density-1565.spec.ts:18` and `serve/cockpit/web/e2e/card-density-1565.spec.ts:380`, not in an assertion.
  - AC-2: Satisfied. `Card.tsx` renders readable cue text for blocked/claimed/deps-unmet/DR-pending at `serve/cockpit/web/src/components/Card.tsx:137`, `serve/cockpit/web/src/components/Card.tsx:142`, `serve/cockpit/web/src/components/Card.tsx:147`, and `serve/cockpit/web/src/components/Card.tsx:152`; Playwright assertions verify visible text at `serve/cockpit/web/e2e/card-density-1565.spec.ts:328`, `serve/cockpit/web/e2e/card-density-1565.spec.ts:340`, `serve/cockpit/web/e2e/card-density-1565.spec.ts:352`, and `serve/cockpit/web/e2e/card-density-1565.spec.ts:364`.
  - AC-3: Satisfied. The violation catalogue is recorded in the spec header at `serve/cockpit/web/e2e/card-density-1565.spec.ts:1` and the baseline tests remain at `serve/cockpit/web/e2e/card-density-1565.spec.ts:373`.
  - AC-4: Satisfied. The component derives recency from `task.updated` at `serve/cockpit/web/src/components/Card.tsx:51` and renders `card-updated` at `serve/cockpit/web/src/components/Card.tsx:113`; E2E integration assertions exist at `serve/cockpit/web/e2e/card-density-1565.spec.ts:407`, `serve/cockpit/web/e2e/card-density-1565.spec.ts:416`, `serve/cockpit/web/e2e/card-density-1565.spec.ts:429`, and `serve/cockpit/web/e2e/card-density-1565.spec.ts:438`; deterministic unit proof now exercises minutes/hours/days/fallback plus stale-vs-recent output at `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:157`, `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:166`, `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:175`, `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:184`, and `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:193`.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The task-local E2E suite still does not assert card title rendering, even though AC-1 explicitly requires E2E fixtures for title. Adjacent durable title tests do not satisfy that task-local E2E requirement on a second review cycle. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:32`; `serve/cockpit/web/e2e/card-density-1565.spec.ts:243`; `serve/cockpit/web/e2e/card-density-1565.spec.ts:18`; `serve/cockpit/web/e2e/card-density-1565.spec.ts:380`; `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx:297`; `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx:305` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine or confirm AC-1 proof shape for title rendering: either require an explicit task-local Playwright title assertion in the 1565 E2E suite or explicitly accept adjacent durable title proof, then reissue the task with that expectation made unambiguous. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md`, `serve/cockpit/web/e2e/card-density-1565.spec.ts`, `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` | Finding #1 |

## Observations
- Independent scoped rerun was otherwise clean: 77 passed / 0 failed; Vitest, Playwright, ESLint, and Stylelint all exited 0.
- The retry does resolve the prior AC-4 false-green issue: `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:193` now proves stale and recent timestamps cannot collapse to the same constant label.
- The scoped quality-runner report also emitted `Card.tsx` coverage `50`, but the report did not specify coverage dimension or missing-line detail. I therefore did not use that metric as a separate blocking finding.


## Architecture Refinement — AC-1 Title Proof
Reviewer finding accepted: AC-1 explicitly requires E2E rendering fixtures for card `title`, so adjacent durable unit/component title proof is not enough for this task after the second review cycle.

Refined AC-1 proof requirement: the task-local Playwright suite `serve/cockpit/web/e2e/card-density-1565.spec.ts` must include an explicit assertion that at least one rendered task card exposes its title in the card metadata/density fixture, preferably through `[data-testid="card-title"]` or an equivalent visible locator scoped to the card. Adjacent `KanbanBoard` title tests may remain supporting evidence, but they do not satisfy AC-1 by themselves.

Architect disposition: require the task-local Playwright title assertion; re-dispatch to test-writer/builder as needed.
2026-05-15T00:01:29+00:00
Architect refinement complete after review rejection. Accepted reviewer finding: AC-1 requires task-local Playwright title proof. Added explicit requirement that `serve/cockpit/web/e2e/card-density-1565.spec.ts` assert visible card title within the card-density fixture; adjacent durable title tests are supporting evidence only. Re-dispatching to todo for test-writer/builder follow-up.
2026-05-15T00:17:12+00:00
## Test-Writer Notes

**Retry cycle 3 — path-guard-constrained, advance to in-progress for builder E2E completion**

**Modified file:** `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`

**New test added (1):**

| Test | Class | Category | Addresses |
|---|---|---|---|
| `card renders visible title element with correct task title text (AC-1 title fixture)` | TestFromAC_CardDensityElements | happy | AC-1 title fixture + architect refinement |

**Total new tests: 1 — PASSES against current impl (74c50eb5 / 624cd46c)**

**Path guard constraint:**
Test-writer mode blocks writes to `serve/cockpit/web/e2e/` — only `tests/`, `__tests__/`, and `.owlbear/scratch/` are permitted write targets. This prevented direct modification of `e2e/card-density-1565.spec.ts` in all three retry cycles.

**Architect disposition (second review cycle refinement):** "require the task-local Playwright title assertion; re-dispatch to test-writer/builder as needed." The Vitest unit test in `Card.signal.test.tsx` provides deterministic AC-1 title proof. The E2E companion assertion is delegated to the builder per architect authorization.

**AC coverage (this retry):**
| AC | This retry | Status |
|---|---|---|
| AC-1 (title) | Vitest unit proof: `card-title` visible, text equals task title | UNIT ✓ / E2E — see builder note |
| AC-2 | Satisfied (previous retries) | ✓ |
| AC-3 | Satisfied (previous retries) | ✓ |
| AC-4 | Satisfied (previous retries, deterministic branch tests) | ✓ |

**Quality-runner evidence:** 25 passed / 0 failed on `Card.signal.test.tsx`; ESLint clean.
**Commit:** 624cd46c — `test: add AC-1 title unit proof for card-density retry (#1565, test-writer)`

---

## Builder Instructions — E2E Title Assertion (Required)

The architect refinement (see above) requires a task-local **Playwright** title assertion in `serve/cockpit/web/e2e/card-density-1565.spec.ts`. The test-writer path guard prevented adding it. **Builder must add this assertion** to satisfy AC-1.

**Target file:** `serve/cockpit/web/e2e/card-density-1565.spec.ts`

**Target describe block:** `AC-1 | Card rendering fixtures — id, priority, tags, state cues`

**Insert after the `card displays task id` test, before the `card displays priority tag` test:**

```typescript
  test('card displays task title as a visible element with correct text', async ({ page }) => {
    await loadBoard(page)
    // AC-1 explicitly requires E2E fixtures for title rendering.
    // Architect refinement (second review cycle): task-local Playwright title
    // assertion required. Card.tsx: <span data-testid="card-title">{task.title}</span>
    const card = page.locator('[data-testid="task-card"][data-id="1"]')
    await card.waitFor({ state: 'visible', timeout: 6_000 })
    const titleEl = card.locator('[data-testid="card-title"]')
    await expect(titleEl).toBeVisible({ timeout: 2_000 })
    const text = await titleEl.textContent()
    expect(text?.trim()).toBe('Ready task')  // TASK_READY.title
  })
```

This test will PASS against current impl (no source changes needed). No other implementation changes required for this task.
2026-05-15T00:39:19+00:00
## Builder Notes
- No code changes were made.
- I reviewed the current task body, including Architect refinement and latest Test-Writer retry notes.
- Remaining gap is explicitly test-surface only: AC-1 now requires a task-local Playwright title assertion in `serve/cockpit/web/e2e/card-density-1565.spec.ts`.
- Builder-mode guardrail blocks writing tests (`Builder never writes tests` / `Never modify TestFromAC_* classes`), so this dispatch is role-incompatible as written.
- Implementation status remains unchanged: existing UI code for card density cues/recency is already in place from prior builder commit evidence.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add the missing AC-1 task-local Playwright title assertion (visible `card-title` proof) in the card-density E2E suite, then rerun scoped proof and re-advance. | `serve/cockpit/web/e2e/card-density-1565.spec.ts` | Architect refinement in task body requiring task-local Playwright title proof; latest Test-Writer Notes delegated this exact insertion |
| 2 | architect | If test-writer path-guard constraints still prevent edits under `e2e/`, update dispatch/routing so AC-1 title proof ownership aligns with role/tool boundaries (either relax path guard for this task or explicitly reassign). | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md` | Task body states builder should add E2E assertion, which conflicts with builder-mode no-test rule |

- Verification commands were not run in this cycle because no implementation surface was edited and the task is rejected on ownership/routing mismatch, not on runtime behavior.
2026-05-15T01:09:30+00:00
## Test-Writer Notes

**Retry cycle 4 — structural path guard deadlock → reject to backlog**

**Finding:** The VS Code test-writer path guard enforces hard write restrictions: only `tests/`, `__tests__/`, and `.owlbear/scratch/` are writable. `serve/cockpit/web/e2e/card-density-1565.spec.ts` is outside these bounds.

**What was attempted:** Added the architect-required AC-1 title assertion to the E2E spec per the exact insertion spec from the previous test-writer retry. Tool returned: `Tool execution denied: test-writer path guard: write target '...' is outside the allowed directories.`

**Pattern:** This blocker has occurred in every retry cycle since the original creation:
- Cycle 1 (original): Created `e2e/card-density-1565.spec.ts` — succeeded (creation vs. edit distinction)
- Cycles 2–4: Editing the same file — blocked each time

**Builder route attempted:** Builder dispatched in cycle 3 — returned without change (builder-mode no-test rule blocks E2E assertion insertion).

**Structural assessment:** No test-writer retry can resolve this. The architect's AC-1 refinement requires editing a file the path guard blocks. Builder cannot write tests.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Choose resolution for AC-1 E2E title assertion deadlock: (a) accept existing unit proof in `Card.signal.test.tsx` as sufficient for AC-1 title; (b) relax path guard scope so test-writer can edit existing e2e/ specs; or (c) create a user-action task for the single E2E assertion insertion. Without a resolution, this task will loop indefinitely. | `serve/cockpit/web/e2e/card-density-1565.spec.ts`, `serve/cockpit/web/src/__tests__/Card.signal.test.tsx` | Path guard enforcement — cycles 2, 3, 4 |

**Current state of evidence (all other ACs satisfied):**
- AC-1 (non-title): 8 E2E tests cover id, priority, tags, overflow, 4 state cues — pass against current impl
- AC-1 (title): Vitest unit proof in `Card.signal.test.tsx` (`card renders visible title element with correct task title text`) — passes; E2E equivalent blocked by path guard
- AC-2: 4 E2E accessibility assertions — pass
- AC-3: Violation catalogue + 2 baseline tests — documented
- AC-4: 4 E2E recency tests + 5 deterministic Vitest branch tests — pass; stale-vs-recent guard confirmed
2026-05-15T01:38:06+00:00

## Architecture Review (Cycle 2 — Deadlock Resolution)

### Context
Task returned to backlog after 4 retry cycles. Structural deadlock: test-writer path guard blocks edits to `serve/cockpit/web/e2e/`, builder mode blocks writing tests. Neither agent can add the single missing E2E title assertion in `card-density-1565.spec.ts`.

### AC-1 Refinement
**Previous requirement:** Task-local Playwright E2E title assertion required.
**Refined requirement:** AC-1 title proof accepted via Vitest unit test (`Card.signal.test.tsx:152-164`) which asserts `[data-testid="card-title"]` presence and exact text content match. E2E companion assertion is desirable but not blocking — the unit test provides stronger deterministic proof than a Playwright visibility check for a simple `<span>` render.

**Rationale:**
- Unit test proves exact DOM element presence + text equality — stronger than E2E `toBeVisible()` + `textContent()`
- Title rendering is a trivial `<span>` — no browser interaction, animation, or layout dependency that only E2E would catch
- 8 E2E tests already cover all *complex* AC-1 elements (state cues, tags, overflow, id, priority)
- Adjacent durable title proof exists in `KanbanBoard.test.tsx:297,305`
- 4 cycles of retry demonstrate structural impossibility, not a quality gap
- KISS: infrastructure changes or user-action tasks for one assertion line is over-engineering

### AC Assessment (Post-Refinement)
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 | PASS — title proof accepted via unit test; 8 E2E tests cover remaining density elements | Refined: unit proof sufficient for title |
| AC-2 | PASS — 4 E2E accessibility assertions verified in prior reviews | No change |
| AC-3 | PASS — violation catalogue + 2 baseline tests | No change |
| AC-4 | PASS — 4 E2E + 5 Vitest deterministic branch tests; stale-vs-recent guard confirmed | No change |

### Evidence State
- Implementation: complete (commit 74c50eb5)
- E2E: 18 tests pass (commit fcfa1f42)
- Unit coverage: 25 tests pass including density/recency/cue/title (commits e48fd533, 624cd46c)
- Lint: ESLint + Stylelint clean
- All 4 ACs functionally covered

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (no new tests needed — existing proof covers refined AC)

### Verdict: APPROVE (REFINE path — AC-1 proof shape relaxed to resolve tooling deadlock)
### Action: Advance to todo; existing implementation and test evidence should flow through remaining pipeline without new work.
2026-05-15T01:38:11+00:00
Architecture review cycle 2: resolved structural tooling deadlock (test-writer path guard blocks e2e/ edits, builder blocks test writes). Accepted AC-1 title proof via Vitest unit test — stronger deterministic proof than E2E for a trivial span render. All 4 ACs now covered. Existing implementation and 43 passing tests should flow through remaining pipeline without new work.
2026-05-15T02:21:04+00:00
## Test-Writer Notes

**Retry cycle 5 — direct-to-review pass-through (Step 1b.1)**

**No new tests written this cycle.**

**Architect cycle 2 resolution (2026-05-15T01:38:11):**
- AC-1 title proof accepted via Vitest unit test `Card.signal.test.tsx:152-164` (`card renders visible title element with correct task title text`)
- Unit proof asserts `[data-testid="card-title"]` presence + exact text equality — stronger than E2E `toBeVisible()` for a trivial `<span>` render
- Architect explicitly: "no new tests needed — existing proof covers refined AC"

**Step 1b.1 qualification:**
- Reviewer Required Follow-up (AC-1 title proof) resolved by architect refinement — no implementation fixes needed
- No new tests: vacuously satisfies "all new tests pass" condition (arch confirmed no new tests required)
- All 43 existing tests (25 Vitest + 18 Playwright) pass against current impl (74c50eb5)
- Lint clean (ESLint + Stylelint exit 0)
- Builder has no work — implementation complete, tests complete

**AC coverage (final):**
| AC | Tests | Status |
|---|---|---|
| AC-1 (id, priority, tags, overflow, cues) | 8 E2E + 3 Vitest unit | ✓ |
| AC-1 (title) | Vitest unit — `card-title` visible + exact text | ✓ (arch-accepted) |
| AC-2 (accessibility, no color-only) | 4 E2E Playwright assertions | ✓ |
| AC-3 (baseline failing evidence) | Violation catalogue + 2 baseline tests | ✓ |
| AC-4 (recency metadata) | 4 E2E + 5 Vitest deterministic branch tests | ✓ |
2026-05-15T03:00:28+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1565 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: current proof surface is internally consistent. The task body records the RED baseline (0 passed / 18 failed), the implementation surface, and the retry-cycle unit proof additions. Independent reviewer verification was justified because prior builder notes left coverage ambiguous; the fresh scoped quality-runner rerun is clean: 43 passed / 0 failed, lint clean, no runtime errors.
- AC mapping:
  - AC-1: Card.tsx renders id, priority, updated chip, title, tag preview, overflow indicator, and state cues (`serve/cockpit/web/src/components/Card.tsx`: tag derivation at lines 49-50; render block at lines 82-158). Task-local Playwright proof covers id/priority/tags/overflow/cues (`serve/cockpit/web/e2e/card-density-1565.spec.ts`: 243-316). Title proof is explicitly accepted by the architect cycle-2 refinement and is covered by the unit assertion in `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`: 139-152.
  - AC-2: Non-color state cues are rendered as visible text in Card.tsx (`Blocked`, `Claimed`, `Dependencies blocked`, `Decision pending`) and verified by Playwright locator/text assertions in `serve/cockpit/web/e2e/card-density-1565.spec.ts`: 321-369.
  - AC-3: Baseline title-only evidence remains recorded in the E2E violation catalogue and baseline tests in `serve/cockpit/web/e2e/card-density-1565.spec.ts`: 1-39 and 373-394, paired with the original RED quality-runner result already captured in task history.
  - AC-4: Recency is derived from `task.updated` in `serve/cockpit/web/src/components/Card.tsx`: 8-25 and rendered at 104-109. Playwright covers element presence/accessibility in `serve/cockpit/web/e2e/card-density-1565.spec.ts`: 399-443, and deterministic unit proof in `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`: 160-218 covers minutes/hours/days/fallback plus stale-vs-recent divergence.
- Proof sufficiency: sufficient for PASS after the architect's title-proof refinement. The fresh scoped quality-runner rerun reports 43 passed / 0 failed, vitest/playwright/eslint/stylelint all exit 0, and no errors.
- Safety & security: no authentication, storage, injection, or secret-handling surface changed in this task.
- Blocking findings: none.

## Observations
- The quality-runner scoped coverage figure for `src/components/Card.tsx` is 45.94% statement coverage. I did not treat that as blocking because the uncovered regions map to keyboard/context-menu and drag handlers outside the card-density AC surface, and adjacent durable proof exists in `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`: 119-177 and 192-277, `serve/cockpit/web/src/__tests__/CardDrag_1546.test.tsx`: 53-130, and `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`: 366-374.
- Residual hardening opportunity only: current tag-preview assertions prove element presence and overflow count, but they do not pin exact preview text or `aria-label` contents. Given AC-1 as written and the architect's recorded refinement path, I did not treat that as a blocker in this cycle.
2026-05-15T03:25:29+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | Updated | `serve/cockpit/README.md` accessibility section lacked #1565 milestone; added bullet documenting card density cues and AC-2 accessibility proof (text cues, not color-only). Layer 1: grep confirms #1565 at line 64 and `card-density-1565.spec.ts` at line 68. Layer 2: editorial read confirms no contradictions or stale content; new bullet is coherent with existing accessibility milestone list. |
| 2 | External attribution | No | N/A | No external sources cited; implementation uses standard React/CSS/Playwright tooling. |
| 3 | Research doc | Yes | N/A | Research doc `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` referenced in task body Context section — linkage already present. |
| 4 | Deletion detection | No | N/A | No files deleted; Card.tsx and Card.css modified, new test file created, existing test file extended. No orphaned references. |

### Verification Layers
- Layer 1 — grep confirmed `#1565`, `card-density-1565.spec.ts`, and `State cues` present in `serve/cockpit/README.md` (lines 64–68); no removed symbols found in README.
- Layer 2 — full editorial read: README coherent, accessibility section now reflects the #1565 milestone in chronological order (before #1566), no contradictions.

### Files Updated
- `serve/cockpit/README.md` — added accessibility milestone bullet for #1565 (commit 41342d46)

### Scratch Files Cleaned
- None found for task #1565
2026-05-15T03:56:11+00:00
## Audit
### Regression Detection
- quality-runner mode full: 6353+ passed, 20 failed (2 vitest, 18 python/other)
- quality-runner scoped verification on `KanbanBoard.performance-700.test.tsx`: 8 passed, **2 failed** — `expected 5801 to be less than 5000` (both uniform and skewed distributions)
- Root cause: Card.tsx now renders ~8 DOM elements per card (id chip, priority chip, updated chip, title, card-main, header-row, cues-row, card root) vs ~2-3 pre-#1565. For 700 tasks: 700 × 8 + structure = ~5,801, exceeding the 5,000-node budget.
- `test_kanban_board_split.py::test_card_tsx_has_priority_colors` — confirmed pre-existing (broken by #1544's PRIORITY_COLORS removal), NOT a #1565 regression.
- Remaining 18 failures are in unrelated domains (ideation, server, python version, cockpit models, etc.) — not #1565-caused.
- regression verdict: **FAIL** — 1 confirmed cross-task regression (DOM budget test)

### Intent Verification
- scope alignment: PASS — changed files are Card.tsx, Card.css, card-density-1565.spec.ts, Card.signal.test.tsx, cockpit/README.md — all cockpit frontend domain
- purpose match: PASS — card information density cues implemented as stated in AC
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC-1 ambiguity about "E2E rendering fixtures" for title caused 4 retry cycles before architect resolved via cycle-2 refinement (unit proof accepted). Additionally, architect did not consider the pre-existing 700-task DOM budget test when specifying card density additions — an edge case that resulted in the regression. Score 3: notable gaps requiring significant improvisation across multiple pipeline cycles.

### Commit Integrity
- upstream commit presence: PASS — 5 commits verified via `git log --oneline`:
  - `fcfa1f42` test-writer (RED)
  - `74c50eb5` builder (GREEN)
  - `e48fd533` test-writer retry
  - `624cd46c` test-writer retry 2
  - `41342d46` doc-writer (README)
- kanban commit packaging: PASS (will commit after end_work)

### Deduction Breakdown
| Criterion | Deduction | Evidence |
|-----------|-----------|----------|
| Regression failure (DOM budget: 5801 > 5000) | -.10 | `KanbanBoard.performance-700.test.tsx` fails on both distributions |
| AC quality score ≤ 3 | -.03 | 4 retry cycles from AC-1 ambiguity + missed DOM budget edge case |

### Confidence: 0.87
### Action: reject-to-backlog
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Recalibrate the 700-task DOM budget threshold in the performance test to accommodate new card density elements (~8 elements/card), OR optimize Card.tsx DOM structure (e.g., conditionally render cues-row only when cues exist) to stay within 5000. | `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx`, `serve/cockpit/web/src/components/Card.tsx` | DOM count 5801 > 5000 on both uniform and skewed distributions |