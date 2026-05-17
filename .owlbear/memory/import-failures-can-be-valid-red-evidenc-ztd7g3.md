---
id: 1670d436-42db-4c4c-a672-50d135a38965
title: Import failures can be valid RED evidence
categories:
- pitfall
- process
confidence: 0.82
state: curated
scope_agents:
- test-writer
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:38:25.352792Z'
updated_at: '2026-05-17T01:48:31.946912Z'
approved_at: null
---

For new-file RED tasks, `0 collected` with an import-resolution failure can be valid RED evidence because the implementation file does not exist yet. Still review the test body assertions for AC quality; collection failure does not prove assertion strength.
