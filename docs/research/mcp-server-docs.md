# Documenting Project-Specific MCP Server Configuration

> **Owning task:** #122 — Document adding project-specific MCP servers
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #122 (from parent #18, AC item 9) asks: how should we document the process
of adding project-specific MCP servers to the generated `.vscode/mcp.json`? What
content should the documentation cover, where should it live, and what format?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code MCP Config Reference | https://code.visualstudio.com/docs/copilot/reference/mcp-configuration | 1.0 |
| S2 | VS Code MCP Server Guide | https://code.visualstudio.com/docs/copilot/chat/mcp-servers | 0.9 |
| S3 | MCP Spec — Transports | https://modelcontextprotocol.io/docs/concepts/transports | 0.8 |
| S4 | OwlBear setup.py | scripts/setup.py (local) | 1.0 |
| S5 | OwlBear README.md | README.md (local) | 1.0 |
| S6 | OwlBear MCP registry research | docs/research/mcp-server-registry.md (local) | 0.9 |

## 3. Analysis

### 3.1 Where to put the documentation

| Location | Pros | Cons | Verdict |
|----------|------|------|---------|
| README.md | User-facing, already has "New Project Setup" section | Grows the README | **Include** — natural home |
| copilot-instructions.md | Read by agents automatically | Not user-facing; agents don't add MCP servers | Skip |
| Separate `docs/` file | Keeps README lean | Users won't find it | Skip |

**Recommendation (.90 confidence):** Add a subsection under "New Project Setup"
in README.md. Users already read that section when bootstrapping a project (S5).

### 3.2 What content to cover (S1, S2, S3)

The AC requires coverage of: (a) adding a new server entry, (b) stdio vs http types,
(c) env vars for secrets, (d) reference to VS Code docs.

Key facts from sources:

- **stdio servers** (S1, S3): `"type": "stdio"`, `"command"`, `"args"`. Command must
  be on PATH or use full path. Most common for locally-run servers.
- **http servers** (S1, S2): `"type": "http"`, `"url"`. VS Code tries HTTP Stream
  transport first, falls back to SSE (S1).
- **Environment variables** (S1): `"env"` object on server config for non-secret vars.
  `"envFile"` for loading from `.env` files.
- **Secret handling** (S1): Use `${input:variable-id}` references with an `"inputs"`
  array. VS Code prompts once and stores securely. Never hardcode API keys.
- **Naming convention** (S1): camelCase server names, no spaces or special chars.
- **IntelliSense** (S1): VS Code provides schema autocomplete for mcp.json.

### 3.3 setup.py output change (S4)

Current setup.py prints 3 "Next steps" lines. AC requires a note about customizing
mcp.json. A 4th line like `"  4. Edit .vscode/mcp.json to add project-specific MCP
servers."` fits naturally. This also requires updating the test assertion in
`test_setup_script.py`.

### 3.4 Duplicate task #124

Task #124 has identical title, AC, and context to #122. It was created in the same
batch (both at 06:33 on 2026-03-29). One should be closed as duplicate.

## 4. Recommendation (.90 confidence)

1. **Add README section** (~20 lines) under "New Project Setup → Next Steps" with:
   - A stdio server example (Python command, common pattern)
   - An http server example (remote URL)
   - An env vars + input variables example for secrets
   - Link to VS Code MCP configuration reference
2. **Add setup.py output line** about customizing mcp.json
3. **Update test** for the new print output
4. **Close #124 as duplicate** of #122

Risks: None. Pure documentation task with clear prior art.

## 5. Follow-up Tasks

Task #122 itself is the implementation task — it should proceed through the
pipeline (backlog → architect → builder). No additional tasks needed.

Task #124 should be closed as duplicate.
