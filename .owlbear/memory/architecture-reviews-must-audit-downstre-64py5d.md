---
approved_at: '2026-05-17T02:48:07.352928Z'
categories: [pitfall, process]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:33:51.494520Z'
didnt_use_count: 48
id: 120b043a-8b96-4af1-bc7a-e73eefb1eaf1
outstanding_count: 25
scope_agents: [shaper, verifier]
score: 3.0
source_agent: copilot
state: approved
title: Audit non-code consumers in architecture reviews
unremarkable_count: 30
updated_at: '2026-07-28T10:00:18.975057+00:00'
---

For OwlBear service or interface redesign reviews, inspect non-code downstream consumers such as `share/skills/`, `share/prompts/`, `share/instructions/`, Cockpit UI routes, tests, and startup hooks. Package-local evidence can miss rollout gaps in those consumers.
