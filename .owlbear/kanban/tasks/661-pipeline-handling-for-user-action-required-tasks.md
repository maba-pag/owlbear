---
id: 661
title: Pipeline handling for user-action-required tasks
status: research
priority: nice-to-have
created: 2026-04-06T08:25:07.1782653+02:00
updated: 2026-04-06T15:11:00.543308+02:00
tags:
    - phase-3
    - scope:orchestrator
    - type:feature
claimed_by: flare-zone
claimed_at: 2026-04-06T15:11:00.543308+02:00
class: standard
---

## Objective
Design a mechanism for tasks that require manual user action (GUI verification, external approvals, etc.) to avoid futile pipeline pass-through cycles.

## Context
Task #597 proved the gap empirically: 6 pipeline agents correctly processed it as a type:test pass-through, but the objective (manual Teams GUI verification) was never fulfilled. The auditor rejected at .88 confidence, and the architect confirmed re-entering the pipeline would repeat the cycle verbatim.

Current workaround: architect rejects to ideation with a note recommending direct user execution. This works but is wasteful (full pipeline cycle before detection).

## Acceptance Criteria
- [ ] Define a convention for user-action-required tasks (tag, status, or dedicated handoff mechanism)
- [ ] Architect can identify and route these tasks early (skip test-writer/builder/reviewer)
- [ ] Orchestrator recognizes the convention and does not dispatch to automated agents
- [ ] Document the convention in agent-common.instructions.md or r-pipeline-protocol
- [ ] Verify with a dry-run scenario that the convention prevents the #597-style loop

## Evidence
- #597 pipeline cycle: all 6 agents passed through, auditor rejected, architect confirmed structural gap
- Auditor note: "The pipeline lacks a mechanism for user-action-required tasks"
- Architect (cycle 2): "No pipeline pattern exists for user-action-required tasks"

## Needs decomposition: multiple pipeline components affected (orchestrator, architect, agents-common, kanban-md config)
