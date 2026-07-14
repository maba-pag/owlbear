---
approved_at: null
categories: [pitfall, process]
confidence: 0.83
contested_by_task: null
created_at: '2026-05-25T01:47:40.575767Z'
didnt_use_count: 0
id: 8347c1da-b0e5-4b9c-bea9-c9f06919cbdc
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.0
source_agent: reviewer
state: deleted
title: No-disk-write proof needs persisted entry
unremarkable_count: 0
updated_at: '2026-07-14T23:38:23.743478+00:00'
---

When reviewing an AC that says a no-op path must not write to disk, tests that only compare file presence on unsaved entries can false-green. Prefer a persisted-entry case that checks mtime/content stability or unchanged updated_at so rewrites of existing files are caught.
