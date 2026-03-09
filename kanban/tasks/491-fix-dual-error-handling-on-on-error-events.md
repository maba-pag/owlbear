---
id: 491
title: Fix dual error handling on ON_ERROR events
status: done
priority: important
created: 2026-03-04T07:38:06.9326328+01:00
updated: 2026-03-07T19:34:32.4308041+01:00
started: 2026-03-06T17:49:55.7317939+01:00
completed: 2026-03-07T19:34:22.7012737+01:00
tags:
    - audit
    - resilience
    - scope:core
blocked: true
block_reason: 'REVIEW FAIL: AC fundamentally invalid. #484 (done) deleted escalation.py and test_escalation.py entirely. All 9 AC lines target code that no longer exists. Task is moot -- close or redefine.'
class: standard
---

## Closed as moot (2026-03-07)

Task #484 (archived) deleted escalation.py and 	est_escalation.py entirely. All 9 AC lines targeted code that no longer exists. Zero references to EscalationHook remain in src/ or 	ests/.

The dual error handling problem this task aimed to fix was resolved by #484's decision to delete EscalationHook (YAGNI). No further action needed.

Verification:
- Test-Path src/owlbear/core/escalation.py = False
- Test-Path tests/test_escalation.py = False
- grep -r EscalationHook src/ tests/ = 0 matches
