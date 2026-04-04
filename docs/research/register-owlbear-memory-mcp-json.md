# Register owlbear-memory Server in .vscode/mcp.json

> **Owning task:** #571 — Register owlbear-memory server in .vscode/mcp.json
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #571 requires: (1) adding `owlbear-memory` MCP server to `.vscode/mcp.json`, (2) fixing `setup.py` server key naming from camelCase to kebab-case, and (3) verifying agent tool patterns resolve correctly. Parent research (`docs/research/add-owlbear-memory-tool-access.md`) identified both gaps during #568 investigation.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | VS Code custom agents docs | code.visualstudio.com/docs/copilot/customization/custom-agents | 1.0 |
| S2 | .vscode/mcp.json (workspace) | `.vscode/mcp.json` (terminal read — Copilot-ignored) | 1.0 |
| S3 | Agent tool patterns | `agents/*.agent.md` tools: arrays (grep) | 1.0 |
| S4 | setup.py MCP config | `scripts/setup.py` L50–82 | .95 |
| S5 | test_setup_script.py | `tests/test_setup_script.py` L417–445 | .90 |
| S6 | test_scaffold_mcp_memory_524.py | `tests/test_scaffold_mcp_memory_524.py` L710–790 | .90 |
| S7 | FastMCP server names | `packages/mcp-*/src/*/server.py` FastMCP() calls | .85 |
| S8 | Parent research | `docs/research/add-owlbear-memory-tool-access.md` §3 | 1.0 |

## 3. Analysis

### 3A. Missing server registrations (S2)

Current `.vscode/mcp.json` registers 3 servers: `microsoft/markitdown`, `owlbear-kanban`, `owlbear_knowledge`. Missing: `owlbear-memory` and `owlbear-project`.

| Server | FastMCP name (S7) | mcp.json key | Agent pattern | Status |
|--------|-------------------|-------------|---------------|--------|
| kanban | owlbear-kanban | owlbear-kanban | owlbear-kanban/* | Registered |
| knowledge | owlbear_knowledge | owlbear_knowledge | owlbear_knowledge/* | Registered |
| memory | owlbear-memory | (missing) | owlbear-memory/* (#568) | **MISSING** |
| project | owlbear-project | (missing) | (none yet) | **MISSING** |

The `owlbear-memory` entry should follow the existing pattern:
```json
"owlbear-memory": {
  "type": "stdio",
  "command": "uv",
  "args": ["run", "python", "-m", "owlbear_mcp_memory"]
}
```

### 3B. Server key naming mismatch (S1, S3, S4)

VS Code docs (S1) state: tool patterns use `<server name>/*` where server name = mcp.json key. Agent tool patterns use kebab-case (`'owlbear-kanban/*'`). The workspace mcp.json keys are kebab-case. But `setup.py` generates camelCase keys for consumer projects:

| Convention | setup.py (S4) | workspace mcp.json (S2) | Agent patterns (S3) |
|-----------|--------------|------------------------|-------------------|
| kanban | owlbearKanban | owlbear-kanban | owlbear-kanban/* |
| knowledge | owlbearKnowledge | owlbear_knowledge | owlbear_knowledge/* |
| memory | owlbearMemory | (missing) | owlbear-memory/* |
| project | owlbearProject | (missing) | (none) |

**Consumer projects bootstrapped by `setup.py` have broken tool routing** — the camelCase keys don't match the kebab-case agent patterns.

### 3C. Test impact (S5, S6)

Two test files explicitly assert camelCase keys:
- `test_setup_script.py` `TestFromAC_McpServerNames` — asserts `owlbearKanban`, `owlbearKnowledge`, etc.
- `test_scaffold_mcp_memory_524.py` `TestFromAC_SetupMcp` — asserts `owlbearMemory` key

These tests enforce the wrong convention. The builder must update them to kebab-case.

### 3D. Duplicate task (S8)

Task #570 has identical title and body to #571 — created seconds apart during the same dispatch cycle. One should be archived.

## 4. Recommendation (.95 confidence)

**T1 (autonomous)** — config naming fix + server registration. No new capability, no architecture change.

Three changes needed:
1. Add `owlbear-memory` entry to `.vscode/mcp.json` (note: Copilot-ignored file, must edit via terminal)
2. Change `setup.py` server keys from camelCase to kebab-case (4 keys: `owlbearKanban` → `owlbear-kanban`, etc.)
3. Update test assertions in `test_setup_script.py` and `test_scaffold_mcp_memory_524.py`

Challenge: SKIP — trivial config validation, parent research already challenged (#568).

## 5. Follow-up Tasks

Task #571 itself is the implementation task — AC is already well-defined.

Additional follow-up: `owlbear-project` also missing from `.vscode/mcp.json`, separate from #571 scope.
