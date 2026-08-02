---
# >> Resolved decision (filed 2026-04-29)
response: approved
decision: "Option A — grant test-writer write access to __tests__/ directories"
notes: "Added __tests__/ to allow-list in deny-src-writes.py (both dev and seed copies). 4 new test cases added. Task #1159 is a merged residual — archive when convenient."
# >> Agent metadata
task_id: 1159
agent: test-writer
created: 2026-04-29
urgency: blocking
decision_type: approach-selection
impact_tier: 2
resolved: 2026-04-29
---

# Decision: Test-Writer Path Guard Structural Loop on Task #1159

## Context

Task #1159 (scope:cockpit-frontend) requires adding 2 branch-binding TypeScript tests to `serve/cockpit/web/src/__tests__/useScanPolling_1157.test.ts`:
1. Non-array JSON payload handling (200 OK → items=[], error=null)
2. Non-Error rejection normalization (rejects as Error instance)

**The structural problem:** The test-writer VS Code mode enforces a path guard that denies writes to `serve/cockpit/web/src/__tests__/`. The builder also refuses TestFromAC_* ownership for frontend tests. This creates a 3+ cycle loop:
- Cycle 1: Test-writer mode rejects path
- Cycle 2: Builder cannot claim ownership (TestFromAC_ pattern)
- Cycle 3+: Request returns to test-writer, unresolved

**Reviewer assessment:** Implementation is verified (branch bindings confirmed). Reviewer confidence is 0.82 with only -0.08 deductions per missing test — suggesting residual-complete viability.

## Options

### A: Grant test-writer mode write access to serve/cockpit/web/src/__tests__/ for scope:cockpit-frontend tasks
- **Effort:** Low (mode boundary adjustment)
- **Trade-off:** Broadens test-writer scope to frontend TypeScript; creates two test paths (Python tests via current path guard, TS tests via new exception)
- **Risk:** Path guard exceptions can proliferate if not scoped strictly; breaks uniform test-writer behavior across scopes

### B: Authorize builder to add branch-binding proof tests (TypeScript only, no TestFromAC_ ownership concerns for frontend)
- **Effort:** Medium (builder adds TS tests as proof companion, not TDD artifact)
- **Trade-off:** Builder deviates from TestFromAC_ pattern for frontend; proof tests remain with implementation rather than in test suite
- **Risk:** Breaks TDD boundary between builder (code) and test-writer (tests); may set precedent for other scope:frontend deviations

### C: Archive #1159 as residual-complete — mark missing tests as informational only
- **Effort:** Immediate (no path guard negotiation needed)
- **Trade-off:** Two specific branch-binding scenarios go untested; implementation coverage stands as verified but not exhaustive
- **Risk:** Coverage gap persists; future refactoring could regress the two scenarios (-0.08 confidence each per reviewer estimate)

## Resolution

**Selected: Option A (modified)** — grant test-writer write access to `__tests__/` directories (the standard JS/TS test convention), not just `serve/cockpit/web/src/__tests__/` specifically.

### Changes Made
- `.owlbear/hooks/deny-src-writes.py` — added `_DUNDER_TESTS_RE` pattern matching `__tests__/` to the allow-list
- `seed/.owlbear/hooks/deny-src-writes.py` — same change (seed copy kept in sync)
- `tests/test_write_guard_hooks.py` — added 4 test cases (2 per copy) covering `__tests__/` file creation and apply_patch

### Rationale
`__tests__/` is the standard Jest/Vitest test directory convention. Recognizing it alongside Python's `tests/` is not an exception but a completeness fix — the allow-list was Python-only by omission.
