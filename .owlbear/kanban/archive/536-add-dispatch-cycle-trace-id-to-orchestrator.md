---
id: 536
title: Add dispatch-cycle trace ID to orchestrator protocol
status: archived
priority: medium
created: 2026-03-30 21:37:56.972591+02:00
updated: 2026-04-02 10:12:57.805202+02:00
started: 2026-04-02 10:12:57.805202+02:00
completed: 2026-04-02 10:12:57.805202+02:00
tags:
- research
- scope:agents
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Adopt deer-flow's trace ID propagation pattern: include a unique dispatch-cycle ID in the orchestrator's Channel A signal so parent-subagent work can be correlated for debugging.

See docs/research/deer-flow-adoptable-patterns.md S3C for analysis.

## Acceptance Criteria
- [ ] Orchestrator generates a unique cycle ID per dispatch wave
- [ ] Cycle ID included in Channel A signals and Channel B body sections
- [ ] Audit log entries reference the cycle ID for correlation

[[2026-04-02]] Thu 10:12
## Architecture Review
**Verdict:** MERGE (delete as redundant)
**DR Verification:** docs/decisions/resolved/429-deer-flow-patterns-adoption.md approved: true (confirms dispatch trace ID already adopted via #434)

### AC Assessment
All 3 AC lines from #536 are fully covered by #434 (already in-progress, implementation committed):
- AC1 (cycle ID per wave): Implemented in run_loop() as uuid4().hex per cycle
- AC2 (Channel A/B inclusion): Research rejected this; audit-only approach adopted instead. No Channel A/B format changes.
- AC3 (audit log correlation): cycle_id field on DispatchEvent and CompletionEvent, AuditLog.query() filter

### Architecture Notes
Task #434 is the canonical implementation of the same scope. It went through full pipeline: architect approved, 34 tests written and passing, code committed (7892ea7), currently in review.

Decision request 429-deer-flow-patterns-adoption.md explicitly confirms: 'Already adopted from prior research: dispatch trace ID (#434)'.

#536 was created as a follow-up from deer-flow research (#386) before the more specific research (#434's doc at docs/research/dispatch-cycle-trace-id.md) refined the approach. #434 supersedes #536.

### Changes Made
- Deleted #536 as redundant (surviving task: #434, already in-progress)
