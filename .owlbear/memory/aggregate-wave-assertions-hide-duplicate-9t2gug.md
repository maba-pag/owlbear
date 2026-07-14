---
approved_at: null
categories: [pitfall, process, domain-knowledge]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:17.038313Z'
didnt_use_count: 0
id: f44162a2-bcb3-45a2-9dc9-7ebdda28c31f
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Aggregate wave assertions hide duplicate placements
unremarkable_count: 0
updated_at: '2026-07-14T23:51:52.813341+00:00'
---

Wave-assembly tests that collapse all task IDs into a flat set can miss duplicate placement across waves or within a wave. Preserve at least one assertion on per-wave entry lists when the AC concerns placement or wave structure.
