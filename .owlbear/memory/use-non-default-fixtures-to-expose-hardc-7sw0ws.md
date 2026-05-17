---
id: 5fc7be32-8bab-44b4-83eb-d62cbd1671de
title: Use non-default fixtures to expose hardcoding
categories:
- pitfall
- process
confidence: 0.84
state: curated
scope_agents:
- test-writer
- reviewer
- builder
source_agent: copilot
created_at: '2026-05-17T01:37:48.831901Z'
updated_at: '2026-05-17T01:48:20.978598Z'
approved_at: null
---

Default-shaped fixtures can hide bugs: empty lists mask element-type drift, default directory names hide hardcoded paths, and default YAML values hide loader omissions. Use non-empty, non-default sentinel values when testing extraction or preservation contracts.
