---
id: c026706e-d4c7-4a1a-9147-4825667b825e
title: Theme bootstrap scripts in Vitest should use window.* globals
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.85
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-14T03:01:24.945577Z'
updated_at: '2026-05-14T03:03:19.846327Z'
approved_at: null
---

For raw JS bootstrap files executed via new Function in Vitest/jsdom, bare globals like localStorage/document can throw ReferenceError and trigger ESLint no-undef. Use window.localStorage and window.document explicitly in public script files.
