---
id: 1259
title: Add paused option to usePollingFetch
status: research
priority: nice-to-have
created: 2026-05-01T09:34:21.381409+00:00
updated: 2026-05-01T09:34:40.318213+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Add a `paused?: boolean` option to usePollingFetch. When true, skip interval ticks but keep refetch() callable. Default false for backward compatibility. See .owlbear/research/1235-eventsource-client-implementation.md §3.5