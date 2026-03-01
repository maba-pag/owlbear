---
id: 331
title: Implement Block Kit template helpers — format_proposal_blocks and format_status_blocks
status: archived
priority: needed
created: 2026-03-01T11:17:08.1158986+01:00
updated: 2026-03-01T17:10:01.999187+01:00
started: 2026-03-01T11:21:29.0990527+01:00
completed: 2026-03-01T17:10:01.999187+01:00
tags:
    - phase-12
    - slack
    - channels
depends_on:
    - 330
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/channels/slack_templates.py with pure functions
- [ ] format_proposal_blocks(title: str, description: str, options: list[str]) -> list[dict]
  - header block, section with mrkdwn description, divider, numbered option sections, context footer
- [ ] format_status_blocks(task_name: str, step: int, total_steps: int, status: str, eta: str, last_tool: str) -> list[dict]
  - header, 2-column fields section, last action section
- [ ] Truncate text fields to Slack limits (3000 chars for section text)
- [ ] No external dependencies — pure dict construction

See docs/slack-rich-messaging-research.md S3.3
