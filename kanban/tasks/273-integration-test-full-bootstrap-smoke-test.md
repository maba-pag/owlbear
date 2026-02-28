---
id: 273
title: 'Integration test: full bootstrap() smoke test'
status: archived
priority: important
created: 2026-02-28T14:21:26.7385691+01:00
updated: 2026-02-28T23:54:36.3275741+01:00
started: 2026-02-28T15:06:43.1549416+01:00
completed: 2026-02-28T23:54:36.3275741+01:00
tags:
    - phase-8
    - test
    - agent
depends_on:
    - 267
class: standard
---

## Context
End-to-end test verifying bootstrap() wires all components correctly.
This is the integration test counterpart to #267's unit tests.

## Acceptance Criteria
- [ ] tests/test_bootstrap_integration.py (separate from #267 unit tests in test_bootstrap.py)
- [ ] pytest.mark.asyncio async test function(s)
- [ ] Mock create_copilot_model to return a test model (avoid real API calls)
- [ ] Call bootstrap(settings, channel_name='cli', workspace_root=tmp_path) with test settings
- [ ] Verify BootstrapResult.hooks has handlers registered for: PRE_TOOL_USE, POST_TOOL_USE, ON_MESSAGE, ON_ERROR, SESSION_START, SESSION_END, SUBAGENT_COMPLETE, TASK_COMPLETE
- [ ] Verify BootstrapResult.agent is an OwlBearAgent instance
- [ ] Verify BootstrapResult.agent.inner has toolsets (at minimum: FileToolset, TerminalToolset, AskUserToolset, DelegationToolset)
- [ ] Verify BootstrapResult.channel is a CLIChannel (for channel_name='cli')
- [ ] Verify BootstrapResult.mcp_registry is None when settings.mcp_servers is None
- [ ] Verify BootstrapResult.agent._deps.agent_registry is set
- [ ] Verify agent.turn() works end-to-end with mocked model (mock model returns canned response)
- [ ] Verify cleanup callbacks list is populated (at least MCP shutdown if configured)
- [ ] Test with settings.github_token = None: verify GitHubToolset is NOT in toolsets
- [ ] Test with settings.github_token set: verify GitHubToolset IS in toolsets (mock token)
- [ ] ~80 LOC

## Architecture Notes
- Use tmp_path for workspace_root to avoid filesystem side effects
- Mock at the create_copilot_model boundary (not deeper) — test the wiring, not the auth
- Use FunctionToolset.__len__ or count inner _user_toolsets to verify toolset count
- Browser toolset: verify it's present but NOT initialized (no setup called)
- This test validates the contract between bootstrap and the daemon/chat loop

## TDD
This IS a test task. No separate test task needed.

## Dependencies
depends_on: [267]
