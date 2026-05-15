---
id: e20b2270-6582-4eb4-ad13-6b09004e50b9
title: Task reference substring checks false-green
categories:
- pitfall
- process
- tool-usage
confidence: 0.87
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-15T06:41:27.147469Z'
updated_at: '2026-05-15T09:11:19.010187Z'
approved_at: null
---

In review of fixture-backed DOM proofs, reject assertions like toContain('1') for task or record IDs. They false-green wrong values such as 10 or 21. Require an exact match or a boundary-aware assertion on the labeled field.
