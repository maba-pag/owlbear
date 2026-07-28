---
approved_at: '2026-07-22T03:44:59.612398+00:00'
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:35:42.219291Z'
didnt_use_count: 86
id: 384486bf-5e49-4ccf-833e-3fcad98c9e28
outstanding_count: 59
scope_agents: [builder, verifier]
score: 6.2700000000000005
source_agent: copilot
state: approved
title: Adapter contract tests need live signatures
unremarkable_count: 49
updated_at: '2026-07-28T10:00:18.858236+00:00'
---

For adapter contract changes, include an executable assertion against the public callable or advertised response shape; import or model-metadata checks alone can miss contract drift. Do not restore removed APIs solely to satisfy stale compatibility tests.
