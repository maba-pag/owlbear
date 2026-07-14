---
approved_at: null
categories: [pitfall, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-17T01:35:42.219291Z'
didnt_use_count: 0
id: 384486bf-5e49-4ccf-833e-3fcad98c9e28
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: curated
title: Adapter contract tests need live signatures
unremarkable_count: 0
updated_at: '2026-07-14T23:39:10.040862+00:00'
---

For adapter contract changes, include an executable assertion against the public callable or advertised response shape; import or model-metadata checks alone can miss contract drift. Do not restore removed APIs solely to satisfy stale compatibility tests.
