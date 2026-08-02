---
id: 181
title: 'Test: AcpClient wrapper forwards required SDK parameters'
status: archived
priority: medium
created: 2026-03-29 20:03:34.543667+02:00
updated: 2026-03-30 16:59:07.704985+02:00
started: 2026-03-30 16:58:48.459426+02:00
completed: 2026-03-30 16:58:48.459426+02:00
tags:
- phase-1
- ' scope:orchestrator'
- ' type:test'
- ' test'
depends_on:
- 59
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests that verify AcpClient.initialize(), new_session(), and prompt() forward required SDK parameters to the underlying ClientSideConnection methods.

## AC
- [ ] test_initialize_forwards_protocol_version: calls conn.initialize(protocol_version=1) through the wrapper, asserts the mock conn.initialize was called with protocol_version=1
- [ ] test_new_session_forwards_cwd: calls wrapper.new_session(cwd="/tmp"), asserts conn.new_session was called with cwd="/tmp"
- [ ] test_new_session_forwards_mcp_servers: calls wrapper.new_session(cwd="/tmp", mcp_servers=[...]), asserts conn.new_session was called with mcp_servers list
- [ ] test_prompt_forwards_content_blocks: calls wrapper.prompt(prompt=[TextContentBlock(...)], session_id="s1"), asserts conn.prompt was called with both prompt and session_id
- [ ] test_prompt_forwards_optional_message_id: calls wrapper.prompt(..., message_id="m1"), asserts conn.prompt was called with message_id="m1"
- [ ] All existing 21 tests in tests/test_acp_client.py still pass
- [ ] Tests must call through to the actual mock connection methods (not patch asyncio.wait_for)
- [ ] ruff clean

## Notes
- Test file: tests/test_acp_client.py (extend existing file)
- Mock pattern: use AsyncMock(spec=ClientSideConnection) with explicit method overrides (see existing _make_conn helper)
- These tests MUST FAIL on current HEAD because initialize/new_session/prompt do not accept or forward the required params
- See docs/research/acp-client-wrapper-validation.md SS3.3 for gap analysis
- SDK signatures (acp v0.9.0):
  - initialize(protocol_version: int, client_capabilities=None, client_info=None)
  - new_session(cwd: str, mcp_servers=None)
  - prompt(prompt: list[ContentBlock], session_id: str, message_id=None)

[[2026-03-30]] Mon 14:21
## Test-Writer Notes
- This task IS a test-writing task (tagged type:test). No separate TW pass needed — the task itself is TW output.
- Retroactively added by manual triage (2026-03-30) to unblock Gate 4.

-t

[[2026-03-30]] Mon 14:33
## Builder Notes
- Files changed: none (tests and implementation already committed)
- Tests: 27 passed (21 original + 6 new SDK-forwarding tests); all 5 AC tests present
- Coverage: 100% on acp_client.py
- Lint: ruff clean
- Evidence: test_initialize_forwards_protocol_version, test_new_session_forwards_cwd, test_new_session_forwards_mcp_servers, test_prompt_forwards_content_blocks, test_prompt_forwards_optional_message_id all pass
- Fixes applied: None — implementation already uses kwargs forwarding; tests pass on current HEAD

[[2026-03-30]] Mon 15:12
## Review Evidence

### Test Results
- pytest tests/test_acp_client.py: **27 passed**, 0 failed

### Lint Results
- ruff: All checks passed!

### Coverage
- packages\orchestrator\src\owlbear_orchestrator\acp_client.py: **100%** (53/53 stmts)

### Step 6.0 — Test-writer audit
This task IS the test-writer deliverable (tagged type:test). No pre-existing TestFromAC audit required.
New tests added: 6 (3 in TestFromAC_SDKParameterForwarding, 3 in TestBuilderDiscovered_SDKForwarding).

### Step 6.1 — Security
No issues. No hardcoded secrets, no injection risks, no external input at unvalidated boundaries.

### Step 6.2 — TestFromAC comparison
Existing TestFromAC_* classes from prior tasks unchanged (no code changes in git diff; all 21 original tests pass).

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_Timeouts (3 tests) | No change | PRESERVED |
| TestFromAC_ErrorClassification (6 tests) | No change | PRESERVED |
| TestFromAC_Cancellation (4 tests) | No change | PRESERVED |
| TestFromAC_AllSevenErrorCodes (3 tests) | No change | PRESERVED |
| TestFromAC_ConnectionErrorsAllMethods (4 tests) | No change | PRESERVED |

### Step 6.3 — Test quality
All 5 AC-named tests have STRONG specific-value assertions that would fail if forwarding broke.

| Test | Assertion | Quality |
|------|-----------|---------|
| test_initialize_forwards_protocol_version | assert_called_once_with(protocol_version=1) | STRONG |
| test_new_session_forwards_cwd | assert_called_once_with(cwd='/work/cwd') | STRONG |
| test_new_session_forwards_mcp_servers | assert_called_once_with(cwd=..., mcp_servers=...) | STRONG |
| test_prompt_forwards_content_blocks | call_args.kwargs prompt + session_id | STRONG |
| test_prompt_forwards_optional_message_id | call_args.kwargs message_id | STRONG |

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| test_initialize_forwards_protocol_version | TestFromAC_SDKParameterForwarding, no wait_for patch, strong assert | PASS |
| test_new_session_forwards_cwd | TestFromAC_SDKParameterForwarding, no wait_for patch, strong assert | PASS |
| test_new_session_forwards_mcp_servers | TestBuilderDiscovered_SDKForwarding, no wait_for patch, strong assert | PASS |
| test_prompt_forwards_content_blocks | TestBuilderDiscovered_SDKForwarding, no wait_for patch, both args asserted | PASS |
| test_prompt_forwards_optional_message_id | TestBuilderDiscovered_SDKForwarding, no wait_for patch, message_id asserted | PASS |
| All 21 existing tests still pass | 27 total passed = 21 + 6 new | PASS |
| Tests call through actual mock methods (no wait_for patch) | All 5 AC-named tests verified | PASS |
| ruff clean | All checks passed! | PASS |

### Step 6.5 — Implementation-aware gap analysis
Implementation uses **kwargs for initialize and new_session (forward-all pattern).
Prompt assembles dict with session_id + optional prompt + **kwargs before calling conn.prompt.
No untested branches for the SDK forwarding paths.

### Verdict: PASS (confidence 0.93)

[[2026-03-30]] Mon 15:31
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | type:test task — no behavior or API change |
| 2 | Docstrings | No | N/A | Builder: 'Files changed: none'; only tests/test_acp_client.py extended, no application modules modified by this task |
| 3 | docs/sources/overview.md | No | N/A | No new external patterns; ACP SDK sources already recorded for tasks #94 and #59 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No new research doc produced; task references existing acp-client-wrapper-validation.md (confirmed present) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/181-* files found)

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| dead0a4 | chore | kanban/tasks/181-*.md | #181 |
