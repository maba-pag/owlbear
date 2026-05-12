---
id: a720ea78-99b2-43d2-837b-9b02e57e418b
title: 'Reviewer: isolate build rerun failures caused by dirty worktree drift'
categories:
- process
- pitfall
- tool-usage
confidence: 0.89
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-12T17:28:28.050558Z'
updated_at: '2026-05-12T21:24:29.413563Z'
approved_at: null
---

If an independent frontend build rerun fails outside the reviewed file, check git scope before failing the task. When the reviewed commit touched only one file and unrelated uncommitted work in other files explains the build error, treat it as workspace contamination (not a defect in the reviewed task). Use scoped lint/search evidence plus git forensics to justify PASS.
