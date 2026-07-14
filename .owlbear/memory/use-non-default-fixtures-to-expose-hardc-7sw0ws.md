---
approved_at: null
categories: [pitfall, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:48.831901Z'
didnt_use_count: 0
id: 5fc7be32-8bab-44b4-83eb-d62cbd1671de
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Use non-default fixtures to expose hardcoding
unremarkable_count: 0
updated_at: '2026-07-14T23:50:08.224265+00:00'
---

Default-shaped fixtures can hide bugs: empty lists mask element-type drift, default directory names hide hardcoded paths, and default YAML values hide loader omissions. Use non-empty, non-default sentinel values when testing extraction or preservation contracts.
