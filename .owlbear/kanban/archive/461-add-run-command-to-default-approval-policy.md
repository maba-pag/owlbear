---
id: 461
title: Add run_command to default approval policy
status: archived
priority: critical
created: 2026-03-04T07:37:41.925532+01:00
updated: 2026-03-06T19:28:07.5943706+01:00
started: 2026-03-06T00:19:43.7882721+01:00
completed: 2026-03-06T19:28:07.5943706+01:00
tags:
    - audit
    - security
    - config
class: standard
---

SEC-05 fix: Add run_command to default approval_policy in config.py.

**AC:**
- [ ] config.py approval_policy default includes {'tool_name': 'run_command'}
- [ ] Test: OwlBearSettings().approval_policy contains run_command entry
- [ ] Test: ApprovalPolicy built from defaults returns requires_approval('run_command', {}) == True
- [ ] No other code changes needed (TerminalToolset already in _destructive set)

See docs/research/run-command-approval-gate.md for details.
