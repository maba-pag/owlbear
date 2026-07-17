---
id: 1937
title: 'P1-01: Kanban task and graph health evidence'
status: build
priority: high
created: 2026-07-17T02:31:31.385612+02:00
updated: 2026-07-17T02:33:38.572513+02:00
tags:
  - phase-1
  - scope:kanban
  - integrity
parent: 1945
depends_on: []
ac:
  - Given active/archive fixtures containing one readable task with two 
    independently detectable persisted-field defects and one unreadable task, 
    the Kanban task-health public method returns both readable-file findings 
    plus the read failure and leaves file paths, bytes, and mtimes unchanged.
  - Given same-ID fixtures within tasks, within archive, across both 
    directories, and a heterogeneous three-record set, the public method returns
    the complete path set and a repairable or unresolved classification for each
    ID without pairwise mutation.
  - Given missing parent/dependency/archival targets, dependency self-reference,
    a multi-task dependency cycle, and a well-formed task whose persisted state 
    is archived but whose record exists only in active storage with no archive 
    destination conflict, the public method returns findings naming the owner 
    and field or cycle involved; the location finding names the task ID and 
    active/archive locations; storage remains unchanged.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Provide read-only normalized task evidence for persisted-file defects, complete duplicate-ID sets, location drift, broken references, self-reference, and dependency cycles.

## Scope
In scope: Kanban task-health models, scanner behavior, and the public engine health method. Out of scope: request diagnostics, storage mutation, claim maintenance, and Cockpit HTTP/UI behavior.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the workspace-health spec and accepted design.

## Proof Guidance
Use a focused real-filesystem Kanban behavior check plus a downstream-impact scan. Because this is shared integrity behavior, retain or add durable regression coverage only where it protects the multi-finding, complete-set, or graph-analysis boundary.