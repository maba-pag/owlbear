---
id: 330
title: Test Block Kit template helpers — proposal and status format functions
status: archived
priority: needed
created: 2026-03-01T11:16:54.0360862+01:00
updated: 2026-03-01T17:10:01.3547005+01:00
started: 2026-03-01T11:20:58.1320542+01:00
completed: 2026-03-01T17:10:01.3547005+01:00
tags:
    - phase-12
    - slack
    - channels
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test format_proposal_blocks(title, description, options) returns valid Block Kit blocks
- [ ] Verify: header block with title, section with description, divider, numbered option sections, context footer
- [ ] Test format_status_blocks(task_name, step, total_steps, status, eta, last_tool) returns valid blocks
- [ ] Verify: header, section with 2-column fields (task, step, status, eta), last action section
- [ ] Test edge cases: empty options list, long descriptions (>3000 chars truncated), special chars escaped
- [ ] Pure function tests — no Slack API mocking needed

See docs/research/slack-rich-messaging.md S3.3
