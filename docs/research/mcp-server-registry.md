# MCP Server Registry Configuration

> **Owning task:** #18 — Configure MCP server registry
> **Date:** 2026-03-29 (refreshed 2026-03-29) **Status:** Complete

## 1. Context and Question

Task #18 asks: what should the `.vscode/mcp.json` template contain? The setup script
(`scripts/setup.py`) generates an `mcp.json` via `create_mcp_config()`. This research
validates the current config against the VS Code MCP spec, evaluates community servers,
and confirms the template is correctly implemented.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code MCP Config Reference | https://code.visualstudio.com/docs/copilot/reference/mcp-configuration | 1.0 |
| S2 | VS Code MCP Server Guide | https://code.visualstudio.com/docs/copilot/chat/mcp-servers | 0.9 |
| S3 | GitHub MCP Server | https://github.com/github/github-mcp-server | 0.9 |
| S4 | Playwright MCP Server | https://github.com/microsoft/playwright-mcp | 0.8 |
| S5 | OwlBear setup.py | scripts/setup.py (local) | 1.0 |
| S6 | OwlBear mcp-kanban server | packages/mcp-kanban/src/ (local) | 1.0 |

## 3. Analysis

### 3.1 Current Template (Verified Correct)

`setup.py` generates 4 servers with correct module names (`owlbear_mcp_kanban`,
`owlbear_mcp_knowledge`, `owlbear_mcp_project`) and the GitHub remote server first.
Module names match installed package names (S5, S6). Tests in `test_setup_script.py`
verify: 4 servers, correct module names, camelCase keys, relative paths, idempotent
skip. All passing.

### 3.2 Missing `__main__.py` Entry Points

Only `mcp-kanban` has `__main__.py`. `mcp-knowledge` and `mcp-project` lack this file,
so `-m owlbear_mcp_knowledge` / `-m owlbear_mcp_project` will fail until their servers
are built. Tracked by tasks #16 (mcp-knowledge) and #17 (mcp-project). Task #133
covers the `mcp[cli]` dependency for both packages. VS Code shows clear error
indicators for unavailable servers (S2).

### 3.3 Community Servers

| Server | Config Type | Deps | KISS | Recommendation |
|--------|-------------|------|------|----------------|
| **GitHub MCP** (S3) | `http` remote, zero local deps | None (OAuth via Copilot) | High | **Included** ✅ |
| **Playwright MCP** (S4) | `stdio`, requires Node.js + npx | Node.js runtime | Medium | **Excluded** (YAGNI) |

GitHub MCP: already in template. Zero deps, OAuth via Copilot (S2, S3).
Playwright: YAGNI for Python-only stack. Installable via VS Code gallery (S2).

### 3.4 Config Format Validation (S1, S2 — updated 2026-03-25)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `"servers"` top-level key | ✅ | S1 schema |
| `"type": "stdio"` + `"command"` + `"args"` | ✅ | S1 stdio spec |
| `"type": "http"` + `"url"` for remote | ✅ | S1 http spec |
| camelCase server names | ✅ | S1 naming conventions |
| Module names match packages | ✅ | S5, S6 verified |
| `env` entries (optional) | N/A | KANBAN_BIN override is optional (S6) |

VS Code also supports `envFile`, `sandboxEnabled` (macOS/Linux only), `dev` mode,
and `inputs` for secrets (S1). None needed for OwlBear's current use case.

### 3.5 Final Template Structure (.90 confidence)

```json
{
  "servers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "owlbearKanban": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "{rel}", "-m", "owlbear_mcp_kanban"]
    },
    "owlbearKnowledge": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "{rel}", "-m", "owlbear_mcp_knowledge"]
    },
    "owlbearProject": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "{rel}", "-m", "owlbear_mcp_project"]
    }
  }
}
```

### 3.6 Project-Specific Servers

`setup.py` is idempotent (skips if `mcp.json` exists). Users add project-specific
servers by editing `.vscode/mcp.json` directly. VS Code provides IntelliSense (S1).
Setup output already notes this: "Edit .vscode/mcp.json to add project-specific MCP
servers."

## 4. Recommendation (.90 confidence)

The template is **fully implemented and tested**. All original recommendations
(module names, GitHub MCP, Playwright exclusion, test coverage) are resolved.

Remaining dependency: tasks #16, #17 must build mcp-knowledge and mcp-project servers
(including `__main__.py` entry points) before those MCP entries function. Task #133
adds `mcp[cli]` dependency. These are tracked — no new tasks required from this research.

## 5. Follow-up Tasks

No new tasks needed. All gaps are tracked by existing tasks:

- **#16** — Build mcp-knowledge server (includes `__main__.py`)
- **#17** — Build mcp-project server (includes `__main__.py`)
- **#133** — Add `mcp[cli]` dependency to mcp-knowledge and mcp-project
