# Validate Multi-Project Setup in VS Code — Research

> **Owning task:** #167 — Validate multi-project setup in VS Code (manual)
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #167 validates the clone=install distribution model end-to-end by manually opening a test project in VS Code and verifying agents, skills, instructions, and MCP servers load correctly. This research validates the AC is still accurate given current project state, identifies new VS Code verification tools, and confirms prerequisites.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code custom agents docs | <https://code.visualstudio.com/docs/copilot/customization/custom-agents> | .95 |
| 2 | VS Code customization overview | <https://code.visualstudio.com/docs/copilot/copilot-customization> | .90 |
| 3 | VS Code MCP configuration reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | .90 |
| 4 | Prior research: multi-project-setup-test.md | `docs/research/multi-project-setup-test.md` (task #25) | 1.0 |
| 5 | Setup script implementation | `scripts/setup.py` | 1.0 |
| 6 | Setup guide | `docs/setup-guide.md` | .95 |
| 7 | MCP kanban server | `packages/mcp-kanban/` | .90 |
| 8 | MCP knowledge server | `packages/mcp-knowledge/` | .85 |
| 9 | MCP project server | `packages/mcp-project/` | .85 |

## 3. Analysis

### 3.1 Prerequisite Status

| Prerequisite | Status | Evidence |
|--------------|--------|----------|
| #12 (setup script) | Archived | 60 tests passing in test_setup_script.py |
| #18 (MCP server config) | Archived | .vscode/mcp.json generated with 4 servers |

Both prerequisites met. No blockers.

### 3.2 MCP Server Readiness (Updated)

| Server | Task | Status | Startable? |
|--------|------|--------|-----------|
| owlbearKanban | #14 | Archived | YES — fully operational |
| owlbearKnowledge | #16 | Backlog | NO — depends on unbuilt knowledge package |
| owlbearProject | #17 | In-progress | PARTIAL — models exist, server has import issues |

**Impact on AC:** AC item 5 ("Invoke an owlbear-kanban MCP tool") is correctly scoped to kanban only. The other two servers will show startup errors in `MCP: List Servers` — this is expected behavior documented in setup-guide.md.

### 3.3 AC Validation Against Current VS Code Docs

| AC Item | Still Valid? | Notes |
|---------|-------------|-------|
| Run setup.py | YES | No changes to setup script |
| Agents in picker | YES | `chat.agentFilesLocations` confirmed (Source 1) |
| Skills via /skills or auto-load | YES | `chat.agentSkillsLocations` confirmed (Source 2) |
| Instructions via Diagnostics | YES | `chat.instructionsFilesLocations` confirmed (Source 2) |
| MCP tool invocation | YES | stdio config is standard (Source 3) |
| copilot-instructions.md in References | YES | Auto-detected in workspace root (Source 2) |
| Test agent in project's .github/agents/ | YES | VS Code loads from all locations (Source 1) |
| No agent shadowing | YES | Both visible with distinct names per Source 1 |

### 3.4 New VS Code Verification Tools (Since Prior Research)

Since the prior research (#25), VS Code has added:

| Tool | How to Access | Validation Use |
|------|---------------|---------------|
| **Chat Customizations editor** (Preview) | Gear icon in Chat view, or `Chat: Open Chat Customizations` | Browse all loaded agents, skills, instructions in a tabbed UI (Source 2) |
| **Configure Custom Agents menu** | `/agents` in chat input or from agents dropdown | Quick agent list with source tooltips on hover (Source 1) |
| **Agent Debug Logs** | Chat ellipsis menu, "Show Agent Debug Logs" | Chronological tool calls, prompt discovery events (Source 2) |

These supplement the existing Diagnostics view. The Chat Customizations editor is especially useful for systematic verification — it lists everything by category.

### 3.5 Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| owlbearKnowledge/Project fail on start | Low | Expected — VS Code starts servers independently. Document in validation notes. |
| `uv` not on PATH in test project | Medium | Ensure uv is installed before validation. setup-guide.md documents this. |
| Relative path breaks if dirs not siblings | Low | setup.py handles this; unit-tested. |

## 4. Recommendation (.90 confidence)

**Task #167 AC is valid and ready for pipeline progression.** No AC changes needed. The manual validation checklist is well-scoped and all prerequisites are met.

Two minor additions for the executor (not AC changes — tips):
1. Use the **Chat Customizations editor** (Preview) as an alternative to Diagnostics for verifying loaded customizations — it provides a cleaner per-category view.
2. When checking MCP servers, use `MCP: List Servers` command and expect owlbearKnowledge and owlbearProject to show errors (non-blocking).

**This is a human task.** It cannot be executed by pipeline agents — it requires physically opening VS Code with a test project and interacting with the UI. The task should move through architect → todo and be picked up by the user.

## 5. Follow-up Tasks

No new follow-up tasks needed. The AC is complete and self-contained. Related documentation tasks (#175) already exist.
