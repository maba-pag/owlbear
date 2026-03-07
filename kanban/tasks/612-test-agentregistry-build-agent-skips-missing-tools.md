---
id: 612
title: 'Test: AgentRegistry._build_agent skips missing tools'
status: archived
priority: critical
created: 2026-03-07T05:18:42.3179311+01:00
updated: 2026-03-07T18:08:20.4077441+01:00
started: 2026-03-07T05:36:49.7516519+01:00
completed: 2026-03-07T18:08:20.4077441+01:00
tags:
    - test
    - bugfix
    - phase-9
depends_on:
    - 611
class: standard
---

## TDD Red Phase for #611

Add tests to tests/test_agent_registry.py proving _build_agent degrades gracefully when a tool resolver raises KeyError.

## AC
- [ ] test_build_agent_skips_unavailable_tool: register agent def with tools=['a','b'], resolver raises KeyError for 'b' only -- agent created with 1 toolset, no exception
- [ ] test_build_agent_logs_warning_for_skipped_tool: same setup, assert WARNING log contains agent name ('test_agent') and tool name ('b')
- [ ] test_build_agent_all_tools_present_unchanged: resolver returns toolset for all tools -- agent created with full toolset list, no warnings
- [ ] test_build_agent_skips_mcp_tool_when_missing: agent def has tools=['mcp:missing'], no MCP registry -- KeyError caught, agent still created
- [ ] All existing tests in test_agent_registry.py still pass

## Implementation notes
- Write agent def fixture with tools: [a, b] where b is missing
- Use MagicMock or FunctionToolset for resolved tools
- Use caplog to assert WARNING level messages
- Tests must FAIL before #611 impl task is done (TDD red)
