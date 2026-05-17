---
id: f44162a2-bcb3-45a2-9dc9-7ebdda28c31f
title: Aggregate wave assertions hide duplicate placements
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.82
state: curated
scope_agents:
- test-writer
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:38:17.038313Z'
updated_at: '2026-05-17T01:48:31.861409Z'
approved_at: null
---

Wave-assembly tests that collapse all task IDs into a flat set can miss duplicate placement across waves or within a wave. Preserve at least one assertion on per-wave entry lists when the AC concerns placement or wave structure.
