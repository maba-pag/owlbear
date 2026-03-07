# ComposioHQ/agent-orchestrator — Research Analysis

> **Owning task:** #585 — Research: ComposioHQ/agent-orchestrator
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear's orchestrator dispatches specialist agents (builder, reviewer, writer, etc.)
sequentially through a kanban pipeline. agent-orchestrator solves a *different*
problem: spawning **parallel** AI coding agents (Claude Code, Codex, Aider), each
in isolated git worktrees, with automated CI/review reaction loops. The question:
which patterns from agent-orchestrator are adoptable in OwlBear?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| ComposioHQ/agent-orchestrator | <https://github.com/ComposioHQ/agent-orchestrator> | .90 — primary subject |
| AutoGen SelectorGroupChat | <https://github.com/microsoft/autogen> | .70 — prior art for LLM-based agent routing |
| PydanticAI multi-agent docs | <https://ai.pydantic.dev/multi-agent-applications/> | .75 — OwlBear's agent framework reference |
| OpenClaw (prior research #22) | <https://github.com/openclaw/openclaw> | .65 — previously studied hook/plugin patterns |

## 3. Analysis

### 3.1 Architectural Comparison

| Criterion | agent-orchestrator | OwlBear | Gap / Opportunity |
|-----------|-------------------|---------|-------------------|
| **Language** | TypeScript (Node 20+, pnpm) | Python 3.12 (PydanticAI, uv) | Patterns transferable, code not |
| **Agent model** | External processes (Claude Code, Codex in tmux/Docker) | In-process PydanticAI agents | Different paradigm — AO manages *processes*, OB manages *coroutines* |
| **Parallelism** | True parallel: N agents in N worktrees | Sequential pipeline per task | **Gap**: OB could parallelize independent builder tasks |
| **Isolation** | Git worktrees per session | Single workspace shared | **Gap**: worktree isolation for parallel builds |
| **Plugin system** | 8-slot interface-based (Runtime, Agent, Workspace, Tracker, SCM, Notifier, Terminal, Lifecycle) | Toolset-based (FunctionToolset subclasses) | OB toolsets serve similar purpose; no gap |
| **State machine** | Polling-based lifecycle manager (15 statuses) | Kanban statuses (7 columns) + hook events | AO's lifecycle is CI/PR-focused; OB's is task-pipeline-focused |
| **Reactions** | Config-driven auto-responses (ci-failed → send-to-agent, changes-requested → send-to-agent) | Hook system (ON_ERROR, ON_RUN_START, etc.) | **Opportunity**: config-driven reaction patterns |
| **Notifications** | Push-based (desktop, Slack, webhook) with priority routing | Slack channel + CLI | AO's priority-routed notifications are more mature |
| **Config** | YAML + Zod validation | pydantic-settings (env + TOML) | Same pattern, different implementation |

### 3.2 Patterns Worth Adopting (.75 confidence)

**A. Reaction Engine Pattern**
AO's reaction system maps events → configurable actions (send-to-agent, notify,
auto-merge) with retry counts and escalation timers. OwlBear's hook system fires
events but does not have config-driven reaction routing with retry/escalation.
Adoptable as an extension to `owlbear.core.hooks`.

**B. Priority-Routed Notifications**
AO routes notifications by priority level (urgent → desktop+slack, info → slack only).
OwlBear currently has a single Slack channel. Adding priority-based routing to the
existing `SlackChannel` is straightforward and improves signal-to-noise.

**C. Layered Prompt Builder**
AO composes prompts in 3 layers: base agent instructions → config-derived context →
user rules. OwlBear's agent `.md` files serve a similar purpose but lack runtime
context injection (project name, active branch, reaction rules). A thin prompt-builder
layer could inject runtime context into agent system prompts.

### 3.3 Patterns Not Applicable

| Pattern | Why Not |
|---------|---------|
| Git worktree isolation | OwlBear agents work in-process on the same codebase; isolation is via kanban task boundaries, not filesystem |
| tmux/Docker runtimes | OwlBear agents are PydanticAI coroutines, not external processes |
| External agent adapters (Claude Code, Codex, Aider) | OwlBear uses one LLM provider (Copilot) via PydanticAI — no adapter layer needed |
| Session metadata (flat key=value files) | OwlBear uses kanban-md for task state; adding a parallel metadata store would violate single-source-of-truth |
| Web dashboard (Next.js SSE) | Not in OwlBear's scope — CLI + Slack are the interfaces |
| PR auto-merge / CI monitoring | OwlBear doesn't manage PRs; the human developer does |

### 3.4 KISS/YAGNI Assessment

AO is a **process orchestrator** for external AI tools. OwlBear is an **agent
framework** with internal PydanticAI agents. The core abstraction (spawn external
processes + monitor via polling) does not transfer. What transfers are the *periphery
patterns*: reaction routing, notification priority, prompt layering.

Estimated effort: each adoptable pattern is ~50–100 LOC. None requires architectural
changes — they extend existing systems (hooks, Slack channel, agent prompts).

## 4. Recommendation (.75 confidence)

Adopt the reaction engine and notification priority-routing patterns as extensions to
existing OwlBear subsystems. Skip process isolation and external agent management —
these solve problems OwlBear doesn't have.

**Risk:** Over-engineering the reaction system for a single-agent-at-a-time pipeline.
Mitigation: implement only when OwlBear gains parallel task execution.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Reaction engine: config-driven event→action routing with retry/escalation" --priority nice-to-have --status ideation --tags "phase-research,scope:core,hooks" --body "Extend owlbear.core.hooks with a reaction config mapping HookEvent types to actions (notify, retry-agent, escalate). Include retry count and escalation timer per reaction. Inspired by agent-orchestrator reaction engine. See docs/agent-orchestrator-research.md §3.2A"

kanban\kanban-md.exe create "Priority-routed notifications for Slack channel" --priority nice-to-have --status ideation --tags "phase-research,scope:slack" --body "Add priority-based notification routing to SlackChannel: urgent→DM+channel, action→channel, info→thread-only. Inspired by agent-orchestrator notificationRouting config. See docs/agent-orchestrator-research.md §3.2B"

kanban\kanban-md.exe create "Runtime context injection in agent system prompts" --priority nice-to-have --status ideation --tags "phase-research,scope:agent" --body "Add a thin prompt-builder layer that injects runtime context (active project, workspace root, current task ID) into agent system prompts at dispatch time. Inspired by agent-orchestrator 3-layer prompt builder. See docs/agent-orchestrator-research.md §3.2C"
```
