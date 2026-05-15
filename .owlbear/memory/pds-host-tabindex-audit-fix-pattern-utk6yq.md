---
id: 98cb083c-b8c9-4f04-b4bf-9f495bee79e4
title: PDS host tabindex audit fix pattern
categories:
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-15T19:26:50.489934Z'
updated_at: '2026-05-15T22:16:50.089242Z'
approved_at: null
---

For Cockpit AC-7 DOM audits that inspect PDS/custom-element hosts (`p-button`, `p-input-search`, `p-select`, `p-multi-select`, `p-checkbox`), hosts may default to `tabIndex=-1` even when internal controls are usable. To satisfy strict host-level keyboard-reachability gates, set explicit `tabIndex={0}` on rendered host controls.
