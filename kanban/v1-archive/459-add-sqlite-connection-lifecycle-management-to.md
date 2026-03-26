---
id: 459
title: Add SQLite connection lifecycle management to bootstrap
status: archived
priority: critical
created: 2026-03-04T07:37:39.2136015+01:00
updated: 2026-03-06T19:28:06.6604279+01:00
started: 2026-03-06T00:10:22.616867+01:00
completed: 2026-03-06T19:28:06.6604279+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

ARC-04/C-1: SQLite connections created in bootstrap helpers are never closed. No cleanup hook, no context manager. BootstrapResult.cleanup doesnt include connection closure. Leaked FDs accumulate over daemon lifetime.
Research complete (2026-03-06). See docs/research/sqlite-connection-lifecycle.md.

AC:
- [ ] After build_toolsets() completes, if _build_knowledge_infra() created a sqlite3.Connection, that connections close method is present in BootstrapResult.cleanup
- [ ] The connection is surfaced from build_toolsets() to bootstrap()  either by adding conn to the return tuple (A1) or by passing the cleanup list as a parameter (A2). Builder chooses; both are approved.
- [ ] No new classes, context managers, or abstractions introduced. Change is <=5 lines of production code (excl. tests)
- [ ] Unit test: mock _build_knowledge_infra to return a _KnowledgeInfra with a mock conn, call bootstrap or build_toolsets, assert conn.close is in the cleanup list
- [ ] Unit test: when _build_knowledge_infra returns None, cleanup list has no conn.close entry
- [ ] Existing contextlib.suppress(Exception) in CLI finally block handles double-close  no change needed there

Architecture notes:
- Follow the progress_reporter.stop pattern (bootstrap.py L868)
- _KnowledgeInfra.conn is the only sqlite3.Connection in bootstrap
- conn.close() is sync, cleanup iteration is sync  no async wrapper needed
- build_toolsets already has noqa: PLR0913  one more param is acceptable if using A2
