# Agent Port to v2 — Research

> **Owning task:** #8 — Port agents to .agent.md format
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #8 requires porting all 11 v1 agents from `.github/agents/` to the v2 `agents/`
directory, "replacing PydanticAI tool references with VS Code built-in tools." Research
question: what exactly needs to change, and what is the safest port strategy?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .95 — `.agent.md` spec, frontmatter fields |
| VS Code Chat Tools Reference | https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .90 — complete built-in tool list |
| VS Code Subagents docs | https://code.visualstudio.com/docs/copilot/agents/subagents | .90 — `agents:` field, restriction patterns |
| #4 research (agent-md-format.md) | docs/research/agent-md-format.md | .95 — tool name mapping, v1 validation |
| v1 agent files (11 files) | .github/agents/*.agent.md | 1.0 — current state |
| .vscode/settings.json | Local file | .85 — agent discovery config |

## 3. Analysis

### 3a. Port complexity: copy + fix, not rewrite

The v1 agents in `.github/agents/` **already use VS Code `.agent.md` format** with correct
built-in tool names. The PydanticAI tool references existed only in the older
`src/owlbear/agents/*.md` files (v0), not in the v1 `.github/agents/` format. The port is
therefore a copy + targeted fix operation, not a structural rewrite.

### 3b. Tool reference corrections needed

| Issue | Agents affected | Fix | Existing task? |
|-------|----------------|-----|---------------|
| `todo` → `todos` | All 11 | Rename in `tools:` | #36 (archived but **NOT applied**) |
| `vscode/resolveMemoryFileUri` | curator | Remove (undocumented tool) | #80 (in todo) |
| `microsoft/markitdown/*` | researcher | Keep as-is (valid MCP syntax) | N/A |

**Critical finding:** Task #36 (rename `todo` → `todos`) is archived, but `grep` confirms
all 11 `.github/agents/` files still reference `todo`, not `todos`. The fix was never
applied. The v2 port must include this correction.

### 3c. `agents:` field analysis

| Agent | Current `agents:` | Delegates? | Recommended v2 |
|-------|-------------------|-----------|----------------|
| orchestrator | explicit list (10) | Yes — dispatches all | Keep list, add `Explore` |
| researcher | default (`*`) | Yes — uses `Explore` | `[Explore]` |
| All 9 others | default (`*`) | No | `agents: []` |

**Rationale (.80 confidence):** VS Code docs confirm `agents: *` (default) allows any
subagent. Leaf agents (builder, reviewer, writer, auditor, test-writer, architect,
planner, kanban-planner, curator) don't delegate. Setting `agents: []` follows
least-privilege. The orchestrator's list should add `Explore` (used by multiple
agents via subagent). The researcher explicitly uses `Explore`.

**Alternative (.60 confidence):** Leave all at default `*` for simplicity (KISS).
Risk: unintended subagent dispatch by leaf agents.

### 3d. New tools available since v1

| Tool | Use case | Priority for v2 |
|------|----------|-----------------|
| `search/usages` | Find All References | Useful for reviewer, builder |
| `search/changes` | Source control changes | Useful for reviewer, auditor |
| `vscode/askQuestions` | Interactive question carousel | Useful for user-facing agents |
| `read/terminalSelection` | Terminal selection | Low priority |

**Recommendation:** Defer new tool additions to a separate task. The port should
minimize changes to reduce risk. Tool list expansion is independent of the port.

### 3e. Settings and filesystem readiness

| Check | Status |
|-------|--------|
| `agents/` directory exists | Yes (has README.md placeholder) |
| `chat.agentFilesLocations` includes `agents/` | Yes (confirmed) |
| `chat.subagents.allowInvocationsFromSubagents` | Not verified — needed for orchestrator → planner → kanban-planner chain |

### 3f. Duplicate agent risk

During the port, both `.github/agents/` and `agents/` will contain the same agents. VS
Code will discover both, causing duplicate agent names. **Migration strategy:**

1. Copy all 11 agents to `agents/` with fixes applied
2. Test 2+ agents from the `agents/` location
3. Delete `.github/agents/` only after verification
4. Remove `.github/agents` from `chat.agentFilesLocations`

**Alternative:** Rename v1 files to `.agent.md.bak` during testing to avoid duplicates.

## 4. Recommendation (.85 confidence)

The port is straightforward — copy 11 files, apply 2 targeted fixes (`todo` → `todos`,
remove `vscode/resolveMemoryFileUri`), and tighten `agents:` fields. **Total expected
diff: ~15 lines across 11 files + 11 file copies + 11 file deletes.**

Risk: the `agents: []` change could theoretically break an agent that needs delegation
in an edge case not documented. Mitigation: test delegation-dependent agents first
(orchestrator, researcher).

Alignment: KISS (minimal changes), YAGNI (no new tools in port), DRY (no content
changes needed).

## 5. Per-agent port checklist

| Agent | `todo`→`todos` | Remove unsupported tool | Set `agents:` | Other |
|-------|:-:|:-:|:-:|-------|
| orchestrator | ✓ | — | Add `Explore` to list | — |
| builder | ✓ | — | `[]` | — |
| reviewer | ✓ | — | `[]` | — |
| researcher | ✓ | — | `[Explore]` | Keep `microsoft/markitdown/*` |
| architect | ✓ | — | `[]` | — |
| planner | ✓ | — | `[]` | — |
| writer | ✓ | — | `[]` | — |
| auditor | ✓ | — | `[]` | — |
| curator | ✓ | Remove `vscode/resolveMemoryFileUri` | `[]` | Subsumes #80 |
| test-writer | ✓ | — | `[]` | — |
| kanban-planner | ✓ | — | `[]` | — |

## 6. Follow-up Tasks

```
kanban\kanban-md.exe create "Evaluate new VS Code tools for v2 agents (search/usages, search/changes, vscode/askQuestions)" --priority nice-to-have --status ideation --tags phase-2,scope:agents,research
```
