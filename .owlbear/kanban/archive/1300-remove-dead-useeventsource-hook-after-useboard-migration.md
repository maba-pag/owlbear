---
id: 1300
title: Remove dead useEventSource hook after useBoard migration
status: archived
priority: medium
created: 2026-05-02T19:48:32.676272+00:00
updated: 2026-05-03T16:48:12.988874+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1277
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

After #1277 refactors useBoard to use EventSourceProvider context, hooks/useEventSource.ts has zero production imports. Delete the hook file and its test files (useEventSource_1260.test.ts, useEventSource_1263.test.ts). Verify no other production code imports it first.

## Research

**Verified:** `hooks/useEventSource.ts` has zero production imports. Only consumers are its own test files (`useEventSource_1260.test.ts`, `useEventSource_1263.test.ts`). `useBoard.ts` was migrated to `useSSEEvent` from `EventSourceProvider` (task #1277, archived). Task #1278 (pending ActivityTab work) also uses the new pattern.

**Files to delete (3):**
1. `serve/cockpit/web/src/hooks/useEventSource.ts`
2. `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
3. `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts`

**Risk:** None — zero production consumers confirmed via exhaustive grep.
**Confidence:** 0.95
**No follow-up tasks needed** — task is atomic and ready for implementation.

## Acceptance Criteria

- [ ] `serve/cockpit/web/src/hooks/useEventSource.ts` deleted (td:0)
- [ ] `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` deleted — includes `TestFromAC_*` suites that tested the dead hook; deletion authorized (td:0)
- [ ] `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts` deleted — includes `TestFromAC_*` suites that tested the dead hook; deletion authorized (td:0)
- [ ] No production source file imports `useEventSource` (grep verification) (td:0)

## Architecture Review (cycle 2)

**Verdict:** APPROVE

**Context:** Reviewer rejected cycle 1 on two process grounds: (a) builder deleted `TestFromAC_*` suites without explicit AC authorization, and (b) blanket `npm test` gate was infeasible due to 57 pre-existing failures in ActivityTab/Shell suites tracked by #1278. Both are AC design defects, not implementation defects. Builder commit `f82de323` is correct.

### AC Refinements
1. Replaced blanket `npm test` gate with scoped grep verification (no production imports remain). The pre-existing ActivityTab/Shell failures are unrelated to this deletion and tracked by #1278.
2. Added explicit `TestFromAC_*` deletion authorization to test-file AC lines. These suites tested the dead hook being removed — their deletion is the task's purpose, not a side-effect.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Delete one dead hook + its dead tests |
| Interface clarity | PASS | 3 file deletions + grep gate |
| Dependency correctness | PASS | #1277 archived (completed) |
| Module layering | PASS | Deletion only |
| TDD compliance | PASS | All td:0 — mechanical removal |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | Zero production imports confirmed |
| Pattern consistency | PASS | Standard dead-code cleanup |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Frontend only |

### Challenge
Challenge: SKIP — all AC lines td:0.

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC to authorize TestFromAC_* deletion and replace infeasible blanket suite gate with scoped grep verification. Re-approved for review.
[[2026-05-03]]
Architecture review cycle 2 complete. Refined AC to fix two process gaps that caused reviewer rejection: (1) explicitly authorized TestFromAC_* suite deletion in test-file AC lines, (2) replaced infeasible blanket `npm test` gate with scoped grep verification. Builder commit f82de323 is correct — all implementation work already done. Test-writer: SKIP (all td:0).
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Task is a pure file-deletion: `hooks/useEventSource.ts` + 2 dead test files.
- Architecture review explicitly authorized: "Test-writer: SKIP (all td:0)".
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation: No new code edits were required in this cycle; AC-deliverable files were already removed in workspace state.
- AC verification:
  - Confirmed missing: `serve/cockpit/web/src/hooks/useEventSource.ts`
  - Confirmed missing: `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
  - Confirmed missing: `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts`
  - Confirmed no production imports/usages of `useEventSource` in `serve/cockpit/web/src` (excluding tests).
- Tests: 43 passed, 0 failed (scoped frontend verification).
- Coverage: 90.98% overall in scoped run; `EventSourceProvider.tsx` 95.09%, `useBoard.ts` 86.53%.
- Lint: clean in task-scoped quality-runner pass (`eslint: 0`, no violations).
- Evidence summary: Task is a td:0 dead-code cleanup and is now validated green with scoped tests/lint/coverage evidence.
- Commit: none in this cycle (no file modifications were made by builder in this pass).
[[2026-05-03]]
## Review Evidence
### Test Results
- Skipped by design. All AC lines are td:0, and the architecture review explicitly marked Test-writer: SKIP.

### Lint
- quality-runner broad pass on the frontend source returned unrelated baseline violations outside this task's diff.
- quality-runner narrow retry on the three AC-targeted paths returned an expected file-not-found instrument error because those paths are already deleted.
- Commit f82de323 changes exactly 3 paths, all deletions, so no surviving task-owned file remains to lint.

### Coverage
- Skipped for td:0 task.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. td:0 across all AC lines, with explicit authorization to delete the two TestFromAC suites.

#### Security Review
- No issues. This task only removes dead frontend code and tests; it introduces no new runtime behavior, inputs, or dependencies.

#### Test Integrity
- PASS. Commit f82de323 contains only three deletions and no modifications to surviving tests. The authorized TestFromAC deletions are the task deliverable, not weakened coverage.

#### Builder Process Quality
- CLEAN. One builder section, no retry loop pattern, no evidence of repetitive failed attempts.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Hook file deleted | git show --name-status f82de323 reports deletion; current workspace search returns no file at the target hook path | SKIP (td:0) | PASS |
| First dead hook test deleted | git show --name-status f82de323 reports deletion; current workspace search returns no file at the first target test path | SKIP (td:0) | PASS |
| Second dead hook test deleted | git show --name-status f82de323 reports deletion; current workspace search returns no file at the second target test path | SKIP (td:0) | PASS |
| No production source reference remains | Production-only grep for useEventSource under src returned no matches; the only remaining hits are test comments in [serve/cockpit/web/src/__tests__/useBoard_1277.test.ts](serve/cockpit/web/src/__tests__/useBoard_1277.test.ts#L5) and [serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx](serve/cockpit/web/src/__tests__/EventSourceProvider_1276.test.tsx#L248) | SKIP (td:0) | PASS |

### Deductions
- -0.03: task-scoped lint on the deleted paths is impossible after the fact, so lint evidence is indirect.
- -0.01: broad frontend lint baseline is noisy and required a scope reconstruction pass.

### Verdict
- PASS with confidence 0.94.

### Action
- Advanced to docs.
[[2026-05-03]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose docs (README.md, setup guides, share/README.md) reference `useEventSource` as a feature. The cockpit README covers backend API/engine surface only. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Task #1300 is a pure deletion — no new external patterns introduced. Existing source rows in `sources/overview.md` are historical attribution records (tasks #1235, #1260) and remain accurate as research provenance. |
| 4 | Research doc | No | N/A | No `.owlbear/research/1300-*.md` file produced; task body has inline `## Research` section only. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches deleted files. Footer updated from `85b3e028` → `3b1c83e0` (2026-05-03). Committed as `fd79a004`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | Deleted files are TypeScript source and test files — no IN-scope descriptive docs reference `useEventSource` as a current feature. Sources/research references are historical attribution archives, not live docs. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/hooks/useEventSource.ts` (deleted) | OUT | N/A — application source |
| `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` (deleted) | OUT | N/A — test file |
| `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts` (deleted) | OUT | N/A — test file |
| `share/diagrams/cockpit.excalidraw` | IN | Footer updated (describes-match) |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer timestamp updated to current commit `3b1c83e0`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files found for task #1300)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Hook file deleted | `file_search` returns no file; `git log` shows deletion in `f82de323` | PASS |
| Test file `useEventSource_1260` deleted | `file_search` returns no file; same commit | PASS |
| Test file `useEventSource_1263` deleted | `file_search` returns no file; same commit | PASS |
| No production import of `useEventSource` | `grep_search` on `serve/cockpit/web/src/**/*.ts` — only hits are test comments in `useBoard_1277.test.ts` and `EventSourceProvider_1276.test.tsx` | PASS |

### Test Results
- pytest: 3799 passed, 128 failed, 4 skipped — all failures pre-existing (guidance, migrate, server, engine, react-compiler modules); zero in task scope
- vitest: 936 passed, 13 failed — failures in Shell_966/ActivityTab suites tracked by #1278; zero in task scope
- ruff: 1 pre-existing T201 in copilot_auth.py (unrelated)
- eslint: 4 pre-existing issues (unrelated)
- quality-runner env fallback: 2× SIGINT; executed directly

### Architect Quality: 4/5
AC is clear and specific (file paths, td:0 across the board). Required one cycle-2 iteration to authorize TestFromAC deletion and replace infeasible blanket test gate — reasonable for a deletion task with process edge cases.

### Deduction Breakdown
- Starting: 1.00
- AC evidence: all 4 lines verified with independent tooling — no deduction
- Lint: pre-existing violations only, none in task scope — no deduction
- Full-suite failures: pre-existing across unrelated modules — no deduction
- Reviewer evidence: present, detailed, PASS verdict — no deduction
- Reviewer confidence .94 (below .95) on process-artifact deductions (can't lint deleted files): -.01

### Confidence: .99
### Action: archive

### Commits Verified
| Commit | Type | Files | Agent |
|--------|------|-------|-------|
| f82de323 | chore | 3 deleted files (hook + 2 tests) | builder |
| fd79a004 | docs | cockpit.excalidraw footer | doc-writer |