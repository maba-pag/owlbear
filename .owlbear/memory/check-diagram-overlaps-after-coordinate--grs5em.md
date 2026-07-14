---
approved_at: null
categories: [pitfall, domain-knowledge, tool-usage]
confidence: 0.8
contested_by_task: null
created_at: '2026-05-17T01:37:08.933416Z'
didnt_use_count: 0
id: f94416a2-cd78-402e-b4f3-58ede1be78c7
outstanding_count: 0
scope_agents: [builder, verifier, collector]
score: 0.0
source_agent: copilot
state: deleted
title: Check diagram overlaps after coordinate normalization
unremarkable_count: 0
updated_at: '2026-07-14T23:41:39.853678+00:00'
---

After batch coordinate normalization in Excalidraw or generated diagrams, run a bounding-box overlap check on standalone text. Uniform offsets can collapse distinct labels onto the same coordinate while other structural checks stay green.
