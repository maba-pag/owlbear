---
id: 560
title: Add dispatch-cycle trace ID to orchestrator protocol
status: archived
priority: medium
created: 2026-03-30 21:37:56.972591+02:00
updated: 2026-04-04 07:10:04.134980+02:00
started: 2026-04-04 07:09:38.464512+02:00
completed: 2026-04-04 07:09:38.464512+02:00
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

[[2026-04-03]] Fri 00:27
## Architecture Review
**Verdict:** BLOCK (duplicate)
**DR Verification:** N/A -- capability already delivered by #434

### AC Assessment
AC Line 1 (cycle ID per dispatch wave): Already implemented in loop.py run_loop() via uuid4().hex -- delivered by #434
AC Line 2 (Channel A/B signals): Explicitly rejected during #434 arch review -- Channel A is write-only diagnostic, orchestrator never parses it. Protocol design conflict.
AC Line 3 (audit log correlation): Already implemented in audit/models.py and log.py -- delivered by #434

### Architecture Notes
Task #560 is a duplicate of #434 (Add audit-centric dispatch-cycle trace ID), which completed the full pipeline (test-writer, builder, reviewer PASS .95). #434 was created from the same research doc (deer-flow-adoptable-patterns.md S3C) and is acknowledged as adopted in decision request #429.

The Channel A/B inclusion (AC line 2) was evaluated during #434 arch review and deliberately excluded: Channel A is a diagnostic convention not parsed by the orchestrator, and subagents have no mechanism to receive a cycle_id (dispatch prompts contain only task ID per orchestration skill). The audit-only approach provides full correlation without protocol changes.

### Changes Made
- Blocked to ideation as duplicate of #434

### Dependencies
- #434 (canonical implementation, status: done) covers all non-contradictory AC
