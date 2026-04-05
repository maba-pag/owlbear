# End-to-End Dispatch Test — Research Findings

> **Owning task:** #23 — End-to-end dispatch test
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #23 requires proving the full v2 stack works end-to-end: CLI command
dispatches a task, Copilot CLI spawns via ACP, the agent works autonomously
using MCP tools (kanban), and the board updates on completion.

Key questions: (1) What test architecture handles both automated CI and manual
validation? (2) How to make E2E tests deterministic when Copilot CLI responses
are non-deterministic? (3) What mock layers are needed? (4) What fixtures and
infrastructure must exist? (5) What's the dependency timeline?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|:---------:|
| S1 | ACP SDK `test_rpc.py` — in-memory agent/client test harness | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py) | .95 |
| S2 | ACP SDK `test_spawn_agent_process_roundtrip` — subprocess E2E | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/tests/test_rpc.py) | .95 |
| S3 | ACP SDK `duet.py` — two-process spawn pattern | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/examples/duet.py) | .90 |
| S4 | ACP SDK `conftest.py` — TestClient/TestAgent mock helpers | [github](https://github.com/agentclientprotocol/python-sdk/blob/main/tests/conftest.py) | .90 |
| S5 | OwlBear mcp-kanban `test_integration.py` — real binary E2E | `packages/mcp-kanban/tests/test_integration.py` | .95 |
| S6 | OwlBear `hello_world.py` — ACP spawn pattern | `packages/orchestrator/examples/hello_world.py` | .90 |
| S7 | OwlBear `acp_client.py` + `process_supervisor.py` | `packages/orchestrator/src/owlbear_orchestrator/` | .95 |
| S8 | OwlBear `e2e-pipeline-test.md` (v1 E2E research) | `docs/research/e2e-pipeline-test.md` | .80 |
| S9 | ACP architecture spec | [agentclientprotocol.com](https://agentclientprotocol.com/get-started/architecture) | .85 |
| S10 | OwlBear dispatch-planning SKILL + orchestration SKILL | `skills/dispatch-planning/`, `skills/orchestration/` | .90 |

## 3. Analysis

### 3.1 Dependency Status — Blocking Assessment

| Dep | Task | Status | Blocks #23? |
|-----|------|--------|:-----------:|
| #14 | Build mcp-kanban server | archived | No |
| #20 | Build dispatch planner (umbrella) | backlog (#144 backlog, #145 ideation, #146 ideation) | **Yes** |
| #22 | Build CLI trigger commands | backlog | **Yes** |

#23 cannot be implemented until #20's subtasks and #22 are complete. Research
now establishes the test architecture so implementation can proceed immediately
when dependencies clear.

### 3.2 Test Architecture Options

| Criterion | A: Real Copilot CLI (.55) | B: Mock ACP Agent (.85) | C: Layered (.90) |
|-----------|--------------------------|-------------------------|-------------------|
| Determinism | Non-deterministic (LLM varies) | Deterministic | Deterministic (layer 1-2) + manual (layer 3) |
| CI-friendly | No (needs auth, internet) | Yes | Yes (layers 1-2) |
| Coverage | Full stack incl. LLM | Full stack minus LLM | Full per layer |
| Repeatability | Poor (AC item: repeatable) | Excellent | Excellent (layers 1-2) |
| Setup cost | Low (just needs Copilot CLI) | Medium (~100 LOC agent) | Medium-High |
| KISS alignment | High | High | Medium |

### 3.3 Layered Test Architecture (Recommended)

**Layer 1 — Integration test with mock ACP agent** (automated, CI-friendly):

The ACP SDK provides `spawn_agent_process()` which spawns any Python script as
an ACP agent subprocess [S2, S3]. We write a ~80 LOC `test_agent.py` that:
1. Receives the ACP prompt (containing task ID)
2. Calls `kanban-md.exe` to read the task
3. Edits the task body (simulating work)
4. Calls `kanban-md.exe` to move the task
5. Returns a PromptResponse

This exercises: CLI invocation, planner board read, gate checks, task selection,
agent mapping, ProcessSupervisor spawn, AcpClient session, mock agent execution,
kanban board mutations, audit logging. The only thing NOT tested is real LLM
behavior — which is inherently non-deterministic.

```
Test harness
  ├── Temp kanban board (config.yml + tasks/)  [S5 pattern]
  ├── Mock ACP agent (Python script)           [S2 pattern]
  ├── owlbear dispatch <id>
  │   ├── Planner reads board via kanban-md    [S10]
  │   ├── ProcessSupervisor spawns mock agent  [S7]
  │   ├── AcpClient sends prompt               [S7]
  │   ├── Mock agent edits kanban board         [S5]
  │   └── CLI reports outcome
  └── Assertions: task status changed, agent got prompt, audit entry
```

**Layer 2 — Manual smoke test script** (for human validation with real Copilot):

A standalone script (`scripts/e2e_smoke.py`) that:
1. Creates a temp task: "E2E smoke test" with trivial AC
2. Runs `owlbear dispatch <id>` targeting it
3. Waits for completion (with timeout)
4. Checks board state, prints pass/fail
5. Cleans up the temp task

This covers AC items 3 ("Copilot CLI spawns") and 8 ("Document manual steps").

### 3.4 Mock Agent Pattern (from ACP SDK)

The ACP SDK's `echo_agent.py` + `test_spawn_agent_process_roundtrip` [S2]
proves the pattern: spawn a Python script as ACP agent, send a prompt, verify
the response. Key code path:

```python
async with spawn_agent_process(client, sys.executable, str(agent_script)) as (conn, proc):
    await conn.initialize(protocol_version=PROTOCOL_VERSION)
    session = await conn.new_session(mcp_servers=[], cwd=str(tmp_path))
    await conn.prompt(session_id=session.session_id, prompt=[text_block("...")])
```

For OwlBear's E2E test, the mock agent receives the task ID in the prompt,
calls `kanban-md.exe` as a subprocess to edit the board, and returns. The
`ProcessSupervisor` and `AcpClient` wrappers are exercised identically to
production — only the binary name changes from `copilot` to `python test_agent.py`.

### 3.5 Temp Board Fixture (from mcp-kanban)

The `test_integration.py` pattern [S5] creates a minimal kanban board in
`tmp_path` with `config.yml` and `tasks/`. The E2E test reuses this:

```python
@pytest.fixture
def board_dir(tmp_path):
    (tmp_path / "tasks").mkdir()
    (tmp_path / "config.yml").write_text(BOARD_CONFIG)
    # Pre-create a test task
    subprocess.run([kanban_bin, "create", "E2E test task", "--dir", str(tmp_path)])
    return tmp_path
```

### 3.6 AC Mapping to Test Approach

| AC Item | Layer 1 (mock agent) | Layer 2 (smoke script) |
|---------|:--------------------:|:----------------------:|
| Create test task on board | Fixture creates task | Script creates task |
| Run `owlbear dispatch <id>` | CLI invoked via CliRunner | CLI invoked via subprocess |
| Copilot CLI spawns, receives prompt | Mock agent spawns | Real Copilot spawns |
| Agent uses MCP tools (kanban) | Mock agent calls kanban-md | Copilot uses mcp-kanban |
| Task status updates on completion | Assert board state | Assert board state |
| Audit log records dispatch/outcome | Assert log entry | Assert log entry |
| Repeatable: run multiple times | pytest (deterministic) | Script (manual) |
| Document manual steps | N/A | Script IS the doc |

### 3.7 Test File Structure

```
tests/
  test_e2e_dispatch.py          # Layer 1: integration test (~150 LOC)
  fixtures/
    mock_acp_agent.py           # Mock agent script (~80 LOC)
scripts/
  e2e_smoke.py                  # Layer 2: manual smoke test (~100 LOC)
```

### 3.8 Pytest Markers

```python
@pytest.mark.integration  # requires kanban-md binary
@pytest.mark.e2e          # full-stack, slower
```

Both markers allow selective test runs: `pytest -m e2e` for the full stack,
`pytest -m "not e2e"` for fast unit tests.

## 4. Recommendation (.85 confidence)

**Layered approach (Option C):** Primary deliverable is a deterministic
integration test with a mock ACP agent (Layer 1). Secondary deliverable is a
manual smoke test script for real Copilot CLI validation (Layer 2).

This satisfies all 8 AC items across the two layers. Layer 1 is automated and
CI-friendly (covers 6/8 AC items). Layer 2 covers the remaining 2 items that
require real Copilot CLI ("Copilot CLI spawns" and "Document manual steps").

**Risks:**
- Dependencies #20 and #22 must complete first (both at backlog)
- Mock agent complexity may grow if agent-kanban interactions become elaborate
- Real Copilot CLI may change ACP behavior between versions

**Mitigations:**
- Pin ACP SDK version (already `>=0.9.0,<1.0.0`)
- Keep mock agent minimal — only kanban-md subprocess calls
- AC for #23 should be refined: Layer 1 is the primary automated deliverable;
  Layer 2 is a supplementary manual validation tool

## 5. Follow-up Tasks

Decompose #23 into implementation tasks once dependencies clear:

```
kanban\kanban-md.exe create "Build mock ACP agent for E2E testing" --priority needed --status ideation --tags "phase-2,scope:orchestrator,type:test" --depends-on 20 --body "## Objective\nCreate a mock ACP agent Python script that receives task IDs via ACP prompt, reads/edits kanban board via kanban-md subprocess, and returns PromptResponse. Used as test double for Copilot CLI in E2E dispatch tests.\n\n## Acceptance Criteria\n- [ ] Python script at tests/fixtures/mock_acp_agent.py implementing ACP Agent interface\n- [ ] Receives prompt containing task ID, parses it\n- [ ] Calls kanban-md.exe to read task (show), edit body, and move status\n- [ ] Returns PromptResponse with stop_reason end_turn\n- [ ] Works with spawn_agent_process() from ACP SDK\n- [ ] Unit test verifying agent behavior with mocked kanban-md\n\n## Context\nSee docs/research/e2e-dispatch-test.md S3.4 for the mock agent pattern from ACP SDK."
```

```
kanban\kanban-md.exe create "Implement E2E dispatch integration test" --priority needed --status ideation --tags "phase-2,scope:orchestrator,type:test" --depends-on 20,22 --body "## Objective\nIntegration test proving full dispatch stack: CLI command, planner, AcpClient, mock agent, kanban board mutations.\n\n## Acceptance Criteria\n- [ ] Test file at tests/test_e2e_dispatch.py\n- [ ] Temp kanban board fixture with pre-created test task\n- [ ] owlbear dispatch <id> invoked via Typer CliRunner\n- [ ] Mock ACP agent spawned instead of Copilot CLI\n- [ ] Assert task status changed after dispatch completes\n- [ ] Assert audit log contains dispatch entry\n- [ ] Marked @pytest.mark.integration and @pytest.mark.e2e\n- [ ] Repeatable: passes on consecutive runs\n- [ ] All tests pass with uv run pytest tests/test_e2e_dispatch.py -q --tb=short\n\n## Context\nSee docs/research/e2e-dispatch-test.md S3.3 (Layer 1). Depends on #20 (planner) and #22 (CLI)."
```

```
kanban\kanban-md.exe create "Create E2E smoke test script for real Copilot CLI" --priority important --status ideation --tags "phase-2,scope:orchestrator,type:test" --depends-on 20,22 --body "## Objective\nManual smoke test script that validates the full stack with real Copilot CLI.\n\n## Acceptance Criteria\n- [ ] Script at scripts/e2e_smoke.py\n- [ ] Creates temp task on kanban board\n- [ ] Runs owlbear dispatch targeting temp task\n- [ ] Waits for completion with configurable timeout (default 5 min)\n- [ ] Checks board state and prints PASS/FAIL\n- [ ] Cleans up temp task on exit\n- [ ] Documents prerequisites (Copilot CLI installed, authenticated)\n- [ ] Script header documents manual steps required\n\n## Context\nSee docs/research/e2e-dispatch-test.md S3.3 (Layer 2). Supplements the automated integration test."
```
