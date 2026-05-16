---
id: 1599
title: 'P1-06: Tests — computeSignal unknown state'
status: backlog
priority: important
created: 2026-05-16T03:35:25.284760+00:00
updated: 2026-05-16T04:22:52.183268+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on: []
ac:
  - Test asserts computeSignal(null, pendingDRIds) and computeSignal({} as 
    SignalInput, pendingDRIds) return 'unknown'
  - Test asserts existing 5-state behavior unchanged for valid inputs 
    (dr-pending, blocked, claimed, deps-unmet, ready)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for computeSignal unknown state extension.
Out of scope: Implementation, formatting utilities, token migration.

2026-05-16T04:22:00+00:00


## Research
- AC-1 corrected: function returns a string, not an object; brief confirms `\"unknown\"` state string
- AC-2 corrected: actual 5 states are dr-pending/blocked/claimed/deps-unmet/ready (not green/yellow/red/gray/stale)
- Research doc: .owlbear/research/compute-signal-unknown-state.md
- Sources: 2 studied (brief + codebase), 2 high-relevance
- Recommendation: extend CardSignal union type + guard clause (confidence: 0.90)

[[2026-05-16T06:22:52+02:00]]
## Research
- Research doc: .owlbear/research/compute-signal-unknown-state.md
- Sources: 4 studied (impl, brief, existing tests, stance doc), 4 high-relevance
- Corrected both ACs: (1) function returns string not object, (2) actual state names not color names
- Recommendation: extend CardSignal union + guard clause (confidence: 0.90)
- Challenge: skipped (trivial scope)
- No new follow-up tasks — impl task #1605 already exists
- Commit: 5c9736bc
