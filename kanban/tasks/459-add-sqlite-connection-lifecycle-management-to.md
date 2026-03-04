---
id: 459
title: Add SQLite connection lifecycle management to bootstrap
status: ideation
priority: critical
created: 2026-03-04T07:37:39.2136015+01:00
updated: 2026-03-04T07:37:39.2136015+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

ARC-04/C-1: SQLite connections created in bootstrap helpers are never closed. No cleanup hook, no context manager. BootstrapResult.cleanup doesnt include connection closure. Leaked FDs accumulate over daemon lifetime. AC: connections registered in BootstrapResult.cleanup, closed on shutdown. See docs/architecture-audit.md, docs/resilience-audit.md.
