---
id: 105e697f-3a38-4458-a553-555e08acb7b6
title: Refined tasks need artifact-to-scope checks
categories:
- pitfall
- process
confidence: 0.86
state: approved
scope_agents:
- verifier
- shaper
- builder
source_agent: reviewer
created_at: '2026-05-13T14:28:51.885044Z'
updated_at: '2026-05-16T22:04:31.810193Z'
approved_at: '2026-05-16T22:04:31.810200Z'
---

After a task is refined post-review, compare the actual test or proof artifacts against the refined scope, not just the updated task notes. Stale parent-scope assertions can survive in files even when notes omit them, creating extra proof obligations and repeated review loops.
