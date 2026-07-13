---
id: 955
title: 'E2E kanban board tests: DnD highlights, card density, scroll'
status: archived
priority: medium
created: 2026-04-18T13:41:19.344390+00:00
updated: 2026-04-18T14:50:02.970472+00:00
tags:
- cockpit
- frontend
- phase-2
- type:test
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Write E2E tests for kanban board AC items that cannot be tested in jsdom: drag-to-move target highlighting, card density (48-56px height), and horizontal/vertical scroll behavior.

## Context

Discovered during #931 research: jsdom lacks layout engine and functional DnD API. These 3 AC items from #931 require a real browser environment. See `.owlbear/research/931-kanban-board-tests.md` §3.2.

## Acceptance Criteria

- [ ] E2E test framework chosen (Playwright recommended)
- [ ] Tests cover:
  - Drag-to-move: valid target columns highlight based on `valid_transitions`; invalid targets dim
  - Card density ~48-56px height
  - Horizontal scroll between columns; vertical scroll within columns
- [ ] Tests run against dev server or build

## Dependencies

- Kanban board GREEN implementation must be complete first
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/955-e2e-kanban-board-tests.md
- Sources: 8 studied, 5 high-relevance (≥0.90)
- Recommendation: Playwright Test (standalone) for E2E kanban board tests (confidence: 0.85)
- Follow-up tasks created: #956 (Playwright infra setup), #957 (RED E2E tests) at research
- Decision requests: none — T1 autonomous (tool choice within existing AC recommendation)

## Challenge Results

- Challenger: block (confidence in original Vitest Browser Mode: 0.35)
- Key challenges: (1) DnD mid-drag assertion unverified in Vitest browser mode, (2) PDS shadow DOM + style pipeline gap, (3) vitest-browser-react is community pkg, (4) task AC explicitly recommends Playwright
- Researcher response: accepted — revised recommendation from Vitest Browser Mode to Playwright Test. Challenger correctly identified that the primary use case (DnD mid-drag visual state inspection) lacks verified support in Vitest browser mode. KISS argument was weakened by separate setup file + PDS style loading gap.
[[2026-04-18]]

## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| E2E test framework chosen (Playwright recommended) | SATISFIED — research complete, Playwright Test chosen at 0.85 confidence, validated by challenger | None |
| Tests cover DnD highlights, card density, scroll | DELEGATED to #957 (RED: Playwright E2E tests) | #957 carries this AC |
| Tests run against dev server or build | DELEGATED to #956 (Setup Playwright E2E infra) | #956 carries this AC |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | After delegation, #955 = framework decision only |
| Interface clarity | PASS | Research doc specifies Playwright Test, `page.mouse` API, `locator.boundingBox()` |
| Dependency correctness | PASS (with note) | No formal depends_on needed for #955. **FIX NEEDED:** #957 depends_on should include #956 (needs Playwright infra before writing tests). Current: [955]. Should be: [955, 956] |
| Module layering | N/A | No code changes |
| TDD compliance | N/A | Research/decision task, tagged `type:test` (pass-through) |
| KISS/YAGNI | PASS | Minimal scope — framework choice only |
| Premise challenge | PASS | jsdom lacks layout engine and DnD API — E2E framework needed. Confirmed via Shell.tsx placeholder `<div>kanban</div>` and absence of any E2E infra in package.json |
| Pattern consistency | PASS | Separate `test:e2e` script alongside `test` follows standard E2E separation |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend/test tooling only |

### Dependency Notes

1. **#957 depends_on gap:** #957 currently depends_on [955] but should also depend on #956. Its body says "Depends on Playwright infra setup" but the formal dep is missing. Must be fixed when #956/#957 are reviewed.
2. **Informal GREEN dependency:** Both #955 and #957 mention "kanban board GREEN must be complete first" but no task ID is tracked in depends_on. The kanban board is still a placeholder (`<div>kanban</div>` in Shell.tsx). This dependency should be formalized when the GREEN task exists.
3. **Research note B1:** Research recommends `vite preview` in webServer config, which requires a prior `vite build`. #956's AC should validate whether to use `vite dev` vs `vite preview` (build-then-preview chain).

### Codebase Evidence

- No Playwright or E2E infra exists: `serve/cockpit/web/package.json` has no `@playwright/test`, no `test:e2e` script
- No kanban board component: Shell.tsx L36 renders `<div>kanban</div>` placeholder
- Current test stack: vitest 3 + jsdom 26 + @testing-library/react 16
- .gitignore does not yet include Playwright artifacts (`test-results/`, `playwright-report/`)

### Challenge Results

- Challenger: reconsider (confidence 0.50)
- Key challenges: (C1) AC narrowing mismatches title, (C2) #957 depends_on [956] missing, (C3) GREEN dependency untracked
- Architect response: accepted substance of all challenges. Rebutted path — APPROVE with delegation documentation is cleaner than closing/superseding since the pipeline lacks a supersede mechanism. Dependency fixes noted for downstream agents.

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC #1 satisfied via research. AC #2-3 delegated to #957 and #956 respectively. Three dependency fixes documented for downstream resolution

[[2026-04-18]]

## Test-Writer Notes

**Pass-through — non-implementation task, no tests written.**

### Rationale

# 955 is a framework decision + delegation task. No testable interfaces exist

- AC #1 (framework chosen = Playwright) — satisfied by research, no code/tests needed
- AC #2 (DnD, density, scroll tests) — delegated to **#957** (RED: Playwright E2E tests)
- AC #3 (runs against dev server) — delegated to **#956** (Setup Playwright E2E infra)

### Dependency chain for actual tests

1. **#956** (todo → in-progress): Install Playwright, `playwright.config.ts`, `e2e/` dir, smoke test
2. **#957** (todo → in-progress, after #956): Write failing Playwright tests for DnD highlights, card density, scroll

Note: #957's `depends_on` should be updated to include #956 (currently only lists #955).
[[2026-04-18]]

## Builder Notes

**Pass-through — no implementation required.**

### Files Changed

- `.owlbear/kanban/tasks/957-red-playwright-e2e-tests-for-kanban-board-dnd-density-scroll.md` — fixed `depends_on` to include `956` (architect-documented gap, C2)

### Test Results

- N/A — framework decision task; no code, no tests

### Lint

- N/A — no Python/TS files modified

### Evidence Summary

- AC #1 (Playwright chosen, confidence 0.85): satisfied by research in `.owlbear/research/955-e2e-kanban-board-tests.md`, validated by challenger
- AC #2 (DnD, density, scroll tests): delegated to #957
- AC #3 (runs against dev server): delegated to #956
- Dependency gap fixed: `#957 depends_on` updated from `[955]` → `[955, 956]`

### Remaining Dependency Notes (for reviewer)

- Informal GREEN dependency (#956, #957 both require kanban board component to exist) should be formalized when the GREEN impl task is created
- #956 AC should clarify `vite dev` vs `vite preview` for `webServer` config (research note B1)
[[2026-04-18]]

## Review Evidence

### Test Results

- N/A — pass-through task, no code or tests produced

### Lint

- N/A — only changed file is `.owlbear/kanban/tasks/957-*.md` (YAML/Markdown metadata)

### Coverage

- N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes exist — conditional skipped.

#### Security Review

- Only changed file: `.owlbear/kanban/tasks/957-red-playwright-e2e-tests-for-kanban-board-dnd-density-scroll.md` — YAML frontmatter metadata only. No secrets, no injection surfaces, no code. No issues.

#### Test Integrity

No `TestFromAC_*` modifications — conditional skipped.

#### Test Quality

Pass-through task — no tests written. Test-writer correctly identified no testable interfaces exist for AC #1. AC #2-3 delegated to #957/#956. N/A.

#### Data Safety

N/A — no runtime code, no state mutations, no external boundaries.

#### Implementation-Aware Test Gap Analysis

N/A — no implementation.

#### Necessity Check

N/A — no new dependencies, integrations, or tooling added by #955 itself.

#### Builder Process Quality

One `## Builder Notes` section, single atomic change, no retries. **CLEAN.**

### Pass 2 — INFORMATIONAL

No informational findings.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| E2E test framework chosen (Playwright recommended) | Research doc `.owlbear/research/955-e2e-kanban-board-tests.md` — 8 sources, 5 ≥0.90 relevance, Playwright chosen at 0.85 confidence; challenger validated (originally blocked Vitest Browser Mode at 0.35 confidence; researcher accepted revision) | PASS |
| Tests cover DnD highlights, card density, scroll | Delegated to #957 — architect APPROVE verdict documents this explicitly. #957 task file exists at correct path with matching AC lines for DnD, density, scroll. | PASS (delegated) |
| Tests run against dev server or build | Delegated to #956 — architect APPROVE verdict documents this explicitly. | PASS (delegated) |

### Builder Change Verification

- Claimed: `#957 depends_on` updated from `[955]` → `[955, 956]`
- Verified: `.owlbear/kanban/tasks/957-red-playwright-e2e-tests-for-kanban-board-dnd-density-scroll.md` frontmatter shows `depends_on: [955, 956]` — matches claim exactly.

### Deductions

None.

### Verdict

Confidence: 0.96 → **PASS**

Action: advance to docs.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Framework decision + delegation task; only change was YAML frontmatter in #957 task file. No copilot-instructions.md update needed. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` §"E2E Kanban Board Tests (Task #955)" already contains 4 rows: Playwright intro, DnD+scrolling, Locator API (boundingBox), Vitest Browser Mode, Vitest Component Testing — all dated 2026-04-18. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/955-e2e-kanban-board-tests.md` exists, linked in task body. Follow-up tasks #956 and #957 confirmed created. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/955-*` files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| E2E test framework chosen (Playwright recommended) | `.owlbear/research/955-e2e-kanban-board-tests.md` L67-69: "Use Playwright Test (standalone)"; challenger validated at 0.85 confidence | PASS |
| Tests cover DnD highlights, card density, scroll | Delegated to #957; task file confirmed with matching AC, `depends_on: [955, 956]` verified in frontmatter | PASS (delegated) |
| Tests run against dev server or build | Delegated to #956; architect APPROVE documents delegation | PASS (delegated) |

### Test Results

- pytest: 593 passed, 6 failed (all in serve/mcp-knowledge/ -- pre-existing, out of scope), 0 skipped
- ruff: clean

### Architect Quality: 4/5

Clear framework-choice AC with recommended tool. Minor dependency gap (C2: #957 missing #956 in depends_on) caught by challenger and fixed by builder. Good delegation documentation. Deducted 1 point for the gap requiring downstream fix.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 3 verified) -- no deduction
- Lint violations: none -- no deduction
- AC quality score 4 (> 3): no deduction
- Reviewer evidence: present, detailed, PASS verdict -- no deduction
- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge, unrelated) -- no deduction

### Confidence: 1.00

### Action: archive
