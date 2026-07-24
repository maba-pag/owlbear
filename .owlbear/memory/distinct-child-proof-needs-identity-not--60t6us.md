---
approved_at: '2026-05-15T21:16:41.240210Z'
categories: [pitfall, process, tool-usage]
confidence: 0.92
contested_by_task: null
created_at: '2026-05-15T03:23:24.940262Z'
didnt_use_count: 56
id: d75dbe0e-9a63-42a0-bdca-a8daa3ceb730
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.9
source_agent: reviewer
state: approved
title: Distinct-child proof needs identity, not per-label counts
unremarkable_count: 2
updated_at: '2026-07-24T19:45:01.464517+00:00'
---

In DOM-proof reviews, `:scope > *` per-label count assertions can false-green distinct-child requirements if one child contains all labels. Require proof that labeled fields resolve to different child elements, not just count 1 for each label.
