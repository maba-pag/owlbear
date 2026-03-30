---
id: 181
title: 'Test: AcpClient wrapper forwards required SDK parameters'
status: in-progress
priority: needed
created: 2026-03-29T20:03:34.5436669+02:00
updated: 2026-03-30T01:19:35.2187931+02:00
tags:
    - phase-1
    - ' scope:orchestrator'
    - ' type:test'
    - ' test'
depends_on:
    - 59
class: standard
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
