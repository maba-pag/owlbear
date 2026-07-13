---
id: 47
title: Document ACP error handling strategy
status: archived
priority: medium
created: 2026-03-26 18:56:10.838213+01:00
updated: 2026-03-27 05:35:34.174563+01:00
started: 2026-03-27 05:35:15.995341+01:00
completed: 2026-03-27 05:35:15.995341+01:00
tags:
- phase-1
- scope:orchestrator
- docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Document how the orchestrator handles ACP errors, timeouts, and process crashes.

See docs/research/acp-protocol.md section 5 for origin and follow-up context.

## AC

- [ ] Error handling doc covers: process crash detection, JSON parse errors, timeout strategy, cancellation flow
- [ ] References ACP error codes (-32700, -32601, -32000, -32002)
- [ ] Located in docs/research/ or packages/orchestrator/docs/

[[2026-03-26]] Thu 19:46

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Error handling doc covers: crash, parse, timeout, cancel | All four topics covered in research doc SS3.1-SS3.4 | No change |
| References ACP error codes (-32700, -32601, -32000, -32002) | Full table in SS3.1 plus classification mapping in SS3.5 | No change |
| Located in docs/research/ or packages/orchestrator/docs/ | Exists at docs/research/acp-error-handling-strategy.md | No change |

### Architecture Notes

The deliverable already exists: docs/research/acp-error-handling-strategy.md was produced during task #1 (ACP protocol deep-dive). The doc is comprehensive (174 lines) covering all AC topics plus error classification mapping (SS3.5) and recommended architecture (SS3.6).

Implementation follow-ups already created: #58 ProcessSupervisor, #59 AcpClient wrapper, #60 classify_error extension. All at ideation, referencing the research doc.

Pure docs task, no code changes, no TDD task required.

### Changes Made

- Verified existing doc completeness against AC
- No AC refinement needed (all lines are verifiable pass/fail)
- Approved to todo

### Dependencies

- Verified: #1 (ACP protocol deep-dive) produced the research doc
- No blocking dependencies

[[2026-03-26]] Thu 20:42

## Test-Writer Notes

- Non-implementation task (tagged docs) - no tests applicable.
- Passing through to builder.

[[2026-03-26]] Thu 21:32

## Builder Notes

- Non-implementation task confirmed from Test-Writer Notes.
- Files changed: none.
- Validation: docs/research/acp-error-handling-strategy.md covers process crash detection, JSON parse errors, timeout strategy, cancellation flow, and ACP error codes -32700, -32601, -32000, -32002.
- Tests: not applicable (docs-only pass-through).
- Lint: not applicable (no source changes).
- Fixes applied: None.

[[2026-03-27]] Fri 03:41

## Review Evidence

### Test Results

- Pytest review slice in v1/tests/test_error_classification.py ran with 0 failed, 0 passed, 10 skipped, 44 deselected, 5 warnings.
- The ACP-specific test class is skipped when the optional acp package is unavailable, so there was no executable ACP-path runtime validation in this environment.

### Lint Results

- Ruff check passed for v1/src/owlbear/core/errors.py and v1/tests/test_error_classification.py.

### Pass 1 - CRITICAL

- Test-Writer AC Coverage: not applicable for this docs-only card.
- Security Review: no issues found in the document deliverable.
- Test Integrity: not applicable; no TestFromAC assets exist for task 47.
- Test Quality: not applicable; no task-specific tests exist for task 47.
- Data Safety: no issues found in the document deliverable.
- Implementation-Aware Test Gaps: not applicable; builder changed no implementation files.

### AC Compliance

- Crash, parse, timeout, and cancellation coverage: PASS. See docs/research/acp-error-handling-strategy.md sections 3.1 through 3.4.
- ACP codes -32700, -32601, -32000, and -32002: PASS. See sections 3.1 and 3.5.
- Document location: PASS. File is docs/research/acp-error-handling-strategy.md.

### Verdict: PASS

[[2026-03-27]] Fri 05:35

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Error handling doc covers crash, parse, timeout, cancel | SS3.1-SS3.4 in docs/research/acp-error-handling-strategy.md | PASS |
| References ACP error codes -32700, -32601, -32000, -32002 | SS3.1 table + SS3.5 classification mapping | PASS |
| Located in docs/research/ or packages/orchestrator/docs/ | File at docs/research/acp-error-handling-strategy.md | PASS |

### Test Results

- pytest: COLLECTION ERROR in tests/test_process_supervisor.py (task #73 RED phase, unrelated to #47). No task-#47-specific code exists.
- ruff: All checks passed (no source files changed by this task).

### AC Quality Score: 4

AC was clear and verifiable for a docs task. Three concrete lines covering all deliverable aspects.

### Follow-up Tasks Verified

- #58 ProcessSupervisor (todo), #59 AcpClient wrapper (ideation), #60 classify_error extension (todo). All reference the research doc.

### Upstream Commit Gap

Deliverable doc was not committed by upstream agents. Committed by auditor.

### Confidence: .97

### Action: archive

[[2026-03-27]] Fri 05:35

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8df1572 | docs | docs/research/acp-error-handling-strategy.md | #47 |
