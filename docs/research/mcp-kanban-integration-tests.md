# mcp-kanban Integration Tests with Real kanban-md Binary

> **Owning task:** #57 — Add mcp-kanban integration tests with real kanban-md binary
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #57 asks for integration tests exercising mcp-kanban MCP tools against
the real `kanban-md.exe` binary with a temp board directory. Unit tests (#65)
use mock subprocess; these integration tests verify the full stack: MCP tool →
subprocess → real binary → temp filesystem → response parsing.

Key questions: (a) how to run MCP tools in-process for testing, (b) how to
isolate test boards, (c) how to handle binary availability in CI.

## 2. Sources Studied

| # | Source | URL | Key Takeaway | Relevance |
|---|--------|-----|--------------|-----------|
| 1 | MCP Python SDK test suite | `github.com/modelcontextprotocol/python-sdk` (v1.26.0) | `mcp.shared.memory.create_connected_server_and_client_session` provides in-memory client/server pair for testing tools without transport | .95 |
| 2 | MCP Python SDK README | `github.com/modelcontextprotocol/python-sdk` | FastMCP lifespan pattern, `ctx.request_context.lifespan_context` for accessing shared state | .90 |
| 3 | v1 KanbanToolset | `v1/src/owlbear/tools/kanban.py` | `_run_kanban()` appends `--no-color --dir {kanban_dir}` to every call; 7 tool signatures | .90 |
| 4 | Scaffold mcp-kanban research | `docs/research/scaffold-mcp-kanban.md` | Lifespan yields `AppContext(kanban_bin=Path(...))`, binary resolution via env var + convention | .85 |
| 5 | kanban-md config | `kanban/config.yml` | Minimal config: `version`, `board.name`, `tasks_dir`, `statuses` list, `next_id` | .80 |
| 6 | pytest tmp_path docs | `docs.pytest.org` | `tmp_path` fixture provides unique temporary directory per test; cleaned automatically | .75 |

## 3. Analysis

### 3a. In-Process MCP Testing Pattern

The MCP SDK uses `create_connected_server_and_client_session` (source 1) to
create an in-memory client connected to a server's low-level backend. Tests
call `client.call_tool("tool_name", {args})` and assert on `result.content`.

| Approach | Pros | Cons | Score |
|----------|------|------|-------|
| A. In-memory via `client_session(mcp._mcp_server)` | No transport overhead, fast, same pattern as SDK tests | Requires lifespan override for temp dir | .90 |
| B. Stdio subprocess (launch server as child) | Tests real transport | Slow, complex setup, fragile | .50 |
| C. Direct tool function calls (no MCP) | Simplest | Skips MCP serialization/context layer | .65 |

**Recommendation (.90):** Option A — in-memory client session. This tests the
full MCP tool → lifespan → subprocess → binary chain without transport noise.

### 3b. Board Isolation Strategy

| Strategy | Pros | Cons | Score |
|----------|------|------|-------|
| `tmp_path` per test | Full isolation, auto-cleanup | Needs config + tasks dir setup | .90 |
| Shared temp board (session-scoped) | Faster, fewer fixtures | Test ordering deps, cleanup risk | .65 |
| Use real `kanban/` dir | Zero setup | Mutates real board, dangerous | .10 |

**Recommendation (.90):** `tmp_path` per test. Create minimal `config.yml` +
`tasks/` directory via a pytest fixture. Each test starts with a clean board.

### 3c. Minimal Board Config

From source 5, the minimal `config.yml` that `kanban-md.exe` needs:

```yaml
version: 10
board:
    name: test
tasks_dir: tasks
statuses:
    - name: ideation
    - name: backlog
    - name: todo
    - name: in-progress
next_id: 1
```

### 3d. Binary Availability

| Strategy | Pros | Cons | Score |
|----------|------|------|-------|
| `KANBAN_BIN` env var (CI sets it) | Explicit, portable | Requires CI config | .80 |
| Detect `kanban/kanban-md.exe` at workspace root | Zero config for devs | Fragile in CI | .70 |
| pytest skip marker if binary missing | Graceful degradation | Tests silently skipped | .85 |
| Both: detect + skip if missing | Best of both | Slightly more fixture code | .90 |

**Recommendation (.90):** Fixture resolves binary via `KANBAN_BIN` env var
falling back to `kanban/kanban-md.exe`. If binary is missing, skip the test
with `pytest.skip("kanban-md binary not found")`.

### 3e. Test Scope — End-to-End Scenarios

Per AC, tests must exercise create, list, show, move. Recommended scenarios:

1. **Create + list roundtrip** — create a task, list tasks, verify it appears
2. **Create + show roundtrip** — create a task, show by ID, verify fields
3. **Create + move + show** — create, move to different status, verify status
4. **Create + list with filter** — create 2 tasks with different tags, filter
5. **Error case** — show nonexistent task ID, verify error response

### 3f. Pytest Markers

Mark integration tests with `@pytest.mark.integration` so they can be run
selectively. Register in `pyproject.toml` under `[tool.pytest.ini_options]`.

### 3g. Dependencies

| Dependency | Status | Risk |
|------------|--------|------|
| `packages/mcp-kanban/` exists | Blocked (#39 at todo, #7 at ideation) | **High** — no package to test yet |
| `kanban-md.exe` binary | Available (v0.33.0) | **Low** — setup.ps1 handles download |
| `mcp` package installed | Available when workspace synced | **Low** |

**Critical:** Task #57 cannot be implemented until #39 (scaffold) ships.
The test file will live at `packages/mcp-kanban/tests/test_integration.py`.

## 4. Recommendation (.85 confidence)

Use in-memory MCP client testing with real binary and per-test temp board:

1. Pytest fixture creates temp dir with `config.yml` + `tasks/`
2. Fixture resolves binary path (env var → convention → skip)
3. Override lifespan context to point at temp dir + real binary
4. Tests use `client_session(server._mcp_server)` from MCP SDK
5. Each test calls `client.call_tool(...)` and asserts on real output
6. Mark tests with `@pytest.mark.integration`
7. 5 test scenarios: create+list, create+show, create+move+show, filtered
   list, error case

**Risk:** Blocked on #39 and #7. No implementation until package exists.

## 5. Follow-up Tasks

Task #57 itself is the follow-up — no new tasks needed. Update its AC and
dependencies based on research findings.
