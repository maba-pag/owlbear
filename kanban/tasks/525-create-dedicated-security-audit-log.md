---
id: 525
title: Create dedicated security audit log
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:32.6960467+01:00
updated: 2026-03-04T07:38:32.6960467+01:00
tags:
    - audit
    - security
    - observability
class: standard
---

SEC-14: Security events (blocked commands, approvals, auth failures) mixed into standard rotating logs. Security events can be lost in rotation. Create SecurityAuditLog with separate append-only file. AC: security events in dedicated file with longer retention. See docs/security-audit.md.
