---
id: 1536
title: 'P1-03: test — card signal data model: type extension, DR cross-reference,
  signal computation'
status: archived
priority: medium
created: 2026-05-13T18:41:58.221454+00:00
updated: 2026-05-13T22:44:53.427408+00:00
tags:
  - phase-1
  - scope:cockpit
  - data
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
- **In:** Tests for signal computation function, precedence chain, dep_status consumption, DR cross-reference
- **Out:** Implementation of signal model, card CSS rendering, data wiring to backend

## Acceptance Criteria

- AC-1: Vitest verifies `computeSignal(task, pendingDRIds)` returns `"dr-pending"` when `task.id` is present in the `pendingDRIds` Set, regardless of other flags
- AC-2: Vitest verifies `computeSignal(task, pendingDRIds)` respects the full precedence chain via competing-state tests: `dr-pending` > `blocked` > `claimed` > `deps-unmet` > `ready` (each pair tested with both conditions active, higher wins)
- AC-3: Vitest verifies `computeSignal(task, pendingDRIds)` maps `dep_status` values to signal: `"blocked"` → `deps-unmet`; `"ok"` / `"redirect"` / `null` → no `deps-unmet` (falls through to lower-precedence or `ready`)

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/card-signal-data-model-1536.md
- Sources: 7 studied, 5 high-relevance (all codebase-internal)
- Recommendation: pure function `computeSignal(task, pendingDRIds)` in `src/utils/computeSignal.ts`, tests in `src/__tests__/computeSignal.test.ts`, following existing `filterTasks` pattern (confidence: 0.90)
- Follow-up tasks created: none (decomposition #1536→#1544 already correct)
- Decision requests: none

## Key Findings
- Board `Task` type in `useBoard.ts` lacks `dep_status` — backend already serves it via `TaskSummary`; type extension needed in #1544
- `usePendingDRs` hook already provides `PendingDR[]` with `task_id` for DR cross-reference
- Function signature: `computeSignal(task, pendingDRIds: Set<number>): CardSignal`
- Backend `dep_status` values: `null` (no deps), `"ok"` (all resolved), `"redirect"` (dep redirected), `"blocked"` (dep unresolved)
- 10-12 test cases covering AC-1 (DR detection), AC-2 (full precedence chain), AC-3 (dep_status consumption)

## Challenge Results
- Challenge: reconsider (confidence: 0.62) — AC quality issues (function name missing from AC-2/AC-3), dep_status value mismatch (research used non-existent "ready" value)
- Architect response: accepted — refined all 3 AC lines, corrected dep_status values to match backend contract (`null`/`"ok"`/`"redirect"`/`"blocked"`)
2026-05-13T19:38:56+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure-function test only — one callable, one concern |
| Interface clarity | PASS | Function signature, input types, and return union fully specified in AC |
| Dependency correctness | PASS | No deps; impl task #1544 correctly depends on this |
| Module layering | PASS | Utils module, no upward imports |
| TDD compliance | PASS | This IS the test task; impl follows as #1544 |
| KISS/YAGNI | PASS | Minimal pure function, no abstractions |
| Premise challenge | PASS | Signal computation needed per brief D10/D14; no existing equivalent |
| Pattern consistency | PASS | Follows filterTasks.ts + filterTasks.test.ts pattern exactly |
| Security surface | PASS | No system boundaries — pure data transform |
| Single domain | PASS | Cockpit frontend data layer only |

### Challenge Results
- Challenger: reconsider (0.62)
- Findings: AC quality (function name missing in AC-2/AC-3), dep_status value mismatch (research used "ready" which backend never emits — actual values: null/ok/redirect/blocked), task-boundary stub concern
- Architect response: accepted AC quality and contract issues — refined all 3 AC lines to name callable and correct dep_status values. Dismissed task-boundary stub concern (standard TDD RED stub) and integration risk (out of scope, handled by sibling #1546).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: SKIP (task tagged `test` — builder writes tests directly)

### Design Diverge
- Trigger: skipped — single obvious approach (pure function + fixture factory), no competing designs

### Verdict: APPROVE
### Action Taken: Refined AC (dep_status contract alignment, function-name specificity), advanced to todo
2026-05-13T20:05:18+00:00
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/computeSignal.test.ts`
- Classes: `TestFromAC_ComputeSignal`
- Tests per category: happy 5 (one per signal value), edge 5 (AC-1 "regardless of other flags" variants), boundary 5 (AC-3 dep_status values + compound)
- Total: 16 tests, all FAIL (import error — `../utils/computeSignal` does not exist yet)
- ESLint: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC-1: dr-pending when id in pendingDRIds Set, regardless of flags | 6 tests (basic, not-in-set, blocked, claimed, dep_status, all-active) |
| AC-2: full precedence chain dr-pending > blocked > claimed > deps-unmet > ready | 5 tests (4 pairs + baseline) |
| AC-3: dep_status mapping "blocked"→deps-unmet; "ok"/"redirect"/null→ready | 5 tests (one per value + compound) |

Builder note: must create `src/utils/computeSignal.ts` exporting `computeSignal(task, pendingDRIds: Set<number>): CardSignal` and the `CardSignal` union type. Local `SignalInput` interface in test file is self-contained — does not depend on Task type extension (#1544).
2026-05-13T20:19:19+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/utils/computeSignal.ts

- Implementation summary:
  - Added `CardSignal` union export: `"dr-pending" | "blocked" | "claimed" | "deps-unmet" | "ready"`.
  - Added `computeSignal(task, pendingDRIds)` with AC precedence order:
    1. `dr-pending` when `pendingDRIds.has(task.id)`
    2. `blocked` when `task.blocked`
    3. `claimed` when `task.claimed`
    4. `deps-unmet` when `task.dep_status === "blocked"`
    5. `ready` fallback

- RED verification (quality-runner):
  - Test path: serve/cockpit/web/src/__tests__/computeSignal.test.ts
  - Result: FAIL as expected before implementation (missing module import `../utils/computeSignal`).

- GREEN verification (quality-runner):
  - Test path: serve/cockpit/web/src/__tests__/computeSignal.test.ts
  - Result: 16 passed, 0 failed
  - Coverage: 100% on `src/utils/computeSignal.ts`

- Lint status:
  - Source-scoped lint (builder-owned path): clean
  - Note: task test file reports an existing no-unused-vars warning on `CardSignal` import in test code; eslint exit code remains 0 and source lint is clean.

- Module-level durable test check:
  - No module-level durable `computeSignal` test file exists beyond task-scoped suite; skipped.

- Evidence summary:
  - AC-1 satisfied by top-priority Set membership check.
  - AC-2 satisfied by explicit ordered branch chain.
  - AC-3 satisfied by mapping only `dep_status === "blocked"` to `deps-unmet`; all other values fall through to lower-priority/`ready`.
2026-05-13T20:58:05+00:00
## Review Evidence
- Verdict: FAIL
- Builder evidence packet was internally consistent: 16 passed, 0 failed; 100% coverage on `serve/cockpit/web/src/utils/computeSignal.ts`; scoped source lint clean. No independent rerun was required.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/utils/computeSignal.ts:11` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:42`, `:54`, `:60`, `:66`, `:72` | PASS |
| AC-2 | `serve/cockpit/web/src/utils/computeSignal.ts:15`, `:19`, `:23`, `:27` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:82`, `:88`, `:94`, `:100`, `:106` | FAIL |
| AC-3 | `serve/cockpit/web/src/utils/computeSignal.ts:23`, `:27` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:116`, `:122`, `:128`, `:134`, `:140` | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-2 | The helper suite proves precedence ordering, but it never directly asserts that `computeSignal()` returns `"blocked"` when `task.blocked=true` and no higher-priority signal is active. Current blocked coverage only shows `dr-pending` beating `blocked` and `blocked` beating `claimed`, so a regression that returned `"blocked"` only when `claimed` was also true would still pass the existing helper tests. | `serve/cockpit/web/src/utils/computeSignal.ts:15`; `serve/cockpit/web/src/__tests__/computeSignal.test.ts:82`; `serve/cockpit/web/src/__tests__/computeSignal.test.ts:88` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a helper-level test that asserts `computeSignal()` returns `"blocked"` for `task.blocked=true` with no pending DR and no competing higher-priority signal, then re-run the task-scoped suite against current implementation. | `serve/cockpit/web/src/__tests__/computeSignal.test.ts` | Blocking finding #1 |

## Observations
- The implementation in `serve/cockpit/web/src/utils/computeSignal.ts` matches the intended branch order and shows no implementation defect from direct inspection.
- Safety/security review: no external input, auth, storage, or integration surface is in scope here; this is a pure local data transform.
- Adjacent Card signal tests are not sufficient substitute proof for this helper because the component currently resolves signal through separate local logic rather than importing `computeSignal()`. 
2026-05-13T21:29:08+00:00
## Test-Writer Notes
- Retry: added 1 test for reviewer gap (blocking finding #1, AC-2).
- Test file: `serve/cockpit/web/src/__tests__/computeSignal.test.ts`
- New test: `blocked alone: "blocked" when blocked=true with no pending DR and no other active signal` — directly asserts `computeSignal()` returns `"blocked"` in isolation (no pendingDRs, blocked=false, dep_status=null).
- Quality-runner (scoped): 17 passed, 0 failed; ESLint exit 0.
- Builder skip: test-only retry, all tests green (impl already correct).
- AC-2 coverage gap closed.
2026-05-13T21:59:53+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1536 -> docs | AC mapped to code and evidence sufficient.
- Combined builder and retry evidence was sufficient without an independent rerun: the builder note established 100% coverage on `serve/cockpit/web/src/utils/computeSignal.ts`, and the retry note added the previously-missing blocked-alone assertion and reported 17 passed, 0 failed with ESLint exit 0.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/utils/computeSignal.ts:11` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:42`, `serve/cockpit/web/src/__tests__/computeSignal.test.ts:72` | PASS |
| AC-2 | `serve/cockpit/web/src/utils/computeSignal.ts:11`, `:15`, `:19`, `:23`, `:27` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:82`, `:88`, `:94`, `:100`, `:106`, `:112` | PASS |
| AC-3 | `serve/cockpit/web/src/utils/computeSignal.ts:23`, `:27` | `serve/cockpit/web/src/__tests__/computeSignal.test.ts:122`, `:128`, `:134`, `:140`, `:146` | PASS |

## Observations
- Challenger cross-check raised an AC-2 wording ambiguity, but that concern is non-blocking here: the suite now directly covers every adjacent precedence comparison in the stated chain, and the `ready` endpoint can only be proven by the baseline no-signal case.
- AC-3 proof is sufficient because `dep_status === "blocked"` is the only special branch in `computeSignal()`, each non-blocking dep_status value is proven to avoid `deps-unmet`, and one compound case confirms lower-precedence fall-through still reaches `claimed`.
- Safety/security review: this task is a pure local data transform with no auth, storage, network, shell, or path-handling surface.
- Adjacent card wiring still uses separate signal resolution logic and remains out of scope for this task’s helper-level contract.
2026-05-13T22:21:58+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|---|---|---|
| README Verification | No update needed | `serve/cockpit/README.md` covers backend API, frontend stack attributes, and configuration — no section documents internal utility modules; `computeSignal.ts` introduces no new endpoint, CLI flag, or config var |
| External Attribution | N/A | All 7 sources codebase-internal per task body research section |
| Research Doc | N/A — linked | `.owlbear/research/card-signal-data-model-1536.md` exists; task body references it explicitly |
| Deletion Detection | N/A | No files deleted in this task (utility and test file both added) |

### Verification

- Layer 1 (grep): No `computeSignal` references in `serve/cockpit/README.md`; no orphaned references from prior docs.
- Layer 2 (editorial): README scope is API/stack/config — internal utilities are out of scope by convention. No contradictions or stale content introduced.

### Files Updated

None — task has no docs impact.

### Scratch Cleanup

No `.owlbear/scratch/1536-*` files found.
2026-05-13T22:44:53+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4594 passed (Python); vitest 17/17 passed for task-scoped `computeSignal.test.ts`. 214+ frontend failures and 5 Python failures are all from sibling/unrelated tasks (#1535, #1541, #1542, pre-existing board UI tests). Task adds a pure function with zero cross-module imports — cannot cause cross-task regressions.\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS — 3 commits touch only `src/utils/computeSignal.ts` and `src/__tests__/computeSignal.test.ts`, strictly cockpit frontend utils domain\n- purpose match: PASS — pure signal computation function with precedence chain matches stated task purpose\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC was refined after challenger caught dep_status contract mismatch and function-name specificity gaps (initial AC-2/AC-3 omitted callable name). Corrected before development. Final AC is specific and verifiable. Minor gap: initial AC needed challenger intervention, but the process worked as designed.\n\n### Commit Integrity\n- upstream commit presence: PASS — `e74d70a0` (test-writer), `a3450b55` (builder), `0411255d` (test-writer retry), `e06db75b` (researcher). All scoped to task files.\n- kanban commit packaging: pending (this audit cycle)\n\n### Deduction Breakdown\n- Lint violation (CardSignal unused import in test file, eslint warning): -.05\n\n### Confidence: 0.95\n### Action: archive