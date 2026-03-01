---
id: 339
title: Implement ApprovalPolicy and ApprovalSession — policy config and session pre-grants
status: archived
priority: needed
created: 2026-03-01T11:18:29.8984368+01:00
updated: 2026-03-01T17:10:08.8535068+01:00
started: 2026-03-01T11:21:44.3481589+01:00
completed: 2026-03-01T17:10:08.8535068+01:00
tags:
    - phase-12
    - agent
    - safety
depends_on:
    - 338
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/core/approval.py
- [ ] ApprovalRule(BaseModel): tool_name (str), arg_pattern (str | None = None)
- [ ] ApprovalPolicy(BaseModel): rules (list[ApprovalRule]), default_timeout (float = 120.0)
- [ ] ApprovalPolicy.requires_approval(tool_name, args) -> bool: checks rules, supports arg_pattern regex
- [ ] ApprovalSession: tracks set of pre-granted tool names for current session
- [ ] ApprovalSession.is_pre_granted(tool_name) -> bool
- [ ] ApprovalSession.grant(tool_name) -> None: adds to pre-grant set
- [ ] ApprovalSession.clear() -> None: resets all pre-grants

See docs/approval-gates-research.md S3.5
