# Ideator M6 + w-ideation: Structured Planner Dispatch Prefix

> **Owning task:** #1007 — Ideator M6 + w-ideation: use structured planner dispatch prefix
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

Ideator M6 invokes planner with `brief.md` reference but no structured task ID or mode prefix. This caused the #973 failure: planner couldn't detect dispatch context → defaulted to user-invoked (output-only) mode → exited without creating tasks.

**Question:** What specific edits are needed to make ideator's M6 handoff use the `Plan and create: #{parent_id}` prefix convention already implemented in planner?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | planner.agent.md (codebase) — three-tier prefix detection already implemented | 1.0 |
| 2 | ideator.agent.md (codebase) — subagents table shows `Plan: {brief content summary}` | 1.0 |
| 3 | w-ideation SKILL.md (codebase) — Step 6 says "invoke planner with `brief.md` reference" | 1.0 |
| 4 | .owlbear/research/998-planner-askquestions-approval.md — parent research | 0.95 |

## 3. Analysis

### Current State (3 gaps)

| Location | Current Text | Problem |
|----------|-------------|---------|
| ideator.agent.md subagents table | `Plan: {brief content summary}` | Uses user mode prefix — triggers askQuestions in subagent context |
| ideator.agent.md critical_rules "Surgical handoff" | "invoke planner for subtask decomposition" | No mention of prefix or passing parent task ID |
| w-ideation Step 6 item 1 | "Invoke the **planner** subagent with `brief.md` reference" | No parent task creation step, no structured prefix |

### Planner Side (already done — #1005)

Planner recognises `Plan and create: #{id} — ...` → dispatch mode (auto-create, no askQuestions). Compatibility fallback notes tasks #1007/#1008 for caller adoption.

### Required Edits

| File | Section | Change |
|------|---------|--------|
| ideator.agent.md | Subagents table, planner row | `Plan: {brief content summary}` → `Plan and create: #{parent_id} — {brief summary}` |
| ideator.agent.md | critical_rules "Surgical handoff" | Add: pass parent task ID to planner via `Plan and create: #{id}` prefix |
| w-ideation SKILL.md | Step 6, items 1–2 | Split into: (1) create parent kanban task, (2) invoke planner with `Plan and create: #{parent_id} — {brief summary}` |

No other files affected. The Pipeline Handoff section in w-ideation (line ~260) already mentions the parent task concept but doesn't prescribe the prefix — no update needed there since Step 6 is the procedural authority.

## 4. Recommendation

**Apply the three edits above.** Confidence: 0.95.

Rationale: The convention is already designed, validated, and implemented on the receiving end (planner). This is pure caller-side adoption with zero ambiguity. The Brief is already user-approved at M5 — dispatch mode is correct (no double-approval needed).

Challenge: skipped — trivial prescribed change, single approach, no trade-offs.

## 5. Follow-up Tasks

None required — task #1007 already has implementation ACs. Advance to backlog for builder execution.

Sibling task #1008 covers the architect caller path separately.
