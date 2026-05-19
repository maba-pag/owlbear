---
id: 964
title: 'Benchmark tests: kanban board 700-task mount, scroll, and re-render'
status: archived
priority: needed
created: 2026-04-18T15:51:06.555742+00:00
updated: 2026-04-19T00:49:09.434004+00:00
tags:
- cockpit
- frontend
- phase-2
- type:bench
- type:test
parent:
depends_on:
- 959
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Write benchmark tests that measure kanban board performance at 700 tasks. Covers AC1–AC3 from parent #959.

## Context

Research #959 defined a two-tier benchmarking approach: jsdom for structural assertions, Playwright for timing/scroll. Must test both uniform (100/column) and skewed (400 backlog) distributions.

See `.owlbear/research/959-frontend-perf-virtualization.md` § 3.4.

## Acceptance Criteria

- [ ] jsdom test: render 700 tasks, assert total DOM node count <5,000
- [ ] Playwright test: mount 700 tasks, assert LCP or render time <500ms
- [ ] Playwright test: scroll 100+ card column, measure frame drops (<5% target)
- [ ] Playwright test: trigger state change (e.g. context menu) with 700 cards, assert re-render <100ms
- [ ] Both uniform (100/col) and skewed (400 backlog) distributions tested
- [ ] Mock API serves deterministic 700-task fixture (SEED=42 for reproducibility)

## Dependencies

- Memoization task (sibling) should land first for realistic measurements
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/964-benchmark-tests-700-task-board.md
- Sources: 5 studied (all codebase-internal), 4 high-relevance
- Recommendation: No additional test code needed — all 6 ACs fully covered by existing passing tests (confidence: 0.95)
- Test coverage: 15 tests (10 jsdom in KanbanBoard_959.test.tsx + 5 Playwright in bench_959.spec.ts), all PASS
- Memoization dependency (#963) confirmed satisfied
- Follow-up tasks created: none (all ACs verified as passing)
- Decision requests: none
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: benchmark tests for 700-task board |
| Interface clarity | PASS | All 6 AC lines have specific numeric thresholds (<5000 nodes, <500ms, <5%, <100ms, SEED=42) |
| Dependency correctness | PASS | #959 (archived/done), #963 memoization (archived/done). Both satisfied. |
| Module layering | PASS | Test-only task, no production code changes |
| TDD compliance | N/A | This IS a test task — tests already exist from #959 pipeline |
| KISS/YAGNI | PASS | Minimal scope — verify existing coverage |
| Premise challenge | PASS | Tests exist and pass. Task validates tracking/audit trail for benchmark coverage. |
| Pattern consistency | PASS | Tests follow existing Vitest/Playwright patterns with data-testid selectors |
| Security surface | N/A | No system boundaries touched |
| Single domain | PASS | Single domain: cockpit frontend |

### Challenge Results

- Challenger: **reconsider** (confidence 0.45)
- Architect response: **partially accepted, partially rebutted**

Challenger raised 4 concerns:

1. **C1 — `type:bench` not a pass-through tag (critical):** ACCEPTED. Added `type:test` tag to enable pipeline pass-through. Without this, Gate 4 would fail.
2. **C2 — Fixture generators not identical (moderate):** ACKNOWLEDGED. `block_reason` strings differ (`"Blocked reason N"` vs `"Blocked N"`). Functionally benign — no code inspects block_reason text. DRY concern is real but below task threshold.
3. **C3 — AC says "LCP or render time" but tests use wall-clock (minor):** REBUTTED. AC literally says "LCP **or** render time." Wall-clock via `Date.now()` satisfies "render time" and is conservative (over-measures). AC is satisfied.
4. **C4 — No-op task entering pipeline (moderate):** REBUTTED. Pipeline protocol requires audit trail. Pass-through with `type:test` is the correct mechanism — test-writer will note existing coverage, reviewer will verify, auditor will archive. Direct closure from backlog would bypass verification gates.

Challenger confidence was low (0.45) primarily due to the tag issue (C1), which is now resolved. The core finding — all 6 ACs covered by existing tests — was not disputed.

### Action Taken

- Added `type:test` tag for pipeline pass-through (fixes C1)
- AC lines verified against actual test implementations in `KanbanBoard_959.test.tsx` (10 jsdom tests) and `bench_959.spec.ts` (5 Playwright tests)
- All 15 tests map to specific AC lines per research doc § 3.1

### Verdict: APPROVE

[[2026-04-18]]

## Test-Writer Notes

- Non-implementation task (tagged `type:test`) — no new tests applicable.
- Passing through to builder.

**Existing coverage verified (all ACs satisfied by prior #959 pipeline cycle):**

| AC | Test file | Test(s) | Coverage |
|----|-----------|---------|----------|
| jsdom: 700 tasks, DOM &lt;5,000 nodes | `KanbanBoard_959.test.tsx` | `total DOM node count within board stays below 5000` ×2 | ✓ uniform + skewed |
| Playwright: mount &lt;500ms | `bench_959.spec.ts` | `mount time &lt;500ms — uniform`, `mount time &lt;500ms — skewed` | ✓ |
| Playwright: scroll &lt;5% frame drops | `bench_959.spec.ts` | `100+ card column has overflow-y auto or scroll` + scroll tests | ✓ |
| Playwright: re-render &lt;100ms | `bench_959.spec.ts` | `re-render after task move &lt;100ms with 700 cards present` | ✓ |
| Uniform + skewed distributions | Both files | Every applicable test covers both | ✓ |
| SEED=42 deterministic fixture | Both files | LCG generator with seed=42 | ✓ |

**Test files:**

- `serve/cockpit/web/src/__tests__/KanbanBoard_959.test.tsx` — 10 jsdom structural tests (`TestFromAC_Board700Structural`)
- `serve/cockpit/web/e2e/bench_959.spec.ts` — 5 Playwright performance tests (`TestFromAC_Board700Performance`)
- Total: 15 tests, written during #959 TDD cycle

**Note:** `type:test` tag was added by architect (AC1 fix from challenger review) specifically to enable this pass-through.
[[2026-04-18]]

## Builder Notes

**Files changed:** None — pass-through task (type:test).

**Test results (GREEN verification):**

- `KanbanBoard_959.test.tsx` → 10/10 passed (jsdom, `TestFromAC_Board700Structural`)
- `bench_959.spec.ts` → 5/5 passed (Playwright, `TestFromAC_Board700Performance`)
- **Total: 15/15 passed**

**Lint:** No Python or TS files changed; ruff and ESLint not applicable.

**Evidence summary:**
All 6 ACs from task body are covered by existing tests written during #959 TDD cycle. Verified tests fail prior to implementation was not applicable here — this is a pure audit/pass-through task where tests already existed and passed. GREEN state confirmed by running both test suites directly.
[[2026-04-18]]

## Review Evidence

### Test Results

- Vitest (jsdom): 10 passed, 0 failed — `KanbanBoard_959.test.tsx`
- Playwright: 5 passed, 0 failed — `bench_959.spec.ts`
- **Total: 15/15 passed** (quality-runner, independent run)

### Lint: clean

- ESLint: no violations on either test file
- TypeScript: pre-existing config warnings (jsx/module resolution) unrelated to this task — do not affect execution

### Coverage: N/A

- Pass-through task — no production code changed; no modules to instrument

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| jsdom: 700 tasks, DOM <5,000 nodes | `total DOM node count within board stays below 5000` ×2 | Yes — `expect(nodeCount).toBeLessThan(5000)` | COVERED |
| Playwright: mount <500ms | `mount time <500ms — uniform/skewed` | Yes — `expect(elapsed).toBeLessThan(500)` | COVERED |
| Playwright: scroll <5% frame drops | `100+ card column overflow-y` + `scroll 400-card: scrollTop + <5% long tasks` | Yes — `longTasks <= 1` (5% of 30 frames) + scrollTop > 0 | COVERED |
| Playwright: re-render <100ms | `re-render after task move <100ms` | Yes — `expect(renderMs).toBeLessThan(100)` via MutationObserver + performance.now() | COVERED |
| Uniform + skewed distributions | Both distributions tested in all applicable tests | Yes — separate test cases per distribution | COVERED |
| SEED=42 deterministic fixture | Both files use `lcg(seed=42)` | Yes — hardcoded seed | COVERED |

#### Security Review

- No new production code or dependencies added. Test-only files, no system boundaries. No issues.

#### Test Integrity

- Files changed: none (pass-through task). No TestFromAC_* methods were modified. N/A.

#### Test Quality

- **Assertion specificity:** STRONG — all assertions use exact numeric thresholds (5000 nodes, 500ms, 1 long task, 100ms, 400/150/30 card counts)
- **Negative/error-path coverage:** STRONG — scroll test checks `longTasks !== -1` (element-not-found guard), re-render test checks `renderMs !== null`, overflow test inspects computed style
- **Manual mutation reasoning:** STRONG — flipping `<5000` to `>=5000`, `<500` to `>=500`, etc. would immediately fail; threshold mutations caught
- **Test independence:** STRONG — `afterEach(() => vi.unstubAllGlobals())` cleans global fetch stub; Playwright tests each set up their own route handlers
- **Descriptive names:** STRONG — all tests have precise human-readable names including distribution, threshold, and seed

#### Data Safety

- Test files only. No data safety concerns.

#### Builder Process Quality

- Single `## Builder Notes` section, no retries. CLEAN.

### Deductions

- None

### Verdict

Confidence: 0.97 → PASS
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pass-through test task — zero production code changes; `copilot-instructions.md` tables unchanged |
| 2 | Module docstrings | No | N/A | No Python modules created or modified; frontend-only test files (`KanbanBoard_959.test.tsx`, `bench_959.spec.ts`) |
| 3 | External attribution | No | N/A | All 5 sources codebase-internal (S1–S5 in research doc § 2); no external patterns used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/964-benchmark-tests-700-task-board.md` exists, linked in task body; follow-up tasks = none (all 6 ACs covered by existing tests, confidence 0.95) |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/964-*` files found)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| jsdom: 700 tasks, DOM <5,000 nodes | `KanbanBoard_959.test.tsx` — `expect(nodeCount).toBeLessThan(5000)` x2 (uniform + skewed) | PASS |
| Playwright: mount <500ms | `bench_959.spec.ts` — `expect(elapsed).toBeLessThan(500)` x2 | PASS |
| Playwright: scroll <5% frame drops | `bench_959.spec.ts` — `longTasks <= 1` (5% of 30 frames) + scrollTop | PASS |
| Playwright: re-render <100ms | `bench_959.spec.ts` — `expect(renderMs).toBeLessThan(100)` via MutationObserver | PASS |
| Uniform + skewed distributions | Both files test both distributions as separate cases | PASS |
| SEED=42 deterministic fixture | Both files use `lcg(seed=42)` | PASS |

### Test Results

- pytest (full suite): 652 passed, 12 failed — all failures outside task scope (mcp-knowledge #541, mcp-kanban #987)
- Vitest (jsdom): 10/10 passed (reviewer-verified independent run)
- Playwright: 5/5 passed (reviewer-verified independent run)
- ruff: clean, no violations

### Architect Quality: 4/5

All 6 AC lines have specific numeric thresholds (<5000, <500ms, <5%, <100ms, SEED=42). Minor gap: task was effectively pass-through since tests already existed from #959, but AC clarity was excellent.

### Deduction Breakdown

- 6/6 AC lines with specific evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence present, detailed, PASS 0.97: no deduction
- Full-suite failures all outside scope: no deduction

### Confidence: 0.98

### Action: archive
