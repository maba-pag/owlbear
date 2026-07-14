---
approved_at: null
categories: [pitfall, process, tool-usage]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:54.465692Z'
didnt_use_count: 1
id: 27841d5e-75d3-4279-880e-9389105a0d55
outstanding_count: 0
scope_agents: [collector, verifier, builder, shaper]
score: 0.83
source_agent: copilot
state: curated
title: Doc-chain migrations need stale-text scans
unremarkable_count: 1
updated_at: '2026-07-14T10:48:05.479561+00:00'
---

After a doc-chain or rule-authority migration, grep consumer prompts and instruction files for stale text naming the old authority source. Structural chain tests can pass while prompts still direct agents to load or cite the retired source.
