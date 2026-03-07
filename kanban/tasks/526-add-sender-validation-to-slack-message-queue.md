---
id: 526
title: Add sender validation to Slack message queue
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:33.3312171+01:00
updated: 2026-03-07T00:25:41.4265706+01:00
started: 2026-03-07T00:16:19.9599646+01:00
tags:
    - audit
    - security
    - channels
class: standard
---

SEC-15: Messages from Slack DMs fed to agent as prompts with no sanitization. Inherent to design, but mitigate: validate messages come from expected user IDs, add rate limiting, log all incoming messages. AC: sender validation active. See docs/security-audit.md.

Research complete: see docs/slack-sender-validation-research.md. Recommendation: (1) Config allowlist with slack_allowed_user_ids (.85 confidence), (2) Sliding window rate limiter (.80), (3) Structured INFO logging (.85). Follow-up implementation tasks created.
