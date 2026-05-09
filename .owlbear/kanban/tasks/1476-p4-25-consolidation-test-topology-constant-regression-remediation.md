---
id: 1476
title: 'P4-25: consolidation test: topology-constant regression remediation'
status: backlog
priority: critical
created: 2026-05-09T08:46:53.962568+00:00
updated: 2026-05-09T08:48:11.351067+00:00
tags:
- phase-4
- type:test
- scope:tests
- topology
- consolidation-test
parent: 1439
depends_on:
- 1472
- 1473
- 1474
- 1475
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Context
Parent #1439 AC5 regression gate. All 4 category subtasks (#1472 Cat-A, #1473 Cat-B1, #1474 Cat-B2, #1475 Cat-C) must pass before this consolidation gate runs.

## Scope
In scope: full test suite verification.
Out of scope: any test modifications (those are done by the category subtasks).

## Acceptance Criteria
1. `uv run pytest` exits 0 with no new failures introduced by the topology-constant refactor. The full test suite passes end-to-end. (td:2)

## Verification Method
Run the complete test suite and confirm zero failures. Any remaining failures must be triaged as either pre-existing (not introduced by #1439) or as missed remediation requiring a follow-up task.
