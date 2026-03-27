# .agent.md Format Validation

> **Owning task:** #4 — .agent.md format validation
> **Date:** 2026-03-26 (updated 2026-03-27) **Status:** Complete

## 1. Context and Question

OwlBear v1 has 11 agents in `.github/agents/` already using `.agent.md` format with VS Code
Copilot. The task is to validate the format specification, document all frontmatter fields,
map v1 tool references to VS Code built-in tools, and identify gaps for the v2 port.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .95 — canonical spec |
| VS Code Chat Tools Reference | https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .90 — complete built-in tool list |
| VS Code Agent Tools docs | https://code.visualstudio.com/docs/copilot/agents/agent-tools | .85 — tool sets, approval, terminal |
| VS Code Hooks docs | https://code.visualstudio.com/docs/copilot/customization/hooks | .85 — hook lifecycle + agent-scoped hooks |
| VS Code Subagents docs | https://code.visualstudio.com/docs/copilot/agents/subagents | .90 — orchestration patterns |

## 3. YAML Frontmatter Fields (complete spec)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `name` | string | filename | Agent display name |
| `description` | string | — | Placeholder text in chat input |
| `argument-hint` | string | — | Hint text in chat input |
| `tools` | string[] | all | Allowed built-in/MCP/extension tools |
| `agents` | string[] / `*` / `[]` | `*` | Allowed subagents; `*`=all, `[]`=none |
| `model` | string / string[] | picker | AI model; array = priority fallback list |
| `user-invocable` | bool | true | Show in agents dropdown |
| `disable-model-invocation` | bool | false | Block AI from invoking as subagent |
| `target` | string | — | `vscode` or `github-copilot` |
| `mcp-servers` | list | — | MCP server configs (github-copilot target only) |
| `handoffs` | list | — | Guided workflow transitions |
| `handoffs[].label` | string | — | Button display text |
| `handoffs[].agent` | string | — | Target agent name |
| `handoffs[].prompt` | string | — | Pre-filled prompt |
| `handoffs[].send` | bool | false | Auto-submit prompt |
| `handoffs[].model` | string | — | Model override for handoff |
| `hooks` | object | — | Agent-scoped hooks (preview; needs `chat.useCustomAgentHooks`) |

**Deprecated:** `infer` — replaced by `user-invocable` + `disable-model-invocation`.

## 4. Tool Name Mapping: v1 Agents → VS Code Built-in

| v1 Tool Reference | VS Code Built-in | Available? |
|--------------------|-----------------|------------|
| `read/readFile` | `read/readFile` | YES — identical |
| `read/problems` | `read/problems` | YES — identical |
| `read/terminalLastCommand` | `read/terminalLastCommand` | YES — identical |
| `read/viewImage` | `read/viewImage` | YES — identical |
| `edit/createFile` | `edit/createFile` | YES — identical |
| `edit/createDirectory` | `edit/createDirectory` | YES — identical |
| `edit/editFiles` | `edit/editFiles` | YES — identical |
| `edit/rename` | `edit/rename` | YES — identical |
| `execute/runInTerminal` | `execute/runInTerminal` | YES — identical |
| `execute/getTerminalOutput` | `execute/getTerminalOutput` | YES — identical |
| `execute/awaitTerminal` | `execute/awaitTerminal` | YES — identical |
| `execute/killTerminal` | `execute/killTerminal` | YES — identical |
| `search` | `search` (tool set) | YES — identical |
| `agent` | `agent` (tool set) | YES — identical |
| `web` | `web` (tool set) | YES — identical |
| `todo` | `todos` | RENAME — `todo` → `todos` |
| `vscode/memory` | `vscode/memory` | YES — identical |
| `vscode/resolveMemoryFileUri` | — | NO — not documented in built-in tool registry |
| `microsoft/markitdown/*` | — | MCP — needs MCP server reference |

**Key findings:**

- **17 of 19** v1 tool references map directly to VS Code built-ins (identical names).
- `todo` needs renaming to `todos` (the VS Code built-in name).
- `vscode/resolveMemoryFileUri` (curator agent only) is not listed in the official built-in tool registry and should be treated as unsupported for custom agent tool allowlists.
- `microsoft/markitdown/*` (researcher agent only) — this is an MCP server tool, correctly referenced with `server/*` syntax already.

## 5. Agent-to-Agent Handoff via `agents` Field

V1 orchestrator already uses `agents:` to list 10 subagents. This maps directly to the
VS Code `agents` field. Key validation points:

- **`agents` field restricts subagent scope** — the orchestrator's list of `[kanban-planner, planner, researcher, ...]` correctly limits which agents are delegatable.
- **`user-invocable: false`** is already used in v1 for pipeline agents (builder, reviewer, etc.) to hide them from the dropdown while keeping them available as subagents.
- **Nested subagents** require `chat.subagents.allowInvocationsFromSubagents` setting. Currently v1 agents don't nest, but the orchestrator→planner→kanban-planner chain may need this.
- **`disable-model-invocation: true`** is a new option not used in v1. Could protect pipeline agents from being invoked by unintended callers.

### Hands-on validation evidence (2026-03-27)

1. **Custom agent invocation in Copilot Chat equivalent flow**
- Method: invoked the `Explore` custom agent via the VS Code agent runtime (`runSubagent` tool) for a workspace question.
- Result: PASS. Agent responded with the correct `README.md` path and project summary.

2. **Agent-to-agent delegation (handoff behavior) validation**
- Method: invoked the `orchestrator` agent in read-only mode and requested a dry delegation check.
- Result: PASS. Orchestrator successfully invoked `planner`, which returned a structured dispatch plan; no task mutations occurred.

3. **Tool restriction behavior (allow and deny) validation**
- Method: invoked the `reviewer` agent and requested a file write plus a file read.
- Result: PASS. Write request was refused due to reviewer read-only constraints, while `README.md` read succeeded.

## 6. Model Selection and Thinking Configuration

V1 agents already use correct model syntax: `Claude Opus 4.6 (copilot)`, `Claude Sonnet 4.6 (copilot)`, etc. Array syntax for fallback priority is used (e.g., builder: `[GPT-5.3-Codex (copilot), Claude Sonnet 4.6 (copilot)]`). This is fully compatible.

Thinking effort is **not** configurable via `.agent.md` frontmatter fields in current VS Code custom-agent docs. Current supported guidance is:

- Use the `model` field in frontmatter for fixed model selection or fallback order.
- Configure thinking/reasoning effort in the Copilot model picker UI, which persists per model.
- Do not add non-documented frontmatter keys for effort control.

## 7. Hooks (Preview)

Agent-scoped hooks are new in VS Code (preview). V1 agents don't use them yet. Potential uses:
- **PostToolUse** on builder: auto-run ruff after file edits
- **PreToolUse** on all agents: enforce kanban-md claim validation
- **Stop** on auditor: ensure commit before session ends

Requires `chat.useCustomAgentHooks: true` setting.

## 8. Recommendation (.90 confidence)

The v1 agents are **already compatible** with the VS Code `.agent.md` specification, with one compatibility correction and two minor follow-ups:

1. Rename `todo` → `todos` in all agent tool lists (trivial, 1 line per file)
2. Replace/remove `vscode/resolveMemoryFileUri` usage in curator tooling (not documented as a supported built-in tool)
3. Keep `microsoft/markitdown/*` as an MCP tool reference (already correct pattern)

No structural changes required. The format is validated and portable.

## 9. Follow-up Tasks

1. **Rename `todo` tool reference to `todos` in all `.agent.md` files** (`#36`)
- Priority rationale: required for strict compatibility with VS Code built-in tool naming.
- Dependencies: none.
- One-line AC: all `.agent.md` tool lists use `todos`, and no `todo` entries remain.
- Command used: `kanban\kanban-md.exe create "Rename todo tool reference to todos in all .agent.md files" --priority nice-to-have --status ideation --tags phase-1,scope:agents`
- Created task ID: `36`.

2. **Evaluate agent-scoped hooks for pipeline enforcement** (`#37`)
- Priority rationale: improves governance and quality automation but not required for baseline compatibility.
- Dependencies: none.
- One-line AC: produce a documented recommendation for enabling hook types and rollout guardrails.
- Command used: `kanban\kanban-md.exe create "Evaluate agent-scoped hooks for pipeline enforcement" --priority nice-to-have --status ideation --tags research,phase-1,scope:agents,hooks`
- Created task ID: `37`.

3. **Add `disable-model-invocation` to pipeline-only agents** (`#38`)
- Priority rationale: reduces accidental autonomous invocation of non-user-facing pipeline agents.
- Dependencies: none.
- One-line AC: pipeline-only agents set and validate `disable-model-invocation: true` where appropriate.
- Command used: `kanban\kanban-md.exe create "Add disable-model-invocation to pipeline-only agents" --priority nice-to-have --status ideation --tags phase-1,scope:agents`
- Created task ID: `38`.

4. **Replace unsupported `vscode/resolveMemoryFileUri` tool usage in curator agent** (`#80`)
- Priority rationale: closes the remaining unsupported mapping gap identified during retry review.
- Dependencies: none.
- One-line AC: curator tooling references only documented built-in or MCP tool names, with mapping documented in this report.
- Command used: `kanban\kanban-md.exe create "Replace unsupported vscode/resolveMemoryFileUri tool usage in curator agent" --priority important --status backlog --tags phase-1,scope:agents,type:build`
- Created task ID: `80`.
