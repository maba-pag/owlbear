# Build mcp-kanban Server — Research

> **Owning task:** #14 — Build mcp-kanban server
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #14 requires a full MCP server in `packages/mcp-kanban/` that wraps
`kanban-md.exe` via Python MCP SDK, exposing 5 tools + 1 resource over stdio.
Prior research covered the SDK (#2), scaffold patterns (#39), and integration
testing (#57). This research validates the full 12-item AC and maps each to
a concrete implementation approach.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK (v1.26.0) | github.com/modelcontextprotocol/python-sdk | .95 |
| 2 | OwlBear MCP SDK deep-dive | docs/research/mcp-python-sdk.md | .95 |
| 3 | OwlBear scaffold research | docs/research/scaffold-mcp-kanban.md | .90 |
| 4 | Integration test research | docs/research/mcp-kanban-integration-tests.md | .85 |
| 5 | v1 KanbanToolset | v1/src/owlbear/tools/kanban.py | .90 |
| 6 | kanban-md CLI help output | `kanban-md {cmd} --help` (v0.33.0) | .95 |
| 7 | VS Code MCP Config Reference | code.visualstudio.com/docs/copilot/reference/mcp-configuration | .90 |
| 8 | MCP Tools Spec (2025-06-18) | modelcontextprotocol.io/specification/2025-06-18/server/tools | .85 |

## 3. Analysis

### 3a. AC Feasibility Matrix

| # | AC Item | Feasible | Implementation Pattern | Risk |
|---|---------|----------|----------------------|------|
| 1 | MCP server in packages/mcp-kanban/ | Yes | FastMCP v1, package scaffold exists | None |
| 2 | kanban_list with filters | Yes | `kanban-md list --status X --tag Y --priority Z --json` | None |
| 3 | kanban_show by ID | Yes | `kanban-md show ID --json` | None |
| 4 | kanban_create | Yes | `kanban-md create TITLE --body B --status S --priority P --tags T` | None |
| 5 | kanban_edit | Yes | `kanban-md edit ID --status/--priority/--tags/--body/--claim` | None |
| 6 | kanban_move | Yes | `kanban-md move ID STATUS` or `--next`/`--prev` | None |
| 7 | board://summary resource | Yes | `kanban-md board --json`, serve as MCP resource | None |
| 8 | stdio transport | Yes | `mcp.run()` default | None |
| 9 | Binary path discovery | Yes | Env var `KANBAN_BIN` + convention fallback | None |
| 10 | Error handling | Yes | Subprocess exit code + stderr capture | None |
| 11 | .vscode/mcp.json registration | Yes | stdio config with `uv run` | None |
| 12 | SKILL.md | Yes | Documentation deliverable | None |

All 12 AC items are technically feasible with no blockers.

### 3b. Tool Parameter Mapping

Derived from `kanban-md --help` output (source 6):

**kanban_list:**

| Parameter | Type | Required | Maps to CLI flag |
|-----------|------|----------|-----------------|
| status | list[str] | No | `--status s1,s2` |
| tag | str | No | `--tag t` |
| priority | list[str] | No | `--priority p1,p2` |
| search | str | No | `--search q` |
| limit | int | No | `--limit n` |
| blocked | bool | No | `--blocked` |

**kanban_show:**

| Parameter | Type | Required | Maps to CLI flag |
|-----------|------|----------|-----------------|
| id | int | Yes | positional `ID` |

**kanban_create:**

| Parameter | Type | Required | Maps to CLI flag |
|-----------|------|----------|-----------------|
| title | str | Yes | positional `TITLE` |
| body | str | No | `--body B` |
| status | str | No | `--status S` |
| priority | str | No | `--priority P` |
| tags | str | No | `--tags T` |
| depends_on | str | No | `--depends-on 1,2` |

**kanban_edit:**

| Parameter | Type | Required | Maps to CLI flag |
|-----------|------|----------|-----------------|
| id | int | Yes | positional `ID` |
| status | str | No | `--status S` |
| priority | str | No | `--priority P` |
| tags | str | No | `--add-tag T` |
| body | str | No | `--body B` |
| append_body | str | No | `--append-body B` |
| claim | str | No | `--claim A` |
| release | bool | No | `--release` |
| block | str | No | `--block R` |
| unblock | bool | No | `--unblock` |

**kanban_move:**

| Parameter | Type | Required | Maps to CLI flag |
|-----------|------|----------|-----------------|
| id | int | Yes | positional `ID` |
| status | str | No | positional `STATUS` |
| next | bool | No | `--next` |
| prev | bool | No | `--prev` |

### 3c. Subprocess Wrapper Pattern

The v1 `KanbanToolset._run_kanban()` (source 5) establishes the pattern:

```python
async def _run_kanban(self, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        str(self.kanban_bin),
        *args,
        "--no-color",
        "--dir",
        str(self.kanban_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"kanban-md failed: {stderr.decode()}")
    return stdout.decode()
```

Key patterns to carry forward:
- Always append `--no-color` (prevents ANSI escape codes in output)
- Always append `--dir {kanban_dir}` (explicit board path)
- Append `--json` for structured output where supported
- Capture stderr for error messages
- Check return code, surface clear error text

### 3d. Error Handling Strategy

| Error | Detection | MCP Response |
|-------|-----------|-------------|
| Binary not found | Lifespan startup check | Server fails to start with clear message |
| Binary exits non-zero | `proc.returncode != 0` | Return `isError: true` with stderr text |
| Timeout | `asyncio.wait_for` | Return `isError: true` with timeout message |
| Invalid params (e.g. bad ID) | Binary returns non-zero | Forward binary error message |
| Malformed JSON output | `json.JSONDecodeError` | Return `isError: true` with parse error |

### 3e. board://summary Resource

`kanban-md board --json` returns board summary (task counts per status, WIP,
blocked counts). Expose as `board://summary` MCP resource. The MCP SDK
`@mcp.resource("board://summary")` decorator handles this. Resource returns
the JSON string directly — clients parse it.

### 3f. Testing Strategy

| Layer | Tool | What | Coverage |
|-------|------|------|----------|
| Unit | pytest + mock | Mock `asyncio.create_subprocess_exec`, verify CLI args | All tools |
| Integration | pytest + real binary | `tmp_path` board, real `kanban-md.exe` | Create/list/show/move roundtrip |
| MCP layer | `create_connected_server_and_client_session` | In-memory MCP client/server, verify tool schemas | All tools |

Unit tests use `unittest.mock.AsyncMock` patching `asyncio.create_subprocess_exec`.
Integration tests per `docs/research/mcp-kanban-integration-tests.md`.

### 3g. Package Dependencies

```toml
[project]
dependencies = ["mcp[cli]>=1.26"]
```

Minimal: only the MCP SDK. No other deps needed — subprocess is stdlib.

## 4. Recommendation (.90 confidence)

Implement `packages/mcp-kanban/` using:
- **FastMCP v1** with stdio transport and lifespan pattern
- **5 tools** (list, show, create, edit, move) mapping directly to kanban-md
  CLI subcommands with `--json --no-color --dir` flags
- **1 resource** (`board://summary`) via `kanban-md board --json`
- **Subprocess wrapper** following v1 `_run_kanban()` pattern with
  async subprocess, stderr capture, and return code checking
- **Binary discovery** via `KANBAN_BIN` env var fallback to
  `kanban/kanban-md.exe` convention, validated at lifespan startup
- **Error handling** returning `isError: true` with descriptive messages
- **Unit tests** with mocked subprocess + in-memory MCP client tests

Risk: Low. All patterns are proven in prior art (v1 codebase, SDK examples).
The kanban-md CLI is stable at v0.33.0 with well-documented `--json` output.

## 5. Follow-up Tasks

Task #14 itself is the primary implementation task — no new tasks needed.
The AC is comprehensive and implementable as-is. Prior duplicate tasks
#39, #40, #41 were flagged for deletion in #2's architecture review.
