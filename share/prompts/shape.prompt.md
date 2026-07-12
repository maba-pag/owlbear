---
description: "Start the user-facing shaper for an OpenSpec change, approved Brief, shape task, or simple idea"
agent: shaper
---

Shape: ${input:planning_source:Task number, OpenSpec change path, approved Brief path, or simple idea}

## Interaction Protocol

Use the user's language unless they ask otherwise. When shaping requires a real product, architecture, scope, or trade-off decision, present exactly one decision item before calling `askQuestions`.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## Input Modes

- If the input is a task number, shape that existing task.
- If the input is an OpenSpec change directory or one of its native artifacts, resolve the change
 through `openspec status --change <name> --json`, then read every existing `proposal`, `specs`,
 `design`, and `tasks` path reported by the CLI. Do not assume paths from the stock schema.
- If the input is an approved `brief.md` path, read the Brief and its sibling `decisions.md` before
 task creation when that sibling exists. Apply the planning-readiness gate, contract authority
 guard, and product invariant map.
- If the input is a simple idea, shape it directly into routed task artifacts. Do not create a temporary `shape` staging task.

## What Happens

1. The shaper classifies planning authority before decomposition. For native OpenSpec, Proposal owns
 product intent and material user decisions; Specs own normative behavior; Design owns verified
 technical decisions; Tasks are advisory suggestions only.
2. The shaper confirms product invocation, existing-system fit and authorities, normal-path proof,
 and the completion/change contract before decomposition.
3. The shaper records load-bearing contract claims and maps each product invariant to one owning task
 and one normal-path proof.
4. When local context is insufficient, the shaper runs source-grounded research and records it in Shape Notes or `.owlbear/research/`.
5. Important user choices are discussed through `askQuestions` before approval or blocking.
6. The shaper treats OpenSpec Tasks as recommendations, then writes final Kanban scope, acceptance
 criteria, dependencies, priorities, tags, proof guidance, and aggregate routing.
7. Over-broad work may be decomposed by shaper, with build-ready leaf tasks created in `build` and aggregate parents/EPICs created or parked in `collect` behind child dependencies.
8. For OpenSpec Proposals or approved Briefs with a confirmed Shared or Production investment tier,
 concrete tasks receive a post-shaping expectation-fidelity check before approval. Do not infer a
 tier when the planning source does not establish one.
9. Approved existing tasks move to `build` or `collect`; unresolved existing tasks stay in `shape` or become blocked through `create_request`. For free-text ideas that remain unresolved after live clarification, stop without creating board artifacts.

## Routing Rules

When calling `create_task`, pass `status` explicitly unless the user is manually creating raw intake. Shaper-created outputs use:

| Artifact | Status |
|----------|--------|
| Build-ready leaf task | `build` |
| Aggregate parent / EPIC with child dependencies | `collect` |
| Raw unresolved intake | do not create; ask/refine or stop |

After creating tasks, verify their statuses with `list_tasks(ids=[...])` before returning.
