# Canonical Tool Registry Validation for validate_agents.py

> **Owning task:** #198 — Expand validate_agents.py to check all tool names against canonical registry
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The current `validate_agents.py` checks only 2 specific tool name regressions (bare `todo` and `resolveMemoryFileUri`). Task #198 asks: how should we expand it to validate ALL tool names in agent `tools:` lists against the canonical VS Code built-in tool registry?

Key sub-questions: (a) what is the complete canonical tool list? (b) how should MCP server references be handled? (c) what implementation approach fits KISS/YAGNI?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Cheat Sheet (2026-03-25) | https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .95 — canonical built-in tool list |
| VS Code Agent Tools docs | https://code.visualstudio.com/docs/copilot/agents/agent-tools | .90 — tool sets, MCP tool format, tool type taxonomy |
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — tools: field spec, `<server>/*` format |
| Prior research: stale-tool-names.md | docs/research/stale-tool-names.md (#193) | .85 — confirmed-active tools missing from cheat sheet |

## 3. Analysis

### 3a. Canonical Built-in Registry

**Tool sets** (valid as set names; members are also individually valid):

| Set | Members |
|-----|---------|
| `agent` | `agent/runSubagent` |
| `browser` | (experimental, undocumented members) |
| `edit` | `edit/createDirectory`, `edit/createFile`, `edit/editFiles`, `edit/editNotebook` |
| `execute` | `execute/createAndRunTask`, `execute/getTerminalOutput`, `execute/runInTerminal`, `execute/runNotebookCell`, `execute/testFailure` |
| `read` | `read/getNotebookSummary`, `read/problems`, `read/readFile`, `read/readNotebookCellOutput`, `read/terminalLastCommand`, `read/terminalSelection` |
| `search` | `search/changes`, `search/codebase`, `search/fileSearch`, `search/listDirectory`, `search/textSearch`, `search/usages` |
| `web` | `web/fetch` |

**Standalone:** `newWorkspace`, `selection`, `todos`, `vscode/askQuestions`, `vscode/extensions`, `vscode/getProjectSetupInfo`, `vscode/installExtension`, `vscode/runCommand`, `vscode/VSCodeAPI`

**Confirmed active but absent from cheat sheet** (observed in OwlBear sessions, verified per stale-tool-names.md): `execute/awaitTerminal`, `execute/killTerminal`, `execute/runTests`, `read/viewImage`, `edit/rename`, `vscode/memory`

Total: 7 tool sets + 37 individual tools (31 documented + 6 confirmed-active).

### 3b. MCP Server Pattern

Per Custom Agents docs: "To include all tools of an MCP server, use the `<server name>/*` format." Our agents use `'owlbear-kanban/*'` and `'microsoft/markitdown/*'`. Validator should allow any `*/\*` pattern.

### 3c. Implementation Approach

| Approach | KISS | Deps | Maintenance | Recommendation |
|----------|------|------|-------------|----------------|
| Hardcoded `frozenset` in script | High | Zero | Manual (add source comment) | **(rec:)** |
| External JSON registry file | Medium | Zero | Separate file | (bp:) |
| Dynamic discovery via API | Low | Complex | Auto but unreliable | Rejected |

### 3d. OwlBear Agent Audit

All 11 agents use only tools from the canonical list + MCP patterns. No unknown tools found. The expansion will serve as a regression safety net for future agent edits.

## 4. Recommendation (.90 confidence)

**Hardcoded frozenset approach.** Add `TOOL_SETS`, `BUILT_IN_TOOLS` frozensets to `validate_agents.py`. Parse each tool name from `tools:` and classify: tool set → pass, built-in → pass, MCP pattern (`*/\*`) → pass, else → flag. Keep existing `todo`/`resolveMemoryFileUri` checks. Add `# Source: <URL> | Last verified: YYYY-MM-DD` comment for maintenance.

Risk: cheat sheet omits active tools (6 found). Mitigation: include confirmed-active tools with `# not on cheat sheet` annotation so maintainers know which need periodic re-verification.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement canonical tool registry validation in validate_agents.py" --priority nice-to-have --status ideation --tags phase-1,tooling,agent,config --body "## Objective\nAdd full tool name validation to validate_agents.py.\n\n## AC\n- [ ] Define TOOL_SETS and BUILT_IN_TOOLS frozensets with all 37 known tools + 7 sets\n- [ ] New validate function: classify each tools: entry as tool-set, built-in, MCP pattern, or unknown\n- [ ] MCP pattern: any name matching .*/.* (glob-style server reference)\n- [ ] Flag unknown tool names with actionable error messages\n- [ ] Keep existing todo/resolveMemoryFileUri checks\n- [ ] Add source URL and date comment for maintenance\n- [ ] All 11 current agent files pass validation\n- [ ] ruff clean\n\nSee docs/research/canonical-tool-registry-validation.md"
kanban\kanban-md.exe create "Add tests for canonical tool registry validation" --priority nice-to-have --status ideation --tags phase-1,tooling,test --body "## Objective\nTest the expanded validate_agents.py tool name validation.\n\n## AC\n- [ ] Test valid tool set names pass (agent, edit, search, etc.)\n- [ ] Test valid individual built-in tools pass\n- [ ] Test MCP server patterns pass (e.g. owlbear-kanban/*)\n- [ ] Test unknown tool names are flagged\n- [ ] Parametrized regression test over all 11 agent files\n- [ ] Existing todo and resolveMemoryFileUri tests still pass\n- [ ] ruff clean\n\nSee docs/research/canonical-tool-registry-validation.md"
```
