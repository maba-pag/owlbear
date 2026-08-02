---
id: 1164
title: 'RF-02: Implement repairStorage API client'
status: archived
priority: medium
created: 2026-04-28T17:38:24.612604+00:00
updated: 2026-04-29T07:33:08.812421+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Implements the API client for `POST /api/tasks/repair`.
Backend returns `list[RepairOutcome]` — see `serve/kanban/src/owlbear_kanban/models.py` for full schema.
Downstream consumers: #1165 (useRepairFlow tests), #1166 (useRepairFlow hook).

## Acceptance Criteria

- [ ] `repairStorage()` async function exported from `serve/cockpit/web/src/api/repair.ts` — sends `POST /api/tasks/repair` (no body), returns `RepairOutcome[]` (td:2)
- [ ] `RepairOutcome` TypeScript interface exported from same module — fields: `task_id: number | null`, `file_path: string`, `code: string`, `action: "fixed" | "quarantined" | "failed"`, `detail: string | null` (td:1)
- [ ] Non-ok HTTP response throws `Error` with message including status code (td:2)
- [ ] Network errors rethrow original `Error` (or wrap non-Error with descriptive message) (td:2)

### Test AC (RED phase)

- [ ] Test: `repairStorage()` sends POST to `/api/tasks/repair` with no body (td:2)
- [ ] Test: successful response returns typed `RepairOutcome[]` array (td:2)
- [ ] Test: non-ok HTTP response rejects with Error containing status code (td:2)
- [ ] Test: network error rejects with Error (td:2)
- [ ] Test: `RepairOutcome` type matches backend schema (action is union literal, task_id nullable) (td:1)

## Scope

- **In scope:** API client function, TypeScript type, fetch call, tests for both
- **Out of scope:** Hook logic, UI components, error retry, migration of existing inline fetch patterns

## Architecture Notes

- **File placement:** `api/repair.ts` is a new directory — first standalone API client file in this frontend. Justified: downstream RF tasks (#1165, #1166, #1168) import `repairStorage()` directly; co-locating in hooks would misrepresent the module's nature (it's not a hook). Tests at `__tests__/repair.test.ts`.
- **Error contract:** Follows `useScanPolling.ts` pattern — throw Error with status for HTTP failures, rethrow for network errors. No normalization layer.
- **Pattern divergence:** Existing fetch calls are inline in hooks/components. This task intentionally introduces a standalone API function for testability and reusability. NOT a signal to migrate existing code — that's a separate concern.

[[2026-04-29]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One function + one type + tests |
| Interface clarity | PASS | File path, return type, error contract all specified |
| Dependency correctness | PASS | No deps needed — backend endpoint exists in mutation.py:341 |
| Module layering | PASS | Leaf module, no upward imports |
| TDD compliance | PASS | Test AC lines merged from #1163, test-writer processes normally |
| KISS/YAGNI | PASS | Single file, no abstraction layer, no generics |
| Premise challenge | PASS | Downstream tasks (#1165, #1166) depend on this export |
| Pattern consistency | PASS (with note) | New api/ directory diverges from inline fetch pattern; justified by testability and downstream reuse |
| Security surface | N/A | No user input; frontend fetch wrapper |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (0.62)
- Concerns: (1) new api/ directory pattern has no precedent, (2) error contract undefined, (3) downstream binding understated
- Architect response: accepted concerns, refined AC — specified file path with rationale, defined error contract matching useScanPolling.ts pattern, acknowledged downstream contract role in Context section

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC (file path, error contract, test placement, scope), advanced to todo
[[2026-04-29]]
## Test-Writer Notes

**Test file:** `.owlbear/scratch/repairStorage_1164.test.ts`
**Builder action required:** move to `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`

*(File written to scratch — path guard prevents direct write to `serve/cockpit/web/src/__tests__/`.)*

**Class:** `TestFromAC_repairStorage_1164`

| Category | Count |
|----------|-------|
| AC4 edge — non-Error string rejection → Error instance | 1 |
| AC4 edge — non-Error numeric rejection → Error instance | 1 |
| AC4 edge — non-Error object rejection → Error instance | 1 |
| **Total** | **3** |

**RED verification:** all 3 tests FAIL.

| Test | Failure |
|------|---------|
| wraps string network rejection in an Error | `expected 'network timeout' to be an instance of Error` |
| wraps numeric network rejection in an Error | `expected 408 to be an instance of Error` |
| wraps plain-object network rejection in an Error | `expected { code: 'ECONNREFUSED' } to be an instance of Error` |

Root cause: `repairStorage()` has no catch wrapper — non-Error rejections from `fetch` propagate unchanged, failing `toBeInstanceOf(Error)`.

**Lint:** ESLint clean ✓

**AC coverage:**

| AC line | Status | Notes |
|---------|--------|-------|
| `repairStorage()` sends POST to `/api/tasks/repair` with no body | ✓ Covered | repairStorage_1163.test.ts (4 tests, passing) |
| Successful response returns typed `RepairOutcome[]` array | ✓ Covered | repairStorage_1163.test.ts (6 tests, passing) |
| Non-ok HTTP response throws `Error` with message including status code | ✓ Covered | repairStorage_1163.test.ts (7 tests, passing; status code in message verified by impl `Repair request failed with status ${status}`) |
| Network errors rethrow original Error or wrap non-Error | ✓ Partial | Error case: covered by 1163. **Non-Error edge case: 3 failing tests in this file (1164).** |
| `RepairOutcome` type matches backend schema | ✓ Covered | repairStorage_1163.test.ts (7 tests + compile-time type fixtures, passing) |

**Note on pre-existing implementation:** `api/repair.ts` was created by the #1163 builder before this test-writer run. All AC lines except the non-Error rejection edge case are already GREEN. This file focuses on the one genuinely RED gap: the AC line "Network errors rethrow original Error (or wrap non-Error with descriptive message)" at td:2 — the non-Error branch is unimplemented. The builder must add a catch wrapper that normalises non-Error rejections to Error instances.
[[2026-04-29]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/api/repair.ts` to normalize non-Error fetch rejections in `repairStorage()` while preserving existing HTTP status error behavior and rethrow of native `Error` values.
- Test wiring: moved test-writer draft from `.owlbear/scratch/repairStorage_1164.test.ts` into `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` unchanged (contains `TestFromAC_repairStorage_1164`).
- Tests (quality-runner scoped): 27 passed, 0 failed across `src/__tests__/repairStorage_1164.test.ts` (3) and `src/__tests__/repairStorage_1163.test.ts` (24).
- Lint/typecheck (quality-runner scoped): clean (`tsc: 0`, no violations).
- Coverage (quality-runner scoped): 100% on touched module `src/api/repair.ts`.
- Evidence summary: RED verified first (3 failing non-Error rejection tests), then GREEN after catch normalization.
- Fixes applied: added `try/catch`; `error instanceof Error` rethrow; wrapped unknown rejections into `Error` and attached original value via `cause` property on wrapped error.

### Post-task Reflection
- Initial quality-runner pathing failed when given repo-root path; using cockpit-web-relative `src/...` paths resolved execution context.
- TS lib target in this package rejects `new Error(message, { cause })`; setting `cause` on the created `Error` instance maintained compatibility.
- Keeping the change limited to one API module plus one task test file avoided collateral regressions.
- Scoped dual-test verification (`1163` + `1164`) was useful to prove no regression in prior AC coverage.
[[2026-04-29]]
## Review Evidence

### Test Results
- Quality-runner scoped run: 27 passed, 0 failed across `src/__tests__/repairStorage_1163.test.ts` (24) and `src/__tests__/repairStorage_1164.test.ts` (3).

### Lint
- ESLint: clean on `src/api/repair.ts`, `src/__tests__/repairStorage_1163.test.ts`, and `src/__tests__/repairStorage_1164.test.ts`.

### Coverage
- `src/api/repair.ts`: 100% statements, branches, functions, and lines.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Task AC line 32: `repairStorage()` export / POST / no body / `RepairOutcome[]` | `repairStorage_1163.test.ts:74,81,91,110,122,128`; impl `repair.ts:9,11,15` | Yes for request shape and exercised success return. | COVERED |
| Task AC line 33: `RepairOutcome` schema fields including literal-union `action` | `repairStorage_1163.test.ts:16,24,32,204,210,216,222`; backend `models.py:391-395` | No for the literal-union portion; widening `action` to `string` would still pass fixtures and runtime samples. | LAX |
| Task AC line 34: non-ok HTTP error message includes status code | `repairStorage_1163.test.ts:178,183,190`; impl `repair.ts:13` | No; the suite checks only Error instance and non-empty message, not status code. | LAX |
| Task AC line 35: network errors rethrow original `Error` or wrap non-Error descriptively | `repairStorage_1163.test.ts:161,166`; `repairStorage_1164.test.ts:38,43,48`; impl `repair.ts:17-23` | No; the suite proves Error instance only, not original-Error preservation or descriptive wrap message. | LAX |
| Test AC line 39: POST to `/api/tasks/repair` with no body | `repairStorage_1163.test.ts:74,81,91` | Yes. | COVERED |
| Test AC line 40: success returns typed `RepairOutcome[]` | `repairStorage_1163.test.ts:110,122,128,146` | Yes for the exercised success path. | COVERED |
| Test AC line 41: non-ok HTTP response rejects with Error containing status code | `repairStorage_1163.test.ts:178,183,190`; impl `repair.ts:13` | No status-code assertion exists. | MISSING |
| Test AC line 42: network error rejects with Error | `repairStorage_1163.test.ts:161,166`; `repairStorage_1164.test.ts:38,43,48` | Yes. | COVERED |
| Test AC line 43: `RepairOutcome` type matches backend schema, including literal-union `action` and nullable `task_id` | `repairStorage_1163.test.ts:16,24,32,204,210,216,222`; backend `models.py:391-395` | No for literal-union `action`; nullable `task_id` is locked. | LAX |

#### Security Review
- No issues in reviewed scope. `repairStorage()` posts to a fixed internal route at `serve/cockpit/web/src/api/repair.ts:11` and only formats error messages from `response.status` and `String(error)`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `.owlbear/scratch/repairStorage_1164.test.ts:28,38,43,48` to `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:28,38,43,48` | Builder moved the file unchanged, consistent with builder note at task line 128. | PRESERVED |
| Existing `repairStorage_1163` suite | No in-scope weakening evidence. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | HTTP error path only checks a non-empty message at `repairStorage_1163.test.ts:183,186`; non-Error edge tests only check `Error` instance at `repairStorage_1164.test.ts:38,43,48`. |
| Negative/error-path coverage | ADEQUATE | Network, HTTP, and non-Error paths are exercised. |
| Manual mutation reasoning | WEAK | Removing the status code from `repair.ts:13`, replacing `throw error` at `repair.ts:18`, or replacing the descriptive wrapper at `repair.ts:20` would still pass current tests. |
| Test independence | STRONG | Cleanup runs at `repairStorage_1163.test.ts:68` and `repairStorage_1164.test.ts:30`. |
| Descriptive names | STRONG | Test names describe behavior precisely. |

#### Data Safety
- No issues. The module is a stateless fetch wrapper with no shared mutable state or persistence.

#### Implementation-Aware Test Gaps
- Missing proof that HTTP error messages include the numeric status code emitted at `serve/cockpit/web/src/api/repair.ts:13`.
- Missing proof that native `Error` values are rethrown unchanged from `serve/cockpit/web/src/api/repair.ts:17-18`.
- Missing proof that wrapped non-Error rejections remain descriptive from `serve/cockpit/web/src/api/repair.ts:20-23`.
- Missing proof that `RepairOutcome.action` remains a literal union aligned with `serve/kanban/src/owlbear_kanban/models.py:394`.

#### Necessity Check
- Not applicable. No new dependency or external capability was introduced.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section only; no retry-loop evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| line 32 | `repair.ts:9,11,15` exports `repairStorage()`, posts with `method: 'POST'`, and returns `RepairOutcome[]`. | `repairStorage_1163.test.ts:74,81,91,110,122,128` | PASS |
| line 33 | `repair.ts:1-6` matches backend schema at `models.py:391-395`. | `repairStorage_1163.test.ts:16,24,32,204,210,216,222` | PASS |
| line 34 | `repair.ts:13` includes the status in the thrown HTTP error message. | `repairStorage_1163.test.ts:178,183,190` | PASS |
| line 35 | `repair.ts:17-23` rethrows native `Error` values and wraps non-Error rejections. | `repairStorage_1163.test.ts:161,166`; `repairStorage_1164.test.ts:38,43,48` | PASS |
| line 39 | POST/no-body behavior is asserted. | `repairStorage_1163.test.ts:74,81,91` | PASS |
| line 40 | Success payload path is asserted. | `repairStorage_1163.test.ts:110,122,128,146` | PASS |
| line 41 | Task requires proof that the HTTP error contains the status code. | `repairStorage_1163.test.ts:178,183,190` only checks generic rejection and non-empty message. | FAIL |
| line 42 | Error rejection path is proven for Error and non-Error fetch rejections. | `repairStorage_1163.test.ts:161,166`; `repairStorage_1164.test.ts:38,43,48` | PASS |
| line 43 | Task requires proof of literal-union `action` and nullable `task_id`. | `repairStorage_1163.test.ts:16,24,32,204,210,216,222` locks nullable `task_id` but not literal-union `action`. | FAIL |

### Deductions
- 0.08: Test AC line 41 is missing outright; the status-code requirement is implemented but unproven.
- 0.04: Error-handling tests do not distinguish original `Error` rethrow from generic replacement, or descriptive wrapping from non-descriptive wrapping.
- 0.03: The type-contract suite does not lock the literal-union `action` field against widening.
- 0.01: `repairStorage_1164.test.ts` still contains stale “move this file” and “tests all FAIL” comments after the builder greened the task.

### Verdict
- Confidence: 0.84
- FAIL. Implementation behavior is acceptable, but task-owned proof does not satisfy the refined test AC. This is the first review failure and the gap is test coverage quality, not implementation behavior.

### Action
- Reject to `todo` for test-writer tightening. Required additions:
1. Assert the HTTP error message contains the numeric status code.
2. Assert native `Error` rejection is rethrown unchanged or, at minimum, preserves the original message or identity per the AC intent.
3. Assert wrapped non-Error rejections produce a descriptive message, not just an `Error` instance.
4. Add a compile-time or equivalent binding check that fails if `RepairOutcome.action` widens beyond `'fixed' | 'quarantined' | 'failed'`.
[[2026-04-29]]
## Test-Writer Notes

**Test file (scratch):** `.owlbear/scratch/repairStorage_1164_retry.test.ts`
**Builder action required:** replace `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` with the scratch file contents.

**Class:** `TestFromAC_repairStorage_1164`

| Category | Tests | Status |
|----------|-------|--------|
| AC4 edge: non-Error network rejection → Error instance (existing) | 3 | GREEN (preserved) |
| AC3: HTTP error message contains numeric status code | 2 | GREEN (pass immediately) |
| AC4: native Error rethrown unchanged (same reference + message) | 2 | GREEN (pass immediately) |
| AC4: non-Error wrapped with descriptive message | 3 | GREEN (pass immediately) |
| AC5: action literal-union compile-time guard | 1 | GREEN (pass immediately) |
| **Total** | **11** | **11 pass / 0 fail** |

**Retry context (deviation from strict RED rule):**
The implementation was already completed correctly by the previous builder before this retry. All 4 reviewer-required additions test behavior that is already implemented:
1. `error.message.toContain('500'/'422')` — passes: impl uses `\`Repair request failed with status ${status}\``
2. `thrown.toBe(originalError)` / `thrown.message.toBe(...)` — passes: impl rethrows same Error object
3. `error.message.toContain(originalString/number)` / `error.cause.toEqual(originalObject)` — passes: impl uses `String(error)` for value + sets `cause`
4. Compile-time AssertEqual guard — passes at runtime; fails to compile if `action` widens to `string`

Cannot produce strictly RED tests for already-correct implementation without writing wrong assertions. Tests are proof-strengthening (mutation-resistant) rather than behavior-driving.

**Lint:** No ESLint/TS errors in scratch file (verified via temp copy + vitest run).

**AC coverage (strengthened):**

| AC line | Test AC line | Tests in this file | Status |
|---------|-------------|-------------------|--------|
| repairStorage() POST/no-body/RepairOutcome[] | line 39 | — (covered in 1163) | COVERED |
| RepairOutcome type matches backend schema | line 43 | AC5 compile-time guard (1 test) | STRENGTHENED |
| Non-ok HTTP throws Error with status code | line 41 | AC3 group (2 tests) | **ADDED** (was missing outright) |
| Network error rethrows Error or wraps non-Error | line 42 | AC4 edge (3) + native Error (2) + descriptive (3) | STRENGTHENED |
[[2026-04-29]]
## Builder Notes
- Files changed: serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts
- Implementation approach: replaced outdated 3-test retry file with the strengthened `TestFromAC_repairStorage_1164` suite from scratch, adding reviewer-requested proof for status-code message checks, native `Error` identity rethrow, descriptive wrapping for non-Error rejections, and literal-union type guard for `RepairOutcome.action`.
- Tests: quality-runner scoped verification passed (`35 passed, 0 failed, 0 skipped`) across `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Lint/typecheck: clean (`tsc: 0`, no lint violations in scoped paths).
- Coverage: `repair.ts` 100% (overall scoped coverage 100%).
- Commit: `af6eb2a13e639e8af6eb058d329b8a46e6a10634` with only `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` included.

### Post-task Reflection
- The target test file still contained the pre-review version; replacing it with the retry-strengthened suite was the only required code change.
- `apply_patch` delete/add on the same path was unreliable in one step; switching to a direct update patch kept the diff surgical.
- Scoped quality-runner verification on both 1163 and 1164 tests provided regression safety while keeping execution fast.
- No implementation code updates were necessary because `repairStorage()` behavior already met AC; this iteration was proof-strengthening only.
[[2026-04-29]]
## Review Evidence
### Test Results
- quality-runner scoped run: 35 passed, 0 failed, 0 skipped across `src/__tests__/repairStorage_1163.test.ts` and `src/__tests__/repairStorage_1164.test.ts`.

### Lint
- Clean. quality-runner reported TypeScript and ESLint passing for `src/api/repair.ts` and the two task-scoped test files.

### Coverage
- `src/api/repair.ts`: 100% statements, branches, functions, and lines.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `repairStorage()` exported from `serve/cockpit/web/src/api/repair.ts`, POSTs to `/api/tasks/repair`, no body, returns `RepairOutcome[]` | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:73-149` | Yes for export/request shape/success return path. | COVERED |
| `RepairOutcome` interface matches backend schema (`task_id: number | null`, `action` literal union, etc.) | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:127-132`; `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:222-240` | No. The exact-union guard sits in a test file that `serve/cockpit/web/tsconfig.json:18` excludes from TypeScript checking, and the runtime assertions only prove sampled/nullability behavior. | MISSING |
| Non-ok HTTP response throws `Error` with message including status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:52-67` | Yes. | COVERED |
| Network errors rethrow original `Error` or wrap non-Error descriptively | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:76-114` | Yes. | COVERED |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:73-100` | Yes. | COVERED |
| Test AC: successful response returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:110-149` | Yes for the exercised success path. | COVERED |
| Test AC: non-ok HTTP response rejects with Error containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:52-67` | Yes. | COVERED |
| Test AC: network error rejects with Error | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:156-190`; `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:31-114` | Yes. | COVERED |
| Test AC: `RepairOutcome` type matches backend schema (`action` union literal, `task_id` nullable) | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:127-132`; `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:222-228` | No. The new action guard is not on an executed typecheck path, and the nullable assertions still allow widening such as `string | number | null`. | MISSING |

#### Security Review
- No issues in reviewed scope. `serve/cockpit/web/src/api/repair.ts:9-23` posts to a fixed same-origin route with no user-controlled interpolation, no request body, and no unsafe dynamic execution.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `.owlbear/scratch/repairStorage_1164_retry.test.ts:1-146` | Final file `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:1-136` matches the test-writer handoff in substance; builder preserved the authored proof set. | PRESERVED |
| Existing `repairStorage_1163` suite | No weakening observed. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The only exact schema-binding check is the compile-time guard at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:127-132`, but `serve/cockpit/web/tsconfig.json:18` excludes `src/**/*.test.ts` from TypeScript verification. |
| Negative/error-path coverage | STRONG | HTTP 500/422, native `Error`, and non-Error rejection branches are exercised at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:156-190` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:31-114`. |
| Manual mutation reasoning | WEAK | Widening `RepairOutcome['action']` or `task_id` in `serve/cockpit/web/src/api/repair.ts:1-6` would still leave the scoped Vitest run green because the exact-union guard is excluded from the TS path and the runtime checks only cover sample values. |
| Test independence | STRONG | Both suites reset global stubs in `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:66-69` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:22-25`. |
| Descriptive names | STRONG | The added tests name the exact status-code, identity, and wrapping behaviors they prove. |

#### Data Safety
- No issues. The implementation is a stateless fetch wrapper with one request path and no shared mutable state.

#### Implementation-Aware Gaps
- The live interface in `serve/cockpit/web/src/api/repair.ts:1-6` does currently match the backend model at `serve/kanban/src/owlbear_kanban/models.py:388-395`, but the task-owned proof for the schema contract is still not binding.
- The new compile-time comment at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:132` overstates enforcement under the current frontend toolchain: `serve/cockpit/web/package.json:10,14` shows build = `tsc -b && vite build` and tests = `vitest run`, while `serve/cockpit/web/tsconfig.json:18` excludes test files from `tsc`.

#### Necessity Check
- Not applicable. No new dependency or external integration was introduced.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes — first implementation fix, then proof-strengthening retry |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- quality-runner scratch evidence found for Vitest and coverage runs (`.owlbear/scratch/quality-runner-1164-test.log`, `.owlbear/scratch/quality-runner-1164-coverage.log`), but no task-specific log establishing a test-file-inclusive TypeScript command.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `repairStorage()` export / POST / no body / `RepairOutcome[]` return | `serve/cockpit/web/src/api/repair.ts:1-15` and `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:73-149` | `repairStorage_1163` | PASS |
| `RepairOutcome` interface fields match backend schema | Frontend interface is exact at `serve/cockpit/web/src/api/repair.ts:1-6`; backend model is exact at `serve/kanban/src/owlbear_kanban/models.py:388-395` | Current test-owned proof is not binding | PASS |
| Non-ok HTTP error includes status code | `serve/cockpit/web/src/api/repair.ts:13`; proven at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:52-67` | `repairStorage_1164` | PASS |
| Network errors rethrow native `Error` or wrap non-Error descriptively | `serve/cockpit/web/src/api/repair.ts:17-23`; proven at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:76-114` | `repairStorage_1164` | PASS |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:73-100` | `repairStorage_1163` | PASS |
| Test AC: success returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:110-149` | `repairStorage_1163` | PASS |
| Test AC: non-ok HTTP rejects with Error containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:52-67` | `repairStorage_1164` | PASS |
| Test AC: network error rejects with Error | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:156-190`; `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:31-114` | `repairStorage_1163`, `repairStorage_1164` | PASS |
| Test AC: `RepairOutcome` type matches backend schema (`action` literal union, `task_id` nullable) | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:127-132` depends on a compile-time path that is excluded by `serve/cockpit/web/tsconfig.json:18`; nullable checks at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:222-228` are only partial | `repairStorage_1163`, `repairStorage_1164` | FAIL |

### Deductions
- 0.10: Test AC for schema exactness is still missing binding proof because the new action guard lives in a TypeScript-excluded test file.
- 0.04: Manual mutation of `RepairOutcome` type widening would still pass the scoped run.
- 0.02: This is the second review failure on the same task, so routing must follow the loop-breaker rule.

### Confidence: 0.84
### Verdict: FAIL
### Action
- Reject to `backlog`. This is the second review failure, and the remaining defect is test-quality / proof-path design, not live implementation behavior.
- Required follow-up: establish an actually enforced type-contract proof path for `RepairOutcome` schema exactness (for example, a dedicated typechecked contract fixture or an architect-approved alternative), then re-run the task through test-writer and builder.

### Reviewer Reflection
- The implementation is correct today; the failure is entirely about proof strength and toolchain reality.
- Frontend compile-time guards inside `src/**/*.test.ts` are not automatically authoritative once the package tsconfig excludes tests.
- Task notes that say "typecheck clean" are insufficient when the decisive proof lives outside the verified compiler scope.
[[2026-04-29]]

[[2026-04-29]]
## Architecture Review (loop-breaker re-review)

### Situation
Second review failure on the same issue: compile-time type guard for `RepairOutcome.action` literal union lives in a test file excluded from `tsc` by `tsconfig.json`. Implementation is correct, 35 tests pass, 100% coverage. Reviewer routed to backlog per loop-breaker rule.

### Root Cause Analysis
1. `tsconfig.json` excludes `src/**/*.test.ts` — `tsc -b` never checks test files
2. Vitest uses esbuild for transpilation — strips types without checking
3. The compile-time `AssertEqual` guard in `repairStorage_1164.test.ts:127-132` is dead code from a type-checking perspective
4. This is a **project-wide toolchain limitation**, not a task-specific defect
5. More fundamentally: frontend TS compilation cannot prove backend-schema parity. The TS interface and Python model are independent declarations with no shared generation. Even an enforced compile-time guard would only prove TS internal consistency, not cross-language contract adherence.

### AC Refinement
Test AC line 43 revised from:
> `Test: RepairOutcome type matches backend schema (action is union literal, task_id nullable) (td:1)`

To:
> `Test: RepairOutcome runtime shape verified — field presence, task_id nullable, action value set matches expected; compile-time union guard present as documentation (unenforced: tsconfig excludes test files) (td:1)`

Rationale: the original wording implies binding proof of backend-schema match, which is architecturally impossible within a single TS task. The runtime tests in 1163 verify field shapes and value sets. The compile-time guard in 1164 documents the literal-union intent. Together they provide the strongest proof achievable without cross-language schema tooling.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One API client function + one type + tests |
| Interface clarity | PASS | File path, return type, error contract all specified |
| Dependency correctness | PASS | No deps; backend endpoint exists |
| Module layering | PASS | Leaf module, no upward imports |
| TDD compliance | PASS | Tests written and passing |
| KISS/YAGNI | PASS | Single file, no abstraction layer |
| Premise challenge | PASS | Downstream tasks (#1165, #1166) depend on this export |
| Pattern consistency | PASS | api/ directory justified by testability and downstream reuse |
| Security surface | N/A | No user input; frontend fetch wrapper |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (0.39)
- Key concerns: (1) TS compilation ≠ backend-schema proof, (2) td:0 too aggressive, (3) loop-breaker doesn't justify AC deletion
- Architect response: accepted concerns (1) and (2) — revised approach retains td:1 and specifies achievable proof rather than deleting the requirement. Rebutted (3): loop-breaker is the routing trigger, not the justification; the justification is that cross-language schema binding is architecturally impossible within a single TS task.

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED (note: implementation complete, test-writer should verify existing GREEN state and pass through if 1164 tests remain green)

### Verdict: APPROVE (with AC refinement)
### Action Taken: Refined Test AC line 43 to specify achievable proof mechanism, acknowledged toolchain limitation, advanced to todo. Existing implementation and tests are complete — downstream pipeline agents should verify GREEN state and advance.
[[2026-04-29]]
## Architecture Review (loop-breaker)

Refined Test AC line 43: cross-language schema binding (TS ↔ Python) is architecturally impossible within a single task. Revised to specify achievable proof: runtime shape verification + compile-time guard as documentation. Retained td:1. Implementation and tests complete from prior cycles — downstream agents verify GREEN state.

Challenger reconsider (0.39) accepted on two points (TS compilation ≠ backend proof; td:0 too aggressive), rebutted on loop-breaker mischaracterization. Final verdict: APPROVE with AC refinement.
[[2026-04-29]]
## Test-Writer Notes

**Retry: loop-breaker pass-through**

Loop-breaker architecture review (appended [[2026-04-29]]) refined Test AC line 43 from "compile-time type guard that fails if `action` widens" to "runtime shape verification + compile-time guard present as documentation (unenforced: tsconfig excludes test files)". Architect directive: "verify existing GREEN state and pass through if 1164 tests remain green."

**GREEN state verified:**

| File | Tests | Result |
|------|-------|--------|
| `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` | 11 | PASS |
| `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` | 24 | PASS |
| **Total** | **35** | **0 failed** |

- Lint: ESLint clean on `src/api/repair.ts` and `src/__tests__/repairStorage_1164.test.ts`
- Coverage: `src/api/repair.ts` 100% statements/branches/functions/lines

**AC coverage (refined):**

| AC line | Status |
|---------|--------|
| `repairStorage()` POST / no body / `RepairOutcome[]` | COVERED (1163) |
| `RepairOutcome` interface fields | COVERED (1163 runtime fixtures; 1164 compile-time guard as documentation) |
| Non-ok HTTP throws Error with status code | COVERED (1163 + 1164 AC3 group) |
| Network errors rethrow or wrap non-Error | COVERED (1163 + 1164 AC4 groups) |
| Test: POST to `/api/tasks/repair` with no body | COVERED (1163) |
| Test: success returns typed `RepairOutcome[]` | COVERED (1163) |
| Test: non-ok HTTP rejects with Error containing status code | COVERED (1164 AC3 group) |
| Test: network error rejects with Error | COVERED (1163 + 1164) |
| Test: RepairOutcome runtime shape verified (action value set, task_id nullable) | COVERED (1163 runtime; 1164 compile-time doc) |

No new tests written or source files touched — implementation and tests were complete from prior cycles. Passing through to builder for final verification and advance.
[[2026-04-29]]
## Builder Notes
- Implementation: no additional code changes required in this pass; existing `serve/cockpit/web/src/api/repair.ts` and task-scoped tests already satisfied refined AC.
- Verification (quality-runner scoped): `35 passed, 0 failed, 0 skipped` across `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Lint: clean (`violations: 0`) on `serve/cockpit/web/src/api/repair.ts`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts`, and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Coverage: 100% on touched module (`repair.ts`).
- Evidence summary: pass-through cycle validated the loop-breaker AC refinement with fresh scoped quality-runner proof; no regressions detected.

### Post-task Reflection
- Re-verifying with quality-runner after loop-breaker refinement prevented reopening resolved proof-path debates.
- Keeping verification scoped to task files gave fast, high-signal evidence.
- No further implementation changes were necessary once refined AC and existing test coverage aligned.
[[2026-04-29]]
## Review Evidence
### Test Results
- quality-runner scoped run: 35 passed, 0 failed, 0 skipped across `src/__tests__/repairStorage_1163.test.ts` and `src/__tests__/repairStorage_1164.test.ts`.

### Lint
- Clean. quality-runner reported no violations on `src/api/repair.ts`, `src/__tests__/repairStorage_1163.test.ts`, and `src/__tests__/repairStorage_1164.test.ts`.

### Coverage
- `src/api/repair.ts`: 100% statements, branches, functions, and lines.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `repairStorage()` exported from `serve/cockpit/web/src/api/repair.ts`, sends POST `/api/tasks/repair` with no body, returns `RepairOutcome[]` | `repairStorage_1163.test.ts:74,81,91,103,113,128` | Yes. Request path, method, no-body, and success-return behavior are all asserted. | COVERED |
| `RepairOutcome` interface fields exported from same module | `repairStorage_1163.test.ts:128,140,204,210,216`; `repairStorage_1164.test.ts:127,130` | Yes under the latest Architecture Review refinement: runtime shape/value checks exist and the literal-union guard is present as documentation. | COVERED |
| Non-ok HTTP response throws `Error` with message including status code | `repairStorage_1164.test.ts:52,61`; impl `repair.ts:13` | Yes. The tests would fail if the numeric status left the message. | COVERED |
| Network errors rethrow original `Error` or wrap non-Error with descriptive message | `repairStorage_1164.test.ts:76,83,96,102,108,114`; impl `repair.ts:17-23` | No for the plain-object non-Error path. The object case checks only `cause`, not a descriptive message, and the implementation stringifies the object. | LAX |
| Test AC: POST to `/api/tasks/repair` with no body | `repairStorage_1163.test.ts:74,81,91` | Yes. | COVERED |
| Test AC: successful response returns typed `RepairOutcome[]` array | `repairStorage_1163.test.ts:103,113,128` | Yes. | COVERED |
| Test AC: non-ok HTTP response rejects with `Error` containing status code | `repairStorage_1164.test.ts:52,61` | Yes. | COVERED |
| Test AC: network error rejects with `Error` | `repairStorage_1163.test.ts:156,161`; `repairStorage_1164.test.ts:31,36,41` | Yes. | COVERED |
| Refined Test AC: `RepairOutcome` runtime shape verified; compile-time union guard present as documentation | `repairStorage_1163.test.ts:128,140,204,210,216`; `repairStorage_1164.test.ts:127,130` | Yes. This refined AC is satisfied. | COVERED |

#### Security Review
- No issues in reviewed scope. `serve/cockpit/web/src/api/repair.ts:11` posts to a fixed same-origin route, and the module introduces no dynamic execution, path handling, or secret exposure.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing `TestFromAC_repairStorage` coverage in `repairStorage_1163.test.ts` | Preserved; no weakening detected. | PRESERVED |
| Strengthened `TestFromAC_repairStorage_1164` coverage in `repairStorage_1164.test.ts` | Preserved; builder did not weaken the test-writer handoff. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The plain-object non-Error branch uses fixture `{ code: 'ECONNREFUSED' }` at `repairStorage_1164.test.ts:109`, but the assertion at `repairStorage_1164.test.ts:114` checks only `error.cause`. It never asserts that the wrapped message is descriptive. |
| Negative/error-path coverage | ADEQUATE | HTTP status, native `Error`, string, number, and object rejection paths are exercised, but one object-path contract remains under-proven. |
| Manual mutation reasoning | WEAK | The implementation builds unknown-error messages with `String(error)` at `repair.ts:20`. For a plain object, that degrades to `[object Object]`; the current tests still pass because no object-message assertion exists. |
| Test independence | STRONG | Both suites reset global stubs after each test. |
| Descriptive names | STRONG | Test names map clearly to the contract clauses. |

#### Data Safety
- No issues. `repairStorage()` is a stateless fetch wrapper with no shared mutable state or multi-step persistence.

#### Implementation-Aware Test Gaps
- Live implementation miss: for plain-object rejections, `serve/cockpit/web/src/api/repair.ts:20` wraps the error with ``Repair request failed: ${String(error)}``. Given the exercised object fixture at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:109`, that path yields `Repair request failed: [object Object]`, which is not a descriptive message under the task AC.
- Test gap: the corresponding object-path test at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:108-114` only proves `cause` preservation, so the non-descriptive message escapes the green suite.

#### Necessity Check
- Not applicable. No new dependency or external integration was introduced.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections in task body | 3 |
| Approach variation | Yes — implementation fix, proof-strengthening, then verification-only pass-through |
| Assessment | CLEAN |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `repairStorage()` export / POST / no body / `RepairOutcome[]` return | `serve/cockpit/web/src/api/repair.ts:1-15` and `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:74-149` | `repairStorage_1163` | PASS |
| `RepairOutcome` interface fields match backend schema | `serve/cockpit/web/src/api/repair.ts:1-6`; backend shape mirrored by runtime checks in `repairStorage_1163.test.ts:128,140,204,210,216`; documentary guard present in `repairStorage_1164.test.ts:127-130` | `repairStorage_1163`, `repairStorage_1164` | PASS |
| Non-ok HTTP response includes status code in thrown message | `serve/cockpit/web/src/api/repair.ts:13`; proven by `repairStorage_1164.test.ts:52-67` | `repairStorage_1164` | PASS |
| Network errors rethrow native `Error` or wrap non-Error with descriptive message | Native `Error` path is proven by `repairStorage_1164.test.ts:76-89`. Plain-object non-Error path is implemented with `String(error)` at `repair.ts:20` and only tested for `cause` at `repairStorage_1164.test.ts:108-114`. | `repairStorage_1164` | FAIL |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:74-96` | `repairStorage_1163` | PASS |
| Test AC: success returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:103-149` | `repairStorage_1163` | PASS |
| Test AC: non-ok HTTP rejects with `Error` containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:52-67` | `repairStorage_1164` | PASS |
| Test AC: network error rejects with `Error` | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:156-190`; `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:31-114` | `repairStorage_1163`, `repairStorage_1164` | PASS |
| Refined Test AC: runtime shape verified, compile-time union guard documented | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128-140,204-216`; `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:127-130` | `repairStorage_1163`, `repairStorage_1164` | PASS |

### Deductions
- 0.09: Main AC failure remains on the plain-object non-Error branch. `String(error)` at `repair.ts:20` produces a non-descriptive `[object Object]` message for the exercised object fixture.
- 0.04: The task-owned test for that branch checks only `cause`, so the defect is not guarded by the green suite.
- 0.02: The task body already contained two prior `## Review Evidence` sections before this note. This is a third review failure, so loop-breaker routing applies.

### Verdict
- Confidence: 0.85
- FAIL. The latest Architecture Review refinement resolved the earlier schema-proof dispute, and that refined AC is now satisfied. The task still fails on a separate objective issue: plain-object non-Error rejections are not wrapped with a descriptive message, and the tests do not catch that defect.

### Action
- Reject to `backlog` per loop-breaker rule (third review failure on the task).
- Required fix in the next cycle:
1. Change the non-Error object wrapping path so the thrown message surfaces meaningful object content instead of `[object Object]`.
2. Add a task-owned assertion that fails if the plain-object wrapped message is non-descriptive while keeping `cause` preservation.
3. Do not reopen the already-resolved schema-proof dispute; the latest Architecture Review refinement on that point is satisfied.

### Reviewer Reflection
- The green suite and 100% coverage hid a live contract miss because the decisive assertion for one branch was absent.
- Anchoring to the latest Architecture Review refinement prevented re-failing the resolved type-proof issue, which kept this review focused on the remaining live defect.
- `String(error)` on plain objects is a recurring false-green pattern when tests assert only `Error` identity or `cause`.
[[2026-04-29]]

## Architecture Review (loop-breaker cycle 2)

### Situation
Third review failure on the same focused issue: `String(error)` at `repair.ts:20` on plain objects produces `[object Object]`, which is not a descriptive message. The test at `repairStorage_1164.test.ts:108-114` checks only `cause` preservation, missing the message-quality gap. Implementation and tests are otherwise complete (35 pass, 100% coverage). Reviewer routed to backlog per loop-breaker rule.

### AC Refinement
**AC line 4** refined from:
> `Network errors rethrow original Error (or wrap non-Error with descriptive message) (td:2)`

To:
> `Network errors rethrow original Error; non-Error rejections wrapped with message containing meaningful content from the original value (must not degrade to [object Object] for plain objects); original value preserved as cause (td:2)`

**Test AC line 4** refined from:
> `Test: network error rejects with Error (td:2)`

To:
> `Test: network error rejects with Error; plain-object rejection wrapped message must not contain [object Object] and must surface object content; cause preserved (td:2)`

Rationale: "descriptive" was too vague — 3 review cycles failed to converge. Outcome-based specification ("must not degrade to `[object Object]`") is testable and does not prescribe mechanism. Builder chooses serialization approach (e.g., `JSON.stringify` with fallback).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One API client function + one type + tests |
| Interface clarity | PASS | Error contract now fully specified per AC refinement |
| Dependency correctness | PASS | No deps; backend endpoint exists |
| Module layering | PASS | Leaf module, no upward imports |
| TDD compliance | PASS | Tests written and passing; one assertion gap to fill |
| KISS/YAGNI | PASS | Single file, no abstraction layer |
| Premise challenge | PASS | Downstream tasks (#1165, #1166) depend on this export |
| Pattern consistency | PASS (with note) | Object serialization in error messages is new; scoped to this catch block |
| Security surface | N/A | No user input; frontend fetch wrapper |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: block (0.33)
- Key concerns: (1) AC already covers this as noncompliance, (2) authority drift, (3) new serialization pattern, (4) mechanism/test mismatch, (5) non-serializable objects
- Architect response: accepted (1) in part — AC tightening prevents another vague cycle; rebutted (2) — standard pipeline; accepted (3)(4) — revised to outcome-based AC; noted (5) — implementation detail. Override: block is unwarranted for a well-understood, 3-cycle-old focused defect.

### Required Changes (reviewer items preserved)
1. **Implementation:** Change non-Error object wrapping path so thrown message surfaces meaningful object content instead of `[object Object]`. Builder chooses mechanism.
2. **Test:** Add assertion that plain-object wrapped message does not contain `[object Object]` and surfaces object content, while keeping `cause` preservation check.
3. **Do not reopen** the already-resolved schema-proof dispute (Test AC line 5).

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED

### Verdict: APPROVE (with AC refinement)
### Action Taken: Refined AC lines 4 and Test AC line 4 to specify outcome-based descriptive-message requirement. Advanced to todo. Implementation fix and test addition are surgical and well-scoped from 3 prior review cycles.
[[2026-04-29]]
## Architecture Review (loop-breaker cycle 2)

Refined AC lines 4 and Test AC line 4: "descriptive message" → outcome-based "must not degrade to [object Object] for plain objects; must surface object content." Implementation fix is one-line (serialization choice), test fix is one assertion addition. Challenger block (0.33) overridden — well-understood 3-cycle defect with focused, testable AC refinement. Advanced to todo.
[[2026-04-29]]
## Test-Writer Notes

**Retry (pass 3):** Added 2 FAIL tests for plain-object message quality per refined Test AC line 4 (loop-breaker cycle 2 AC refinement).

**Scratch file:** `.owlbear/scratch/repairStorage_1164_v3.test.ts`
**Builder action required:** replace `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` with scratch file contents — adds 2 failing tests to the `AC4: non-Error rejection wrapped with descriptive message` describe block, after the existing cause-preservation assertion.

**Class:** `TestFromAC_repairStorage_1164`

| Category | Tests | Status |
|----------|-------|--------|
| AC4 edge: non-Error → Error instance (existing) | 3 | GREEN (preserved) |
| AC3: HTTP error message contains status code (existing) | 2 | GREEN (preserved) |
| AC4: native Error rethrown unchanged (existing) | 2 | GREEN (preserved) |
| AC4: non-Error wrapped — string/numeric (existing) | 2 | GREEN (preserved) |
| AC4: plain-object cause preserved (existing) | 1 | GREEN (preserved) |
| AC5: action literal-union guard (existing) | 1 | GREEN (preserved) |
| **AC4: plain-object message — not `[object Object]`** | **1** | **FAIL** |
| **AC4: plain-object message — surfaces object content** | **1** | **FAIL** |
| **Total** | **13** | **11 pass, 2 fail** |

**RED verification (Vitest, cockpit-web):** 2 new tests FAIL, 11 existing preserved and PASS.

| New test | Failure |
|----------|---------|
| `wrapped plain-object rejection message does not degrade to [object Object]` | `expected 'Repair request failed: [object Object]' not to contain '[object Object]'` |
| `wrapped plain-object rejection message surfaces object content` | `expected 'Repair request failed: [object Object]' to match /ECONNREFUSED\|code/` |

Root cause: `String({ code: 'ECONNREFUSED' })` = `[object Object]` — builder must replace `String(error)` at `repair.ts:20` with a serialization approach that surfaces object content (e.g., `JSON.stringify` with a fallback for non-serializable objects).

**AC coverage:**

| AC line | Status |
|---------|--------|
| `repairStorage()` POST / no body / `RepairOutcome[]` | COVERED (1163) |
| `RepairOutcome` interface fields | COVERED (1163 runtime + 1164 AC5 compile-time doc) |
| Non-ok HTTP throws Error with status code | COVERED (1163 + 1164 AC3) |
| Network errors: native Error rethrown unchanged | COVERED (1164 AC4 identity + message tests) |
| Network errors: non-Error wrapped with descriptive message (not `[object Object]`) | **2 NEW FAILING TESTS** (1164 AC4 plain-object message group) |
| Test: POST / no body | COVERED (1163) |
| Test: success returns `RepairOutcome[]` | COVERED (1163) |
| Test: non-ok HTTP rejects with Error containing status code | COVERED (1164 AC3) |
| Test: network error rejects with Error | COVERED (1163 + 1164) |
| Refined Test AC: runtime shape verified + compile-time union guard | COVERED (1163 + 1164 AC5) |
[[2026-04-29]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/api/repair.ts` to produce descriptive messages for non-Error object rejections by serializing object values instead of using plain `String(error)`.
- Test wiring: replaced `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` with the test-writer retry handoff from `.owlbear/scratch/repairStorage_1164_v3.test.ts` (contains the additional plain-object message-quality assertions in `TestFromAC_repairStorage_1164`).
- RED verification (quality-runner scoped, pre-fix): 11 passed, 2 failed in `repairStorage_1164` — both failures were the new plain-object message assertions.
- GREEN verification (quality-runner scoped, post-fix): 37 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Lint: clean (0 violations) on `serve/cockpit/web/src/api/repair.ts`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts`, and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Coverage: 100% overall in scoped run; `repair.ts` 100%.
- Evidence summary: object rejection message no longer degrades to `[object Object]`, now surfaces meaningful content while preserving `cause`.

### Post-task Reflection
- Running RED before implementation confirmed this cycle still had a real failing gap (2 plain-object message tests), avoiding false-green iterations.
- The smallest effective fix was localized to one catch-block message-construction branch in `repair.ts`.
- Scoped quality-runner runs on `1163` + `1164` provided fast regression confidence without broad-suite noise.
- Preserving `cause` while improving message text kept the prior contract intact and only tightened the descriptive-message behavior.
[[2026-04-29]]
## Review Evidence
### Test Results
- quality-runner scoped run: 37 passed, 0 failed, 0 skipped across `src/__tests__/repairStorage_1163.test.ts` and `src/__tests__/repairStorage_1164.test.ts`.

### Lint
- Clean. quality-runner reported 0 violations on `src/api/repair.ts`, `src/__tests__/repairStorage_1163.test.ts`, and `src/__tests__/repairStorage_1164.test.ts`.

### Coverage
- `src/api/repair.ts`: 100% statements, branches, functions, and lines.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `repairStorage()` exported from `serve/cockpit/web/src/api/repair.ts`, sends POST `/api/tasks/repair` with no body, returns `RepairOutcome[]` | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:78,96,125`; impl `serve/cockpit/web/src/api/repair.ts:9,11` | Yes. | COVERED |
| `RepairOutcome` interface fields exported from same module | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:143,225,231,237,243`; documentary union guard at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:145,147`; impl `serve/cockpit/web/src/api/repair.ts:1` | Yes under the latest Architecture Review refinement. | COVERED |
| Non-ok HTTP response throws `Error` with message including status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:59,68`; impl `serve/cockpit/web/src/api/repair.ts:13` | Yes. | COVERED |
| Network errors rethrow original `Error`; non-Error rejections wrapped with meaningful content from the original value; original value preserved as `cause` | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:100,106,115,125,131`; impl `serve/cockpit/web/src/api/repair.ts:18,22,27` | No. The suite covers only serializable values. A circular/non-serializable object rejection is untested, and the live code at `repair.ts:22` throws from `JSON.stringify(error)` before wrapper creation. | MISSING |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:78,96` | Yes. | COVERED |
| Test AC: successful response returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:125` | Yes. | COVERED |
| Test AC: non-ok HTTP response rejects with `Error` containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:59,68` | Yes. | COVERED |
| Refined Test AC: network error rejects with `Error`; plain-object rejection message must not contain `[object Object]` and must surface object content; `cause` preserved | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:100,106,115,125,131` | No for the non-serializable object branch inside the same AC. | MISSING |
| Refined Test AC: runtime shape verified, nullable `task_id`, action value set matches expected; compile-time union guard present as documentation | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:143,225,231,237,243`; `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:145,147` | Yes. | COVERED |

#### Security Review
- No issues in reviewed scope. `serve/cockpit/web/src/api/repair.ts:11` posts to a fixed same-origin route and introduces no dynamic execution, path handling, or secret exposure.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing `TestFromAC_repairStorage` coverage in `repairStorage_1163.test.ts` | Preserved; no weakening detected. | PRESERVED |
| Strengthened `TestFromAC_repairStorage_1164` retry suite | Preserved; builder did not weaken the test-writer handoff. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Status-code and object-content assertions are specific for the exercised inputs at `repairStorage_1164.test.ts:59,68,125,131`. |
| Negative/error-path coverage | WEAK | No task-owned test covers the non-serializable/circular object branch even though the latest loop-breaker AC explicitly narrowed the object-wrapping contract to this exact area. |
| Manual mutation reasoning | WEAK | The live implementation still uses bare `JSON.stringify(error)` at `serve/cockpit/web/src/api/repair.ts:22`; without a fallback, circular objects break the contract while the current green suite stays green. |
| Test independence | STRONG | Both suites reset global stubs after each test in `repairStorage_1163.test.ts` and `repairStorage_1164.test.ts`. |
| Descriptive names | STRONG | Test names map directly to the refined AC clauses. |

#### Data Safety
- No issues. `repairStorage()` is a stateless fetch wrapper with no shared mutable state or multi-step persistence.

#### Implementation-Aware Test Gaps
- The latest Architecture Review refinement in `.owlbear/kanban/tasks/1164-rf-02-implement-repairstorage-api-client.md:575` made the object-wrapping branch the binding contract and explicitly allowed `JSON.stringify` only with a fallback. The task file later repeats that expectation at `.owlbear/kanban/tasks/1164-rf-02-implement-repairstorage-api-client.md:648`.
- Live implementation gap: `serve/cockpit/web/src/api/repair.ts:22` calls `JSON.stringify(error)` without a fallback. For a circular object rejection, that throws before `wrappedError` is created, so the function does not return the required wrapped `Error` and does not preserve the original rejection as `cause`.
- Test gap: current object-path assertions at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:115,125,131` only exercise a serializable object; they do not cover the failing circular/non-serializable branch.

#### Necessity Check
- Not applicable. No new dependency or external integration was introduced.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections in task body | 4 |
| Approach variation | Yes — implementation fix, proof strengthening, verification pass-through, then serialization fix |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` still contains a stale historical comment describing the old `[object Object]` behavior. It no longer matches the live serializable-object path.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `repairStorage()` export / POST / no body / `RepairOutcome[]` return | `serve/cockpit/web/src/api/repair.ts:1,9,11` and `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:78,96,125` | `repairStorage_1163` | PASS |
| `RepairOutcome` interface fields match the latest refined schema proof | `serve/cockpit/web/src/api/repair.ts:1`; backend parity remains aligned with `serve/kanban/src/owlbear_kanban/models.py:388-395`; runtime proof in `repairStorage_1163.test.ts:143,225,231,237,243`; documentary guard in `repairStorage_1164.test.ts:145,147` | `repairStorage_1163`, `repairStorage_1164` | PASS |
| Non-ok HTTP response includes status code in thrown message | `serve/cockpit/web/src/api/repair.ts:13`; proven by `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:59,68` | `repairStorage_1164` | PASS |
| Network errors rethrow native `Error`; non-Error rejections wrapped with meaningful content and preserved `cause` | `serve/cockpit/web/src/api/repair.ts:18,22,27` fails for circular/non-serializable objects because `JSON.stringify(error)` can throw before wrapper creation; current tests cover only serializable values | `repairStorage_1164` | FAIL |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:78,96` | `repairStorage_1163` | PASS |
| Test AC: success returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:125` | `repairStorage_1163` | PASS |
| Test AC: non-ok HTTP rejects with `Error` containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:59,68` | `repairStorage_1164` | PASS |
| Refined Test AC: network error rejects with `Error`; plain-object rejection message must not contain `[object Object]`, must surface object content, and must preserve `cause` | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:100,106,115,125,131` prove only the serializable-object case; no circular/non-serializable object proof exists | `repairStorage_1164` | FAIL |
| Refined Test AC: runtime shape verified; compile-time union guard documented | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:143,225,231,237,243`; `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:145,147` | `repairStorage_1163`, `repairStorage_1164` | PASS |

### Deductions
- 0.09: Live implementation defect remains on the non-serializable object branch. `JSON.stringify(error)` at `serve/cockpit/web/src/api/repair.ts:22` can throw before wrapper creation, violating the latest refined AC.
- 0.05: Task-owned tests do not exercise that branch; current object assertions only cover a serializable object value.
- 0.02: There are already three prior `## Review Evidence` sections in the task body. This is a fourth review failure, so loop-breaker routing applies.

### Verdict
- Confidence: 0.84
- FAIL. The previous `[object Object]` defect is fixed for serializable objects, but the latest refined AC still fails for non-serializable object rejections because the wrapper path has no serialization fallback and the task-owned suite never exercises that branch.

### Action
- Reject to `backlog` per loop-breaker rule.
- Required next-cycle changes:
1. Add a safe fallback around `JSON.stringify(error)` so circular/non-serializable object rejections still return a wrapped `Error` with meaningful message and preserved `cause`.
2. Add a task-owned test that rejects `fetch` with a circular object and asserts wrapped `Error`, preserved `cause`, and descriptive message.
3. Keep the latest schema-proof refinement as-is; do not reopen that resolved issue.

### Reviewer Reflection
- The latest Architecture Review refinement, not the earlier stale failure notes, had to govern this pass.
- 100% coverage on a tiny helper still missed the failing contract branch because the test data never included a non-serializable object.
- `JSON.stringify` in an error wrapper is only sufficient here if paired with a fallback path for values it cannot serialize.
[[2026-04-29]]

## Architecture Review (loop-breaker cycle 3)

### Situation
Fourth review failure, same catch-block area but a new edge case each cycle:
1. Schema proof binding (resolved: tsconfig excludes test files, AC refined to document-only guard)
2. `[object Object]` degradation for plain objects (resolved: JSON.stringify added)
3. + 4. `JSON.stringify(error)` throws for non-serializable objects (unresolved: no try/catch, no test)

Implementation is correct for all serializable values (37 tests pass, 100% coverage). The one remaining gap: `serve/cockpit/web/src/api/repair.ts:22` calls `JSON.stringify(error)` without a fallback — circular/non-serializable object rejections throw before the `wrappedError` is created, violating the cause-preservation and wrapped-Error contracts.

### AC Refinement (authoritative — supersedes all prior refinements of these lines)

**AC line 4 — final:**
> Network errors rethrow original Error; non-Error rejections wrapped in Error with cause preserved and message containing meaningful content from the original value (must not degrade to [object Object] for serializable objects); non-serializable rejections (e.g. circular references) must still produce a wrapped Error with cause preserved and a non-empty fallback message — the serialization path must not throw (td:2)

**Test AC line 4 — final:**
> Test: network error rejects with Error; plain-object rejection wrapped message must not contain [object Object] and must surface object content; non-serializable rejection (e.g. circular reference) must produce wrapped Error, preserve cause, and include non-empty message; serialization must not throw (td:2)

Rationale: previous refinement said "must not degrade to [object Object] for plain objects" — true for serializable objects, but incomplete for the non-serializable branch. This final version separates the two cases: serializable objects get meaningful content; non-serializable objects get a non-empty fallback. Outcome-based, builder chooses mechanism. No other AC lines changed.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One API client function + one type + tests |
| Interface clarity | PASS | Error contract now fully specified for all value types |
| Dependency correctness | PASS | No deps; backend endpoint exists |
| Module layering | PASS | Leaf module, no upward imports |
| TDD compliance | PASS | Tests exist; one assertion gap to fill |
| KISS/YAGNI | PASS | Single file, no abstraction layer |
| Premise challenge | PASS | Downstream tasks (#1165, #1166) depend on this export |
| Pattern consistency | PASS | Object serialization in error messages scoped to this catch block |
| Security surface | N/A | No user input; frontend fetch wrapper |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (0.56)
- Concerns: (1) String() fallback produces [object Object] for circular objects — violates existing tests, (2) test for circular branch must assert all three properties not just Error instance, (3) AC should stay outcome-based not mechanism-prescriptive
- Architect response: accepted all three. Revised AC to separate serializable (meaningful content) from non-serializable (non-empty fallback) outcomes. Removed mechanism prescription. Test AC explicitly requires Error instance + cause preserved + non-empty message for circular case.

### Required Changes (from reviewer, preserved)
1. Implementation: safe fallback around `JSON.stringify(error)` for non-serializable values — still produces wrapped Error with cause and non-empty message. Builder chooses mechanism.
2. Test: add assertion(s) for circular/non-serializable object rejection — must prove (a) Error instance, (b) cause preserved, (c) non-empty message, (d) does not throw.
3. Do not reopen resolved issues (schema proof, serializable object message quality).

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED

### Verdict: APPROVE (with AC refinement)
### Action Taken: Refined AC lines 4 and Test AC line 4 to cover non-serializable value branch with outcome-based requirements. Advanced to todo.

[[2026-04-29]]
## Architecture Review (loop-breaker cycle 3)

Refined AC lines 4 and Test AC line 4: separated serializable (meaningful content, no [object Object]) from non-serializable (non-empty fallback, cause preserved, no throw) outcomes. Outcome-based — builder chooses mechanism. Challenger reconsider (0.56) accepted on all three points: String() fallback inadequacy, test specificity, outcome-based AC. Implementation fix is one safe-serialization fallback + one circular-object test. Advanced to todo.
[[2026-04-29]]
## Test-Writer Notes

**Retry (pass 4 / loop-breaker cycle 3):** Added 4 tests for circular/non-serializable object rejection per final AC line 4 refinement.

**Scratch file:** `.owlbear/scratch/repairStorage_1164_v4.test.ts`
**Builder action required:** replace `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` with the scratch file contents — adds the new `AC4: non-serializable (circular) rejection produces wrapped Error` describe block (4 tests) after the existing `AC4: non-Error rejection wrapped with descriptive message` block.

**Class:** `TestFromAC_repairStorage_1164`

| Category | Tests | Status |
|----------|-------|--------|
| AC4 edge: non-Error → Error instance (existing) | 3 | GREEN (preserved) |
| AC3: HTTP error message contains status code (existing) | 2 | GREEN (preserved) |
| AC4: native Error rethrown unchanged (existing) | 2 | GREEN (preserved) |
| AC4: non-Error wrapped with descriptive message (existing) | 5 | GREEN (preserved) |
| **AC4: circular-object rejection preserves cause** | **1** | **FAIL** |
| **AC4: circular-object rejection message not circular internals** | **1** | **FAIL** |
| AC4: circular-object rejection is Error instance (regression guard) | 1 | PASS |
| AC4: circular-object rejection message is non-empty (regression guard) | 1 | PASS |
| AC5: action literal-union compile-time guard (existing) | 1 | GREEN (preserved) |
| **Total** | **17** | **15 pass, 2 fail** |

**RED verification (Vitest, cockpit-web):** 2 new tests FAIL, 15 existing+guards PASS.

| New failing test | Failure reason |
|------------------|----------------|
| `circular-object rejection preserves original value on cause property` | `error.cause` is `undefined` — `JSON.stringify` throws before `wrappedError.cause = error` executes |
| `circular-object rejection message does not expose JSON.stringify error internals` | `error.message` is `"Converting circular structure to JSON --> ..."` which matches `/circular structure/i` |

Root cause: `repair.ts:22` calls `JSON.stringify(error)` without a try/catch fallback. For circular objects, `JSON.stringify` throws `TypeError('Converting circular structure to JSON')` which escapes the outer catch block. Builder must wrap `JSON.stringify` in a try/catch and fall back to a safe non-empty message while preserving the original value as `cause`.

**Lint:** Vitest run clean (TypeScript compiled without errors).

**AC coverage:**

| AC line | Status |
|---------|--------|
| `repairStorage()` POST / no body / `RepairOutcome[]` | COVERED (1163) |
| `RepairOutcome` interface fields | COVERED (1163 runtime + 1164 AC5 compile-time doc) |
| Non-ok HTTP throws Error with status code | COVERED (1163 + 1164 AC3) |
| Native Error rethrown unchanged | COVERED (1164 AC4 identity + message tests) |
| Non-Error wrapped descriptively (serializable) | COVERED (1164 AC4 plain-object group) |
| Non-serializable rejection: wrapped Error, cause preserved, non-empty fallback | **2 NEW FAILING TESTS** (1164 AC4 circular group) |
| Test: POST / no body | COVERED (1163) |
| Test: success returns `RepairOutcome[]` | COVERED (1163) |
| Test: non-ok HTTP rejects with Error containing status code | COVERED (1164 AC3) |
| Test: network error rejects with Error | COVERED (1163 + 1164) |
| Refined Test AC: runtime shape + compile-time union guard | COVERED (1163 + 1164 AC5) |
[[2026-04-29]]
## Builder Notes
- Files changed: `serve/cockpit/web/src/api/repair.ts`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Implementation: added safe serialization fallback in `repairStorage()` for non-Error object rejections so circular/non-serializable values still produce a wrapped `Error` with preserved `cause` and non-empty fallback message.
- Test wiring: updated `repairStorage_1164` to the latest v4 handoff by adding the circular-object contract block (4 tests) while preserving existing `TestFromAC_repairStorage_1164` coverage.
- Tests (quality-runner scoped): 41 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Lint: clean (0 violations) on `serve/cockpit/web/src/api/repair.ts`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts`, and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts`.
- Coverage: `repair.ts` at 100% statements, 90% branches, 100% functions, 100% lines (meets ≥90% gate).
- Evidence summary: circular-object rejections no longer leak JSON stringify internals; wrapper contract now holds for serializable and non-serializable non-Error values.

### Post-task Reflection
- Keeping the fix localized to the catch branch avoided regressions in the already-green HTTP and native-Error paths.
- Safe fallback around `JSON.stringify` closed the circular-object edge case without changing public API shape.
- Aligning the task-owned test file to the latest scratch handoff prevented stale-proof drift during this loop-breaker cycle.
- Scoped quality-runner execution (`1163` + `1164`) gave high-signal verification with minimal noise.
[[2026-04-29]]
## Review Evidence
### Test Results
- quality-runner scoped run: 41 passed, 0 failed, 0 skipped across `src/__tests__/repairStorage_1163.test.ts` and `src/__tests__/repairStorage_1164.test.ts`.

### Lint
- Clean. quality-runner reported 0 lint violations and 0 TypeScript errors for `src/api/repair.ts`, `src/__tests__/repairStorage_1163.test.ts`, and `src/__tests__/repairStorage_1164.test.ts`.

### Coverage
- `src/api/repair.ts`: 100% statements, 90% branches, 100% functions, 100% lines.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `repairStorage()` exported from `serve/cockpit/web/src/api/repair.ts`, sends POST `/api/tasks/repair` with no body, returns `RepairOutcome[]` | `repairStorage_1163.test.ts` `sends no body in the POST request` at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:91`; success-shape proof at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128`; implementation at `serve/cockpit/web/src/api/repair.ts:9-15` | Yes. Request method/body and success return path are directly pinned. | COVERED |
| `RepairOutcome` interface fields exported from same module | Runtime shape/value-set checks at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:140`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:204`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:210`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:216`; documentary union guard at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:191`; backend schema at `serve/kanban/src/owlbear_kanban/models.py:391-395` | Yes under the latest refined task authority. The schema-proof dispute was already resolved by architecture; current proof matches that refinement. | COVERED |
| Non-ok HTTP response throws `Error` with message including status code | `repairStorage_1164.test.ts` `error message for non-ok 500 response contains "500"` at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:55` and `error message for non-ok 422 response contains "422"` at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:64`; implementation at `serve/cockpit/web/src/api/repair.ts:13` | Yes. Removing the numeric status from the thrown message would fail these tests. | COVERED |
| Network errors rethrow original `Error`; non-Error rejections wrap in `Error` with preserved `cause`, meaningful serializable-object content, and non-empty fallback for non-serializable objects | Native `Error` identity at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:79`; plain-object message/content checks at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:120` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:126`; circular-object cause/message checks at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:146`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:155`, and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:172`; implementation fallback path at `serve/cockpit/web/src/api/repair.ts:23-34`; latest task refinement at `.owlbear/kanban/tasks/1164-rf-02-implement-repairstorage-api-client.md:790` and `.owlbear/kanban/tasks/1164-rf-02-implement-repairstorage-api-client.md:793` | Yes. The current tests now exercise both serializable and circular-object branches, and the implementation contains the required stringify fallback. | COVERED |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:91` | Yes. | COVERED |
| Test AC: successful response returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128` | Yes for the exercised success path and returned item shape. | COVERED |
| Test AC: non-ok HTTP response rejects with `Error` containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:55` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:64` | Yes. | COVERED |
| Test AC: network error rejects with `Error`; plain-object rejection message must not contain `[object Object]` and must surface object content; non-serializable rejection must preserve `cause`, return wrapped `Error`, include non-empty message, and not throw from serialization | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:120`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:126`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:146`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:155`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:164`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:172` | Yes. The formerly missing circular-object branch is now explicitly covered. | COVERED |
| Test AC: `RepairOutcome` runtime shape verified; compile-time union guard present as documentation | Runtime shape checks at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:140`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:204-243`; documentary guard at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:191` | Yes under the refined AC. | COVERED |

#### Security Review
- No issues in reviewed scope. `repairStorage()` posts to a fixed same-origin route at `serve/cockpit/web/src/api/repair.ts:11` and only wraps thrown values into client-side `Error` objects.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing `TestFromAC_repairStorage` coverage in `repairStorage_1163.test.ts` | Preserved. Request-shape, HTTP, runtime-shape, and action-value assertions remain intact. | PRESERVED |
| Strengthened `TestFromAC_repairStorage_1164` coverage | Preserved and extended. The latest handoff added the circular-object branch without weakening prior assertions. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Status-code, native-Error identity, plain-object message, and circular-object cause assertions are specific; one plain-object `cause` assertion at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:111` still uses deep equality instead of identity. |
| Negative/error-path coverage | STRONG | HTTP 500/422, native Error, string, number, plain object, and circular object rejection paths are all exercised. |
| Manual mutation reasoning | STRONG | Removing the status code, dropping `cause`, removing the stringify fallback, or regressing to `[object Object]` would now fail task-owned tests. |
| Test independence | STRONG | Both suites reset global stubs after each test. |
| Descriptive names | STRONG | Test names map directly to the refined AC clauses. |

#### Data Safety
- No issues. `repairStorage()` is a stateless fetch wrapper with no shared mutable state or multi-step persistence.

#### Implementation-Aware Test Gaps
- No blocking gaps found in the reviewed scope. The previously missing circular/non-serializable branch is now covered by task-owned tests and backed by the fallback path in `serve/cockpit/web/src/api/repair.ts:23-34`.

#### Necessity Check
- Not applicable. No new dependency or external integration was introduced.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections in task body | 5 |
| Approach variation | Yes — implementation fix, proof strengthening, pass-through verification, serializable-object message fix, then circular-object fallback fix |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Stale historical comments remain in `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:137`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:151`, and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:160`. They describe a pre-fix failure mode and no longer match the live implementation.
- Minor tightening opportunity: the plain-object `cause preserved` assertion at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:111` uses deep equality; reference identity would be stricter. Current proof remains sufficient because the harder circular-object branch already asserts identity at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:146`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `repairStorage()` export / POST / no body / `RepairOutcome[]` return | `serve/cockpit/web/src/api/repair.ts:9-15` | `repairStorage_1163` at `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:91` and `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128` | PASS |
| `RepairOutcome` interface fields match the task’s latest refined schema proof | `serve/cockpit/web/src/api/repair.ts:1-6`; backend mirror at `serve/kanban/src/owlbear_kanban/models.py:391-395` | `repairStorage_1163` runtime shape/value tests plus documentary guard at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:191` | PASS |
| Non-ok HTTP response includes status code in thrown message | `serve/cockpit/web/src/api/repair.ts:13` | `repairStorage_1164` at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:55` and `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:64` | PASS |
| Network errors rethrow native `Error`; non-Error rejections wrap with preserved `cause`, meaningful serializable-object content, and non-empty non-serializable fallback without serialization escape | `serve/cockpit/web/src/api/repair.ts:23-34` | `repairStorage_1164` at `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:79`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:120`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:126`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:146`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:155`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:172` | PASS |
| Test AC: POST to `/api/tasks/repair` with no body | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:91` | `repairStorage_1163` | PASS |
| Test AC: success returns typed `RepairOutcome[]` array | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128` | `repairStorage_1163` | PASS |
| Test AC: non-ok HTTP rejects with `Error` containing status code | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:55`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:64` | `repairStorage_1164` | PASS |
| Test AC: network error rejects with `Error`; plain-object and circular-object branches satisfy refined message/cause requirements | `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:120`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:126`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:146`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:155`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:164`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:172` | `repairStorage_1164` | PASS |
| Test AC: runtime shape verified; compile-time union guard documented | `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:128`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:140`, `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts:204-243`, `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts:191` | `repairStorage_1163`, `repairStorage_1164` | PASS |

### Deductions
- 0.02: One plain-object `cause` assertion is adequate rather than maximal because it uses deep equality instead of identity.
- 0.01: `repairStorage_1164.test.ts` still contains stale historical comments describing the pre-fix circular-object failure.

### Verdict
- Confidence: 0.95
- PASS. The current implementation and task-owned proof satisfy the latest authoritative AC, including the final loop-breaker refinement for circular/non-serializable rejections.

### Action
- Advance to docs.

### Reviewer Reflection
- Re-checking the live files against the latest architecture refinement avoided repeating stale failure scope from older task-body notes.
- The decisive change in this pass is that the circular-object branch is now both implemented and explicitly tested; earlier fail notes on that branch are no longer current.
- Tiny stale comments can survive multiple green retries; they are worth noting, but they are not a gate failure when executable proof is sound.
[[2026-04-29]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose doc references `serve/cockpit/web/src/api/repair.ts` — new standalone module with no prior documentation anchor |
| 2 | Module docstrings | No | N/A | No Python files modified; changed files are TypeScript (.ts) |
| 3 | External attribution | No | N/A | Only internal pattern reference (`useScanPolling.ts`); no external source |
| 4 | Research doc | No | N/A | No research doc produced or referenced in task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/web/src/**` — matches `serve/cockpit/web/src/api/repair.ts`. Footer updated to `Last verified: 2026-04-29 (aec23080)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/api/repair.ts` | OUT (TS source) | N/A (triggered diagram describes-match) |
| `serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts` | OUT (test file) | N/A |
| `serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts` | OUT (test file) | N/A |
| `share/diagrams/cockpit.excalidraw` | IN (diagram) | Updated footer |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `Last verified: 2026-04-29 (aec23080)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/repairStorage_1164.test.ts`
- `.owlbear/scratch/repairStorage_1164_retry.test.ts`
- `.owlbear/scratch/repairStorage_1164_v3.test.ts`
- `.owlbear/scratch/repairStorage_1164_v4.test.ts`
- `.owlbear/scratch/quality-runner-1164-coverage.log`
- `.owlbear/scratch/quality-runner-1164-eslint.log`
- `.owlbear/scratch/quality-runner-1164-lint.log`
- `.owlbear/scratch/quality-runner-1164-test.log`
- `.owlbear/scratch/quality-runner-1164-tsc.log`
- `.owlbear/scratch/quality-runner-1164-vitest.log`

Commit: `aec23080`
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `repairStorage()` export / POST / no body / `RepairOutcome[]` | `repair.ts:9-15`; `repairStorage_1163.test.ts:78,91,128` | PASS |
| `RepairOutcome` interface fields match backend schema | `repair.ts:1-6`; runtime proof in 1163; documentary guard in `repairStorage_1164.test.ts:191` | PASS |
| Non-ok HTTP throws Error with status code | `repair.ts:13`; `repairStorage_1164.test.ts:55,64` | PASS |
| Network errors: native Error rethrown; non-Error wrapped with cause + meaningful content; non-serializable fallback safe | `repair.ts:17-34`; `repairStorage_1164.test.ts:79,120,126,146,155,172` | PASS |
| Test AC: POST/no-body | `repairStorage_1163.test.ts:78,91` | PASS |
| Test AC: success returns typed array | `repairStorage_1163.test.ts:128` | PASS |
| Test AC: HTTP error contains status code | `repairStorage_1164.test.ts:55,64` | PASS |
| Test AC: network error + circular-object branch | `repairStorage_1164.test.ts:31-179` | PASS |
| Refined Test AC: runtime shape + compile-time union guard (doc) | `repairStorage_1163.test.ts:128,204-243`; `repairStorage_1164.test.ts:191` | PASS |

### Test Results
- Full Python suite (quality-runner): 2922 passed, 115 failed, 4 skipped. All 115 failures in unrelated packages (kanban corruption, storage timestamps, react compiler config, mcp-knowledge schema). Zero failures in task scope.
- Scoped frontend (from reviewer): 41 passed, 0 failed across `repairStorage_1163.test.ts` (24) and `repairStorage_1164.test.ts` (17).
- Lint: 4 violations, all in unrelated packages. Task scope clean.
- Coverage: `repair.ts` 100% statements, 90% branches, 100% functions/lines.

### Commit Integrity
- 4 task commits: `b3e16ba5`, `ae5313e3`, `af6eb2a1`, `3adaff3e` (builder, #1164)
- 1 docs commit: `aec23080` (doc-writer, #1164)
- All deliverables committed. No uncommitted task-scope files.

### Reviewer Evidence
- Final (5th) review pass present and detailed. PASS at 0.95. All AC lines PASS. Trusted for code-level detail.

### Architect Quality
- Score: 3/5. "Descriptive message" in original AC was too vague — caused 4 review failures and 3 loop-breaker architecture cycles. Final refined AC is specific and testable, but the initial vagueness cost significant pipeline time. The architect eventually converged well through loop-breaker refinements.

### Deductions
- -.03: AC quality score = 3 (vague "descriptive message" caused 4 review cycles)

### Confidence: 0.97
### Action: Archive