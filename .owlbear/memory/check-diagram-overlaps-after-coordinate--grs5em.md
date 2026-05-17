---
id: f94416a2-cd78-402e-b4f3-58ede1be78c7
title: Check diagram overlaps after coordinate normalization
categories:
- pitfall
- domain-knowledge
- tool-usage
confidence: 0.8
state: curated
scope_agents:
- builder
- test-writer
- reviewer
- doc-writer
source_agent: copilot
created_at: '2026-05-17T01:37:08.933416Z'
updated_at: '2026-05-17T01:48:20.579163Z'
approved_at: null
---

After batch coordinate normalization in Excalidraw or generated diagrams, run a bounding-box overlap check on standalone text. Uniform offsets can collapse distinct labels onto the same coordinate while other structural checks stay green.
