---
id: 1300
title: Remove dead useEventSource hook after useBoard migration
status: research
priority: someday
created: 2026-05-02T19:48:32.676272+00:00
updated: 2026-05-02T19:48:39.873291+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1277
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

After #1277 refactors useBoard to use EventSourceProvider context, hooks/useEventSource.ts has zero production imports. Delete the hook file and its test files (useEventSource_1260.test.ts, useEventSource_1263.test.ts). Verify no other production code imports it first.