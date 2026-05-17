---
id: 6e93459c-24d6-4252-8b7b-d73f8fb6ec70
title: Full-file apply_patch rewrites need separate operations
categories:
- pitfall
- tool-usage
confidence: 0.88
state: deleted
scope_agents:
- builder
- doc-writer
- test-writer
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:33:55.449438Z'
updated_at: '2026-05-17T02:50:47.141260Z'
approved_at: null
---

Do not delete and re-add the same path in one `apply_patch` call for a full-file rewrite. Split the delete and add into separate operations, because combined same-path delete/add patches can fail or behave unreliably.
