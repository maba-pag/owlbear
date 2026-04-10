---
id: 361
title: Human escalation wiring via ON_ERROR hook and AskUser
status: archived
priority: important
created: 2026-03-01T20:11:50.6636773+01:00
updated: 2026-03-03T13:42:26.5897551+01:00
started: 2026-03-01T20:22:22.9301646+01:00
completed: 2026-03-03T13:42:26.5897551+01:00
tags:
    - phase-13
    - agent
    - reliability
    - channels
class: standard
---

From #306 error-recovery.md. After retries exhausted, invoke ask_user with structured error context and options: [retry / skip / abort]. Wire through ON_ERROR hook. ~50 LOC. AC: When all retries fail, user receives structured error message with action options; user response routes to retry, skip, or abort. Depends on #306, #357, #360.
