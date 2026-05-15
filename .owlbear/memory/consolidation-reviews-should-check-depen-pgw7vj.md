---
id: 146eaa6b-11d6-4eaa-906f-02f7bc14662d
title: 'Consolidation reviews: check archived dependency suites before failing on
  coverage gaps'
categories:
- process
- pitfall
confidence: 0.87
state: deleted
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-14T12:08:02.856635Z'
updated_at: '2026-05-15T20:52:14.952272Z'
approved_at: null
---

In consolidation-test reviews, do not fail on missing Shell-level or adjacent integration proof until you inspect archived dependency suites named in the task deps. ThemeToggle/DR routing claims can already be satisfied by durable dependency tests, so only reject when the current task's AC still lacks any falsifiable proof after counting those adjacent surfaces.
