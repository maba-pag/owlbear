---
id: 960
title: TanStack Query migration + mtime-aware polling for kanban board
status: archived
priority: medium
created: 2026-04-18T14:45:58.181560+00:00
updated: 2026-04-18T18:25:11.584597+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent:
depends_on:
- 933
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Replace plain fetch hook with TanStack Query for the kanban board data layer. Enable mtime-aware short-polling at 3s interval (per brief #920). Wire status bar traffic-light to poll health.

## Context

GREEN #933 uses plain fetch. The brief specifies mtime-aware polling and status bar health indicators. TanStack Query provides polling, stale-while-revalidate, dedup, and error retry out of the box.

## Acceptance Criteria

- [ ] TanStack Query installed, useBoard hook migrated
- [ ] 3s polling interval using refetchInterval
- [ ] Conditional refetch: skip if mtime unchanged (saves parse overhead)
- [ ] Status bar traffic-light: green=healthy, yellow=slow, red=error
- [ ] Existing 26 KanbanBoard tests still pass (fetch stubs still work)

## Files

- `serve/cockpit/web/src/hooks/useBoard.ts`
- `serve/cockpit/web/src/KanbanBoard.tsx`
- `serve/cockpit/web/src/Shell.tsx` (status bar wiring)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/960-tanstack-query-vs-plain-polling.md
- Sources: 8 studied, 5 external (high-relevance: TanStack Query docs + npm)
- Recommendation: plain `setInterval` + `useRef` polling (confidence: 0.80)
- TanStack Query deferred until 2nd+ data consumer (KISS/YAGNI aligned)
- Key findings: mtime-skip is 3 lines of custom code either way; TQ's structural sharing, dedup, stale-while-revalidate unused by current AC; yellow-state timing needs custom `performance.now()` in both approaches; Shell ↔ KanbanBoard state wiring is the real architectural gap
- Follow-up tasks created: #965 (RED tests), #966 (Shell wiring), #967 (GREEN impl) — all at research
- Decision requests: none (T1 — autonomous: implementation approach choice)

## Challenge Results

- Challenger: reconsider (confidence in original TanStack Query: 0.45)
- Key challenges: KISS/YAGNI conflict (C2), mtime-skip not TQ-native (C3), yellow-state gap (C5), Shell wiring unaddressed (C6), 26-test migration risk (C7)
- Researcher response: accepted — revised recommendation from TanStack Query to plain polling. All major challenges valid. TQ remains best-practice for multi-consumer scenarios; deferred per "abstractions at 3rd repetition" principle.
[[2026-04-18]]

## Architecture Review

### Context

Research complete. Original TanStack Query approach rejected in favor of plain `setInterval` + `useRef` polling (KISS/YAGNI). Implementation decomposed into subtasks #965 (RED tests), #966 (Shell wiring), #967 (GREEN impl). This parent task's remaining role is as a research-completion marker — no implementation work remains on #960 itself.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research + decomposition is coherent scope; implementation split into subtasks |
| Interface clarity | FAIL (stale) | AC still references TanStack Query (`installed`, `refetchInterval`) — superseded by research rec. Subtask AC is correct. |
| Dependency correctness | WARN | #933 (dependency) is archived/complete ✓. Subtask dep gaps: #967 should depend on #965 (RED→GREEN), #966 should depend on #967 (hook must exist for Shell wiring). Fix when subtasks reach backlog. |
| Module layering | PASS | Subtasks respect component hierarchy: hook extraction → polling impl → Shell context lifting |
| TDD compliance | PASS | #965 is explicit RED-phase test task before #967 GREEN |
| KISS/YAGNI | PASS | Research correctly applied — TanStack Query deferred until 2nd consumer |
| Premise challenge | PASS | Polling + health indicators needed per brief #920 |
| Pattern consistency | PASS | Plain fetch + setInterval follows existing codebase (no external data-fetching library in use) |
| Security surface | PASS | No new system boundaries — polling existing trusted API |
| Single domain | PASS | All cockpit frontend |

### Codebase Findings

- `useBoard` is inline in `KanbanBoard.tsx` (L39-79), not in `hooks/` — subtask #967 correctly specifies extraction to `hooks/useBoard.ts`
- `Shell.tsx` has empty `data-testid="traffic-light"` and `data-testid="task-count"` spans — no state wired yet
- `KanbanBoard` is NOT mounted in Shell's routes (route renders `<div>kanban</div>` placeholder) — subtask #966 will need to address this
- Test count is ~36 (25 + 11 across two files), not 26 as stated in AC — subtask AC should reference actual count
- `TasksResponse` type already includes `mtime` field but it's discarded — ready for mtime-skip implementation
- No existing polling/timer patterns in `src/` — this will be the first

### Stale AC Note

The 5 AC lines on #960 reference TanStack Query and are superseded by the research recommendation (plain polling). The correct, revised AC lives on subtasks #965, #966, #967. This task advances as a research-completion marker.

### Subtask Dependency Gaps (fix at subtask backlog review)

- #967 (GREEN) should `depends_on: [965]` — RED tests must exist before GREEN implementation
- #966 (Shell wiring) should `depends_on: [967]` — needs the polled hook to exist
- Test count references in subtask AC should be updated from "26" to "36"

### Challenge Results

- Challenge: SKIPPED — research phase already included challenger pass (result: `reconsider`, confidence 0.45 in original TQ approach). Recommendation revised from TanStack Query to plain polling. Re-challenging the same already-revised decision on the parent is redundant; subtasks will receive fresh challenges at backlog.

### Verdict: APPROVE (as research-completion marker)

### Action Taken: Advanced #960 to todo. Original AC stale but preserved for history. Implementation proceeds via subtasks #965, #966, #967. Tagged `type:build` — note for test-writer: this task produced research and subtasks, not code; pass through without writing tests

[[2026-04-18]]

## Test-Writer Notes

- Non-impl pass-through: AC references only TypeScript/React files (`useBoard.ts`, `KanbanBoard.tsx`, `Shell.tsx`) — no testable Python interfaces.
- Architecture review explicitly flagged this task as a research-completion marker: "pass through without writing tests."
- Original TanStack Query AC is stale (superseded by plain polling recommendation from research).
- Actual RED-phase tests are in subtask **#965** (`useBoard` polling + mtime-skip + error state tests) which must be promoted to `todo` before the builder starts #967.
[[2026-04-18]]

## Builder Notes

**Pass-through: research-completion marker — no implementation.**

### Files Changed

None.

### Test Results

N/A — no testable code. All existing tests unaffected.

### Lint

N/A.

### Evidence Summary

- Architecture review and test-writer both explicitly flagged #960 as a non-impl pass-through.
- Original AC (TanStack Query) is stale; superseded by plain polling recommendation from research.
- Implementation decomposed into subtasks: #965 (RED tests), #966 (Shell wiring), #967 (GREEN impl).
- Subtask dependency gaps remain to be fixed at backlog review: #967 should depend on #965; #966 should depend on #967.
[[2026-04-18]]

## Review Evidence

**Type:** Research-completion marker pass-through. No code changed, no tests written.

**Changed files:** None (builder confirmed; consistent with research decomposition outcome).

**Quality-Runner:** Skipped — justified. Zero source/test files changed. Existing suite unaffected by definition.

**AC compliance:** All 5 AC lines are stale (reference TanStack Query approach superseded by research). Uniformly documented at every upstream stage. Correct AC lives on subtasks #965, #966, #967.

**Test integrity:** No `TestFromAC_*` classes created. No tests modified. N/A.

**Security:** No code changed. No new attack surface. Clean.

**Subtasks verified:** #965 (RED tests), #966 (Shell wiring), #967 (GREEN impl) — all exist at `research` status, all depend on #960. ✓

**Open defects (pre-flagged by architect, not #960's responsibility):**

- #967 missing `depends_on: [965]` (RED→GREEN ordering gap)
- #966 missing `depends_on: [967]` (wiring needs hook to exist)
- "26 tests" in #965 and #967 AC should be ~36

**Deductions:** -0.04 (pre-documented subtask gaps not yet resolved)

**Confidence: .94 → PASS**

**Action:** Advancing to docs.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Research-completion marker — no code changed, no behavior/API change |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Updated | 5 external TanStack Query sources added to `.owlbear/sources/overview.md` (sources 1–5 from research doc: TQ overview, polling guide, testing guide, important defaults, npm) |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/960-tanstack-query-vs-plain-polling.md` exists and is linked from task body ✓ |

### Files Updated

- `.owlbear/sources/overview.md` — added "TanStack Query vs Plain Polling Research (Task #960)" section with 5 external sources

### Scratch Files Cleaned

- None (no `.owlbear/scratch/960-*` files found)

Commit: `226495e6` — docs: update sources for TanStack Query research (#960, doc-writer)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| TanStack Query installed, useBoard hook migrated | STALE — superseded by research rec (plain polling). Research doc exists at `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | N/A (stale) |
| 3s polling interval using refetchInterval | STALE — revised AC on subtask #967 (plain setInterval) | N/A (stale) |
| Conditional refetch: skip if mtime unchanged | STALE — revised AC on subtask #967 (useRef mtime-skip) | N/A (stale) |
| Status bar traffic-light: green/yellow/red | STALE — revised AC on subtask #966 (Shell wiring) | N/A (stale) |
| Existing 26 KanbanBoard tests still pass | STALE — architect noted actual count is ~36. No code changed, tests unaffected | N/A (stale) |

**Research deliverable verification (Step 1a):**

1. Research doc exists and is substantive (8 sources, feature comparison, recommendation)
2. Follow-up tasks #965, #966, #967 all exist at `research` status, all depend on #960, all have concrete AC
3. All three subtasks reference the research doc
4. Sources overview updated with 5 external sources (commit `226495e6`)

### Test Results

- pytest: 594 passed, 6 failed (all in `serve/mcp-knowledge/` — outputschema_541, search_v2, phase_a_config — entirely outside task scope)
- ruff: clean

### Architect Quality: 4/5

Thorough review. Correctly identified stale AC, codebase realities (useBoard inline in KanbanBoard.tsx, ~36 actual tests, empty Shell spans), and subtask dependency gaps. Minor gap: stale AC preserved without inline revision, requiring every downstream agent to re-explain staleness. Subtask dep gaps flagged but not fixed at review time.

### Deduction Breakdown

- Stale AC (5 lines): -.02 total. Staleness is by documented design (research pivot), not missing evidence. True deliverables (research doc, subtasks, sources) all verified.
- Test failures outside scope: no deduction
- Ruff clean: no deduction
- AC quality 4/5: no deduction
- Reviewer evidence present and detailed: no deduction

### Confidence: .98

### Action: archive
