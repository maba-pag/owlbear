---
id: 1234
title: Implement SSE endpoint with watchfiles-based file watcher
status: backlog
priority: nice-to-have
created: 2026-04-30 16:48:42.978432+00:00
updated: 2026-05-01T09:20:36.105326+00:00
tags:
- cockpit
- backend
parent:
depends_on:
- 1233
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Add GET /api/events SSE endpoint to cockpit backend. Use watchfiles to watch the tasks directory for changes. On change, emit invalidation-only events (mtime payload). Single async generator per connection. Cleanup on disconnect. Dependency: sse-starlette + watchfiles packages. See .owlbear/research/1233-realtime-cockpit-updates.md
[[2026-05-01]]
## Research

**Key findings:** Implementation validated. ~35 LOC endpoint using `sse-starlette` EventSourceResponse + `watchfiles.awatch`. Design decisions documented: per-connection watcher, .md-only filter excluding .tmp- files, recursive=False, invalidation-only events, missing-dir guard, sse-starlette native shutdown handling.

**Challenge outcome:** reconsider (0.64 confidence in original). Challenger identified valid gaps in missing-dir handling, shutdown lifecycle, temp-file filtering, and dependency grounding. All addressed in design decisions table. Revised confidence: 0.75. Core approach unchanged.

**Trade-off matrix:** See .owlbear/research/1234-sse-endpoint-implementation.md §3.2 and §3.4.

**Dependencies:** sse-starlette (already in lock via MCP, 16.5KB wheel) + watchfiles (new, ~2MB Rust binary wheel). Both need explicit addition to serve/cockpit/pyproject.toml.

**Classification:** T1 — autonomous. Approach already approved in #1233 research. No architecture change, no user decision needed.

**Follow-up tasks:** None needed — #1234 is itself the implementation task (now advancing to backlog). Frontend counterpart #1235 already exists.

**Doc:** .owlbear/research/1234-sse-endpoint-implementation.md