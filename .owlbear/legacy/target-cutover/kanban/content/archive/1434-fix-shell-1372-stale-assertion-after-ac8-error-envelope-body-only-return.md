---
id: 1434
title: Fix Shell_1372 stale assertion after AC8 error-envelope body-only return
status: archived
priority: medium
created: 2026-05-08T01:18:13.984319+00:00
updated: 2026-05-08T09:27:17.870132+00:00
tags:
- cockpit
- frontend
- type:fix
- test-curation
- test
parent: 1375
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Task #1375 adopted `getResponseErrorMessage()` across frontend error paths. AC8 changed the helper to return parsed body text alone (no fallback decoration). This caused `Shell_1372.test.tsx` L479 assertion `toContain('Polling request failed with status 500')` to fail — `usePollingFetch` now surfaces the body message "Board scan encountered an error and could not complete." instead of the old fallback string.

## Objective

Update the single assertion in `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx` at L479 to expect the body message instead of the old fallback string.

## Acceptance Criteria

- [ ] AC1: Assertion at L479 expects `"Board scan encountered an error and could not complete."` (or the actual body text the mock returns) instead of `'Polling request failed with status 500'` (td:0)
- [ ] AC2: `npm test -- --run Shell_1372` passes (td:0)
- [ ] AC3: No other test files modified (td:0)

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One stale assertion in one test file |
| Interface clarity | PASS | AC1 specifies exact old/new values; AC2 is a concrete pass gate |
| Dependency correctness | PASS | No deps needed — error-envelope change already landed |
| Module layering | N/A | Test-only change, no production code |
| TDD compliance | PASS | Tagged `test` for pass-through — this IS the test fix |
| KISS/YAGNI | PASS | Minimal scope, single assertion update |
| Premise challenge | PASS | Traced: `getResponseErrorMessage()` returns `SCAN_ERROR_ENVELOPE.message` ("Board scan...") instead of fallback string. Stale assertion confirmed |
| Pattern consistency | PASS | Assertion update follows existing test patterns |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Frontend/cockpit only |

### Code Trace Evidence
- `SCAN_ERROR_ENVELOPE` at L87: `{ code: 'SCAN_FAILED', message: 'Board scan encountered an error and could not complete.' }`
- `getResponseErrorMessage()` in `api/errorMessage.ts` L20-32: parses JSON, returns `message` field if present → returns body text
- `usePollingFetch.ts` L69-72: calls `getResponseErrorMessage(response, fallback)` → throws `new Error(errorMessage)` with body text
- L479 assertion expects old fallback `'Polling request failed with status 500'` — must become `'Board scan encountered an error and could not complete.'`

### Note
Adjacent comment at L478 (`// usePollingFetch error message for non-2xx: "Polling request failed with status 500"`) and block comment at L464-466 are also stale. Builder should update these alongside the assertion — cosmetic, within spirit of AC1.

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Annotated AC with td:0, added `test` pass-through tag, advanced to todo
[[2026-05-08]]
Architecture review complete. Code trace confirms stale assertion: `getResponseErrorMessage()` now returns `SCAN_ERROR_ENVELOPE.message` body text instead of fallback string. All AC lines td:0. Added `test` pass-through tag. Test-writer: SKIP.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- All AC lines annotated td:0. Architect explicitly marked "Test-writer: SKIP".
- Task scope: update a single stale assertion in an existing test file (`Shell_1372.test.tsx` L479). This IS the test artifact — no new test file needed.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: updated stale HTTP 500 status-bar expectation and adjacent explanatory comments in serve/cockpit/web/src/__tests__/Shell_1372.test.tsx.
- Tests: 20 passed, 0 failed, 0 skipped (scoped Shell_1372 suite via quality-runner frontend execution).
- Coverage: N/A for this scoped frontend pass (not required by AC for this td:0 task).
- Lint: clean (eslint clean via quality-runner).
- Approach: surgical one-file assertion refresh to align with body-only error envelope behavior from getResponseErrorMessage().

### Post-task Reflection
- Problem faced: task carried a non-impl pass-through note while still requiring a concrete test assertion update.
- Workaround applied: followed the explicit AC/objective and limited changes to exactly the targeted test file.
- Pattern discovered: frontend error-message contracts can silently invalidate hard-coded fallback-string assertions.
- Quality gap: stale inline comments near assertions can mask expectation drift; updating them with assertion edits reduces future false diagnoses.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run on `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx`: 20 passed, 0 failed, 0 skipped.
- Exit codes: vitest 0, eslint 0, errors: none.
- IDE diagnostics: no errors reported for `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx`.

### Coverage
- N/A for this td:0 targeted test-curation task. AC does not require coverage and no production code changed.

### Scope And Ownership
- First review cycle: task file contains no prior `## Review Evidence` sections.
- Task ownership commit recorded in `.git/logs/HEAD` line 2264 and `.git/logs/refs/heads/dev` line 2088: `test: update Shell_1372 stale 500-message assertion (#1434, builder)`.
- Git inspection of commit `be1edb550667563359a1f75bfe0216a7f4fe4051` showed only `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx` changed.
- Git inspection also found no overlapping uncommitted changes in `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx`, so review evidence is not contaminated by dirty-tree state.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: Assertion at L479 expects `"Board scan encountered an error and could not complete."` (or the actual body text the mock returns) instead of `'Polling request failed with status 500'` | `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx:479` now asserts `toContain('Board scan encountered an error and could not complete.')`; `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx:89` defines `SCAN_ERROR_ENVELOPE.message` with the same string; `serve/cockpit/web/src/api/errorMessage.ts:20-29` returns the body `message`; `serve/cockpit/web/src/hooks/usePollingFetch.ts:67-73` throws that parsed message for non-2xx responses. Old fallback string no longer appears in the test file. | PASS |
| AC2: `npm test -- --run Shell_1372` passes | quality-runner scoped Vitest run for `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx`: 20 passed, 0 failed, 0 skipped; vitest exit 0. | PASS |
| AC3: No other test files modified | Builder notes scoped the change to `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx`; git inspection of commit `be1edb550667563359a1f75bfe0216a7f4fe4051` confirmed no other files in the change set. | PASS |

### Pass 1 Checks
- Test-writer audit: N/A. No `TestFromAC_*` tests exist in scope.
- Security review: N/A. Test-only change, no new runtime surface.
- Test integrity: PASS. No weakened `TestFromAC_*` coverage; changed assertion remains discriminating because it checks the exact body message now emitted by the code path.
- Test quality: PASS. The updated expectation would fail if the helper regressed to the old fallback string or any different message.
- Data safety: N/A. No persisted data, concurrency, or boundary-handling code changed.
- Implementation-aware gap analysis: PASS. Task scope is the single stale expectation plus adjacent explanatory comments; live file matches the traced body-message contract.
- Builder process quality: CLEAN. Single builder cycle, no prior review failures.

### Deductions
- None.

### Verdict
PASS -> docs | confidence 0.98

### Action
Advance to docs.
[[2026-05-08]]
## Docs Gate

### Step 0
- Task status: `docs` ✓
- Review Evidence section: present ✓

### Scope Classification

| File | Classification |
|------|---------------|
| `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx` | OUT-scope (frontend TypeScript test file) |

All changed files are OUT-scope. Proceeding to no-impact check.

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only change; no behavior/API/CLI/config/package structure changed; no IN-scope docs reference test internals |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase for this task |
| 5 | Diagram maintenance | No | N/A | Doc-index has no `describes` entry matching `Shell_1372.test.tsx` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

**No docs impact.** Test-only assertion fix (single `.tsx` test file) — all seven checklist items N/A.

### Files Updated
None.

### Child Tasks Created
None.

### Scratch Files
None found for task #1434 (`.owlbear/scratch/1434-*`).

### Commit
No documentation files changed; no commit needed.
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Assertion expects body message | Shell_1372.test.tsx:479 asserts toContain('Board scan encountered an error and could not complete.'); old fallback string removed; comment at L478 updated to "parsed body message from envelope" | PASS |
| AC2: npm test Shell_1372 passes | quality-runner full frontend run: Shell_1372 suite 20 passed, 0 failed | PASS |
| AC3: No other test files modified | git log commit be1edb55 shows only Shell_1372.test.tsx in changeset | PASS |

### Test Results
- Frontend (vitest full): 1107 passed, 2 failed (HealthBadgeRepair_1168 - unrelated pre-existing)
- Python (pytest full): 4882 passed, 214 failed (pre-existing migration/accessor tests - unrelated to frontend task)
- No cross-task regressions attributable to task 1434

### Lint
- ruff: 29 pre-existing violations (none in task scope)
- eslint: 1 pre-existing error + 3 warnings (none in Shell_1372.test.tsx)

### Commit Integrity
- Commit be1edb55: "test: update Shell_1372 stale 500-message assertion (#1434, builder)"
- Single file in changeset: serve/cockpit/web/src/__tests__/Shell_1372.test.tsx

### Reviewer Evidence
Present, detailed, PASS at 0.98. Thorough AC mapping with file/line evidence, git inspection, and multi-pass checks.

### Architect Quality: 5/5
Specific AC with exact old/new assertion strings, file/line references, and concrete pass gate. Code trace evidence in architecture review section. No gaps.

### Deduction Breakdown
- AC lines without evidence: 0
- Lint violations in scope: 0
- AC quality deduction: 0 (score 5)
- Missing reviewer evidence: 0
- Full-suite failures in task scope: 0
- Total deductions: 0

### Confidence: .98
### Action: archive