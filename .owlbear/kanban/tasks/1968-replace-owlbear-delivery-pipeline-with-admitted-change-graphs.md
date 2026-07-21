---
id: 1968
title: Replace OwlBear delivery pipeline with admitted change graphs
status: shape
priority: high
created: 2026-07-21T01:46:53.257501+02:00
updated: 2026-07-21T18:33:04.396222+02:00
tags:
  - pipeline-redesign
  - architecture
  - scope:core
parent:
depends_on:
  - 1975
  - 1976
ac:
  - The bootstrap native change package records the approved intent, 
    architecture decisions, complete delivery-node graph, admission 
    requirements, atomic migration, and end-to-end replay proof before 
    implementation decomposition.
  - The implementation cutover removes OpenSpec and the current 
    shape/build/verify/collect task-authoritative path while preserving the 
    healthy capabilities enumerated in the planning-workflow authority.
  - The replacement rejects all four historical defective plans before Kanban 
    execution and accepts their corrected forms through executable scenario 
    tests.
blocked: false
block_reason:
claimed_at: 2026-07-21T16:55:26.897374+02:00
archival_reason:
archival_refs: []
---
## Objective
Replace the OpenSpec and task-authoritative planning pipeline with the native, graph-authoritative delivery control plane defined by `.owlbear/research/planning-workflow-root-cause-and-redesign.md` and the user decisions recorded on 2026-07-21.

## Scope
This is the bootstrap intake for an atomic cutover. The durable native change package will own intent, design, decisions, and the complete delivery-node graph. Do not decompose this intake into implementation tasks until that package is complete, independently challenged, and explicitly admitted.

## Required outcome
- Native four-file change authority replaces OpenSpec.
- Global delivery graph is complete before Kanban execution.
- Each delivery node is shaped once into outcome-cohesive build packets.
- Kanban jobs have purpose-specific statuses: shape, build, accept, audit.
- Builders use an inline read-only review loop; acceptors and auditors remain independent and cannot edit tracked files.
- Corrective work is append-only through new jobs and superseding receipts.
- Shared-worktree writes are serialized by orchestration.
- Existing pipeline, OpenSpec integration, and legacy behavior are removed in the same atomic cutover.

## Planning authority
`.owlbear/research/planning-workflow-root-cause-and-redesign.md`