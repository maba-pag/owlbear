# E2E Pipeline Test: Orchestrate Real Task Through Refactored Pipeline

> **Owning task:** #452 — E2E test: orchestrate real task through refactored pipeline
> **Date:** 2026-03-03 **Status:** Complete

## 1. Context and Question

How should we implement an E2E test validating the full OwlBear pipeline (bootstrap → agent registry → delegation → specialist agents) with the refactored agent definitions? This is the acceptance test for the agent definition sync (#453).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI testing docs | <https://ai.pydantic.dev/testing/> | .95 | `FunctionModel`, `TestModel`, `Agent.override`, `ALLOW_MODEL_REQUESTS` |
| `tests/test_integration_e2e.py` | local | .95 | Bootstrap→daemon→delegation→hooks E2E patterns, `FunctionModel` step-dispatch |
| `tests/test_intent_routing.py` | local | .90 | Multi-agent delegation via `_build_registry` + `ExitStack` override pattern |
| `tests/test_bootstrap_integration.py` | local | .90 | `_make_settings`, `cli_result` fixture, `_toolset_names` helper |
| `tests/test_agent_definitions.py` | local | .85 | Real agents dir scan, `EXPECTED_AGENTS` metadata, role validation |
| `src/owlbear/bootstrap.py` | local | .90 | Full wiring: `build_toolsets` → `build_agent_registry` → `OwlBearAgent` |

## 3. Analysis

### 3.1 Existing Coverage vs. Gap

| Capability | Already tested? | Where | Gap for #452 |
|------------|----------------|-------|---------------|
| Bootstrap creates BootstrapResult | Yes | `test_bootstrap_integration.py` | None |
| 8 agents parse from real `agents/` dir | Yes | `test_agent_definitions.py` | None |
| AgentRegistry.scan finds all 8 | Yes | `test_agent_definitions.py::TestRegistryScanAgentsDir` | None |
| Single delegation (outer→inner) | Yes | `test_integration_e2e.py::TestDelegation` | None |
| Sequential re-routing (2 agents) | Yes | `test_intent_routing.py::TestMidConversationReroute` | None |
| Full multi-step pipeline (4+ agents) | **No** | — | **Key gap** |
| Real agent registry in bootstrap | Yes | `test_bootstrap_integration.py::test_agent_registry_set` | None |
| Tool resolution per agent | Partial | `test_agent_definitions.py::test_get_planner_returns_agent_with_resolved_tools` | Only 1 agent tested |
| Hook pipeline with tool calls | Yes | `test_integration_e2e.py::TestHookPipeline` | None |
| Role policy filtering | Partial | `test_agent_registry.py::test_get_applies_role_policy_for_non_builder` | Synthetic, not real defs |
| Skills loaded via registry | **No** | — | **Gap** |
| System prompts loaded | Yes | `test_agent_definitions.py::test_system_prompt_nonempty` | None |

**Key gaps**: (1) Full pipeline dispatch across 4+ agents in sequence, (2) skills loading integration, (3) tool resolution for ALL agents via real bootstrap.

### 3.2 Mock Strategy

| Component | Mock? | Approach | Rationale |
|-----------|-------|----------|-----------|
| LLM model | Yes | `FunctionModel` per agent via `Agent.override` | Deterministic, no API calls |
| `create_copilot_model` | Yes | `AsyncMock` returning `FunctionModel` | Bypass OAuth |
| Channel | No | Real `CLIChannel` or `MockChannel` | Lightweight, no external deps |
| Settings | Partial | `_make_settings(tmp_path)` with real `agents_dir` | Override paths only |
| FileToolset | No | Real, on `tmp_path` | Exercise real file I/O |
| TerminalToolset | No | Real, on `tmp_path` | Exercise real subprocess |
| KanbanToolset | No | Real, on `tmp_path/kanban` | File-based, no binary needed for tool resolution |
| Knowledge/Browser | Skipped | Bootstrap silently swallows failures | Not needed for pipeline test |
| SkillRegistry | No | Real, with temp skills dir | Validates skills loading |
| AgentRegistry | No | Real, scanning real `src/owlbear/agents/` | Validates full wiring |

### 3.3 Test Pattern: Multi-Step Pipeline

Extending the proven `test_intent_routing.py` pattern:

```
1. bootstrap() with real agents_dir, FunctionModel
2. For each specialist agent in registry, apply Agent.override(model=FunctionModel)
3. Orchestrator's FunctionModel emits delegate_to_agent for each step
4. Each inner agent's FunctionModel returns a step-specific result
5. Assert: all delegations happened, results propagated correctly
```

The `contextlib.ExitStack` pattern from `test_intent_routing.py` scales to 8 agents cleanly.

### 3.4 Test Structure Decision

| Option | Scope | Run time | Confidence |
|--------|-------|----------|------------|
| A. Single monolithic test | 1 test, 4 sequential turns | ~2s | .70 — fragile, hard to debug |
| B. Test class with focused methods | 6-8 tests, each targeting one concern | ~5s total | **.85** — isolated failures, clear AC mapping |
| C. Parameterized per-agent | 8 parameterized tests | ~4s | .75 — repetitive, misses integration |

**Recommendation (.85):** Option B — a test class with focused methods sharing a common fixture. Each test validates one concern, making failures pinpointable.

### 3.5 Proposed Test File Structure

**File:** `tests/test_pipeline_e2e.py`

```
TestBootstrapRealAgents
  test_bootstrap_loads_all_eight_agents       # AgentRegistry has 8 definitions
  test_all_agents_instantiate                 # registry.get() succeeds for each
  test_tool_resolution_per_agent              # Each agent's tools resolve without KeyError

TestFullPipelineDelegation
  test_orchestrator_delegates_to_builder      # Orchestrator → builder delegation
  test_sequential_pipeline_four_agents        # Orchestrator → builder → reviewer → writer → closer
  test_delegation_depth_increments            # Inner deps._delegation_depth > 0

TestSkillsIntegration
  test_agents_with_skills_get_skill_registry  # builder, orchestrator get SkillRegistry in toolsets
  test_agents_without_skills_skip_registry    # researcher has no skills → no SkillRegistry

TestRolePoliciesApplied
  test_validator_agents_deny_write_tools      # reviewer, architect, closer have filtered toolsets
  test_builder_agents_keep_all_tools          # builder, orchestrator keep full toolsets

TestHooksPipelineIntegration
  test_hooks_fire_during_delegation           # PRE_TOOL → delegate → POST_TOOL fires
```

### 3.6 Key Technical Decisions

1. **Use real `agents_dir`** (`src/owlbear/agents/`) — not temp copies. This validates the actual shipped definitions.
2. **Use `build_agent_registry` from bootstrap** — not manual `AgentRegistry` construction. Tests the real `_resolve` function.
3. **Use `FunctionModel` for deterministic control** — not `TestModel` (auto-calls all tools with garbage args).
4. **Shared async fixture** for bootstrap result — avoids re-bootstrapping per test.
5. **Skills dir from workspace** — create a temp `.github/skills/` with one test skill definition.

### 3.7 Estimated Effort

| Work item | LOC | Time |
|-----------|-----|------|
| Shared fixtures (settings, bootstrap, overrides) | ~40 | 15 min |
| TestBootstrapRealAgents (3 tests) | ~60 | 20 min |
| TestFullPipelineDelegation (3 tests) | ~80 | 30 min |
| TestSkillsIntegration (2 tests) | ~40 | 15 min |
| TestRolePoliciesApplied (2 tests) | ~40 | 15 min |
| TestHooksPipelineIntegration (1 test) | ~30 | 10 min |
| **Total** | **~290** | **~105 min** |

### 3.8 Blockers and Concerns

1. **KanbanToolset needs kanban dir** — `build_toolsets` creates `KanbanToolset(kanban_dir=workspace/"kanban")`. The toolset won't fail without the binary; tool resolution just needs the class to exist. No blocker.
2. **Knowledge/Browser/WebSearch** — All conditional, fail silently. No blocker.
3. **SkillRegistry needs real skills dir** — Must create `tmp_path/.github/skills/test.md` with valid YAML frontmatter. Already done in `test_bootstrap.py`.
4. **Role policy test requires introspecting filtered toolsets** — `_build_agent` in AgentRegistry filters toolsets for validators. Need to inspect the Agent's `_user_toolsets` after `get()`. May need to access internal attribute.

## 4. Recommendation (.85 confidence)

Create `tests/test_pipeline_e2e.py` with 11 focused tests in 5 test classes. Use real `agents_dir` from `src/owlbear/agents/`, real `build_agent_registry`, and `FunctionModel` for all LLM calls. Share a bootstrap fixture across tests.

Risk: Agent override scope with `ExitStack` across 8 agents needs care — but `test_intent_routing.py` proves the pattern works at scale (5 agents). Low risk (.15).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement E2E pipeline test" --priority needed --status todo --tags "test,agent-refactor,phase-refactor" --depends-on 453 --body "Create tests/test_pipeline_e2e.py with 11 tests in 5 classes validating the full pipeline: bootstrap with real agents → tool resolution → multi-agent delegation → skills loading → role policies → hook pipeline. See docs/research/e2e-pipeline-test.md §3.5 for structure. AC: (1) All 8 agents instantiate from real definitions (2) Tool resolution works for every agent (3) 4-step pipeline delegation works (4) Skills integration tested (5) Role policies validated (6) Hooks fire during delegation (7) All tests pass with `uv run pytest tests/test_pipeline_e2e.py -q --tb=short`"
```

```
kanban\kanban-md.exe move 452 backlog
```
