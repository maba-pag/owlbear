# Scaffold mcp-kanban MCP Server — Research

**Task:** #39 · **Status:** ideation → backlog · **Date:** 2026-03-27

## 1. Scope

Design a `packages/mcp-kanban/` MCP server package that wraps the `kanban-md`
CLI binary via FastMCP v1, exposing kanban board operations as MCP tools over
stdio transport. VS Code discovers it via `.vscode/mcp.json`.

## 2. Sources

| # | Source | URL | Key takeaway |
|---|--------|-----|--------------|
| 1 | MCP Python SDK README | <https://github.com/modelcontextprotocol/python-sdk> | FastMCP v1 `@mcp.tool()`, lifespan pattern, `mcp.run()` entry point |
| 2 | VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | stdio server registration in `.vscode/mcp.json` |
| 3 | OwlBear KanbanToolset (v1) | `v1/src/owlbear/tools/kanban.py` | `_run_kanban()` helper, `asyncio.create_subprocess_exec`, 7 tool signatures |
| 4 | Scaffold mcp-knowledge (#40) | `docs/research/scaffold-mcp-knowledge.md` | Sister package blueprint: layout, lifespan, testing strategy |
| 5 | Monorepo tooling (#6) | `docs/research/monorepo-tooling.md` | uv workspace config, `uv_build` backend, `project.scripts` entry points |
| 6 | MCP SDK deep-dive (#2) | `docs/research/mcp-python-sdk.md` | Transport trade-offs, server lifecycle, context injection |

## 3. Analysis

### 3a. Tool surface comparison

| Approach | Tools | Complexity | KISS score |
|----------|-------|------------|------------|
| Minimal (AC only) | 1 (`list_tasks`) | Low | .95 |
| Mirror v1 KanbanToolset | 7 (list, show, create, move, edit, pick, context) | Medium | .80 |
| Full + resources/prompts | 7+ tools + board resource | High | .55 |

**Recommendation (.85):** Start with minimal (1 tool) per AC, design for the
full set. The v1 KanbanToolset tool signatures are proven and can be ported
incrementally. Follow-up tasks handle expansion.

### 3b. Binary path resolution

| Strategy | Pros | Cons | Score |
|----------|------|------|-------|
| Env var only (`KANBAN_BIN`) | Explicit, CI-friendly | Extra setup for users | .70 |
| Convention (`kanban/kanban-md.exe`) | Zero config for OwlBear devs | Fragile outside workspace | .75 |
| Both (env overrides convention) | Best of both, fallback chain | Slightly more code | .90 |

**Recommendation (.90):** Lifespan checks `KANBAN_BIN` env var first, falls
back to `kanban/kanban-md.exe` relative to workspace root. Validates binary
exists at startup; raises clear error if missing.

### 3c. Package layout

```
packages/mcp-kanban/
├── pyproject.toml          # uv_build backend, mcp dep
├── src/
│   └── mcp_kanban/
│       ├── __init__.py
│       ├── __main__.py     # python -m mcp_kanban
│       └── server.py       # FastMCP app + lifespan + tools
└── tests/
    └── test_server.py
```

Aligns with sister task (#40) layout and uv workspace conventions from #6.

### 3d. Lifespan pattern

```python
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    bin_path = Path(os.environ.get("KANBAN_BIN", "kanban/kanban-md.exe"))
    if not bin_path.exists():
        raise FileNotFoundError(f"kanban-md not found at {bin_path}")
    yield AppContext(kanban_bin=bin_path)
```

### 3e. VS Code registration

```json
{
  "servers": {
    "mcp-kanban": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--package", "mcp-kanban", "mcp-kanban"]
    }
  }
}
```

### 3f. Prerequisites

| Dependency | Status | Risk |
|------------|--------|------|
| `packages/` directory | Does NOT exist | Blocked on monorepo skeleton (#7) |
| Root `pyproject.toml` with workspace config | Does NOT exist | Blocked on #7 |
| `.vscode/mcp.json` | Exists (empty `{"servers": {}}`) | Ready |
| `kanban/kanban-md.exe` | Exists (v0.33.0) | Ready |

**Risk mitigation:** Task #39 can scaffold files before #7 merges — just can't
`uv sync` until workspace root exists. Alternatively, sequence #7 first.

## 4. Recommendation (.85 confidence)

Scaffold `packages/mcp-kanban/` with:
- FastMCP v1 + stdio transport
- Single `list_tasks` tool calling `kanban-md.exe list --no-color`
- Lifespan for binary path resolution (env var + convention fallback)
- `__main__.py` entry point for `python -m mcp_kanban`
- Register in `.vscode/mcp.json`
- Unit tests with mock subprocess

Expansion to full 7-tool set is a separate follow-up task. This keeps the
scaffold focused and KISS-aligned.

**Dependency:** Requires monorepo skeleton (#7) for `uv sync` to work. Can
scaffold files independently but integration testing needs #7 complete.

## 5. Follow-up Tasks

See kanban commands below — all created at `ideation` for architect review.

```
kanban\kanban-md.exe create "Expand mcp-kanban to full kanban-md tool set" --priority important --status ideation --tag phase-3,mcp,tooling --body "Port remaining 6 tools from v1 KanbanToolset (show, create, move, edit, pick, context) to mcp-kanban MCP server.\n\n## Acceptance Criteria\n- All 7 kanban-md commands exposed as MCP tools\n- Tool signatures match v1 KanbanToolset patterns\n- Each tool has unit test with mock subprocess\n- Error handling for binary failures\n\n## References\n- v1/src/owlbear/tools/kanban.py (prior art)\n- docs/research/scaffold-mcp-kanban.md" -t
```

```
kanban\kanban-md.exe create "Add mcp-kanban integration tests with real kanban-md binary" --priority nice-to-have --status ideation --tag phase-3,mcp,test --body "Integration tests that exercise mcp-kanban against real kanban-md binary with temp board directory.\n\n## Acceptance Criteria\n- Integration test suite using real kanban-md.exe\n- Temp directory with test board config\n- Tests create, list, show, move tasks end-to-end\n- CI-compatible (binary downloaded via setup.ps1)\n\n## References\n- docs/research/scaffold-mcp-kanban.md\n- kanban/setup.ps1 (binary download)" -t
```
