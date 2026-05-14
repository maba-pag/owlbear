---
id: ceee7d8d-2817-4694-b44f-27b6733fbfcf
title: Scope-aware source URL proof
categories:
- pitfall
- domain-knowledge
confidence: 0.94
state: curated
scope_agents:
- reviewer
- test-writer
- builder
- architect
source_agent: reviewer
created_at: '2026-05-14T19:20:32.795153Z'
updated_at: '2026-05-14T21:29:36.012527Z'
approved_at: null
---

When a knowledge ingestion AC ties source_url resolution to scope, seed the same URL in multiple scopes during review/tests. The current resolve_by_url path is scope-blind, so single-scope tests can false-green while linking documents to the wrong KnowledgeSource.
