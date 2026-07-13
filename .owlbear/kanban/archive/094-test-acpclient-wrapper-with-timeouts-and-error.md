---
id: 94
title: 'Test: AcpClient wrapper with timeouts and error classification'
status: archived
priority: medium
created: 2026-03-28 01:50:49.053873+01:00
updated: 2026-03-29 15:37:46.739483+02:00
started: 2026-03-29 15:37:46.444402+02:00
completed: 2026-03-29 15:37:46.444402+02:00
tags:
- phase-1
- scope:orchestrator
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
RED phase tests for AcpClient (task #59).

## AC
- [ ] Test: initialize wraps with 30s asyncio.wait_for timeout (assert timeout kwarg passed to patched wait_for)
- [ ] Test: new_session wraps with 15s timeout (assert timeout kwarg)
- [ ] Test: prompt wraps with 300s timeout (assert timeout kwarg)
- [ ] Test: RequestError caught and classified by error code (mock side_effect=RequestError(code, msg), verify ErrorCategory mapping)
- [ ] Test: session/cancel sent on asyncio.TimeoutError during prompt (mock timeout on prompt, assert conn.cancel awaited with session_id)
- [ ] Test: external CancelSignal triggers session/cancel before prompt (set CancelSignal, call prompt, assert conn.cancel called)
- [ ] Test: BrokenPipeError detected and classified as TRANSIENT (mock side_effect=BrokenPipeError, verify classification)
- [ ] Test: EOF on stdout detected as TRANSIENT (mock side_effect=ConnectionError, verify classification)
- [ ] All tests use AsyncMock(spec=ClientSideConnection) with no real Copilot CLI
- [ ] Tests import from owlbear_orchestrator.acp_client (module does not exist yet; import failure is expected RED state)
- [ ] Follow test_process_supervisor.py patterns: pytest.mark.asyncio(loop_scope=function), patch(), AsyncMock

Precedes: #59. See docs/research/acp-error-handling-strategy.md SS3.3-SS3.5 and docs/research/acp-client-test-strategy.md.

[[2026-03-28]] Sat 04:24
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| initialize 30s timeout | Precise, verifiable via patched wait_for kwarg | Keep |
| new_session 15s timeout | Same pattern, verifiable | Keep |
| prompt 300s timeout | Same pattern, verifiable | Keep |
| RequestError classified by code | Verifiable via side_effect + ErrorCategory assert | Keep |
| session/cancel on TimeoutError | Verifiable via conn.cancel assert | Keep |
| external CancelSignal | **Added** per research gap (acp-client-test-strategy SS3.5, #59 AC) | Added |
| BrokenPipeError as TRANSIENT | Clarified: tests classification, not respawn (supervisor respawns) | Refined |
| EOF as TRANSIENT | ConnectionError side_effect per research recommendation | Keep |
| Mocked ClientSideConnection | Constraint, enforced by AsyncMock(spec=) | Keep |
| Import from owlbear_orchestrator.acp_client | Module path consistent with package layout | Keep |
| Follow test_process_supervisor.py patterns | Ensures consistency across test suite | Keep |

### Architecture Notes
- Single domain: scope:orchestrator, type:test. Pure test task.
- Follows established test_process_supervisor.py patterns (AsyncMock, patch, pytest.mark.asyncio).
- v1 classify_error already maps ACP error codes (v1/src/owlbear/core/errors.py L93-101). Tests verify AcpClient delegates correctly.
- CancelSignal exists in v1 (memory/knowledge/cancellation.py). v2 CancelSignal will be defined by impl task.
- No dependency on ProcessSupervisor being implemented; tests mock ClientSideConnection directly.

### Changes Made
- Refined AC: added CancelSignal test line (research gap), clarified BrokenPipeError wording, added module path and pattern constraints
- Approved to todo

### Dependencies
- Verified: no depends_on needed (RED phase mocks everything)
- Verified: #59 (impl) at ideation, correctly follows this test task

[[2026-03-29]] Sun 13:03
## Test-Writer Notes
- Test file: tests/test_acp_client.py
- Classes: TestFromAC_Timeouts, TestFromAC_ErrorClassification, TestFromAC_Cancellation
- Tests per category: happy 3, edge 1, error 7, boundary 2
- Total: 13 tests
- ruff: clean
- Status: PRE-BUILT — both tests and implementation (owlbear_orchestrator/acp_client.py) existed before test-writer ran. Tests PASS (not RED) because the builder implemented ahead of the pipeline.
- AC coverage complete: all 11 AC lines have at least one test.
- AC line to test mapping:
  - initialize 30s timeout: test_initialize_uses_30s_timeout
  - new_session 15s timeout: test_new_session_uses_15s_timeout
  - prompt 300s timeout: test_prompt_uses_300s_timeout
  - RequestError by code: test_request_error_* (5 tests, codes -32700 -32601 -32603 -32000 -32002)
  - session/cancel on TimeoutError: test_cancel_sent_on_timeout_error_during_prompt
  - external CancelSignal: test_cancel_sent_when_cancel_signal_already_set
  - BrokenPipeError TRANSIENT: test_broken_pipe_classified_transient
  - EOF TRANSIENT: test_eof_connection_error_classified_transient
  - AsyncMock(spec=ClientSideConnection): verified in _make_conn()
  - import from owlbear_orchestrator.acp_client: verified
  - test_process_supervisor.py patterns: pytest.mark.asyncio(loop_scope=function), patch(), AsyncMock

[[2026-03-29]] Sun 15:04
## Test-Writer Notes (retry 2026-03-29)
- Pre-built situation confirmed: tests/test_acp_client.py -- 13 tests, all PASS
- Implementation owlbear_orchestrator/acp_client.py already exists
- ruff: clean
- Tests cannot be RED -- builder implemented ahead of pipeline
- Advancing to in-progress to unblock the builder for task #59

[[2026-03-29]] Sun 15:10
## Builder Notes
- Pre-built situation: tests/test_acp_client.py and owlbear_orchestrator/acp_client.py already existed
- Files changed: none (implementation was already in place before builder ran)
- Tests: 13 passed, coverage 92% on owlbear_orchestrator/acp_client.py
- Lint: ruff clean
- Evidence: uv run pytest tests/test_acp_client.py -q -- 13 passed in 0.37s; ruff check -- no issues found
- Fixes applied: None (pass-through, all AC satisfied by pre-existing implementation)

[[2026-03-29]] Sun 15:37
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| initialize 30s timeout | test_initialize_uses_30s_timeout asserts timeout=30 on patched wait_for | PASS |
| new_session 15s timeout | test_new_session_uses_15s_timeout asserts timeout=15 | PASS |
| prompt 300s timeout | test_prompt_uses_300s_timeout asserts timeout=300 | PASS |
| RequestError classified by code | 5 tests for codes -32700,-32601,-32603,-32000,-32002 | PASS |
| session/cancel on TimeoutError | test_cancel_sent_on_timeout_error_during_prompt | PASS |
| CancelSignal triggers cancel | test_cancel_sent_when_cancel_signal_already_set | PASS |
| BrokenPipeError TRANSIENT | test_broken_pipe_classified_transient | PASS |
| EOF TRANSIENT | test_eof_connection_error_classified_transient | PASS |
| AsyncMock(spec=ClientSideConnection) | _make_conn() uses AsyncMock(spec=ClientSideConnection) | PASS |
| Import from owlbear_orchestrator.acp_client | Line 19 imports AcpClient, AcpClientError, ErrorCategory | PASS |
| Follow test_process_supervisor.py patterns | pytest.mark.asyncio(loop_scope=function), patch(), AsyncMock confirmed | PASS |

### Test Results
- pytest: 13/13 passed (test_acp_client.py), full suite 679 passed, 90 pre-existing failures unrelated to #94
- ruff: all checks passed

### Upstream Commits
- 5bca212 test: add failing tests (#94, test-writer)
- ffefc29 feat: implement AcpClient (#94, builder)

### Quality Gaps
- No Review Evidence section in task body (reviewer skipped or failed to record)
- No Docs Gate section in task body (writer skipped or failed to record)
- Pre-built situation: builder implemented ahead of pipeline, tests were never RED

### AC Quality Score: 5/5
AC was precise and verifiable: exact timeout values, specific error codes, concrete mock patterns. No gaps requiring improvisation.

### Confidence: .95
### Action: archive
