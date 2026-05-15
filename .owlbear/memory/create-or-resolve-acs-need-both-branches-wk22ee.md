---
id: bfe44264-fdb8-4f55-9d94-6e2543e88520
title: Create-or-resolve ACs need both branches proved
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.94
state: curated
scope_agents:
- reviewer
- architect
- test-writer
source_agent: reviewer
created_at: '2026-05-15T03:15:12.674835Z'
updated_at: '2026-05-15T06:23:28.164555Z'
approved_at: null
---

When an AC says persistence must link to a created or resolved row, do not accept tests that only cover the create path from an empty DB. Require a seeded existing-row case, especially with conflicting scope/tenant keys, or URL-only/source-only resolution regressions can false-green.
