# Add `disable-model-invocation` to Pipeline-Only Agents

> **Owning task:** #38 — Add disable-model-invocation to pipeline-only agents
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

OwlBear has 11 agents. Eight are pipeline-only (invoked exclusively by the orchestrator as subagents). The VS Code `.agent.md` spec includes `disable-model-invocation`, which prevents an agent from being invoked as a subagent by arbitrary callers. Should pipeline agents use this flag, and which agents qualify?

Parent research: `docs/research/agent-md-format.md` (task #4) identified this as a follow-up.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .95 — canonical `disable-model-invocation` definition |
| VS Code Subagents docs | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — override behavior: explicit `agents` array overrides the flag |

## 3. Analysis

### How `disable-model-invocation` works

- **Default:** `false` — any agent can invoke this agent as a subagent.
- **When `true`:** the AI model cannot autonomously select this agent as a subagent.
- **Override:** explicitly listing the agent in a caller's `agents` array **overrides** the flag. From the subagents docs: "Explicitly listing an agent in the `agents` array overrides `disable-model-invocation: true`."

This means: setting the flag on pipeline agents blocks unintended callers while the orchestrator (which explicitly lists them in `agents`) continues to work.

### Current agent inventory

| Agent | `user-invocable` | In orchestrator `agents` | Pipeline-only? |
|-------|:-----------------:|:------------------------:|:--------------:|
| orchestrator | true | N/A (is coordinator) | No |
| kanban-planner | true | Yes | No |
| curator | true | Yes | No |
| planner | false | Yes | **Yes** |
| researcher | false | Yes | **Yes** |
| architect | false | Yes | **Yes** |
| test-writer | false | Yes | **Yes** |
| builder | false | Yes | **Yes** |
| reviewer | false | Yes | **Yes** |
| writer | false | Yes | **Yes** |
| auditor | false | Yes | **Yes** |

### Risk assessment

| Risk | Without flag | With flag |
|------|-------------|-----------|
| Unintended subagent invocation by generic chat | Possible — model may autonomously invoke pipeline agents | Blocked — only explicit `agents` lists allow it |
| Pipeline functionality broken | N/A | No — orchestrator's explicit `agents` list overrides the flag |
| Future flexibility reduced | N/A | Minimal — any new coordinator just adds the agent to its `agents` list |

## 4. Recommendation (.90 confidence)

Add `disable-model-invocation: true` to all 8 pipeline-only agents (planner, researcher, architect, test-writer, builder, reviewer, writer, auditor). Do **not** add it to orchestrator, kanban-planner, or curator.

**Rationale:** Defense-in-depth. Pipeline agents carry tools that modify files, run commands, and mutate kanban state. Blocking unintended invocation prevents accidental task mutations and claim conflicts. The orchestrator's explicit `agents` list ensures the pipeline continues to function. This aligns with KISS (one-line config per agent) and the principle of least privilege.

**Implementation:** Add `disable-model-invocation: true` to the YAML frontmatter of each pipeline agent file. No other changes required. Trivial config-only change — 8 files, 1 line each.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Set disable-model-invocation: true on 8 pipeline agents" --priority nice-to-have --status ideation --tags phase-1,scope:agents,type:build
```
