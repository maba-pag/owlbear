---
id: 32f1d15c-6052-411c-b871-abd6d99002bb
title: Instruction applyTo needs built-in file access
categories:
- pitfall
- tool-usage
- process
confidence: 0.86
state: deleted
scope_agents:
- architect
- builder
- reviewer
- planner
source_agent: copilot
created_at: '2026-05-17T01:34:55.120125Z'
updated_at: '2026-05-17T03:35:15.921948Z'
approved_at: null
---

VS Code `.instructions.md` `applyTo` scoping is triggered by agents reading or writing matching files with built-in file tools. Pipeline agents that never read matching agent files may not receive those instructions; use explicit required-reading links or skills when instruction loading must be guaranteed.
