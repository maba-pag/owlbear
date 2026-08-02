---
id: 1163
title: 'RF-01: Tests for repairStorage API client'
status: archived
priority: medium
created: 2026-04-28T17:38:24.600049+00:00
updated: 2026-04-29T05:32:20.881178+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:test
parent:
depends_on:
- 1162
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Backend: `POST /api/tasks/repair` returns `list[RepairOutcome]` where each has:
- `task_id: int | None`
- `file_path: str`
- `code: str`
- `action: "fixed" | "quarantined" | "failed"`
- `detail: str | None`

Existing API client pattern: `serve/cockpit/web/src/api/` (fetch wrappers).

## Acceptance Criteria

- [ ] Test: `repairStorage()` sends POST to `/api/tasks/repair` with no body
- [ ] Test: successful response returns typed `RepairOutcome[]` array
- [ ] Test: network/server error rejects with meaningful error
- [ ] Test: `RepairOutcome` TypeScript type matches backend schema (action is union literal, task_id nullable)

## Scope

- **In scope:** API client function tests, TypeScript type definition
- **Out of scope:** Hook logic, UI components, backend changes

[[2026-04-29]]
## Architecture Review

### Verdict: MERGE — absorbed into #1164

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | API client tests only |
| Interface clarity | PASS | AC lines are specific and testable |
| Dependency correctness | FAIL | Depends on #1162 which does not exist (was deleted/merged previously) |
| Module layering | PASS | Test code only |
| TDD compliance | N/A | Task IS the test deliverable |
| KISS/YAGNI | PASS | 4 focused test cases |
| Premise challenge | FAIL | `type:test` tag causes double pass-through (test-writer + builder both skip). Nobody writes the tests. Identical structural flaw to #1161. |
| Pattern consistency | FAIL | References non-existent `serve/cockpit/web/src/api/` directory |
| Security surface | N/A | Test code |
| Single domain | PASS | Cockpit frontend |

### Challenge Results
- Challenger: SKIPPED — MERGE verdict (not APPROVE)

### Root Cause
The test/build decomposition pattern (separate #1163 for tests, #1164 for implementation) is structurally unsound in the TDD pipeline: `type:test` tag makes test-writer pass through, which cascades to builder pass-through, so the test file is never written. Identical to #1161 root cause.

Additional issues:
1. Dependency on #1162 is broken — task does not exist
2. Task body references `serve/cockpit/web/src/api/` (fetch wrappers) but directory does not exist; current pattern is inline fetch in hooks/components

### Action Taken
**MERGED into #1164** with refined AC:
1. All 4 test AC lines incorporated into #1164 alongside implementation AC
2. Removed #1164's dependency on #1163
3. Noted non-existent `api/` directory for #1164's architecture review
4. #1164 scope expanded: "repairStorage API client tests (merged from #1163)"
[[2026-04-29]]
## Test-Writer Notes

**Test file:** `.owlbear/scratch/repairStorage_1163.test.ts`
**Builder action required:** move to `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts`

*(File written to scratch — path guard prevents direct write to `serve/cockpit/web/src/__tests__/`.)*

**Class:** `TestFromAC_repairStorage`

| Category | Count |
|----------|-------|
| AC1 — POST /api/tasks/repair, no body | 4 |
| AC2 — returns typed RepairOutcome[] | 6 |
| AC3 — network/server error rejection | 7 |
| AC4 — RepairOutcome schema contract | 7 |
| **Total** | **24** |

**RED verification:** `npm test -- src/__tests__/repairStorage_1163.test.ts` — test file fails to load: `Error: Failed to resolve import "../api/repair"`. Module does not exist. All 24 tests fail. ✓

**AC coverage:**

| AC line | Tests |
|---------|-------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | AC1: 4 tests (URL, method, no-body, single-call) |
| Successful response returns typed `RepairOutcome[]` array | AC2: 6 tests (array, empty, length, fields, null task_id, null detail) |
| Network/server error rejects with meaningful error | AC3: 7 tests (network throw, Error type, non-empty msg; HTTP 500 throw, Error type, non-empty msg; HTTP 422 throw) |
| `RepairOutcome` type matches backend schema | AC4: 7 tests (fixed/quarantined/failed action values; null/number task_id; string file_path; string code) + compile-time: fixture variables typed as `RepairOutcome` |

**Note on AC4 TypeScript type-checking:** The fixture variables (`OUTCOME_FIXED`, `OUTCOME_QUARANTINED`, `OUTCOME_FAILED`) use explicit `RepairOutcome` type annotations. If the exported type has the wrong shape, TypeScript compilation fails — this is the type contract test.
[[2026-04-29]]
## Builder Notes
- Implementation: added [serve/cockpit/web/src/api/repair.ts](serve/cockpit/web/src/api/repair.ts) with exported `RepairOutcome` type and `repairStorage()` API client; moved TestFromAC file from scratch to [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts).
- Tests: 24/24 TestFromAC tests passed (scoped quality-runner run on `repairStorage_1163.test.ts`).
- Coverage: 100% on touched module `repair.ts`.
- Lint/Typecheck: clean (eslint clean, tsc clean).
- Evidence summary: RED verified first (module import missing), then GREEN after implementation; one intermediate lint/coverage issue was resolved by removing unnecessary catch wrapper branch.
- Fixes applied: created new frontend API module at `src/api/repair.ts` implementing `POST /api/tasks/repair` with no body; non-ok response throws `Error` including status code; successful response returns parsed `RepairOutcome[]`.

### Post-task Reflection
- Problems faced: task body referenced merged context and scratch-file handoff; needed to materialize the test file in repo path before RED verification could run.
- Workarounds applied: used quality-runner scoped runs for vitest/lint/coverage to preserve pipeline evidence and avoid direct terminal test execution.
- Patterns discovered: minimal fetch wrapper without a defensive catch branch is cleaner and satisfies both lint and full coverage for this contract.
- Time sinks: first implementation introduced a non-essential fallback branch that reduced module coverage below gate, requiring one refinement.
- Quality gaps: none blocking after final scoped run (tests/lint/coverage all green).
[[2026-04-29]]
## Review Evidence

### Test Results
- vitest (scoped): 24 passed, 0 failed in [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts)
- eslint (scoped): clean for [serve/cockpit/web/src/api/repair.ts](serve/cockpit/web/src/api/repair.ts) and [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts)
- typecheck: clean (`tsc --noEmit`)
- coverage: 100% on [serve/cockpit/web/src/api/repair.ts](serve/cockpit/web/src/api/repair.ts)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L74](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L74), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L81](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L81), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L91](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L91), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L99](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L99) | Yes | COVERED |
| Successful response returns typed `RepairOutcome[]` array | [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L110](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L110), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L116](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L116), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L122](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L122), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L128](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L128), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L140](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L140), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L146](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L146) | Yes | COVERED |
| Network/server error rejects with meaningful error | [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L157](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L157), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L166](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L166), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L174](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L174), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L183](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L183) | No. A generic non-empty message still passes the assertions at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L169](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L169) and [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L186](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L186). | LAX |
| `RepairOutcome` TypeScript type matches backend schema (action is union literal, task_id nullable) | Typed fixtures at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L16](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L16), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L24](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L24), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L32](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L32) and runtime assertions at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L207](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L207), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L213](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L213), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L219](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L219), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L225](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L225), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L231](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L231) | Partially. `task_id` nullability is enforced, but widening `action` from a literal union to `string` would still compile and the suite would stay green. | LAX |

#### Security Review
- No issues. The implementation is a fixed same-origin POST with no user-controlled interpolation at [serve/cockpit/web/src/api/repair.ts#L9](serve/cockpit/web/src/api/repair.ts#L9) and [serve/cockpit/web/src/api/repair.ts#L13](serve/cockpit/web/src/api/repair.ts#L13).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [ .owlbear/scratch/repairStorage_1163.test.ts](.owlbear/scratch/repairStorage_1163.test.ts) | Comment-only formatting changed; executable assertions remained materially the same in [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts) | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC3 only checks for a non-empty message at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L169](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L169) and [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L186](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L186). AC4 only proves current example values at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L207](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L207), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L213](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L213), and [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L219](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L219); they do not bind the literal-union type. |
| Negative/error-path coverage | ADEQUATE | Error-based network failures and non-ok HTTP responses are covered in this task slice. The non-Error fetch-rejection branch is explicitly owned by sibling task #1164 and was not counted against #1163. |
| Manual mutation reasoning | WEAK | If [serve/cockpit/web/src/api/repair.ts#L13](serve/cockpit/web/src/api/repair.ts#L13) changed to throw `new Error("oops")`, or [serve/cockpit/web/src/api/repair.ts#L5](serve/cockpit/web/src/api/repair.ts#L5) widened from a literal union to `string`, this suite would still pass. |
| Test independence | STRONG | Global fetch stubs are reset in `afterEach` at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L67](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L67). |
| Descriptive names | STRONG | The suite is AC-structured with descriptive `describe` / `it` labels throughout [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts). |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- No blocking gap inside task #1163's slice after scoping. The unresolved non-Error rejection branch is explicitly owned by sibling task #1164, which is already in review.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The live backend contract is correct today: [serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L341](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L341) returns `list[RepairOutcome]`, and [serve/kanban/src/owlbear_kanban/models.py#L391](serve/kanban/src/owlbear_kanban/models.py#L391), [serve/kanban/src/owlbear_kanban/models.py#L394](serve/kanban/src/owlbear_kanban/models.py#L394), [serve/kanban/src/owlbear_kanban/models.py#L395](serve/kanban/src/owlbear_kanban/models.py#L395) define the nullable and literal-union fields mirrored by [serve/cockpit/web/src/api/repair.ts#L2](serve/cockpit/web/src/api/repair.ts#L2), [serve/cockpit/web/src/api/repair.ts#L5](serve/cockpit/web/src/api/repair.ts#L5), and [serve/cockpit/web/src/api/repair.ts#L6](serve/cockpit/web/src/api/repair.ts#L6).
- The implementation is stronger than the AC3 tests: [serve/cockpit/web/src/api/repair.ts#L13](serve/cockpit/web/src/api/repair.ts#L13) includes the HTTP status code, but the tests only require a non-empty message.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | Implementation sends POST at [serve/cockpit/web/src/api/repair.ts#L9](serve/cockpit/web/src/api/repair.ts#L9); tests assert URL, method, no body, and single call at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L74](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L74), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L81](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L81), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L91](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L91), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L99](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L99) | AC1 block | PASS |
| Successful response returns typed `RepairOutcome[]` array | Frontend type matches live schema at [serve/cockpit/web/src/api/repair.ts#L1](serve/cockpit/web/src/api/repair.ts#L1) through [serve/cockpit/web/src/api/repair.ts#L6](serve/cockpit/web/src/api/repair.ts#L6); tests assert array return, empty array, item count, field mapping, and null preservation at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L110](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L110), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L116](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L116), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L122](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L122), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L128](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L128), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L140](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L140), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L146](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L146) | AC2 block | PASS |
| Network/server error rejects with meaningful error | Implementation throws a status-bearing HTTP error at [serve/cockpit/web/src/api/repair.ts#L13](serve/cockpit/web/src/api/repair.ts#L13), but the tests only require a non-empty message at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L169](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L169) and [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L186](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L186) | AC3 block | FAIL |
| `RepairOutcome` TypeScript type matches backend schema (action is union literal, task_id nullable) | Backend schema uses a literal union at [serve/kanban/src/owlbear_kanban/models.py#L394](serve/kanban/src/owlbear_kanban/models.py#L394); frontend interface mirrors it at [serve/cockpit/web/src/api/repair.ts#L5](serve/cockpit/web/src/api/repair.ts#L5). Tests enforce nullable `task_id` at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L225](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L225) and [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L231](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L231), but they do not fail if `action` widens to `string`. | AC4 block | FAIL |

### Deductions
- -0.08: AC3 "meaningful error" is only enforced as "non-empty string"
- -0.10: AC4 literal-union contract is not bound by compile-time or runtime assertions
- -0.02: false-green risk remains under plausible mutations (`action: string`, generic HTTP error message)

### Confidence: 0.80
### Verdict: FAIL
### Action: reject to backlog for test-quality rewrite/refined AC proof. The implementation itself does not need changes for this task slice.
[[2026-04-29]]
## Architecture Review (Re-merge cycle)

### Verdict: MERGE — re-absorbed into #1164

### Context
First arch review (2026-04-29) declared MERGE into #1164. Task survived and ran through a full pipeline cycle independently. Reviewer FAILed (0.80) with two valid deductions:
- AC3: assertions use `/.+/` (any non-empty string) — does not prove status code inclusion
- AC4: runtime assertions don't bind the `action` literal union — widening to `string` stays green

### Why MERGE (not REFINE)
Both reviewer concerns map directly to #1164's already-tighter AC:
- #1164 AC: "Non-ok HTTP response throws Error with message including status code (td:2)" → covers AC3
- #1164 AC: "RepairOutcome TypeScript interface... action: 'fixed' | 'quarantined' | 'failed'" (td:1) → covers AC4
- #1164's builder already ran both test files as a single suite (27 tests: 24 from 1163 + 3 from 1164)
- #1164 reviewer will evaluate `repairStorage_1163.test.ts` assertion strength against #1164's tighter AC

### Additional defects (carried from first review)
- Dependency on #1162 is broken (task deleted/never existed)
- `type:test` tag causes structural double-pass-through (test-writer + builder both skip)
- These are moot after merge — #1164 owns the scope

### Challenge Results
- Challenger: SKIPPED — MERGE verdict (not APPROVE)

### Test Depth
- Max depth: N/A (merged task)
- Test-writer: SKIP (pass-through via type:test tag; work owned by #1164)
[[2026-04-29]]
## Test-Writer Notes

- Non-implementation task (tagged `type:test`) — pass-through (Step 1a).
- Retry cycle: reviewer cited weak assertion specificity (AC3: non-empty message only; AC4: action literal-union not bound). Per Step 1b, weak-test findings pass through — the builder addresses. However, builder cannot modify `TestFromAC_*` tests.
- Architecture Review (2026-04-29) declared MERGE into #1164. #1164 carries tighter AC ("throws Error with message including status code"; "action: 'fixed' | 'quarantined' | 'failed'"). #1164's reviewer will evaluate `repairStorage_1163.test.ts` assertion strength against those AC lines.
- RED phase blocker: any strengthened assertions for AC3/AC4 would immediately PASS against the already-built `repair.ts` implementation — disqualifies them from RED phase.
- Passing through to builder (in-progress).
[[2026-04-29]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Pass-through per Test-Writer note (type:test workflow / merged scope context).
- No files changed, no tests run in this builder pass-through step.

[[2026-04-29]]
## Review Evidence

### Review Basis
- Latest binding refinement in this task body is the 2026-04-29 re-merge Architecture Review: task #1163 is a merged shell re-absorbed into #1164, and the missing proof for the original weak points is owned by the live absorbed file [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts).
- Verdict is therefore grounded on the live merged artifact set, not the older standalone shell summary: [serve/cockpit/web/src/api/repair.ts](serve/cockpit/web/src/api/repair.ts), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts), [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts), [serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L341](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L341), and [serve/kanban/src/owlbear_kanban/models.py#L388](serve/kanban/src/owlbear_kanban/models.py#L388).

### Test Results
- quality-runner scoped run: 35 passed, 0 failed across `src/__tests__/repairStorage_1163.test.ts` and `src/__tests__/repairStorage_1164.test.ts`

### Lint
- eslint scoped run: clean on `src/api/repair.ts`, `src/__tests__/repairStorage_1163.test.ts`, and `src/__tests__/repairStorage_1164.test.ts`
- typecheck: clean via quality-runner scoped report

### Coverage
- `src/api/repair.ts`: 100% statements, branches, functions, and lines

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L73](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L73), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L80](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L80), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L90](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L90), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L98](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L98) against [serve/cockpit/web/src/api/repair.ts#L9](serve/cockpit/web/src/api/repair.ts#L9) | Yes | COVERED |
| Successful response returns typed `RepairOutcome[]` array | [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L109](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L109), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L115](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L115), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L121](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L121), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L127](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L127), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L139](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L139), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L145](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L145) | Yes | COVERED |
| Network/server error rejects with meaningful error | [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L155](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L155), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L164](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L164), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L172](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L172), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L181](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L181) plus strengthened status/descriptive assertions at [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49), [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L69](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L69), [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L91](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L91) against [serve/cockpit/web/src/api/repair.ts#L12](serve/cockpit/web/src/api/repair.ts#L12) and [serve/cockpit/web/src/api/repair.ts#L17](serve/cockpit/web/src/api/repair.ts#L17) | Yes, under the latest merged-shell refinement. The older 1163-only non-empty-message assertions are tightened by the live absorbed 1164 suite. | COVERED |
| `RepairOutcome` TypeScript type matches backend schema (action is union literal, task_id nullable) | Typed fixtures at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L15](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L15), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L23](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L23), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L31](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L31), nullable checks at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L221](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L221), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L227](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L227), and exact literal-union guard at [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124) against [serve/cockpit/web/src/api/repair.ts#L1](serve/cockpit/web/src/api/repair.ts#L1) and [serve/kanban/src/owlbear_kanban/models.py#L391](serve/kanban/src/owlbear_kanban/models.py#L391) | Yes, under the latest merged-shell refinement. | COVERED |

#### Security Review
- No issues. The implementation posts to a fixed same-origin route at [serve/cockpit/web/src/api/repair.ts#L9](serve/cockpit/web/src/api/repair.ts#L9) and only formats error text from `response.status` or `String(error)` at [serve/cockpit/web/src/api/repair.ts#L12](serve/cockpit/web/src/api/repair.ts#L12) and [serve/cockpit/web/src/api/repair.ts#L19](serve/cockpit/web/src/api/repair.ts#L19).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts) | Original shell tests remain materially intact and still prove request shape, success path, and nullable-field behavior. | PRESERVED |
| [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts) | Builder-added changes are strengthening only: exact status-code assertions, original-Error preservation checks, descriptive wrapping checks, and literal-union compile-time guard. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | 1163 alone is weaker on AC3/AC4, but the live absorbed 1164 suite adds exact status-code and literal-union proofs at [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49) and [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124). |
| Negative/error-path coverage | ADEQUATE | Network `Error`, non-Error rejection, and non-ok HTTP paths are exercised across [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L155](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L155) and [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L28](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L28). |
| Manual mutation reasoning | ADEQUATE | Removing the status code from the HTTP error message or widening `RepairOutcome['action']` to `string` would now fail due to [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49) and [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124). |
| Test independence | STRONG | Global fetch stubs are reset in `afterEach` at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L66](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L66) and [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L22](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L22). |
| Descriptive names | STRONG | Both files use behavior-specific group and test names throughout [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts) and [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts). |

#### Data Safety
- No issues. This is a stateless fetch wrapper with no shared mutable state or persistence.

#### Implementation-Aware Gaps
- Non-blocking: the success-path `response.json()` failure branch at [serve/cockpit/web/src/api/repair.ts#L15](serve/cockpit/web/src/api/repair.ts#L15) is not explicitly exercised. This does not block the task because it is outside the written AC and latest refinement.

#### Necessity Check
- Not applicable. No dependency or external capability was added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes — original implementation pass, then merged-shell pass-through after re-merge |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Proof ownership is split across [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts) and the absorbed strengthening file [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts). Future standalone shell reviews will misread the contract unless both files are cited together.
- The frontend type is a compile-time mirror of the backend schema; there is no runtime validation on `response.json()` beyond the cast at [serve/cockpit/web/src/api/repair.ts#L15](serve/cockpit/web/src/api/repair.ts#L15). That is acceptable for this task’s narrow contract.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | Implementation posts to fixed route at [serve/cockpit/web/src/api/repair.ts#L9](serve/cockpit/web/src/api/repair.ts#L9); request shape is asserted at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L73](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L73), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L80](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L80), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L90](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L90), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L98](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L98) | AC1 block | PASS |
| Successful response returns typed `RepairOutcome[]` array | Frontend interface matches live backend schema at [serve/cockpit/web/src/api/repair.ts#L1](serve/cockpit/web/src/api/repair.ts#L1) and [serve/kanban/src/owlbear_kanban/models.py#L388](serve/kanban/src/owlbear_kanban/models.py#L388); success return and null preservation are asserted at [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L109](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L109), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L121](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L121), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L127](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L127), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L139](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L139), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L145](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L145) | AC2 block | PASS |
| Network/server error rejects with meaningful error | HTTP status-bearing error is implemented at [serve/cockpit/web/src/api/repair.ts#L12](serve/cockpit/web/src/api/repair.ts#L12); exact status-code proof and descriptive wrapping live at [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L49), [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L69](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L69), [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L91](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L91) | AC3 block across merged shell | PASS |
| `RepairOutcome` TypeScript type matches backend schema (action is union literal, task_id nullable) | Backend literal union is defined at [serve/kanban/src/owlbear_kanban/models.py#L394](serve/kanban/src/owlbear_kanban/models.py#L394); frontend mirror exists at [serve/cockpit/web/src/api/repair.ts#L4](serve/cockpit/web/src/api/repair.ts#L4); nullable `task_id` is asserted in [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L221](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L221), [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L227](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts#L227), and exact union equality is guarded in [serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124](serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts#L124) | AC4 block across merged shell | PASS |

### Deductions
- -0.03: proof ownership is split across two task files, so this pass depends on honoring the latest merged-shell refinement rather than reading [serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts](serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts) in isolation.

### Confidence: 0.92
### Verdict: PASS
### Action: advance to docs. The merged-shell scope is satisfied by the live absorbed artifact set, and the absorbed `1164` proofs strengthen rather than weaken the original `1163` intent.
[[2026-04-29]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/cockpit/README.md` already documents `POST /tasks/repair` → `view.repair_storage()` in the Mutation routes table (line confirmed in live file). No IN-scope prose doc references the new frontend fetch-wrapper module specifically. No update needed. |
| 2 | Module docstrings | No | N/A | No Python modules touched. All changed files are TypeScript. |
| 3 | External attribution | No | N/A | No external patterns cited in task body. |
| 4 | Research doc | No | N/A | No research doc produced or referenced. |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index consulted — no diagram `describes` glob matches `serve/cockpit/web/**`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No IN-scope doc files deleted. Scratch file `.owlbear/scratch/repairStorage_1163.test.ts` was already absent (file search returned nothing). |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/api/repair.ts` | OUT | N/A (TypeScript application source) |
| `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` | OUT | N/A (TypeScript test) |
| `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` | OUT | N/A (TypeScript test, merged shell reference) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (`.owlbear/scratch/repairStorage_1163*` — already absent before docs gate)
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | repair.ts:L10 sends POST; repairStorage_1163.test.ts:L73,L80,L90,L98 assert URL, method, no body, single call | PASS |
| Successful response returns typed `RepairOutcome[]` array | repair.ts:L1-6 type definition, L15 return; repairStorage_1163.test.ts:L109-L145 assert array, empty, fields, nulls | PASS |
| Network/server error rejects with meaningful error | repair.ts:L12-13 throws status-bearing error; repairStorage_1164.test.ts:L49-58 proves status code inclusion | PASS |
| `RepairOutcome` TypeScript type matches backend schema | repair.ts:L4 literal union mirrors models.py:L394; repairStorage_1164.test.ts:L124-134 compile-time AssertEqual guard | PASS |

### Test Results
- vitest (frontend full): 366 passed, 0 failed
- pytest (Python full): 107 failures — all outside task scope (kanban config, knowledge, orchestrator)
- eslint: clean for task files
- ruff: 4 violations — all outside task scope

### Architect Quality: 3/5
AC3 "meaningful error" was vague enough to cause a full reviewer FAIL cycle (0.80). Broken dependency on #1162 and structural `type:test` tag required two architecture reviews before merged-shell resolution. Builder/reviewer compensated, but avoidable rework.

### Deduction Breakdown
- AC quality score ≤ 3: -.03

### Confidence: .97
### Action: archive