# mcp-kanban Unit Test Strategy

> **Owning task:** #89 — Test: mcp-kanban full tool set
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #89 specifies ~17 failing test scenarios for the mcp-kanban MCP server
(#56): lifespan, `_run_kanban` helper, 7 tool success paths, and error paths.
This research validates the testing approach, identifies the correct mock
targets for FastMCP module-level functions, and confirms test file placement.

## 2. Sources Studied

| # | Source | URL | Key Takeaway | Relevance |
|---|--------|-----|--------------|-----------|
| 1 | v1 KanbanToolset tests | `v1/tests/test_kanban_tools.py` | Mock `asyncio.create_subprocess_exec`, verify CLI args tuple, error string pattern | .95 |
| 2 | mcp-knowledge unit tests | `packages/mcp-knowledge/tests/test_search_knowledge.py` | Sister MCP package test pattern: mock context, test tool function directly | .90 |
| 3 | MCP Python SDK README (v1) | <https://github.com/modelcontextprotocol/python-sdk> | `@mcp.tool()` injects `Context[ServerSession, AppContext]`; lifespan yields typed context | .85 |
| 4 | mcp-kanban integration test research | `docs/research/mcp-kanban-integration-tests.md` | In-memory `client_session()` for integration; confirms subprocess mock for unit level | .80 |
| 5 | Scaffold mcp-kanban research | `docs/research/scaffold-mcp-kanban.md` | Package layout: `packages/mcp-kanban/tests/test_server.py`; lifespan binary resolution | .85 |
| 6 | Expand mcp-kanban research | `docs/research/expand-mcp-kanban-tools.md` | Agent-essential params beyond v1; error text (not exceptions) on non-zero rc | .90 |

## 3. Analysis

### 3a. Unit vs Integration Testing Pattern

| Approach | What it tests | Mock target | KISS | Score |
|----------|---------------|-------------|------|-------|
| A. Direct function call + mock subprocess | Tool logic, arg construction | `asyncio.create_subprocess_exec` | High | .90 |
| B. In-memory MCP client session | Full MCP stack including serialization | Subprocess only | Medium | .75 |
| C. Stdio subprocess (launch server) | Full transport | Nothing | Low | .40 |

**Pattern A** is correct for #89 (unit tests). Source 1 uses this pattern for
v1 with 900+ lines of proven tests. Source 2 confirms direct function calls
work for MCP tools. Pattern B suits integration tests (#57).

### 3b. v1 vs MCP Tool Testing — Key Differences

| Aspect | v1 KanbanToolset | MCP @mcp.tool() |
|--------|-----------------|-----------------|
| Unit under test | Instance method (`ts.kanban_list()`) | Module function (`list_tasks(ctx=...)`) |
| Subprocess mock path | `owlbear.tools.kanban.asyncio.create_subprocess_exec` | `owlbear_mcp_kanban.server.asyncio.create_subprocess_exec` |
| Binary/dir access | `self._kanban_bin`, `self._kanban_dir` | `ctx.request_context.lifespan_context` |
| Context setup | Constructor: `KanbanToolset(kanban_dir=..., kanban_bin=...)` | `MagicMock(request_context=MagicMock(...))` or inject `AppContext` |

### 3c. Lifespan Testing

The `app_lifespan` async context manager (Source 5, §3d) needs three tests:

| Scenario | Mock | Assertion |
|----------|------|-----------|
| Yields AppContext | Mock `Path.exists()` → True | `ctx.kanban_bin` and `ctx.kanban_dir` are Paths |
| Binary missing | Mock `Path.exists()` → False, no env var | `FileNotFoundError` raised |
| Env var override | `os.environ["KANBAN_BIN"] = "/custom/path"` | `ctx.kanban_bin == Path("/custom/path")` |

### 3d. Tool Parameter Coverage

The task body specifies one test per tool (success) plus parametrized error.
Comparing to v1 tests (Source 1), this is minimal but sufficient for TDD RED:

| Tool | v1 test count | #89 test count | Delta notes |
|------|---------------|----------------|-------------|
| list_tasks | 11 | 1 + error | Reduced: #89 covers expanded params (search, sort, unclaimed) in single test |
| show_task | 2 | 1 + error | Adequate |
| create_task | 6 | 1 + error | Adequate: includes new `claim` param |
| move_task | 2 | 1 + error | Adequate |
| edit_task | 8 | 1 + error | Reduced: single test covers all 10 flags |
| pick_task | 5 | 1 + error | Reduced: includes new `tags` param |
| board_context | 1 | 1 + error | Adequate |

This is intentionally lean for TDD RED. The builder may add finer-grained
tests. The reviewer verifies coverage.

### 3e. Test File Location

| Option | Path | Precedent | Score |
|--------|------|-----------|-------|
| Package tests dir | `packages/mcp-kanban/tests/test_server.py` | Source 2, Source 5 | .85 |
| Root tests dir | `tests/test_mcp_kanban_server.py` | `tests/test_process_supervisor.py` | .70 |

Package-local is recommended (Source 5, §3c). The mcp-knowledge sister package
uses this pattern already (Source 2).

### 3f. Import Strategy (TDD RED)

Tests import from `owlbear_mcp_kanban.server` — which doesn't exist yet. All
tests will fail at import, confirming RED phase.  Standard pattern from Source 2:

```python
from owlbear_mcp_kanban.server import (
    app_lifespan, _run_kanban, list_tasks, ...
)
```

## 4. Recommendation (.90 confidence)

The 17-scenario test plan in #89's body is validated:

1. **Pattern:** Direct function calls with `asyncio.create_subprocess_exec` mocked
2. **File:** `packages/mcp-kanban/tests/test_server.py`
3. **Lifespan:** 3 tests (happy path, missing binary, env var override)
4. **Helper:** 2 tests (`_run_kanban` arg construction + return tuple)
5. **Tools:** 7 success + 1 parametrized error (7 subtests) = ~14 scenarios
6. **Total:** ~17 scenarios (matches task body)
7. **Risk:** None identified. Pattern is proven across v1 and mcp-knowledge.

## 5. Follow-up Tasks

No new tasks needed. Task #89 (at `ideation`) is the actionable follow-up.
Research validates its test plan and moves it to `backlog` for the test-writer.
