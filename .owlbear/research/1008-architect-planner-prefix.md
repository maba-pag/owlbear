# Architect: Update Planner Delegation to Use Structured Prefix

> **Owning task:** #1008 — Architect: update planner delegation to use structured prefix
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

Architect delegates to planner when a task body contains `Needs decomposition:`, but the delegation prompt uses `Plan: {feature description from task body}` — the user-mode prefix. This triggers planner's askQuestions approval flow in a subagent context where no user can respond, causing a pipeline stall.

**Question:** What specific edits are needed to make architect's planner delegation use the `Plan and create: #{task_id}` prefix convention already implemented in planner (#1005)?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | planner.agent.md (codebase) — three-tier prefix detection implemented by #1005 | 1.0 |
| 2 | architect.agent.md (codebase) — subagents table line 67, decomposition rule | 1.0 |
| 3 | .owlbear/research/998-planner-askquestions-approval.md — parent research | 0.95 |
| 4 | .owlbear/research/1007-ideator-planner-prefix.md — sibling task, same pattern | 0.90 |

## 3. Analysis

### Current State (2 gaps)

| Location | Current Text | Problem |
|----------|-------------|---------|
| architect.agent.md subagents table | `` `Plan: {feature description from task body}` `` | Uses user-mode prefix — triggers askQuestions in subagent context |
| architect.agent.md critical_rules "Decomposition detection" | "delegate to the **planner** agent immediately" | No mention of prefix or passing claimed task ID |

### Planner Side (already done — #1005)

Planner recognises `Plan and create: #{id} — ...` → dispatch mode (auto-create, no askQuestions). Tier 3 compatibility fallback explicitly references #1008 for caller adoption.

### Required Edits

| File | Section | Change |
|------|---------|--------|
| architect.agent.md | Subagents table, planner row | `` `Plan: {feature description from task body}` `` → `` `Plan and create: #{task_id} — {feature description from task body}` `` |
| architect.agent.md | critical_rules "Decomposition detection" | Add: use `Plan and create: #{task_id}` prefix when delegating (architect holds the claimed task ID from `start_work`) |

No other files affected. The `w-arch-review` skill references planner delegation but defers to the agent file for the prompt format.

### Architecture Review Bindings (from #998)

The #998 architecture review established two constraints binding on this task:
- **Fallback refinement (C1):** Planner-side fallback already context-aware (implemented in #1005). Architect caller adopting the explicit prefix satisfies this.
- **Atomicity note:** All #998 children (#1005–#1008) must ship together before sync-to-main. #1005 is complete; #1007 and #1008 are the remaining caller-side updates.

## 4. Recommendation

**Apply the two edits above.** Confidence: 0.95.

The convention is designed, validated, and implemented on the receiving end (planner). This is pure caller-side adoption. The architect dispatches planner in a subagent context — dispatch mode (no askQuestions) is the only correct behavior.

Challenge: skipped — trivial prescribed change, single approach, no trade-offs. Identical pattern to sibling #1007 (also skipped challenge).

## 5. Follow-up Tasks

None required — task #1008 already has implementation ACs. Advance to backlog for builder execution.

Once #1007 and #1008 are both complete, the planner's Tier 3 compatibility fallback comment can be removed (noted in planner.agent.md line 41).
