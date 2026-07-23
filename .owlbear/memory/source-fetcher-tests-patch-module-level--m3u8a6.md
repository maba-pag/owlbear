---
approved_at: '2026-07-14T20:41:16.367720+00:00'
categories: [domain-knowledge, pitfall]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-28T00:59:15.613379Z'
didnt_use_count: 6
id: ff677a6d-9989-4f7d-b1f5-a28340c4937f
outstanding_count: 0
scope_agents: [builder]
score: 0.8
source_agent: builder
state: approved
title: Source fetcher tests patch module-level intake symbol
unremarkable_count: 0
updated_at: '2026-07-23T13:09:44.169617+00:00'
---

For source fetcher adapters, import intake as a module (`from owlbear_knowledge import intake`) when tests patch `owlbear_knowledge.source_fetcher.intake.read_url/read_file`; direct function imports break the patch target.
