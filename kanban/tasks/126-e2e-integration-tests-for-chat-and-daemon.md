---
id: 126
title: E2E integration tests for chat and daemon lifecycle
status: archived
priority: needed
created: 2026-02-27T14:55:31.2596059+01:00
updated: 2026-02-28T23:52:50.4485593+01:00
started: 2026-02-27T16:40:11.2917537+01:00
completed: 2026-02-28T23:52:50.4485593+01:00
tags:
    - phase-7
    - test
depends_on:
    - 120
    - 121
    - 122
class: standard
---

Prove the full P7 stack works end-to-end: OwlBearAgent + real toolsets + FunctionModel + SessionStore. Phase gate tests for P7. See docs/e2e-integration-tests-research.md.

## AC
- [ ] File: tests/test_e2e_chat.py
- [ ] Global guard: pydantic_ai.models.ALLOW_MODEL_REQUESTS = False (blocks real LLM calls)
- [ ] Pattern: FunctionModel with step-based dispatch + Agent.override on agent.inner
- [ ] Test: text response — FunctionModel returns TextPart, OwlBearAgent.turn() returns the response string
- [ ] Test: read_file tool — FunctionModel emits ToolCallPart('read_file', {'path': 'test.txt'}), FileToolset reads real tmp_path file, model returns summary
- [ ] Test: run_command tool — FunctionModel emits ToolCallPart('run_command', {'command': 'echo hello'}), TerminalToolset executes real subprocess, model returns result
- [ ] Test: session persistence — after agent.turn(), SessionStore JSONL file exists and contains serialized messages
- [ ] Test: session continuity — create agent A, run turn, create agent B with same session path, verify B loads A's history and can continue conversation
- [ ] All tests use real FileToolset(tmp_path) and TerminalToolset(workspace_root=tmp_path) with FunctionModel for LLM
- [ ] ruff clean

## Deferred
- ask_user E2E test deferred until #123 (AskUserToolset) is complete — add to test_e2e_chat.py then
- Daemon lifecycle E2E deferred until #124 (bearclaw run) is complete

## Architecture
- FunctionModel callback: def model_fn(messages, info) -> ModelResponse — dispatch on len(messages) for step-based control
- Agent.override: agent.inner.override(model=FunctionModel(fn)) — exercises full turn() stack including hooks, session, usage
- Do NOT use TestModel (auto-generates synthetic args like path='a', not realistic for E2E)
- Do NOT mock OwlBearAgent.inner.run — the whole point is exercising real tool execution
