# w-task-decomposition: Conditional Approval Step

> **Owning task:** #1006 — w-task-decomposition: add conditional approval step for user-invoked mode
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

The `w-task-decomposition` skill has no approval gate between plan validation (Step 5a) and task creation (Step 6). When planner runs in user-invoked mode (`Plan:` prefix), it needs to present the plan and ask for approval before creating tasks. This was identified in the parent task #998 research and the architecture review specifies the behavior.

**Dependency:** #1005 (archived/done) established the explicit prefix convention in `planner.agent.md`. This task brings `w-task-decomposition/SKILL.md` into alignment.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `share/skills/w-task-decomposition/SKILL.md` | Codebase | 1.0 |
| 2 | `share/agents/planner.agent.md` (post-#1005) | Codebase | 1.0 |
| 3 | `share/skills/w-ideation/SKILL.md` (M5 approval pattern) | Codebase | 0.85 |
| 4 | `.owlbear/research/998-planner-askquestions-approval.md` | Codebase | 0.90 |
| 5 | #998 architecture review (task body) | Codebase | 0.95 |

## 3. Analysis

### Current State

**Step 0** describes execution mode using "parent task ID provided" as the detection mechanism:
- Dispatched → auto-create
- User-invoked → "output planned tasks for review — do NOT execute them"

**Problem 1:** The detection mechanism is outdated. #1005 replaced NL-based parent-ID detection with explicit prefix convention (`Plan and create:` vs `Plan:`). Step 0 should reference the prefix convention.

**Problem 2:** User-invoked mode says "do NOT execute them" — but the new behavior is "present → approve → create." The skill currently makes user-invoked mode output-only with no path to creation.

**Step 5a** validates planned tasks. **Step 6** creates tasks. There's nothing between them that gates creation on user approval.

### What Needs to Change

| Location | Current | Required |
|----------|---------|----------|
| Step 0 — Execution mode | "parent task ID provided" detection | Reference prefix convention from planner.agent.md |
| Step 0 — User-invoked behavior | "output for review — do NOT execute" | "present plan → askQuestions approval → create on approve" |
| New Step 5b | Does not exist | Conditional approval gate (user mode only) |
| Step 6 — Preamble | Unconditional creation | Implicit: only reached after 5b approval (user) or directly (dispatch) |

### Approval Pattern (from ideator prior art)

The ideator M5 Brief approval uses structured options: approve / adjust / rework. For task decomposition, the interaction is simpler — the user either approves the full breakdown or rejects it. An "adjust" option adds complexity without clear value: the user can reject and re-invoke with different instructions.

**Recommended approval options:** `Approve` / `Reject`. Two options, no freeform — keeps the interaction crisp.

### Presentation Before Approval

Per the ideator convention (and user memory note): always present content inline before calling askQuestions. Step 5b should present the task table and dependency graph in the chat message, then call askQuestions for the binary approve/reject choice.

## 4. Recommendation

**Implement all four changes from the table in §3** — confidence: 0.90

This is a well-scoped skill file edit. The behavior is fully specified by the parent #998 architecture review and demonstrated in planner.agent.md examples. No ambiguity in the implementation.

Challenge: skipped (trivial — behavior already fully specified in architecture review and demonstrated in planner.agent.md).

### Specific Step 5b Wording

Add between Step 5a and Step 6:

> **Step 5b — Approval (user mode only)**
>
> Skip this step in dispatch mode (`Plan and create:` prefix).
>
> Present the planned task breakdown inline:
> - Task list table (title, priority, dependencies, tags)
> - Dependency graph (Mermaid)
> - Summary: total count, dependency layers, phase
>
> Call `askQuestions` with two options:
> - "Approve — create all {N} tasks"
> - "Reject — cancel without creating tasks"
>
> **On approve:** proceed to Step 6.
> **On reject:** stop. Report cancellation. Do not create tasks or advance the parent.

### Step 0 Update

Replace execution mode paragraph with:

> **Execution mode** (determined by caller — see `planner.agent.md` prefix convention):
> - **Dispatch mode** (`Plan and create:` prefix): claim parent task, execute `create_task` calls directly, report created IDs.
> - **User mode** (`Plan:` prefix or no prefix): present plan for review → askQuestions approval (Step 5b) → create on approve.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #1006 itself is the implementation task — it advances to backlog for the builder to execute the changes specified here.
