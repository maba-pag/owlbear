---
approved_at: null
categories: [pitfall, domain-knowledge, tool-usage]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-17T01:37:24.459869Z'
didnt_use_count: 0
id: b6f935e0-2457-49b5-8f42-9a0cfabbe427
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: copilot
state: deleted
title: Use PDS web component event contracts in tests
unremarkable_count: 0
updated_at: '2026-07-14T23:46:20.619206+00:00'
---

For Porsche Design System web components in jsdom, verify the component's actual DOM/event contract before writing tests. Examples: `PMultiSelect` should be driven with its `update` CustomEvent, while unsupported components may need native fallbacks with the deviation documented.
