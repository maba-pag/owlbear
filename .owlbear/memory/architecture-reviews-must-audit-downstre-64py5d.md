---
id: 120b043a-8b96-4af1-bc7a-e73eefb1eaf1
title: Audit non-code consumers in architecture reviews
categories:
- pitfall
- process
confidence: 0.8
state: approved
scope_agents:
- architect
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:33:51.494520Z'
updated_at: '2026-05-17T02:48:07.352920Z'
approved_at: '2026-05-17T02:48:07.352928Z'
---

For OwlBear service or interface redesign reviews, inspect non-code downstream consumers such as `share/skills/`, `share/prompts/`, `share/instructions/`, Cockpit UI routes, tests, and startup hooks. Package-local evidence can miss rollout gaps in those consumers.
