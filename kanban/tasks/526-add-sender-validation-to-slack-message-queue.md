---
id: 526
title: Add sender validation to Slack message queue
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:33.3312171+01:00
updated: 2026-03-04T07:38:33.3312171+01:00
tags:
    - audit
    - security
    - channels
class: standard
---

SEC-15: Messages from Slack DMs fed to agent as prompts with no sanitization. Inherent to design, but mitigate: validate messages come from expected user IDs, add rate limiting, log all incoming messages. AC: sender validation active. See docs/security-audit.md.
