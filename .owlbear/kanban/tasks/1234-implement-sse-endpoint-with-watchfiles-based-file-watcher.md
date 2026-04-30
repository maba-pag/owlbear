---
id: 1234
title: Implement SSE endpoint with watchfiles-based file watcher
status: research
priority: nice-to-have
created: '2026-04-30 16:48:42.978432+00:00'
updated: '2026-04-30 16:48:56.190594+00:00'
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