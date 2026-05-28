---
id: 1904
title: 'Knowledge: Implement SourceFetcher adapter and migrate refresh to IngestCoordinator
  (Phase B2b)'
status: backlog
priority: needed
created: 2026-05-27T23:24:10.601235+02:00
updated: 2026-05-28T04:49:39.677778+02:00
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
blocked: true
block_reason: 'Gated on child #1911 completion — depends_on now enforces mechanically.
  Unblock when #1911 is archived.'
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
- #1909 — CompositeSourceFetcher adapter (archived ✓)
- #1910 — IngestCoordinator error propagation (archived ✓)
- #1911 — MCP server wiring (backlog — BLOCKING)

## Completion Gate
This parent advances ONLY when #1911 reaches archived status. The `depends_on` field enforces this mechanically — no static status table maintained (previous tables drifted and caused 2 reviewer rejections).

[[2026-05-28T04:49:39+02:00]]
## Architecture Review (3rd pass — structural fix after 2 reviewer rejections)

### Problem
Parent coordination shell kept advancing through pipeline (test-writer, builder pass-through due to `ac: []`) before child #1911 completed. Static status table drifted on every cycle, causing reviewer to reject twice.

### Resolution
1. Added #1911 to `depends_on` — mechanical gate prevents advancement while child is incomplete
2. Removed drifting static status table from body (root cause of Finding #2)
3. Replaced with explicit Completion Gate section referencing `depends_on` as enforcement mechanism
4. Blocked task until #1911 archives

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Coordination container only |
| Interface clarity | PASS | Gate now mechanically enforced via depends_on |
| Dependency correctness | PASS | depends_on=[1900 (archived), 1911 (blocking)] |
| KISS/YAGNI | PASS | No abstractions — pure parent grouping with dep gate |
| Pattern consistency | PASS | Standard parent-shell pattern, now with mechanical enforcement |

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Verdict: BLOCK
### Action Taken: Added #1911 to depends_on for mechanical gating. Rewrote body to remove drifting static table. Blocked until #1911 archives. When unblocked, task can flow through pipeline to completion.
