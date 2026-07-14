---
approved_at: null
categories: [tool-usage, pitfall]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T08:17:07.705626Z'
didnt_use_count: 0
id: e8c980ad-61cb-4dd3-9a32-1981bc583c47
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Delete patch may not remove files on disk
unremarkable_count: 0
updated_at: '2026-07-14T20:38:07.459540+00:00'
---

In owlbear-dev, apply_patch Delete File reported success for a 13-file batch but files still existed. For deletion-heavy tasks, verify filesystem immediately and fall back to explicit rm with per-file ABSENT checks before running quality gates.
