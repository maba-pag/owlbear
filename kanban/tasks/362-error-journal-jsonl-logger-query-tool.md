---
id: 362
title: Error journal — JSONL logger + query tool
status: archived
priority: important
created: 2026-03-01T20:11:59.9232321+01:00
updated: 2026-03-03T13:42:27.2704936+01:00
started: 2026-03-01T20:22:24.7416349+01:00
completed: 2026-03-03T13:42:27.2704936+01:00
tags:
    - phase-13
    - memory
    - reliability
class: standard
---

From #306 error-recovery.md. Append-only JSONL log in {workspace}/.owlbear/error_journal.jsonl capturing every error and resolution. Query tool: query_error_journal(tool_name?, error_type?, last_n?) for agents to learn from past failures. 10K entry cap with rotation. ~80 LOC in memory/error_journal.py. AC: Errors logged with ts/type/tool/exc/action/attempt/resolved/session_id; query tool returns filtered entries; rotation triggers at 10K entries. Depends on #306.
