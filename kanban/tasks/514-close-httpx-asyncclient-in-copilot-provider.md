---
id: 514
title: Close httpx.AsyncClient in Copilot provider
status: ideation
priority: important
created: 2026-03-04T07:38:25.3834342+01:00
updated: 2026-03-04T07:38:25.3834342+01:00
tags:
    - audit
    - resilience
    - auth
class: standard
---

C-4: providers/copilot.py creates httpx.AsyncClient passed to AsyncOpenAI but never closes it. Leaks connection pool for daemon lifetime. Register close() in bootstrap cleanup or restructure as async context manager. AC: client closed on shutdown. See docs/resilience-audit.md.
