# Bootstrap-to-Daemon E2E Integration Tests

> **Owning task:** #295 — End-to-end integration test — bootstrap to daemon loop
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Task #295 requires integration tests covering the full system wiring: bootstrap → agent → tools → daemon loop. Individual modules have 1883 unit tests but the *composition* — how modules connect at runtime — has gaps. Question: what exactly is untested, what patterns should the tests follow, and how complex is implementation?

## 2. Sources Studied

| Source | Location | Relevance | What |
|---|---|---|---|
| test_bootstrap_integration.py | tests/ | .95 | Existing bootstrap + TestModel integration pattern |
| test_e2e_chat.py | tests/ | .95 | FunctionModel step-dispatch for tool calls |
| test_daemon.py | tests/ | .90 | MockChannel + daemon loop tests (AsyncMock agent) |
| test_hooked_toolset.py | tests/ | .85 | Hook order verification pattern |
| test_delegation.py | tests/ | .85 | Mock registry delegation pattern |
| PydanticAI testing docs | ai.pydantic.dev/testing/ | .80 | TestModel, FunctionModel, Agent.override |

## 3. Analysis

### 3.1 Coverage Baseline

| Module | Coverage | Missing Lines |
|---|---|---|
| bootstrap.py | 95% | 158-160 (voice), 216-217, 248-249, 284 |
| daemon.py | 92% | 55-60 (auth partial), 182-184 (otel), 222 |
| **Total** | **93%** | Already exceeds 90% gate |

New tests fill **wiring gaps** (component composition), not raw line coverage.

### 3.2 AC Gap Analysis

| AC Item | Already Tested? | Gap |
|---|---|---|
| bootstrap() with mock model | **Yes** — test_bootstrap_integration.py (11 tests) | Consolidate in new file |
| run_daemon() 1 msg + sentinel exit | **Partial** — test_daemon.py uses AsyncMock agent | Never wired with real OwlBearAgent + mock LLM |
| bearclaw chat loop I/O | **No** | `_chat_loop()` entirely untested |
| delegation orchestrator → coder | **No** (component-level only) | Never tested through full bootstrap stack |
| hook pipeline order through stack | **Partial** — unit-tested in HookedToolset | Never verified through bootstrap wiring |

### 3.3 Mock Patterns Available

| Pattern | Source | Use Case |
|---|---|---|
| `FunctionModel(callback)` | test_e2e_chat.py | Step-based dispatch (tool call → text) |
| `TestModel(custom_output_text=...)` | test_bootstrap_integration.py | Simple text-only response |
| `Agent.override(model=...)` | test_e2e_chat.py | Model injection on existing agent |
| `patch("owlbear.bootstrap.create_copilot_model")` | test_bootstrap_integration.py | Intercept model creation |
| `CLIChannel(input=StringIO, output=StringIO)` | channels/cli.py | Test I/O injection |
| `MockChannel(messages=[...])` | test_daemon.py | Programmable receive/send |

### 3.4 Implementation Complexity

| Test Class | Complexity | LOC Est. | Key Mock |
|---|---|---|---|
| TestBootstrapE2E | Low | ~30 | TestModel (proven in test_bootstrap_integration.py) |
| TestDaemonWithRealAgent | Medium | ~50 | FunctionModel + bootstrap + sentinel |
| TestChatLoopE2E | Medium | ~40 | FunctionModel + CLIChannel(StringIO) |
| TestDelegationE2E | High | ~60 | FunctionModel dispatching delegate_to_agent |
| TestHookPipelineOrder | Medium | ~40 | FunctionModel + custom hook listener |

Total: ~220 LOC in `tests/test_integration_e2e.py`.

## 4. Recommendation (.90 confidence)

**Proceed with implementation.** All mock patterns are proven. Key approach:

1. **Daemon test** — Wire `run_daemon()` with real `OwlBearAgent` + `FunctionModel` via `Agent.override` (biggest wiring gap — currently only tested with AsyncMock agent).
2. **Chat loop** — Test `_chat_loop()` directly with `CLIChannel(input=StringIO("hello\nexit\n"), output=StringIO())`, verify output.
3. **Delegation** — Create minimal agent def `.md` files in tmp_path, bootstrap with `agents_dir=tmp_path`, FunctionModel emits `delegate_to_agent` ToolCallPart.
4. **Hook order** — Register test listener on bootstrapped hooks, run agent.turn(), assert `[PRE_TOOL_USE, POST_TOOL_USE]` order.
5. **Guard** — `ALLOW_MODEL_REQUESTS = False` globally (existing convention).

**Risk:** Delegation test requires two agent definitions + two FunctionModels. Mitigation: pattern exists in test_delegation.py at component level; scaling is mechanical.

## 5. Follow-up Tasks

Single implementation task: build `tests/test_integration_e2e.py` with all 5 test classes per the AC. See kanban commands below.
