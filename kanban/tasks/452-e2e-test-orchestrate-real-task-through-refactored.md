---
id: 452
title: 'E2E test: orchestrate real task through refactored pipeline'
status: archived
priority: needed
created: 2026-03-03T17:30:23.6283645+01:00
updated: 2026-03-04T07:58:27.3007618+01:00
started: 2026-03-03T20:01:00.1698336+01:00
completed: 2026-03-04T07:58:27.3007618+01:00
tags:
    - agent-refactor
    - test
    - phase-refactor
depends_on:
    - 442
    - 443
    - 444
    - 445
    - 446
    - 447
    - 448
    - 449
class: standard
---

## Context
See docs/e2e-pipeline-test-research.md for full analysis.

## Test file
tests/test_pipeline_e2e.py

## Acceptance Criteria

### AC-1: All 8 agents instantiate from real definitions via build_agent_registry
bootstrap() with real src/owlbear/agents/ dir, mocked create_copilot_model, and real build_toolsets + build_agent_registry. registry.get(name) succeeds for all 8 agent names without KeyError. This exercises the _resolve function with real alias mapping.

### AC-2: Tool resolution succeeds for every agent
For each of the 8 agents, registry.get(name) resolves all tools listed in the agent's definition. No KeyError from the _resolve callback. Parametrize over EXPECTED_AGENTS.keys() — one failure pinpoints the broken agent.

### AC-3: Four-step sequential pipeline delegation
Orchestrator FunctionModel emits delegate_to_agent for builder, then builder's result triggers reviewer, then writer, then closer — 4 sequential delegations in one logical flow. Each inner agent's FunctionModel returns a distinguishable marker string. Assert all 4 markers appear in final output and delegation_depth increments correctly at each level.

### AC-4: Skills integration — agents with skills get SkillRegistry
Create a temp .github/skills/ dir with a valid skill .md file. After bootstrap, agents whose definitions declare skills: (builder, orchestrator, kanban-planner, reviewer, writer, closer, architect) have SkillRegistry in their toolsets. researcher (skills: []) does not.

### AC-5: Role policies applied with real agent definitions
After registry.get(), validator-role agents (reviewer, architect, closer) have write_file and create_file denied. Builder-role agents (orchestrator, builder, kanban-planner, writer, researcher) retain full access. Test by inspecting the agent's toolsets for filtered vs unfiltered state.

## Constraints
- Use FunctionModel for all LLM calls (no real API, no TestModel)
- Use real agents_dir: src/owlbear/agents/
- Use real build_toolsets + build_agent_registry from bootstrap.py
- Mock only create_copilot_model (AsyncMock returning FunctionModel)
- Share bootstrap fixture across test classes to avoid re-bootstrapping
- ExitStack pattern for Agent.override across 8 agents (proven in test_intent_routing.py)

## Explicitly out of scope
- Hook pipeline (already tested in test_integration_e2e.py::TestHookPipeline)
- Scan-level metadata validation (already tested in test_agent_definitions.py)
- Delegation depth limits/errors (already tested in test_delegation.py)
- Knowledge/Browser/WebSearch toolset functionality
