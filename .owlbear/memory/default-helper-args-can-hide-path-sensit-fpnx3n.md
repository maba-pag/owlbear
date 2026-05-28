---
id: 9290ca07-e845-4a8a-b195-86b4ee98bbf0
title: Default helper args can hide path-sensitive proof gaps
categories:
- pitfall
- process
confidence: 0.89
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-28T01:56:20.863292Z'
updated_at: '2026-05-28T03:39:32.204959Z'
approved_at: null
---

When reviewing tests for path-sensitive ACs, check whether helper defaults like base_path='.' make every call site exercise only the default branch. A suite can false-green while code inspection shows the implementation is correct but unproven for non-default path routing.
