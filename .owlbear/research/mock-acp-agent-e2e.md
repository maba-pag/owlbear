# Mock ACP Agent for E2E Testing

> **Owning task:** #155 — Build mock ACP agent for E2E testing
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #155 requires a mock ACP agent script at `tests/fixtures/mock_acp_agent.py`
that acts as a test double for Copilot CLI. It receives task IDs via ACP prompt,
calls `kanban-md.exe` to mutate the board, and returns `PromptResponse`. Used by
the E2E dispatch integration test (#156).

Key questions: (1) What is the minimum Agent interface to implement? (2) What's
the right entry point (`run_agent` vs raw `AgentSideConnection`)? (3) Can #155
proceed without waiting for #20 (dispatch planner)? (4) Testing approach?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|:---------:|
| S1 | ACP SDK `interfaces.py` — Agent Protocol | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/interfaces.py) | .95 |
| S2 | ACP SDK `examples/agent.py` — ExampleAgent | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/examples/agent.py) | .95 |
| S3 | ACP SDK `stdio.py` — `spawn_agent_process()` | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/stdio.py) | .90 |
| S4 | ACP SDK `test_rpc.py` — spawn roundtrip test | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py) | .90 |
| S5 | ACP SDK `examples/duet.py` — two-process spawn | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/examples/duet.py) | .85 |
| S6 | OwlBear `hello_world.py` — ACP spawn pattern | `packages/orchestrator/examples/hello_world.py` | .90 |
| S7 | ACP SDK `conftest.py` — TestAgent/TestClient | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/tests/conftest.py) | .90 |
| S8 | OwlBear `e2e-dispatch-test.md` S3.4 | `docs/research/e2e-dispatch-test.md` | .95 |
| S9 | OwlBear mcp-kanban `test_integration.py` | `packages/mcp-kanban/tests/test_integration.py` | .85 |

## 3. Analysis

### 3.1 Agent Protocol — Required Methods

The `Agent` Protocol [S1] declares 15 methods. Analysis of which ones the mock
must implement meaningfully vs. stub:

| Method | Mock behavior | Rationale |
|--------|--------------|-----------|
| `initialize` | Return `InitializeResponse` with version | Required by ACP handshake [S2, S4] |
| `new_session` | Return `NewSessionResponse` with session_id | Required by session setup [S2] |
| `prompt` | **Core logic**: parse task ID, call kanban-md, return `PromptResponse` | The whole point of the mock |
| `cancel` | No-op | Not exercised in E2E test |
| `on_connect` | Save `conn` reference for `session_update` | Needed to send progress updates [S2] |
| Other 10 methods | Stub (return default/None) | Not called during E2E dispatch flow |

### 3.2 Entry Point: `run_agent()` vs Raw Connection

| Criterion | `run_agent(agent)` (.90) | Raw `AgentSideConnection` (.60) |
|-----------|--------------------------|--------------------------------|
| Subprocess compatibility | Yes — reads/writes stdio | Requires manual pipe setup |
| Matches `spawn_agent_process` | Yes — duet.py + test_rpc.py pattern [S4, S5] | No |
| LOC overhead | ~3 lines (import + call) | ~15 lines for pipe setup |
| KISS alignment | High — single function call | Low |

**Verdict (.90):** Use `run_agent()`. It's the standard entry point for agent
scripts spawned via `spawn_agent_process()` [S3, S5]. The test harness calls
`spawn_agent_process(client, sys.executable, "mock_acp_agent.py")` which spawns
the script as a subprocess, connecting stdin/stdout via ACP JSON-RPC.

### 3.3 Dependency Analysis

#155 currently depends on #20 (dispatch planner). However:

- The mock agent is a **standalone Python script** — it doesn't import planner code
- It only needs the `acp` SDK (already installed) and `kanban-md.exe` (binary)
- The dependency on #20 exists because the E2E test (#156) needs the planner,
  but the mock agent itself does not

**Recommendation (.85):** Remove `depends_on: [20]` from #155. The mock agent
can be built and unit-tested immediately. Only the E2E integration test (#156)
needs to wait for #20 and #22.

### 3.4 Implementation Sketch (~60 LOC)

```
mock_acp_agent.py
├── KanbanMockAgent(Agent)
│   ├── on_connect(conn)       — save client conn
│   ├── initialize(...)        — return version + caps
│   ├── new_session(...)       — return session_id
│   ├── prompt(prompt, ...)    — CORE: parse task ID → kanban-md calls → PromptResponse
│   └── 11 stubs              — return defaults
└── main() → run_agent(KanbanMockAgent())
```

The `prompt()` method:
1. Extracts task ID from first `TextContentBlock` via regex `#(\d+)` or `task (\d+)`
2. Runs `kanban-md.exe show <id> --dir <board_dir>` as subprocess
3. Runs `kanban-md.exe edit <id> -a "Mock agent processed" --dir <board_dir>`
4. Runs `kanban-md.exe move <id> <next_status> --dir <board_dir>`
5. Sends `session_update` with agent message text ("Processed task #ID")
6. Returns `PromptResponse(stop_reason="end_turn")`

**Board dir:** Passed via environment variable `KANBAN_DIR` (set by test fixture).
**Kanban binary:** Resolved via `KANBAN_BIN` env var or default path.

### 3.5 Unit Testing Approach

| Test | Mock | Assertion |
|------|------|-----------|
| Parses task ID from prompt | N/A (pure string parsing) | Correct ID extracted |
| Calls kanban-md show | `subprocess.run` | Called with `["kanban-md", "show", "42", "--dir", ...]` |
| Calls kanban-md edit | `subprocess.run` | Called with `["kanban-md", "edit", "42", "-a", ...]` |
| Calls kanban-md move | `subprocess.run` | Called with `["kanban-md", "move", "42", ...]` |
| Returns PromptResponse | N/A | `stop_reason == "end_turn"` |
| Works with spawn_agent_process | In-memory pipes [S4, S7] | Full roundtrip: prompt in, response out |

The unit test can use the ACP SDK's `TestClient` + in-memory pipes pattern [S7]
for the spawn roundtrip test, and simple `subprocess.run` mocking for kanban-md
verification.

## 4. Recommendation (.90 confidence)

**Proceed with implementation.** The AC is well-defined and validated against
the ACP SDK interface.

1. Use `run_agent()` as entry point — matches SDK patterns [S2, S5]
2. **Remove dependency on #20** — mock agent is standalone, only E2E test needs planner
3. ~60 LOC implementation following `examples/agent.py` pattern [S2]
4. Pass board dir via `KANBAN_DIR` env var for test isolation
5. Unit test with mocked `subprocess.run` + one spawn roundtrip test with in-memory pipes

**Risk:** ACP SDK Agent Protocol may add required methods in future versions.
**Mitigation:** Pin `agent-client-protocol>=0.9.0,<1.0.0` (already done).

## 5. Follow-up Tasks

AC refinements for #155 (no new tasks needed — AC is already well-scoped):

- Remove `depends_on: [20]` — mock agent has no code dependency on the planner
- Add AC item: "Board dir configurable via KANBAN_DIR environment variable"
- Add AC item: "Kanban binary path configurable via KANBAN_BIN environment variable"
