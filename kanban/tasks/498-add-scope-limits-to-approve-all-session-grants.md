---
id: 498
title: Add scope limits to approve-all session grants
status: ideation
priority: important
created: 2026-03-04T07:38:12.1149492+01:00
updated: 2026-03-04T07:38:12.1149492+01:00
tags:
    - audit
    - security
    - safety
class: standard
---

SEC-12: 'approve all git_push' grants blanket session-wide approval for any args. Approving 'git push origin main' also approves 'git push --force'. Add max-uses limit, expiry, and consider arg-scoped grants. AC: grants limited in scope/duration. See docs/security-audit.md.
