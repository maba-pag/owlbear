---
id: b6f935e0-2457-49b5-8f42-9a0cfabbe427
title: Use PDS web component event contracts in tests
categories:
- pitfall
- domain-knowledge
- tool-usage
confidence: 0.84
state: curated
scope_agents:
- builder
- verifier
source_agent: copilot
created_at: '2026-05-17T01:37:24.459869Z'
updated_at: '2026-05-17T01:48:20.732611Z'
approved_at: null
---

For Porsche Design System web components in jsdom, verify the component's actual DOM/event contract before writing tests. Examples: `PMultiSelect` should be driven with its `update` CustomEvent, while unsupported components may need native fallbacks with the deviation documented.
