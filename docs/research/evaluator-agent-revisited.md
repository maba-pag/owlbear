# Evaluator Agent: Revisited — Do We Need One?

> **Owning task:** #681 — Evaluator agent: subagent result assessment + routing decisions
> **Date:** 2026-03-09 **Status:** Complete

## 1. Context and Question

Task #681 originally proposed a standalone `evaluator.agent.md`. The original research ([evaluator-agent.md](evaluator-agent.md)) recommended this based on Reflexion and Conductor patterns. Task #682 (orchestrator rewrite) was designed to depend on this evaluator.

**However, the actual state of the codebase diverges from the task history:**

| Artifact | Expected | Actual |
|----------|----------|--------|
| `evaluator.agent.md` | Created per #681 AC | Does not exist |
| Planner EVALUATE mode | Architect claimed "evaluator merged into planner" | No such mode exists |
| Orchestrator rewrite (#682) | Committed, using evaluator Step 4 | In review, never committed — current file has no evaluator |
| Current orchestrator | Superseded by #682 | Still live: plan→dispatch→re-plan loop, no evaluator |

The architect's BLOCK assessment ("design superseded by planner EVALUATE mode, 8/11 AC moot") is **factually incorrect** — no merge happened. The question is now: given the current working design, **is a standalone evaluator still needed, or has the pipeline's defense-in-depth made it redundant?**

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Reflexion (Shinn et al., 2023) | <https://arxiv.org/abs/2303.11366> | .90 — Evaluator (M_e) + verbal Self-Reflection; key contribution: guided retry feedback |
| 2 | Conductor evaluate-loop | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | .85 — Plan→EvalPlan→Execute→EvalExec→Fix cycle (max 3); 4 specialized evaluators |
| 3 | OpenAI Agents SDK | <https://github.com/openai/openai-agents-python> | .75 — No evaluator agent; uses Guardrails + Handoffs; evaluation implicit in framework |
| 4 | OwlBear pipeline (codebase) | `planner.agent.md`, `orchestrator.agent.md`, `reviewer.agent.md`, `auditor.agent.md` | 1.0 — current working system |

## 3. Analysis

### 3.1 What the current pipeline already covers

The current design has implicit evaluation via re-plan + defense-in-depth:

| Failure mode | How current design handles it | Gap? |
|---|---|---|
| Agent crashes | Orchestrator retries once → planner sees stale task | No |
| Agent succeeds, moves task | Planner reads new status, dispatches next agent | No |
| Agent produces poor output | Reviewer catches (review stage), auditor catches (done stage) | 1-stage delay |
| Agent returns without moving task | Planner detects stale task next cycle | No |
| Agent needs guided retry | Blind re-dispatch with same context | **Yes** |

### 3.2 Design options

| Criterion | A: No evaluator (.80) | B: Standalone evaluator (.65) | C: Close #681, simplify #682 (.85) |
|---|---|---|---|
| KISS | High — current design works | Low — new agent, new protocol | High — remove unrealized complexity |
| YAGNI | Aligned — pipeline handles quality | Risk of over-engineering | Aligned |
| Guided retry | Missing | Full Reflexion-style feedback | Missing (add to planner later if needed) |
| Latency | 0 extra LLM calls | +1 call per wave | 0 extra calls |
| Pipeline coverage | reviewer + auditor = 2 quality gates | + evaluator = 3 quality gates | reviewer + auditor = 2 quality gates |
| #682 compatibility | Current orchestrator works | Required by #682's 8-step design | Requires simplifying #682 |
| Context budget | Constant — agents move tasks, planner re-reads | Constant — evaluator is stateless | Constant |
| Implementation effort | None | New .agent.md + modify orchestrator | Simplify #682 to drop Steps 4-6 |

### 3.3 Key insight: where does value come from?

Conductor uses **4 specialized evaluators** (UI/UX, code quality, integration, business logic) — OwlBear's reviewer and auditor already fill these roles. The evaluator's unique value is **guided retry** (Reflexion pattern). But guided retry can be achieved by enhancing the planner's stale-task handling — passing failure context it already receives from the orchestrator — without a separate agent.

The OpenAI Agents SDK confirms the trend: no evaluator agent. Quality is handled by guardrails (pre/post validation) and structured handoffs. The framework's `Runner` handles routing mechanically, similar to OwlBear's re-plan loop.

## 4. Recommendation (.85 confidence)

**Option C: Close #681 as superseded. Simplify #682 to not require an evaluator.**

Rationale:

- The evaluator was designed to solve orchestrator context degradation. The current plan→dispatch→re-plan design already solves this — the orchestrator accumulates no context.
- Quality evaluation is the reviewer's and auditor's job. Adding a third evaluator violates DRY.
- Guided retry (the evaluator's unique value) is a minor enhancement to the planner's stale-task detection, not a new agent.
- #682's 8-step design was never committed. Simplifying it to match the current working design is less work than building an evaluator to satisfy a rewrite that doesn't exist.

**Risk:** If retry quality is poor (agents fail repeatedly with the same context), a guided-retry mechanism may be needed later. Mitigation: track this as a backlog item with concrete trigger criteria.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Simplify #682 AC: remove evaluator dependency (Steps 4-6)" --priority needed --status backlog --tags "scope:copilot,agent,phase-agent-arch" --body "The #682 orchestrator rewrite depends on an evaluator agent that was never created and is now deemed unnecessary. Simplify #682 AC to use the current plan->dispatch->re-plan model. Remove Steps 4 (Evaluate), 5 (Execute evaluator verdicts), 6 (Pipeline stage progression). Keep Steps 1-3, 7-8. See docs/research/evaluator-agent-revisited.md §4."

kanban\kanban-md.exe create "Add guided retry hints to planner stale-task detection" --priority nice-to-have --status backlog --tags "scope:copilot,agent" --body "When the planner detects a stale task (dispatched but unchanged), enhance the failure context to include a brief diagnostic hint from the task body's latest agent notes. This provides Reflexion-style verbal feedback without a separate evaluator agent. AC: (1) Planner reads task body for latest ## Notes section when task is stale, (2) Stale task BLOCKED reason includes 1-line hint from agent notes, (3) Orchestrator passes this hint in re-dispatch context. See docs/research/evaluator-agent-revisited.md §3.3."
```
