---
id: 490
title: Fix ContextInjectionHook blocking event loop
status: ideation
priority: important
created: 2026-03-04T07:38:06.1851597+01:00
updated: 2026-03-04T07:38:06.1851597+01:00
tags:
    - audit
    - bugfix
    - scope:core
class: standard
---

ARC-19: _run_kanban() calls subprocess.run() synchronously inside an async hook handler. Blocks event loop for kanban command duration. Replace with asyncio.create_subprocess_exec(). AC: hook fully async, no sync subprocess calls. See docs/architecture-audit.md.
