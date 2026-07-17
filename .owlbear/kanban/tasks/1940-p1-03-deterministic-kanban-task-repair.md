---
id: 1940
title: 'P1-03: Deterministic Kanban task repair'
status: build
priority: medium
created: 2026-07-17T02:32:03.458344+02:00
updated: 2026-07-17T02:33:38.486366+02:00
tags:
  - phase-1
  - scope:kanban
  - repair
  - data-safety
parent: 1945
depends_on:
  - 1937
ac:
  - Given the eight complete-set classes in the task's Repair Matrix, repair 
    handles (a) by deleting active copies and retaining the deterministic 
    archive copy, (b) by retaining the canonical copy and deleting peers, and 
    (c) by retaining the unique-largest body and quarantining smaller peers; 
    classes (d)-(h) remain unchanged and unresolved.
  - Given a conflict-free archived-state task located only in active storage, 
    repair moves it active-to-archive using no-overwrite behavior; given an 
    archive destination conflict, changed candidate after discovery, or 
    delete/move/quarantine failure, repair revalidates before mutation, routes 
    the conflict through the complete duplicate matrix or records 
    skipped/failed, and never claims an unapplied mutation succeeded.
  - When repair returns, its response contains start/completion times, 
    removed/moved/quarantined/skipped/failed/unresolved outcomes, and a 
    task-health result observed after item processing; repeating repair causes 
    no further mutation for resolved conditions.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Provide convergent task repair that applies the approved complete-set duplicate and archive-reconciliation rules, preserves ambiguous records, and returns post-repair health evidence.

## Scope
In scope: Kanban repair classification, delete/move/quarantine operations, revalidation, terminal outcomes, and the post-operation task scan. Out of scope: claims, activity maintenance, HTTP orchestration, per-file client choices, ID renumbering, and global transaction guarantees.

## Repair Matrix
The exhaustive complete-set fixtures for AC1 are:

- (a) semantically identical archived cross-directory copies;
- (b) semantically identical same-directory copies;
- (c) same-directory identical normalized frontmatter with one unique largest normalized body;
- (d) tied-largest bodies;
- (e) differing normalized frontmatter;
- (f) semantically identical but non-archived cross-directory copies;
- (g) non-semantically-identical cross-directory copies;
- (h) a heterogeneous complete set not wholly matching one rule.

For class (b), canonical means the generated-name record when present, otherwise the lexicographically first path.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, especially the accepted complete duplicate-set matrix and filesystem concurrency design. Read-only evidence comes from dependency #1937.

## Proof Guidance
Use a focused real-filesystem Kanban data-safety behavior check plus a downstream-impact scan. This is a data-loss-sensitive path; retain or add durable regression coverage for matrix classification, no-overwrite/revalidation, and convergence when existing coverage is insufficient.