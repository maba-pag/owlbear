---
id: 105e697f-3a38-4458-a553-555e08acb7b6
title: Refined child task may retain stale parent-scope tests
categories:
- pitfall
- process
confidence: 0.92
state: approved
scope_agents:
- reviewer
- architect
- test-writer
source_agent: reviewer
created_at: '2026-05-13T14:28:51.885044Z'
updated_at: '2026-05-15T19:48:31.650125Z'
approved_at: '2026-05-15T19:48:31.650134Z'
---

After an architect refines a child task body post-review, compare the actual test file against the refined scope and class list. Stale test classes from the parent contract can survive even when task notes omit them, creating extra proof obligations and repeated review loops.
