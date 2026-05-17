---
id: 27841d5e-75d3-4279-880e-9389105a0d55
title: Doc-chain migrations need stale-text scans
categories:
- pitfall
- process
- tool-usage
confidence: 0.84
state: curated
scope_agents:
- doc-writer
- reviewer
- builder
- architect
source_agent: copilot
created_at: '2026-05-17T01:37:54.465692Z'
updated_at: '2026-05-17T01:48:21.037110Z'
approved_at: null
---

After a doc-chain or rule-authority migration, grep consumer prompts and instruction files for stale text naming the old authority source. Structural chain tests can pass while prompts still direct agents to load or cite the retired source.
