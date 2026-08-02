---
id: 434
title: Add audit-centric dispatch-cycle trace ID
status: archived
priority: medium
created: 2026-03-30 21:37:56.972591+02:00
updated: 2026-04-03 01:24:26.491086+02:00
started: 2026-04-03 01:23:51.339877+02:00
completed: 2026-04-03 01:23:51.339877+02:00
tags:
- scope:orchestrator
- phase-2
- type:build
depends_on:
- 509
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Add a unique cycle ID (UUID4 hex) to the orchestrator dispatch loop for debugging and correlation. Audit-only approach — no Channel A/B protocol format changes. Per docs/research/dispatch-cycle-trace-id.md Option A (.80 confidence).

See docs/research/deer-flow-adoptable-patterns.md S3C for original pattern analysis.
See docs/research/dispatch-cycle-trace-id.md for approach comparison and recommendation.

Merged: #456 (research follow-up) deleted as redundant — this task is canonical.

Note for test-writer/builder: ~4 test files construct DispatchEvent/CompletionEvent directly (test_audit_log, test_analysis, test_analysis_package, test_dispatch_audit_wiring). These need updating for the new field.

## Acceptance Criteria
- [ ] DispatchEvent and CompletionEvent in packages/orchestrator/src/owlbear/audit/models.py gain a cycle_id: str = "" field; audit_adapter TypeAdapter auto-reflects at import time (no explicit rebuild needed)
- [ ] run_loop() in packages/orchestrator/src/owlbear/orchestrator/loop.py generates uuid4().hex ONCE per cycle iteration (all waves in that cycle share the same cycle_id); stored as local variable, not in LoopState
- [ ] cycle_id passed from run_loop() to dispatch_wave() and dispatch_entry() via explicit keyword parameter (not LoopState mutation)
- [ ] dispatch_entry() sets cycle_id on both DispatchEvent and CompletionEvent it constructs (note: CompletionEvent does not currently have session_id, so cycle_id will be its only correlation field)
- [ ] AuditLog.query() in packages/orchestrator/src/owlbear/audit/log.py accepts optional cycle_id: str | None = None filter; None means no filter (returns all events including legacy with cycle_id="")
- [ ] No changes to Channel A/B signal format, agent .md files, or instruction files
- [ ] Existing tests updated for new cycle_id field; new tests verify cycle_id propagation through dispatch_entry and dispatch_wave

## Architecture Review
**Verdict:** APPROVED (with AC refinement + merge)
**DR Verification:** N/A — T1 outcome (additive audit improvement, no T3 triggers)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| cycle ID per dispatch wave | Ambiguous per-wave vs per-cycle | Rewritten: uuid4().hex ONCE per cycle, all waves share it |
| Channel A/B inclusion | Contradicts research (Channel A is write-only) | Rewritten: audit-only, no Channel A/B changes |
| Audit log correlation | Correct concept, missing specifics | Rewritten: cycle_id on both event models + query filter |

### Architecture Notes
Research doc evaluated 3 approaches. Option A (audit-centric) at .80 confidence. Option B (full protocol) rejected: Channel A write-only. Option C (OTel) rejected: YAGNI.

Integration points: DispatchEvent (6 fields, has session_id), CompletionEvent (8 fields, no session_id), run_loop() with LoopState, dispatch_entry() constructs both events, AuditLog.query() with 3 existing filters.

Pattern: cycle_id threads via explicit kwarg (same as audit_log kwarg pattern). Per-cycle granularity for correct grouping.

### Changes Made
- Rewrote AC: audit-only scope, 7 verifiable lines, explicit file paths
- Title: "Add audit-centric dispatch-cycle trace ID"
- Tags: scope:orchestrator, phase-2, type:build
- Deleted #456 (redundant follow-up, merged)
- Created #509 (TDD test task); #434 depends on #509
- Approved both to todo

### Dependencies
- Created: #509 (test task, #434 depends on it)
- Deleted: #456 (merged into #434)

### Challenge Results
- Challenger: reconsider (confidence .62)
- Key challenges: CompletionEvent has no session_id (accepted, AC clarified); session_name dropped (rebutted: cli.py separate path, not applicable); per-cycle vs per-wave (accepted, AC explicit); merge undefined (resolved); test blast radius (noted in body)
- Architect response: 4/5 accepted and revised. T1 classification maintained.

[[2026-04-01]] Wed 01:44
## Test-Writer Notes
- Test file: tests/test_dispatch_cycle_trace_id.py
- Classes: TestFromAC_CycleIdModels, TestFromAC_CycleIdSignatures, TestFromAC_CycleIdDispatchEntry, TestFromAC_CycleIdDispatchWave, TestFromAC_CycleIdRunLoop, TestFromAC_CycleIdAuditQuery
- Tests per category: happy 16, edge 6, error 6, boundary 4
- Total: 32 tests, all FAIL
- ruff: clean
- AC coverage: AC1 models(12), AC2 run_loop(3), AC3 signatures(4), AC4 dispatch_entry(7), AC5 audit_query(7), AC6 no-format-change(1)

[[2026-04-02]] Thu 06:27
## Builder Notes
- Files changed: already committed in 7892ea7 (feat: add cycle_id propagation #509, builder)
- Tests: 32 passed (tests/test_dispatch_cycle_trace_id.py), all TestFromAC_* classes green
- Related tests: test_dispatch_audit_wiring.py 16 passed, test_audit_log.py 35 passed (1 pre-existing fixture error unrelated to #434)
- Lint: ruff clean on audit/ and loop.py
- Coverage: models.py 100%, log.py 67%, loop.py 67% (full coverage with combined test suite)
- Evidence: implementation was pre-committed by #509 builder; #434 tests verify AC1-AC6 end-to-end
- Fixes applied: None - implementation already in place

[[2026-04-02]] Thu 07:31
## Review Evidence
See docs/scratch/434-reviewer.md for full evidence.

Verdict: FAIL (.87) - AC4 error paths in dispatch_entry() untested. Lines 142-156 (new_session failure) and 176-191 (prompt failure) both set cycle_id on CompletionEvent but are unreached by tests. Two TestBuilderDiscovered tests required.

[[2026-04-02]] Thu 08:26
## Test-Writer Notes (retry)\n- Retry reason: reviewer FAIL (.87) cited 2 MISSING tests for AC4 error paths\n- Added: 2 new tests for dispatch_entry() error paths in TestFromAC_CycleIdDispatchEntry\n  - test_cycle_id_on_completion_event_when_session_create_fails\n  - test_cycle_id_on_completion_event_when_prompt_fails\n- Preserved: 32 existing tests (all PASS)\n- New tests: PASS (implementation already correct; tests guard against regression)\n- ruff: clean\n- Total: 34 tests, 34 pass\n- AC4 coverage: all 3 CompletionEvent construction paths now tested

[[2026-04-02]] Thu 18:59
## Builder Notes (retry)\n- Files changed: tests/test_dispatch_cycle_trace_id.py (committed 6102a7c)\n- Reason: test-writer added 2 error-path tests (AC4 retry) that were uncommitted\n- Tests: 34 passed (was 32; +2 error-path tests from test-writer retry)\n- New tests: test_cycle_id_on_completion_event_when_session_create_fails, test_cycle_id_on_completion_event_when_prompt_fails\n- Lint: ruff clean on audit/, loop.py, test file\n- Coverage: models.py 100%, log.py 67%, loop.py 74%\n- Implementation: already in place (7892ea7), no src changes needed\n- Fixes applied: None

[[2026-04-02]] Thu 22:43
## Review Evidence (Cycle 2 -- Retry)
See docs/scratch/434-reviewer.md for full evidence.

Verdict: PASS (.95) - 34/34 tests pass, ruff clean, all 7 AC lines verified. 2 new error-path tests from test-writer retry fully address previous FAIL. All TestFromAC classes preserved or strengthened.

[[2026-04-03]] Fri 01:19
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: cycle_id field on both models | models.py L22 (DispatchEvent), L38 (CompletionEvent); audit_adapter L44 auto-reflects | PASS |
| AC2: uuid4().hex once per cycle, local var | loop.py L397 cycle_id=uuid4().hex; LoopState (L85-92) has no cycle_id field | PASS |
| AC3: explicit cycle_id kwarg | dispatch_entry L133, dispatch_wave L331, _run_sequential L264, _run_concurrent L290 | PASS |
| AC4: cycle_id on both events in dispatch_entry | DispatchEvent L161; CompletionEvent L179, L199, L222 (all 3 paths) | PASS |
| AC5: AuditLog.query() cycle_id filter | log.py L48 param, L73-74 filter logic | PASS |
| AC6: No Channel A/B format changes | Only audit/ and loop.py modified; no agent/instruction changes | PASS |
| AC7: Tests updated + new propagation tests | 34/34 pass (32 original + 2 error-path retry); related suites pass | PASS |

### Test Results
- pytest (task scope): 34 passed, 0 failed
- pytest (full suite): 2344 passed, 223 failed, 8 skipped -- 0 failures in task scope; all 223 are pre-existing
- ruff: All checks passed (audit/, loop.py, test file)

### Reviewer Evidence
Cycle 2 PASS at .95 with detailed AC table, test quality matrix, security review, and implementation-aware gap analysis. No concerns.

### AC Quality Score: 5/5
AC was specific (7 lines with file paths), complete (covered all integration points), and led to clean implementation. Architect rewrote AC after challenger feedback. No improvisation needed.

### Deduction breakdown
Starting at 1.0:
- All 7 AC lines verified with code evidence: no deduction
- Lint clean: no deduction
- AC quality 5: no deduction
- Reviewer evidence present and thorough: no deduction
- No task-scope test failures: no deduction

### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 01:19
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: cycle_id field on both models | models.py L22 (DispatchEvent), L38 (CompletionEvent); audit_adapter L44 auto-reflects | PASS |
| AC2: uuid4().hex once per cycle, local var | loop.py L397 cycle_id=uuid4().hex; LoopState (L85-92) has no cycle_id field | PASS |
| AC3: explicit cycle_id kwarg | dispatch_entry L133, dispatch_wave L331, _run_sequential L264, _run_concurrent L290 | PASS |
| AC4: cycle_id on both events in dispatch_entry | DispatchEvent L161; CompletionEvent L179, L199, L222 (all 3 paths) | PASS |
| AC5: AuditLog.query() cycle_id filter | log.py L48 param, L73-74 filter logic | PASS |
| AC6: No Channel A/B format changes | Only audit/ and loop.py modified; no agent/instruction changes | PASS |
| AC7: Tests updated + new propagation tests | 34/34 pass (32 original + 2 error-path retry); related suites pass | PASS |

### Test Results
- pytest (task scope): 34 passed, 0 failed
- pytest (full suite): 2344 passed, 223 failed, 8 skipped -- 0 failures in task scope; all 223 are pre-existing
- ruff: All checks passed (audit/, loop.py, test file)

### Reviewer Evidence
Cycle 2 PASS at .95 with detailed AC table, test quality matrix, security review, and implementation-aware gap analysis. No concerns.

### AC Quality Score: 5/5
AC was specific (7 lines with file paths), complete (covered all integration points), and led to clean implementation. Architect rewrote AC after challenger feedback. No improvisation needed.

### Deduction breakdown
Starting at 1.0:
- All 7 AC lines verified with code evidence: no deduction
- Lint clean: no deduction
- AC quality 5: no deduction
- Reviewer evidence present and thorough: no deduction
- No task-scope test failures: no deduction

### Confidence: .98
### Action: archive

-t

[[2026-04-03]] Fri 01:23
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: cycle_id field on both models | models.py L22 (DispatchEvent), L38 (CompletionEvent); audit_adapter L44 auto-reflects | PASS |
| AC2: uuid4().hex once per cycle, local var | loop.py L397 cycle_id=uuid4().hex; LoopState (L85-92) has no cycle_id field | PASS |
| AC3: explicit cycle_id kwarg | dispatch_entry L133, dispatch_wave L331, _run_sequential L264, _run_concurrent L290 | PASS |
| AC4: cycle_id on both events in dispatch_entry | DispatchEvent L161; CompletionEvent L179, L199, L222 (all 3 paths) | PASS |
| AC5: AuditLog.query() cycle_id filter | log.py L48 param, L73-74 filter logic | PASS |
| AC6: No Channel A/B format changes | Only audit/ and loop.py modified; no agent/instruction changes | PASS |
| AC7: Tests updated + new propagation tests | 34/34 pass (32 original + 2 error-path retry); related suites pass | PASS |

### Test Results
- pytest (task scope): 34 passed, 0 failed
- pytest (full suite): 2344 passed, 223 failed, 8 skipped -- 0 failures in task scope; all 223 are pre-existing
- ruff: All checks passed (audit/, loop.py, test file)

### Reviewer Evidence
Cycle 2 PASS at .95 with detailed AC table, test quality matrix, security review, and implementation-aware gap analysis. No concerns.

### AC Quality Score: 5/5
AC was specific (7 lines with file paths), complete (covered all integration points), and led to clean implementation. Architect rewrote AC after challenger feedback. No improvisation needed.

### Deduction breakdown
Starting at 1.0:
- All 7 AC lines verified with code evidence: no deduction
- Lint clean: no deduction
- AC quality 5: no deduction
- Reviewer evidence present and thorough: no deduction
- No task-scope test failures: no deduction

### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 01:24
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 5f9b7ab | chore | kanban/tasks/434-*.md | #434 |
