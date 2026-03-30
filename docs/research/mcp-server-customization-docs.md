# Documenting How to Add Project-Specific MCP Servers

> **Owning task:** #124 — Document how to add project-specific MCP servers
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #18 (mcp-server-registry research, §3.6) identified that users need guidance on
adding their own MCP servers to the generated `.vscode/mcp.json`. The setup script
already skips mcp.json if it exists (idempotent), so users edit the file directly.
This research validates the documentation approach and identifies where content should go.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code MCP Config Reference | https://code.visualstudio.com/docs/copilot/reference/mcp-configuration | 1.0 |
| S2 | VS Code MCP Server Guide | https://code.visualstudio.com/docs/copilot/chat/mcp-servers | 0.9 |
| S3 | MCP Protocol docs | https://modelcontextprotocol.io/quickstart/user | 0.7 |
| S4 | OwlBear setup.py | scripts/setup.py (local) | 1.0 |
| S5 | OwlBear README.md | README.md (local) | 1.0 |
| S6 | mcp-server-registry research | docs/research/mcp-server-registry.md (local) | 0.9 |

## 3. Analysis

### 3.1 Where should the docs go?

| Location | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **README.md** section | Visible to all users; version-controlled; standard location | README already 108 lines; risks bloat | **Yes (.85)** — add concise section |
| **setup.py print output** | Shown at setup time; immediate visibility | Ephemeral (not re-readable); limited space | **Yes (.90)** — one-line hint |
| **copilot-instructions.md** | Agent-visible; auto-loaded | For agent behavior, not user docs | **No (.70)** — wrong audience |
| **Separate docs/guide** | Detailed; extensible | Over-engineering for 3 examples | **No (.60)** — YAGNI |

### 3.2 What content is needed?

Per VS Code MCP Config Reference (S1), the essential concepts for users are:

1. **Adding a server entry** — add a key under `"servers"` in `.vscode/mcp.json`
2. **Server types** — `stdio` (local command) vs `http`/`sse` (remote URL) (S1)
3. **Environment variables** — `env` object for secrets, `envFile` for `.env` files (S1)
4. **Input variables** — `${input:var-id}` with `"inputs"` array for prompted secrets (S1)
5. **Naming** — camelCase, unique, descriptive (S1)
6. **IntelliSense** — VS Code provides autocomplete in mcp.json (S1, S2)

### 3.3 Setup.py output change

Current output (S4, line 130-134):
```
OwlBear workspace setup complete for '{name}'.
Next steps:
  1. Open the project in VS Code.
  2. Run `kanban/setup.ps1` to download kanban-md.
  3. Start orchestrating with the OwlBear agents.
```

Recommended addition:
```
  4. To add your own MCP servers, edit .vscode/mcp.json — see README for examples.
```

### 3.4 README section content

A concise section (~30 lines) with three annotated examples covering the AC:
- stdio server (Python tool), http server (remote API), env vars for secrets
- Link to VS Code MCP Config Reference for full schema
- Note about IntelliSense support

## 4. Recommendation (.85 confidence)

**Two changes, both minimal and KISS-aligned:**

1. **README.md**: Add "Adding MCP Servers" section after "New Project Setup" with
   3 commented JSON examples (stdio, http, env/input variables). Link to VS Code
   MCP Config Reference (S1). ~30 lines.

2. **setup.py**: Add one print line pointing users to the README and mcp.json.

Risk: Low. Both are additive documentation changes. No code behavior changes.

The copilot-instructions.md is the wrong location — it's for agent behavior
rules, not user-facing how-to documentation (S5 confirms README is the user guide).

## 5. Follow-up Tasks

Tasks created at `ideation` for architect gate:

```
kanban\kanban-md.exe create "Add MCP server customization section to README" --priority important --status ideation --tags phase-1,scope:mcp,type:docs --body "## Objective\nAdd a section to README.md documenting how to add project-specific MCP servers.\n\n## Acceptance Criteria\n- [ ] Section titled 'Adding MCP Servers' after 'New Project Setup'\n- [ ] Example: stdio server (Python tool with uv)\n- [ ] Example: http server (remote API)\n- [ ] Example: env vars and input variables for secrets\n- [ ] Links to VS Code MCP Config Reference\n- [ ] Mentions IntelliSense support in mcp.json\n- [ ] Section is ≤30 lines\n\n## Context\nSee docs/research/mcp-server-customization-docs.md"
```

```
kanban\kanban-md.exe create "Add mcp.json customization hint to setup.py output" --priority important --status ideation --tags phase-1,scope:mcp,type:docs --body "## Objective\nAdd a print line to setup.py output hinting users can customize .vscode/mcp.json.\n\n## Acceptance Criteria\n- [ ] setup() print output includes line about customizing mcp.json\n- [ ] Line references README for examples\n- [ ] Existing test assertions updated if needed\n\n## Context\nSee docs/research/mcp-server-customization-docs.md"
```
