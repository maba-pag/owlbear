---
id: 59
title: Implement AcpClient wrapper with timeouts and error classification
status: archived
priority: medium
created: 2026-03-26 19:27:25.570717+01:00
updated: 2026-03-30 00:08:06.431198+02:00
started: 2026-03-30 00:08:01.785751+02:00
completed: 2026-03-30 00:08:01.785751+02:00
tags:
- phase-1
- scope:orchestrator
- type:build
depends_on:
- 58
- 46
- 94
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Wrap ACP SDK ClientSideConnection with per-method timeouts and error classification.

## AC
- [ ] Wraps initialize (30s), new_session (15s), prompt (300s) with asyncio.wait_for
- [ ] Catches RequestError and classifies by code per acp-error-handling-strategy.md SS3.5 (_ACP_ERROR_CODES dict mapping all 7 JSON-RPC codes)
- [ ] Sends session/cancel on timeout or external CancelSignal (duck-typed Protocol with is_set() -> bool)
- [ ] Detects BrokenPipeError and EOF (ConnectionError) as TRANSIENT via AcpClientError

Depends on: #58 (ProcessSupervisor, archived), #46 (ACP SDK dep, archived), #94 (test task, archived).
See docs/research/acp-error-handling-strategy.md SS3.3, SS3.4 and docs/research/acp-client-wrapper-validation.md.

### Implementation notes
- Module: packages/orchestrator/src/owlbear_orchestrator/acp_client.py (pre-built during #94, 121 LOC)
- Tests: tests/test_acp_client.py (13 tests, all pass, 92% coverage)
- ErrorJournal integration deferred to #148 (v2 error infra does not exist yet)
- API parameter forwarding deferred to #147 (separate concern from timeout/classification)

[[2026-03-29]] Sun 19:25
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Wraps initialize (30s), new_session (15s), prompt (300s) with asyncio.wait_for | Precise: timeout values match research SS3.3 rationale. Verified at acp_client.py L95, L102, L113 | Keep |
| Catches RequestError and classifies by code (7 JSON-RPC codes) | Verifiable: _ACP_ERROR_CODES maps all 7 codes per SS3.5. Default-to-PERMANENT for unknowns is conservative and correct | Keep |
| Sends session/cancel on timeout or external CancelSignal | Verifiable: L111-113 (CancelSignal), L116-118 (timeout cancel). _CancelSignal Protocol is correct interface decoupling | Keep |
| Detects BrokenPipeError and EOF as TRANSIENT | Verifiable: L99-100, L106-107, L119-120 catch both. Raises AcpClientError with TRANSIENT category | Keep |
| (removed) Logs errors to ErrorJournal when available | ErrorJournal does not exist in v2. Deferred to #148 | Removed from AC |

### Architecture Notes
- Single responsibility: timeout wrapping + error classification only. No subprocess lifecycle (ProcessSupervisor #58), no SDK param forwarding (#147), no journal wiring (#148).
- Interface design: _CancelSignal Protocol (duck-typed is_set() -> bool) follows architecture-standards Protocol pattern. Decoupled from any concrete CancelSignal implementation.
- Error taxonomy: Local ErrorCategory(StrEnum) in orchestrator package is correct for v2. v1 core/errors.py has a separate taxonomy; unification happens when v2 error infra is built.
- Module layering: Clean leaf module. Imports only acp SDK types (external) and stdlib asyncio. No upward imports

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| initialize() | SDK call times out after 30s | asyncio.TimeoutError | Propagated to caller | Caller retries or respawns via ProcessSupervisor |
| prompt() | LLM times out after 300s | asyncio.TimeoutError | Yes, sends session/cancel then re-raises | Prompt aborted cleanly |
| prompt() | CancelSignal pre-set | asyncio.CancelledError | Yes, sends session/cancel | Prompt aborted by user intent |
| any method | Pipe break mid-call | AcpClientError(TRANSIENT) | Yes, classified for caller retry | Caller triggers ProcessSupervisor respawn |
| any method | Auth expired | AcpClientError(AUTH) | Yes, classified | Caller triggers re-auth flow |

### Changes Made
- Refined AC: removed ErrorJournal line (deferred to #148), tightened remaining 4 lines with specifics
- Added implementation notes section referencing pre-built module and test locations
- Linked both follow-up tasks (#147 API params, #148 ErrorJournal)

### Dependencies
- Verified: #58 (ProcessSupervisor) archived
- Verified: #46 (ACP SDK dep) archived
- Verified: #94 (test task) archived, 13 tests pass
- Downstream: #147 (API params) and #148 (ErrorJournal) depend on #59

[[2026-03-29]] Sun 19:25
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Wraps initialize (30s), new_session (15s), prompt (300s) with asyncio.wait_for | Precise: timeout values match research SS3.3 rationale. Verified at acp_client.py L95, L102, L113 | Keep |
| Catches RequestError and classifies by code (7 JSON-RPC codes) | Verifiable: _ACP_ERROR_CODES maps all 7 codes per SS3.5. Default-to-PERMANENT for unknowns is conservative and correct | Keep |
| Sends session/cancel on timeout or external CancelSignal | Verifiable: L111-113 (CancelSignal), L116-118 (timeout cancel). _CancelSignal Protocol is correct interface decoupling | Keep |
| Detects BrokenPipeError and EOF as TRANSIENT | Verifiable: L99-100, L106-107, L119-120 catch both. Raises AcpClientError with TRANSIENT category | Keep |
| (removed) Logs errors to ErrorJournal when available | ErrorJournal does not exist in v2. Deferred to #148 | Removed from AC |

### Architecture Notes
- Single responsibility: timeout wrapping + error classification only. No subprocess lifecycle (ProcessSupervisor #58), no SDK param forwarding (#147), no journal wiring (#148).
- Interface design: _CancelSignal Protocol (duck-typed is_set() -> bool) follows architecture-standards Protocol pattern. Decoupled from any concrete CancelSignal implementation.
- Error taxonomy: Local ErrorCategory(StrEnum) in orchestrator package is correct for v2. v1 core/errors.py has a separate taxonomy; unification happens when v2 error infra is built.
- Module layering: Clean leaf module. Imports only acp SDK types (external) and stdlib asyncio. No upward imports

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| initialize() | SDK call times out after 30s | asyncio.TimeoutError | Propagated to caller | Caller retries or respawns via ProcessSupervisor |
| prompt() | LLM times out after 300s | asyncio.TimeoutError | Yes, sends session/cancel then re-raises | Prompt aborted cleanly |
| prompt() | CancelSignal pre-set | asyncio.CancelledError | Yes, sends session/cancel | Prompt aborted by user intent |
| any method | Pipe break mid-call | AcpClientError(TRANSIENT) | Yes, classified for caller retry | Caller triggers ProcessSupervisor respawn |
| any method | Auth expired | AcpClientError(AUTH) | Yes, classified | Caller triggers re-auth flow |

### Changes Made
- Refined AC: removed ErrorJournal line (deferred to #148), tightened remaining 4 lines with specifics
- Added implementation notes section referencing pre-built module and test locations
- Linked both follow-up tasks (#147 API params, #148 ErrorJournal)

### Dependencies
- Verified: #58 (ProcessSupervisor) archived
- Verified: #46 (ACP SDK dep) archived
- Verified: #94 (test task) archived, 13 tests pass
- Downstream: #147 (API params) and #148 (ErrorJournal) depend on #59

[[2026-03-29]] Sun 19:25
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Wraps initialize (30s), new_session (15s), prompt (300s) with asyncio.wait_for | Precise: timeout values match research SS3.3 rationale. Verified at acp_client.py L95, L102, L113 | Keep |
| Catches RequestError and classifies by code (7 JSON-RPC codes) | Verifiable: _ACP_ERROR_CODES maps all 7 codes per SS3.5. Default-to-PERMANENT for unknowns is conservative and correct | Keep |
| Sends session/cancel on timeout or external CancelSignal | Verifiable: L111-113 (CancelSignal), L116-118 (timeout cancel). _CancelSignal Protocol is correct interface decoupling | Keep |
| Detects BrokenPipeError and EOF as TRANSIENT | Verifiable: L99-100, L106-107, L119-120 catch both. Raises AcpClientError with TRANSIENT category | Keep |
| (removed) Logs errors to ErrorJournal when available | ErrorJournal does not exist in v2. Deferred to #148 | Removed from AC |

### Architecture Notes
- Single responsibility: timeout wrapping + error classification only. No subprocess lifecycle (ProcessSupervisor #58), no SDK param forwarding (#147), no journal wiring (#148).
- Interface design: _CancelSignal Protocol (duck-typed is_set() -> bool) follows architecture-standards Protocol pattern. Decoupled from any concrete CancelSignal implementation.
- Error taxonomy: Local ErrorCategory(StrEnum) in orchestrator package is correct for v2. v1 core/errors.py has a separate taxonomy; unification happens when v2 error infra is built.
- Module layering: Clean leaf module. Imports only acp SDK types (external) and stdlib asyncio. No upward imports

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| initialize() | SDK call times out after 30s | asyncio.TimeoutError | Propagated to caller | Caller retries or respawns via ProcessSupervisor |
| prompt() | LLM times out after 300s | asyncio.TimeoutError | Yes, sends session/cancel then re-raises | Prompt aborted cleanly |
| prompt() | CancelSignal pre-set | asyncio.CancelledError | Yes, sends session/cancel | Prompt aborted by user intent |
| any method | Pipe break mid-call | AcpClientError(TRANSIENT) | Yes, classified for caller retry | Caller triggers ProcessSupervisor respawn |
| any method | Auth expired | AcpClientError(AUTH) | Yes, classified | Caller triggers re-auth flow |

### Changes Made
- Refined AC: removed ErrorJournal line (deferred to #148), tightened remaining 4 lines with specifics
- Added implementation notes section referencing pre-built module and test locations
- Linked both follow-up tasks (#147 API params, #148 ErrorJournal)

### Dependencies
- Verified: #58 (ProcessSupervisor) archived
- Verified: #46 (ACP SDK dep) archived
- Verified: #94 (test task) archived, 13 tests pass
- Downstream: #147 (API params) and #148 (ErrorJournal) depend on #59

[[2026-03-29]] Sun 20:00
## Test-Writer Notes
- Test file: tests/test_acp_client.py
- Classes: TestFromAC_Timeouts, TestFromAC_ErrorClassification, TestFromAC_Cancellation, TestFromAC_AllSevenErrorCodes, TestFromAC_ConnectionErrorsAllMethods
- Tests per category: happy 7, edge 3, error 9, boundary 2
- Total: 21 tests (13 pre-existing from #94 + 8 new AC gap tests)
- ruff: clean
- NOTE: Implementation was pre-built during #94. All 21 tests PASS at write time. New tests fill AC coverage gaps (error codes -32600/-32602/unknown, BrokenPipe/ConnectionError on initialize+new_session).
- AC coverage: all 4 AC lines covered (21 tests total)

[[2026-03-29]] Sun 22:02
## Builder Notes
- Files changed: none — implementation pre-built during #94 (acp_client.py 121 LOC), tests pre-committed by test-writer
- Tests: 21 passed (13 pre-existing + 8 new AC gap tests), 0 failures
- Coverage: 100% on acp_client.py (50 stmts, 0 miss)
- Lint: ruff clean
- Evidence: uv run pytest tests/test_acp_client.py -q: 21 passed 0.37s; coverage 100% on acp_client.py
- Fixes applied: None — pre-built module satisfies all 4 AC lines and all 21 tests pass green

[[2026-03-29]] Sun 23:26
## Review Evidence
Reviewer: reviewer | Date: 2026-03-29

### Test Results
- pytest tests/test_acp_client.py: 21 passed, 0 failed (0.59 s)
- 4 RuntimeWarning: coroutine AsyncMockMixin._execute_mock_call was never awaited (informational, see notes)

### Lint Results
- ruff check packages/orchestrator/src/ tests/test_acp_client.py: All checks passed

### Coverage
- acp_client.py: 100% (0 missed lines)

### Test-Writer Coverage
All 4 AC lines COVERED. No MISSING, no LAX entries.
- AC1 timeouts: TestFromAC_Timeouts x3 - patches wait_for, asserts timeout kwarg == 30/15/300 exactly. COVERED
- AC2 all 7 codes: TestFromAC_ErrorClassification x7 + TestFromAC_AllSevenErrorCodes x3. COVERED
- AC3 cancel: TestFromAC_Cancellation x4 - on timeout, pre-set signal, not-set signal, CancelledError. COVERED
- AC4 pipe TRANSIENT: TestFromAC_ConnectionErrorsAllMethods x4 + 2 in ErrorClassification. COVERED

### TestFromAC Comparison
No builder modifications. All 21 tests are test-writer originals (0 TestBuilderDiscovered). 100% coverage already achieved. All PRESERVED.

### AC Compliance
- wrap initialize 30s: L95 asyncio.wait_for(timeout=30); test_initialize_uses_30s_timeout passes. PASS
- wrap new_session 15s: L102 asyncio.wait_for(timeout=15); test passes. PASS
- wrap prompt 300s: L113 asyncio.wait_for(timeout=300); test passes. PASS
- _ACP_ERROR_CODES 7 codes: L41-49 maps -32700,-32600,-32601,-32602,-32603,-32000,-32002; all tested. PASS
- cancel on timeout: L116-118 except TimeoutError calls cancel then re-raises; test confirms. PASS
- cancel on pre-set CancelSignal: L111-113 is_set() pre-check calls cancel then CancelledError; test confirms. PASS
- BrokenPipeError TRANSIENT: L99,L106,L119 all 3 methods; tests confirm. PASS
- ConnectionError TRANSIENT: same handler all 3 methods; tests confirm. PASS

### Security
Clean: no hardcoded secrets, no injection, no path traversal, no insecure deserialization. session_id is internal SDK parameter.

### Data Safety
Clean: no shared mutable state, no atomicity risks, no unbounded input.

### Informational (non-blocking)
1. AsyncMock coroutine warnings on 4 tests: known mock artifact when side_effect raises before coroutine fully executes. Behavior verified correct.
2. Timeout test accepts (asyncio.TimeoutError, AcpClientError) - permissive; implementation correctly re-raises TimeoutError but mutation to AcpClientError would also pass.

### Verdict: PASS - confidence .92

[[2026-03-29]] Sun 23:40
## Docs Gate
### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Orchestrator row already reads 'ACP client, dispatch planning, orchestration CLI hooks' - accurate, no update needed |
| 2 | Docstrings | Yes | Pass | acp_client.py: ErrorCategory, AcpClientError, AcpClient, initialize(), new_session(), prompt(), _CancelSignal all have accurate docstrings |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'AcpClient Wrapper Validation (Task #59)' present with 3 ACP SDK source rows |
| 4 | README.md | No | N/A | Internal module, no CLI changes |
| 5 | Research docs | Yes | Pass | Both acp-error-handling-strategy.md and acp-client-wrapper-validation.md exist and are linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/59-* files found)

[[2026-03-30]] Mon 00:07
## Audit
Auditor: auditor | Date: 2026-03-30

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Wraps initialize(30s), new_session(15s), prompt(300s) | acp_client.py L95 timeout=30, L102 timeout=15, L113 timeout=300; 3 timeout tests pass | PASS |
| _ACP_ERROR_CODES 7 codes + classify | L41-49 maps all 7 codes, L70 default PERMANENT; 10 classification tests pass | PASS |
| session/cancel on timeout + CancelSignal | L111-113 pre-check is_set cancels, L117-118 timeout cancels; 4 cancellation tests pass | PASS |
| BrokenPipeError + ConnectionError TRANSIENT | L99,L106,L119 catch both on all 3 methods; 6 tests pass | PASS |

### Test Results
- pytest tests/test_acp_client.py: 21 passed (AC-scoped), 3 failed (belong to #19, not #59)
- ruff: All checks passed

### AC Quality: 4/5
AC was precise and verifiable. Minor gap: connection errors across all 3 methods not explicitly stated (test-writer filled it).

### Confidence: .95
### Action: archive

-t

[[2026-03-30]] Mon 00:07
## Audit
Auditor: auditor, Date: 2026-03-30

### AC Verification
- AC1 (timeouts 30/15/300): acp_client.py L95,L102,L113 verified, 3 tests pass. PASS
- AC2 (7 error codes): L41-49 maps all 7, L70 default PERMANENT, 10 tests pass. PASS
- AC3 (cancel on timeout+signal): L111-113 pre-check, L117-118 timeout cancel, 4 tests pass. PASS
- AC4 (BrokenPipe+ConnectionError TRANSIENT): L99,L106,L119 all 3 methods, 6 tests pass. PASS

### Test Results
- pytest: 21 passed (AC-scoped), 3 failed (belong to #19 not #59)
- ruff: clean

### AC Quality: 4/5
AC precise and verifiable. Minor gap: connection errors across all methods not explicitly stated.

### Confidence: .95
### Action: archive

[[2026-03-30]] Mon 00:07
## Audit
Auditor: auditor, Date: 2026-03-30

### AC Verification
- AC1 (timeouts 30/15/300): acp_client.py L95,L102,L113 verified, 3 tests pass. PASS
- AC2 (7 error codes): L41-49 maps all 7, L70 default PERMANENT, 10 tests pass. PASS
- AC3 (cancel on timeout+signal): L111-113 pre-check, L117-118 timeout cancel, 4 tests pass. PASS
- AC4 (BrokenPipe+ConnectionError TRANSIENT): L99,L106,L119 all 3 methods, 6 tests pass. PASS

### Test Results
- pytest: 21 passed (AC-scoped), 3 failed (belong to #19 not #59)
- ruff: clean

### AC Quality: 4/5
AC precise and verifiable. Minor gap: connection errors across all methods not explicitly stated.

### Confidence: .95
### Action: archive
