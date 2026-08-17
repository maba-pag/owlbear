# E2E Integration Tests for Chat and Daemon Lifecycle

> **Owning task:** #126 — E2E integration tests for chat and daemon lifecycle
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

Task #126 requires E2E integration tests proving the full P7 stack works end-to-end: OwlBearAgent + FileToolset + TerminalToolset + CLIChannel + SessionStore. The key question: **how to mock the LLM so tool-calling flows execute realistically without real API calls?**

Dependencies (all DONE): #120 (FileToolset), #121 (TerminalToolset), #122 (bearclaw chat CLI).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI testing docs | <https://ai.pydantic.dev/testing/> | .95 | Official patterns: `TestModel`, `FunctionModel`, `Agent.override`, `ALLOW_MODEL_REQUESTS`, `capture_run_messages` |
| PydanticAI `models/test.py` (installed v1.63.0) | source code | .95 | `TestModel` internals: auto-calls all tools, generates args from JSON schema, returns tool results as JSON text |
| PydanticAI `models/function.py` (installed) | source code | .90 | `FunctionModel` internals: custom `(messages, AgentInfo) -> ModelResponse` callback for full control |
| OwlBear `test_agent.py` (existing) | tests/test_agent.py | .85 | Current test patterns: `MagicMock` on `agent.inner.run`, `AsyncMock` side_effect |
| OwlBear `test_cli_chat.py` (existing) | tests/test_cli_chat.py | .85 | CLI testing via `typer.testing.CliRunner`, patching `OwlBearSettings`/`SessionStore`/`OwlBearAgent` |
| PydanticAI weather_app example | <https://ai.pydantic.dev/testing/> | .80 | Canonical `FunctionModel` E2E pattern: parse user prompt → emit `ToolCallPart` → receive `ToolReturnPart` → emit `TextPart` |

## 3. Analysis

### 3.1 Mock Strategy Comparison

| Criterion | TestModel (.65) | FunctionModel (.90) | MagicMock on inner (.50) |
|-----------|----------------|--------------------|-----------------------|
| Tool args realism | Auto-generated from JSON schema (e.g. `path="a"`) — not realistic | Full control — specify exact args | N/A — tools never called |
| Tool execution | Actually calls registered tools | Actually calls registered tools | No real tool execution |
| Multi-step flows | Calls all tools → returns JSON of results | Custom logic per conversation step | Only returns canned response |
| E2E coverage | Medium — proves wiring but args are synthetic | High — proves exact scenarios (read specific file, run specific cmd) | Low — only tests agent wrapper |
| Complexity | Zero config | ~15 LOC per test function | ~5 LOC per test |
| Determinism | Deterministic but synthetic | Deterministic and realistic | Deterministic but trivial |

**Verdict:** `FunctionModel` is the right choice for E2E tests. It gives full control over which tools get called with what args, while still executing real tool code. `TestModel` is suitable for smoke tests but generates meaningless args (`path="a"`).

### 3.2 Key Patterns

**Pattern A: FunctionModel with step-based dispatch**

```python
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart


def _model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if len(messages) == 1:
        # Step 1: call the tool
        return ModelResponse(parts=[ToolCallPart("read_file", {"path": "hello.txt"})])
    else:
        # Step 2: summarize the tool result
        return ModelResponse(parts=[TextPart("The file contains: hello world")])
```

The model function receives the full conversation so far. On the first call (user prompt only), it emits a `ToolCallPart`. PydanticAI executes the real tool, appends a `ToolReturnPart`, and calls the model function again. On the second call, it returns a `TextPart` as the final answer.

**Pattern B: Agent.override for OwlBearAgent**

`OwlBearAgent.inner` is a PydanticAI `Agent`. We can use `agent.inner.override(model=FunctionModel(...))` to swap the model for testing:

```python
agent = OwlBearAgent(model="test", session=store, toolsets=[FileToolset(ws)])
with agent.inner.override(model=FunctionModel(my_fn)):
    result = await agent.turn("Read hello.txt")
```

This exercises the full stack: hooks → session load → Agent.run (with FunctionModel) → real tool execution → session save → return output.

**Pattern C: ALLOW_MODEL_REQUESTS safety net**

```python
from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False  # Global — blocks real LLM calls
```

Set globally at module level in the test file. `TestModel` and `FunctionModel` are exempt from this check.

**Pattern D: capture_run_messages for inspection**

```python
from pydantic_ai import capture_run_messages

with capture_run_messages() as messages:
    result = await agent.turn("...")
# messages now contains the full ModelMessage list for assertion
```

### 3.3 Test Scenarios Mapped to AC

| AC | Mock Strategy | What's Tested |
|----|--------------|---------------|
| REPL startup, send message, agent responds | FunctionModel returning `TextPart` | OwlBearAgent.turn → session → response |
| Agent uses read_file to read tmp_path file | FunctionModel emitting `ToolCallPart("read_file", {"path": "test.txt"})` | FileToolset._read_file executes, content returned to model |
| Agent uses run_command to execute command | FunctionModel emitting `ToolCallPart("run_command", {"command": "echo hi"})` | TerminalToolset.run_command executes subprocess |
| Agent uses ask_user (mocked channel) | FunctionModel emitting `ToolCallPart("ask_user", ...)` — **BLOCKED** | ask_user tool doesn't exist yet (not in FileToolset/TerminalToolset) |
| Graceful shutdown saves session | Test sends prompt → asserts session file exists with messages | SessionStore.save called by agent.turn |
| Session persistence across restarts | Create agent, run turn, create new agent with same session path, verify history loaded | SessionStore.load returns previous messages |

### 3.4 ask_user Tool — Gap Identified

The AC requires testing "Agent uses ask_user tool (mocked channel), user responds." However, **no `ask_user` tool exists** in the current codebase. The `CLIChannel` has `receive()`, but there's no tool that exposes this to the LLM. This would need to be a `FunctionToolset` tool that calls `channel.receive()`.

**Options:**

1. Create a minimal `ask_user` tool as part of the E2E test setup (test-only)
2. Create the tool in production code first, then test it
3. Defer this AC item to a follow-up task

Recommendation (.75): Option 2 — create a `ChatToolset` with `ask_user` in production, then test it. This is a natural need for interactive chat. But it's a separate task from #126.

### 3.5 OwlBearAgent.turn vs Direct Agent.run

`OwlBearAgent.turn()` wraps `self.inner.run()` with hooks, session persistence, and usage tracking. For E2E tests, we want to test through `turn()` (not `Agent.run()` directly) to validate the full stack. The override approach (`agent.inner.override(model=...)`) is compatible with this.

### 3.6 Async Test Execution

PydanticAI recommends `pytest-anyio` with `pytestmark = pytest.mark.anyio`. Our project uses `pytest-asyncio`. Both work — `asyncio.run()` is the pattern used in existing tests. For consistency, continue using `asyncio.run()` in sync test methods.

## 4. Recommendation (.85 confidence)

Use **FunctionModel** as the primary mock, with **Agent.override** on `OwlBearAgent.inner`, guarded by **ALLOW_MODEL_REQUESTS=False**.

Implementation plan:

1. Create `tests/test_e2e_chat.py` with `models.ALLOW_MODEL_REQUESTS = False`
2. Each test creates `OwlBearAgent` with real `SessionStore`, real `FileToolset`/`TerminalToolset`, and `FunctionModel` via override
3. Test functions use step-based dispatch (Pattern A above)
4. The `ask_user` AC is deferred to a separate task that creates a `ChatToolset`
5. Session persistence tested by creating two sequential agents sharing the same session path

Risks:

- `FunctionModel` must handle `run_command`'s async tool correctly — PydanticAI wraps sync tools in executors, async tools run natively. `TerminalToolset._run_command_wrapper` is async, registered via `add_function`. Verify PydanticAI handles this. Risk: Low (.15).
- `Agent.override` may not compose correctly with `OwlBearAgent.turn()` if `turn()` replaces `self.inner`. Current code doesn't — `turn()` calls `self.inner.run()` which respects overrides. Risk: Very low (.05).

## 5. Follow-up Tasks

1. **Implement E2E integration tests for chat** — Core test file covering 5 of 6 AC scenarios (exclude ask_user). Use FunctionModel + Agent.override pattern.
2. **Create ChatToolset with ask_user tool** — Production tool that bridges ChannelPlugin.receive() into an LLM-callable tool. Required for the ask_user AC.
3. **E2E test for ask_user tool** — After ChatToolset exists, add the ask_user E2E test.
