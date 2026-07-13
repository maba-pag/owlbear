---
id: 212
title: 'Update #86 research doc to reflect command-execution hook model'
status: archived
priority: medium
created: 2026-03-30 08:58:34.396954+02:00
updated: 2026-03-31 03:38:22.070141+02:00
started: 2026-03-31 03:37:34.212146+02:00
completed: 2026-03-31 03:37:34.212146+02:00
tags:
- docs
- hooks
- scope:agents
class: standard
archival_reason: completed
archival_refs: []
---

## Context

The VS Code hooks API (updated 3/25/2026) uses a command-execution model, not prompt-injection. docs/research/agent-scoped-hooks-pipeline-enforcement.md sections 3.2 and 4 contain incorrect YAML examples using `prompt:` and `when:` keys that no longer match the API.

See docs/research/stop-commit-guard-hooks-phase1.md for full analysis.

## Acceptance Criteria

- [ ] Update YAML examples in sections 3.2 and 4 to use `type: command` format
- [ ] Update section 3.3 constraint table: hooks now support blocking via exit code 2
- [ ] Note PascalCase event names (Stop, PreToolUse, PostToolUse)
- [ ] Keep the recommendation matrix conclusions unchanged (just fix format)

[[2026-03-30]] Mon 09:33
## Research
Updated docs/research/agent-scoped-hooks-pipeline-enforcement.md per AC:
- Sections 3.2 and 4: all YAML examples now use type: command format with PascalCase event names
- Section 3.3: constraint table revised (exit code 2 blocking, permissionDecision deny, command execution)
- Section 3.1: expanded from 3 to 8 hook types per current API
- Section 1: context table updated for command-execution mechanism
- Recommendation matrix conclusions unchanged
- Sources: VS Code Hooks docs (3/25/2026) confirmed via live fetch
No new follow-up tasks needed (existing #209, #210, #211 cover the implementation phases).

[[2026-03-30]] Mon 09:46
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Update YAML examples in 3.2 and 4 to type: command format | Verified: all YAML blocks use type: command with PascalCase events | None |
| Update 3.3 constraint table: exit code 2 blocking | Verified: table includes exit code 2, permissionDecision deny, Stop decision block | None |
| Note PascalCase event names | Verified: 3.1 table and all YAML examples use PascalCase | None |
| Keep recommendation matrix conclusions unchanged | Verified: Phase 1/2 plan and skip list unchanged | None |

### Architecture Notes
Docs-only task: no code, no TDD requirement. Researcher already applied all four AC changes to docs/research/agent-scoped-hooks-pipeline-enforcement.md (confirmed by reading the file). Task is atomic (single doc update) and correctly scoped. Builder can verify in-place and advance.

### Changes Made
- Approved to todo

### Dependencies
- Verified: no code dependencies (docs-only)
- Downstream: #209, #210, #211 reference this doc but do not depend on this task

[[2026-03-30]] Mon 13:17
pass-through

[[2026-03-30]] Mon 13:17
## Test-Writer Notes
- Non-implementation task (tagged docs) - no tests applicable.
- Passing through to builder.

[[2026-03-30]] Mon 14:00
## Builder Notes
- Non-implementation task (docs-only) — no code changes needed.
- Verified docs/research/agent-scoped-hooks-pipeline-enforcement.md contains all AC changes:
  - Sections 3.2 and 4: YAML examples use type: command with PascalCase event names
  - Section 3.3 constraint table: exit code 2 blocking documented
  - PascalCase event names (Stop, PreToolUse, PostToolUse, SubagentStop) present
  - Recommendation matrix conclusions unchanged
- Passing through to review.

[[2026-03-30]] Mon 14:38
## Review Evidence

Docs-only task; no tests or lint applicable.

### AC Compliance

AC1 YAML type:command format: Sections 3.2 and 4 all use type: command with PascalCase event keys. PASS
AC2 Exit code 2 blocking: Section 3.3 table has Exit code 2 blocks row plus PreToolUse can deny and Stop hook can block rows. PASS
AC3 PascalCase event names: Section 3.1 table lists all 8 hooks in PascalCase; YAML examples follow. PASS
AC4 Recommendation matrix unchanged: C1=Adopt Phase 2, C2=Skip, C3=Adopt Phase 1, C4=Skip, C5=Adopt Phase 2. PASS

### Verdict: PASS confidence .92

[[2026-03-30]] Mon 14:38
## Review Evidence

Docs-only task; no tests or lint applicable.

### AC Compliance

AC1 YAML type:command format: Sections 3.2 and 4 all use type: command with PascalCase event keys. PASS
AC2 Exit code 2 blocking: Section 3.3 table has Exit code 2 blocks row plus PreToolUse can deny and Stop hook can block rows. PASS
AC3 PascalCase event names: Section 3.1 table lists all 8 hooks in PascalCase; YAML examples follow. PASS
AC4 Recommendation matrix unchanged: C1=Adopt Phase 2, C2=Skip, C3=Adopt Phase 1, C4=Skip, C5=Adopt Phase 2. PASS

### Verdict: PASS confidence .92

[[2026-03-30]] Mon 15:13
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Docs-only research doc revision; no behavior/convention change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'Update #86 Research Doc (Task #212)' already present at line 3102 with VS Code Hooks docs and Custom Agents docs attribution |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc archived/linked | Yes | Pass | docs/research/agent-scoped-hooks-pipeline-enforcement.md exists and all 4 AC items verified by reviewer (confidence .92) |

### Files Updated
- None (all changes were applied by researcher in prior stage)

### Scratch Files Cleaned
- None found (no docs/scratch/212-* files exist)

[[2026-03-30]] Mon 15:48
## Audit
### AC Verification
AC1 YAML type:command format in 3.2 and 4: 8 occurrences of type: command confirmed via grep. PASS
AC2 Constraint table exit code 2: Line 89 documents exit code 2 blocking for PreToolUse, PostToolUse, Stop. Line 90 documents PreToolUse permissionDecision deny. PASS
AC3 PascalCase event names: Section 3.1 table uses PascalCase (PreToolUse, PostToolUse, SubagentStop, Stop). All YAML examples use PascalCase. PASS
AC4 Recommendation matrix unchanged: C1 Adopt Phase 2, C2 Skip, C3 Adopt Phase 1, C4 Skip, C5 Adopt Phase 2. Matches original. PASS

### Test Results
- pytest (task-specific): 13 passed, 1 FAILED (test_document_covers_pretooluse expects camelCase preToolUse but doc now uses PascalCase PreToolUse per AC3)
- pytest (full suite): 134 failures, all unrelated to #212 except the above
- ruff: not applicable (docs-only task)

### Regression
test_agent_scoped_hooks_research.py line 39 asserts preToolUse (camelCase). The doc was updated to PascalCase per AC3. The test needs updating to match (e.g., case-insensitive check or PascalCase string). This is a 1-line fix.

### AC Quality Score: 4/5
AC was specific and verifiable. Minor gap: AC did not mention updating the existing test from #86 that validates this document.

### Deduction breakdown
- -.05 task-scope test failure (test_document_covers_pretooluse broken by PascalCase change)
### Confidence: .95
### Action: reject to review (task-scope test failure needs fix before archive)

[[2026-03-30]] Mon 17:43
## Review Evidence (2nd cycle)

### Test Results
- pytest: 1 failed, 13 passed
- FAILED: test_document_covers_pretooluse -- asserts camelCase preToolUse but doc uses PascalCase PreToolUse per AC3. Builder did not update the test.
- Note: test_document_covers_posttooluse passes only because doc line 36 retains pre/postToolUse in prose; test does not verify correct PascalCase term.

### Lint Results
- ruff: not applicable (docs-only task)

### AC Compliance
AC1 YAML type:command in 3.2/4: 8 occurrences confirmed by grep. PASS
AC2 Section 3.3 exit code 2: Line 89 documents hard blocking for PreToolUse, PostToolUse, Stop. PASS
AC3 PascalCase event names: Section 3.1 table and all YAML examples use PascalCase. PASS
AC4 Recommendation matrix unchanged: C1=Adopt Phase 2, C2=Skip, C3=Adopt Phase 1, C4=Skip, C5=Adopt Phase 2. PASS

### Failure: test not updated to match PascalCase doc changes
test_document_covers_pretooluse (line 39) still checks for preToolUse (camelCase). Document is correct per AC3; test is stale.
Required fix: update assertion to PreToolUse (PascalCase). Also update test_document_covers_posttooluse to check PostToolUse directly (currently relies on accidental substring match).

### Verdict: FAIL confidence .88

[[2026-03-30]] Mon 18:18
## Test-Writer Notes (retry)
- Retry reason: reviewer (2nd cycle) cited stale test assertions, not missing tests
- test_document_covers_pretooluse: updated from camelCase preToolUse to PascalCase PreToolUse per AC3
- test_document_covers_posttooluse: updated from camelCase postToolUse to PascalCase PostToolUse (was passing via accidental substring match)
- Result: 14 passed, 0 failed (stale assertions corrected; doc is already correct)
- ruff: clean

[[2026-03-30]] Mon 21:30
## Builder Notes (retry)\n- Non-implementation task (docs-only) — no code changes needed.\n- test_document_covers_pretooluse: now checks PascalCase PreToolUse (updated by test-writer retry).\n- test_document_covers_posttooluse: now checks PascalCase PostToolUse (updated by test-writer retry).\n- pytest: 14 passed, 0 failed.\n- ruff: not applicable (docs-only).\n- Passing through to review.

[[2026-03-31]] Tue 03:37
## Audit (2nd cycle)
### AC Verification
AC1 YAML type:command in 3.2/4: 8 occurrences confirmed via grep. PASS
AC2 Constraint table exit code 2: Line 89 documents blocking for PreToolUse, PostToolUse, Stop. PASS
AC3 PascalCase event names: Section 3.1 table and all YAML examples use PascalCase. Tests updated to match. PASS
AC4 Recommendation matrix unchanged: C1-C5 unchanged. PASS

### Test Results
- pytest (task-specific): 14 passed, 0 failed
- pytest (full suite): 198 failed, 1849 passed -- no failures in task scope
- ruff: not applicable (docs-only)

### Upstream Commits Verified
- 47a618c test: fix stale hook-name assertions to PascalCase (#212, test-writer)
- 884bcb6 docs: update hooks research with command-execution model (#86, auditor)

### AC Quality Score: 4/5
AC was specific and verifiable. Minor gap: AC did not mention updating existing test from #86.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archived

[[2026-03-31]] Tue 03:38
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b9c1428 | chore | kanban/tasks/212-*.md | #212 |
