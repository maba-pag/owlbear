# Register owlbear-memory Server in .vscode/mcp.json

> **Owning task:** #570 — Register owlbear-memory server in .vscode/mcp.json
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #570 (follow-up from #568 research) requires adding owlbear-memory to the workspace `.vscode/mcp.json` and fixing setup.py naming from camelCase to kebab-case. Without the mcp.json entry, agent tool patterns `'owlbear-memory/*'` (to be added by #568) are inert. The setup.py naming mismatch means consumer projects would have broken tool routing.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | VS Code MCP config reference | https://code.visualstudio.com/docs/copilot/reference/mcp-configuration | .95 |
| S2 | Workspace .vscode/mcp.json | `.vscode/mcp.json` (3 servers: markitdown, owlbear-kanban, owlbear_knowledge) | 1.0 |
| S3 | scripts/setup.py L62-90 | `scripts/setup.py` — `create_mcp_config()` | 1.0 |
| S4 | tests/test_setup_script.py L415-465 | `tests/test_setup_script.py` — `TestFromAC_McpServerNames` | .95 |
| S5 | All 14 agent frontmatters | `agents/*.agent.md` tools: arrays | 1.0 |
| S6 | FastMCP server names | `packages/mcp-*/src/**/server.py` — all use kebab-case | .90 |
| S7 | Prior research (#568) | `docs/research/add-owlbear-memory-tool-access.md` | 1.0 |

## 3. Analysis

### Naming convention conflict (S1, S2, S3, S5)

| Artifact | Convention | Examples |
|----------|-----------|----------|
| VS Code docs (S1) | camelCase recommended | "uiTesting", "githubIntegration" |
| Workspace mcp.json (S2) | kebab-case | `owlbear-kanban`, `owlbear_knowledge` |
| setup.py output (S3) | camelCase | `owlbearKanban`, `owlbearKnowledge` |
| Agent tool patterns (S5) | kebab-case | `'owlbear-kanban/*'` |
| FastMCP names (S6) | kebab-case | `"owlbear-kanban"`, `"owlbear-memory"` |
| Existing tests (S4) | enforce camelCase | `{"owlbearKanban", "owlbearKnowledge", ...}` |

**Tool routing requires server key = tool pattern prefix.** Agent tool pattern `'owlbear-kanban/*'` routes to mcp.json key `owlbear-kanban`. If setup.py generates `owlbearKanban`, consumer projects break — tool patterns don't match server keys. Workspace works because its mcp.json already uses kebab-case.

VS Code's camelCase recommendation is guidance, not enforcement. Hyphens in keys work.

### Missing servers in workspace mcp.json (S2)

| Server | In mcp.json? | In setup.py? | Agent patterns exist? |
|--------|:---:|:---:|:---:|
| microsoft/markitdown | Yes | No | N/A |
| owlbear-kanban | Yes | Yes | Yes (11 agents) |
| owlbear_knowledge | Yes | Yes | No |
| owlbear-memory | **No** | Yes | No (pending #568) |
| owlbear-project | **No** | Yes | No |
| github (remote) | No | Yes | N/A |

owlbear-memory and owlbear-project are both missing from the workspace mcp.json. Only owlbear-memory is in #570's AC scope. owlbear-project has no agent tool patterns yet, so it's lower priority.

### Test impact (S4)

`TestFromAC_McpServerNames` (6 tests) asserts camelCase keys. Changing setup.py to kebab-case requires updating these tests. Scope: ~15 lines across 6 test methods.

### Duplicate task

#571 is an exact duplicate of #570 (same title, body, AC). Created simultaneously by the same research step. One should be archived.

## 4. Recommendation (.90 confidence)

**T1 (autonomous)** — config fix + bug fix, no new capability or architecture change.

**Approach for #570:**
1. Add `owlbear-memory` entry to `.vscode/mcp.json` following the existing pattern (stdio, `uv run python -m owlbear_mcp_memory`)
2. Change setup.py server keys from camelCase to kebab-case (`owlbear-kanban`, `owlbear_knowledge`, `owlbear-memory`, `owlbear-project`)
3. Update `tests/test_setup_script.py` to expect kebab-case keys
4. Verify existing agent tool patterns still match

Challenge: SKIP — trivial config research extending prior research (#568).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Register owlbear-project server in workspace mcp.json" --priority nice-to-have --status ideation --tags "scope:config,phase-2" --body "owlbear-project is missing from .vscode/mcp.json (same gap as owlbear-memory fixed by #570). No agent tool patterns use owlbear-project/* yet, so this is lower priority. Add when agents need project MCP tools.\n\nAC:\n- [ ] .vscode/mcp.json includes owlbear-project entry\n- [ ] Entry format matches existing servers"
```
