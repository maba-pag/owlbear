---
id: 558
title: Add dispatch-cycle trace ID to orchestrator protocol
status: ideation
priority: nice-to-have
created: 2026-03-30T21:37:56.9725911+02:00
updated: 2026-04-02T20:49:51.6934741+02:00
tags:
    - research
    - scope:agents
    - phase-2
blocked: true
block_reason: 'Duplicate of #434 -- dispatch-cycle trace ID already fully implemented (models, loop, log, tests). AC2 (Channel A/B embedding) is architecturally unsound.'
class: standard
---

## Context
Adopt deer-flow's trace ID propagation pattern: include a unique dispatch-cycle ID in the orchestrator's Channel A signal so parent-subagent work can be correlated for debugging.

See docs/research/deer-flow-adoptable-patterns.md S3C for analysis.

## Acceptance Criteria
- [ ] Orchestrator generates a unique cycle ID per dispatch wave
- [ ] Cycle ID included in Channel A signals and Channel B body sections
- [ ] Audit log entries reference the cycle ID for correlation

[[2026-04-02]] Thu 20:49
## Architecture Review
See docs/scratch/558-architect.md for full review.
