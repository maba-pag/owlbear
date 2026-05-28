---
id: ff677a6d-9989-4f7d-b1f5-a28340c4937f
title: Source fetcher tests patch module-level intake symbol
categories:
- domain-knowledge
- pitfall
confidence: 0.8
state: curated
scope_agents:
- builder
- test-writer
source_agent: builder
created_at: '2026-05-28T00:59:15.613379Z'
updated_at: '2026-05-28T01:31:39.928476Z'
approved_at: null
---

For source fetcher adapters, import intake as a module (`from owlbear_knowledge import intake`) when tests patch `owlbear_knowledge.source_fetcher.intake.read_url/read_file`; direct function imports break the patch target.
