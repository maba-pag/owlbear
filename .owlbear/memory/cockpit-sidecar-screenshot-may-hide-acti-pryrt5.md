---
id: ca0d8245-f7b0-48e0-b0a8-65fb1fe22187
title: Cockpit sidecar screenshot may hide Actions at 1280x800
categories:
- pitfall
- tool-usage
confidence: 0.84
state: deleted
scope_agents:
- builder
- reviewer
source_agent: builder
created_at: '2026-05-15T10:06:35.451159Z'
updated_at: '2026-05-15T21:49:47.473392Z'
approved_at: null
---

Sidecar Actions section falls below fold at 1280×800 viewport; captures appear complete (header, metadata/body visible) but Actions region is clipped. Use 1280×1200 or taller to produce a full in-frame artifact covering all three sidecar regions. Confirmed for task #1568 AC-3 evidence.
