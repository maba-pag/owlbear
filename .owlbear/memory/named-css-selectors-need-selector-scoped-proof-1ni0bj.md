---
id: ecee51b4-81d6-4d64-9676-626610cf6749
title: Named CSS selectors need selector-scoped proof
categories:
- pitfall
- process
confidence: 0.85
state: approved
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-13T21:09:42.972951Z'
updated_at: '2026-05-16T22:05:05.637992Z'
approved_at: '2026-05-16T22:05:05.637998Z'
---

When a CSS source-contract AC names a class or selector, require proof against that selector itself. Generic class presence plus a file-wide regex can false-green after declarations move elsewhere; the rendered element and CSS assertion both need to target the named selector.
