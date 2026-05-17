---
id: 384486bf-5e49-4ccf-833e-3fcad98c9e28
title: Adapter contract tests need live signatures
categories:
- pitfall
- process
confidence: 0.86
state: curated
scope_agents:
- builder
- reviewer
- test-writer
- architect
source_agent: copilot
created_at: '2026-05-17T01:35:42.219291Z'
updated_at: '2026-05-17T01:48:10.715303Z'
approved_at: null
---

For adapter contract tasks, import-only or `model_fields`-only tests are insufficient. At least one assertion should target the live tool signature or advertised output schema; stale compatibility tests should be migrated rather than restoring removed legacy APIs.
