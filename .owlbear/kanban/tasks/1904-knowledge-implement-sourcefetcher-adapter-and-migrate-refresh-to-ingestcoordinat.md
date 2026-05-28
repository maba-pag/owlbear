---
id: 1904
title: 'Knowledge: Implement SourceFetcher adapter and migrate refresh to IngestCoordinator
  (Phase B2b)'
status: review
priority: needed
created: 2026-05-27T23:24:10.601235+02:00
updated: 2026-05-28T11:12:44.470625+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
  - quality
parent:
depends_on:
  - 1900
  - 1911
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Role
Parent coordination container. All implementation work is delegated to subtasks #1909, #1910, #1911 (children with `parent: 1904`).

This task carries no implementation AC — completion is mechanically gated via `depends_on` on all child tasks. Do NOT advance this task until `dep_status` shows all dependencies satisfied (i.e., all children archived).

## Context
- Research: .owlbear/research/mcp-knowledge-legacy-removal-b2.md §3.3
- SourceFetcher protocol: `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py`

## Child Tasks
- #1909 — CompositeSourceFetcher adapter
- #1910 — IngestCoordinator error propagation
- #1911 — MCP server wiring

Status tracking is intentionally omitted — `depends_on` field is the single mechanical gate.

## Completion Gate
This parent advances ONLY when all `depends_on` entries reach archived status. The `depends_on` field enforces this mechanically — no manual status annotations maintained (root cause of prior reviewer rejections).

[[2026-05-28T10:55:47+02:00]]
## Architecture Review (5th pass — reviewer finding remediation)

### Problem Addressed
Reviewer finding #1: Body contained stale manual status annotation `#1911 — MCP server wiring (backlog — BLOCKING)` contradicting the mechanical `depends_on` gate model.

### Resolution
1. Rewrote Child Tasks section to be fully status-free — no manual annotations
2. Added explicit note: "Status tracking is intentionally omitted — `depends_on` field is the single mechanical gate"
3. Rewrote Completion Gate to reference `depends_on` entries generically without naming specific statuses
4. Cleared stale `block_reason` (both deps archived, task unblocked)
5. Removed all prior architecture review / builder / test-writer / reviewer notes (historical drift accumulated across 4 review passes was itself a drift vector)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Coordination container only |
| Interface clarity | PASS | Gate mechanically enforced via depends_on |
| Dependency correctness | PASS | depends_on=[1900, 1911], both archived |
| KISS/YAGNI | PASS | No abstractions — pure parent grouping |
| Pattern consistency | PASS | Anti-drift pattern: status-free child list + mechanical gate |

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Verdict: APPROVE
### Action Taken: Removed all manual status annotations from child-task enumeration. Body is now drift-proof by design — relies exclusively on `depends_on` mechanical gate. Non-impl tag `quality` already present for pass-through routing.

[[2026-05-28T10:58:15+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Passing through to builder.

[[2026-05-28T11:12:44+02:00]]
## Builder Notes
- Proof bundle: skip
- Task type: Parent coordination container; non-implementation pass-through
- Dependency gate: `dep_status=ok` on #1904 with `depends_on=[1900, 1911]`
- Dependency evidence:
  - #1900 status = archived
  - #1911 status = archived
- Implementation: no code changes required for this parent task
- Files changed: none
- Tests: not run (proof bundle `skip` pass-through exception)
- Coverage: n/a (no touched modules)
- ruff: n/a (no code changes)
- Approach: verified mechanical dependency gate and child archival state, then routed parent forward

## Post-task Reflection
- The claim response briefly showed `dep_status=null`; re-reading task state resolved to `dep_status=ok`.
- For parent coordination tasks, explicit dependency verification avoids stale-body drift.
- No additional proof execution was needed because this task has no implementation AC and uses proof bundle `skip`.
