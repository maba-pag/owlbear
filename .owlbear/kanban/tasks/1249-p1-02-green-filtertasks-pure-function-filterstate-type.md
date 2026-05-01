---
id: 1249
title: 'P1-02: GREEN — filterTasks pure function + FilterState type'
status: review
priority: critical
created: 2026-05-01T04:34:45.636679+00:00
updated: 2026-05-01T15:32:20.430646+00:00
tags:
- phase-1
- scope:cockpit-web
- tdd:green
parent: 1247
depends_on:
- 1248
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- filterTasks function exported from utils/filterTasks.ts (td:2)
- FilterState interface exported from the same module (td:0)
- All #1248 unit tests pass (GREEN) (td:2)
- Pure function — no React imports, no side effects (td:1)
- AND semantics across all four dimensions (td:2)

## In Scope
- filterTasks implementation
- FilterState type (may already exist from #1248 if co-located)

## Out of Scope
- React components
- Memoization (React Compiler handles this at call sites)

Brief: see parent #1247

[[2026-05-01]]
## Path Correction (from parent #1247 review)
AC path corrected: `lib/filterTasks.ts` → `utils/filterTasks.ts`. Authoritative path established by #1248 RED suite (imports `../utils/filterTasks`) and committed stub at `serve/cockpit/web/src/utils/filterTasks.ts`.

[[2026-05-01]]
## Research

Trivial GREEN implementation — pure `filterTasks` function matching 19 RED tests from #1248.

### Gate Checklist
1–4: N/A — trivial change; single obvious approach (Array.filter + AND-composed predicates).
5. Architecture fit: standalone utility at `serve/cockpit/web/src/utils/filterTasks.ts` (stub committed, imports aligned).
6. Implementation approach: `.filter()` with 4 dimension predicates:
   - text: `task.title.toLowerCase().includes(filter.text.toLowerCase())` (empty = pass)
   - priority: exact equality (empty = pass)
   - tags: `filter.tags.every(t => task.tags?.includes(t))` (empty = pass, undefined guard)
   - blocked: `!filter.blocked || task.blocked`

No external deps. No React imports. ~10 LOC. No follow-up tasks needed — implementation is self-contained within AC scope.
[[2026-05-01]]
## Architecture Review

**Verdict:** APPROVED #1249 → todo

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| filterTasks function exported from utils/filterTasks.ts (td:2) | Path corrected from `lib/` to `utils/` matching committed stub and #1248 test imports | Fixed in AC |
| FilterState interface exported from the same module (td:0) | Already defined in stub — type-only, compilation-verified | None |
| All #1248 unit tests pass (GREEN) (td:2) | 19 RED tests committed in `filterTasks_1248.test.ts` covering text (5), priority (4), tags (4), blocked (2), AND (2), edge (2) | None |
| Pure function — no React imports, no side effects (td:1) | Structural constraint — reviewer verifies via import scan. `.filter()` is non-mutating. `import type { Task }` is TS erasure, no runtime React dep | Builder note added |
| AND semantics across all four dimensions (td:2) | Tested by AND combination suite (2 tests) | None |

### Architecture Notes

- **Single file change**: `serve/cockpit/web/src/utils/filterTasks.ts` — replace stub body with ~10 LOC filter logic.
- **Type import**: `import type { Task } from '../hooks/useBoard'` is compile-time erased. No runtime dependency on React. AC "no React imports" = no runtime React code in utility.
- **Purity**: `.filter()` + predicate composition is inherently non-mutating. Reviewer should confirm: no `.sort()`, no `.splice()`, no parameter reassignment.
- **Implementation**: `Array.filter()` with 4 AND-composed predicates: text (case-insensitive substring), priority (exact equality), tags (`.every()` with optional chaining), blocked (boolean gate).

### Dependency Analysis

- **#1248** (RED tests): archived/done — tests committed, stub committed.
- **Parent #1247**: archived/done — brief context satisfied.
- No downstream blockers for this task.

### Challenger Results

Challenger returned `reconsider` (0.68). Rebuttal:
1. Purity untested by RED suite: acknowledged — purity is a structural td:1 constraint, not a behavioral test target. `.filter()` is non-mutating by definition.
2. Type import ambiguity: `import type` is TS compile-time erasure. No runtime React dependency. Non-issue.
3. Tag test count 3→4: minor evidence inaccuracy, corrected.

Override justified: all concerns addressed by structural constraints and builder guidance.
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts
- Classes: TestFromAC_FilterTasksPurity
- Tests per category: happy 0, edge 0, error 0, boundary 0 (purity smoke test — 1 test combining mutation guard + determinism + correctness)
- Total: 1 test, all FAIL (AssertionError: expected [] to deep equally contain task object — stub returns [])
- ruff: N/A (TypeScript file); no linter errors

## AC Coverage

| AC line | td | Coverage |
|---------|----|----|
| filterTasks function exported from utils/filterTasks.ts | td:2 | filterTasks_1248.test.ts (19 tests, primary RED suite) |
| FilterState interface exported from the same module | td:0 | skipped |
| All #1248 unit tests pass (GREEN) | td:2 | filterTasks_1248.test.ts is the evidence suite |
| Pure function — no React imports, no side effects | td:1 | filterTasks_1249.test.ts (1 smoke test — mutation guard + determinism) |
| AND semantics across all four dimensions | td:2 | filterTasks_1248.test.ts (AND combination describe block) |

Note: The primary RED suite is filterTasks_1248.test.ts (from task #1248). All functional AC is already covered by its 19 tests. filterTasks_1249.test.ts adds the purity smoke test (the only AC line not addressed by #1248).
[[2026-05-01]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/utils/filterTasks.ts
- Tests (RED -> GREEN): quality-runner scoped run first showed 20 failed (all task-owned tests), then 20 passed / 0 failed after implementation.
- Coverage: 100% for filterTasks.ts (statements/branches/functions/lines).
- Lint/diagnostics: quality-runner ruff reports TypeScript parse limitation (expected for TS); VS Code diagnostics show no errors in touched file and related task tests.
- Approach: implemented pure `filterTasks(tasks, filter)` using `Array.filter()` with AND-composed predicates across text (case-insensitive substring), priority (exact match), tags (`every` + undefined-safe optional chaining), and blocked (`blocked=true` gates to blocked tasks only).
- Scope control: single-file surgical source change; no tests modified; no React imports or side effects introduced.
- Durable module test check: no non-task-scoped filterTasks test file discovered; task-scoped suites used as authoritative GREEN evidence.

### Post-task Reflection
- quality-runner is effective for Vitest pass/fail and coverage on frontend tasks, but ruff output is non-actionable for `.ts` files by design.
- Keeping the implementation as a direct predicate composition avoided over-engineering and aligned tightly with AC semantics.
- Running RED and GREEN through the same scoped suite gave clear evidence integrity and prevented false-green risk.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped run: 20 passed, 0 failed
- Suites: `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts` (19/19), `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts` (1/1)

### Lint
- ESLint: clean on `src/utils/filterTasks.ts` and both task-owned test files
- VS Code diagnostics: no errors in `serve/cockpit/web/src/utils/filterTasks.ts`, `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts`, or `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts`

### Coverage
- `src/utils/filterTasks.ts`: 100% statements, 100% branches, 100% functions, 100% lines

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| filterTasks function exported from utils/filterTasks.ts (td:2) | `filterTasks_1248.test.ts` + `filterTasks_1249.test.ts` import the symbol from `serve/cockpit/web/src/utils/filterTasks.ts` | Yes — removing the export breaks the suites at import/compile time | COVERED |
| FilterState interface exported from the same module (td:0) | Type imports/usages in both task suites | Yes — removing the exported interface breaks the typed imports/usages | COVERED |
| All #1248 unit tests pass (GREEN) (td:2) | `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts` exact behavioral assertions across text, priority, tags, blocked, AND, edge paths | Yes — the suite would fail on behavioral regressions, and quality-runner confirms 19/19 GREEN | COVERED |
| Pure function — no React imports, no side effects (td:1) | `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts` | No — the test does not prove the explicit no-React-import clause, and its side-effect guard only checks input array length plus deterministic output | MISSING |
| AND semantics across all four dimensions (td:2) | `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts` combined-dimensions case | Yes — relaxing the final conjunction would fail the exact expected-result assertion | COVERED |

#### Security Review
- No issues. `serve/cockpit/web/src/utils/filterTasks.ts` is limited to local string normalization and array predicates; no filesystem, network, subprocess, eval, template, or persistence surface is present.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_FilterTasks | No builder edits detected in task-owned tests | PRESERVED |
| TestFromAC_FilterTasksPurity | No builder edits detected in task-owned tests | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts` uses exact `toEqual(...)` assertions across the behavioral suite |
| Negative/error-path coverage | ADEQUATE | False/pass-through branches are exercised for all four predicates in `filterTasks_1248.test.ts` |
| Manual mutation reasoning | WEAK | `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts` would still pass if a future implementation added a React import or mutated task objects in place while preserving array length and filtered output |
| Test independence | STRONG | Both suites build fresh fixtures locally; no shared mutable state |
| Descriptive test names | STRONG | Test names directly describe expected filter behavior |

#### Data Safety
- No issues. The implementation is a synchronous in-memory projection with no shared mutable state or multi-step writes.

#### Implementation-Aware Gaps
- No significant untested implementation branches in the current source.
- Current implementation matches the intended behavior in `serve/cockpit/web/src/utils/filterTasks.ts`: exported `FilterState`, exported `filterTasks`, AND-composed predicates across text/priority/tags/blocked, no mutating array operations, no runtime React import.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `vscode_listCodeUsages` found no live consumers beyond the task-owned tests, so there is no downstream caller regression risk from the exported utility signature.
- The current runtime boundary is safe because the only import in `serve/cockpit/web/src/utils/filterTasks.ts` is type-only, but importing `Task` from a hook-named module makes the non-React utility boundary slightly more fragile than a neutral shared type source.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| filterTasks function exported from utils/filterTasks.ts (td:2) | `serve/cockpit/web/src/utils/filterTasks.ts` exports `filterTasks`; both suites import it and quality-runner reports GREEN | `filterTasks_1248.test.ts` / `filterTasks_1249.test.ts` | PASS |
| FilterState interface exported from the same module (td:0) | `serve/cockpit/web/src/utils/filterTasks.ts` exports `FilterState`; test files type-import it successfully | type imports in both suites | PASS |
| All #1248 unit tests pass (GREEN) (td:2) | quality-runner: 19/19 passing in `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts` | `filterTasks_1248.test.ts` | PASS |
| Pure function — no React imports, no side effects (td:1) | Source currently appears compliant, but the mapped TestFromAC does not prove the explicit no-React-import clause or robustly fail on object mutation side effects | `filterTasks_1249.test.ts` | FAIL |
| AND semantics across all four dimensions (td:2) | `serve/cockpit/web/src/utils/filterTasks.ts` returns `matchesText && matchesPriority && matchesTags && matchesBlocked`; combined-dimensions suite is GREEN | `filterTasks_1248.test.ts` | PASS |

### Deductions
- -0.09: explicit no-React-import clause is unproved by the current TestFromAC suite.
- -0.05: purity side-effect guard is too weak to catch in-place mutation of task objects when array length and filtered output stay stable.

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to `todo` for test-writer follow-up only.
- Required follow-up: strengthen `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts` so the purity AC fails if the module introduces React import/hook usage and fails if task objects are mutated in place. If strengthened tests pass against the current source unchanged, builder-skip applies and the task can return directly to review.

### Post-task Reflection
- Frontend review evidence is now stronger than older repo memory implied: quality-runner ran both Vitest and ESLint successfully for this TS task, but the reviewer still had to verify the exact proof strength of the TestFromAC suite.
- The current source implementation is acceptable; the gate failure is entirely about missing/weak proof on an explicit AC clause.
- Routing this test-only miss back to `todo` preserves the working implementation and avoids an unnecessary builder retry.
[[2026-05-01]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts`
**Class:** `TestFromAC_FilterTasksPurity`

### Strengthening (reviewer reject follow-up)

Two gaps identified by reviewer were addressed:

1. **No-React-import clause** — added `module source contains no React import` test that reads `filterTasks.ts` from disk with `readFileSync` and asserts no `from 'react'`, `import 'react'`, or `require('react')` pattern. Fails the moment any React import is added to the source.

2. **Deep object mutation guard** — replaced the array-length-only guard with a per-object deep snapshot (`snapshotTask` helper copies both primitive fields and the mutable `tags` array). `does not mutate input task objects in place` fails if any property or nested array is modified in place, even when the filtered output length is unchanged.

### Tests (4 total)

| Test | Category | Purpose |
|------|----------|---------|
| module source contains no React import | structural | proves explicit no-React-import AC clause |
| does not mutate input task objects in place | side-effect | deep-object snapshot guard |
| does not mutate the input array itself | side-effect | array-reference + order guard |
| returns deterministic results for identical arguments | determinism | repeat-call value equality + correctness |

### AC Coverage

| AC line | td | Coverage |
|---------|----|----------|
| filterTasks exported from utils/filterTasks.ts | td:2 | filterTasks_1248.test.ts (primary suite) |
| FilterState exported from same module | td:0 | type imports in both suites |
| All #1248 unit tests pass GREEN | td:2 | filterTasks_1248.test.ts (19 tests) |
| Pure function — no React imports, no side effects | td:1 | filterTasks_1249.test.ts (4 tests — NOW FULLY PROVED) |
| AND semantics across all four dimensions | td:2 | filterTasks_1248.test.ts (AND block) |

### Result

4 tests, **all PASS** against current implementation (correct GREEN state).
Reviewer-confirmed builder-skip applies — task can advance directly to review.

[[2026-05-01]]
## Builder Notes
- Implementation: no source changes in this builder pass; existing implementation in `serve/cockpit/web/src/utils/filterTasks.ts` remains valid.
- Context: prior reviewer reject was test-proof only; test-writer strengthened `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts` and confirmed builder-skip conditions.
- Verification (quality-runner, scoped): 23 passed, 0 failed, 0 skipped.
  - `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts`: 19 passed
  - `serve/cockpit/web/src/__tests__/filterTasks_1249.test.ts`: 4 passed
- Coverage: `src/utils/filterTasks.ts` at 100% statements / 100% branches / 100% functions / 100% lines.
- Lint: ESLint clean for task-scoped source and tests.
- Approach: pass-through to review per pipeline rule for test-only retry where strengthened tests now pass against unchanged implementation.

### Post-task Reflection
- A reviewer test-proof reject can become builder-noop when test-writer strengthens assertions and green is re-established.
- Re-running independent quality-runner evidence in builder phase prevents stale-green handoffs.
- For frontend TypeScript tasks, ESLint + Vitest coverage is the relevant gate; ruff is not applicable.
- Keeping this pass surgical (no source edits) avoids unnecessary churn and preserves clear ownership boundaries.