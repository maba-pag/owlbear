---
id: 1837
title: Review Decisions task reference open-task affordance
status: research
priority: important
created: 2026-05-24T12:32:00.730098+02:00
updated: 2026-05-24T12:32:00.730098+02:00
tags:
  - scope:cockpit-web
  - decisions
  - ux
  - navigation
  - discussion
parent: 1773
depends_on: []
ac:
  - Evaluate whether Decisions task references should open or preview the 
    associated task before resolution.
  - Any approved change preserves the current decision brief/resolver flow and 
    does not make resolution harder to scan.
  - Any approved change uses public Cockpit task-selection/navigation state 
    rather than private DOM or router internals.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The Decisions list and resolver display the associated task as `Task #...`, but the task reference is inert metadata rather than an open-task affordance. The decision card opens the resolver, and the resolver shows summary/options/metadata/full request, but none of the visible task-id surfaces acts as a task link or opens the task detail surface.

## Evidence
- Decision card screenshot: `.owlbear/scratch/1773-audit-continue/decisions-card-task-context.png`
- Resolver screenshot: `.owlbear/scratch/1773-audit-continue/decisions-resolver-task-context.png`
- Runtime report: `.owlbear/scratch/1773-audit-continue/decisions-task-context-report.json`
- Runtime facts: card and resolver both display `Task #1558`; `p-tag` task-id elements have no href, role, or click affordance; clicking task-id-like elements did not open/select task detail; the only visible action path is `Open resolver` / resolution controls.
- Code surface: `serve/cockpit/web/src/pages/DecisionsPage.tsx` renders `Task #{item.task_id}` as `PTag`; `serve/cockpit/web/src/components/ResolveModal.tsx` renders the task id in header tags and metadata values, not as a link/action.
- Historical context: archived #1688 required the decisions workflow to surface `task link, request type, options, recommendation, and consequences`; the current workflow surfaces task context but not an actual task link/open-task action.

## Observed User Impact
Decision requests are tied to work items. Before approving, rejecting, or asking for info, a user may need to inspect the underlying task's acceptance criteria, current status, dependencies, or recent task history. Today the decision workspace makes the resolver path obvious but requires the user to leave the workflow and locate the task manually if the decision body is insufficient.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The review should decide whether Decisions needs a direct open-task affordance, a stronger task context preview, or whether the full request body is intentionally sufficient.
