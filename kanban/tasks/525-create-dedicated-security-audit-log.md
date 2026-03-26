---
id: 525
title: Create dedicated security audit log
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:32.6960467+01:00
updated: 2026-03-26T12:52:18.1369533+01:00
started: 2026-03-07T00:06:04.8208398+01:00
completed: 2026-03-26T12:52:11.4240836+01:00
tags:
    - audit
    - security
    - observability
depends_on:
    - 847
class: standard
---

SEC-14: Security events for runtime safety enforcement currently mix into standard rotating logs, so blocked actions and approval decisions can be lost in rotation.

Research complete. See docs/research/security-audit-log.md.

Scope for this task is runtime emitters only: CommandSafetyGuard, ApprovalGateToolset, and TerminalToolset. Auth login events are out of scope here and are handled by #848.

This implementation task depends on the RED contract in #847 and must satisfy tests/test_security_audit_log.py.

## AC
1. Add src/owlbear/safety/audit_log.py with a Pydantic SecurityEvent model containing exactly these fields: timestamp, event_type, severity, actor, session_id, tool_name, detail, metadata. tool_name may be None.
2. Add SecurityAuditLog(JsonlStore[SecurityEvent]) that writes to {workspace}/.owlbear/security_audit.jsonl, defaults max_entries to 500_000, and trims to the newest max_entries after overflow.
3. SecurityAuditLog.log(...) appends a single SecurityEvent and auto-generates an ISO-8601 timestamp when the caller does not provide one.
4. Bootstrap creates one workspace-scoped SecurityAuditLog instance and injects an audit sink into CommandSafetyGuard, ApprovalGateToolset, and TerminalToolset. src/owlbear/core/command_guard.py and src/owlbear/tools/terminal.py must not import owlbear.safety.audit_log directly.
5. Blocked shell commands and blocked file-path writes emit command_blocked through the injected sink and preserve existing BlockedCommandError behavior.
6. ApprovalGateToolset emits approval_granted, approval_denied, approval_timeout, and approval_granted_all through the injected sink while preserving current prompt flow, grant behavior, return values, and existing POST_TOOL_USE hook payloads.
7. TerminalToolset emits path_escape_blocked when working_dir escapes the workspace and preserves the current PermissionError behavior. Valid working_dir values do not emit audit events.
8. Audit emission is best-effort: sink failures are swallowed at the audit-emission boundary and do not change existing block, allow, deny, timeout, or path-escape behavior.
9. Implementation passes tests/test_security_audit_log.py plus existing affected guard/gate/terminal tests, and ruff is clean for changed files.

[[2026-03-21]] Sat 04:43
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| security events in dedicated file with longer retention | Too vague to verify; did not define scope, schema, emitters, retention semantics, or TDD dependency. | Rewritten into 9 explicit AC lines. |

### Architecture Notes
- Research and existing RED tests agree on JsonlStore reuse; that matches src/owlbear/core/jsonl_store.py and src/owlbear/memory/error_journal.py.
- Scope is runtime emitters only for this task: CommandSafetyGuard in src/owlbear/core/command_guard.py, ApprovalGateToolset in src/owlbear/safety/gate.py, and TerminalToolset in src/owlbear/tools/terminal.py. Auth logging already has a separate follow-up task in #848.
- Layering constraint: src/owlbear/core/command_guard.py and src/owlbear/tools/terminal.py must receive an injected sink or callback; they must not import owlbear.safety.audit_log directly. Bootstrap is the assembly root and owns creation of the workspace-scoped SecurityAuditLog instance.
- Best-effort audit logging is a side-channel, not a control path. Sink failures must be swallowed at a narrow emission boundary so existing guard, approval, and path-confinement behavior remains unchanged.
- No further split is required at this point because the live RED contract in tests/test_security_audit_log.py already couples the store and runtime emitter wiring into one implementation task. Splitting now would create board and test-contract drift.

### Changes Made
- Replaced the task body with explicit runtime-only scope and 9 verifiable AC lines.
- Added dependency on #847 so TDD order is explicit on the board.
- Verified #848 already isolates auth success/failure logging as a separate follow-up.

### Dependencies
- Added: #847 (RED tests for runtime security audit log)
- Verified: #848 remains the separate auth follow-up depending on #525

[[2026-03-26]] Thu 06:37
## Test-Writer Notes
- Test file: tests/test_security_audit_log.py (written in paired RED task #847, archived)
- Classes: TestFromAC_SecurityAuditLogStore, TestFromAC_CommandBlockedAuditEvent, TestFromAC_ApprovalDecisionAuditEvents, TestFromAC_PathEscapeAuditEvent, TestFromAC_BestEffortAuditLogging, TestFromAC_NoConcreteSafetyImport, TestFromAC_BootstrapAuditSinkWiring
- Total: 44 tests, all PASS (green on arrival -- implementation already present)
- Situation: #847 was a dedicated RED task that pre-wrote the contract tests. Builder completed the GREEN phase before this test-writer slot ran. All 44 tests pass against the existing implementation.
- No new tests needed. No fabricated failing tests. Passing through per green-on-arrival protocol.
- ruff: clean (verified in #847 audit trail)
- AC coverage:
  AC1 (SecurityEvent schema): TestFromAC_SecurityAuditLogStore (12 tests)
  AC2 (SecurityAuditLog path + max_entries): TestFromAC_SecurityAuditLogStore
  AC3 (log() appends + auto-timestamp): TestFromAC_SecurityAuditLogStore
  AC4 (bootstrap wiring): TestFromAC_BootstrapAuditSinkWiring (5 tests)
  AC5 (command_blocked emit): TestFromAC_CommandBlockedAuditEvent (8 tests)
  AC6 (approval events): TestFromAC_ApprovalDecisionAuditEvents (9 tests)
  AC7 (path_escape_blocked): TestFromAC_PathEscapeAuditEvent (5 tests)
  AC8 (best-effort sink): TestFromAC_BestEffortAuditLogging (5 tests)
  AC9 (ruff clean, tests pass): covered

[[2026-03-26]] Thu 07:22
## Builder Notes
- Files changed: None. No source or test code changes were needed.
- Tests: 44 passed in tests/test_security_audit_log.py; 331 passed in related regressions (tests/test_command_guard.py, tests/test_approval_gate.py, tests/test_terminal_tools.py, tests/test_bootstrap.py).
- Coverage: task contract run reported audit_log.py 100, command_guard.py 95, gate.py 93.
- Lint: ruff check passed for task-relevant source and test files.
- Evidence: Green-on-arrival task. Test-Writer Notes document that RED was overtaken by prior implementation from paired task 847.
- Fixes applied: None (pass-through with verification evidence).

[[2026-03-26]] Thu 07:58
## Review Evidence
- Verdict: FAIL (confidence .86).
- Pytest: 375 passed in 85.58s on tests/test_security_audit_log.py, tests/test_command_guard.py, tests/test_approval_gate.py, tests/test_terminal_tools.py, and tests/test_bootstrap.py with scoped coverage.
- Ruff: All checks passed on the task-relevant source and test files.
- TestFromAC comparison: Git history for tests/test_security_audit_log.py shows only the two #847 test-writer commits, while implementation commit ce07053 changed only src/owlbear/bootstrap/__init__.py, src/owlbear/bootstrap/hooks.py, and src/owlbear/bootstrap/toolsets.py. No builder modification of the TestFromAC classes was found.
- AC1: Implemented in src/owlbear/safety/audit_log.py starting at line 18, but the mapped test at tests/test_security_audit_log.py lines 89-102 is LAX. It only checks hasattr for required names and never asserts that the field set is exact, so extra schema fields would still pass.
- AC2: Implemented in src/owlbear/safety/audit_log.py starting at lines 31 and 86; exercised by tests/test_security_audit_log.py lines 120-149 and 176-201.
- AC3: Implemented in src/owlbear/safety/audit_log.py starting at line 48, but the mapped test at tests/test_security_audit_log.py lines 152-174 is LAX. It asserts only that timestamp is a non-empty string and never validates ISO-8601 format, so malformed timestamps would still pass.
- AC4: Implemented in src/owlbear/bootstrap/__init__.py lines 191, 199, and 221, src/owlbear/bootstrap/hooks.py lines 105, 141, and 167, and src/owlbear/bootstrap/toolsets.py lines 48, 318, 344, and 369; exercised by tests/test_security_audit_log.py lines 549-725.
- AC5: Implemented in src/owlbear/core/command_guard.py lines 171-218; exercised by tests/test_security_audit_log.py lines 210-268 and tests/test_command_guard.py.
- AC6: Implemented in src/owlbear/safety/gate.py lines 127-235; event-type coverage exists in tests/test_security_audit_log.py lines 280-372, and existing hook payload behavior remains covered by tests/test_approval_gate.py lines 361-404 and 562-589.
- AC7: Implemented in src/owlbear/tools/terminal.py lines 223-303; exercised by tests/test_security_audit_log.py lines 374-418 and confinement regressions in tests/test_terminal_tools.py lines 231-293.
- AC8: Best-effort sink swallowing is implemented in src/owlbear/core/command_guard.py lines 204-219, src/owlbear/safety/gate.py lines 221-235, and src/owlbear/tools/terminal.py lines 289-303; exercised by tests/test_security_audit_log.py lines 429-498.
- AC9: Scoped pytest passed and task-scoped ruff is clean.
- Decision: Return to todo because AC1 and AC3 do not have strict regression tests. The current implementation matches the source, but the review gate cannot PASS a card whose contract tests would still go green after those ACs are violated.

[[2026-03-26]] Thu 11:30
## Builder Notes
- Files changed: none (pass-through verification only)
- Tests: tests/test_security_audit_log.py passed, 46 tests
- Coverage: unavailable in this run because pytest startup aborted in tests/conftest.py while loading optional dependency chain from qdrant_client and ended with KeyboardInterrupt
- Lint: ruff clean for src/owlbear/safety/audit_log.py, src/owlbear/core/command_guard.py, src/owlbear/safety/gate.py, src/owlbear/tools/terminal.py, src/owlbear/bootstrap/__init__.py, src/owlbear/bootstrap/hooks.py, src/owlbear/bootstrap/toolsets.py, tests/test_security_audit_log.py
- Evidence: pytest reported 46 passed in 2.88s; ruff reported all checks passed
- Fixes applied: none required, implementation already satisfied AC

[[2026-03-26]] Thu 12:12
## Review Evidence
- Verdict: PASS (confidence .92).
- Pytest: 377 passed, 0 failed, 4 warnings in 76.40s across tests/test_security_audit_log.py, tests/test_command_guard.py, tests/test_approval_gate.py, tests/test_terminal_tools.py, and tests/test_bootstrap.py. Direct pytest startup was unstable in this workspace, so verification used a read-only Python wrapper with Pydantic plugins disabled, pytest plugin autoload disabled, pytest_asyncio loaded manually, and qdrant_client treated as missing for the process. The warnings were the expected qdrant skip warnings from tests/conftest.py.
- Ruff: task-scoped ruff passed on src/owlbear/safety/audit_log.py, src/owlbear/core/command_guard.py, src/owlbear/safety/gate.py, src/owlbear/tools/terminal.py, src/owlbear/bootstrap/__init__.py, src/owlbear/bootstrap/hooks.py, src/owlbear/bootstrap/toolsets.py, and tests/test_security_audit_log.py.
- Coverage: not used as gating evidence. Two coverage-instrumented runs aborted with KeyboardInterrupt during unrelated import startup, so percentages were not trustworthy.
- Test-writer coverage:
  AC1: tests/test_security_audit_log.py:84 and 204 verify src/owlbear/safety/audit_log.py:18.
  AC2: tests/test_security_audit_log.py:120, 126, 176, and 199 verify src/owlbear/safety/audit_log.py:31 and 86.
  AC3: tests/test_security_audit_log.py:136, 152, and 226 verify src/owlbear/safety/audit_log.py:48.
  AC4: tests/test_security_audit_log.py:609, 621, 637, 702, and 728 verify src/owlbear/bootstrap/__init__.py:191, 199, 212, and 221; src/owlbear/bootstrap/hooks.py:104, 141, and 167; and src/owlbear/bootstrap/toolsets.py:47, 318, 344, and 369.
  AC5: tests/test_security_audit_log.py:259, 265, 273, 282, 289, 297, and 313 verify src/owlbear/core/command_guard.py:166, 171, 180, 185, and 194.
  AC6: tests/test_security_audit_log.py:346, 351, 360, 369, 378, 387, 395, and 404 verify src/owlbear/safety/gate.py:127, 147, 171, 196, and 212. Existing POST_TOOL_USE payload regressions still pass in tests/test_approval_gate.py:361, 384, and 562.
  AC7: tests/test_security_audit_log.py:423, 439, 450, and 459 verify src/owlbear/tools/terminal.py:198, 226, and 280. Existing confinement regressions still pass in tests/test_terminal_tools.py:277 and 284.
  AC8: tests/test_security_audit_log.py:483, 489, 505, 521, and 537 verify the best-effort audit boundaries in src/owlbear/core/command_guard.py:194, src/owlbear/safety/gate.py:212, and src/owlbear/tools/terminal.py:280.
  AC9: satisfied by the passing scoped pytest slice and clean task-scoped ruff.
- TestFromAC comparison:
  Original RED-phase tests from commits aaa4a5e and f546925 remain present; no weakened or removed TestFromAC methods were found.
  Commit 08ef4d0 added stricter TestFromAC methods at tests/test_security_audit_log.py:204 and 226 to close the earlier AC1 and AC3 gaps. Assessment: STRENGTHENED.
- Test quality:
  Assertion specificity: STRONG.
  Negative and error-path coverage: STRONG.
  Mutation resistance: STRONG after the exact-field and ISO-8601 tests were added.
  Independence: STRONG.
  Naming: STRONG.
- Security and data safety:
  No hardcoded secrets, direct injection surface, path traversal regression, or unbounded-input issue was introduced in the reviewed scope.
  The injected audit sink remains a best-effort side channel; sink failures are swallowed at the emission boundary and existing block, deny, timeout, and PermissionError behavior stay intact.

[[2026-03-26]] Thu 12:21
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | SecurityAuditLog documented at Safety row, line 64; '(wired in #847)' confirmed correct via git log ce07053 |
| 2 | Docstrings | Yes | Pass | audit_log.py: SecurityEvent, SecurityAuditLog, log(), max_entries, _maybe_trim all have docstrings; modified files (hooks.py, toolsets.py) had no per-param docstring style pre-existing this task |
| 3 | sources/overview.md | Yes | Pass | 'Security Audit Log Research (Task #525)' section present with 3 entries (OWASP, Python logging.handlers, structlog) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/security-audit-log.md exists; linked from task body; follow-up tasks (#848) created |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-26]] Thu 12:51
## Audit
### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC1 SecurityEvent schema | src/owlbear/safety/audit_log.py:18-29 all 8 fields | PASS |
| AC2 SecurityAuditLog path+max | audit_log.py:33-43 path=workspace/.owlbear/security_audit.jsonl default 500k | PASS |
| AC3 log() auto-timestamp | audit_log.py:48-81 uses datetime.now(UTC).isoformat() | PASS |
| AC4 No direct import | grep confirmed command_guard.py and terminal.py have zero audit_log references | PASS |
| AC5 command_blocked emit | Reviewer evidence lines 166-194 of command_guard.py; 7 tests pass | PASS |
| AC6 approval events | Reviewer evidence lines 127-212 of gate.py; 8 tests + POST_TOOL_USE regressions pass | PASS |
| AC7 path_escape_blocked | Reviewer evidence lines 198-280 of terminal.py; 4 tests pass | PASS |
| AC8 best-effort sink | Reviewer evidence: 5 tests verify swallowing at emission boundary | PASS |
| AC9 tests+ruff | 4506 passed full suite, 90 pre-existing RED failures unrelated; ruff clean on 8 task files | PASS |

### Test Results
- pytest: 4506 passed, 90 failed (all pre-existing RED-phase), 2 skipped, --ignore benchmarks placeholder
- ruff: All checks passed on task-relevant files

### Architect Quality
- AC specificity: Excellent -- 9 explicit AC lines with schema fields, layering constraints, and best-effort requirements
- Edge case coverage: No gaps found; builder had no improvisation needed
- Design direction: Architecture notes on JsonlStore reuse and injection pattern were productive
- AC quality score: 5

### Confidence: .97
### Action: archive

-t

[[2026-03-26]] Thu 12:52
## Audit
### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC1 SecurityEvent schema | audit_log.py:18-29 all 8 fields | PASS |
| AC2 SecurityAuditLog path+max | audit_log.py:33-43 .owlbear/security_audit.jsonl 500k | PASS |
| AC3 log() auto-timestamp | audit_log.py:48-81 datetime.now(UTC).isoformat() | PASS |
| AC4 No direct import | grep: zero audit_log refs in command_guard.py/terminal.py | PASS |
| AC5 command_blocked emit | command_guard.py:166-194; 7 tests pass | PASS |
| AC6 approval events | gate.py:127-212; 8 tests + POST_TOOL_USE regressions pass | PASS |
| AC7 path_escape_blocked | terminal.py:198-280; 4 tests pass | PASS |
| AC8 best-effort sink | 5 tests verify swallowing at emission boundary | PASS |
| AC9 tests+ruff | 4506 passed full suite, 90 pre-existing RED; ruff clean | PASS |

### Test Results
- pytest: 4506 passed, 90 failed (pre-existing RED), 2 skipped
- ruff: All checks passed

### Architect Quality
- AC quality score: 5 (specific, complete, clean implementation)

### Confidence: .97
### Action: archive
