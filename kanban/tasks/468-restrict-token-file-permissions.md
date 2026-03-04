---
id: 468
title: Restrict token file permissions
status: ideation
priority: needed
created: 2026-03-04T07:37:47.9515569+01:00
updated: 2026-03-04T07:37:47.9515569+01:00
tags:
    - audit
    - security
    - auth
class: standard
---

SEC-03: save_token() writes copilot_token.json as plaintext with default permissions. On multi-user systems, other users can read. Set 0o600 on Unix, restrict ACL on Windows. AC: token file not readable by other users, test verifies permissions. See docs/security-audit.md.
