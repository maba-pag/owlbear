---
approved_at: null
categories: [pitfall, process]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-17T01:38:25.352792Z'
didnt_use_count: 0
id: 1670d436-42db-4c4c-a672-50d135a38965
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Import failures can be valid RED evidence
unremarkable_count: 0
updated_at: '2026-07-14T23:51:53.096437+00:00'
---

For new-file RED tasks, `0 collected` with an import-resolution failure can be valid RED evidence because the implementation file does not exist yet. Still review the test body assertions for AC quality; collection failure does not prove assertion strength.
