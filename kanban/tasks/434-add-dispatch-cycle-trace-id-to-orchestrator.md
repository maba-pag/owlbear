---
id: 434
title: Add dispatch-cycle trace ID to orchestrator protocol
status: backlog
priority: nice-to-have
created: 2026-03-30T21:37:56.9725911+02:00
updated: 2026-03-30T23:47:48.6227623+02:00
tags:
    - research
    - scope:agents
    - phase-2
class: standard
---

## Context
Adopt deer-flow's trace ID propagation pattern: include a unique dispatch-cycle ID in the orchestrator's Channel A signal so parent-subagent work can be correlated for debugging.

See docs/research/deer-flow-adoptable-patterns.md S3C for analysis.

## Acceptance Criteria
- [ ] Orchestrator generates a unique cycle ID per dispatch wave
- [ ] Cycle ID included in Channel A signals and Channel B body sections
- [ ] Audit log entries reference the cycle ID for correlation
