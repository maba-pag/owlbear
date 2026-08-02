---
id: 1376
title: 'P2-01: Test Cockpit task detail context model'
status: archived
priority: medium
created: 2026-05-06T01:04:29.741762+00:00
updated: 2026-05-08T12:43:49.316861+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- task-detail
- model
parent: 1363
depends_on:
- 1367
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests proving Cockpit task detail state includes the backend context needed for safe UI decisions.

## Problem Evidence
- DetailTab `TaskDetail` omits backend task fields: `claimed`, `claimed_at`, and `dep_status`. Note: `claimed_by` is deliberately dropped by the backend in `TaskSummary._coerce_claimed` and is NOT part of the API response — this is not a gap to fill.
- Dependency and parent context (`dep_status` read-time projection) is not available on the frontend detail model.
- Missing context can be confused with a user clearing a value.

## Acceptance Criteria
- Tests prove the frontend task detail model exposes claim state fields: `claimed` (boolean) and `claimed_at` (string or null). `claimed_by` is NOT in the backend API response and is not tested. (td:2)
- Tests prove `dep_status` from the backend `ShowTaskResponse` is present on the task detail model. Existing `parent` and `depends_on` fields are not regressed. (td:2)
- Tests prove that when `claimed_at` or `dep_status` is null, DetailTab renders an explicit DOM element (not a missing element). The `TaskDetail` interface in DetailTab.tsx defines these as required fields (`string | null`, not optional), enforced by `tsc` on the implementation file — test files are excluded from `tsc` by tsconfig.json and cannot provide compile-time proof. (td:1)
- Tests cover model state representation for: unclaimed, claimed, blocked, and dependency-constrained tasks — asserting data shape, not UI gating behavior (gating is out of scope). (td:2)
- Tests exercise all three new fields (`claimed`, `claimed_at`, `dep_status`) via `data-testid` queries and exact value assertions; removing any rendered field element from DetailTab would fail the suite. (td:1)

## Scope
- In scope: Cockpit frontend task detail type, hook, and component-state tests.
- Out of scope: parent/dependency edit validation, action gating, conflict resolution, backend schema changes, mutation-response handling, and cache/SSE invalidation from #1346.

## Architecture Notes
- Backend chain: `ShowTaskResponse` → `TaskFull` → `TaskSummary`. All three include `claimed_at`, `claimed`, `dep_status`, `parent`, `depends_on`. See `serve/kanban/src/owlbear_kanban/models.py`.
- `_coerce_claimed` validator pops `claimed_by` and derives `claimed: bool` from `claimed_at` presence. Frontend should mirror this: `claimed_at` + derived `claimed`, no `claimed_by`.
- `dep_status` is a read-time projection (not stored), computed from dependency task states. The frontend model needs to accept it from the API response.
- Blast radius: existing `TaskDetail` fixture literals appear in ~6 durable test files (`DetailTab.test.tsx`, `DetailTab_1344.test.tsx`, `ErrorContract_1374.test.tsx`, `ActivityTab_1156.test.tsx`, `Shell_1344.test.tsx`, `PdsMigration_1230.test.tsx`). When #1377 adds fields to the interface, these fixtures will need updating. The test-writer should be aware but this is expected TDD RED/GREEN behavior.
- Avoid ID-only or type-shape-only assertions — pin specific field values in fixtures to prevent false-green tests.

## Counterpart
Implementation task: #1377.

[[2026-05-08]]
## Architecture Review

### Verdict: APPROVE (after refinement)

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| Claim state fields: `claimed`, `claimed_at` | REFINED — removed `claimed_by` (backend `_coerce_claimed` deliberately drops it; not in API response) | Corrected to match actual backend surface |
| `dep_status` available on detail model | REFINED — vague "dependency context" replaced with specific field name `dep_status` | Anchored to `TaskSummary.dep_status` |
| Absent optional context explicit | REFINED — narrowed from mutation-clearing semantics to model-level null representation | Removed scope overlap with edit validation |
| State combination coverage | REFINED — clarified "asserting data shape, not UI gating behavior" to resolve scope contradiction | Challenger caught scope conflict; resolved |
| RED proof fails against current model | PASS — current `TaskDetail` in DetailTab.tsx omits `claimed`, `claimed_at`, `dep_status` | Verified via codebase read |

### Architecture Notes
- Backend model chain: `ShowTaskResponse` → `TaskFull` → `TaskSummary` — all include `claimed_at`, `claimed`, `dep_status`.
- `claimed_by` explicitly stripped by `_coerce_claimed` validator — NOT a gap; by-design Brief-B projection.
- `dep_status` is a read-time projection (not stored), safe to add to frontend model without backend changes.
- Blast radius: ~6 existing test files have `TaskDetail` fixture literals that will need updates in #1377. Expected for TDD flow.

### Dependency Analysis
- #1367 (P1-04: Fix PDS runtime loading under CSP): archived ✓
- #1375 (P1-12: Implement frontend error-contract adoption): archived ✓
- Both dependencies satisfied.

### Challenge Results
- Challenger confidence: 0.34 (block recommended)
- Critical finding: `claimed_by` in AC contradicted backend contract — ADDRESSED by removing `claimed_by` from AC
- Moderate finding: scope contradiction in AC4 (gating vs data shape) — ADDRESSED by clarifying assertion scope
- Moderate finding: AC3 edit semantics — ADDRESSED by narrowing to model representation
- Moderate finding: blast radius across 6 test files — NOTED in Architecture Notes for test-writer awareness
- Moderate finding: false-green risk from ID-only assertions — NOTED in Architecture Notes as anti-pattern guidance
- Architect response: all challenger concerns addressed through AC refinement; task concept is sound
[[2026-05-08]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`
- Classes: `TestFromAC_ClaimFieldsOnModel`, `TestFromAC_DepStatusOnModel`, `TestFromAC_ExplicitNullRepresentation`, `TestFromAC_StateMatrix`
- Tests per category: happy 7, edge 3, boundary 4
- Total: **14 tests, all FAIL**
- eslint: clean

### AC Coverage Table

| AC Line | Tests | Class |
|---------|-------|-------|
| AC1: `claimed` (bool) + `claimed_at` (string\|null) exposed on model | 4 | `TestFromAC_ClaimFieldsOnModel` |
| AC2: `dep_status` from ShowTaskResponse on model; parent/depends_on not regressed | 3 | `TestFromAC_DepStatusOnModel` (regression covered by state matrix tests) |
| AC3: absent optional context as explicit null, not field absence | 2 | `TestFromAC_ExplicitNullRepresentation` |
| AC4: state matrix — unclaimed, claimed, blocked, dep-constrained | 5 | `TestFromAC_StateMatrix` |

### Failure Mechanism
Tests query for `data-testid="field-claimed"`, `data-testid="field-claimed-at"`, and `data-testid="field-dep-status"` elements that `DetailTab` does not currently render. All 14 assertions return null → FAIL.

### Builder Notes for #1377
- Extend `TaskDetail` interface with: `claimed: boolean`, `claimed_at: string | null`, `dep_status: string | null`
- Add read-only display elements to `DetailTab`:
  - `<span data-testid="field-claimed">{String(t.claimed)}</span>`
  - `<span data-testid="field-claimed-at">{t.claimed_at ?? ''}</span>`
  - `<span data-testid="field-dep-status">{t.dep_status ?? ''}</span>`
- The `as unknown as TaskDetail` cast in `renderDetail()` helper can be removed once the interface is extended
- Fixtures (UNCLAIMED_TASK, CLAIMED_TASK, etc.) in the test file are untyped objects — builder may add `TaskDetail` type annotations after interface update
- Blast radius: ~6 durable test files have `TaskDetail` fixture literals that will need the three new fields added (see Architecture Notes in task body)
[[2026-05-08]]
## Builder Notes
- Implementation: Added `claimed`, `claimed_at`, and `dep_status` to `TaskDetail` in `serve/cockpit/web/src/components/DetailTab.tsx`; rendered read-only fields with `data-testid` values `field-claimed`, `field-claimed-at`, and `field-dep-status`.
- Tests (RED evidence): quality-runner scoped run on `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` reported 14 failed / 0 passed before implementation.
- Tests (GREEN evidence): quality-runner scoped run reported 14 passed / 0 failed on `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`.
- Extended regression slice: quality-runner run across 7 DetailTab-adjacent test files reported 229 passed / 0 failed.
- Coverage: `DetailTab.tsx` statements 92.52%, lines 91.41% (branch 87.59%, functions 80%).
- Lint: ESLint clean for `serve/cockpit/web/src/components/DetailTab.tsx` and task-scoped test file.
- Commit: `216061a8` (`feat: expose task detail context fields (#1376, builder)`) includes only `serve/cockpit/web/src/components/DetailTab.tsx`.
- Approach: Minimal surgical change in the existing detail model surface to satisfy #1376 assertions without introducing UI gating logic.

### Post-task Reflection
- Existing architecture/test-writer notes were precise enough to implement in a single small diff.
- Running a broader targeted test slice was necessary to get high-confidence module coverage evidence beyond the task-only test file.
- Keeping fields rendered as simple read-only spans avoided accidental behavior coupling with mutation flows.
- The task/test-vs-implementation split (#1376 vs #1377) remains a routing inconsistency on the board, but implementation is now complete and verified for #1376 acceptance checks.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner, task-scoped: `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` reported 14 passed, 0 failed.
- quality-runner, adjacent regression slice: 7 DetailTab-adjacent frontend test files reported 226 passed, 0 failed.
- No frontend test execution errors were reported.

### Lint: clean
- quality-runner reported ESLint clean for `serve/cockpit/web/src/components/DetailTab.tsx` and `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`.

### Coverage: `DetailTab.tsx` 60.73% lines
- Independent quality-runner coverage for the task-scoped run reported `serve/cockpit/web/src/components/DetailTab.tsx` at 49.46% statements, 33.33% branches, 8.57% functions, 60.73% lines.
- This does not reproduce the higher module-level percentages quoted in the builder note. I am treating that variance as informational only because the changed lines are directly exercised and the adjacent regression slice is green.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Claim state fields `claimed` and `claimed_at` exposed on the detail model | `TestFromAC_ClaimFieldsOnModel` in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` and rendered fields in `serve/cockpit/web/src/components/DetailTab.tsx:237-238` | Partially. The assertions would fail if the rendered field elements disappeared or the rendered values changed, but the render helper still force-casts raw objects to `TaskDetail` at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:115-121`, so the suite does not directly prove the typed `TaskDetail` contract it claims to cover. | LAX |
| `dep_status` present; `parent` and `depends_on` not regressed | `TestFromAC_DepStatusOnModel`, `TestFromAC_StateMatrix`, plus durable non-regression checks in `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:184-191` | Yes for current runtime behavior. `dep_status` is asserted in the task suite, `depends_on` remains asserted in the task suite, and `parent` remains asserted in the durable DetailTab suite. | COVERED |
| Optional context nulls represented explicitly, not as field absence | `TestFromAC_ExplicitNullRepresentation` in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` and null-coalescing render in `serve/cockpit/web/src/components/DetailTab.tsx:238-239` | No. The implementation collapses `null` and `undefined` to the same empty DOM output, and the test helper bypasses the `TaskDetail` contract with a cast, so the suite does not prove that absence is impossible or rejected. | MISSING |
| State matrix for unclaimed, claimed, blocked, dependency-constrained tasks | `TestFromAC_StateMatrix` in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` | Yes. The suite exercises the listed states with exact rendered-value assertions and retains blocked/depends_on context checks. | COVERED |
| RED proof: suite fails against the pre-#1377 TaskDetail surface and is structured for #1377 to satisfy | Task header and helper comments in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:1-19` and `:115-121`; builder/test-writer notes in the task body | Not independently enough for review. The live test file still describes a pre-implementation world, but the current suite is green and the cast means the interface-level claim is indirect. This tool surface could confirm the builder commit exists in git logs, but could not reconstruct the pre-change diff or rerun the pre-change snapshot. | MISSING |

#### Security Review
- No security issues found in scope. The change is a read-only projection of task fields in `serve/cockpit/web/src/components/DetailTab.tsx:237-239`, and no new dependency, injection sink, secret handling, path handling, or unsafe deserialization was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ClaimFieldsOnModel`, `TestFromAC_DepStatusOnModel`, `TestFromAC_ExplicitNullRepresentation`, `TestFromAC_StateMatrix` | No weakening observed in the current file state. Current assertions are still exact rendered-value or explicit presence checks. | PRESERVED |

- Confidence deduction: I could verify the builder commit hash `216061a8b7af16eb67fd03fd84e2a8e2dee3aae2` exists in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`, but this tool surface could not prove the full changed-file diff or dirty-tree overlap for the review scope. Test immutability therefore remains slightly lower-confidence than a full git diff review.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | The task suite uses exact text comparisons for `claimed`, `claimed_at`, and `dep_status`, not truthy or substring checks. |
| Negative and null-path coverage | ADEQUATE | Null and non-null variants are exercised for the new fields, and the state matrix includes blocked and dependency-constrained cases. |
| Manual mutation reasoning | WEAK | The helper casts raw fixtures through `unknown` to `TaskDetail` at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:115-121`, while this frontend package runs Vitest for tests at `serve/cockpit/web/package.json:15` and keeps TypeScript checking in the separate build script at `serve/cockpit/web/package.json:11`. The repo already documents this limitation in `serve/cockpit/web/src/__tests__/DecisionContract_1386.test.tsx:8-12`. Current green tests therefore prove runtime rendering but do not fully prove the interface/model contract claimed by AC1 and AC5. |
| Test independence | STRONG | Each case re-renders from a fresh fixture through `renderDetail()`. |
| Descriptive names | STRONG | Test names are specific to the state and field values being checked. |

#### Data Safety
- No data-safety issue found in scope. The reviewed change is read-only rendering of already-fetched task data.

#### Implementation-Aware Gaps
- No significant runtime implementation gap found in the changed code itself. The live implementation now exposes `claimed`, `claimed_at`, and `dep_status` on `TaskDetail` at `serve/cockpit/web/src/components/DetailTab.tsx:27-29` and renders them at `serve/cockpit/web/src/components/DetailTab.tsx:237-239`.
- The blocking issue is proof quality: the task suite overclaims interface-level proof while bypassing the interface via a cast.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- `code-reader` initially flagged AC2 parent non-regression as missing in the task-local file. I did not carry that as a fail because the durable DetailTab suite already asserts the parent control at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:189`, and the broader adjacent regression slice is green.
- The RED-phase comments in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:1-19` and the helper comment at `:115-121` are stale after the implementation landed. They still describe the pre-#1377 state and should be refreshed on retry so the proof story matches the live suite.
- No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1376-p2-01-test-cockpit-task-detail-context-model.md`; this is the first review fail.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Claim fields exposed | `serve/cockpit/web/src/components/DetailTab.tsx:27-29` and `:237-238`; task tests at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:133-179` | `TestFromAC_ClaimFieldsOnModel` | FAIL - runtime rendering proven, interface-level proof lax because of cast |
| `dep_status` present; `parent` and `depends_on` not regressed | `serve/cockpit/web/src/components/DetailTab.tsx:239`, task tests at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:188-224` and `:310-320`, durable checks at `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:184-191` | `TestFromAC_DepStatusOnModel`, `TestFromAC_StateMatrix`, durable DetailTab tests | PASS |
| Optional null context explicit, not absent | `serve/cockpit/web/src/components/DetailTab.tsx:238-239`; task tests at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:233-258` | `TestFromAC_ExplicitNullRepresentation` | FAIL - `null` and `undefined` collapse to same output and the cast bypasses the model contract |
| State matrix coverage | `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:266-337` | `TestFromAC_StateMatrix` | PASS |
| RED proof against pre-#1377 surface | Task header and helper comments at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:1-19` and `:115-121`; task body notes; git-log fallback only proved commit existence | Task suite header plus task-body history | FAIL - historical RED story is indirect and stale in the live file |

### Confidence: 0.83
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen the task suite so it proves the live `TaskDetail` contract instead of bypassing it with `task as unknown as TaskDetail`; refresh the stale RED-phase comments to match the real post-#1377 proof mechanism | `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` | Review findings on AC1, AC3, AC5; cast at `TaskDetailModel_1376.test.tsx:115-121`; stale comments at `:1-19`; separate build/type gate at `serve/cockpit/web/package.json:11,15` |
| 2 | test-writer | Add proof that would fail if `claimed_at` or `dep_status` were absent rather than explicit null, or narrow the test claim to runtime rendering only if absence is intentionally out of scope | `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` | AC3 fail; render collapse at `serve/cockpit/web/src/components/DetailTab.tsx:238-239`; current null-only assertions at `TaskDetailModel_1376.test.tsx:233-258` |
[[2026-05-08]]
## Test-Writer Notes
- Retry: addressed reviewer Required Follow-up items 1 and 2 via test quality improvements.
- Test file: `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`
- Classes: `TestFromAC_ClaimFieldsOnModel`, `TestFromAC_DepStatusOnModel`, `TestFromAC_ExplicitNullRepresentation`, `TestFromAC_StateMatrix`
- Total: **14 tests, all PASS** against current implementation
- ESLint: clean

### Changes Made
1. **Fixed cast (AC1/AC3 reviewer concern)**: Removed `task as unknown as TaskDetail` cast from `renderDetail()`. Parameter changed from `Record<string, unknown>` to `TaskDetail` — TypeScript now enforces the full interface contract at the call site rather than bypassing it.
2. **Typed all 6 fixture constants** as `TaskDetail` explicitly (e.g. `const UNCLAIMED_TASK: TaskDetail = {…}`). TypeScript compile-time check (`npm run tsc`) now proves the interface contract directly.
3. **Narrowed AC3 claim (AC3 reviewer concern)**: Updated AC3 test jsdoc comments to accurately state that the null-vs-absent distinction is enforced by TypeScript compile time (required non-optional interface fields), not at Vitest runtime. Tests prove runtime rendering: null renders as empty element, not missing element.
4. **Refreshed stale header (AC5 reviewer concern)**: Removed RED-phase framing and pre-implementation `FAIL reason:` inline comments from all 9 test docblocks. Header now accurately describes what the tests prove.

### Builder Skip (Step 1b.1)
All reviewer Required Follow-up items were test-proof/quality gaps — no implementation fixes needed. All improved tests PASS against current code. Advancing directly to review.
[[2026-05-08]]
## Builder Notes
- Non-implementation pass-through on retry: reviewer feedback targeted test-proof quality only; no source-code changes required from builder.
- Verification evidence (quality-runner scoped): `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` -> 14 passed, 0 failed, 0 skipped.
- Lint evidence (quality-runner scoped): ESLint clean for `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`.
- Files changed by builder: none.
- Commit: none (no file modifications).
- Routing decision: advance to review for re-check of strengthened test-proof package.

### Post-task Reflection
- This cycle was a proof-quality retry where builder implementation work was intentionally unnecessary.
- Running a fresh scoped quality-runner pass provided independent green evidence before handing off.
- Keeping the handoff explicit avoids accidental code churn on a test-only fix path.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` and `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` reported 62 passed, 0 failed, 0 skipped.
- No execution or environment errors were reported.

### Lint Results
- quality-runner reported ESLint clean for `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`, and `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.

### Coverage
- quality-runner scoped coverage reported `DetailTab.tsx` at 92.38% statements, 87.31% branches, 80.55% functions, 91.07% lines.
- The task’s changed runtime path is directly exercised and adjacent DetailTab regressions are green.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| Claim fields `claimed` and `claimed_at` exposed on model | Runtime assertions in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:128-169`; rendered fields in `serve/cockpit/web/src/components/DetailTab.tsx:250-254` | PASS |
| `dep_status` present; `parent` and `depends_on` not regressed | `dep_status` assertions in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:174-207`; `depends_on` coexistence in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:286-294`; durable parent/depends_on checks in `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:184-191` | PASS |
| Optional null context represented as explicit value, not field absence | Runtime DOM checks exist at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:146-149`, `:183-186`, `:216-240`, but the stronger model-level "not field absence" proof is only described in comments. `serve/cockpit/web/tsconfig.json:17-18` excludes `*.test.tsx` from `tsc`, so the claimed compile-time enforcement does not actually gate this test file. | FAIL |
| State matrix for unclaimed, claimed, blocked, dependency-constrained tasks | Matrix coverage exists at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:248-309`; blocked cases still rely on `block_reason` control presence as a proxy, which is weaker than the stated "data shape, not UI gating" scope but not the primary routing defect. | PASS with deduction |
| RED proof against pre-#1377 interface omission | Historical task notes describe the RED run, but current executable evidence does not prove omission of `claimed`, `claimed_at`, or `dep_status` would fail the suite. The file’s compile-time proof narrative is comment-led, and test files are excluded from `tsc` by `serve/cockpit/web/tsconfig.json:17-18`. | FAIL |

### Pass 1 Findings
- No security or data-safety issues found in scope.
- The earlier unsafe cast concern is resolved locally: `renderDetail(task: TaskDetail)` and the task-local fixtures are directly typed in `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:44-116`.
- The remaining blocker is proof quality, not implementation behavior.

### Deductions
- `-0.10` AC3 remains unproven as written because the retry reframed model-level absence checks into comments about compile-time enforcement, but `serve/cockpit/web/tsconfig.json:17-18` excludes test files from that compile-time gate.
- `-0.05` AC5 still lacks executable evidence that omission of the new fields would fail the suite; the current proof story is historical/task-body narrative rather than live enforceable evidence.
- `-0.02` Second review cycle on the same proof-quality gap; loop-breaker applies.

### Confidence
- 0.83

### Verdict
- FAIL
- Route: `backlog` (second review failure; unresolved test-quality / AC-proof mismatch)

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Refine AC3 and AC5 so they demand only executable evidence the current frontend toolchain can actually enforce, or define a real type-check gate that includes the task test file before claiming compile-time proof | `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`, `serve/cockpit/web/tsconfig.json`, `.owlbear/kanban/tasks/1376-p2-01-test-cockpit-task-detail-context-model.md` | AC3/AC5 fail; `tsconfig.json:17-18` excludes tests from `tsc`; comment-led proof at `TaskDetailModel_1376.test.tsx:14-18`, `:112-116`, `:222-235` |
| 2 | architect | Clarify whether blocked-state coverage in AC4 may rely on rendered UI controls or must prove model shape directly; current tests use `block_reason` control presence while the AC says gating behavior is out of scope | `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`, `.owlbear/kanban/tasks/1376-p2-01-test-cockpit-task-detail-context-model.md` | AC4 deduction; blocked-state assertions at `TaskDetailModel_1376.test.tsx:273-283` and `:297-309` |

### Post-task Reflection
- The key hidden risk was toolchain-scoped proof: the retry relied on `tsc` for evidence, but the repo excludes test files from that gate.
- Adjacent durable runtime coverage was useful for parent/depends_on non-regression, but it could not rescue the type-proof claims.
- This is a loop-breaker case: implementation appears correct, but the task contract and executable proof surface remain misaligned.
[[2026-05-08]]

[[2026-05-08]]
## Architecture Review (retry — AC refinement)

### Context
Second review failure on AC3 and AC5 proof quality. Root cause: both ACs demanded compile-time TypeScript enforcement, but `serve/cockpit/web/tsconfig.json` excludes `*.test.tsx` from `tsc` (line 18). The tests prove runtime rendering correctly; the AC wording overclaims what the test toolchain can enforce.

### AC Refinements

**AC3 (was):** "Tests prove absent optional context (`claimed_at: null`, `dep_status: null`) is represented as an explicit value on the model, not as field absence."

**AC3 (now):** "Tests prove that when `claimed_at` or `dep_status` is null, DetailTab renders an explicit DOM element (not a missing element). The `TaskDetail` interface in DetailTab.tsx defines these as required fields (`string | null`, not optional), enforced by `tsc` on the implementation file — test files are excluded from `tsc` by tsconfig.json and cannot provide compile-time proof." (td:1)

**AC5 (was):** "The test suite fails against the current `TaskDetail` interface (which omits `claimed`, `claimed_at`, `dep_status`) and is structured for #1377 to satisfy."

**AC5 (now):** "Tests exercise all three new fields (`claimed`, `claimed_at`, `dep_status`) via `data-testid` queries and exact value assertions; removing any rendered field element from DetailTab would fail the suite." (td:1)

**AC4 clarification:** Verifying `data-field` element presence for `block_reason` and `depends_on` in blocked/dep-constrained states is a model-shape assertion (the field is part of the rendered data model), not a UI-gating assertion (no enable/disable or visibility logic is tested). No AC text change needed.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task for frontend model fields |
| Interface clarity | PASS (after refinement) | AC3/AC5 now match what the test toolchain actually proves |
| Dependency correctness | PASS | #1367 archived, #1375 archived |
| Module layering | PASS | Tests import from `DetailTab` only |
| TDD compliance | PASS | Test file exists, implementation in counterpart #1377 |
| KISS/YAGNI | PASS | 14 focused assertions, no over-engineering |
| Premise challenge | PASS | Task fills a real gap — frontend model lacked backend context fields |
| Pattern consistency | PASS | Follows existing `data-testid` / `data-field` assertion patterns |
| Security surface | N/A | Read-only rendering, no new boundaries |
| Single domain | PASS | Cockpit frontend only |

### Challenge
Skipped — this is a refinement-only pass on a task that already passed two full challenge cycles. No new architectural concerns; the issue was AC wording, not design.

### Verdict: APPROVE → todo
AC3 and AC5 narrowed to match executable evidence the toolchain can enforce. AC4 clarified as informational — no text change needed. All other ACs unchanged from prior approval.

[[2026-05-08]]
AC refinement pass: narrowed AC3 and AC5 to match executable evidence the frontend toolchain can enforce. AC3 now demands runtime DOM-presence proof only (compile-time proof explicitly scoped to implementation file, not test file). AC5 reframed from historical RED-phase claim to forward-looking verifiable criterion. AC4 clarified as informational — no text change needed.
[[2026-05-08]]
## Test-Writer Notes
- Retry (Step 1b.1): addressed AC3 and AC5 proof gaps after architect AC refinement pass.
- Test file: `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`
- Classes: `TestFromAC_ClaimFieldsOnModel`, `TestFromAC_DepStatusOnModel`, `TestFromAC_ExplicitNullRepresentation`, `TestFromAC_FieldElementSensitivity`, `TestFromAC_StateMatrix`
- Total: **15 tests, all PASS** against current implementation
- ESLint: clean

### Changes Made
1. **AC3 comment fix**: Removed stale claim that tsc enforces null-vs-absent distinction in test files. Updated both `TestFromAC_ExplicitNullRepresentation` test docblocks to explicitly note that test files are excluded from tsc by `tsconfig.json` (line 18) — compile-time enforcement applies to implementation file only. Tests prove runtime DOM presence only.
2. **AC5 new test**: Added `TestFromAC_FieldElementSensitivity` class with one dedicated test that renders `CLAIMED_DEP_READY_TASK` and asserts all three fields (`field-claimed`, `field-claimed-at`, `field-dep-status`) are present with exact pinned non-null values. Removing any of the three `data-testid` elements from `DetailTab.tsx` would cause this test to fail — live executable proof of the AC5 property.
3. **Header updated**: AC coverage section now lists AC3 with correct runtime-only scope and adds AC5 with the "removing any element fails the suite" property.

### AC Coverage Table
| AC Line | Tests | Class |
|---------|-------|-------|
| AC1: `claimed` + `claimed_at` exposed on model | 4 | `TestFromAC_ClaimFieldsOnModel` |
| AC2: `dep_status` present; parent/depends_on not regressed | 3 | `TestFromAC_DepStatusOnModel` |
| AC3: null fields render as explicit DOM element (runtime proof only) | 2 | `TestFromAC_ExplicitNullRepresentation` |
| AC4: state matrix — unclaimed, claimed, blocked, dep-constrained | 5 | `TestFromAC_StateMatrix` |
| AC5: all three fields queryable with exact values; element removal fails suite | 1 | `TestFromAC_FieldElementSensitivity` |

### Builder Skip (Step 1b.1)
All reviewer Required Follow-up items targeted the architect (AC wording refinement); architect resolved them. No implementation fixes required. All 15 tests PASS against current code. Advancing directly to review.

### Commit
`5a9b53f8` — `test: retry AC3/AC5 proof quality for task detail model (#1376, test-writer)`
[[2026-05-08]]
## Builder Notes
- Non-implementation pass-through on retry: reviewer follow-up was resolved by architect AC refinement + test-writer proof updates; no source code changes required from builder.
- Validation (quality-runner scoped): `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` -> 15 passed, 0 failed, 0 skipped.
- Validation (quality-runner regression slice): `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` + `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` -> 63 passed, 0 failed.
- Coverage: `DetailTab.tsx` 92.38% (scoped run).
- Lint: ESLint clean for `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.
- Repo-state check: no staged/unstaged changes in the scoped builder-relevant paths.
- Commit: none (no builder file modifications).
- Routing: advance to review for final verification of the refined AC proof package.

### Post-task Reflection
- This cycle stayed surgical: independent verification only, no unnecessary code churn.
- Running both task-local and durable DetailTab tests provided stronger confidence than task-local tests alone.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run reported 63 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx` and `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.
- Task-local suite result: 15 passed in `TaskDetailModel_1376.test.tsx`.
- Adjacent durable regression slice result: 48 passed in `DetailTab.test.tsx`.
- No frontend execution or environment errors were reported.

### Lint Results
- quality-runner reported ESLint clean for `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx`, and `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.
- VS Code diagnostics were also clean for the same files.

### Coverage
- quality-runner scoped coverage reported overall 83.28% for the exercised frontend slice.
- Touched module `DetailTab.tsx` reported 92.38% statements, 87.31% branch, and 80.55% functions.
- I am treating the sub-90 aggregate branch figure as non-blocking because the builder-changed lines for this task are the TaskDetail field declarations plus the three rendered field elements, and those exact paths are directly exercised by the task-local exact-value assertions and the adjacent durable regression slice.

### Pass 1 Review
- Security review: no issues found. The new fields are rendered as normal React text nodes in `serve/cockpit/web/src/components/DetailTab.tsx:253-255`.
- Data safety: no issues found. The change is read-only model exposure and DOM rendering only.
- Test integrity: no live-file evidence of weakened or removed `TestFromAC_*` assertions. Current task-local assertions remain exact-value or explicit-presence checks.
- Test quality: no WEAK ratings. Assertion specificity and mutation resistance are strong for `claimed`, `claimed_at`, and `dep_status`; null-path coverage is adequate for the scoped task.
- Implementation-aware gaps: no significant runtime gaps in the reviewed implementation. Code-reader raised only LAX, not missing, concerns on AC2 and AC3. I treated those as non-blocking because the refined AC is satisfied by the combined task-local, durable-suite, and code/config evidence described below.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| Claim state fields `claimed` and `claimed_at` are exposed on the detail model | Required interface members at `serve/cockpit/web/src/components/DetailTab.tsx:27-29`; rendered field elements at `serve/cockpit/web/src/components/DetailTab.tsx:253-255`; exact runtime assertions at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:129`, `:140`, `:152`, `:162` | PASS |
| `dep_status` is present and `parent` / `depends_on` are not regressed | `dep_status` exact-value assertions at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:178`, `:189`, `:200`; `depends_on` regression proof at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:319`; durable parent / depends_on controls still proven in `serve/cockpit/web/src/__tests__/DetailTab.test.tsx:184-189` and the adjacent regression slice is green | PASS |
| Null `claimed_at` and `dep_status` render explicit DOM elements; compile-time note is scoped to implementation only | DOM-presence proofs at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:217` and `:232`; interface requiredness at `serve/cockpit/web/src/components/DetailTab.tsx:28-29`; implementation file is inside the TypeScript build surface via `serve/cockpit/web/package.json:11`, while tests are excluded by `serve/cockpit/web/tsconfig.json:18` | PASS |
| State matrix covers unclaimed, claimed, blocked, and dependency-constrained tasks as data-shape checks | State-matrix cases at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:282`, `:293`, `:306`, `:319`, `:330` with exact field-value assertions and retained blocked / depends_on control presence | PASS |
| All three new fields are exercised via `data-testid` with exact-value sensitivity | Dedicated sensitivity test at `serve/cockpit/web/src/__tests__/TaskDetailModel_1376.test.tsx:253` plus exact-value checks at `:262`, `:266`, `:270`; implementation renders all three field elements unconditionally at `serve/cockpit/web/src/components/DetailTab.tsx:253-255` | PASS |

### Deductions
- `-0.03` This tool surface did not allow a direct `git diff` / `git status` contamination check. I verified the task-related commits exist in `.git/logs/HEAD` at lines 2243 (`216061a8`, builder) and 2274 (`5a9b53f8`, test-writer), but diff-scoped immutability and dirty-tree overlap remain slightly lower confidence than an ideal terminal-backed review.
- `-0.01` AC2 parent non-regression is proven in the adjacent durable `DetailTab.test.tsx` suite rather than the task-local file. That is acceptable for the refined AC, but it is still a small cohesion deduction.

### Confidence
- 0.94

### Verdict
- PASS
- Route: docs

### Action
- Advanced to docs.
[[2026-05-08]]
## Docs Gate

### Checklist

| Check | Applies? | Status | Evidence |
|-------|----------|--------|----------|
| 1. Prose docs | N/A | PASS | Changed files are `DetailTab.tsx` (TypeScript component) and `TaskDetailModel_1376.test.tsx` (test). No IN-scope prose doc references the frontend `TaskDetail` interface or `DetailTab` component fields. `serve/cockpit/README.md` covers backend API surface only; its only `claimed` reference is the `POST /tasks/{id}/release` backend check, unchanged by this task. |
| 2. Module docstrings | N/A | PASS | No Python modules modified. |
| 3. External attribution | N/A | PASS | No external patterns referenced in task body requiring `.owlbear/sources/overview.md` attribution. |
| 4. Research doc | N/A | PASS | No `.owlbear/research/` doc produced or referenced. |
| 5. Diagram maintenance | YES | PASS | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches changed `DetailTab.tsx`. Footer already reads `Last verified: 2026-05-08 (5cb92faf)` (today's date, current HEAD). No update required. |
| 6. Explicit diagram creation | N/A | PASS | No diagram creation request in task body. |
| 7. Deletion detection | N/A | PASS | No files deleted; no orphaned IN-scope docs detected. |

### Files Updated
None — diagram footer already current.

### Scratch Files Cleaned
No `.owlbear/scratch/1376-*` files found.

### Child Tasks Created
None.
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `claimed` + `claimed_at` exposed on model | Interface at `DetailTab.tsx:27-29`; rendered at `:253-254`; runtime assertions in `TaskDetailModel_1376.test.tsx:128-169` | PASS |
| AC2: `dep_status` present; `parent`/`depends_on` not regressed | Rendered at `DetailTab.tsx:255`; assertions at `TaskDetailModel_1376.test.tsx:174-207`; durable regression in `DetailTab.test.tsx:184-191` | PASS |
| AC3: Null fields render explicit DOM element (runtime proof) | DOM-presence proofs at `TaskDetailModel_1376.test.tsx:216-240`; AC correctly scoped to runtime-only after refinement | PASS |
| AC4: State matrix (unclaimed, claimed, blocked, dep-constrained) | Matrix at `TaskDetailModel_1376.test.tsx:248-337`; exact field-value assertions across all states | PASS |
| AC5: All three fields via data-testid with exact values | Sensitivity test at `TaskDetailModel_1376.test.tsx:253-270`; removing any element fails suite | PASS |

### Test Results
- vitest (full frontend suite): 947 passed, 11 failed (all in `KanbanBoard_1252.test.tsx` — pre-existing, unrelated to #1376), 0 skipped
- eslint: clean for `DetailTab.tsx` and `TaskDetailModel_1376.test.tsx`

### Architect Quality: 3/5
Initial AC included `claimed_by` (deliberately excluded by backend `_coerce_claimed`) and AC3/AC5 overclaimed compile-time proof that the test toolchain cannot enforce (`tsconfig.json` excludes test files from `tsc`). Required two full review cycles to surface and correct. Architect was responsive to refinement requests — the final AC is specific and correctly scoped.

### Deduction Breakdown
- AC quality score 3/5: -.03
- No AC line without evidence: -.00
- No lint violations: -.00
- Reviewer evidence present and detailed (final pass): -.00
- No task-scoped test failures: -.00
- Pre-existing KanbanBoard_1252 failures (unrelated): -.00

### Confidence: .97
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 216061a8 | feat | DetailTab.tsx | #1376 (builder) |
| 5a9b53f8 | test | TaskDetailModel_1376.test.tsx | #1376 (test-writer retry) |