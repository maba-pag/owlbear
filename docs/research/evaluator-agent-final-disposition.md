# Evaluator Agent: Final Disposition

> **Owning task:** #681 — Evaluator agent: subagent result assessment + routing decisions
> **Date:** 2026-03-09 **Status:** Complete

## 1. Context and Question

Task #681 proposed a standalone `evaluator.agent.md` to offload result-assessment and routing decisions from the orchestrator. Two prior research docs exist:

- [evaluator-agent-research.md](evaluator-agent-research.md) (2026-03-08): recommended creation (.85)
- [evaluator-agent-revisited.md](evaluator-agent-revisited.md) (2026-03-09): recommended closure (.85)

Since the last research, the codebase evolved further. This doc resolves the conflict with a final recommendation based on verified codebase state and updated industry patterns.

**Core question:** Should #681 be closed, or does the evaluator still provide enough unique value to justify building?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OpenAI Agents SDK v0.11.1 — Orchestration | <https://openai.github.io/openai-agents-python/multi_agent/> | .90 — no evaluator; eval-loop is code-level, not a separate agent |
| 2 | Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | .85 — guided retry via verbal self-reflection (evaluator's unique value) |
| 3 | OwlBear orchestrator.agent.md (current) | `.github/agents/orchestrator.agent.md` | 1.0 — 3-step loop: plan→dispatch→re-plan, no evaluator |
| 4 | OwlBear planner.agent.md + wave-planning skill | `.github/agents/planner.agent.md`, `.github/skills/wave-planning/SKILL.md` | 1.0 — planner reads board, produces JSON plan, flags stale tasks |
| 5 | OwlBear orchestration skill | `.github/skills/orchestration/SKILL.md` | 1.0 — constant-size context, 1 retry + stale-to-planner |

## 3. Analysis

### 3.1 Verified codebase state (March 9)

| Artifact | Status |
|----------|--------|
| `evaluator.agent.md` | Does not exist |
| Planner EVALUATE mode | Does not exist — architect's claim was wrong |
| Orchestrator (committed) | 3-step loop (plan→dispatch→loop), no evaluator calls |
| #682 orchestrator rewrite | `review`, blocked — 8-step version was overwritten by 3-step |
| Reviewer agent | Active — quality gate for 1 task (code + tests) |
| Auditor agent | Active — exit gate for 1 task (full AC verification) |

### 3.2 The evaluator's original problem is solved

The evaluator was designed to solve: _orchestrator accumulates cognitive context across waves, causing degradation_. The current design solves this differently:

| Concern | Evaluator solution | Current solution |
|---------|-------------------|-----------------|
| Context accumulation | Evaluator consumes results per wave | Planner re-reads board each cycle; orchestrator discards results |
| Result interpretation | Evaluator assesses AC compliance | Agents move their own tasks; planner reads updated board state |
| Retry routing | Evaluator returns RETRY + hint | Orchestrator retries once → planner flags stale tasks |
| Quality check | Evaluator per wave | Reviewer per task + auditor per task = 2 independent gates |

### 3.3 Industry pattern: evaluators are code, not agents

OpenAI Agents SDK documents the evaluator pattern as a _code-level while loop_: "Running the agent that performs the task in a while loop with an agent that evaluates and provides feedback." The evaluator is not a separate agent type — it's an orchestration pattern in code. This matches OwlBear's current approach: the orchestrator retries mechanically, the planner detects stale tasks.

No major framework (OpenAI SDK, CrewAI, LangGraph, AutoGen) ships a standalone evaluator agent. Quality gates are implemented as guardrails (OpenAI), validators (Pydantic), or inline checks (Conductor's max-3 fix cycle).

### 3.4 Remaining gap: guided retry

The evaluator's unique value from Reflexion is _verbal retry hints_ — when a task fails, the evaluator generates specific fix guidance. Current gap:

| Scenario | Current behavior | With guided retry |
|----------|-----------------|-------------------|
| Builder fails, task stale | Planner flags STALE, orchestrator retries blindly | Planner reads task body, includes 1-line failure hint |

This gap is real but minor — it affects only stale-task retries (rare after defense-in-depth improvements). It can be addressed by a small enhancement to the planner's stale-task detection, not a new agent.

### 3.5 #682 dependency resolution

# 682 lists `depends_on: [680, 681]`. Since #680 (planner) is archived and #681 should close:

- #682's 8-step AC (Plan, Track, Dispatch, **Evaluate**, **Execute**, **Pipeline**, Loop, Curate) assumed an evaluator in Steps 4-6
- The committed orchestrator already uses the simpler 3-step design
- #682 should be updated to remove the evaluator dependency and align AC with the working 3-step model

## 4. Recommendation (.90 confidence)

**Close #681 as superseded. No evaluator agent needed.**

| Factor | Assessment |
|--------|-----------|
| Original problem (context degradation) | Solved by plan→dispatch→re-plan loop |
| Quality evaluation | Covered by reviewer + auditor (DRY) |
| Guided retry (unique value) | Minor gap; addressable via planner enhancement |
| Industry alignment | No framework ships standalone evaluator agents |
| KISS | Current 3-step + 2 quality gates is simpler |
| YAGNI | No evidence of repeated blind-retry failures in practice |

**Risk:** If retry quality becomes a measurable problem (agents fail ≥3× on same task), revisit guided retry as a planner enhancement. Track via concrete trigger, not speculation.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Update #682 AC: remove evaluator dep, align with 3-step orchestrator" --priority needed --status backlog --tags "scope:copilot,agent,phase-agent-arch" --body "Task #682 depends on #681 (evaluator) which is being closed as superseded. Update #682 AC to: (1) Remove depends_on 681, (2) Replace 8-step workflow (Plan/Track/Dispatch/Evaluate/Execute/Pipeline/Loop/Curate) with 3-step (Plan/Dispatch/Loop) matching current committed orchestrator, (3) Remove evaluator-related AC lines (Steps 4-6, signal contracts for EvalResult, agents list evaluator entry), (4) Unblock #682. See docs/research/evaluator-agent-final-disposition.md."

kanban\kanban-md.exe create "Add guided retry hints to planner stale-task detection" --priority nice-to-have --status backlog --tags "scope:copilot,agent" --body "When the planner detects a stale task (dispatched but status unchanged), read the task body for the latest agent notes section and include a 1-line diagnostic hint in the BLOCKED reason. This provides Reflexion-style verbal retry feedback without a separate evaluator agent. Trigger: only build this if we observe repeated blind-retry failures in orchestrator sessions. AC: (1) Planner reads task body latest ## Notes when task is stale, (2) BLOCKED reason includes 1-line hint from agent notes, (3) Orchestrator passes hint in failure context for re-dispatch. See docs/research/evaluator-agent-final-disposition.md §3.4."
```
