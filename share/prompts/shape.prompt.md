---
description: "Start the user-facing shaper for a shape task or simple idea"
agent: shaper
---

Shape: ${input:task_or_idea:Task number or simple idea — e.g. '#123' or 'make Cockpit request handling less noisy'}

## Interaction Protocol

Use the user's language unless they ask otherwise. When shaping requires a real product, architecture, scope, or trade-off decision, present exactly one decision item before calling `askQuestions`.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## Input Modes

- If the input is a task number, shape that existing task.
- If the input is a simple idea, shape it directly into routed task artifacts. Do not create a temporary `shape` staging task.

## What Happens

1. The shaper turns intent into build-ready scope and acceptance criteria.
2. When local context is insufficient, the shaper runs source-grounded research and records it in Shape Notes or `.owlbear/research/`.
3. Important user choices are discussed through `askQuestions` before approval or blocking.
4. Over-broad work may be decomposed by shaper, with build-ready leaf tasks created in `build` and aggregate parents/EPICs created or parked in `collect` behind child dependencies.
5. Approved existing tasks move to `build` or `collect`; unresolved existing tasks stay in `shape` or become blocked through `create_request`. For free-text ideas that remain unresolved after live clarification, stop without creating board artifacts.

## Routing Rules

When calling `create_task`, pass `status` explicitly unless the user is manually creating raw intake. Shaper-created outputs use:

| Artifact | Status |
|----------|--------|
| Build-ready leaf task | `build` |
| Aggregate parent / EPIC with child dependencies | `collect` |
| Raw unresolved intake | do not create; ask/refine or stop |

After creating tasks, verify their statuses with `list_tasks(ids=[...])` before returning.
