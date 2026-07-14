---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:51.641533Z'
didnt_use_count: 0
id: e1e10857-dec0-4341-9138-ef02546c53e0
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Repo-wide string-search ACs need full declared surface
unremarkable_count: 0
updated_at: '2026-07-14T23:50:08.317520+00:00'
---

For repo-wide string-search or banned-token ACs, tests must scan the full declared surface or explicitly exempt historical paths. Scanning only `serve/` or `share/` can false-green while `.owlbear/decisions`, sources, or other retained artifacts still contain the banned text.
