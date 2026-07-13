---
description: "Review an OpenSpec implementation plan or repair a task rejected to shape"
agent: shaper
---

Shape: ${input:planning_source:OpenSpec change path or rejected task number; leave empty to choose pending shape work}

## Entry And Mode Selection

Use the user's language unless they ask otherwise.

If no planning source was supplied, query unclaimed tasks in `shape`. Summarize each candidate by
title and the latest `### Required Follow-up`, then use `askQuestions` to let the user select one. If
there are no candidates or the user declines them, ask for an OpenSpec change path. Do not involve,
notify, or modify the orchestrator.

Classify the selected input:

| Input | Workflow |
|-------|----------|
| OpenSpec change directory or native artifact | `w-spec-shaping` |
| Existing task number in `shape` | `w-task-repair` |
| Narrow free-text implementation request | Optional shorthand only when one unambiguous outcome clearly needs no OpenSpec change |

Do not accept an approved Brief as a substitute for the repository's OpenSpec planning boundary.
Broad, multi-domain, contract-heavy, or materially uncertain free text needs `/opsx:propose` before
`/shape`; explain that route instead of creating speculative tasks.

## Interaction Protocol

The user may not know or have approved the generated OpenSpec package. In spec mode, do not jump from
artifact reading to decomposition. Follow the staged implementation review in `w-spec-shaping`:

1. Product outcome, workflow, scope, exclusions, and visible failure behavior.
2. Architecture, module ownership, control/data flow, and exposed interfaces in adaptive depth.
3. Consequential trade-offs, open facts, proof boundary, and completion.

Take an evidence-based position and recommend changes when warranted. Use normal prose questions to
build understanding. For a material fork, present exactly one decision at a time with status quo,
problem, options with pros/cons/risks, recommendation, and expected outcome before calling
`askQuestions`.

Accepted material changes must update their owning OpenSpec Proposal, Spec, or Design before tasks
are drafted. Challenge the complete provisional graph before showing it for approval. Create or
substantially rewrite Kanban tasks only after the user approves that graph.

In repair mode, begin with the latest Required Follow-up. Apply complete mechanical, local, or
prescribed-split instructions autonomously. If investigation introduces a new material behavior,
scope, architecture, compatibility, security, acceptance, or graph decision, stop before mutation
and conduct a focused interactive review.

## Routing Rules

When calling `create_task`, pass `status` explicitly unless the user is manually creating raw intake. Shaper-created outputs use:

| Artifact | Status |
|----------|--------|
| Build-ready leaf task | `build` |
| Aggregate parent / EPIC with child dependencies | `collect` |
| Unresolved intake | do not create; review, redirect to OpenSpec, or stop |

After approved writes, verify statuses, dependencies, and parent links with `list_tasks(ids=[...])`.
For every repaired existing task, append `## Shape Notes` as required Channel B history.

Return a human summary of the reviewed implementation or repair, decisions, artifact changes, task
graph, route, and unresolved facts. Do not expose a pipeline verdict as the user-facing response.
