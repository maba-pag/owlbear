---
approved_at: null
categories: [pitfall, process]
confidence: 0.89
contested_by_task: null
created_at: '2026-05-27T22:47:19.568286Z'
didnt_use_count: 1
id: 2110335a-8024-41cc-b379-faaffb4784ad
outstanding_count: 0
scope_agents: [verifier, shaper, builder]
score: 0.89
source_agent: reviewer
state: curated
title: Root-level pytest selector proof risk
unremarkable_count: 0
updated_at: '2026-07-13T13:51:56.948329+00:00'
---

When an AC requires a root-level `pytest tests/ -k ...` command, unrelated collection errors can block the proof even if the task’s own slice is green. Treat that as a proof-plan/AC defect, not an implementation defect, and prefer path-scoped proof surfaces for reviewable contracts.
