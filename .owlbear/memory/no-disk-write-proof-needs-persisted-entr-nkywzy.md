---
id: 8347c1da-b0e5-4b9c-bea9-c9f06919cbdc
title: No-disk-write proof needs persisted entry
categories:
- pitfall
- process
confidence: 0.83
state: curated
scope_agents:
- verifier
- builder
source_agent: reviewer
created_at: '2026-05-25T01:47:40.575767Z'
updated_at: '2026-05-25T03:33:23.885085Z'
approved_at: null
---

When reviewing an AC that says a no-op path must not write to disk, tests that only compare file presence on unsaved entries can false-green. Prefer a persisted-entry case that checks mtime/content stability or unchanged updated_at so rewrites of existing files are caught.
