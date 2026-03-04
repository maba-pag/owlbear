---
id: 472
title: Sanitize error messages before sending to channels
status: ideation
priority: needed
created: 2026-03-04T07:37:51.3590676+01:00
updated: 2026-03-04T07:37:51.3590676+01:00
tags:
    - audit
    - security
    - channels
class: standard
---

SEC-08: Exception details sent via f-string to Slack/CLI. httpx exceptions can include URLs with tokens, auth headers, infrastructure details. Create error_to_user_message() helper that strips sensitive data. AC: no raw exception messages sent to channels. See docs/security-audit.md.
