# Planner: askQuestions Approval by Default + Override Mechanism

> **Owning task:** #998 — Planner: askQuestions approval by default + override mechanism
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

When user invokes `@planner` directly, planner outputs a decomposition plan and exits. The user must re-invoke planner with "create now" to actually create tasks. During ideation #973, planner returned a 10-task plan, asked for approval in prose, then exited stateless — ideator had to create tasks manually.

**Question:** How should planner implement default approval-via-askQuestions for user-invoked mode, with an override for subagent/dispatched contexts?

**Sub-question (resolved):** Can stateless subagents use askQuestions? Answer: No reliable documentation supports it. The design must prevent askQuestions from firing in subagent context.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Custom Agents docs | code.visualstudio.com/docs/copilot/customization/custom-agents | 0.95 |
| 2 | VS Code Subagents docs | code.visualstudio.com/docs/copilot/agents/subagents | 0.95 |
| 3 | planner.agent.md (codebase) | share/agents/planner.agent.md | 1.0 |
| 4 | ideator.agent.md (codebase) | share/agents/ideator.agent.md | 0.90 |
| 5 | w-task-decomposition skill | share/skills/w-task-decomposition/SKILL.md | 0.90 |
| 6 | w-ideation skill (M6 handoff) | share/skills/w-ideation/SKILL.md | 0.85 |
| 7 | All 23 agent files — askQuestions audit | share/agents/*.agent.md | 0.80 |

## 3. Analysis

### Current State

- Only **ideator** has `vscode/askQuestions` (1 of 23 agents).
- Planner has two modes: user-invoked (output for review) vs dispatched (auto-create). Detection: "parent task ID in prompt."
- Planner callers: user (direct), ideator (M6 subagent), architect (decomposition delegation).
- VS Code subagents: autonomous, return final report. No documented support for askQuestions in subagent context.
- VS Code handoffs: agent-switching mechanism, not applicable here (breaks subagent model).

### #973 Root Cause

The existing planner already has "dispatched = auto-create" logic. It failed in #973 because ideator M6 invokes planner with `brief.md` reference — **no structured task ID** in the prompt. Planner couldn't detect dispatch context → defaulted to user-invoked (output-only) mode → exited without creating tasks.

### Option Comparison

| Criterion | A: Explicit mode prefix | B: Parent-ID detection (original) | C: Caller-mediated only |
|-----------|------------------------|----------------------------------|------------------------|
| Detection reliability | **High** — caller specifies mode | Low — NL inference of task ID | N/A — no detection |
| User-invoked UX | askQuestions approval | askQuestions approval | Output-only, re-invoke |
| Subagent safety | Safe — caller says "create" | Risky — if detection fails, askQuestions fires in subagent | Safe — no askQuestions |
| All callers covered | Yes — each caller uses prefix | Gaps — architect path unclear | Yes — but clunky |
| Complexity | Moderate — mode prefix + askQuestions | Moderate — same but fragile detection | Low — no changes |
| Fulfills AC | Yes | Yes | No — no askQuestions |
| KISS alignment | Good — explicit over implicit | Poor — magic detection | Best — minimal change |

### Explicit Mode Prefix Convention (Option A — recommended)

Planner recognizes two prompt prefixes:

| Prefix | Mode | Behavior |
|--------|------|----------|
| `Plan and create: #{id} — ...` | Dispatch | Claim task, auto-create subtasks, report Channel B |
| `Plan: ...` (default) | User | Present plan → askQuestions("Approve?") → create on approve |

**Caller responsibilities:**

| Caller | Prefix used | Rationale |
|--------|-------------|-----------|
| User (direct) | `Plan: {description}` | Gets approval checkpoint |
| Ideator M6 | `Plan and create: #{parent_id} — {brief}` | Brief already user-approved at M5 |
| Architect | `Plan and create: #{task_id} — {decomposition}` | Pipeline dispatch, no user present |
| Orchestrator | (does not invoke planner directly) | N/A |

**Fallback:** If planner can't determine mode from prompt, default to approval mode (safer to ask than to create unwanted tasks).

## 4. Recommendation

**Option A: Explicit mode prefix** — confidence: 0.80

Challenge: reconsider (0.45 on original). Challenger identified fragile NL-based parent-task-ID detection, unaddressed architect path, and undocumented askQuestions-in-subagent failure mode. Revised to use explicit caller-specified mode prefix instead of planner-side detection. All challenger concerns addressed:

- C1 (detection reliability): Caller specifies mode explicitly, not inferred.
- C2 (#973 root cause): Ideator M6 prompt lacked structured task reference. Fix: use "Plan and create: #{id}" prefix.
- C3 (override fragility): No NL keyword matching. Mode is in the prompt prefix.
- C4 (architect path): Documented in caller table above.

Residual risk: askQuestions in single-shot agent context is untested outside ideator. Mitigated by: planner is user-invocable, askQuestions is a standard tool, and the interaction (ask once → resume) is simpler than ideator's multi-turn pattern.

## 5. Follow-up Tasks

1. **planner.agent.md update** — Add `vscode/askQuestions` to tools. Document explicit mode prefix convention and both behaviors. Update execution mode section.
2. **w-task-decomposition skill update** — Add approval step between Step 5a (validate) and Step 6 (create). Conditional on user-invoked mode.
3. **ideator.agent.md + w-ideation M6 update** — Change planner invocation to use "Plan and create: #{parent_id}" prefix.
4. **architect.agent.md update** — Change planner delegation prompt to use "Plan and create: #{task_id}" prefix.
