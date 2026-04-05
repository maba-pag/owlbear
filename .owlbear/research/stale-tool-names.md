# Stale VS Code Tool Names Audit

> **Owning task:** #193 — Fix stale VS Code tool names in validation scripts and agent files
> **Date:** 2026-03-29 **Status:** Complete (decision pending)

## 1. Context and Question

Task #193 asked: are there stale VS Code Copilot Chat tool names in the
validation scripts and agent files? Specifically, the user believed `todos` was
the OLD tool name and `todo` the current one.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Cheat Sheet (March 25, 2026) | https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .95 — canonical built-in tool list |
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — tools field spec |
| Prior research: agent-md-format.md | docs/research/agent-md-format.md (task #4) | .90 — v1→v2 tool mapping |
| Existing tests: test_agent_port_v2.py | tests/test_agent_port_v2.py | .85 — validates todos in all agents |
| VS Code v1.99 Release Notes | https://code.visualstudio.com/updates/v1_99 | .70 — no tool renames mentioned |

## 3. Analysis

### Canonical built-in tool list (from VS Code cheat sheet, March 25, 2026)

| Tool Set | Individual Tools |
|----------|-----------------|
| `agent` | `agent/runSubagent` |
| `browser` | (experimental, multiple) |
| `edit` | `edit/createDirectory`, `edit/createFile`, `edit/editFiles`, `edit/editNotebook` |
| `execute` | `execute/createAndRunTask`, `execute/getTerminalOutput`, `execute/runInTerminal`, `execute/runNotebookCell`, `execute/testFailure` |
| `read` | `read/getNotebookSummary`, `read/problems`, `read/readFile`, `read/readNotebookCellOutput`, `read/terminalLastCommand`, `read/terminalSelection` |
| `search` | `search/changes`, `search/codebase`, `search/fileSearch`, `search/listDirectory`, `search/textSearch`, `search/usages` |
| `web` | `web/fetch` |
| Standalone | `newWorkspace`, `selection`, **`todos`**, `vscode/askQuestions`, `vscode/extensions`, `vscode/getProjectSetupInfo`, `vscode/installExtension`, `vscode/runCommand`, `vscode/VSCodeAPI` |

**Note:** The cheat sheet is NOT exhaustive. Tools confirmed active in current
sessions but absent from the cheat sheet: `execute/awaitTerminal`,
`execute/killTerminal`, `read/viewImage`, `edit/rename`, `vscode/memory`.

### Audit: validate_agents.py

| Check | Logic | Correct? |
|-------|-------|----------|
| `\btodo\b` → "should be `todos`" | Flags bare `todo`, recommends `todos` | YES — `todos` is the official name |
| `resolveMemoryFileUri` presence | Flags deprecated tool | YES — not in official registry |

The validator is correct but limited (only 2 checks).

### Audit: validate_skills.py

Validates skill frontmatter metadata structure (name, description fields).
Does NOT reference or validate tool names. Not affected by tool name changes.

### Audit: agent files (agents/*.agent.md)

All 11 agent files use `todos` in their tools lists. This is CORRECT per the
official docs. No stale references found.

### Audit: `todos` vs `todo` — the premise question

| Evidence Source | Says current name is | Confidence |
|----------------|---------------------|------------|
| VS Code cheat sheet (2026-03-25) | `#todos` | .95 |
| Prior research, task #4 | `todos` (renamed from `todo`) | .90 |
| test_agent_port_v2.py | asserts `todos` | .85 |
| Task #193 context (user claim) | `todo` | unverified |

**Conclusion (.95 confidence):** `todos` IS the current correct name. The task
premise is inverted — `todo` was the OLD v1 name, already migrated to `todos`
during the v2 agent port (task #8).

## 4. Recommendation (.95 confidence)

**No tool name renames are needed.** The codebase is already correct. A decision
request has been created at `docs/decisions/pending/193-todos-vs-todo-tool-name.md`
for the user to confirm or override this finding.

**Separate improvement opportunity:** The validator checks only 2 specific tool
names. It could be expanded to validate all agent tool references against the
canonical built-in tool registry, catching future stale references automatically.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Expand validate_agents.py to check all tool names against canonical registry" --priority nice-to-have --status ideation --tags phase-1,tooling,agent,config
```
