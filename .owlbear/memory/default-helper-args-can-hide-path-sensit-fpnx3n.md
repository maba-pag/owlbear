---
approved_at: '2026-07-14T20:21:50.870257+00:00'
categories: [pitfall, process]
confidence: 0.89
contested_by_task: null
created_at: '2026-05-28T01:56:20.863292Z'
didnt_use_count: 0
id: 9290ca07-e845-4a8a-b195-86b4ee98bbf0
outstanding_count: 0
scope_agents: [verifier, builder]
score: 0.88
source_agent: reviewer
state: approved
title: Default helper args can hide path-sensitive proof gaps
unremarkable_count: 1
updated_at: '2026-07-17T06:28:15.127725+00:00'
---

When reviewing tests for path-sensitive ACs, check whether helper defaults like base_path='.' make every call site exercise only the default branch. A suite can false-green while code inspection shows the implementation is correct but unproven for non-default path routing.
