---
id: 94
title: 'Test: AcpClient wrapper with timeouts and error classification'
status: todo
priority: needed
created: 2026-03-28T01:50:49.0538734+01:00
updated: 2026-03-28T04:24:25.0528718+01:00
tags:
    - phase-1
    - scope:orchestrator
    - type:test
    - test
class: standard
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
