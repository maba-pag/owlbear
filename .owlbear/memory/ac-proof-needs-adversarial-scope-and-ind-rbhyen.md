---
id: 90c7870a-bc3e-4899-99b1-5ef993947d7f
title: AC proof needs adversarial scope and index-column checks
categories:
- pitfall
- process
confidence: 0.92
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-26T05:49:58.581043Z'
updated_at: '2026-05-26T08:37:45.308959Z'
approved_at: null
---

When ACs require document-scoped queries or indexes on specific columns, do not accept tests that only use one document or only match index names. Require cross-document contamination fixtures and column-level index inspection (for example via PRAGMA) or the suite can false-green.
