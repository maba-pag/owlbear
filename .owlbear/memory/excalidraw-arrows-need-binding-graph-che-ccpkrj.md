---
id: d015f2c5-92bf-45d5-b1e0-4c91d8c58a71
title: Excalidraw arrows need binding graph checks
categories:
- pitfall
- domain-knowledge
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- builder
- verifier
- collector
source_agent: copilot
created_at: '2026-05-17T01:37:05.636939Z'
updated_at: '2026-05-17T01:48:20.549163Z'
approved_at: null
---

For machine-readable Excalidraw diagrams, text scans are weak proof for topology changes. Resolve arrow `startBinding`/`endBinding` IDs through container chains to the bound text, then assert required or forbidden edges on the binding graph.
