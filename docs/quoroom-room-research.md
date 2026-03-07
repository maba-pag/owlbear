# quoroom-ai/room — Multi-Agent Orchestration Research

> **Owning task:** #588 — Research: quoroom-ai/room
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Analyze quoroom-ai/room for multi-agent delegation, orchestration patterns, and task execution logic reusable in OwlBear. Room is a TypeScript/Node.js swarm-intelligence system with Queen/Worker/Quorum architecture, MCP server, and autonomous agent loops. OwlBear needs patterns for: always-on agent cycles, delegation between agents, governance/approval, WIP continuity, stuck detection, and session management.

## 2. Sources Studied

| Source | URL | License | Relevance |
|--------|-----|---------|-----------|
| quoroom-ai/room | <https://github.com/quoroom-ai/room> | MIT | .95 — primary subject; Queen/Worker/Quorum delegation, agent loop, WIP continuity, stuck detection, session compression |
| microsoft/autogen | <https://github.com/microsoft/autogen> | MIT/CC-BY-4.0 | .70 — comparison: AgentTool delegation pattern, multi-agent orchestration via tool wrapping |

## 3. Analysis

### 3.1 Agent Loop Architecture

| Criterion | Quoroom Room | OwlBear (current) | Gap |
|-----------|-------------|-------------------|-----|
| Always-on loop | `startAgentLoop` with gap/quiet-hours/rate-limit | Single `agent.turn()` calls, no persistent loop | **Major** — OwlBear has no autonomous cycling |
| Cycle gap (adaptive) | Momentum gap (10s when WIP active, configurable base otherwise) | N/A | Useful pattern for daemon mode |
| Quiet hours | Time-window where agent sleeps | N/A | Nice-to-have for daemon |
| Rate limit handling | `RateLimitError` detection, auto-wait, state transition to `rate_limited` | tenacity retry on provider errors | Room's approach is more granular |
| Agent states | `idle`, `thinking`, `acting`, `voting`, `rate_limited`, `blocked` | No explicit state machine | **Medium** — useful for observability |

**Key pattern — Adaptive cycle gap:** When a worker has active WIP (work-in-progress), the gap shrinks to 10s (momentum). Otherwise it uses the configured gap. This prevents idle agents from burning tokens while keeping active work moving fast.

### 3.2 Delegation Model

| Criterion | Quoroom Room | OwlBear (current) | AutoGen |
|-----------|-------------|-------------------|---------|
| Mechanism | `quoroom_delegate_task` tool creates a Goal assigned to a worker, then `triggerAgent` wakes that worker | `delegate_to_agent` tool looks up agent in registry, runs inline | `AgentTool` wraps agent as tool callable |
| Async? | Yes — delegation is fire-and-forget, worker picks up next cycle | No — delegation is synchronous inline | No — synchronous |
| Role separation | Queen = control plane only (delegate, monitor, unblock); Workers = execution | All agents can call all tools within allowed set | No enforced separation |
| Tool partitioning | `QUEEN_TOOLS` vs `WORKER_TOOLS` — separate allowlists by role | Single toolset per agent, configured at bootstrap | Per-agent tool assignment |

**Key pattern — Control plane / Execution plane separation:** The Queen explicitly cannot perform execution tasks (web search, browser, etc.) in "control-plane mode." A policy hint is injected: `[policy] Queen control-plane mode: delegate execution tasks to workers`. Workers get execution tools but not governance tools. This prevents the orchestrator from doing work it should delegate.

### 3.3 WIP Continuity Across Cycles

Room agents call `quoroom_save_wip` at end of each cycle to persist what they accomplished. Next cycle, WIP is injected as `>>> CONTINUE FORWARD <<<` directive at highest priority in the prompt. This enables multi-cycle task continuity without the agent re-discovering what it was doing.

OwlBear currently has no WIP continuity — each agent turn is independent. The session store persists messages but has no structured "resume from here" mechanism.

### 3.4 Stuck Detection

Room tracks `productiveToolCalls` per worker over last N cycles. If a worker had WIP but 0 productive calls for 2+ cycles, it injects a `STUCK — TAKE ACTION NOW` directive. This is a simple but effective self-healing mechanism.

### 3.5 Quorum Governance vs. OwlBear Approval Gates

| Criterion | Quoroom Room | OwlBear (current) |
|-----------|-------------|-------------------|
| Model | Announce + 10min objection window + auto-effective | Approval gates on destructive tools (Slack/CLI approval buttons) |
| Who decides | Workers + Keeper can object | Human only |
| Granularity | Per decision type (strategy, resource, personnel, rule_change, low_impact) | Per tool category (git push, PRs, deploy, run_command) |

Room's governance is more autonomous (agents self-govern), OwlBear's is more human-gated. Both approaches are valid for their contexts.

### 3.6 Session Compression

When API-mode sessions exceed 30 messages, Room compresses them via a dedicated LLM call into a summary, then stores the summary as a "queen_session_summary" memory entity. This prevents context window overflow while preserving institutional knowledge.

### 3.7 Skills System

Room's skills are context-activated: `loadSkillsForAgent` matches skills to the current cycle context, injects top 8 skills (max 6000 chars). Skills are versioned, agent-createable, and have `activationContext` arrays for relevance matching. OwlBear has a `SkillsRegistry` with file-based skills — Room's context-activation and version tracking are more sophisticated.

### 3.8 Self-Modification Safety

Room has `canModify` guards: rate-limited (60s between mods per worker), forbidden path patterns (private keys, .env, self-mod.ts itself), full audit trail with one-click revert, snapshot-based revert for skill content. OwlBear has `ApprovalPolicy` but no per-agent rate limiting on modifications.

## 4. Recommendation

### Adopt (.80 confidence): WIP Continuity Pattern

The `save_wip` → `CONTINUE FORWARD` pattern is the highest-value takeaway. It solves the multi-cycle amnesia problem that any always-on agent system faces. Implementation: a `WipStore` keyed by agent name, injected at prompt-build time.

### Adopt (.75 confidence): Stuck Detection

Simple counter of productive tool calls over recent cycles. Low implementation cost, high defensive value. Can be added to the hook system as a `PRE_TURN` hook.

### Consider (.65 confidence): Adaptive Cycle Gap

Momentum gap when WIP is active vs. longer gap when idle. Only relevant once OwlBear daemon mode is implemented.

### Consider (.60 confidence): Role-Based Tool Partitioning

Separate `QUEEN_TOOLS` / `WORKER_TOOLS` enforces delegation discipline. OwlBear already has per-agent tool configuration in bootstrap, but adding an explicit control-plane-only constraint for the orchestrator would be valuable.

### Skip (.40 confidence): Quorum Governance

Room's announce/objection model is designed for autonomous agent collectives where agents self-govern. OwlBear's human-gated approval system is more appropriate for a developer assistant.

### Skip (.30 confidence): Session Compression via LLM

Expensive (extra LLM call per cycle when threshold hit). PydanticAI's history processors provide a cleaner extension point for this if needed later.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement WIP continuity store for agent cycles" --priority needed --tags "phase-7,agent,scope:core" --body "Add a WipStore (keyed by agent name) that persists what each agent accomplished. Inject as high-priority context in next turn. Pattern from quoroom-ai/room save_wip/CONTINUE FORWARD. See docs/quoroom-room-research.md S3.3. AC: (1) WipStore CRUD with JSONL backend (2) save_wip tool registered on agents (3) WIP injected in prompt before other context (4) Tests cover save/load/inject cycle"

kanban\kanban-md.exe create "Add stuck detection hook for agent loops" --priority important --tags "phase-7,agent,hooks,scope:core" --body "Track productive tool calls per agent over recent turns. If agent had WIP but 0 productive calls for N turns, inject stuck directive. Pattern from quoroom-ai/room stuck detector. See docs/quoroom-room-research.md S3.4. AC: (1) Counter in hook system tracks tool calls per agent (2) PRE_TURN hook checks counter and injects stuck warning (3) Configurable threshold (default 2 turns) (4) Tests cover stuck detection and warning injection"

kanban\kanban-md.exe create "Enforce control-plane-only constraint on orchestrator agent" --priority important --tags "phase-7,agent,scope:core" --body "Orchestrator should only delegate, never execute. Add policy hint injection and restrict orchestrator toolset to delegation/kanban/messaging tools only. Pattern from quoroom-ai/room Queen control-plane mode. See docs/quoroom-room-research.md S3.2. AC: (1) Orchestrator agent toolset excludes execution tools (filesystem, terminal, browser) (2) Policy hint injected in orchestrator system prompt (3) Delegation tool is primary action mechanism (4) Tests verify tool restriction"

kanban\kanban-md.exe create "Add agent state machine for observability" --priority nice-to-have --tags "phase-7,agent,scope:core" --body "Track agent states (idle, thinking, acting, rate_limited, blocked) for dashboard/logging. Pattern from quoroom-ai/room agent states. See docs/quoroom-room-research.md S3.1. AC: (1) AgentState enum with transitions (2) State transitions logged via hooks (3) Current state queryable per agent (4) Tests cover state transitions"
```
