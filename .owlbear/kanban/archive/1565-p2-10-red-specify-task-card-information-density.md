---
id: 1565
title: 'P2-10 RED: Specify task card information density'
status: archived
priority: medium
created: 2026-05-14T18:26:23.493454+00:00
updated: 2026-05-15T06:01:46.760239+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - cards
  - visual-remediation
  - type:build
parent: 1559
depends_on:
  - 1560
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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


## Architecture Correction — Audit Regression
Auditor finding accepted: #1565 introduced a confirmed cross-task performance regression in the 700-task DOM budget (`KanbanBoard.performance-700.test.tsx` measured approximately 5801 DOM nodes, above the existing 5000 budget).

Correction decision: route to builder with an optimize-first requirement. Do **not** treat a simple threshold increase as the default fix.

Required builder follow-up:
- First reduce avoidable card DOM: conditionally render empty cue containers only when cues exist, remove or merge purely structural wrappers where this does not weaken accessibility, and preserve all required visible card signals from AC-1 through AC-4.
- Re-run the scoped 700-task performance proof after optimization.
- If the DOM count still exceeds 5000 after minimal structural optimization, a threshold recalibration may be proposed only with measured evidence: before/after DOM counts, rationale for the new budget, and confirmation that card-density ACs and visual readability remain intact.

Architect disposition: builder correction required for the regression; no new test-writer work is needed unless the builder changes the public proof contract.
2026-05-15T04:02:42+00:00
Claim released after architecture correction override. #1565 is now routed as builder work for the accepted DOM-budget regression: optimize Card DOM first, then recalibrate threshold only with measured evidence if necessary.
2026-05-15T04:08:44+00:00

## Architecture Review (Cycle 3 — DOM Budget Regression Fix)

### Context
Auditor rejected to backlog: Card.tsx now renders ~8 DOM elements per card (up from ~3 pre-density), causing `KanbanBoard.performance-700.test.tsx` to fail (5801 > 5000 threshold) for both uniform and skewed distributions. The regression is a direct consequence of the card density implementation (commit 74c50eb5). All 4 original ACs remain satisfied.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | AC-5 scoped to one regression: DOM budget for card density |
| Interface clarity | PASS | Target file, optimization requirement, and verification method all named |
| Dependency correctness | PASS | #1560 archived; no new deps needed |
| Module layering | N/A | Card.tsx DOM structure change, no layering impact |
| TDD compliance | PASS | Durable test already exists; fix targets the failing assertion |
| KISS/YAGNI | PASS | Conditional cues-row is minimal optimization; threshold recalibration is necessary consequence of intentional density increase |
| Premise challenge | PASS | The 5000 threshold was calibrated for ~2500-node title-only cards (task #959 research). Card density intentionally tripled per-card DOM elements. Threshold update is feature-contract evolution, not contract weakening |
| Pattern consistency | PASS | Conditional rendering matches existing tags-row pattern in Card.tsx (line 122-130) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signal C2 present |
| DR verification | N/A | Not research-tagged |

### AC Assessment (Post-Refinement)
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 | PASS — satisfied in prior cycles (8 E2E + unit title proof) | No change |
| AC-2 | PASS — satisfied in prior cycles (4 E2E accessibility assertions) | No change |
| AC-3 | PASS — satisfied in prior cycles (violation catalogue + baseline tests) | No change |
| AC-4 | PASS — satisfied in prior cycles (4 E2E + 5 Vitest branch tests) | No change |
| AC-5 (NEW) | PASS — verifiable: quality-runner scoped run on performance test file | Added |

### AC-5 Text
AC-5: Builder resolves the 700-task DOM budget regression: (a) conditionally render `card-cues-row` in `Card.tsx` only when at least one state cue (`blocked`, `claimed`, `dep_status === 'blocked'`, or `signal === 'dr-pending'`) is active, following the existing conditional pattern used for `card-tags-row` at Card.tsx lines 122-130; (b) rerun the performance tests after optimization and recalibrate the DOM count threshold in `KanbanBoard.performance-700.test.tsx` to reflect the actual post-optimization node count with reasonable headroom — document the before/after counts in builder notes; verify by quality-runner scoped run confirming both "total DOM node count" assertions pass for uniform and skewed distributions.

### Architecture Notes
- Card.tsx conditional tags-row pattern (lines 122-130) is the exact template for cues-row optimization
- The cues-row at line 136 is unconditionally rendered even when all 4 conditions (`blocked`, `claimed`, `dep_status === 'blocked'`, `signal === 'dr-pending'`) are false → empty div for ~75% of fixture cards
- Optimization alone reduces base to ~5275 nodes (still above 5000), so threshold recalibration IS required
- The threshold change is in a durable performance test (`KanbanBoard.performance-700.test.tsx`), not a `TestFromAC_*` class — builder may modify it
- AC-5 is builder-only to avoid the multi-agent routing deadlock that caused 4 retry cycles on AC-1

### Challenge Results
- Challenger: reconsider (confidence 0.43)
- Findings: (1) contract weakening concern about raising threshold, (2) AC-5 routing ambiguity mixing builder/test-writer, (3) sparse fixture gap
- Architect response:
  - Finding 1: partially accepted. Threshold update is feature-contract evolution (cards went from ~3 to ~7-8 elements by design), not weakening. But accepted optimize-first ordering — AC-5 requires optimization before recalibration, with before/after counts documented.
  - Finding 2: accepted. Rewrote AC-5 as builder-only scope. The threshold is in a durable test (not TestFromAC_), and the change is a regression fix from builder's own implementation.
  - Finding 3: noted, out-of-scope. The 700-task fixture (from #959) omits tags/deps/DR. Enriching it to stress-test full density is a legitimate improvement but belongs in a separate task, not this regression fix.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (pass-through — no new test-writer work; AC-5 is builder-scoped)

### Design Diverge
- Trigger: skipped — single valid approach (conditional render + threshold recalibration)

### Verdict: APPROVE (REFINE path — added AC-5 for DOM budget regression)
### Action Taken: Added AC-5 for builder to resolve DOM budget regression; advancing to todo. Existing implementation and test evidence for ACs 1-4 should flow through remaining pipeline; only AC-5 requires new builder work.
2026-05-15T04:08:56+00:00
Architecture review cycle 3: added AC-5 for DOM budget regression. Builder must (a) conditionally render card-cues-row following existing tags-row pattern, (b) recalibrate threshold based on post-optimization node count. Challenger reconsider at 0.43 — accepted routing-ambiguity fix (builder-only AC), rebutted contract-weakening concern (threshold update is feature-contract evolution from ~3 to ~8 elements/card). ACs 1-4 satisfied from prior cycles; only AC-5 requires new builder work.
2026-05-15T04:30:27+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1565 -> backlog | AC-5 remains unimplemented in the current workspace, and the required scoped DOM-budget proof still fails at `5801 > 5000`.
- Builder evidence review: the current review packet is insufficient for AC-5. The latest recorded builder note says no code changes were made and no verification commands were run (`.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:301`, `:313`). AC-5 was added later as builder-only follow-up work requiring conditional `card-cues-row` rendering, a recalibrated DOM-budget threshold, before/after DOM counts in builder notes, and a scoped quality-runner pass (`.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:536`, `:563`, `:565`). No later builder proof is present in the task body.
- AC mapping summary:
  - AC-1 through AC-4: not the blocker in this cycle. The current `Card.tsx` surface still renders the previously accepted density and accessibility elements, and the late-cycle regression work did not change those contracts.
  - AC-5: FAIL. `Card.tsx` still uses an unconditional `card-cues-row` at `serve/cockpit/web/src/components/Card.tsx:136` instead of following the conditional `card-tags-row` pattern at `serve/cockpit/web/src/components/Card.tsx:124`. The durable DOM-budget test still enforces the unrecalibrated `<5000` threshold at `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:208` and `:266`.
- Independent verification: scoped `quality-runner` rerun on `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx` plus scoped lint for `Card.tsx` / the performance test. Result: 8 passed / 2 failed, lint clean. Both failing tests are the DOM-budget assertions with the exact failure `expected 5801 to be less than 5000`.
- Safety & security: no auth, storage, injection, or secret-handling surface is involved in this regression.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-5 | The builder-only DOM-budget remediation has not been applied. The current component still renders the cues container unconditionally, so the optimization explicitly required by AC-5(a) is absent. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:536`; `serve/cockpit/web/src/components/Card.tsx:124`; `serve/cockpit/web/src/components/Card.tsx:136` | backlog |
| 2 | AC-5 | The required post-optimization threshold recalibration and proof packet are also absent. The test still checks `<5000`, and the fresh scoped rerun still fails both DOM-budget assertions at `5801`. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:536`; `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:208`; `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:266`; scoped quality-runner rerun for #1565 | backlog |
| 3 | AC-5 / Evidence | The task was returned to review without the builder proof AC-5 requires. The latest builder note predates AC-5 and explicitly records no code change and no verification, so the current review packet is incomplete even before considering the failing rerun. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:301`; `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:313`; `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:563`; `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:565` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reissue the AC-5 builder handoff as the next cycle’s sole blocker: require conditional `card-cues-row` rendering, rerun the 700-task performance test, and keep the task out of review until a post-AC-5 builder note includes before/after DOM counts plus scoped quality-runner output. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md`, `serve/cockpit/web/src/components/Card.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx` | Findings #1-#3 |
| 2 | architect | Tighten the AC-5 recalibration acceptance text so the next builder cycle has an objective threshold target, not just “reasonable headroom,” while preserving the optimize-first requirement already recorded in cycle 3. | `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md`, `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx` | Finding #2 |

## Observations
- The current failure is isolated to the late-cycle DOM-budget remediation. I did not find a new defect in the original card-density cue/accessibility surface from AC-1 through AC-4.
- The 700-task fixture remains sparse (no tag/dependency/DR load), so it is a valid regression gate for the current durable test but not a full-density calibration model. If the threshold is recalibrated, the builder note should explain why the chosen headroom still covers the intended card surface.
2026-05-15T04:41:00+00:00
## Architecture Review (Cycle 4 — AC-5 Threshold Tightening)

### Context
Task returned from reviewer finding #2: AC-5's "reasonable headroom" language is not objectively verifiable. Additionally, no builder has yet executed AC-5 (previous builder dispatch predated AC-5's creation). This cycle tightens AC-5 per reviewer findings and re-advances.

### AC-5 Refinement (replaces prior AC-5 text)
AC-5: Builder resolves the 700-task DOM budget regression: (a) conditionally render `card-cues-row` in `Card.tsx` only when at least one state cue (`blocked`, `claimed`, `dep_status === 'blocked'`, or `signal === 'dr-pending'`) is active, following the existing conditional pattern used for `card-tags-row` at Card.tsx lines 122-130; (b) verify optimization reduced DOM nodes — post-optimization count for both scenarios must be strictly less than 5801 (the current measured count); (c) set both threshold assertions in `KanbanBoard.performance-700.test.tsx` to `ceil(max(uniform_post_count, skewed_post_count) × 1.2 / 100) × 100` — i.e., 120% of the higher post-optimization count, rounded up to the nearest 100; (d) document in builder notes: before counts (both scenarios, expected 5801), after counts (both scenarios), derived threshold, and the formula calculation; verify by quality-runner scoped run on `KanbanBoard.performance-700.test.tsx` confirming both "total DOM node count" assertions pass for uniform and skewed distributions.

### Evaluation (Cycle 4 — incremental)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | AC-5 is one concern: DOM budget regression fix |
| Interface clarity | PASS | Before/after counts, formula, verification method all named |
| Dependency correctness | PASS | No new dependencies |
| Module layering | N/A | Card.tsx DOM structure, no import changes |
| TDD compliance | PASS | Durable performance test already exists and currently fails |
| KISS/YAGNI | PASS | Conditional render + threshold recalibration; minimal change |
| Premise challenge | PASS | Regression is confirmed (5801 > 5000); optimization target proven viable (tags-row pattern) |
| Pattern consistency | PASS | Follows existing conditional tags-row at Card.tsx:122-130 |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signal C2 (test outcome expectations) |
| DR verification | N/A | Not research-tagged |

### Challenge Results
- Challenger: block (confidence 0.34)
- Findings: (1) optimization-proof gap — threshold alone could pass without optimization, (2) scenario scope ambiguity — which count governs, (3) builder-actionability — refined AC not yet in task body, (4) calibration-model mismatch — fixture is sparse
- Architect response: accepted findings 1-3 and incorporated into refined AC-5 (added strict < 5801 proof, max(uniform,skewed) formula, editing task body now). Rebutted finding 4 — sparse fixture is the existing durable test that already caught this regression; enriching it is a separate concern (noted in cycle 3 observations)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (pass-through — AC-5 is builder-scoped; existing durable test is the proof target)

### Design Diverge
- Trigger: skipped — single valid approach (conditional render + threshold recalibration)

### Verdict: APPROVE (REFINE path — AC-5 threshold formula tightened per reviewer finding)
### Action Taken: Replaced "reasonable headroom" with objective threshold formula (120% of max post-optimization count, rounded to 100), added strict optimization-proof requirement (post < 5801), and specified which scenario measurement governs (max of both). Advancing to todo.
2026-05-15T04:41:07+00:00
Architecture review cycle 4: tightened AC-5 per reviewer finding. Replaced "reasonable headroom" with objective threshold formula: 120% of max(uniform, skewed) post-optimization count rounded to nearest 100. Added strict optimization-proof gate (post < 5801). Challenger accepted 3/4 findings — incorporated optimization-proof, scenario-scope, and builder-actionability fixes; rebutted calibration-model concern (sparse fixture is the existing regression gate). ACs 1-4 remain satisfied from prior cycles; only AC-5 requires builder work.
2026-05-15T04:47:38+00:00
## Test-Writer Notes

**Retry cycle 6 — pass-through (architect cycle 4 disposition)**

**No new tests written this cycle.**

**Architect cycle 4 disposition (2026-05-15T04:41:07):**
- ACs 1–4: Satisfied from prior cycles (18 Playwright E2E + 25 Vitest unit tests, all passing)
- AC-5: **Builder-only scope.** Requires (a) conditional `card-cues-row` rendering in `Card.tsx` following the existing `card-tags-row` pattern; (b) post-optimization threshold recalibration in `KanbanBoard.performance-700.test.tsx` using formula `ceil(max(uniform, skewed) × 1.2 / 100) × 100`; (c) strict proof that post-count < 5801; (d) before/after DOM counts documented in builder notes.
- Architect explicitly: "Test-writer: PROCEED (pass-through — AC-5 is builder-scoped; existing durable test is the proof target)"

**Pass-through qualification:**
- Latest reviewer Required Follow-up (2026-05-15T04:41:00) targeted architect only (tighten AC-5 language) — architect resolved it
- No test-writer gap identified in any agent's required follow-up for this cycle
- Existing durable test `KanbanBoard.performance-700.test.tsx` is the proof vehicle for AC-5; builder modifies the threshold, not the test-writer
- All 43 existing tests (25 Vitest + 18 Playwright) remain passing
2026-05-15T05:03:35+00:00
## Builder Notes
- Implementation:
  - `serve/cockpit/web/src/components/Card.tsx`
  - `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx`
- Approach:
  - Applied AC-5(a) optimize-first change by conditionally rendering `card-cues-row` only when at least one cue is active (`blocked`, `claimed`, `dep_status === "blocked"`, or `signal === "dr-pending"`).
  - Re-ran scoped performance proof, measured post-optimization DOM counts, then applied AC-5(c) threshold recalibration formula in the durable performance test.

- RED verification (quality-runner, before code changes):
  - Test file: `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx`
  - Passed: 8
  - Failed: 2
  - Failures:
    - uniform distribution DOM budget: `expected 5801 to be less than 5000`
    - skewed distribution DOM budget: `expected 5801 to be less than 5000`
  - Lint: clean

- Post-optimization measurement (quality-runner, after Card.tsx change, before threshold update):
  - Passed: 8
  - Failed: 2
  - Measured node counts:
    - uniform: 5253
    - skewed: 5253
  - AC-5(b) proof satisfied: both post counts are strictly less than 5801.

- Threshold derivation (AC-5(c)):
  - `max(uniform_post_count, skewed_post_count) = max(5253, 5253) = 5253`
  - `ceil(5253 × 1.2 / 100) × 100`
  - `= ceil(63.036) × 100`
  - `= 64 × 100`
  - `= 6400`
  - Updated both DOM-budget assertions to `< 6400` via `DOM_NODE_BUDGET` constant.

- Final GREEN verification (quality-runner):
  - Test files:
    - `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx`
    - `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`
  - Passed: 35
  - Failed: 0
  - Lint: clean
  - Coverage: not emitted by quality-runner for this scoped frontend run

- Fixes applied:
  - Removed empty cues-row DOM nodes from cards with no active cues.
  - Recalibrated 700-task DOM threshold to formula-derived 6400 after measured optimization.

- Commit:
  - `09b8b6d2`
  - `fix: resolve card DOM budget regression (#1565, builder)`
2026-05-15T05:35:10+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1565 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: the current packet satisfies refined AC-5. The task body documents pre-optimization 5801 failures, post-optimization 5253/5253 counts, the formula-derived 6400 threshold, and final scoped quality-runner proof in `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:654-700`.
- Independent verification: scoped quality-runner rerun after the latest builder cycle passed 53/53 relevant tests (18 Playwright in `serve/cockpit/web/e2e/card-density-1565.spec.ts`, 25 Vitest in `serve/cockpit/web/src/__tests__/Card.signal.test.tsx`, 10 Vitest in `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx`), with ESLint and Stylelint clean. Coverage was emitted for `serve/cockpit/web/src/components/Card.tsx` at 47.36% statements/lines and 66.66% branches; uncovered lines are `serve/cockpit/web/src/components/Card.tsx:55-77` and `serve/cockpit/web/src/components/Card.tsx:94-105`, which are keyboard/context-menu and drag handlers outside the card-density AC surface.
- AC mapping:
  - AC-1: `serve/cockpit/web/src/components/Card.tsx:115-153` renders id, priority, updated, title, tag preview/overflow, and cue elements. Task-local Playwright proof remains at `serve/cockpit/web/e2e/card-density-1565.spec.ts:244-316`, and the architect-accepted title proof remains at `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:141-152`.
  - AC-2: visible non-color cue text is rendered at `serve/cockpit/web/src/components/Card.tsx:139-153` and asserted at `serve/cockpit/web/e2e/card-density-1565.spec.ts:322-369`.
  - AC-3: baseline title-only evidence remains recorded in `serve/cockpit/web/e2e/card-density-1565.spec.ts:1-39` and `serve/cockpit/web/e2e/card-density-1565.spec.ts:378-394`.
  - AC-4: recency formatting is derived in `serve/cockpit/web/src/components/Card.tsx:7-24` and rendered at `serve/cockpit/web/src/components/Card.tsx:115`; Playwright proof remains at `serve/cockpit/web/e2e/card-density-1565.spec.ts:400-443`, with deterministic branch proof at `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:170-218`.
  - AC-5: the optimize-first gate is implemented via `hasStateCue` at `serve/cockpit/web/src/components/Card.tsx:52` and conditional `card-cues-row` rendering at `serve/cockpit/web/src/components/Card.tsx:138`; the recalibrated performance threshold is encoded at `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:24`, `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:211`, and `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:269`, matching the refined AC-5 text at `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:599-601`.
- Challenger cross-check: `reconsider` at 0.72. Not blocking because AC-5 requires documented post-optimization `<5801` measurements in builder notes plus a passing recalibrated durable test, and architect cycle 4 explicitly rejected sparse-fixture expansion as an in-scope blocker (`.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:599-601`, `.owlbear/kanban/tasks/1565-p2-10-red-specify-task-card-information-density.md:618-620`).
- Blocking findings: none.

## Observations
- `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:9-13` still describes the old `<5,000` / `~2,500 nodes` assumption even though the executable budget is now 6400 at `serve/cockpit/web/src/__tests__/KanbanBoard.performance-700.test.tsx:24`. I did not block on this because the runtime proof and AC-5 math are correct, but the comment should be cleaned up on a future touch.
- The independent scoped rerun confirms proof adequacy despite modest `Card.tsx` statement coverage; the uncovered lines are outside the card-density contract reviewed here.
2026-05-15T05:40:59+00:00
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A (no update) | `serve/cockpit/README.md` lines 64–68 were updated in the prior docs gate cycle (commit 41342d46). AC-5 changes (conditional `card-cues-row` rendering + DOM threshold recalibration in `KanbanBoard.performance-700.test.tsx`) are internal optimizations that do not alter the user-visible feature description. README accurately states cues are rendered for all four state signals — conditional rendering only removes an empty container when none are active. No contradictions or stale content introduced. |
| 2 | External attribution | No | N/A | No external sources used. Standard React/CSS/Playwright tooling throughout. |
| 3 | Research doc | Yes | N/A | `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` referenced in task body Context section — linkage already present from prior cycle. |
| 4 | Deletion detection | No | N/A | No files deleted. AC-5 builder commit `09b8b6d2` modified `Card.tsx` and `KanbanBoard.performance-700.test.tsx` only. No orphaned references. |

### Verification Layers
- Layer 1 — `grep` confirms #1565 at `serve/cockpit/README.md:64` and `card-density-1565.spec.ts` at `:68`; no removed symbols found.
- Layer 2 — full editorial read: description ("id, priority tag, tag preview, update-recency, explicit text cues for all four state signals") remains coherent and accurate after AC-5 conditional rendering optimization.

### Files Updated
- None — README was already updated in prior docs gate cycle (commit 41342d46); AC-5 changes require no documentation change.

### Scratch Files Cleaned
- No `.owlbear/scratch/1565-*` files found.
2026-05-15T06:01:46+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4546 passed, ~230 failed, lint clean\n- All failures are in unrelated domains: kanban engine (dep_status, pick_tasks), storage re-exports, circular imports, cockpit models (claimed_by), cockpit mutation API, init exports. None in cockpit frontend card-density domain.\n- Task-scoped verification: 18 Playwright E2E passed (card-density-1565.spec.ts), 35 Vitest passed (Card.signal.test.tsx + KanbanBoard.performance-700.test.tsx). DOM budget now 5253 < 6400 threshold.\n- Previous audit regression (DOM budget 5801 > 5000) confirmed fixed by builder commit 09b8b6d2.\n- Regression verdict: PASS\n\n### Intent Verification\n- Scope alignment: PASS. Changed files: Card.tsx, Card.css, card-density-1565.spec.ts, Card.signal.test.tsx, KanbanBoard.performance-700.test.tsx, serve/cockpit/README.md. All cockpit frontend domain.\n- Purpose match: PASS. Card information density cues (id, priority, tags, state cues, recency) implemented per AC-1 through AC-4; DOM budget regression resolved per AC-5.\n- Extraneous scope: none.\n- Boundary check: function-level behavior verification deferred to reviewer.\n\n### Architect Quality: 3/5\nAC-1 \"E2E rendering fixtures\" ambiguity for title caused 4 test-writer/builder retry cycles before cycle-2 resolution (unit proof accepted). Architect did not anticipate 700-task DOM budget impact when specifying density additions, causing the regression caught in the first audit. However, architect responded competently across cycles 2-4: resolved tooling deadlock, added AC-5 with objective threshold formula, and tightened per reviewer findings. Score 3: notable gaps requiring significant improvisation across multiple pipeline cycles.\n\n### Commit Integrity\n- Upstream commit presence: PASS. 6 commits verified via git log:\n  - fcfa1f42 test: add failing E2E tests (test-writer RED)\n  - 74c50eb5 feat: implement card density cues (builder GREEN)\n  - e48fd533 test: add density/recency/cue coverage (test-writer retry)\n  - 624cd46c test: add AC-1 title unit proof (test-writer retry 2)\n  - 41342d46 docs: document card density cues in README (doc-writer)\n  - 09b8b6d2 fix: resolve card DOM budget regression (builder)\n- Kanban commit packaging: pending (will commit after end_work)\n\n### Deduction Breakdown\n| Criterion | Deduction | Evidence |\n|-----------|-----------|----------|\n| AC quality score 3 (<=3) | -.03 | 4 retry cycles from AC-1 ambiguity + missed DOM budget edge case |\n\n### Confidence: 0.97\n### Action: archive