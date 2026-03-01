---
id: 295
title: End-to-end integration test — bootstrap to daemon loop
status: archived
priority: critical
created: 2026-03-01T02:52:34.842311+01:00
updated: 2026-03-01T17:08:19.5296145+01:00
started: 2026-03-01T03:46:31.4514215+01:00
completed: 2026-03-01T17:08:19.5296145+01:00
tags:
    - phase-11
    - test
    - integration
depends_on:
    - 291
class: standard
---

## Context

The full system (bootstrap -> agent -> tools -> daemon loop) has never been tested end-to-end.
Individual modules have 1883 unit tests but the wiring has gaps.
See docs/bootstrap-daemon-e2e-research.md for detailed findings.

## Acceptance Criteria

### Test 1: run_daemon with real OwlBearAgent + FunctionModel

- [ ] Bootstrap OwlBearAgent with FunctionModel (patch create_copilot_model)
- [ ] Wire into run_daemon() via MockChannel with 1 message then None (EOF)
- [ ] FunctionModel returns TextPart response
- [ ] Assert MockChannel.sent contains the model response text
- [ ] Assert agent.turn() was exercised (not AsyncMock -- real call stack)
- [ ] Pattern: FunctionModel step-dispatch per test_e2e_chat.py

### Test 2: _chat_loop with real OwlBearAgent + CLIChannel(StringIO)

- [ ] Create OwlBearAgent with FunctionModel (text-only response)
- [ ] CLIChannel(input=StringIO('hello\nexit\n'), output=StringIO())
- [ ] Call _chat_loop(agent, channel) directly (not through CLI runner)
- [ ] Assert output StringIO contains the FunctionModel response text
- [ ] Assert output contains 'Goodbye!' (exit keyword processed)
- [ ] Pattern: CLIChannel(StringIO) per test_channels.py

### Test 3: delegation through bootstrap stack

- [ ] Create 2 minimal agent definition .md files in tmp_path/agents/: orchestrator.md (tools: [DelegationToolset]) and coder.md (no tools)
- [ ] Bootstrap with agents_dir=tmp_path/agents, create_copilot_model returns FunctionModel
- [ ] Outer FunctionModel step 1: emit ToolCallPart(delegate_to_agent, {agent_name: 'coder', task: 'write hello'})
- [ ] Outer FunctionModel step 2: return TextPart summarizing delegation result
- [ ] Inner (coder) agent resolved from registry, model overridden to TestModel(custom_output_text='hello written')
- [ ] Assert final response includes delegated agent output
- [ ] Assert agent_registry.get('coder') was exercised (lazy build path)
- [ ] Pattern: Agent.override per test_e2e_chat.py, agent defs per agent_def.py format

### Test 4: hook pipeline order through bootstrap wiring

- [ ] Bootstrap OwlBearAgent (patch create_copilot_model -> FunctionModel)
- [ ] FunctionModel step 1: emit ToolCallPart for a real tool (e.g. read_file)
- [ ] FunctionModel step 2: return TextPart
- [ ] Register test listener on bootstrapped HookRegistry for PRE_TOOL_USE and POST_TOOL_USE
- [ ] Call agent.turn() -- triggers tool call through HookedToolset
- [ ] Assert captured events order: PRE_TOOL_USE fired before POST_TOOL_USE
- [ ] Assert PRE_TOOL_USE data contains tool_name matching the called tool
- [ ] Pattern: hooks.register(event, captured.append) per test_hooked_toolset.py

### Cross-cutting requirements

- [ ] pydantic_ai.models.ALLOW_MODEL_REQUESTS = False at module level
- [ ] All test classes use pytest.mark.asyncio or asyncio.run() (follow test_e2e_chat.py pattern)
- [ ] No pytest.mark.api marker (runs in default test suite)
- [ ] File: tests/test_integration_e2e.py
- [ ] Coverage >= 90% maintained on bootstrap.py and daemon.py (baseline: 93%)
